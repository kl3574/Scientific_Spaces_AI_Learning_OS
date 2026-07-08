from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

LearningStatus = Literal["unread", "reading", "completed"]
SessionSource = Literal["reader", "rag"]


@dataclass(frozen=True)
class LearningState:
    article_id: str
    status: LearningStatus
    last_read_at: str | None
    completed_at: str | None
    read_count: int
    updated_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "status": self.status,
            "last_read_at": self.last_read_at,
            "completed_at": self.completed_at,
            "read_count": self.read_count,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class Bookmark:
    article_id: str
    title: str
    url: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "title": self.title,
            "url": self.url,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class LearningNote:
    note_id: str
    article_id: str
    content: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "note_id": self.note_id,
            "article_id": self.article_id,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class LearningSession:
    session_id: str
    article_id: str
    started_at: str
    ended_at: str | None
    duration_seconds: int | None
    source: SessionSource

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "article_id": self.article_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "source": self.source,
        }
