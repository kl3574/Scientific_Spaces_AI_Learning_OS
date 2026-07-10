from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import AbstractSet, Any, Iterable

import faiss
import numpy as np

from app.llm.fake import FakeLLMProvider
from app.rag.chunking import ArticleChunk, chunk_article
from app.rag.embeddings import (
    EmbeddingProvider,
    FakeEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)
from app.rag.vector_store import FaissVectorStore, SearchResult
from app.rag.service import NO_SOURCE_ANSWER, RagIndex, RagService
from app.storage.article_store import StoredArticle


DEFAULT_FAKE_EMBEDDING_DIMENSION = 128
EMBEDDING_INPUT_STRATEGY = "article_title_section_text_v1"
_ASCII_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


class CorpusValidationError(ValueError):
    pass


class FullCorpusIndexError(RuntimeError):
    pass


@dataclass(frozen=True)
class FullCorpusChunk:
    chunk_id: str
    article_id: str
    article_title: str
    article_url: str
    section: str
    chunk_index: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "article_id": self.article_id,
            "article_title": self.article_title,
            "article_url": self.article_url,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FullCorpusChunk":
        return cls(
            chunk_id=str(data["chunk_id"]),
            article_id=str(data["article_id"]),
            article_title=str(data["article_title"]),
            article_url=str(data["article_url"]),
            section=str(data["section"]),
            chunk_index=int(data["chunk_index"]),
            text=str(data["text"]),
        )

    def to_article_chunk(self) -> ArticleChunk:
        return ArticleChunk(
            article_id=self.article_id,
            article_title=self.article_title,
            article_url=self.article_url,
            section_title=self.section,
            chunk_index=self.chunk_index,
            content=self.text,
        )

    def to_source(self, *, score: float) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "title": self.article_title,
            "url": self.article_url,
            "section": self.section,
            "chunk_id": self.chunk_id,
            "score": score,
        }


@dataclass(frozen=True)
class LoadedFullCorpusIndex:
    manifest: dict[str, Any]
    chunks: list[FullCorpusChunk]
    vector_store: FaissVectorStore


class FullCorpusRagService:
    def __init__(
        self,
        *,
        loaded_index: LoadedFullCorpusIndex,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self.loaded_index = loaded_index
        self.embedding_provider = embedding_provider
        self._service = RagService(
            embedding_provider=embedding_provider,
            llm_provider=FakeLLMProvider(),
        )
        article_chunks = [chunk.to_article_chunk() for chunk in loaded_index.chunks]
        self._corpus_tokens = local_support_tokens(article_chunks)
        self._service.index = RagIndex(
            article_count=int(loaded_index.manifest["article_count"]),
            chunks=article_chunks,
            vector_store=loaded_index.vector_store,
        )

    @classmethod
    def load(
        cls,
        *,
        article_store_path: Path | str,
        index_dir: Path | str,
        allow_real_provider: bool = False,
    ) -> "FullCorpusRagService":
        root = _resolve_index_dir(Path(index_dir).expanduser().resolve())
        loaded = load_full_corpus_index(root, article_store_path=article_store_path)
        provider = embedding_provider_for_manifest(
            loaded.manifest,
            allow_real_provider=allow_real_provider,
        )
        return cls(loaded_index=loaded, embedding_provider=provider)

    def has_local_support(self, question: str) -> bool:
        return has_local_token_support(question, self._corpus_tokens)

    def search(self, *, question: str, top_k: int = 20) -> list[SearchResult]:
        if top_k <= 0 or not self.has_local_support(question):
            return []
        return self.loaded_index.vector_store.search(
            question,
            top_k=min(top_k, 20),
            embedding_provider=self.embedding_provider,
        )

    def answer(self, *, question: str, top_k: int = 5) -> dict[str, Any]:
        results = self.search(question=question, top_k=top_k)
        if not results:
            return {"answer": NO_SOURCE_ANSWER, "sources": []}
        contexts = [
            {
                "content": result.chunk.content,
                "article_title": result.chunk.article_title,
                "section_title": result.chunk.section_title,
            }
            for result in results
        ]
        return {
            "answer": self._service.llm_provider.chat(question=question, contexts=contexts),
            "sources": [result.chunk.source() for result in results],
        }


def embedding_provider_for_manifest(
    manifest: dict[str, Any],
    *,
    allow_real_provider: bool = False,
) -> EmbeddingProvider:
    provider_name = str(manifest["provider"])
    dimension = int(manifest["embedding_dimension"])
    if provider_name == "fake":
        return FakeEmbeddingProvider(dimension=dimension)
    if provider_name == "openai":
        if not allow_real_provider:
            raise FullCorpusIndexError("Real-provider index loading requires explicit opt-in")
        if os.getenv("CI"):
            raise FullCorpusIndexError("Real-provider full-corpus execution is disabled in CI")
        if not os.getenv("OPENAI_API_KEY"):
            raise FullCorpusIndexError("OPENAI_API_KEY is required to query an openai index")
        return OpenAICompatibleEmbeddingProvider(dimension=dimension)
    raise FullCorpusIndexError(f"Unsupported index provider: {provider_name}")


def load_full_corpus_articles(path: Path | str) -> list[StoredArticle]:
    source = Path(path)
    if not source.is_file():
        raise CorpusValidationError(f"Article store does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusValidationError(f"Article store is not valid JSON: {source}") from exc
    if not isinstance(payload, list):
        raise CorpusValidationError("Article store root must be a JSON list")

    articles: list[StoredArticle] = []
    urls: set[str] = set()
    article_ids: set[str] = set()
    required = {"id", "title", "url", "content", "metadata"}
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise CorpusValidationError(f"Article at index {index} must be an object")
        missing = sorted(required - item.keys())
        if missing:
            raise CorpusValidationError(f"Article at index {index} missing fields: {', '.join(missing)}")

        article_id = _required_text(item["id"], field="id", index=index)
        title = _required_text(item["title"], field="title", index=index)
        url = _required_text(item["url"], field="url", index=index)
        content = _required_text(item["content"], field="content", index=index)
        metadata = item["metadata"]
        if not isinstance(metadata, dict):
            raise CorpusValidationError(f"Article at index {index} metadata must be an object")
        if url in urls:
            raise CorpusValidationError(f"Article store contains duplicate URL: {url}")
        if article_id in article_ids:
            raise CorpusValidationError(f"Article store contains duplicate id: {article_id}")
        urls.add(url)
        article_ids.add(article_id)
        articles.append(
            StoredArticle(
                id=article_id,
                title=title,
                url=url,
                content=content,
                metadata=dict(metadata),
            )
        )
    return sorted(articles, key=lambda article: (article.url, article.id))


def compute_corpus_fingerprint(articles: list[StoredArticle]) -> str:
    digest = hashlib.sha256()
    for article in sorted(articles, key=lambda item: (item.url, item.id)):
        record = {
            "article_id": article.id,
            "url": article.url,
            "content_sha256": hashlib.sha256(article.content.encode("utf-8")).hexdigest(),
            "metadata": article.metadata,
        }
        digest.update(_canonical_json(record).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def chunk_full_corpus(articles: list[StoredArticle]) -> list[FullCorpusChunk]:
    chunks: list[FullCorpusChunk] = []
    for article in sorted(articles, key=lambda item: (item.url, item.id)):
        article_chunks = chunk_article(
            article_id=article.id,
            article_title=article.title,
            article_url=article.url,
            content=article.content,
        )
        for chunk in article_chunks:
            chunks.append(
                FullCorpusChunk(
                    chunk_id=f"{chunk.article_id}:{chunk.chunk_index}",
                    article_id=chunk.article_id,
                    article_title=chunk.article_title,
                    article_url=chunk.article_url,
                    section=chunk.section_title,
                    chunk_index=chunk.chunk_index,
                    text=chunk.content,
                )
            )
    return chunks


def audit_full_corpus_chunks(
    articles: list[StoredArticle],
    chunks: list[FullCorpusChunk],
) -> dict[str, int | float]:
    article_ids = {article.id for article in articles}
    chunk_counts = {article_id: 0 for article_id in article_ids}
    for chunk in chunks:
        if chunk.article_id in chunk_counts:
            chunk_counts[chunk.article_id] += 1
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    character_lengths = [len(chunk.text) for chunk in chunks]
    per_article = list(chunk_counts.values())
    indexed_article_count = sum(1 for count in per_article if count > 0)
    return {
        "article_count": len(articles),
        "total_chunk_count": len(chunks),
        "chunks_per_article_min": min(per_article, default=0),
        "chunks_per_article_max": max(per_article, default=0),
        "chunks_per_article_mean": _mean(per_article),
        "chunks_per_article_median": _median(per_article),
        "chunk_character_length_min": min(character_lengths, default=0),
        "chunk_character_length_max": max(character_lengths, default=0),
        "chunk_character_length_mean": _mean(character_lengths),
        "empty_chunk_count": sum(1 for chunk in chunks if not chunk.text.strip()),
        "duplicate_chunk_id_count": len(chunk_ids) - len(set(chunk_ids)),
        "missing_source_title_count": sum(1 for chunk in chunks if not chunk.article_title.strip()),
        "missing_source_url_count": sum(1 for chunk in chunks if not chunk.article_url.strip()),
        "missing_section_count": sum(1 for chunk in chunks if not chunk.section.strip()),
        "articles_without_chunks_count": len(articles) - indexed_article_count,
        "indexed_article_count": indexed_article_count,
        "indexed_article_coverage_rate": indexed_article_count / len(articles) if articles else 1.0,
    }


def build_full_corpus_index(
    *,
    article_store_path: Path | str,
    output_dir: Path | str,
    provider_name: str = "fake",
    rebuild: bool = False,
    embedding_batch_size: int = 128,
    embedding_dimension: int | None = None,
    expected_article_count: int | None = None,
    allow_real_provider: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    source_path = Path(article_store_path).expanduser().resolve()
    output_root = Path(output_dir).expanduser().resolve()
    index_dir = output_root / "index"
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (output_root / "logs").mkdir(parents=True, exist_ok=True)

    articles = load_full_corpus_articles(source_path)
    if not articles:
        raise CorpusValidationError("Article store must contain at least one article")
    if expected_article_count is not None and len(articles) != expected_article_count:
        raise CorpusValidationError(
            f"Expected {expected_article_count} Articles but found {len(articles)} in {source_path}"
        )
    fingerprint = compute_corpus_fingerprint(articles)
    normalized_provider = provider_name.strip().lower()
    requested_dimension = embedding_dimension or (
        DEFAULT_FAKE_EMBEDDING_DIMENSION if normalized_provider == "fake" else 1536
    )
    _recover_interrupted_replace(index_dir)
    existing_manifest = _read_manifest_if_complete(index_dir)
    existing_manifest_matches = bool(existing_manifest) and _manifest_matches(
        existing_manifest or {},
        fingerprint=fingerprint,
        provider_name=normalized_provider,
        article_count=len(articles),
        embedding_dimension=requested_dimension,
        embedding_input_strategy=EMBEDDING_INPUT_STRATEGY,
    )
    if existing_manifest_matches:
        try:
            load_full_corpus_index(index_dir, article_store_path=source_path)
        except Exception as exc:
            if not rebuild:
                raise FullCorpusIndexError("Existing index artifacts failed integrity validation") from exc
        else:
            previous_summary = _read_json_if_object(reports_dir / "build_summary.json")
            result = _no_op_result(
                manifest=existing_manifest or {},
                index_dir=index_dir,
                elapsed_seconds=time.perf_counter() - started,
            )
            last_rebuild = _last_rebuild(previous_summary)
            if last_rebuild is not None:
                result["last_rebuild"] = last_rebuild
            _write_json_atomic(reports_dir / "build_summary.json", result)
            _cleanup_index_backups(index_dir)
            return result
    if existing_manifest and not rebuild:
        raise FullCorpusIndexError("Existing index is stale; pass rebuild=True to replace it")

    staging = output_root / f".index-staging-{uuid.uuid4().hex}"
    staging.mkdir(parents=True)
    try:
        chunks = chunk_full_corpus(articles)
        audit = audit_full_corpus_chunks(articles, chunks)
        _validate_chunk_audit(audit)
        provider = _embedding_provider(
            normalized_provider,
            dimension=requested_dimension,
            allow_real_provider=allow_real_provider,
        )
        faiss_index = _build_faiss_index(
            chunks,
            embedding_provider=provider,
            batch_size=embedding_batch_size,
        )
        faiss.write_index(faiss_index, str(staging / "faiss.index"))
        _write_chunks(staging / "chunks.jsonl", chunks)
        index_size = (staging / "faiss.index").stat().st_size
        chunk_metadata_size = (staging / "chunks.jsonl").stat().st_size
        elapsed = time.perf_counter() - started
        manifest = {
            "schema_version": 2,
            "article_count": len(articles),
            "unique_url_count": len({article.url for article in articles}),
            "chunk_count": len(chunks),
            "provider": normalized_provider,
            "embedding_dimension": int(faiss_index.d),
            "embedding_input_strategy": EMBEDDING_INPUT_STRATEGY,
            "embedding_model": _embedding_model_name(provider),
            "embedding_batch_size": embedding_batch_size,
            "embedding_call_count_estimate": math.ceil(len(chunks) / embedding_batch_size),
            "build_timestamp": datetime.now(UTC).isoformat(),
            "source_store_path": str(source_path),
            "corpus_fingerprint": fingerprint,
            "index_file": "faiss.index",
            "index_file_size_bytes": index_size,
            "index_file_sha256": _file_sha256(staging / "faiss.index"),
            "chunk_metadata_file": "chunks.jsonl",
            "chunk_metadata_size_bytes": chunk_metadata_size,
            "chunk_metadata_sha256": _file_sha256(staging / "chunks.jsonl"),
            "chunking_audit": audit,
        }
        _write_json(staging / "manifest.json", manifest)
        atomic_replace_directory(staging, index_dir)
        _cleanup_index_backups(index_dir)
        result = {
            "status": "PASS",
            "action": "rebuilt",
            "article_count": len(articles),
            "unique_url_count": len({article.url for article in articles}),
            "chunk_count": len(chunks),
            "provider": normalized_provider,
            "embedding_dimension": int(faiss_index.d),
            "embedding_input_strategy": EMBEDDING_INPUT_STRATEGY,
            "embedding_model": _embedding_model_name(provider),
            "embedding_batch_size": embedding_batch_size,
            "embedding_call_count_estimate": math.ceil(len(chunks) / embedding_batch_size),
            "corpus_fingerprint": fingerprint,
            "build_elapsed_seconds": elapsed,
            "chunks_per_second": len(chunks) / elapsed if elapsed else 0.0,
            "index_size_bytes": index_size,
            "chunk_metadata_size_bytes": chunk_metadata_size,
            "peak_memory_bytes": _peak_memory_bytes(),
            "manifest_path": str(index_dir / "manifest.json"),
            "atomic_replace": True,
            "corpus_fingerprint_unchanged": existing_manifest is not None
            and existing_manifest.get("corpus_fingerprint") == fingerprint,
            "article_count_unchanged": existing_manifest is not None
            and existing_manifest.get("article_count") == len(articles),
            "chunk_count_unchanged": existing_manifest is not None
            and existing_manifest.get("chunk_count") == len(chunks),
            "chunking_audit": audit,
        }
        _write_json_atomic(reports_dir / "build_summary.json", result)
        return result
    except Exception as exc:
        failure = {
            "status": "BLOCKED",
            "action": "failed",
            "provider": normalized_provider,
            "article_count": len(articles),
            "corpus_fingerprint": fingerprint,
            "build_elapsed_seconds": time.perf_counter() - started,
            "error": f"{type(exc).__name__}: {exc}",
            "existing_index_preserved": index_dir.exists(),
        }
        _write_json_atomic(reports_dir / "build_summary.json", failure)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def load_full_corpus_index(
    index_dir: Path | str,
    *,
    article_store_path: Path | str | None = None,
) -> LoadedFullCorpusIndex:
    root = Path(index_dir)
    manifest_path = root / "manifest.json"
    chunks_path = root / "chunks.jsonl"
    faiss_path = root / "faiss.index"
    for required_path in (manifest_path, chunks_path, faiss_path):
        if not required_path.is_file():
            raise FullCorpusIndexError(f"Index artifact is missing: {required_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FullCorpusIndexError("Index manifest is not valid JSON") from exc
    _validate_artifact(
        faiss_path,
        expected_size=manifest.get("index_file_size_bytes"),
        expected_sha256=manifest.get("index_file_sha256"),
    )
    _validate_artifact(
        chunks_path,
        expected_size=manifest.get("chunk_metadata_size_bytes"),
        expected_sha256=manifest.get("chunk_metadata_sha256"),
    )
    try:
        chunks = [
            FullCorpusChunk.from_dict(json.loads(line))
            for line in chunks_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FullCorpusIndexError("Index chunk metadata is invalid") from exc
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise FullCorpusIndexError("Index chunk metadata contains duplicate chunk IDs")
    if any(not chunk.text.strip() for chunk in chunks):
        raise FullCorpusIndexError("Index chunk metadata contains empty text")
    if any(not chunk.article_title or not chunk.article_url or not chunk.section for chunk in chunks):
        raise FullCorpusIndexError("Index chunk metadata is missing source provenance")

    try:
        index = faiss.read_index(str(faiss_path))
    except RuntimeError as exc:
        raise FullCorpusIndexError("FAISS index cannot be loaded") from exc
    expected_chunks = int(manifest.get("chunk_count", -1))
    expected_dimension = int(manifest.get("embedding_dimension", -1))
    if expected_chunks != len(chunks) or index.ntotal != len(chunks):
        raise FullCorpusIndexError("FAISS row count does not match chunk metadata")
    if index.d != expected_dimension:
        raise FullCorpusIndexError("FAISS dimension does not match manifest")

    if article_store_path is not None:
        articles = load_full_corpus_articles(article_store_path)
        fingerprint = compute_corpus_fingerprint(articles)
        if manifest.get("corpus_fingerprint") != fingerprint:
            raise FullCorpusIndexError("Index fingerprint does not match Article corpus")
        if manifest.get("article_count") != len(articles):
            raise FullCorpusIndexError("Index article count does not match Article corpus")
        if {chunk.article_id for chunk in chunks} != {article.id for article in articles}:
            raise FullCorpusIndexError("Index chunk article IDs do not match Article corpus")

    article_chunks = [chunk.to_article_chunk() for chunk in chunks]
    return LoadedFullCorpusIndex(
        manifest=manifest,
        chunks=chunks,
        vector_store=FaissVectorStore(index=index, chunks=article_chunks),
    )


def atomic_replace_directory(staging: Path | str, target: Path | str) -> None:
    staged_path = Path(staging)
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    backup = target_path.with_name(f".{target_path.name}.backup-{uuid.uuid4().hex}")
    had_target = target_path.exists()
    if had_target:
        os.replace(target_path, backup)
    try:
        os.replace(staged_path, target_path)
    except Exception:
        if had_target and backup.exists():
            os.replace(backup, target_path)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


def _recover_interrupted_replace(index_dir: Path) -> None:
    if index_dir.exists():
        return
    backups = sorted(
        index_dir.parent.glob(f".{index_dir.name}.backup-*"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    if backups:
        os.replace(backups[0], index_dir)


def _cleanup_index_backups(index_dir: Path) -> None:
    for backup in index_dir.parent.glob(f".{index_dir.name}.backup-*"):
        if backup.is_dir():
            shutil.rmtree(backup)
        else:
            backup.unlink(missing_ok=True)


def _required_text(value: Any, *, field: str, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CorpusValidationError(f"Article at index {index} has empty or invalid {field}")
    return value.strip() if field != "content" else value


def _canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _mean(values: list[int]) -> float:
    return float(mean(values)) if values else 0.0


def _median(values: list[int]) -> float:
    return float(median(values)) if values else 0.0


def _embedding_provider(
    name: str,
    *,
    dimension: int,
    allow_real_provider: bool,
) -> EmbeddingProvider:
    if name == "fake":
        return FakeEmbeddingProvider(dimension=dimension)
    if name == "openai":
        if not allow_real_provider:
            raise FullCorpusIndexError("provider=openai requires explicit opt-in")
        if os.getenv("CI"):
            raise FullCorpusIndexError("Real-provider full-corpus execution is disabled in CI")
        if not os.getenv("OPENAI_API_KEY"):
            raise FullCorpusIndexError("OPENAI_API_KEY is required for provider=openai")
        return OpenAICompatibleEmbeddingProvider(dimension=dimension)
    raise FullCorpusIndexError(f"Unsupported embedding provider: {name}")


def _embedding_model_name(provider: EmbeddingProvider) -> str:
    if isinstance(provider, FakeEmbeddingProvider):
        return "deterministic-hash-v1"
    return str(getattr(provider, "model", "unknown"))


def _build_faiss_index(
    chunks: list[FullCorpusChunk],
    *,
    embedding_provider: EmbeddingProvider,
    batch_size: int,
) -> faiss.Index:
    if not chunks:
        raise FullCorpusIndexError("Cannot build an index without chunks")
    if batch_size <= 0:
        raise FullCorpusIndexError("embedding_batch_size must be positive")
    index: faiss.Index | None = None
    for offset in range(0, len(chunks), batch_size):
        batch = chunks[offset : offset + batch_size]
        vectors = np.asarray(
            embedding_provider.embed([_embedding_text(chunk) for chunk in batch]),
            dtype="float32",
        )
        if vectors.ndim != 2 or vectors.shape[0] != len(batch):
            raise FullCorpusIndexError("Embedding provider returned an invalid vector batch")
        if index is None:
            index = faiss.IndexFlatL2(int(vectors.shape[1]))
        elif index.d != vectors.shape[1]:
            raise FullCorpusIndexError("Embedding dimension changed during index build")
        index.add(vectors)
    if index is None:
        raise FullCorpusIndexError("Embedding provider returned no vectors")
    return index


def _validate_chunk_audit(audit: dict[str, int | float]) -> None:
    failure_metrics = (
        "empty_chunk_count",
        "duplicate_chunk_id_count",
        "missing_source_title_count",
        "missing_source_url_count",
        "missing_section_count",
        "articles_without_chunks_count",
    )
    failures = [name for name in failure_metrics if audit[name] != 0]
    if failures:
        raise FullCorpusIndexError(f"Chunk audit failed: {', '.join(failures)}")


def _write_chunks(path: Path, chunks: list[FullCorpusChunk]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(_canonical_json(chunk.to_dict()))
            handle.write("\n")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        _write_json(temporary, data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_manifest_if_complete(index_dir: Path) -> dict[str, Any] | None:
    required = (index_dir / "manifest.json", index_dir / "faiss.index", index_dir / "chunks.jsonl")
    if not all(path.is_file() for path in required):
        return None
    try:
        return json.loads(required[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _manifest_matches(
    manifest: dict[str, Any],
    *,
    fingerprint: str,
    provider_name: str,
    article_count: int,
    embedding_dimension: int,
    embedding_input_strategy: str,
) -> bool:
    return (
        manifest.get("schema_version") == 2
        and manifest.get("corpus_fingerprint") == fingerprint
        and manifest.get("provider") == provider_name
        and manifest.get("article_count") == article_count
        and manifest.get("embedding_dimension") == embedding_dimension
        and manifest.get("embedding_input_strategy") == embedding_input_strategy
        and bool(manifest.get("index_file_sha256"))
        and bool(manifest.get("chunk_metadata_sha256"))
    )


def _no_op_result(
    *,
    manifest: dict[str, Any],
    index_dir: Path,
    elapsed_seconds: float,
) -> dict[str, Any]:
    return {
        "status": "PASS",
        "action": "no_op",
        "second_run_action": "no_op",
        "article_count": int(manifest["article_count"]),
        "unique_url_count": int(manifest["unique_url_count"]),
        "chunk_count": int(manifest["chunk_count"]),
        "provider": str(manifest["provider"]),
        "embedding_dimension": int(manifest["embedding_dimension"]),
        "embedding_input_strategy": str(manifest["embedding_input_strategy"]),
        "embedding_model": str(manifest["embedding_model"]),
        "embedding_batch_size": int(manifest["embedding_batch_size"]),
        "embedding_call_count_estimate": int(manifest["embedding_call_count_estimate"]),
        "corpus_fingerprint": str(manifest["corpus_fingerprint"]),
        "build_elapsed_seconds": elapsed_seconds,
        "second_run_elapsed_seconds": elapsed_seconds,
        "chunks_per_second": 0.0,
        "index_size_bytes": (index_dir / "faiss.index").stat().st_size,
        "chunk_metadata_size_bytes": (index_dir / "chunks.jsonl").stat().st_size,
        "peak_memory_bytes": _peak_memory_bytes(),
        "manifest_path": str(index_dir / "manifest.json"),
        "atomic_replace": True,
        "corpus_fingerprint_unchanged": True,
        "article_count_unchanged": True,
        "chunk_count_unchanged": True,
        "chunking_audit": manifest.get("chunking_audit", {}),
    }


def _read_json_if_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _last_rebuild(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if not summary:
        return None
    if summary.get("action") == "rebuilt":
        return summary
    nested = summary.get("last_rebuild")
    return nested if isinstance(nested, dict) and nested.get("action") == "rebuilt" else None


def _peak_memory_bytes() -> int | None:
    try:
        import resource

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    except (ImportError, ValueError):
        return None


def _embedding_text(chunk: FullCorpusChunk) -> str:
    return f"{chunk.article_title}\n{chunk.section}\n{chunk.text}"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_artifact(path: Path, *, expected_size: Any, expected_sha256: Any) -> None:
    if not isinstance(expected_size, int) or path.stat().st_size != expected_size:
        raise FullCorpusIndexError(f"Index artifact size mismatch: {path.name}")
    if not isinstance(expected_sha256, str) or _file_sha256(path) != expected_sha256:
        raise FullCorpusIndexError(f"Index artifact checksum mismatch: {path.name}")


def _resolve_index_dir(path: Path) -> Path:
    if (path / "manifest.json").is_file():
        return path
    if (path / "index" / "manifest.json").is_file():
        return path / "index"
    raise FullCorpusIndexError(f"Full-corpus index manifest not found under: {path}")


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    tokens = set(_ASCII_TOKEN_RE.findall(lowered))
    cjk_chars = _CJK_RE.findall(lowered)
    tokens.update(cjk_chars)
    tokens.update("".join(pair) for pair in zip(cjk_chars, cjk_chars[1:]))
    return tokens


def local_support_tokens(chunks: Iterable[ArticleChunk]) -> frozenset[str]:
    tokens: set[str] = set()
    for chunk in chunks:
        tokens.update(_tokens(chunk.content))
        tokens.update(_tokens(chunk.article_title))
        tokens.update(_tokens(chunk.section_title))
    return frozenset(tokens)


def has_local_token_support(question: str, corpus_tokens: AbstractSet[str]) -> bool:
    return bool(_tokens(question) & corpus_tokens)
