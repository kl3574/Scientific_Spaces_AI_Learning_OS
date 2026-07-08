from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    task_type: str
    question: str
    article_id: str | None = None
    node_id: str | None = None
    expected_source_article_ids: list[str] = field(default_factory=list)
    expected_refusal: bool = False
    expected_mode: str | None = None
    min_sources: int = 0
    notes: str | None = None
    top_k: int = 3
    expected_chunk_index: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalCase":
        return cls(
            case_id=str(data["case_id"]),
            task_type=str(data["task_type"]),
            question=str(data["question"]),
            article_id=data.get("article_id"),
            node_id=data.get("node_id"),
            expected_source_article_ids=[str(item) for item in data.get("expected_source_article_ids", [])],
            expected_refusal=bool(data.get("expected_refusal", False)),
            expected_mode=data.get("expected_mode"),
            min_sources=int(data.get("min_sources", 0)),
            notes=data.get("notes"),
            top_k=int(data.get("top_k", 3)),
            expected_chunk_index=data.get("expected_chunk_index"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "task_type": self.task_type,
            "question": self.question,
            "article_id": self.article_id,
            "node_id": self.node_id,
            "expected_source_article_ids": self.expected_source_article_ids,
            "expected_refusal": self.expected_refusal,
            "expected_mode": self.expected_mode,
            "min_sources": self.min_sources,
            "notes": self.notes,
            "top_k": self.top_k,
            "expected_chunk_index": self.expected_chunk_index,
        }


@dataclass(frozen=True)
class EvalDataset:
    articles: list[dict[str, Any]]
    cases: list[EvalCase]
    zotero_links: dict[str, Any] = field(default_factory=dict)
    graph_expected: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    task_type: str
    answer: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    refusal_reason: str | None = None
    mode: str | None = None
    follow_up_questions: list[str] = field(default_factory=list)
    quiz_questions: list[dict[str, Any]] = field(default_factory=list)
    graph_context: dict[str, Any] = field(default_factory=dict)
    zotero_context: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "task_type": self.task_type,
            "answer": self.answer,
            "sources": self.sources,
            "refusal_reason": self.refusal_reason,
            "mode": self.mode,
            "follow_up_questions": self.follow_up_questions,
            "quiz_questions": self.quiz_questions,
            "graph_context": self.graph_context,
            "zotero_context": self.zotero_context,
            "metrics": self.metrics,
        }


@dataclass(frozen=True)
class EvalMetricSummary:
    case_count: int
    retrieval_hit_at_k: float
    expected_article_hit: float
    expected_chunk_hit: float
    retrieved_source_count: int
    citation_required_pass_rate: float
    non_empty_sources_rate: float
    source_schema_valid_rate: float
    no_fake_source_rate: float
    no_source_refusal_rate: float
    unsupported_query_refusal_rate: float
    explain_grounded_rate: float
    derive_refusal_when_insufficient_rate: float
    qa_sources_required_rate: float
    quiz_question_sources_rate: float
    research_local_only_rate: float
    no_source_answer_fabrication_count: int
    answer_without_sources_count: int
    quiz_without_sources_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_count": self.case_count,
            "retrieval_hit_at_k": self.retrieval_hit_at_k,
            "expected_article_hit": self.expected_article_hit,
            "expected_chunk_hit": self.expected_chunk_hit,
            "retrieved_source_count": self.retrieved_source_count,
            "citation_required_pass_rate": self.citation_required_pass_rate,
            "non_empty_sources_rate": self.non_empty_sources_rate,
            "source_schema_valid_rate": self.source_schema_valid_rate,
            "no_fake_source_rate": self.no_fake_source_rate,
            "no_source_refusal_rate": self.no_source_refusal_rate,
            "unsupported_query_refusal_rate": self.unsupported_query_refusal_rate,
            "explain_grounded_rate": self.explain_grounded_rate,
            "derive_refusal_when_insufficient_rate": self.derive_refusal_when_insufficient_rate,
            "qa_sources_required_rate": self.qa_sources_required_rate,
            "quiz_question_sources_rate": self.quiz_question_sources_rate,
            "research_local_only_rate": self.research_local_only_rate,
            "no_source_answer_fabrication_count": self.no_source_answer_fabrication_count,
            "answer_without_sources_count": self.answer_without_sources_count,
            "quiz_without_sources_count": self.quiz_without_sources_count,
        }


@dataclass(frozen=True)
class EvalSuiteResult:
    results: list[EvalResult]
    metrics: EvalMetricSummary
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "metrics": self.metrics.to_dict(),
            "results": [result.to_dict() for result in self.results],
        }
