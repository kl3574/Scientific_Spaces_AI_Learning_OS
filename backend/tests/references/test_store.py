from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.references.matching import match_reference_records
from app.references.models import sha256_text
from app.references.store import ReferenceStoreError, audit_reference_store, install_reference_store, store_status
from tests.references.helpers import article, reference_data


def _target(tmp_path: Path) -> Path:
    return tmp_path / ".local_data" / "scientific_spaces" / "references" / "pilot"


def _install(tmp_path: Path, *, build_id: str = "build-1", config: str = "config-1", failure_hook=None):
    data = reference_data(article("a1", "DOI:10.1000/example and https://example.org/paper"), build_id=build_id)
    matches = match_reference_records(data.records, [], provider_available=False)
    return install_reference_store(
        _target(tmp_path),
        build_data=data,
        zotero_candidates=matches.candidates,
        article_ids=["a1"],
        corpus_fingerprint=sha256_text("fixture-corpus"),
        configuration_fingerprint=config,
        build_fingerprint=build_id,
        source_asset_id="article-store:fixture",
        network_request_count=0,
        extra_counts={"silent_drops": 0},
        failure_hook=failure_hook,
    )


def test_store_install_integrity_and_no_op_rerun(tmp_path: Path) -> None:
    first = _install(tmp_path)
    second = _install(tmp_path)
    manifest = audit_reference_store(_target(tmp_path))

    assert first.no_op is False
    assert second.no_op is True
    assert manifest.build_fingerprint == "build-1"
    assert manifest.counts["records"] >= 2
    assert set(path.name for path in _target(tmp_path).iterdir()) >= {
        "manifest.json",
        "records.jsonl",
        "evidence.jsonl",
        "article_index.json",
        "identifier_index.json",
        "zotero_candidates.jsonl",
        "reports",
    }


def test_store_detects_corrupt_payload_and_stale_configuration(tmp_path: Path) -> None:
    _install(tmp_path)
    assert store_status(
        _target(tmp_path),
        expected_corpus_fingerprint=sha256_text("fixture-corpus"),
        expected_configuration_fingerprint="other-config",
    ) == "stale"

    with (_target(tmp_path) / "records.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{}\n")
    with pytest.raises(ReferenceStoreError, match="checksum mismatch"):
        audit_reference_store(_target(tmp_path))
    assert store_status(
        _target(tmp_path),
        expected_corpus_fingerprint=sha256_text("fixture-corpus"),
        expected_configuration_fingerprint="config-1",
    ) == "corrupt"


def test_failed_install_restores_previous_valid_store(tmp_path: Path) -> None:
    _install(tmp_path)

    def fail(phase: str, _path: Path) -> None:
        if phase == "after_install":
            raise OSError("injected install failure")

    with pytest.raises(OSError, match="injected"):
        _install(tmp_path, build_id="build-2", config="config-2", failure_hook=fail)

    manifest = audit_reference_store(_target(tmp_path))
    assert manifest.build_fingerprint == "build-1"
    assert not _target(tmp_path).with_name(".pilot.rollback").exists()


def test_interrupted_backup_is_recovered_on_next_run(tmp_path: Path) -> None:
    _install(tmp_path)

    def fail(phase: str, _path: Path) -> None:
        if phase == "after_backup":
            raise OSError("injected interruption")

    with pytest.raises(OSError, match="interruption"):
        _install(tmp_path, build_id="build-2", config="config-2", failure_hook=fail)
    assert not _target(tmp_path).exists()
    assert _target(tmp_path).with_name(".pilot.rollback").exists()

    recovered = _install(tmp_path, build_id="build-2", config="config-2")
    assert recovered.rollback_recovered is True
    assert audit_reference_store(_target(tmp_path)).build_fingerprint == "build-2"


def test_index_reference_mismatch_is_detected(tmp_path: Path) -> None:
    _install(tmp_path)
    index_path = _target(tmp_path) / "article_index.json"
    index_path.write_text(json.dumps({"a1": {"reference_ids": [], "evidence_ids": []}}), encoding="utf-8")
    manifest_path = _target(tmp_path) / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = index_path.read_bytes()
    for record in manifest["files"]:
        if record["path"] == "article_index.json":
            import hashlib

            record["size_bytes"] = len(data)
            record["sha256"] = hashlib.sha256(data).hexdigest()
            record["row_count"] = 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ReferenceStoreError, match="Article index"):
        audit_reference_store(_target(tmp_path))


def test_record_schema_mismatch_is_detected_after_checksum_reconciliation(tmp_path: Path) -> None:
    _install(tmp_path)
    records_path = _target(tmp_path) / "records.jsonl"
    rows = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["schema_version"] = "reference-record/unsupported"
    records_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    _reconcile_manifest_file(_target(tmp_path), "records.jsonl")

    with pytest.raises(ReferenceStoreError, match="record schema"):
        audit_reference_store(_target(tmp_path))


def test_store_rejects_non_runtime_output_path(tmp_path: Path) -> None:
    data = reference_data(article("a1", "DOI:10.1000/example"))
    with pytest.raises(ValueError, match=r"\.local_data"):
        install_reference_store(
            tmp_path / "tracked" / "pilot",
            build_data=data,
            zotero_candidates=[],
            article_ids=["a1"],
            corpus_fingerprint=sha256_text("fixture-corpus"),
            configuration_fingerprint="config",
            build_fingerprint="build",
            source_asset_id="fixture",
            network_request_count=0,
        )


def test_store_rejects_parent_traversal_even_when_local_data_is_present(tmp_path: Path) -> None:
    data = reference_data(article("a1", "DOI:10.1000/example"))
    with pytest.raises(ValueError, match="parent traversal"):
        install_reference_store(
            tmp_path / ".local_data" / ".." / "escaped" / "pilot",
            build_data=data,
            zotero_candidates=[],
            article_ids=["a1"],
            corpus_fingerprint=sha256_text("fixture-corpus"),
            configuration_fingerprint="config",
            build_fingerprint="build",
            source_asset_id="fixture",
            network_request_count=0,
        )


def _reconcile_manifest_file(root: Path, name: str) -> None:
    import hashlib

    path = root / name
    data = path.read_bytes()
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["files"]:
        if record["path"] == name:
            record["size_bytes"] = len(data)
            record["sha256"] = hashlib.sha256(data).hexdigest()
            record["row_count"] = len(data.decode("utf-8").splitlines())
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
