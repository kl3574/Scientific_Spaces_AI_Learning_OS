from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Protocol

from app.rag.chunking import ArticleChunk, chunk_article
from app.rag.embeddings import EmbeddingProvider, FakeEmbeddingProvider
from app.rag.full_corpus import FullCorpusRagService, has_local_token_support, local_support_tokens
from app.rag.vector_store import FaissVectorStore, SearchResult
from app.services.article_reader import article_store_path, get_article, list_articles
from app.tutor.models import TutorRequest


@dataclass(frozen=True)
class RetrievalResult:
    results: list[SearchResult]
    locally_supported: bool


class TutorRetriever(Protocol):
    def retrieve(self, request: TutorRequest, candidate_limit: int) -> RetrievalResult:
        """Return bounded Article chunks for the Tutor source selector."""


@dataclass(frozen=True)
class _PersistedIndexCacheKey:
    article_store_path: str
    article_store_signature: tuple[int, int] | None
    index_dir: str
    manifest_signature: tuple[int, int] | None
    faiss_signature: tuple[int, int] | None
    chunks_signature: tuple[int, int] | None


_PERSISTED_INDEX_CACHE: dict[_PersistedIndexCacheKey, FullCorpusRagService] = {}
_PERSISTED_INDEX_CACHE_LOCK = RLock()


class ConfiguredTutorRetriever:
    """Retrieve Tutor candidates from a configured index or a small local fixture."""

    def __init__(self, *, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.embedding_provider = embedding_provider or FakeEmbeddingProvider()

    def retrieve(self, request: TutorRequest, candidate_limit: int) -> RetrievalResult:
        top_k = max(1, min(candidate_limit, 20))
        configured_index_dir = os.getenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR")
        configured_service: FullCorpusRagService | None = None
        if configured_index_dir:
            configured_service = _load_cached_full_corpus_service(
                article_store=article_store_path(),
                configured_index_dir=Path(configured_index_dir),
            )

        if request.article_id:
            return self._retrieve_article(request=request, top_k=top_k)

        if configured_service is not None:
            return RetrievalResult(
                results=configured_service.search(question=request.question, top_k=top_k),
                locally_supported=configured_service.has_local_support(request.question),
            )

        return self._retrieve_articles(articles=list_articles(), question=request.question, top_k=top_k)

    def _retrieve_article(self, *, request: TutorRequest, top_k: int) -> RetrievalResult:
        article = get_article(request.article_id or "")
        return self._retrieve_articles(
            articles=[article] if article is not None else [],
            question=request.question,
            top_k=top_k,
        )

    def _retrieve_articles(self, *, articles, question: str, top_k: int) -> RetrievalResult:
        chunks: list[ArticleChunk] = []
        for article in articles:
            chunks.extend(
                chunk_article(
                    article_id=article.id,
                    article_title=article.title,
                    article_url=article.url,
                    content=article.content,
                )
            )
        if not chunks:
            return RetrievalResult(results=[], locally_supported=False)
        if not has_local_token_support(question, local_support_tokens(chunks)):
            return RetrievalResult(results=[], locally_supported=False)
        vector_store = FaissVectorStore.from_chunks(chunks, self.embedding_provider)
        results = vector_store.search(question, top_k=top_k, embedding_provider=self.embedding_provider)
        return RetrievalResult(results=results, locally_supported=True)


def reset_configured_retriever_cache() -> None:
    with _PERSISTED_INDEX_CACHE_LOCK:
        _PERSISTED_INDEX_CACHE.clear()


def _load_cached_full_corpus_service(
    *,
    article_store: Path,
    configured_index_dir: Path,
) -> FullCorpusRagService:
    key = _persisted_index_cache_key(article_store=article_store, configured_index_dir=configured_index_dir)
    with _PERSISTED_INDEX_CACHE_LOCK:
        service = _PERSISTED_INDEX_CACHE.get(key)
        if service is not None:
            return service
        service = FullCorpusRagService.load(
            article_store_path=article_store,
            index_dir=configured_index_dir,
        )
        _PERSISTED_INDEX_CACHE.clear()
        _PERSISTED_INDEX_CACHE[key] = service
        return service


def _persisted_index_cache_key(*, article_store: Path, configured_index_dir: Path) -> _PersistedIndexCacheKey:
    resolved_store = article_store.expanduser().resolve()
    resolved_index_dir = configured_index_dir.expanduser().resolve()
    artifacts_dir = _artifact_directory(resolved_index_dir)
    return _PersistedIndexCacheKey(
        article_store_path=str(resolved_store),
        article_store_signature=_file_signature(resolved_store),
        index_dir=str(resolved_index_dir),
        manifest_signature=_file_signature(artifacts_dir / "manifest.json"),
        faiss_signature=_file_signature(artifacts_dir / "faiss.index"),
        chunks_signature=_file_signature(artifacts_dir / "chunks.jsonl"),
    )


def _artifact_directory(configured_index_dir: Path) -> Path:
    return configured_index_dir if (configured_index_dir / "manifest.json").is_file() else configured_index_dir / "index"


def _file_signature(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return (stat.st_mtime_ns, stat.st_size)
