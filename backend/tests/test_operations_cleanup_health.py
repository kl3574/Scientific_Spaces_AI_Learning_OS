from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.operations.cleanup import CleanupSafetyError, cleanup_local_data
from app.operations.health import audit_storage_capacity, check_local_system
from app.operations.inventory import build_local_data_manifest
from tests.operations_helpers import make_local_data_root


def _configure_runtime(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLE_STORE", str(root / "corpus/pilot/article_store/articles.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR", str(root / "rag/full_corpus"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_GRAPH_FILE", str(root / "graph/full_corpus/graph.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_LEARNING_FILE", str(root / "learning.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_FILE", str(root / "zotero_links.json"))
    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_FILE", str(root / "tutor_sessions.json"))


def test_cleanup_is_dry_run_by_default(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    log_file = root / "rag/full_corpus/logs/build.log"
    log_file.parent.mkdir(parents=True)
    log_file.write_text("log", encoding="utf-8")

    result = cleanup_local_data(root, categories=("temp", "logs", "browser-cache"))

    assert result.status == "PASS"
    assert result.dry_run is True
    assert log_file.exists()
    assert root / "cache/transient.cache" in result.candidate_paths


def test_cleanup_never_deletes_tier_one_and_requires_derived_confirmation(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    article_store = root / "corpus/pilot/article_store/articles.json"

    with pytest.raises(CleanupSafetyError, match="confirm-derived-delete"):
        cleanup_local_data(root, categories=("all-derived",), execute=True)

    result = cleanup_local_data(
        root,
        categories=("all-derived",),
        execute=True,
        confirm_derived_delete=True,
    )

    assert result.status == "PASS"
    assert article_store.exists()
    assert not (root / "corpus/local_library").exists()
    assert not (root / "rag/full_corpus").exists()
    assert not (root / "graph/full_corpus").exists()


def test_cleanup_rejects_unknown_category_and_clean_all_alias(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)

    with pytest.raises(CleanupSafetyError):
        cleanup_local_data(root, categories=("clean-all",))


def test_health_check_passes_for_consistent_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, corpus_fingerprint = make_local_data_root(tmp_path)
    _configure_runtime(monkeypatch, root)
    build_local_data_manifest(root, workers=4, write=True)

    report = check_local_system(root, workers=4, free_bytes=10_000_000)

    assert report.status == "PASS"
    assert report.corpus_fingerprint == corpus_fingerprint
    assert report.article_count == 2
    assert report.capacity.total_size_bytes > 0
    assert not report.issues


def test_health_check_warns_for_stale_rag_and_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = make_local_data_root(tmp_path)
    _configure_runtime(monkeypatch, root)
    build_local_data_manifest(root, workers=2, write=True)
    article_path = root / "corpus/pilot/article_store/articles.json"
    articles = json.loads(article_path.read_text(encoding="utf-8"))
    articles[0]["content"] += " changed"
    article_path.write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")

    report = check_local_system(root, workers=4, free_bytes=10_000_000)
    codes = {issue.issue_code for issue in report.issues}

    assert report.status == "WARN"
    assert "STALE_RAG_INDEX" in codes
    assert "STALE_KNOWLEDGE_GRAPH" in codes
    assert "STALE_MARKDOWN_LIBRARY" in codes
    assert all(issue.remediation_command for issue in report.issues)
    assert all(isinstance(issue.rebuildable, bool) for issue in report.issues)
    assert all(isinstance(issue.backup_required_first, bool) for issue in report.issues)


def test_health_check_blocks_corrupt_required_article_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = make_local_data_root(tmp_path)
    _configure_runtime(monkeypatch, root)
    build_local_data_manifest(root, write=True)
    (root / "corpus/pilot/article_store/articles.json").write_text("not-json", encoding="utf-8")

    report = check_local_system(root, free_bytes=10_000_000)

    assert report.status == "BLOCKED"
    assert "ARTICLE_STORE_CORRUPT" in {issue.issue_code for issue in report.issues}


def test_health_check_warns_for_corrupt_derived_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = make_local_data_root(tmp_path)
    _configure_runtime(monkeypatch, root)
    build_local_data_manifest(root, write=True)
    (root / "graph/full_corpus/graph.json").write_text("changed", encoding="utf-8")

    report = check_local_system(root, free_bytes=10_000_000)

    assert report.status == "WARN"
    assert "CORRUPT_KNOWLEDGE_GRAPH" in {issue.issue_code for issue in report.issues}


def test_health_check_warns_when_markdown_content_fingerprint_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = make_local_data_root(tmp_path)
    _configure_runtime(monkeypatch, root)
    build_local_data_manifest(root, workers=2, write=True)
    (root / "corpus/local_library/articles/1.md").write_text("corrupt", encoding="utf-8")

    report = check_local_system(root, workers=2, free_bytes=10_000_000)

    assert report.status == "WARN"
    assert "CORRUPT_MARKDOWN_LIBRARY" in {issue.issue_code for issue in report.issues}


def test_health_check_blocks_corrupt_tutor_session_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = make_local_data_root(tmp_path)
    _configure_runtime(monkeypatch, root)
    build_local_data_manifest(root, write=True)
    (root / "tutor_sessions.json").write_text("not-json", encoding="utf-8")

    report = check_local_system(root, free_bytes=10_000_000)

    assert report.status == "BLOCKED"
    assert "TUTOR_SESSION_STORE_CORRUPT" in {issue.issue_code for issue in report.issues}


def test_capacity_warns_when_free_space_is_below_two_times_data_size(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)

    capacity = audit_storage_capacity(root, free_bytes=1)

    assert capacity.status == "WARN"
    assert capacity.complete_backup_estimated_bytes >= capacity.essential_backup_estimated_bytes
    assert "LOW_DISK_SPACE" in capacity.issue_codes
    assert "COMPLETE_BACKUP_SPACE_INSUFFICIENT" in capacity.issue_codes
    assert "RESTORE_SPACE_INSUFFICIENT" in capacity.issue_codes
