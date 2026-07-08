from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.learning.models import Bookmark, LearningNote, LearningSession, LearningState, LearningStatus, SessionSource

DEFAULT_LEARNING_FILE = ".local_data/scientific_spaces/learning.json"


def learning_store_path() -> Path:
    explicit_file = os.getenv("SCIENTIFIC_SPACES_LEARNING_FILE")
    if explicit_file:
        return Path(explicit_file)

    data_dir = Path(os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
    return data_dir / "learning.json"


def default_learning_state(article_id: str) -> LearningState:
    return LearningState(
        article_id=article_id,
        status="unread",
        last_read_at=None,
        completed_at=None,
        read_count=0,
        updated_at=None,
    )


class LearningStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def get_state(self, article_id: str) -> LearningState:
        data = self._read()
        item = data["states"].get(article_id)
        if item is None:
            return default_learning_state(article_id)
        return LearningState(**item)

    def list_states(self) -> list[LearningState]:
        return [LearningState(**item) for item in self._read()["states"].values()]

    def update_state(self, article_id: str, status: LearningStatus) -> LearningState:
        data = self._read()
        previous = self.get_state(article_id)
        now = _now()
        last_read_at = previous.last_read_at
        completed_at = previous.completed_at
        read_count = previous.read_count

        if status in {"reading", "completed"}:
            last_read_at = now
            read_count += 1
        if status == "completed":
            completed_at = now
        if status == "unread":
            completed_at = None

        state = LearningState(
            article_id=article_id,
            status=status,
            last_read_at=last_read_at,
            completed_at=completed_at,
            read_count=read_count,
            updated_at=now,
        )
        data["states"][article_id] = state.to_dict()
        self._write(data)
        return state

    def list_bookmarks(self) -> list[Bookmark]:
        bookmarks = [Bookmark(**item) for item in self._read()["bookmarks"].values()]
        return sorted(bookmarks, key=lambda item: item.created_at, reverse=True)

    def add_bookmark(self, *, article_id: str, title: str, url: str) -> Bookmark:
        data = self._read()
        existing = data["bookmarks"].get(article_id)
        if existing:
            return Bookmark(**existing)
        bookmark = Bookmark(article_id=article_id, title=title, url=url, created_at=_now())
        data["bookmarks"][article_id] = bookmark.to_dict()
        self._write(data)
        return bookmark

    def delete_bookmark(self, article_id: str) -> None:
        data = self._read()
        data["bookmarks"].pop(article_id, None)
        self._write(data)

    def list_notes(self, article_id: str) -> list[LearningNote]:
        notes = [
            LearningNote(**item)
            for item in self._read()["notes"].values()
            if item["article_id"] == article_id
        ]
        return sorted(notes, key=lambda item: item.created_at, reverse=True)

    def create_note(self, *, article_id: str, content: str) -> LearningNote:
        data = self._read()
        now = _now()
        note = LearningNote(
            note_id=uuid4().hex,
            article_id=article_id,
            content=content,
            created_at=now,
            updated_at=now,
        )
        data["notes"][note.note_id] = note.to_dict()
        self._write(data)
        return note

    def update_note(self, *, note_id: str, content: str) -> LearningNote | None:
        data = self._read()
        existing = data["notes"].get(note_id)
        if existing is None:
            return None
        note = LearningNote(
            note_id=note_id,
            article_id=existing["article_id"],
            content=content,
            created_at=existing["created_at"],
            updated_at=_now(),
        )
        data["notes"][note_id] = note.to_dict()
        self._write(data)
        return note

    def delete_note(self, note_id: str) -> None:
        data = self._read()
        data["notes"].pop(note_id, None)
        self._write(data)

    def create_session(self, *, article_id: str, source: SessionSource) -> LearningSession:
        data = self._read()
        session = LearningSession(
            session_id=uuid4().hex,
            article_id=article_id,
            started_at=_now(),
            ended_at=None,
            duration_seconds=None,
            source=source,
        )
        data["sessions"][session.session_id] = session.to_dict()
        self._write(data)
        return session

    def end_session(self, session_id: str) -> LearningSession | None:
        data = self._read()
        existing = data["sessions"].get(session_id)
        if existing is None:
            return None
        ended_at = _now()
        duration_seconds = _duration_seconds(existing["started_at"], ended_at)
        session = LearningSession(
            session_id=session_id,
            article_id=existing["article_id"],
            started_at=existing["started_at"],
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            source=existing["source"],
        )
        data["sessions"][session_id] = session.to_dict()
        self._write(data)
        return session

    def list_sessions(self) -> list[LearningSession]:
        sessions = [LearningSession(**item) for item in self._read()["sessions"].values()]
        return sorted(sessions, key=lambda item: item.started_at, reverse=True)

    def count_notes(self) -> int:
        return len(self._read()["notes"])

    def _read(self) -> dict[str, dict[str, dict[str, object]]]:
        if not self.path.exists():
            return _empty_data()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        normalized = _empty_data()
        for key in normalized:
            normalized[key].update(data.get(key, {}))
        return normalized

    def _write(self, data: dict[str, dict[str, dict[str, object]]]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _empty_data() -> dict[str, dict[str, dict[str, object]]]:
    return {"states": {}, "bookmarks": {}, "notes": {}, "sessions": {}}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _duration_seconds(started_at: str, ended_at: str) -> int:
    started = _parse_time(started_at)
    ended = _parse_time(ended_at)
    return max(0, int((ended - started).total_seconds()))


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
