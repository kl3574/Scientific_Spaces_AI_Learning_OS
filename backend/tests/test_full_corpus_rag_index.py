from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

import pytest

from app.rag.full_corpus import (
    CorpusValidationError,
    FullCorpusChunk,
    FullCorpusIndexError,
    audit_full_corpus_chunks,
    atomic_replace_directory,
    build_full_corpus_index,
    chunk_full_corpus,
    compute_corpus_fingerprint,
    load_full_corpus_articles,
    load_full_corpus_index,
)
from app.rag.embeddings import FakeEmbeddingProvider


REPO_ROOT = Path(__file__).resolve().parents[2]


def _article(
    article_id: str,
    *,
    content: str = "# Section\n\nGrounded article content.",
    title: str | None = None,
) -> dict[str, object]:
    return {
        "id": article_id,
        "title": title or f"Article {article_id}",
        "url": f"https://spaces.ac.cn/archives/{article_id}",
        "content": content,
        "metadata": {
            "date": "2024-01-01",
            "category": "math",
            "references": [],
            "images": [],
        },
    }


def _write_store(path: Path, articles: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")


def test_full_corpus_loader_accepts_article_contract_and_rejects_missing_content(tmp_path: Path) -> None:
    valid_store = tmp_path / "valid.json"
    invalid_store = tmp_path / "invalid.json"
    _write_store(valid_store, [_article("1")])
    _write_store(invalid_store, [_article("1", content="")])

    articles = load_full_corpus_articles(valid_store)

    assert len(articles) == 1
    assert articles[0].id == "1"
    assert articles[0].metadata["category"] == "math"
    with pytest.raises(CorpusValidationError, match="content"):
        load_full_corpus_articles(invalid_store)


def test_full_corpus_loader_rejects_duplicate_urls(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    first = _article("1")
    second = _article("2")
    second["url"] = first["url"]
    _write_store(store, [first, second])

    with pytest.raises(CorpusValidationError, match="duplicate URL"):
        load_full_corpus_articles(store)


def test_corpus_fingerprint_is_order_independent_and_content_sensitive(tmp_path: Path) -> None:
    first_store = tmp_path / "first.json"
    reordered_store = tmp_path / "reordered.json"
    changed_store = tmp_path / "changed.json"
    first = [_article("1"), _article("2")]
    _write_store(first_store, first)
    _write_store(reordered_store, list(reversed(first)))
    _write_store(changed_store, [_article("1"), _article("2", content="# Section\n\nChanged content.")])

    first_fingerprint = compute_corpus_fingerprint(load_full_corpus_articles(first_store))
    reordered_fingerprint = compute_corpus_fingerprint(load_full_corpus_articles(reordered_store))
    changed_fingerprint = compute_corpus_fingerprint(load_full_corpus_articles(changed_store))

    assert reordered_fingerprint == first_fingerprint
    assert changed_fingerprint != first_fingerprint


def test_chunk_audit_requires_complete_provenance_and_detects_duplicate_ids(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    _write_store(
        store,
        [
            _article("1", content="# First\n\nAlpha.\n\n## Second\n\nBeta."),
            _article("2", content="# Only\n\nGamma."),
        ],
    )
    articles = load_full_corpus_articles(store)
    chunks = chunk_full_corpus(articles)

    audit = audit_full_corpus_chunks(articles, chunks)

    assert audit["article_count"] == 2
    assert audit["total_chunk_count"] == 3
    assert audit["articles_without_chunks_count"] == 0
    assert audit["empty_chunk_count"] == 0
    assert audit["duplicate_chunk_id_count"] == 0
    assert audit["missing_source_title_count"] == 0
    assert audit["missing_source_url_count"] == 0
    assert audit["missing_section_count"] == 0
    assert all(chunk.chunk_id for chunk in chunks)
    assert all(chunk.article_id and chunk.article_title and chunk.article_url for chunk in chunks)
    assert all(chunk.section and chunk.text for chunk in chunks)

    duplicate_audit = audit_full_corpus_chunks(articles, [*chunks, chunks[0]])
    assert duplicate_audit["duplicate_chunk_id_count"] == 1


def test_build_writes_manifest_and_loadable_faiss_index(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store, [_article("1"), _article("2", content="# Matrix\n\nMatrix decomposition SVD.")])

    result = build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    loaded = load_full_corpus_index(output / "index", article_store_path=store)

    assert result["status"] == "PASS"
    assert result["action"] == "rebuilt"
    assert result["article_count"] == 2
    assert result["chunk_count"] == 2
    assert result["atomic_replace"] is True
    assert (output / "index" / "faiss.index").is_file()
    assert (output / "index" / "chunks.jsonl").is_file()
    assert (output / "index" / "manifest.json").is_file()
    assert (output / "reports" / "build_summary.json").is_file()
    assert loaded.manifest["provider"] == "fake"
    assert loaded.manifest["embedding_dimension"] == 128
    assert loaded.manifest["embedding_input_strategy"] == "article_title_section_text_v1"
    assert loaded.manifest["article_count"] == 2
    assert loaded.manifest["chunk_count"] == 2
    assert loaded.vector_store.index.ntotal == 2
    assert len(loaded.chunks) == 2


def test_repeated_build_noops_when_fingerprint_is_unchanged(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store, [_article("1")])

    first = build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    second = build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )

    assert first["action"] == "rebuilt"
    assert second["action"] == "no_op"
    assert second["corpus_fingerprint"] == first["corpus_fingerprint"]
    assert second["article_count"] == first["article_count"]
    assert second["chunk_count"] == first["chunk_count"]
    assert second["second_run_action"] == "no_op"
    assert second["second_run_elapsed_seconds"] >= 0
    build_summary = json.loads((output / "reports" / "build_summary.json").read_text(encoding="utf-8"))
    assert build_summary["last_rebuild"]["action"] == "rebuilt"
    assert build_summary["last_rebuild"]["build_elapsed_seconds"] == first["build_elapsed_seconds"]


def test_full_corpus_embedding_includes_title_and_section(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(
        store,
        [
            _article("1", title="Unrelated heading", content="generic shared body"),
            _article("2", title="UniqueTargetPhrase", content="generic shared body"),
        ],
    )
    build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    loaded = load_full_corpus_index(output / "index", article_store_path=store)
    provider = FakeEmbeddingProvider(dimension=loaded.manifest["embedding_dimension"])

    results = loaded.vector_store.search("UniqueTargetPhrase", top_k=1, embedding_provider=provider)

    assert results[0].chunk.article_id == "2"


def test_corrupt_faiss_index_is_rebuilt_instead_of_false_noop(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store, [_article("1")])
    build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    (output / "index" / "faiss.index").write_bytes(b"corrupt")

    result = build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )

    assert result["action"] == "rebuilt"
    assert load_full_corpus_index(output / "index", article_store_path=store).vector_store.index.ntotal == 1


def test_index_loader_rejects_tampered_chunk_metadata(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store, [_article("1")])
    build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    chunks_path = output / "index" / "chunks.jsonl"
    record = json.loads(chunks_path.read_text(encoding="utf-8"))
    record["article_id"] = "not-in-corpus"
    record["chunk_id"] = "not-in-corpus:0"
    chunks_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    with pytest.raises(FullCorpusIndexError, match="checksum|size|article IDs"):
        load_full_corpus_index(output / "index", article_store_path=store)


def test_atomic_replace_restores_existing_directory_when_commit_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "index"
    staging = tmp_path / "staging"
    target.mkdir()
    staging.mkdir()
    (target / "marker.txt").write_text("old", encoding="utf-8")
    (staging / "marker.txt").write_text("new", encoding="utf-8")
    real_replace = os.replace

    def fail_staging_commit(source: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
        if Path(source) == staging:
            raise OSError("simulated commit failure")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", fail_staging_commit)

    with pytest.raises(OSError, match="simulated commit failure"):
        atomic_replace_directory(staging, target)

    assert target.is_dir()
    assert (target / "marker.txt").read_text(encoding="utf-8") == "old"


def test_build_recovers_backup_left_by_interrupted_atomic_replace(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store, [_article("1")])
    build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )
    backup = output / ".index.backup-interrupted"
    os.replace(output / "index", backup)

    result = build_full_corpus_index(
        article_store_path=store,
        output_dir=output,
        provider_name="fake",
        rebuild=True,
    )

    assert result["action"] == "no_op"
    assert (output / "index" / "manifest.json").is_file()
    assert not backup.exists()


def test_full_corpus_chunk_round_trip_preserves_source_fields() -> None:
    chunk = FullCorpusChunk(
        chunk_id="article-1:0",
        article_id="article-1",
        article_title="Attention",
        article_url="https://spaces.ac.cn/archives/6508",
        section="数学形式",
        chunk_index=0,
        text="$$QK^T$$",
    )

    restored = FullCorpusChunk.from_dict(chunk.to_dict())

    assert restored == chunk
    assert restored.to_source(score=0.25) == {
        "article_id": "article-1",
        "title": "Attention",
        "url": "https://spaces.ac.cn/archives/6508",
        "section": "数学形式",
        "chunk_id": "article-1:0",
        "score": 0.25,
    }


def test_full_corpus_cli_builds_fake_index_without_api_key(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store, [_article("1")])
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/rag/build_full_corpus_index.py",
            "--article-store",
            str(store),
            "--output-dir",
            str(output),
            "--provider",
            "fake",
            "--expected-article-count",
            "1",
            "--rebuild",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "PASS"
    assert payload["provider"] == "fake"
    assert payload["article_count"] == 1
    assert (output / "index" / "manifest.json").is_file()


def test_full_corpus_cli_rejects_partial_store_by_default(tmp_path: Path) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store, [_article("1")])

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/rag/build_full_corpus_index.py",
            "--article-store",
            str(store),
            "--output-dir",
            str(output),
            "--provider",
            "fake",
            "--rebuild",
        ],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode != 0
    assert "1311" in completed.stderr


def test_full_corpus_runtime_output_path_is_ignored() -> None:
    completed = subprocess.run(
        [
            "git",
            "check-ignore",
            ".local_data/scientific_spaces/rag/full_corpus/index/faiss.index",
        ],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0


def test_real_provider_requires_explicit_opt_in_before_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = tmp_path / "articles.json"
    output = tmp_path / "full_corpus"
    _write_store(store, [_article("1")])
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-sent")

    def reject_network(*_args, **_kwargs):
        raise AssertionError("network must not be reached without explicit opt-in")

    monkeypatch.setattr(urllib.request, "urlopen", reject_network)

    with pytest.raises(FullCorpusIndexError, match="explicit opt-in"):
        build_full_corpus_index(
            article_store_path=store,
            output_dir=output,
            provider_name="openai",
            rebuild=True,
        )
