from __future__ import annotations

import hashlib
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable

from app.operations.inventory import (
    DEFAULT_MANIFEST_RELATIVE_PATH,
    DEFAULT_WORKERS,
    directory_fingerprint,
    load_local_data_manifest,
    normalize_workers,
    path_size,
)
from app.operations.models import CapacityReport, HealthIssue, HealthReport
from app.rag.full_corpus import compute_corpus_fingerprint, load_full_corpus_articles


def audit_storage_capacity(
    data_root: Path | str,
    *,
    free_bytes: int | None = None,
) -> CapacityReport:
    root = Path(data_root).expanduser().resolve()
    sizes = {
        "article": path_size(root / "corpus/pilot/article_store/articles.json"),
        "markdown": path_size(root / "corpus/local_library"),
        "pdf": path_size(root / "corpus/pdf_library"),
        "rag": path_size(root / "rag/full_corpus"),
        "graph": path_size(root / "graph/full_corpus"),
    }
    total = path_size(root)
    logs_temp = _logs_temp_size(root)
    essential_paths = (
        "corpus/pilot/article_store/articles.json",
        "corpus/pilot/completion_classifications.json",
        "corpus/pilot/progress.json",
        "articles.json",
        "learning.json",
        "scientific_spaces.db",
        "zotero_links.json",
        "tutor_sessions.json",
    )
    essential = sum(path_size(root / relative) for relative in essential_paths)
    complete = max(essential + sizes["markdown"] + sizes["pdf"] + sizes["rag"] + sizes["graph"] + path_size(root / "evaluation") + path_size(root / "corpus/inventory"), total - logs_temp)
    available = int(free_bytes) if free_bytes is not None else int(shutil.disk_usage(root).free)
    issue_codes: list[str] = []
    if available < total * 2:
        issue_codes.append("LOW_DISK_SPACE")
    if available < complete:
        issue_codes.append("COMPLETE_BACKUP_SPACE_INSUFFICIENT")
    if sizes["pdf"] and available < sizes["pdf"]:
        issue_codes.append("PDF_REBUILD_SPACE_INSUFFICIENT")
    if available < total:
        issue_codes.append("RESTORE_SPACE_INSUFFICIENT")
    return CapacityReport(
        status="WARN" if issue_codes else "PASS",
        article_store_size_bytes=sizes["article"],
        markdown_size_bytes=sizes["markdown"],
        pdf_size_bytes=sizes["pdf"],
        rag_size_bytes=sizes["rag"],
        graph_size_bytes=sizes["graph"],
        logs_temp_size_bytes=logs_temp,
        total_size_bytes=total,
        essential_backup_estimated_bytes=essential,
        complete_backup_estimated_bytes=complete,
        free_bytes=available,
        issue_codes=tuple(issue_codes),
    )


def check_local_system(
    data_root: Path | str,
    *,
    manifest_path: Path | str | None = None,
    workers: int = DEFAULT_WORKERS,
    free_bytes: int | None = None,
) -> HealthReport:
    root = Path(data_root).expanduser().resolve()
    worker_count = normalize_workers(workers)
    issues: list[HealthIssue] = []
    checks: dict[str, str] = {}
    article_count = 0
    corpus_fingerprint: str | None = None
    article_path = root / "corpus/pilot/article_store/articles.json"
    try:
        articles = load_full_corpus_articles(article_path)
        article_count = len(articles)
        corpus_fingerprint = compute_corpus_fingerprint(articles)
        checks["article_store"] = "PASS"
    except Exception as exc:
        articles = []
        checks["article_store"] = "BLOCKED"
        issues.append(_health_issue("ARTICLE_STORE_CORRUPT", "article_store", "restore an essential backup", False, True, "BLOCKED", str(exc)))

    classification_path = root / "corpus/pilot/completion_classifications.json"
    if not _valid_json(classification_path):
        checks["classification_registry"] = "BLOCKED"
        issues.append(_health_issue("CLASSIFICATION_REGISTRY_MISSING_OR_CORRUPT", "classification_registry", "restore an essential backup", False, True, "BLOCKED"))
    else:
        checks["classification_registry"] = "PASS"

    saved_manifest_path = Path(manifest_path) if manifest_path else root / DEFAULT_MANIFEST_RELATIVE_PATH
    saved_assets: dict[str, Any] = {}
    try:
        saved_manifest = load_local_data_manifest(saved_manifest_path)
        saved_assets = {asset.asset_type: asset for asset in saved_manifest.assets}
        checks["unified_manifest"] = "PASS"
    except FileNotFoundError:
        checks["unified_manifest"] = "WARN"
        issues.append(_health_issue("UNIFIED_MANIFEST_MISSING", "unified_manifest", "uv run --project backend python scripts/ops/audit_local_data.py", True, False))
    except Exception as exc:
        checks["unified_manifest"] = "WARN"
        issues.append(_health_issue("UNIFIED_MANIFEST_CORRUPT", "unified_manifest", "uv run --project backend python scripts/ops/audit_local_data.py", True, False, detail=str(exc)))

    if corpus_fingerprint:
        _check_markdown(root, article_count, corpus_fingerprint, saved_assets, worker_count, checks, issues)
        _check_pdf(root, article_count, corpus_fingerprint, worker_count, checks, issues)
        _check_rag(root, corpus_fingerprint, worker_count, checks, issues)
        _check_graph(root, corpus_fingerprint, worker_count, checks, issues)
    _check_reader_configuration(root, article_path, checks, issues)
    _check_tutor_configuration(root, checks, issues)
    _check_user_persistence(root, checks, issues)

    capacity = audit_storage_capacity(root, free_bytes=free_bytes)
    checks["storage_capacity"] = capacity.status
    for code in capacity.issue_codes:
        issues.append(
            _health_issue(
                code,
                "storage_capacity",
                "free disk space or choose a larger external backup/restore target",
                False,
                True,
            )
        )
    ordered_issues = tuple(sorted(_deduplicate_issues(issues), key=lambda item: (item.severity, item.issue_code, item.affected_asset)))
    if any(issue.severity == "BLOCKED" for issue in ordered_issues):
        status = "BLOCKED"
    elif ordered_issues:
        status = "WARN"
    else:
        status = "PASS"
    return HealthReport(
        status=status,
        article_count=article_count,
        corpus_fingerprint=corpus_fingerprint,
        issues=ordered_issues,
        capacity=capacity,
        checks=checks,
    )


def _check_markdown(
    root: Path,
    article_count: int,
    corpus_fingerprint: str,
    saved_assets: dict[str, Any],
    workers: int,
    checks: dict[str, str],
    issues: list[HealthIssue],
) -> None:
    path = root / "corpus/local_library"
    markdown_count = len(list((path / "articles").glob("*.md"))) if path.is_dir() else 0
    saved = saved_assets.get("markdown_library")
    if not path.is_dir() or markdown_count != article_count:
        checks["markdown_library"] = "WARN"
        issues.append(_health_issue("MARKDOWN_LIBRARY_MISSING_OR_INCOMPLETE", "markdown_library", "uv run --project backend python scripts/corpus/materialize_local_library.py", True, False))
    elif saved is None or saved.source_fingerprint != corpus_fingerprint:
        checks["markdown_library"] = "WARN"
        issues.append(_health_issue("STALE_MARKDOWN_LIBRARY", "markdown_library", "uv run --project backend python scripts/corpus/materialize_local_library.py", True, False))
    elif saved.fingerprint and directory_fingerprint(path, workers=workers)[0] != saved.fingerprint:
        checks["markdown_library"] = "WARN"
        issues.append(_health_issue("CORRUPT_MARKDOWN_LIBRARY", "markdown_library", "uv run --project backend python scripts/corpus/materialize_local_library.py", True, False))
    else:
        checks["markdown_library"] = "PASS"


def _check_pdf(root: Path, article_count: int, corpus_fingerprint: str, workers: int, checks: dict[str, str], issues: list[HealthIssue]) -> None:
    library = root / "corpus/pdf_library"
    manifest_path = library / "manifest/pdf_manifest.json"
    manifest = _read_json(manifest_path)
    if not manifest:
        checks["pdf_library"] = "WARN"
        issues.append(_health_issue("PDF_LIBRARY_MISSING_OR_CORRUPT", "pdf_library", "uv run --project backend python scripts/export/export_local_corpus_pdfs.py", True, False))
        return
    if manifest.get("corpus_fingerprint") != corpus_fingerprint:
        checks["pdf_library"] = "WARN"
        issues.append(_health_issue("STALE_PDF_LIBRARY", "pdf_library", "uv run --project backend python scripts/export/export_local_corpus_pdfs.py", True, False))
        return
    records = manifest.get("records")
    if not isinstance(records, list) or len(records) != article_count:
        checks["pdf_library"] = "WARN"
        issues.append(_health_issue("PDF_LIBRARY_COUNT_MISMATCH", "pdf_library", "uv run --project backend python scripts/export/export_local_corpus_pdfs.py", True, False))
        return
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pdf-health") as executor:
        results = list(executor.map(lambda record: _validate_pdf_record(library, record), records))
    if not all(results):
        checks["pdf_library"] = "WARN"
        issues.append(_health_issue("CORRUPT_PDF_LIBRARY", "pdf_library", "uv run --project backend python scripts/export/export_local_corpus_pdfs.py", True, False))
    else:
        checks["pdf_library"] = "PASS"


def _check_rag(root: Path, corpus_fingerprint: str, workers: int, checks: dict[str, str], issues: list[HealthIssue]) -> None:
    index = root / "rag/full_corpus/index"
    manifest = _read_json(index / "manifest.json")
    if not manifest:
        checks["rag_index"] = "WARN"
        issues.append(_health_issue("RAG_INDEX_MISSING_OR_CORRUPT", "rag_index", "uv run --project backend python scripts/rag/build_full_corpus_index.py", True, False))
        return
    if manifest.get("corpus_fingerprint") != corpus_fingerprint:
        checks["rag_index"] = "WARN"
        issues.append(_health_issue("STALE_RAG_INDEX", "rag_index", "uv run --project backend python scripts/rag/build_full_corpus_index.py", True, False))
        return
    artifacts = [
        (index / str(manifest.get("index_file", "faiss.index")), manifest.get("index_file_size_bytes"), manifest.get("index_file_sha256")),
        (index / str(manifest.get("chunk_metadata_file", "chunks.jsonl")), manifest.get("chunk_metadata_size_bytes"), manifest.get("chunk_metadata_sha256")),
    ]
    with ThreadPoolExecutor(max_workers=min(workers, len(artifacts)), thread_name_prefix="rag-health") as executor:
        valid = list(executor.map(lambda item: _validate_file(*item), artifacts))
    if not all(valid):
        checks["rag_index"] = "WARN"
        issues.append(_health_issue("CORRUPT_RAG_INDEX", "rag_index", "uv run --project backend python scripts/rag/build_full_corpus_index.py", True, False))
    else:
        checks["rag_index"] = "PASS"


def _check_graph(root: Path, corpus_fingerprint: str, workers: int, checks: dict[str, str], issues: list[HealthIssue]) -> None:
    graph_root = root / "graph/full_corpus"
    manifest = _read_json(graph_root / "manifest.json")
    if not manifest:
        checks["knowledge_graph"] = "WARN"
        issues.append(_health_issue("KNOWLEDGE_GRAPH_MISSING_OR_CORRUPT", "knowledge_graph", "uv run --project backend python scripts/graph/build_full_corpus_graph.py", True, False))
        return
    if manifest.get("corpus_fingerprint") != corpus_fingerprint:
        checks["knowledge_graph"] = "WARN"
        issues.append(_health_issue("STALE_KNOWLEDGE_GRAPH", "knowledge_graph", "uv run --project backend python scripts/graph/build_full_corpus_graph.py", True, False))
        return
    graph_path = graph_root / str(manifest.get("graph_file", "graph.json"))
    if not _validate_file(graph_path, manifest.get("graph_file_size_bytes"), manifest.get("graph_file_sha256")):
        checks["knowledge_graph"] = "WARN"
        issues.append(_health_issue("CORRUPT_KNOWLEDGE_GRAPH", "knowledge_graph", "uv run --project backend python scripts/graph/build_full_corpus_graph.py", True, False))
    else:
        checks["knowledge_graph"] = "PASS"


def _check_reader_configuration(root: Path, article_path: Path, checks: dict[str, str], issues: list[HealthIssue]) -> None:
    configured = os.getenv("SCIENTIFIC_SPACES_ARTICLES_FILE") or os.getenv("SCIENTIFIC_SPACES_ARTICLE_STORE")
    if configured and Path(configured).expanduser().resolve() == article_path.resolve():
        checks["reader_configuration"] = "PASS"
    else:
        checks["reader_configuration"] = "WARN"
        issues.append(_health_issue("READER_ARTICLE_STORE_NOT_CONFIGURED", "reader_configuration", f"export SCIENTIFIC_SPACES_ARTICLE_STORE={article_path.relative_to(root.parent.parent).as_posix() if root.parent.parent in article_path.parents else article_path}", False, False))


def _check_tutor_configuration(root: Path, checks: dict[str, str], issues: list[HealthIssue]) -> None:
    expected_rag = (root / "rag/full_corpus").resolve()
    expected_graph = (root / "graph/full_corpus/graph.json").resolve()
    configured_rag = os.getenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR")
    configured_graph = os.getenv("SCIENTIFIC_SPACES_GRAPH_FILE")
    valid = bool(configured_rag and Path(configured_rag).expanduser().resolve() == expected_rag and configured_graph and Path(configured_graph).expanduser().resolve() == expected_graph)
    if valid:
        checks["tutor_configuration"] = "PASS"
    else:
        checks["tutor_configuration"] = "WARN"
        issues.append(_health_issue("TUTOR_FULL_CORPUS_NOT_CONFIGURED", "tutor_configuration", "set SCIENTIFIC_SPACES_RAG_INDEX_DIR and SCIENTIFIC_SPACES_GRAPH_FILE to the full-corpus artifacts", False, False))


def _check_user_persistence(root: Path, checks: dict[str, str], issues: list[HealthIssue]) -> None:
    learning_json = root / "learning.json"
    learning_db = root / "scientific_spaces.db"
    if learning_json.exists() and not _valid_json(learning_json):
        checks["learning_persistence"] = "BLOCKED"
        issues.append(_health_issue("LEARNING_STORE_CORRUPT", "learning_persistence", "restore an essential backup", False, True, "BLOCKED"))
    elif learning_db.exists() and not _valid_sqlite(learning_db):
        checks["learning_persistence"] = "BLOCKED"
        issues.append(_health_issue("LEARNING_DATABASE_CORRUPT", "learning_persistence", "restore an essential backup", False, True, "BLOCKED"))
    else:
        checks["learning_persistence"] = "PASS"
    zotero = root / "zotero_links.json"
    if zotero.exists() and not _valid_json(zotero):
        checks["zotero_links"] = "BLOCKED"
        issues.append(_health_issue("ZOTERO_LINKS_CORRUPT", "zotero_links", "restore an essential backup", False, True, "BLOCKED"))
    else:
        checks["zotero_links"] = "PASS"
    tutor_sessions = root / "tutor_sessions.json"
    if tutor_sessions.exists() and not _valid_json(tutor_sessions):
        checks["tutor_sessions"] = "BLOCKED"
        issues.append(_health_issue("TUTOR_SESSION_STORE_CORRUPT", "tutor_sessions", "restore an essential backup", False, True, "BLOCKED"))
    else:
        checks["tutor_sessions"] = "PASS"


def _validate_pdf_record(root: Path, record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    relative = record.get("output_relative_path")
    if not isinstance(relative, str) or ".." in Path(relative).parts or Path(relative).is_absolute():
        return False
    return _validate_file(root / relative, record.get("pdf_size_bytes"), record.get("pdf_sha256"))


def _validate_file(path: Path, expected_size: Any, expected_hash: Any) -> bool:
    if not path.is_file() or not isinstance(expected_size, int) or path.stat().st_size != expected_size or not isinstance(expected_hash, str):
        return False
    return _sha256(path) == expected_hash


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _valid_json(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except (OSError, json.JSONDecodeError):
        return False


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _valid_sqlite(path: Path) -> bool:
    import sqlite3

    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            return str(connection.execute("PRAGMA integrity_check").fetchone()[0]).lower() == "ok"
    except sqlite3.Error:
        return False


def _logs_temp_size(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        parts = {part.lower() for part in path.relative_to(root).parts}
        if parts & {"logs", "cache", "tmp", "temp", "traces", "browser_profiles"} or path.suffix.lower() in {".log", ".trace", ".prof", ".cache"}:
            total += path.stat().st_size
    return total


def _health_issue(
    code: str,
    asset: str,
    remediation: str,
    rebuildable: bool,
    backup_required: bool,
    severity: str = "WARN",
    detail: str = "",
) -> HealthIssue:
    return HealthIssue(
        issue_code=code,
        affected_asset=asset,
        remediation_command=remediation,
        rebuildable=rebuildable,
        backup_required_first=backup_required,
        severity=severity,
        detail=detail,
    )


def _deduplicate_issues(issues: Iterable[HealthIssue]) -> tuple[HealthIssue, ...]:
    unique: dict[tuple[str, str], HealthIssue] = {}
    for issue in issues:
        unique[(issue.issue_code, issue.affected_asset)] = issue
    return tuple(unique.values())
