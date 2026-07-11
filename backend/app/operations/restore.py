from __future__ import annotations

import hashlib
import os
import shutil
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from app.operations.backup import DATA_PREFIX, read_backup_manifest, verify_backup
from app.operations.inventory import DEFAULT_WORKERS, build_local_data_manifest, normalize_workers
from app.operations.models import RestoreResult
from app.persistence.config import data_dir


class RestoreSafetyError(RuntimeError):
    pass


def restore_backup(
    archive_path: Path | str,
    target_dir: Path | str,
    *,
    overwrite: bool = False,
    verify: bool = True,
    protected_data_root: Path | str | None = None,
    workers: int = DEFAULT_WORKERS,
) -> RestoreResult:
    archive = Path(archive_path).expanduser().resolve()
    target = Path(target_dir).expanduser().resolve()
    worker_count = normalize_workers(workers)
    protected = Path(protected_data_root).expanduser().resolve() if protected_data_root else data_dir().expanduser().resolve()
    if target == protected or _is_relative_to(target, protected):
        raise RestoreSafetyError("restore target is the protected current data root")
    if target.exists() and not target.is_dir():
        raise RestoreSafetyError("restore target must be a directory")
    if target.exists() and any(target.iterdir()) and not overwrite:
        raise RestoreSafetyError("restore target must be empty unless overwrite is explicitly enabled")

    verification = verify_backup(archive, workers=worker_count)
    if verification.status != "PASS":
        raise RestoreSafetyError("backup verification failed: " + ", ".join(verification.issue_codes))
    manifest = read_backup_manifest(archive)
    file_records = manifest.get("files", [])
    if not isinstance(file_records, list):
        raise RestoreSafetyError("backup manifest file list is invalid")

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{target.name}.staging-{uuid.uuid4().hex}"
    rollback = target.parent / f".{target.name}.rollback-{uuid.uuid4().hex}"
    replaced_target = False
    try:
        staging.mkdir(mode=0o700)
        for record in file_records:
            if not isinstance(record, dict):
                raise RestoreSafetyError("backup manifest contains an invalid file record")
            _extract_file(archive, record, staging)
        restored_manifest = build_local_data_manifest(staging, workers=worker_count, write=False)
        restored_by_type = {asset.asset_type: asset for asset in restored_manifest.assets}
        expected_assets = {
            str(asset.get("asset_type")): asset
            for asset in manifest.get("asset_records", [])
            if isinstance(asset, dict)
        }
        for asset_type, expected in expected_assets.items():
            actual = restored_by_type.get(asset_type)
            if actual is None:
                raise RestoreSafetyError(f"restored asset is missing: {asset_type}")
            expected_count = expected.get("record_count")
            if expected_count is not None and actual.record_count != expected_count:
                raise RestoreSafetyError(f"restored record count mismatch: {asset_type}")
            if expected.get("tier") == "Tier 1" and expected.get("fingerprint") and actual.fingerprint != expected.get("fingerprint"):
                raise RestoreSafetyError(f"restored Tier 1 fingerprint mismatch: {asset_type}")

        if target.exists():
            if any(target.iterdir()):
                os.replace(target, rollback)
                replaced_target = True
            else:
                target.rmdir()
        os.replace(staging, target)
        if replaced_target:
            shutil.rmtree(rollback)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        if replaced_target and rollback.exists() and not target.exists():
            os.replace(rollback, target)
        raise
    finally:
        if rollback.exists() and target.exists():
            shutil.rmtree(rollback)

    asset_counts = {
        asset_type: restored_by_type[asset_type].record_count
        for asset_type in expected_assets
        if asset_type in restored_by_type
    }
    asset_fingerprints = {
        asset_type: str(expected["fingerprint"])
        for asset_type, expected in expected_assets.items()
        if expected.get("fingerprint")
    }
    if verify:
        _verify_restored_files(target, file_records)
    return RestoreResult(
        status="PASS",
        target_dir=target,
        file_count=len(file_records),
        restored_asset_counts=asset_counts,
        restored_fingerprints=asset_fingerprints,
    )


def _extract_file(archive_path: Path, record: dict[str, Any], staging: Path) -> None:
    archive_name = str(record.get("archive_path") or "")
    relative_name = str(record.get("relative_path") or "")
    if not archive_name.startswith(DATA_PREFIX) or not _safe_relative_path(relative_name):
        raise RestoreSafetyError(f"unsafe restore path: {relative_name or archive_name}")
    destination = (staging / PurePosixPath(relative_name)).resolve()
    if not _is_relative_to(destination, staging.resolve()):
        raise RestoreSafetyError(f"restore path escapes target: {relative_name}")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    digest = hashlib.sha256()
    size = 0
    with zipfile.ZipFile(archive_path) as archive, archive.open(archive_name) as source, destination.open("xb") as output:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
            output.write(block)
            size += len(block)
        output.flush()
        os.fsync(output.fileno())
    os.chmod(destination, 0o600)
    if size != record.get("size_bytes") or digest.hexdigest() != record.get("sha256"):
        raise RestoreSafetyError(f"restored file integrity mismatch: {relative_name}")


_extract_file_unpatched = _extract_file


def _verify_restored_files(target: Path, records: list[dict[str, Any]]) -> None:
    for record in records:
        path = target / str(record["relative_path"])
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        if size != record.get("size_bytes") or digest.hexdigest() != record.get("sha256"):
            raise RestoreSafetyError(f"post-restore integrity mismatch: {record['relative_path']}")


def _safe_relative_path(value: str) -> bool:
    if not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and path.parts[0] not in {"", "."}


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
