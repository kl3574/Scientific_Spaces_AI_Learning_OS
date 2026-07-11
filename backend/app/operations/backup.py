from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from app.operations.inventory import (
    DEFAULT_WORKERS,
    build_local_data_manifest,
    files_for_path,
    normalize_workers,
)
from app.operations.models import (
    AssetRecord,
    BackupResult,
    BackupVerificationResult,
    OperationIssue,
)

BACKUP_SCHEMA_VERSION = 1
BACKUP_MANIFEST_NAME = "backup_manifest.json"
DATA_PREFIX = "data/"
VALID_PROFILES = {"essential", "complete"}


class BackupSafetyError(RuntimeError):
    pass


def create_backup(
    data_root: Path | str,
    output_dir: Path | str,
    *,
    profile: str = "essential",
    include_pdf: bool = False,
    workers: int = DEFAULT_WORKERS,
    verify: bool = False,
) -> BackupResult:
    root = Path(data_root).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    worker_count = normalize_workers(workers)
    normalized_profile = profile.strip().lower()
    if normalized_profile not in VALID_PROFILES:
        raise BackupSafetyError(f"Unknown backup profile: {profile}")
    if normalized_profile == "essential" and include_pdf:
        raise BackupSafetyError("essential backup cannot include the PDF library")
    if _is_relative_to(destination, root):
        raise BackupSafetyError("backup output must be outside the source data root")
    if not root.is_dir():
        raise BackupSafetyError(f"source data root does not exist: {root}")
    _assert_no_symlinks(root)

    manifest = build_local_data_manifest(root, workers=worker_count, write=True)
    required_missing = [
        asset.asset_type for asset in manifest.assets if asset.required_for_restore and not asset.exists
    ]
    if required_missing:
        raise BackupSafetyError("required source assets are missing: " + ", ".join(required_missing))
    selected = _select_assets(manifest.assets, normalized_profile, include_pdf=include_pdf)
    file_selections = _select_files(root, selected)

    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"scientific-spaces-{normalized_profile}-{timestamp}-{manifest.deterministic_fingerprint[:12]}.zip"
    final_path = destination / filename
    if final_path.exists():
        final_path = destination / f"{final_path.stem}-{uuid.uuid4().hex[:8]}.zip"
    partial_path = final_path.with_suffix(final_path.suffix + ".partial")
    verification: BackupVerificationResult | None = None
    try:
        file_records: list[dict[str, Any]] = []
        with zipfile.ZipFile(partial_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for asset, source in file_selections:
                relative = source.relative_to(root).as_posix()
                archive_path = f"{DATA_PREFIX}{relative}"
                size_bytes, sha256 = _stream_file_to_zip(archive, source, archive_path)
                file_records.append(
                    {
                        "asset_type": asset.asset_type,
                        "relative_path": relative,
                        "archive_path": archive_path,
                        "size_bytes": size_bytes,
                        "sha256": sha256,
                    }
                )
            asset_records = _backup_asset_records(selected, file_records)
            backup_manifest = {
                "schema_version": BACKUP_SCHEMA_VERSION,
                "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "profile": normalized_profile,
                "pdf_included": include_pdf,
                "source_manifest_fingerprint": manifest.deterministic_fingerprint,
                "asset_records": asset_records,
                "required_files": sorted(
                    record["archive_path"]
                    for record in file_records
                    if any(
                        asset.asset_type == record["asset_type"] and asset.required_for_restore
                        for asset in selected
                    )
                ),
                "files": sorted(file_records, key=lambda item: item["relative_path"]),
            }
            _write_manifest_to_zip(archive, backup_manifest)
        os.chmod(partial_path, 0o600)
        if verify:
            verification = verify_backup(partial_path, workers=worker_count)
            if verification.status != "PASS":
                raise BackupSafetyError(
                    "new backup failed verification: " + ", ".join(verification.issue_codes)
                )
        os.replace(partial_path, final_path)
        os.chmod(final_path, 0o600)
        if verification is not None:
            verification = replace(verification, archive_path=final_path)
    except Exception:
        partial_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise

    asset_fingerprints = {
        asset.asset_type: asset.fingerprint
        for asset in selected
        if asset.fingerprint is not None
    }
    return BackupResult(
        status="PASS" if verify else "CONDITIONAL",
        archive_path=final_path,
        profile=normalized_profile,
        pdf_included=include_pdf,
        file_count=len(file_selections),
        source_manifest_fingerprint=manifest.deterministic_fingerprint,
        asset_fingerprints=asset_fingerprints,
        verification=verification,
    )


def verify_backup(
    archive_path: Path | str,
    *,
    workers: int = DEFAULT_WORKERS,
) -> BackupVerificationResult:
    path = Path(archive_path).expanduser().resolve()
    worker_count = normalize_workers(workers)
    issues: list[OperationIssue] = []
    profile: str | None = None
    pdf_included: bool | None = None
    file_count = 0
    asset_fingerprints: dict[str, str] = {}
    asset_record_counts: dict[str, int | None] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                issues.append(_issue("DUPLICATE_ARCHIVE_ENTRY", "archive contains duplicate paths"))
            for info in infos:
                if not _safe_archive_name(info.filename):
                    issues.append(_issue("UNSAFE_ARCHIVE_PATH", f"unsafe archive path: {info.filename}"))
                if _zip_info_is_symlink(info):
                    issues.append(_issue("SYMLINK_ENTRY", f"symlink archive entry: {info.filename}"))
            if BACKUP_MANIFEST_NAME not in names:
                issues.append(_issue("MISSING_BACKUP_MANIFEST", "backup manifest is missing"))
                return _verification_result(path, None, None, 0, issues, {}, {})
            try:
                manifest = json.loads(archive.read(BACKUP_MANIFEST_NAME).decode("utf-8"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                issues.append(_issue("INVALID_BACKUP_MANIFEST", str(exc)))
                return _verification_result(path, None, None, 0, issues, {}, {})
    except (OSError, zipfile.BadZipFile, EOFError) as exc:
        return _verification_result(
            path,
            None,
            None,
            0,
            [_issue("CORRUPT_ARCHIVE", str(exc))],
            {},
            {},
        )

    profile = str(manifest.get("profile") or "") or None
    pdf_included = bool(manifest.get("pdf_included"))
    file_records = manifest.get("files")
    asset_records = manifest.get("asset_records")
    if manifest.get("schema_version") != BACKUP_SCHEMA_VERSION or not isinstance(file_records, list) or not isinstance(asset_records, list):
        issues.append(_issue("INVALID_BACKUP_MANIFEST", "unsupported schema or invalid record lists"))
        return _verification_result(path, profile, pdf_included, 0, issues, {}, {})
    file_count = len(file_records)
    names_set = set(names)
    required_files = manifest.get("required_files", [])
    if not isinstance(required_files, list):
        issues.append(_issue("INVALID_BACKUP_MANIFEST", "required_files must be a list"))
        required_files = []
    for required in required_files:
        if required not in names_set:
            issues.append(_issue("MISSING_REQUIRED_FILE", f"required file is missing: {required}"))
    expected_names = {BACKUP_MANIFEST_NAME}
    for record in file_records:
        if not isinstance(record, dict):
            issues.append(_issue("INVALID_FILE_RECORD", "backup file record is not an object"))
            continue
        archive_name = str(record.get("archive_path") or "")
        relative_name = str(record.get("relative_path") or "")
        expected_names.add(archive_name)
        if not _safe_archive_name(relative_name):
            issues.append(_issue("UNSAFE_MANIFEST_PATH", f"unsafe manifest path: {relative_name}"))
        elif archive_name != f"{DATA_PREFIX}{relative_name}":
            issues.append(_issue("MANIFEST_PATH_MISMATCH", f"archive and restore paths differ: {archive_name}"))
        if archive_name not in names_set:
            code = "MISSING_REQUIRED_FILE" if archive_name in required_files else "MISSING_ARCHIVE_FILE"
            issues.append(_issue(code, f"manifest file is missing: {archive_name}"))
    for name in sorted(names_set - expected_names):
        issues.append(_issue("UNMANIFESTED_ARCHIVE_FILE", f"archive file is not in manifest: {name}"))

    valid_records = [record for record in file_records if isinstance(record, dict) and str(record.get("archive_path") or "") in names_set]
    hash_results = _hash_archive_records(path, valid_records, workers=worker_count)
    for record in valid_records:
        result = hash_results[str(record.get("archive_path") or "")]
        if isinstance(result, Exception):
            issues.append(_issue("CORRUPT_ARCHIVE", f"{record.get('archive_path')}: {result}"))
            continue
        actual_size, actual_hash = result
        if actual_size != record.get("size_bytes"):
            issues.append(_issue("SIZE_MISMATCH", f"size mismatch: {record.get('archive_path')}"))
        if actual_hash != record.get("sha256"):
            issues.append(_issue("HASH_MISMATCH", f"hash mismatch: {record.get('archive_path')}"))

    by_asset: dict[str, list[dict[str, Any]]] = {}
    for record in valid_records:
        by_asset.setdefault(str(record.get("asset_type") or ""), []).append(record)
    for asset in asset_records:
        if not isinstance(asset, dict):
            issues.append(_issue("INVALID_ASSET_RECORD", "backup asset record is not an object"))
            continue
        asset_type = str(asset.get("asset_type") or "")
        asset_relative_path = str(asset.get("relative_path") or "")
        if not _safe_archive_name(asset_relative_path):
            issues.append(_issue("UNSAFE_MANIFEST_PATH", f"unsafe asset path: {asset_relative_path}"))
        fingerprint = asset.get("fingerprint")
        if isinstance(fingerprint, str):
            asset_fingerprints[asset_type] = fingerprint
        expected_count = asset.get("record_count")
        actual_count = _archive_asset_record_count(path, asset_type, by_asset.get(asset_type, []))
        asset_record_counts[asset_type] = actual_count
        if expected_count is not None and actual_count is not None and int(expected_count) != actual_count:
            issues.append(_issue("RECORD_COUNT_MISMATCH", f"record count mismatch: {asset_type}"))
        expected_file_count = int(asset.get("backup_file_count", -1))
        if expected_file_count != len(by_asset.get(asset_type, [])):
            issues.append(_issue("FILE_COUNT_MISMATCH", f"file count mismatch: {asset_type}"))
        expected_backup_fingerprint = asset.get("backup_fingerprint")
        actual_backup_fingerprint = _file_record_fingerprint(by_asset.get(asset_type, []))
        if expected_backup_fingerprint != actual_backup_fingerprint:
            issues.append(_issue("ASSET_FINGERPRINT_MISMATCH", f"asset file fingerprint mismatch: {asset_type}"))

    _verify_profile(profile, pdf_included, asset_records, issues)
    selected_types = {str(item.get("asset_type") or "") for item in asset_records if isinstance(item, dict)}
    for required_type in ("article_store", "classification_registry"):
        if required_type not in selected_types:
            issues.append(_issue("MISSING_REQUIRED_ASSET", f"required asset is missing: {required_type}"))
    return _verification_result(path, profile, pdf_included, file_count, issues, asset_fingerprints, asset_record_counts)


def read_backup_manifest(archive_path: Path | str) -> dict[str, Any]:
    with zipfile.ZipFile(archive_path) as archive:
        return json.loads(archive.read(BACKUP_MANIFEST_NAME).decode("utf-8"))


def _select_assets(assets: tuple[AssetRecord, ...], profile: str, *, include_pdf: bool) -> tuple[AssetRecord, ...]:
    allowed_tiers = {"Tier 1"} if profile == "essential" else {"Tier 1", "Tier 2"}
    return tuple(
        asset
        for asset in assets
        if asset.exists
        and asset.tier in allowed_tiers
        and (asset.asset_type != "pdf_library" or include_pdf)
    )


def _select_files(root: Path, assets: tuple[AssetRecord, ...]) -> list[tuple[AssetRecord, Path]]:
    selected: list[tuple[AssetRecord, Path]] = []
    seen: set[Path] = set()
    for asset in assets:
        for path in files_for_path(root / asset.relative_path, include_tier3=False):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            selected.append((asset, path))
    return sorted(selected, key=lambda item: item[1].relative_to(root).as_posix())


def _backup_asset_records(assets: tuple[AssetRecord, ...], files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for asset in assets:
        asset_files = [record for record in files if record["asset_type"] == asset.asset_type]
        records.append(
            {
                **asset.to_dict(),
                "backup_file_count": len(asset_files),
                "backup_fingerprint": _file_record_fingerprint(asset_files),
            }
        )
    return records


def _stream_file_to_zip(archive: zipfile.ZipFile, source: Path, archive_path: str) -> tuple[int, str]:
    expected_size = source.stat().st_size
    digest = hashlib.sha256()
    size = 0
    info = zipfile.ZipInfo(archive_path)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    with source.open("rb") as input_handle, archive.open(info, "w", force_zip64=True) as output_handle:
        for block in iter(lambda: input_handle.read(1024 * 1024), b""):
            digest.update(block)
            output_handle.write(block)
            size += len(block)
    if size != expected_size:
        raise BackupSafetyError(f"source file changed while backing up: {source}")
    return size, digest.hexdigest()


def _write_manifest_to_zip(archive: zipfile.ZipFile, manifest: dict[str, Any]) -> None:
    info = zipfile.ZipInfo(BACKUP_MANIFEST_NAME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    archive.writestr(
        info,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )


def _hash_archive_records(
    path: Path,
    records: list[dict[str, Any]],
    *,
    workers: int,
) -> dict[str, tuple[int, str] | Exception]:
    if not records:
        return {}
    worker_count = min(workers, len(records))
    batches = [records[index::worker_count] for index in range(worker_count)]
    with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="backup-verify") as executor:
        batch_results = list(executor.map(lambda batch: _hash_archive_batch(path, batch), batches))
    return {name: result for batch in batch_results for name, result in batch.items()}


def _hash_archive_batch(
    path: Path,
    records: list[dict[str, Any]],
) -> dict[str, tuple[int, str] | Exception]:
    results: dict[str, tuple[int, str] | Exception] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for record in records:
                name = str(record.get("archive_path") or "")
                try:
                    digest = hashlib.sha256()
                    size = 0
                    with archive.open(name) as handle:
                        for block in iter(lambda: handle.read(1024 * 1024), b""):
                            digest.update(block)
                            size += len(block)
                    results[name] = (size, digest.hexdigest())
                except Exception as exc:
                    results[name] = exc
    except Exception as exc:
        for record in records:
            results[str(record.get("archive_path") or "")] = exc
    return results


def _archive_asset_record_count(path: Path, asset_type: str, records: list[dict[str, Any]]) -> int | None:
    names = [str(record.get("archive_path") or "") for record in records]
    if asset_type == "markdown_library":
        return sum(name.endswith(".md") and "/articles/" in name for name in names)
    if asset_type == "pdf_library":
        return sum(name.endswith(".pdf") and "/articles/" in name for name in names)
    if asset_type in {"evaluation_outputs", "corpus_inventory", "runtime_cache", "browser_profiles", "runtime_traces"} or asset_type.startswith(("unclassified_local_data:", "legacy_corpus_run:")):
        return len(records)
    preferred_suffixes = {
        "article_store": "corpus/pilot/article_store/articles.json",
        "legacy_article_store": "articles.json",
        "classification_registry": "corpus/pilot/completion_classifications.json",
        "corpus_progress": "corpus/pilot/progress.json",
        "learning_json": "learning.json",
        "learning_sqlite": "scientific_spaces.db",
        "zotero_links": "zotero_links.json",
        "tutor_sessions": "tutor_sessions.json",
        "rag_index": "rag/full_corpus/index/manifest.json",
        "knowledge_graph": "graph/full_corpus/manifest.json",
        "corpus_validation": "corpus/pilot/validation_summary.json",
        "corpus_failures": "corpus/pilot/failed_urls.jsonl",
    }
    suffix = preferred_suffixes.get(asset_type)
    name = next((candidate for candidate in names if suffix and candidate.endswith(suffix)), None)
    if name is None:
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            payload = archive.read(name)
        if asset_type == "learning_sqlite":
            return _sqlite_count_from_bytes(payload)
        if asset_type == "corpus_failures":
            return sum(1 for line in payload.decode("utf-8").splitlines() if line.strip())
        data = json.loads(payload.decode("utf-8"))
    except (OSError, KeyError, UnicodeDecodeError, json.JSONDecodeError, zipfile.BadZipFile):
        return None
    if asset_type in {"article_store", "legacy_article_store"}:
        return len(data) if isinstance(data, list) else 0
    if asset_type == "classification_registry":
        values = data.get("classifications", {}) if isinstance(data, dict) else {}
        return len(values) if isinstance(values, (dict, list)) else 0
    if asset_type == "learning_json":
        return sum(len(data.get(key, {})) for key in ("states", "bookmarks", "notes", "sessions") if isinstance(data, dict) and isinstance(data.get(key, {}), (dict, list)))
    if asset_type == "zotero_links":
        return sum(len(value) for value in data.values() if isinstance(value, dict)) if isinstance(data, dict) else 0
    if asset_type == "rag_index":
        return int(data.get("chunk_count", 0)) if isinstance(data, dict) else 0
    if asset_type == "knowledge_graph":
        return int(data.get("node_count", 0)) + int(data.get("edge_count", 0)) if isinstance(data, dict) else 0
    return len(data) if isinstance(data, (dict, list)) else 0


def _verify_profile(profile: str | None, pdf_included: bool | None, assets: list[Any], issues: list[OperationIssue]) -> None:
    if profile not in VALID_PROFILES:
        issues.append(_issue("PROFILE_MISMATCH", f"unknown profile: {profile}"))
        return
    typed = [asset for asset in assets if isinstance(asset, dict)]
    tiers = {str(asset.get("tier")) for asset in typed}
    types = {str(asset.get("asset_type")) for asset in typed}
    if "Tier 3" in tiers:
        issues.append(_issue("PROFILE_MISMATCH", "Tier 3 data must not be backed up"))
    if profile == "essential" and "Tier 2" in tiers:
        issues.append(_issue("PROFILE_MISMATCH", "essential backup contains Tier 2 data"))
    has_pdf = "pdf_library" in types
    if has_pdf != bool(pdf_included):
        issues.append(_issue("PROFILE_MISMATCH", "PDF inclusion does not match manifest policy"))


def _file_record_fingerprint(records: list[dict[str, Any]]) -> str:
    payload = [
        {
            "relative_path": str(record.get("relative_path") or ""),
            "size_bytes": int(record.get("size_bytes", 0)),
            "sha256": str(record.get("sha256") or ""),
        }
        for record in sorted(records, key=lambda item: str(item.get("relative_path") or ""))
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _safe_archive_name(name: str) -> bool:
    if not name or "\\" in name:
        return False
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and path.parts[0] not in {"", "."}
        and not path.parts[0].endswith(":")
    )


def _sqlite_count_from_bytes(payload: bytes) -> int | None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="scientific-spaces-backup-verify-", suffix=".db", delete=False) as handle:
            handle.write(payload)
            temporary_path = Path(handle.name)
        total = 0
        with sqlite3.connect(f"file:{temporary_path}?mode=ro", uri=True) as connection:
            tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ("learning_state", "bookmarks", "notes", "sessions"):
                if table in tables:
                    total += int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        return total
    except (OSError, sqlite3.Error):
        return None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _zip_info_is_symlink(info: zipfile.ZipInfo) -> bool:
    return info.create_system == 3 and stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


def _assert_no_symlinks(root: Path) -> None:
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        for name in (*dirnames, *filenames):
            if (current / name).is_symlink():
                raise BackupSafetyError(f"symlink is not allowed in source data: {(current / name).relative_to(root)}")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _issue(code: str, message: str, severity: str = "BLOCKED") -> OperationIssue:
    return OperationIssue(issue_code=code, message=message, severity=severity)


def _verification_result(
    path: Path,
    profile: str | None,
    pdf_included: bool | None,
    file_count: int,
    issues: list[OperationIssue],
    asset_fingerprints: dict[str, str],
    asset_record_counts: dict[str, int | None],
) -> BackupVerificationResult:
    unique: dict[tuple[str, str], OperationIssue] = {}
    for issue in issues:
        unique[(issue.issue_code, issue.message)] = issue
    ordered = tuple(sorted(unique.values(), key=lambda item: (item.issue_code, item.message)))
    if any(issue.severity == "BLOCKED" for issue in ordered):
        status = "BLOCKED"
    elif ordered:
        status = "CONDITIONAL"
    else:
        status = "PASS"
    return BackupVerificationResult(
        status=status,
        archive_path=path,
        profile=profile,
        pdf_included=pdf_included,
        file_count=file_count,
        issues=ordered,
        asset_fingerprints=asset_fingerprints,
        asset_record_counts=asset_record_counts,
    )
