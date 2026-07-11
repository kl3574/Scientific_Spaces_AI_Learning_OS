from __future__ import annotations

import json
from pathlib import Path

from app.operations.inventory import build_local_data_manifest, load_local_data_manifest
from tests.operations_helpers import make_local_data_root


REQUIRED_ASSET_FIELDS = {
    "asset_type",
    "relative_path",
    "tier",
    "size_bytes",
    "record_count",
    "fingerprint",
    "source_fingerprint",
    "schema_version",
    "rebuild_command",
    "required_for_restore",
    "contains_user_data",
    "backup_priority",
}


def test_inventory_covers_source_derived_and_user_assets(tmp_path: Path) -> None:
    root, corpus_fingerprint = make_local_data_root(tmp_path)

    manifest = build_local_data_manifest(root, workers=4, write=True)
    by_type = {asset.asset_type: asset for asset in manifest.assets}

    assert {
        "article_store",
        "classification_registry",
        "learning_json",
        "zotero_links",
        "tutor_sessions",
        "markdown_library",
        "pdf_library",
        "rag_index",
        "knowledge_graph",
        "evaluation_outputs",
        "runtime_cache",
    } <= set(by_type)
    assert by_type["article_store"].record_count == 2
    assert by_type["article_store"].source_fingerprint == corpus_fingerprint
    assert by_type["classification_registry"].record_count == 1
    assert by_type["learning_json"].record_count == 4
    assert by_type["learning_json"].contains_user_data is True
    assert by_type["pdf_library"].tier == "Tier 2"
    assert by_type["runtime_cache"].tier == "Tier 3"


def test_manifest_fingerprint_is_worker_and_timestamp_independent(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)

    serial = build_local_data_manifest(root, workers=1, write=False)
    concurrent = build_local_data_manifest(root, workers=4, write=False)

    assert serial.deterministic_fingerprint == concurrent.deterministic_fingerprint
    assert [asset.to_dict() for asset in serial.assets] == [asset.to_dict() for asset in concurrent.assets]


def test_manifest_has_required_fields_and_only_relative_paths(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)

    manifest = build_local_data_manifest(root, workers=2, write=True)
    payload = manifest.to_dict()

    assert Path(manifest.manifest_path).is_file()
    assert str(root.resolve()) not in json.dumps(payload)
    assert all(REQUIRED_ASSET_FIELDS <= set(asset) for asset in payload["assets"])
    assert all(not Path(asset["relative_path"]).is_absolute() for asset in payload["assets"])
    assert "generated_at" not in manifest.fingerprint_payload()


def test_manifest_write_is_atomic_and_loadable(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)

    created = build_local_data_manifest(root, workers=2, write=True)
    loaded = load_local_data_manifest(root / "operations/local_data_manifest.json")

    assert loaded.deterministic_fingerprint == created.deterministic_fingerprint
    assert not list((root / "operations").glob("*.tmp-*"))


def test_inventory_output_does_not_expose_note_bodies(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)

    payload = build_local_data_manifest(root, workers=2, write=False).to_dict()

    assert "private-note-body" not in json.dumps(payload, ensure_ascii=False)


def test_legacy_probe_outputs_are_rebuildable_tier_two(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    probe = root / "corpus/p1_003_probe/progress.json"
    probe.parent.mkdir(parents=True)
    probe.write_text('{"status":"diagnostic"}', encoding="utf-8")

    manifest = build_local_data_manifest(root, write=False)
    asset = next(item for item in manifest.assets if item.relative_path == "corpus/p1_003_probe/progress.json")

    assert asset.tier == "Tier 2"
    assert asset.contains_user_data is False
