from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.learning.models import LearningStatus, SessionSource
from app.learning.sqlite_store import LearningSQLiteStore
from app.learning.store import LearningStore, learning_store_path
from app.persistence.config import database_path, learning_backend
from app.services.article_reader import get_article, list_articles

router = APIRouter(prefix="/learning")


class LearningStateUpdate(BaseModel):
    status: LearningStatus


class NoteWrite(BaseModel):
    content: str = Field(min_length=1)


class SessionCreate(BaseModel):
    article_id: str = Field(min_length=1)
    source: SessionSource = "reader"


def get_learning_store() -> LearningStore | LearningSQLiteStore:
    if learning_backend() == "sqlite":
        return LearningSQLiteStore(database_path())
    return LearningStore(learning_store_path())


@router.get("/state")
def list_learning_states() -> dict[str, object]:
    states = [state.to_dict() for state in get_learning_store().list_states()]
    return {"items": states, "total": len(states)}


@router.get("/state/{article_id}")
def get_learning_state(article_id: str) -> dict[str, object]:
    return get_learning_store().get_state(article_id).to_dict()


@router.put("/state/{article_id}")
def update_learning_state(article_id: str, request: LearningStateUpdate) -> dict[str, object]:
    return get_learning_store().update_state(article_id, request.status).to_dict()


@router.get("/bookmarks")
def list_bookmarks() -> dict[str, object]:
    bookmarks = [bookmark.to_dict() for bookmark in get_learning_store().list_bookmarks()]
    return {"items": bookmarks, "total": len(bookmarks)}


@router.post("/bookmarks/{article_id}")
def add_bookmark(article_id: str) -> dict[str, object]:
    article = get_article(article_id)
    title = article.title if article else article_id
    url = article.url if article else ""
    return get_learning_store().add_bookmark(article_id=article_id, title=title, url=url).to_dict()


@router.delete("/bookmarks/{article_id}", status_code=204)
def delete_bookmark(article_id: str) -> Response:
    get_learning_store().delete_bookmark(article_id)
    return Response(status_code=204)


@router.get("/notes/{article_id}")
def list_notes(article_id: str) -> dict[str, object]:
    notes = [note.to_dict() for note in get_learning_store().list_notes(article_id)]
    return {"items": notes, "total": len(notes)}


@router.post("/notes/{article_id}")
def create_note(article_id: str, request: NoteWrite) -> dict[str, object]:
    return get_learning_store().create_note(article_id=article_id, content=request.content).to_dict()


@router.put("/notes/{note_id}")
def update_note(note_id: str, request: NoteWrite) -> dict[str, object]:
    note = get_learning_store().update_note(note_id=note_id, content=request.content)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note.to_dict()


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: str) -> Response:
    get_learning_store().delete_note(note_id)
    return Response(status_code=204)


@router.post("/sessions")
def create_session(request: SessionCreate) -> dict[str, object]:
    return get_learning_store().create_session(article_id=request.article_id, source=request.source).to_dict()


@router.put("/sessions/{session_id}/end")
def end_session(session_id: str) -> dict[str, object]:
    session = get_learning_store().end_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@router.get("/sessions")
def list_sessions() -> dict[str, object]:
    sessions = [session.to_dict() for session in get_learning_store().list_sessions()]
    return {"items": sessions, "total": len(sessions)}


@router.get("/stats")
def learning_stats() -> dict[str, object]:
    articles = list_articles()
    article_map = {article.id: article for article in articles}
    store = get_learning_store()
    states = store.list_states()
    bookmarks = store.list_bookmarks()
    sessions = store.list_sessions()

    reading_count = sum(1 for state in states if state.status == "reading")
    completed_count = sum(1 for state in states if state.status == "completed")
    unread_count = max(0, len(articles) - reading_count - completed_count)

    recent_states = sorted(
        (state for state in states if state.updated_at or state.last_read_at),
        key=lambda state: state.last_read_at or state.updated_at or "",
        reverse=True,
    )[:5]
    recent_articles = [
        _recent_article(state.article_id, state.status, state.last_read_at, state.updated_at, article_map)
        for state in recent_states
    ]

    return {
        "total_articles": len(articles),
        "unread_count": unread_count,
        "reading_count": reading_count,
        "completed_count": completed_count,
        "bookmark_count": len(bookmarks),
        "note_count": store.count_notes(),
        "recent_articles": recent_articles,
        "recent_sessions": [session.to_dict() for session in sessions[:5]],
    }


def _recent_article(
    article_id: str,
    status: Literal["unread", "reading", "completed"],
    last_read_at: str | None,
    updated_at: str | None,
    article_map: dict[str, object],
) -> dict[str, object]:
    article = article_map.get(article_id)
    return {
        "article_id": article_id,
        "title": getattr(article, "title", article_id),
        "url": getattr(article, "url", ""),
        "status": status,
        "last_read_at": last_read_at,
        "updated_at": updated_at,
    }
