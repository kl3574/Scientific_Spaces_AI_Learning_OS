from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.persistence import learning_migrator
from app.persistence.learning_migrator import migrate_json_to_sqlite, migrate_sqlite_to_json
from app.persistence.sqlite import connect


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / script), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_sample_learning_json(path: Path) -> dict[str, object]:
    payload = {
        "states": {
            "a1": {
                "article_id": "a1",
                "status": "reading",
                "last_read_at": "2026-07-01T10:00:00Z",
                "completed_at": None,
                "read_count": 4,
                "updated_at": "2026-07-01T10:00:00Z",
            },
            "a2": {
                "article_id": "a2",
                "status": "completed",
                "last_read_at": "2026-07-02T11:00:00Z",
                "completed_at": "2026-07-02T11:05:00Z",
                "read_count": 7,
                "updated_at": "2026-07-02T11:05:00Z",
            },
        },
        "bookmarks": {
            "a1": {
                "article_id": "a1",
                "title": "Attention",
                "url": "https://spaces.ac.cn/attention",
                "created_at": "2026-01-01T00:00:00Z",
            }
        },
        "notes": {
            "n1": {
                "note_id": "n1",
                "article_id": "a1",
                "content": "first insight",
                "created_at": "2026-01-02T00:00:00Z",
                "updated_at": "2026-01-02T01:00:00Z",
            },
            "n2": {
                "note_id": "n2",
                "article_id": "a1",
                "content": "second insight",
                "created_at": "2026-01-03T00:00:00Z",
                "updated_at": "2026-01-03T01:00:00Z",
            },
        },
        "sessions": {
            "s1": {
                "session_id": "s1",
                "article_id": "a1",
                "started_at": "2026-06-01T09:00:00Z",
                "ended_at": "2026-06-01T09:10:00Z",
                "duration_seconds": 600,
                "source": "reader",
            }
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _read_payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _table_counts(db_path: Path) -> tuple[int, int, int, int]:
    with connect(db_path) as connection:
        tables = [
            "learning_state",
            "bookmarks",
            "notes",
            "sessions",
        ]
        counts = []
        for table in tables:
            row = connection.execute(f'SELECT COUNT(*) AS count FROM "{table}"').fetchone()
            counts.append(int(row["count"]))
        return tuple(counts)


def test_json_to_sqlite_roundtrip_preserves_all_records(tmp_path: Path) -> None:
    source = tmp_path / "learning.json"
    target = tmp_path / "learning.db"
    restored = tmp_path / "restored.json"
    source_payload = _write_sample_learning_json(source)

    forward = migrate_json_to_sqlite(source, target)
    with connect(target) as connection:
        state_rows = {
            row["article_id"]: dict(row)
            for row in connection.execute("SELECT * FROM learning_state ORDER BY article_id ASC").fetchall()
        }
        bookmark_rows = {
            row["article_id"]: dict(row)
            for row in connection.execute("SELECT * FROM bookmarks ORDER BY article_id ASC").fetchall()
        }
        note_rows = {
            row["note_id"]: dict(row)
            for row in connection.execute("SELECT * FROM notes ORDER BY note_id ASC").fetchall()
        }
        session_rows = {
            row["session_id"]: dict(row)
            for row in connection.execute("SELECT * FROM sessions ORDER BY session_id ASC").fetchall()
        }

    backward = migrate_sqlite_to_json(target, restored)
    restored_payload = _read_payload(restored)
    assert source_payload == restored_payload
    assert forward.records["states"] == len(state_rows)
    assert forward.records["bookmarks"] == len(bookmark_rows)
    assert forward.records["notes"] == len(note_rows)
    assert forward.records["sessions"] == len(session_rows)
    assert backward.records["states"] == len(state_rows)
    assert backward.records["bookmarks"] == len(bookmark_rows)
    assert backward.records["notes"] == len(note_rows)
    assert backward.records["sessions"] == len(session_rows)
    assert state_rows["a1"]["status"] == source_payload["states"]["a1"]["status"]
    assert state_rows["a1"]["read_count"] == source_payload["states"]["a1"]["read_count"]
    assert bookmark_rows["a1"]["title"] == source_payload["bookmarks"]["a1"]["title"]
    assert note_rows["n2"]["content"] == source_payload["notes"]["n2"]["content"]
    assert session_rows["s1"]["source"] == source_payload["sessions"]["s1"]["source"]


def test_json_to_sqlite_migration_is_idempotent_no_growth(tmp_path: Path) -> None:
    source = tmp_path / "learning.json"
    target = tmp_path / "learning.db"
    _write_sample_learning_json(source)

    migrate_json_to_sqlite(source, target)
    first_counts = _table_counts(target)
    migrate_json_to_sqlite(source, target)
    second_counts = _table_counts(target)

    assert first_counts == second_counts == (2, 1, 2, 1)


def test_json_to_sqlite_fails_without_changing_existing_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "learning.json"
    target = tmp_path / "learning.db"
    _write_sample_learning_json(source)
    migrate_json_to_sqlite(source, target)
    source_before = source.read_bytes()
    target_before = target.read_bytes()
    before_counts = _table_counts(target)

    monkeypatch.setattr(learning_migrator.os, "replace", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected failure")))
    with pytest.raises(OSError, match="injected failure"):
        migrate_json_to_sqlite(source, target)
    after_counts = _table_counts(target)

    assert after_counts == before_counts
    assert source.read_bytes() == source_before
    assert target.read_bytes() == target_before
    assert not list(tmp_path.glob(".learning.db.to-sqlite-*.tmp"))


def test_sqlite_to_json_is_idempotent_and_failure_preserves_existing_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_json = tmp_path / "learning.json"
    source_db = tmp_path / "learning.db"
    target_json = tmp_path / "restored.json"
    source_payload = _write_sample_learning_json(source_json)
    migrate_json_to_sqlite(source_json, source_db)

    migrate_sqlite_to_json(source_db, target_json)
    first_export = target_json.read_bytes()
    migrate_sqlite_to_json(source_db, target_json)
    assert target_json.read_bytes() == first_export
    assert _read_payload(target_json) == source_payload

    source_before = source_db.read_bytes()
    monkeypatch.setattr(
        learning_migrator.os,
        "replace",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected export failure")),
    )
    with pytest.raises(OSError, match="injected export failure"):
        migrate_sqlite_to_json(source_db, target_json)

    assert source_db.read_bytes() == source_before
    assert target_json.read_bytes() == first_export
    assert not list(tmp_path.glob(".restored.json.to-json-*.tmp"))


@pytest.mark.parametrize(
    ("section", "record_id", "field", "invalid_value"),
    [
        ("states", "a1", "read_count", 1.5),
        ("sessions", "s1", "duration_seconds", "600"),
        ("notes", "n1", "note_id", "different-note-id"),
    ],
)
def test_invalid_or_identity_changing_json_never_replaces_existing_sqlite(
    tmp_path: Path,
    section: str,
    record_id: str,
    field: str,
    invalid_value: object,
) -> None:
    source = tmp_path / "learning.json"
    target = tmp_path / "learning.db"
    payload = _write_sample_learning_json(source)
    migrate_json_to_sqlite(source, target)
    target_before = target.read_bytes()
    payload[section][record_id][field] = invalid_value
    source.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(learning_migrator.LearningMigrationError):
        migrate_json_to_sqlite(source, target)

    assert target.read_bytes() == target_before
    assert not list(tmp_path.glob(".learning.db.to-sqlite-*.tmp"))


def test_sqlite_migration_cli_smoke_and_explicit_paths_required(tmp_path: Path) -> None:
    source = tmp_path / "learning.json"
    target = tmp_path / "learning.db"
    restored = tmp_path / "restored.json"
    _write_sample_learning_json(source)

    forward = _run(
        "scripts/persistence/migrate_learning_json_to_sqlite.py",
        "--json-path",
        str(source),
        "--sqlite-path",
        str(target),
    )
    back = _run(
        "scripts/persistence/migrate_learning_sqlite_to_json.py",
        "--sqlite-path",
        str(target),
        "--json-path",
        str(restored),
    )
    missing = _run("scripts/persistence/migrate_learning_json_to_sqlite.py")

    assert forward.returncode == 0, forward.stderr
    assert back.returncode == 0, back.stderr
    assert missing.returncode != 0
    assert "--json-path" in missing.stderr
    assert restored.exists()
    assert json.loads(restored.read_text(encoding="utf-8")) == _read_payload(source)
