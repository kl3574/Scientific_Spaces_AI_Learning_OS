from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, TypedDict

from app.persistence.sqlite import connect, initialize_schema


class LearningMigrationError(RuntimeError):
    pass


class MigrationRecordSummary(TypedDict):
    states: int
    bookmarks: int
    notes: int
    sessions: int


@dataclass(frozen=True)
class LearningMigrationResult:
    direction: str
    source: str
    target: str
    records: MigrationRecordSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "direction": self.direction,
            "source": self.source,
            "target": self.target,
            "records": dict(self.records),
        }


def migrate_json_to_sqlite(json_path: Path | str, sqlite_path: Path | str) -> LearningMigrationResult:
    source = Path(json_path).expanduser().resolve()
    target = Path(sqlite_path).expanduser().resolve()
    if source == target:
        raise LearningMigrationError("source and target must be distinct paths")

    payload = _load_learning_json(source)
    staging = _staging_path(target, "to-sqlite")
    try:
        initialize_schema(staging)
        records = _load_json_payload_into_sqlite(payload, staging)
        os.replace(staging, target)
    except Exception:
        staging.unlink(missing_ok=True)
        raise
    return LearningMigrationResult(
        direction="json_to_sqlite",
        source=str(source),
        target=str(target),
        records=records,
    )


def migrate_sqlite_to_json(sqlite_path: Path | str, json_path: Path | str) -> LearningMigrationResult:
    source = Path(sqlite_path).expanduser().resolve()
    target = Path(json_path).expanduser().resolve()
    if source == target:
        raise LearningMigrationError("source and target must be distinct paths")

    payload = _load_sqlite_payload(source)
    staging = _staging_path(target, "to-json")
    try:
        staging.parent.mkdir(parents=True, exist_ok=True)
        staging.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(staging, target)
    except Exception:
        staging.unlink(missing_ok=True)
        raise
    return LearningMigrationResult(
        direction="sqlite_to_json",
        source=str(source),
        target=str(target),
        records={
            "states": len(payload["states"]),
            "bookmarks": len(payload["bookmarks"]),
            "notes": len(payload["notes"]),
            "sessions": len(payload["sessions"]),
        },
    )


def _load_json_payload_into_sqlite(
    payload: dict[str, dict[str, dict[str, object]]],
    staging: Path,
) -> MigrationRecordSummary:
    with connect(staging) as connection:
        state_count = _upsert_learning_states(payload["states"], connection)
        bookmark_count = _upsert_bookmarks(payload["bookmarks"], connection)
        note_count = _upsert_notes(payload["notes"], connection)
        session_count = _upsert_sessions(payload["sessions"], connection)
        connection.commit()
    return {
        "states": state_count,
        "bookmarks": bookmark_count,
        "notes": note_count,
        "sessions": session_count,
    }


def _upsert_learning_states(
    states: dict[str, dict[str, Any]],
    connection: sqlite3.Connection,
) -> int:
    statement = """
        INSERT INTO learning_state (
            article_id, status, last_read_at, completed_at, read_count, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(article_id) DO UPDATE SET
            status = excluded.status,
            last_read_at = excluded.last_read_at,
            completed_at = excluded.completed_at,
            read_count = excluded.read_count,
            updated_at = excluded.updated_at
    """
    count = 0
    for article_id, record in _iter_records(states, id_field="article_id"):
        connection.execute(
            statement,
            (
                article_id,
                _require_text_or_default(record.get("status"), "unread"),
                _optional_text(record.get("last_read_at")),
                _optional_text(record.get("completed_at")),
                _coerce_int(record.get("read_count"), default=0, field_name="read_count"),
                _optional_text(record.get("updated_at")),
            ),
        )
        count += 1
    return count


def _upsert_bookmarks(
    bookmarks: dict[str, dict[str, Any]],
    connection: sqlite3.Connection,
) -> int:
    statement = """
        INSERT INTO bookmarks (article_id, title, url, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(article_id) DO UPDATE SET
            title = excluded.title,
            url = excluded.url,
            created_at = excluded.created_at
    """
    count = 0
    for article_id, record in _iter_records(bookmarks, id_field="article_id"):
        connection.execute(
            statement,
            (
                article_id,
                _require_text(record.get("title"), "title"),
                _require_text(record.get("url"), "url"),
                _require_text(record.get("created_at"), "created_at"),
            ),
        )
        count += 1
    return count


def _upsert_notes(
    notes: dict[str, dict[str, Any]],
    connection: sqlite3.Connection,
) -> int:
    statement = """
        INSERT INTO notes (note_id, article_id, content, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(note_id) DO UPDATE SET
            article_id = excluded.article_id,
            content = excluded.content,
            created_at = excluded.created_at,
            updated_at = excluded.updated_at
    """
    count = 0
    for note_id, record in _iter_records(notes, id_field="note_id"):
        connection.execute(
            statement,
            (
                note_id,
                _require_text(record.get("article_id"), "article_id"),
                _require_text(record.get("content"), "content"),
                _require_text(record.get("created_at"), "created_at"),
                _require_text(record.get("updated_at"), "updated_at"),
            ),
        )
        count += 1
    return count


def _upsert_sessions(
    sessions: dict[str, dict[str, Any]],
    connection: sqlite3.Connection,
) -> int:
    statement = """
        INSERT INTO sessions (session_id, article_id, started_at, ended_at, duration_seconds, source)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            article_id = excluded.article_id,
            started_at = excluded.started_at,
            ended_at = excluded.ended_at,
            duration_seconds = excluded.duration_seconds,
            source = excluded.source
    """
    count = 0
    for session_id, record in _iter_records(sessions, id_field="session_id"):
        connection.execute(
            statement,
            (
                session_id,
                _require_text(record.get("article_id"), "article_id"),
                _require_text(record.get("started_at"), "started_at"),
                _optional_text(record.get("ended_at")),
                _optional_int(record.get("duration_seconds"), "duration_seconds"),
                _require_text(record.get("source"), "source"),
            ),
        )
        count += 1
    return count


def _load_learning_json(json_path: Path) -> dict[str, dict[str, dict[str, object]]]:
    if not json_path.exists():
        raise LearningMigrationError(f"source json does not exist: {json_path}")
    try:
        raw_payload = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LearningMigrationError(f"invalid learning json: {exc}") from exc
    if not isinstance(raw_payload, dict):
        raise LearningMigrationError("learning json payload must be an object")
    return {
        "states": _coerce_section(raw_payload.get("states"), "states"),
        "bookmarks": _coerce_section(raw_payload.get("bookmarks"), "bookmarks"),
        "notes": _coerce_section(raw_payload.get("notes"), "notes"),
        "sessions": _coerce_section(raw_payload.get("sessions"), "sessions"),
    }


def _load_sqlite_payload(
    sqlite_path: Path,
) -> dict[str, dict[str, dict[str, object]]]:
    if not sqlite_path.exists():
        raise LearningMigrationError(f"source sqlite does not exist: {sqlite_path}")
    try:
        with connect(sqlite_path) as connection:
            states_rows = connection.execute(
                "SELECT article_id, status, last_read_at, completed_at, read_count, updated_at "
                "FROM learning_state ORDER BY article_id ASC"
            ).fetchall()
            bookmark_rows = connection.execute(
                "SELECT article_id, title, url, created_at FROM bookmarks ORDER BY article_id ASC"
            ).fetchall()
            note_rows = connection.execute(
                "SELECT note_id, article_id, content, created_at, updated_at FROM notes ORDER BY note_id ASC"
            ).fetchall()
            session_rows = connection.execute(
                "SELECT session_id, article_id, started_at, ended_at, duration_seconds, source FROM sessions ORDER BY session_id ASC"
            ).fetchall()
    except sqlite3.DatabaseError as exc:
        raise LearningMigrationError(f"invalid sqlite database: {exc}") from exc

    return {
        "states": {str(row["article_id"]): dict(row) for row in states_rows},
        "bookmarks": {str(row["article_id"]): dict(row) for row in bookmark_rows},
        "notes": {str(row["note_id"]): dict(row) for row in note_rows},
        "sessions": {str(row["session_id"]): dict(row) for row in session_rows},
    }


def _iter_records(
    payload: dict[str, dict[str, Any]] | None,
    *,
    id_field: str,
) -> Iterable[tuple[str, dict[str, Any]]]:
    if not payload:
        return ()
    if not isinstance(payload, dict):
        raise LearningMigrationError(f"{id_field} section must be an object")
    for key, raw in payload.items():
        if not isinstance(raw, dict):
            raise LearningMigrationError(f"{id_field} record is invalid: {key}")
        record = dict(raw)
        key_id = str(key)
        raw_record_id = record.get(id_field)
        if raw_record_id is None:
            record_id = key_id
        elif not isinstance(raw_record_id, str) or not raw_record_id:
            raise LearningMigrationError(f"{id_field} is missing for record: {key}")
        else:
            record_id = raw_record_id
        if record_id != key_id:
            raise LearningMigrationError(
                f"{id_field} does not match record key: {record_id!r} != {key_id!r}"
            )
        record[id_field] = record_id
        yield record_id, record


def _coerce_section(raw: Any, name: str) -> dict[str, dict[str, Any]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise LearningMigrationError(f"{name} section must be an object")
    normalized: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            raise LearningMigrationError(f"{name} record is invalid: {key}")
        normalized[str(key)] = dict(value)
    return normalized


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise LearningMigrationError("field must be a string or null")
    return value


def _require_text(value: object, field_name: str) -> str:
    if value is None:
        raise LearningMigrationError(f"{field_name} is required")
    if not isinstance(value, str):
        raise LearningMigrationError(f"{field_name} must be a string")
    return value


def _require_text_or_default(value: object, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    raise LearningMigrationError("field must be a string")


def _coerce_int(value: object, *, default: int, field_name: str) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise LearningMigrationError(f"{field_name} must be an integer")
    if isinstance(value, int):
        return value
    raise LearningMigrationError(f"{field_name} must be an integer")


def _optional_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise LearningMigrationError(f"{field_name} must be an integer")
    if isinstance(value, int):
        return value
    raise LearningMigrationError(f"{field_name} must be an integer")


def _staging_path(target: Path, namespace: str) -> Path:
    return target.parent / f".{target.name}.{namespace}-{uuid.uuid4().hex}.tmp"
