from __future__ import annotations

import json
import os
import shutil
import stat
import zipfile
from pathlib import Path

import pytest

from app.operations.backup import BackupSafetyError, create_backup, verify_backup
from app.operations.restore import RestoreSafetyError, restore_backup
from app.persistence.sqlite import connect, initialize_schema
from tests.operations_helpers import make_local_data_root


ARTICLE_MEMBER = "data/corpus/pilot/article_store/articles.json"


def _names(archive: Path) -> set[str]:
    with zipfile.ZipFile(archive) as handle:
        return set(handle.namelist())


def _rewrite_archive(source: Path, target: Path, *, drop: str = "", replace: dict[str, bytes] | None = None) -> None:
    replacements = replace or {}
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as new:
        for info in old.infolist():
            if info.filename == drop:
                continue
            new.writestr(info, replacements.get(info.filename, old.read(info.filename)))


def test_essential_backup_contains_only_tier_one_and_manifest(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    output = tmp_path / "backups"

    result = create_backup(root, output, profile="essential", workers=4, verify=True)
    names = _names(result.archive_path)
    verification = verify_backup(result.archive_path, workers=4)

    assert result.status == "PASS"
    assert verification.status == "PASS"
    assert "backup_manifest.json" in names
    assert ARTICLE_MEMBER in names
    assert "data/corpus/pilot/completion_classifications.json" in names
    assert "data/learning.json" in names
    assert not any("local_library" in name for name in names)
    assert not any(name.endswith(".pdf") for name in names)
    assert not any("rag/full_corpus" in name for name in names)
    assert not any("graph/full_corpus" in name for name in names)
    assert stat.S_IMODE(result.archive_path.stat().st_mode) == 0o600


@pytest.mark.parametrize("include_pdf,expected", [(False, False), (True, True)])
def test_complete_backup_pdf_policy_is_explicit(tmp_path: Path, include_pdf: bool, expected: bool) -> None:
    root, _ = make_local_data_root(tmp_path)

    result = create_backup(
        root,
        tmp_path / f"backup-{include_pdf}",
        profile="complete",
        include_pdf=include_pdf,
        workers=4,
        verify=True,
    )
    names = _names(result.archive_path)

    assert any("local_library" in name for name in names)
    assert any("rag/full_corpus" in name for name in names)
    assert any("graph/full_corpus" in name for name in names)
    assert any(name.endswith(".pdf") for name in names) is expected


def test_backup_rejects_output_inside_source_root(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)

    with pytest.raises(BackupSafetyError, match="outside"):
        create_backup(root, root / "backups", profile="essential")


def test_backup_rejects_source_symlink_escape(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    os.symlink(outside, root / "personal-data.json")

    with pytest.raises(BackupSafetyError, match="symlink"):
        create_backup(root, tmp_path / "backups", profile="essential")


def test_failed_backup_leaves_no_complete_or_partial_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _ = make_local_data_root(tmp_path)
    output = tmp_path / "backups"

    def fail(*args: object, **kwargs: object) -> object:
        raise OSError("injected write failure")

    monkeypatch.setattr("app.operations.backup._stream_file_to_zip", fail)
    with pytest.raises(OSError, match="injected"):
        create_backup(root, output, profile="essential")

    assert not list(output.glob("*.zip"))
    assert not list(output.glob("*.partial"))


def test_backup_excludes_env_and_does_not_leak_api_key(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    secret = "sk-test-secret-value"
    (root / ".env").write_text(f"OPENAI_API_KEY={secret}\n", encoding="utf-8")

    result = create_backup(root, tmp_path / "backups", profile="essential", verify=True)
    with zipfile.ZipFile(result.archive_path) as handle:
        manifest_text = handle.read("backup_manifest.json").decode()
        names = handle.namelist()

    assert not any(Path(name).name == ".env" for name in names)
    assert secret not in manifest_text


def test_verifier_detects_hash_mismatch_and_missing_required_file(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    valid = create_backup(root, tmp_path / "backups", profile="essential").archive_path
    modified = tmp_path / "modified.zip"
    missing = tmp_path / "missing.zip"
    _rewrite_archive(valid, modified, replace={ARTICLE_MEMBER: b"[]"})
    _rewrite_archive(valid, missing, drop=ARTICLE_MEMBER)

    modified_result = verify_backup(modified, workers=2)
    missing_result = verify_backup(missing, workers=2)

    assert modified_result.status == "BLOCKED"
    assert "HASH_MISMATCH" in modified_result.issue_codes
    assert missing_result.status == "BLOCKED"
    assert "MISSING_REQUIRED_FILE" in missing_result.issue_codes


def test_verifier_detects_truncated_archive(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    valid = create_backup(root, tmp_path / "backups", profile="essential").archive_path
    corrupt = tmp_path / "corrupt.zip"
    payload = valid.read_bytes()
    corrupt.write_bytes(payload[: len(payload) // 2])

    result = verify_backup(corrupt)

    assert result.status == "BLOCKED"
    assert "CORRUPT_ARCHIVE" in result.issue_codes


def test_verifier_rejects_path_traversal_and_symlink_entries(tmp_path: Path) -> None:
    traversal = tmp_path / "traversal.zip"
    symlink = tmp_path / "symlink.zip"
    with zipfile.ZipFile(traversal, "w") as handle:
        handle.writestr("../escape", b"bad")
    link = zipfile.ZipInfo("data/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(symlink, "w") as handle:
        handle.writestr(link, "../../escape")

    traversal_result = verify_backup(traversal)
    symlink_result = verify_backup(symlink)

    assert "UNSAFE_ARCHIVE_PATH" in traversal_result.issue_codes
    assert "SYMLINK_ENTRY" in symlink_result.issue_codes


def test_restore_to_isolated_directory_preserves_hashes_and_counts(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    backup = create_backup(root, tmp_path / "backups", profile="essential", verify=True)
    target = tmp_path / "restore"

    result = restore_backup(backup.archive_path, target, verify=True, protected_data_root=root, workers=4)

    assert result.status == "PASS"
    assert json.loads((target / "corpus/pilot/article_store/articles.json").read_text())[0]["id"] == "a1"
    assert result.restored_asset_counts["article_store"] == 2
    assert result.restored_fingerprints["article_store"] == backup.asset_fingerprints["article_store"]


def test_restore_rejects_nonempty_and_protected_targets(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    backup = create_backup(root, tmp_path / "backups", profile="essential")
    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(RestoreSafetyError, match="empty"):
        restore_backup(backup.archive_path, nonempty, protected_data_root=root)
    with pytest.raises(RestoreSafetyError, match="protected"):
        restore_backup(backup.archive_path, root, overwrite=True, protected_data_root=root)


def test_restore_failure_rolls_back_without_partial_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = make_local_data_root(tmp_path)
    backup = create_backup(root, tmp_path / "backups", profile="essential")
    target = tmp_path / "restore"
    calls = 0

    def fail_after_one(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise OSError("injected restore failure")
        from app.operations.restore import _extract_file_unpatched

        _extract_file_unpatched(*args, **kwargs)

    monkeypatch.setattr("app.operations.restore._extract_file", fail_after_one)
    with pytest.raises(OSError, match="injected"):
        restore_backup(backup.archive_path, target, protected_data_root=root)

    assert not target.exists()
    assert not list(tmp_path.glob(".restore.staging-*"))


def test_sqlite_learning_data_record_count_is_verified_and_restored(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    database = root / "scientific_spaces.db"
    initialize_schema(database)
    with connect(database) as connection:
        connection.execute(
            "INSERT INTO bookmarks (article_id, title, url, created_at) VALUES (?, ?, ?, ?)",
            ("a1", "Attention", "https://spaces.ac.cn/archives/1", "2025-01-01T00:00:00Z"),
        )

    backup = create_backup(root, tmp_path / "backups", profile="essential", verify=True)
    verification = verify_backup(backup.archive_path)
    restored = restore_backup(
        backup.archive_path,
        tmp_path / "restore",
        protected_data_root=root,
        verify=True,
    )

    assert verification.asset_record_counts["learning_sqlite"] == 1
    assert restored.restored_asset_counts["learning_sqlite"] == 1


def test_restore_rejects_file_target_with_clear_safety_error(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    backup = create_backup(root, tmp_path / "backups", profile="essential")
    target = tmp_path / "target-file"
    target.write_text("do not replace", encoding="utf-8")

    with pytest.raises(RestoreSafetyError, match="directory"):
        restore_backup(backup.archive_path, target, protected_data_root=root)


def test_verifier_rejects_windows_drive_archive_path(tmp_path: Path) -> None:
    archive = tmp_path / "drive.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("C:/escape", b"bad")

    result = verify_backup(archive)

    assert "UNSAFE_ARCHIVE_PATH" in result.issue_codes


def test_verifier_rejects_absolute_path_inside_backup_manifest(tmp_path: Path) -> None:
    root, _ = make_local_data_root(tmp_path)
    valid = create_backup(root, tmp_path / "backups", profile="essential").archive_path
    with zipfile.ZipFile(valid) as handle:
        manifest = json.loads(handle.read("backup_manifest.json"))
    manifest["files"][0]["relative_path"] = "/absolute/escape"
    malicious = tmp_path / "absolute-manifest.zip"
    _rewrite_archive(
        valid,
        malicious,
        replace={"backup_manifest.json": json.dumps(manifest).encode("utf-8")},
    )

    result = verify_backup(malicious)

    assert result.status == "BLOCKED"
    assert "UNSAFE_MANIFEST_PATH" in result.issue_codes
