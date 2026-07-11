from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from app.operations.models import CleanupResult

VALID_CATEGORIES = {
    "temp",
    "logs",
    "browser-cache",
    "evaluation-output",
    "stale-derived",
    "all-derived",
}

TIER_ONE_PATHS = (
    Path("corpus/pilot/article_store/articles.json"),
    Path("corpus/pilot/completion_classifications.json"),
    Path("corpus/pilot/progress.json"),
    Path("articles.json"),
    Path("learning.json"),
    Path("scientific_spaces.db"),
    Path("zotero_links.json"),
    Path("tutor_sessions.json"),
)

DERIVED_PATHS = (
    Path("corpus/local_library"),
    Path("corpus/pdf_library"),
    Path("rag/full_corpus"),
    Path("graph/full_corpus"),
    Path("evaluation"),
    Path("corpus/inventory"),
)


class CleanupSafetyError(RuntimeError):
    pass


def cleanup_local_data(
    data_root: Path | str,
    *,
    categories: Iterable[str],
    execute: bool = False,
    confirm_derived_delete: bool = False,
) -> CleanupResult:
    root = Path(data_root).expanduser().resolve()
    normalized = tuple(dict.fromkeys(category.strip().lower() for category in categories))
    if not normalized:
        raise CleanupSafetyError("at least one cleanup category is required")
    unknown = sorted(set(normalized) - VALID_CATEGORIES)
    if unknown:
        raise CleanupSafetyError("unknown or unsafe cleanup category: " + ", ".join(unknown))
    if "all-derived" in normalized and execute and not confirm_derived_delete:
        raise CleanupSafetyError("all-derived deletion requires --confirm-derived-delete")
    if not root.is_dir():
        raise CleanupSafetyError(f"data root does not exist: {root}")

    candidates: set[Path] = set()
    for category in normalized:
        candidates.update(_candidates_for_category(root, category))
    safe_candidates = tuple(sorted(_compact_paths(root, candidates), key=lambda path: path.as_posix()))
    for path in safe_candidates:
        _assert_safe_candidate(root, path)
    reclaimed = sum(_path_size(path) for path in safe_candidates)
    deleted: list[Path] = []
    if execute:
        for path in sorted(safe_candidates, key=lambda item: len(item.parts), reverse=True):
            if not path.exists() and not path.is_symlink():
                continue
            if path.is_symlink() or path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
            deleted.append(path)
    return CleanupResult(
        status="PASS",
        dry_run=not execute,
        categories=normalized,
        candidate_paths=safe_candidates,
        deleted_paths=tuple(sorted(deleted, key=lambda path: path.as_posix())),
        reclaimed_bytes=reclaimed,
    )


def _candidates_for_category(root: Path, category: str) -> set[Path]:
    if category == "all-derived":
        return {root / relative for relative in DERIVED_PATHS if (root / relative).exists()}
    if category == "evaluation-output":
        path = root / "evaluation"
        return {path} if path.exists() else set()
    if category == "stale-derived":
        return _stale_derived_paths(root)

    candidates: set[Path] = set()
    for path in root.rglob("*"):
        relative_parts = {part.lower() for part in path.relative_to(root).parts}
        name = path.name.lower()
        if category == "logs" and ("logs" in relative_parts or name.endswith(".log")) and path.is_file():
            candidates.add(path)
        elif category == "browser-cache" and (
            relative_parts & {"cache", "browser_profiles", "playwright-report", "test-results", "traces"}
        ) and path.is_file():
            candidates.add(path)
        elif category == "temp" and (
            name.endswith((".tmp", ".partial", ".trace", ".prof"))
            or name.startswith((".staging-", ".restore-", ".backup-"))
            or relative_parts & {"tmp", "temp"}
        ):
            candidates.add(path)
    return candidates


def _stale_derived_paths(root: Path) -> set[Path]:
    from app.operations.health import check_local_system

    report = check_local_system(root)
    code_to_path = {
        "STALE_MARKDOWN_LIBRARY": root / "corpus/local_library",
        "STALE_PDF_LIBRARY": root / "corpus/pdf_library",
        "STALE_RAG_INDEX": root / "rag/full_corpus",
        "STALE_KNOWLEDGE_GRAPH": root / "graph/full_corpus",
    }
    return {
        code_to_path[issue.issue_code]
        for issue in report.issues
        if issue.issue_code in code_to_path and code_to_path[issue.issue_code].exists()
    }


def _compact_paths(root: Path, paths: set[Path]) -> set[Path]:
    resolved = {path.resolve() for path in paths if path.exists() or path.is_symlink()}
    return {
        path
        for path in resolved
        if path != root and not any(parent in resolved for parent in path.parents if parent != root.parent)
    }


def _assert_safe_candidate(root: Path, candidate: Path) -> None:
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise CleanupSafetyError(f"cleanup candidate escapes data root: {candidate}") from exc
    if candidate == root or relative == Path("."):
        raise CleanupSafetyError("the complete local data root can never be deleted")
    for protected in TIER_ONE_PATHS:
        if relative == protected or relative in protected.parents or protected in relative.parents:
            raise CleanupSafetyError(f"Tier 1 asset is protected from cleanup: {relative}")


def _path_size(path: Path) -> int:
    if path.is_symlink():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink())
