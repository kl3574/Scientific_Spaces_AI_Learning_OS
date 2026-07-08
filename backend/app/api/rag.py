from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.rag.service import get_rag_service

router = APIRouter(prefix="/rag")


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/index")
def build_rag_index() -> dict[str, int]:
    return get_rag_service().build_index()


@router.post("/query")
def query_rag(request: RagQueryRequest) -> dict[str, object]:
    return get_rag_service().answer(question=request.question, top_k=request.top_k)
