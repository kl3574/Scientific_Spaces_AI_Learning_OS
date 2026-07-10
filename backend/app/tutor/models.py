from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

TutorMode = Literal["explain", "derive", "qa", "quiz", "research"]
TutorSourceType = Literal["article_chunk", "graph_node", "graph_edge", "zotero_item", "learning_state", "article_metadata"]


@dataclass(frozen=True)
class SelectionSummary:
    candidate_count: int = 0
    selected_article_count: int = 0
    selected_chunk_count: int = 0
    graph_node_count: int = 0
    graph_edge_count: int = 0
    graph_latency_ms: float | None = None
    graph_error_code: str | None = None
    context_character_count: int = 0
    estimated_token_count: int = 0
    truncated: bool = False
    supplement_omitted_count: int = 0


@dataclass(frozen=True)
class EvidenceSummary:
    source_count: int = 0
    article_count: int = 0
    has_formula_evidence: bool = False
    has_definition_evidence: bool = False
    has_answerable_evidence: bool = False
    source_schema_valid: bool = False
    unsupported_or_out_of_scope: bool = False
    refusal_reason: str | None = None


@dataclass(frozen=True)
class TutorSource:
    source_type: TutorSourceType
    source_id: str
    title: str
    url: str | None = None
    section_title: str | None = None
    chunk_index: int | None = None
    evidence: dict[str, Any] | str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "section_title": self.section_title,
            "chunk_index": self.chunk_index,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class TutorRequest:
    question: str
    mode: TutorMode
    article_id: str | None = None
    node_id: str | None = None
    top_k: int = 5
    include_graph_context: bool = True
    include_zotero_context: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "mode": self.mode,
            "article_id": self.article_id,
            "node_id": self.node_id,
            "top_k": self.top_k,
            "include_graph_context": self.include_graph_context,
            "include_zotero_context": self.include_zotero_context,
        }


@dataclass(frozen=True)
class TutorResponse:
    answer: str
    mode: TutorMode
    sources: list[TutorSource]
    graph_context: dict[str, Any] = field(default_factory=dict)
    zotero_context: list[dict[str, Any]] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)
    refusal_reason: str | None = None
    selection_summary: SelectionSummary = field(default_factory=SelectionSummary)
    evidence_summary: EvidenceSummary = field(default_factory=EvidenceSummary)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "mode": self.mode,
            "sources": [source.to_dict() for source in self.sources],
            "graph_context": self.graph_context,
            "zotero_context": self.zotero_context,
            "follow_up_questions": self.follow_up_questions,
            "refusal_reason": self.refusal_reason,
            "selection_summary": {
                "candidate_count": self.selection_summary.candidate_count,
                "selected_article_count": self.selection_summary.selected_article_count,
                "selected_chunk_count": self.selection_summary.selected_chunk_count,
                "graph_node_count": self.selection_summary.graph_node_count,
                "graph_edge_count": self.selection_summary.graph_edge_count,
                "graph_latency_ms": self.selection_summary.graph_latency_ms,
                "graph_error_code": self.selection_summary.graph_error_code,
                "context_character_count": self.selection_summary.context_character_count,
                "estimated_token_count": self.selection_summary.estimated_token_count,
                "truncated": self.selection_summary.truncated,
                "supplement_omitted_count": self.selection_summary.supplement_omitted_count,
            },
            "evidence_summary": {
                "source_count": self.evidence_summary.source_count,
                "article_count": self.evidence_summary.article_count,
                "has_formula_evidence": self.evidence_summary.has_formula_evidence,
                "has_definition_evidence": self.evidence_summary.has_definition_evidence,
                "has_answerable_evidence": self.evidence_summary.has_answerable_evidence,
                "source_schema_valid": self.evidence_summary.source_schema_valid,
                "unsupported_or_out_of_scope": self.evidence_summary.unsupported_or_out_of_scope,
                "refusal_reason": self.evidence_summary.refusal_reason,
            },
        }


@dataclass(frozen=True)
class QuizQuestion:
    question: str
    options: list[str] | None
    correct_answer: str
    explanation: str
    sources: list[TutorSource]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "options": self.options,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "sources": [source.to_dict() for source in self.sources],
        }


@dataclass(frozen=True)
class TutorTurn:
    question: str
    mode: TutorMode
    answer: str
    sources: list[dict[str, Any]]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "mode": self.mode,
            "answer": self.answer,
            "sources": self.sources,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class TutorSession:
    session_id: str
    mode: TutorMode
    article_id: str | None
    node_id: str | None
    created_at: str
    updated_at: str
    turns: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "article_id": self.article_id,
            "node_id": self.node_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turns": self.turns,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TutorSession":
        return cls(
            session_id=str(data["session_id"]),
            mode=data["mode"],
            article_id=data.get("article_id"),
            node_id=data.get("node_id"),
            created_at=str(data["created_at"]),
            updated_at=str(data["updated_at"]),
            turns=list(data.get("turns") or []),
        )
