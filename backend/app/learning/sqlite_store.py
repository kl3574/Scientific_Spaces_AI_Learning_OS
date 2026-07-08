from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.learning.models import Bookmark, LearningNote, LearningSession, LearningState, LearningStatus, SessionSource
from app.learning.store import default_learning_state
from app.persistence.sqlite import connect, initialize_schema


class LearningSQLiteStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        initialize_schema(self.db_path)

    def get_state(self, article_id: str) -> LearningState:
        with connect(self.db_path) as connection:
            row = connection.execute(
                """
                SELECT article_id, status, last_read_at, completed_at, read_count, updated_at
                FROM learning_state
                WHERE article_id = ?
                """,
                (article_id,),
            ).fetchone()
        if row is None:
            return default_learning_state(article_id)
        return LearningState(**dict(row))

    def list_states(self) -> list[LearningState]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT article_id, status, last_read_at, completed_at, read_count, updated_at
                FROM learning_state
                ORDER BY article_id ASC
                """
            ).fetchall()
        return [LearningState(**dict(row)) for row in rows]

    def update_state(self, article_id: str, status: LearningStatus) -> LearningState:
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
        with connect(self.db_path) as connection:
            connection.execute(
                """
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
                """,
                (
                    state.article_id,
                    state.status,
                    state.last_read_at,
                    state.completed_at,
                    state.read_count,
                    state.updated_at,
                ),
            )
        return state

    def list_bookmarks(self) -> list[Bookmark]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT article_id, title, url, created_at
                FROM bookmarks
                ORDER BY created_at DESC, article_id ASC
                """
            ).fetchall()
        return [Bookmark(**dict(row)) for row in rows]

    def add_bookmark(self, *, article_id: str, title: str, url: str) -> Bookmark:
        with connect(self.db_path) as connection:
            existing = connection.execute(
                """
                SELECT article_id, title, url, created_at
                FROM bookmarks
                WHERE article_id = ?
                """,
                (article_id,),
            ).fetchone()
            if existing is not None:
                return Bookmark(**dict(existing))

            bookmark = Bookmark(article_id=article_id, title=title, url=url, created_at=_now())
            connection.execute(
                """
                INSERT INTO bookmarks (article_id, title, url, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (bookmark.article_id, bookmark.title, bookmark.url, bookmark.created_at),
            )
        return bookmark

    def delete_bookmark(self, article_id: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute("DELETE FROM bookmarks WHERE article_id = ?", (article_id,))

    def list_notes(self, article_id: str) -> list[LearningNote]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT note_id, article_id, content, created_at, updated_at
                FROM notes
                WHERE article_id = ?
                ORDER BY created_at DESC, note_id ASC
                """,
                (article_id,),
            ).fetchall()
        return [LearningNote(**dict(row)) for row in rows]

    def create_note(self, *, article_id: str, content: str) -> LearningNote:
        now = _now()
        note = LearningNote(
            note_id=uuid4().hex,
            article_id=article_id,
            content=content,
            created_at=now,
            updated_at=now,
        )
        with connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO notes (note_id, article_id, content, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (note.note_id, note.article_id, note.content, note.created_at, note.updated_at),
            )
        return note

    def update_note(self, *, note_id: str, content: str) -> LearningNote | None:
        with connect(self.db_path) as connection:
            existing = connection.execute(
                """
                SELECT note_id, article_id, content, created_at, updated_at
                FROM notes
                WHERE note_id = ?
                """,
                (note_id,),
            ).fetchone()
            if existing is None:
                return None

            note = LearningNote(
                note_id=note_id,
                article_id=str(existing["article_id"]),
                content=content,
                created_at=str(existing["created_at"]),
                updated_at=_now(),
            )
            connection.execute(
                """
                UPDATE notes
                SET content = ?, updated_at = ?
                WHERE note_id = ?
                """,
                (note.content, note.updated_at, note.note_id),
            )
        return note

    def delete_note(self, note_id: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute("DELETE FROM notes WHERE note_id = ?", (note_id,))

    def create_session(self, *, article_id: str, source: SessionSource) -> LearningSession:
        session = LearningSession(
            session_id=uuid4().hex,
            article_id=article_id,
            started_at=_now(),
            ended_at=None,
            duration_seconds=None,
            source=source,
        )
        with connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id, article_id, started_at, ended_at, duration_seconds, source
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.article_id,
                    session.started_at,
                    session.ended_at,
                    session.duration_seconds,
                    session.source,
                ),
            )
        return session

    def end_session(self, session_id: str) -> LearningSession | None:
        with connect(self.db_path) as connection:
            existing = connection.execute(
                """
                SELECT session_id, article_id, started_at, ended_at, duration_seconds, source
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if existing is None:
                return None

            ended_at = _now()
            duration_seconds = _duration_seconds(str(existing["started_at"]), ended_at)
            session = LearningSession(
                session_id=session_id,
                article_id=str(existing["article_id"]),
                started_at=str(existing["started_at"]),
                ended_at=ended_at,
                duration_seconds=duration_seconds,
                source=existing["source"],
            )
            connection.execute(
                """
                UPDATE sessions
                SET ended_at = ?, duration_seconds = ?
                WHERE session_id = ?
                """,
                (session.ended_at, session.duration_seconds, session.session_id),
            )
        return session

    def list_sessions(self) -> list[LearningSession]:
        with connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT session_id, article_id, started_at, ended_at, duration_seconds, source
                FROM sessions
                ORDER BY started_at DESC, session_id ASC
                """
            ).fetchall()
        return [LearningSession(**dict(row)) for row in rows]

    def count_notes(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM notes").fetchone()
            return int(row["count"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _duration_seconds(started_at: str, ended_at: str) -> int:
    started = _parse_time(started_at)
    ended = _parse_time(ended_at)
    return max(0, int((ended - started).total_seconds()))


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
