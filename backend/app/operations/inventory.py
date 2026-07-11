from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from app.operations.models import AssetRecord, LocalDataManifest
from app.rag.full_corpus import compute_corpus_fingerprint, load_full_corpus_articles

MANIFEST_SCHEMA_VERSION = 1
DEFAULT_WORKERS = 4
MAX_WORKERS = 16
DEFAULT_MANIFEST_RELATIVE_PATH = Path("operations/local_data_manifest.json")


@dataclass(frozen=True)
class AssetSpec:
    asset_type: str
    relative_path: str
    tier: str
    schema_version: str
    rebuild_command: str | None
    required_for_restore: bool
    contains_user_data: bool
    backup_priority: int
    count_strategy: str = "files"


ASSET_SPECS: tuple[AssetSpec, ...] = (
    AssetSpec("article_store", "corpus/pilot/article_store/articles.json", "Tier 1", "article-store-v1", None, True, False, 1, "articles"),
    AssetSpec("classification_registry", "corpus/pilot/completion_classifications.json", "Tier 1", "classification-registry-v1", None, True, False, 2, "classifications"),
    AssetSpec("corpus_progress", "corpus/pilot/progress.json", "Tier 1", "corpus-progress-v1", None, False, False, 3, "json-root"),
    AssetSpec("legacy_article_store", "articles.json", "Tier 1", "article-store-v1", None, False, False, 4, "articles"),
    AssetSpec("learning_json", "learning.json", "Tier 1", "learning-json-v1", None, False, True, 1, "learning"),
    AssetSpec("learning_sqlite", "scientific_spaces.db", "Tier 1", "learning-sqlite-v1", None, False, True, 1, "sqlite-learning"),
    AssetSpec("zotero_links", "zotero_links.json", "Tier 1", "zotero-links-v1", None, False, True, 1, "zotero"),
    AssetSpec("tutor_sessions", "tutor_sessions.json", "Tier 1", "tutor-sessions-v1", None, False, True, 2, "json-root"),
    AssetSpec("markdown_library", "corpus/local_library", "Tier 2", "local-markdown-v1", "uv run --project backend python scripts/corpus/materialize_local_library.py", False, False, 20, "markdown"),
    AssetSpec("pdf_library", "corpus/pdf_library", "Tier 2", "local-pdf-v5", "uv run --project backend python scripts/export/export_local_corpus_pdfs.py", False, False, 30, "pdf"),
    AssetSpec("rag_index", "rag/full_corpus", "Tier 2", "full-corpus-rag-v2", "uv run --project backend python scripts/rag/build_full_corpus_index.py", False, False, 20, "rag"),
    AssetSpec("knowledge_graph", "graph/full_corpus", "Tier 2", "full-corpus-graph-v1", "uv run --project backend python scripts/graph/build_full_corpus_graph.py", False, False, 20, "graph"),
    AssetSpec("evaluation_outputs", "evaluation", "Tier 2", "evaluation-output-v1", None, False, False, 40, "files"),
    AssetSpec("corpus_inventory", "corpus/inventory", "Tier 2", "corpus-inventory-v1", None, False, False, 40, "files"),
    AssetSpec("corpus_validation", "corpus/pilot/validation_summary.json", "Tier 2", "corpus-validation-v1", None, False, False, 40, "json-root"),
    AssetSpec("corpus_failures", "corpus/pilot/failed_urls.jsonl", "Tier 2", "corpus-failures-v1", None, False, False, 40, "jsonl"),
    AssetSpec("runtime_cache", "cache", "Tier 3", "runtime-cache-v1", None, False, False, 99, "files"),
    AssetSpec("browser_profiles", "browser_profiles", "Tier 3", "browser-profile-v1", None, False, True, 99, "files"),
    AssetSpec("runtime_traces", "traces", "Tier 3", "runtime-trace-v1", None, False, True, 99, "files"),
)

SECRET_NAMES = {".env", "credentials", "credentials.json", "secrets.json"}


def normalize_workers(workers: int) -> int:
    if workers < 1 or workers > MAX_WORKERS:
        raise ValueError(f"workers must be between 1 and {MAX_WORKERS}")
    return workers


def build_local_data_manifest(
    data_root: Path | str,
    *,
    manifest_path: Path | str | None = None,
    workers: int = DEFAULT_WORKERS,
    write: bool = True,
) -> LocalDataManifest:
    root = Path(data_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Local data root does not exist: {root}")
    worker_count = normalize_workers(workers)
    target = Path(manifest_path) if manifest_path else root / DEFAULT_MANIFEST_RELATIVE_PATH
    if not target.is_absolute():
        target = target.resolve()

    specs = (*ASSET_SPECS, *_extra_asset_specs(root))
    article_fingerprint = _article_fingerprint(root / ASSET_SPECS[0].relative_path)

    def inspect(spec: AssetSpec) -> AssetRecord:
        return _inspect_asset(root, spec, article_fingerprint=article_fingerprint, workers=worker_count)

    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="asset-inventory") as executor:
        assets = tuple(sorted(executor.map(inspect, specs), key=lambda item: (item.backup_priority, item.asset_type, item.relative_path)))
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "assets": [asset.to_dict() for asset in assets],
    }
    deterministic_fingerprint = _json_fingerprint(payload)
    manifest = LocalDataManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        generated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        deterministic_fingerprint=deterministic_fingerprint,
        assets=assets,
        manifest_path=str(target),
    )
    if write:
        _write_json_atomic(target, manifest.to_dict())
    return manifest


def load_local_data_manifest(path: Path | str) -> LocalDataManifest:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = tuple(AssetRecord.from_dict(item) for item in payload.get("assets", []))
    manifest = LocalDataManifest(
        schema_version=int(payload["schema_version"]),
        generated_at=str(payload.get("generated_at") or ""),
        deterministic_fingerprint=str(payload["deterministic_fingerprint"]),
        assets=assets,
        manifest_path=str(manifest_path),
    )
    if _json_fingerprint(manifest.fingerprint_payload()) != manifest.deterministic_fingerprint:
        raise ValueError("Local data manifest fingerprint is invalid")
    return manifest


def files_for_path(path: Path, *, include_tier3: bool = True) -> list[Path]:
    if not path.exists() and not path.is_symlink():
        return []
    if path.is_symlink():
        raise ValueError(f"symlink is not allowed in local data assets: {path}")
    if path.is_file():
        return [] if _is_secret_path(path) else [path]
    files: list[Path] = []
    for directory, dirnames, filenames in os.walk(path, followlinks=False):
        current = Path(directory)
        for name in tuple(dirnames):
            child = current / name
            if child.is_symlink():
                raise ValueError(f"symlink is not allowed in local data assets: {child}")
            if not include_tier3 and _is_tier3_path(child):
                dirnames.remove(name)
        for name in filenames:
            child = current / name
            if child.is_symlink():
                raise ValueError(f"symlink is not allowed in local data assets: {child}")
            if _is_secret_path(child) or (not include_tier3 and _is_tier3_path(child)):
                continue
            files.append(child)
    return sorted(files)


def path_size(path: Path) -> int:
    try:
        return sum(item.stat().st_size for item in files_for_path(path))
    except (FileNotFoundError, ValueError):
        return 0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_fingerprint(path: Path, *, workers: int = DEFAULT_WORKERS) -> tuple[str | None, int, int]:
    files = files_for_path(path)
    if not files:
        return (None, 0, 0)
    worker_count = normalize_workers(workers)
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="asset-hash") as executor:
        hashes = list(executor.map(file_sha256, files))
    records = [
        {"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "size_bytes": item.stat().st_size, "sha256": digest}
        for item, digest in zip(files, hashes, strict=True)
    ]
    return (_json_fingerprint(records), sum(record["size_bytes"] for record in records), len(records))


def _inspect_asset(root: Path, spec: AssetSpec, *, article_fingerprint: str | None, workers: int) -> AssetRecord:
    path = root / spec.relative_path
    exists = path.exists() and not path.is_symlink()
    fingerprint: str | None = None
    size_bytes = 0
    file_count = 0
    record_count: int | None = None
    if exists:
        if spec.asset_type in {"article_store", "legacy_article_store"}:
            fingerprint = _article_fingerprint(path)
            size_bytes = path.stat().st_size
            file_count = 1
        else:
            fingerprint, size_bytes, file_count = directory_fingerprint(path, workers=workers)
        record_count = _record_count(path, spec.count_strategy)
    source_fingerprint = _source_fingerprint(path, spec, article_fingerprint)
    return AssetRecord(
        asset_type=spec.asset_type,
        relative_path=spec.relative_path,
        tier=spec.tier,
        size_bytes=size_bytes,
        record_count=record_count,
        fingerprint=fingerprint,
        source_fingerprint=source_fingerprint,
        schema_version=spec.schema_version,
        rebuild_command=spec.rebuild_command,
        required_for_restore=spec.required_for_restore,
        contains_user_data=spec.contains_user_data,
        backup_priority=spec.backup_priority,
        exists=exists,
        file_count=file_count,
    )


def _article_fingerprint(path: Path) -> str | None:
    if not path.is_file():
        return None
    articles = load_full_corpus_articles(path)
    return compute_corpus_fingerprint(articles)


def _source_fingerprint(path: Path, spec: AssetSpec, article_fingerprint: str | None) -> str | None:
    if not path.exists():
        return None
    if spec.asset_type in {"article_store", "legacy_article_store", "markdown_library"}:
        return article_fingerprint
    manifest_candidates = {
        "pdf_library": path / "manifest/pdf_manifest.json",
        "rag_index": path / "index/manifest.json",
        "knowledge_graph": path / "manifest.json",
    }
    manifest_path = manifest_candidates.get(spec.asset_type)
    if manifest_path and manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        value = payload.get("corpus_fingerprint")
        return str(value) if value else None
    return None


def _record_count(path: Path, strategy: str) -> int:
    if strategy == "files":
        return len(files_for_path(path))
    if strategy == "markdown":
        return len(list((path / "articles").glob("*.md")))
    if strategy == "pdf":
        return len(list((path / "articles").glob("*.pdf")))
    if strategy == "jsonl":
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    if strategy == "sqlite-learning":
        return _sqlite_learning_count(path)
    if strategy == "rag":
        manifest = _read_json(path / "index/manifest.json")
        return int(manifest.get("chunk_count", 0))
    if strategy == "graph":
        manifest = _read_json(path / "manifest.json")
        return int(manifest.get("node_count", 0)) + int(manifest.get("edge_count", 0))
    payload = json.loads(path.read_text(encoding="utf-8"))
    if strategy == "articles":
        return len(payload) if isinstance(payload, list) else 0
    if strategy == "classifications":
        values = payload.get("classifications", {}) if isinstance(payload, dict) else {}
        return len(values) if isinstance(values, (dict, list)) else 0
    if strategy == "learning":
        if not isinstance(payload, dict):
            return 0
        return sum(len(payload.get(key, {})) for key in ("states", "bookmarks", "notes", "sessions") if isinstance(payload.get(key, {}), (dict, list)))
    if strategy == "zotero":
        if not isinstance(payload, dict):
            return 0
        return sum(len(value) for value in payload.values() if isinstance(value, dict))
    if strategy == "json-root":
        return len(payload) if isinstance(payload, (dict, list)) else 0
    return 0


def _sqlite_learning_count(path: Path) -> int:
    total = 0
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ("learning_state", "bookmarks", "notes", "sessions"):
            if table in tables:
                total += int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    return total


def _extra_asset_specs(root: Path) -> tuple[AssetSpec, ...]:
    known = tuple((root / spec.relative_path).resolve() for spec in ASSET_SPECS)
    extras: list[AssetSpec] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() and not path.is_symlink():
            continue
        relative = path.relative_to(root)
        if relative == DEFAULT_MANIFEST_RELATIVE_PATH or _is_secret_path(path):
            continue
        resolved = path.resolve()
        if any(resolved == item or item in resolved.parents for item in known):
            continue
        is_legacy_probe = (
            len(relative.parts) >= 2
            and relative.parts[0] == "corpus"
            and relative.parts[1].startswith("p1_")
        )
        tier = "Tier 3" if _is_tier3_path(path) else "Tier 2" if is_legacy_probe else "Tier 1"
        prefix = "legacy_corpus_run" if is_legacy_probe else "unclassified_local_data"
        extras.append(
            AssetSpec(
                asset_type=f"{prefix}:{relative.as_posix()}",
                relative_path=relative.as_posix(),
                tier=tier,
                schema_version="unclassified-v1",
                rebuild_command=None,
                required_for_restore=False,
                contains_user_data=tier == "Tier 1",
                backup_priority=10 if tier == "Tier 1" else 40 if tier == "Tier 2" else 99,
                count_strategy="files",
            )
        )
    return tuple(extras)


def _is_secret_path(path: Path) -> bool:
    lowered = path.name.lower()
    return lowered in SECRET_NAMES or lowered.startswith(".env.") or lowered.endswith(".pem") or lowered.endswith(".key")


def _is_tier3_path(path: Path) -> bool:
    # Only inspect the local asset tail. A data root may itself live under
    # /tmp during an isolated restore or fixture test.
    parts = {part.lower() for part in path.parts[-6:]}
    name = path.name.lower()
    return bool(parts & {"cache", "browser_profiles", "playwright-report", "test-results", "traces", "logs", "tmp", "temp"}) or name.endswith((".log", ".trace", ".prof", ".partial")) or ".staging-" in name


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _json_fingerprint(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
