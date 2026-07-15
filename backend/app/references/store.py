from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from app.references.deduplication import ReferenceBuildData
from app.references.models import (
    REFERENCE_EVIDENCE_SCHEMA,
    REFERENCE_MANIFEST_SCHEMA,
    REFERENCE_RECORD_SCHEMA,
    ZOTERO_CANDIDATE_SCHEMA,
    ReferenceManifest,
    ZoteroMatchCandidate,
    canonical_json,
)


CORE_FILES = (
    "records.jsonl",
    "evidence.jsonl",
    "article_index.json",
    "identifier_index.json",
    "zotero_candidates.jsonl",
)
STORE_FORMAT_VERSION = "p3-003-store/v1"
INTEGRITY_RULE_VERSION = "p3-003-integrity/v1"


class ReferenceStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoreInstallResult:
    path: Path
    manifest: ReferenceManifest
    no_op: bool
    rollback_recovered: bool


def install_reference_store(
    target: Path | str,
    *,
    build_data: ReferenceBuildData,
    zotero_candidates: Iterable[ZoteroMatchCandidate],
    article_ids: list[str],
    corpus_fingerprint: str,
    configuration_fingerprint: str,
    build_fingerprint: str,
    source_asset_id: str,
    network_request_count: int,
    extra_counts: dict[str, Any] | None = None,
    failure_hook: Callable[[str, Path], None] | None = None,
) -> StoreInstallResult:
    target_path = Path(target)
    _validate_runtime_target(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    rollback = target_path.with_name(f".{target_path.name}.rollback")
    if rollback.is_symlink():
        raise ValueError("Reference Store rollback path cannot be a symlink")
    recovered = _recover_interrupted_state(target_path, rollback)
    stage = target_path.with_name(f".{target_path.name}.staging-{uuid.uuid4().hex}")
    stage.mkdir(parents=False)
    try:
        manifest = _write_stage(
            stage,
            build_data=build_data,
            zotero_candidates=list(zotero_candidates),
            article_ids=article_ids,
            corpus_fingerprint=corpus_fingerprint,
            configuration_fingerprint=configuration_fingerprint,
            build_fingerprint=build_fingerprint,
            source_asset_id=source_asset_id,
            network_request_count=network_request_count,
            extra_counts=extra_counts or {},
        )
        audit_reference_store(
            stage,
            expected_corpus_fingerprint=corpus_fingerprint,
            expected_configuration_fingerprint=configuration_fingerprint,
        )
        if target_path.exists():
            try:
                current = audit_reference_store(
                    target_path,
                    expected_corpus_fingerprint=corpus_fingerprint,
                    expected_configuration_fingerprint=configuration_fingerprint,
                )
            except ReferenceStoreError:
                current = None
            if current is not None and _same_content_files(current, manifest):
                shutil.rmtree(stage)
                return StoreInstallResult(target_path, current, True, recovered)
            if rollback.exists():
                shutil.rmtree(rollback)
            os.replace(target_path, rollback)
        if failure_hook:
            failure_hook("after_backup", target_path)
        try:
            os.replace(stage, target_path)
            if failure_hook:
                failure_hook("after_install", target_path)
            installed = audit_reference_store(
                target_path,
                expected_corpus_fingerprint=corpus_fingerprint,
                expected_configuration_fingerprint=configuration_fingerprint,
            )
        except Exception:
            if target_path.exists():
                shutil.rmtree(target_path)
            if rollback.exists():
                os.replace(rollback, target_path)
            raise
        if rollback.exists():
            shutil.rmtree(rollback)
        return StoreInstallResult(target_path, installed, False, recovered)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def audit_reference_store(
    root: Path | str,
    *,
    expected_corpus_fingerprint: str | None = None,
    expected_configuration_fingerprint: str | None = None,
) -> ReferenceManifest:
    path = Path(root)
    if not path.is_dir() or path.is_symlink():
        raise ReferenceStoreError("Reference Store directory is missing or unsafe")
    manifest_path = path / "manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = ReferenceManifest.from_dict(payload)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ReferenceStoreError("Reference Store manifest is missing or corrupt") from exc
    if (
        manifest.schema_version != REFERENCE_MANIFEST_SCHEMA
        or manifest.record_schema_version != REFERENCE_RECORD_SCHEMA
        or manifest.evidence_schema_version != REFERENCE_EVIDENCE_SCHEMA
        or manifest.candidate_schema_version != ZOTERO_CANDIDATE_SCHEMA
    ):
        raise ReferenceStoreError("Reference Store schema version is unsupported")
    if manifest.status != "complete":
        raise ReferenceStoreError("Reference Store manifest is not complete")
    if expected_corpus_fingerprint is not None and manifest.corpus_fingerprint != expected_corpus_fingerprint:
        raise ReferenceStoreError("Reference Store is stale: corpus fingerprint mismatch")
    if (
        expected_configuration_fingerprint is not None
        and manifest.configuration_fingerprint != expected_configuration_fingerprint
    ):
        raise ReferenceStoreError("Reference Store is stale: configuration fingerprint mismatch")

    if (
        not isinstance(manifest.files, list)
        or len(manifest.files) != len(CORE_FILES)
        or not all(isinstance(item, dict) for item in manifest.files)
    ):
        raise ReferenceStoreError("Reference Store manifest file inventory is invalid")
    listed = {str(item.get("path")): item for item in manifest.files}
    if set(listed) != set(CORE_FILES):
        raise ReferenceStoreError("Reference Store manifest file inventory is invalid")
    rows: dict[str, list[dict[str, Any]]] = {}
    for name in CORE_FILES:
        file_path = path / name
        if file_path.is_symlink() or not file_path.is_file():
            raise ReferenceStoreError(f"Reference Store file is missing or unsafe: {name}")
        record = listed[name]
        data = file_path.read_bytes()
        try:
            expected_size = int(record.get("size_bytes", -1))
        except (TypeError, ValueError) as exc:
            raise ReferenceStoreError(f"Reference Store file metadata is invalid: {name}") from exc
        if len(data) != expected_size or hashlib.sha256(data).hexdigest() != record.get("sha256"):
            raise ReferenceStoreError(f"Reference Store checksum mismatch: {name}")
        if name.endswith(".jsonl"):
            try:
                rows[name] = [json.loads(line) for line in data.decode("utf-8").splitlines() if line]
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ReferenceStoreError(f"Reference Store JSONL is corrupt: {name}") from exc
            try:
                expected_rows = int(record.get("row_count", -1))
            except (TypeError, ValueError) as exc:
                raise ReferenceStoreError(f"Reference Store row metadata is invalid: {name}") from exc
            if len(rows[name]) != expected_rows:
                raise ReferenceStoreError(f"Reference Store row count mismatch: {name}")
        else:
            try:
                value = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ReferenceStoreError(f"Reference Store JSON is corrupt: {name}") from exc
            rows[name] = [value]

    _audit_references(rows, manifest)
    return manifest


def store_status(
    root: Path | str,
    *,
    expected_corpus_fingerprint: str,
    expected_configuration_fingerprint: str,
) -> str:
    try:
        audit_reference_store(
            root,
            expected_corpus_fingerprint=expected_corpus_fingerprint,
            expected_configuration_fingerprint=expected_configuration_fingerprint,
        )
    except ReferenceStoreError as exc:
        return "stale" if "stale:" in str(exc) else "corrupt"
    return "valid"


def _write_stage(
    stage: Path,
    *,
    build_data: ReferenceBuildData,
    zotero_candidates: list[ZoteroMatchCandidate],
    article_ids: list[str],
    corpus_fingerprint: str,
    configuration_fingerprint: str,
    build_fingerprint: str,
    source_asset_id: str,
    network_request_count: int,
    extra_counts: dict[str, Any],
) -> ReferenceManifest:
    records = [item.to_dict() for item in sorted(build_data.records, key=lambda item: item.reference_id)]
    evidence = [item.to_dict() for item in sorted(build_data.evidence, key=lambda item: item.evidence_id)]
    candidates = [item.to_dict() for item in sorted(zotero_candidates, key=lambda item: item.candidate_id)]
    article_index: dict[str, dict[str, list[str]]] = {
        article_id: {"reference_ids": [], "evidence_ids": []} for article_id in sorted(article_ids)
    }
    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    for record in records:
        for evidence_id in record["evidence_ids"]:
            item = evidence_by_id[evidence_id]
            bucket = article_index[item["source_article_id"]]
            bucket["reference_ids"].append(record["reference_id"])
            bucket["evidence_ids"].append(evidence_id)
    for bucket in article_index.values():
        bucket["reference_ids"] = sorted(set(bucket["reference_ids"]))
        bucket["evidence_ids"] = sorted(set(bucket["evidence_ids"]))
    identifier_index = {
        item["canonical_key"]: item["reference_id"]
        for item in records
        if item["canonical_key"] is not None
    }

    _write_jsonl(stage / "records.jsonl", records)
    _write_jsonl(stage / "evidence.jsonl", evidence)
    _write_json(stage / "article_index.json", article_index)
    _write_json(stage / "identifier_index.json", dict(sorted(identifier_index.items())))
    _write_jsonl(stage / "zotero_candidates.jsonl", candidates)
    (stage / "reports").mkdir()

    files = [_file_record(stage / name, name) for name in CORE_FILES]
    counts = {
        "articles": len(article_ids),
        "records": len(records),
        "evidence": len(evidence),
        "zotero_candidates": len(candidates),
        "record_types": dict(sorted(Counter(item["reference_type"] for item in records).items())),
        "classifications": dict(sorted(Counter(item["classification"] for item in records).items())),
        **extra_counts,
    }
    manifest = ReferenceManifest(
        corpus_fingerprint=corpus_fingerprint,
        configuration_fingerprint=configuration_fingerprint,
        build_fingerprint=build_fingerprint,
        generated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        counts=counts,
        files=files,
        source_asset_id=source_asset_id,
        rebuild_command=(
            "uv run --project backend python scripts/references/run_reference_pilot.py "
            "--article-store <ignored-article-store> --sample-size 75 "
            "--output-dir .local_data/scientific_spaces/references/pilot --no-network"
        ),
        network_request_count=network_request_count,
    )
    _write_json(stage / "manifest.json", manifest.to_dict())
    return manifest


def _audit_references(rows: dict[str, list[dict[str, Any]]], manifest: ReferenceManifest) -> None:
    records = rows["records.jsonl"]
    evidence = rows["evidence.jsonl"]
    candidates = rows["zotero_candidates.jsonl"]
    article_index = rows["article_index.json"][0]
    identifier_index = rows["identifier_index.json"][0]
    if not all(isinstance(item, dict) for item in (*records, *evidence, *candidates)):
        raise ReferenceStoreError("Reference Store rows must be JSON objects")
    if any(item.get("schema_version") != REFERENCE_RECORD_SCHEMA for item in records):
        raise ReferenceStoreError("Reference Store record schema version is unsupported")
    if any(item.get("schema_version") != REFERENCE_EVIDENCE_SCHEMA for item in evidence):
        raise ReferenceStoreError("Reference Store evidence schema version is unsupported")
    if any(item.get("schema_version") != ZOTERO_CANDIDATE_SCHEMA for item in candidates):
        raise ReferenceStoreError("Reference Store candidate schema version is unsupported")
    record_ids = [item.get("reference_id") for item in records]
    evidence_ids = [item.get("evidence_id") for item in evidence]
    candidate_ids = [item.get("candidate_id") for item in candidates]
    if any(not isinstance(value, str) or not value for value in (*record_ids, *evidence_ids, *candidate_ids)):
        raise ReferenceStoreError("Reference Store contains missing or invalid IDs")
    if (
        len(record_ids) != len(set(record_ids))
        or len(evidence_ids) != len(set(evidence_ids))
        or len(candidate_ids) != len(set(candidate_ids))
    ):
        raise ReferenceStoreError("Reference Store contains duplicate IDs")
    record_set = set(record_ids)
    evidence_set = set(evidence_ids)
    evidence_owner = {item.get("evidence_id"): item.get("reference_id") for item in evidence}
    referenced_evidence: set[str] = set()
    for record in records:
        ids = record.get("evidence_ids")
        if not isinstance(ids, list) or sorted(ids) != ids or int(record.get("source_count", -1)) != len(ids):
            raise ReferenceStoreError("Reference Store evidence count/order invariant failed")
        if any(value not in evidence_set or evidence_owner.get(value) != record["reference_id"] for value in ids):
            raise ReferenceStoreError("Reference Store has orphan or misowned evidence")
        referenced_evidence.update(ids)
    if referenced_evidence != evidence_set or any(owner not in record_set for owner in evidence_owner.values()):
        raise ReferenceStoreError("Reference Store has unreferenced or orphan evidence")
    candidate_references = {item.get("reference_id") for item in candidates}
    if candidate_references != record_set:
        raise ReferenceStoreError("Reference Store has orphan Zotero candidate")
    if not isinstance(article_index, dict) or not all(isinstance(value, dict) for value in article_index.values()):
        raise ReferenceStoreError("Reference Store Article index is invalid")
    indexed_references = {
        value for bucket in article_index.values() for value in bucket.get("reference_ids", [])
    }
    indexed_evidence = {value for bucket in article_index.values() for value in bucket.get("evidence_ids", [])}
    if indexed_references != record_set or indexed_evidence != evidence_set:
        raise ReferenceStoreError("Reference Store Article index is incomplete")
    evidence_articles = {item.get("source_article_id") for item in evidence}
    if not evidence_articles.issubset(set(article_index)):
        raise ReferenceStoreError("Reference Store evidence points outside the Article index")
    if not isinstance(identifier_index, dict):
        raise ReferenceStoreError("Reference Store identifier index is invalid")
    expected_identifiers = {
        item["canonical_key"]: item["reference_id"] for item in records if item.get("canonical_key") is not None
    }
    if identifier_index != expected_identifiers:
        raise ReferenceStoreError("Reference Store identifier index is invalid")
    if not isinstance(manifest.counts, dict) or (
        manifest.counts.get("records") != len(records)
        or manifest.counts.get("evidence") != len(evidence)
        or manifest.counts.get("zotero_candidates") != len(candidates)
        or manifest.counts.get("articles") != len(article_index)
    ):
        raise ReferenceStoreError("Reference Store manifest counts do not reconcile")
    if manifest.network_request_count != 0:
        raise ReferenceStoreError("Reference Store network request count is nonzero")


def _validate_runtime_target(path: Path) -> None:
    if ".." in path.parts:
        raise ValueError("Reference Store output path cannot escape through parent traversal")
    resolved = path.resolve(strict=False)
    if ".local_data" not in resolved.parts or resolved.parts[-1] == ".local_data":
        raise ValueError("Reference Store output must be below an ignored .local_data directory")
    cursor = path
    while cursor != cursor.parent:
        if cursor.exists() and cursor.is_symlink():
            raise ValueError("Reference Store output path cannot contain symlinks")
        cursor = cursor.parent


def _recover_interrupted_state(target: Path, rollback: Path) -> bool:
    if rollback.exists() and not target.exists():
        os.replace(rollback, target)
        audit_reference_store(target)
        return True
    if rollback.exists() and target.exists():
        try:
            audit_reference_store(target)
        except ReferenceStoreError:
            shutil.rmtree(target)
            os.replace(rollback, target)
            audit_reference_store(target)
            return True
        shutil.rmtree(rollback)
    return False


def _same_content_files(left: ReferenceManifest, right: ReferenceManifest) -> bool:
    left_files = {(item["path"], item["sha256"], item["size_bytes"], item["row_count"]) for item in left.files}
    right_files = {(item["path"], item["sha256"], item["size_bytes"], item["row_count"]) for item in right.files}
    return (
        left.build_fingerprint == right.build_fingerprint
        and left.corpus_fingerprint == right.corpus_fingerprint
        and left.configuration_fingerprint == right.configuration_fingerprint
        and left_files == right_files
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    payload = "".join(canonical_json(row) + "\n" for row in rows)
    _write_bytes(path, payload.encode("utf-8"))


def _write_json(path: Path, value: Any) -> None:
    _write_bytes(path, (canonical_json(value) + "\n").encode("utf-8"))


def _write_bytes(path: Path, value: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _file_record(path: Path, name: str) -> dict[str, Any]:
    data = path.read_bytes()
    row_count = len(data.decode("utf-8").splitlines()) if name.endswith(".jsonl") else 1
    return {
        "path": name,
        "size_bytes": len(data),
        "row_count": row_count,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
