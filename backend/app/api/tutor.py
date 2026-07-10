from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.tutor.models import TutorMode, TutorRequest
from app.tutor.service import TutorIndexUnavailable, TutorService
from app.tutor.store import TutorSessionStore

router = APIRouter(prefix="/tutor")


class TutorAskRequest(BaseModel):
    question: str = Field(min_length=1)
    mode: TutorMode = "explain"
    article_id: str | None = None
    node_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    include_graph_context: bool = True
    include_zotero_context: bool = True


class TutorQuizRequest(BaseModel):
    article_id: str | None = None
    node_id: str | None = None
    topic: str | None = None
    num_questions: int = Field(default=3, ge=1, le=10)


class TutorSessionCreate(BaseModel):
    mode: TutorMode = "qa"
    article_id: str | None = None
    node_id: str | None = None


def get_tutor_service() -> TutorService:
    return TutorService()


def get_tutor_store() -> TutorSessionStore:
    return TutorSessionStore()


@router.post("/ask")
def ask_tutor(request: TutorAskRequest) -> dict[str, object]:
    tutor_request = TutorRequest(
        question=request.question,
        mode=request.mode,
        article_id=request.article_id,
        node_id=request.node_id,
        top_k=request.top_k,
        include_graph_context=request.include_graph_context,
        include_zotero_context=request.include_zotero_context,
    )
    try:
        return get_tutor_service().answer(tutor_request).to_dict()
    except TutorIndexUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/quiz")
def tutor_quiz(request: TutorQuizRequest) -> dict[str, object]:
    try:
        questions = get_tutor_service().quiz(
            article_id=request.article_id,
            node_id=request.node_id,
            topic=request.topic,
            num_questions=request.num_questions,
        )
    except TutorIndexUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"questions": [question.to_dict() for question in questions], "total": len(questions)}


@router.get("/sessions")
def list_tutor_sessions() -> dict[str, object]:
    sessions = [session.to_dict() for session in get_tutor_store().list_sessions()]
    return {"items": sessions, "total": len(sessions)}


@router.post("/sessions")
def create_tutor_session(request: TutorSessionCreate) -> dict[str, object]:
    return get_tutor_store().create_session(
        mode=request.mode,
        article_id=request.article_id,
        node_id=request.node_id,
    ).to_dict()


@router.get("/sessions/{session_id}")
def get_tutor_session(session_id: str) -> dict[str, object]:
    session = get_tutor_store().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Tutor session not found")
    return session.to_dict()
