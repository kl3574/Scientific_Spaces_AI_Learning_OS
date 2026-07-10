from __future__ import annotations

from app.rag.service import NO_SOURCE_ANSWER
from app.tutor.models import TutorMode, TutorSource


def enforce_grounding(*, mode: TutorMode, answer: str, sources: list[TutorSource]) -> tuple[str, str | None]:
    if not sources:
        return NO_SOURCE_ANSWER, "no_sources"
    if mode in {"explain", "derive", "qa", "quiz", "research"} and not any(
        source.source_type == "article_chunk" for source in sources
    ):
        return NO_SOURCE_ANSWER, "no_sources"
    return answer, None


def refusal_response(mode: TutorMode, reason: str, message: str = NO_SOURCE_ANSWER) -> tuple[str, str]:
    return message, reason
