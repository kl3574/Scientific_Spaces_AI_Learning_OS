from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.evaluation.models import EvalCase, EvalMetricSummary, EvalResult

NO_SOURCE_MARKERS = (
    "无法基于当前资料回答",
    "无法基于当前资料形成可靠研究建议",
    "当前资料不足以完整推导",
)
ARTICLE_SOURCE_TYPES = {None, "article_chunk"}
SUPPLEMENTAL_SOURCE_TYPES = {"graph_node", "graph_edge", "zotero_item", "article_metadata"}


@dataclass(frozen=True)
class MetricInputs:
    cases: list[EvalCase]
    results: list[EvalResult]
    valid_article_ids: set[str]


def source_article_id(source: dict[str, Any]) -> str | None:
    direct = source.get("article_id")
    if direct:
        return str(direct)
    metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    metadata_article_id = metadata.get("article_id")
    if metadata_article_id:
        return str(metadata_article_id)
    source_type = source.get("source_type")
    source_id = source.get("source_id")
    if source_type == "article_chunk" and source_id:
        return str(source_id).split(":", 1)[0]
    return None


def has_valid_source_schema(source: dict[str, Any]) -> bool:
    source_type = source.get("source_type")
    if source_type in ARTICLE_SOURCE_TYPES and source_article_id(source):
        title = source.get("article_title") or source.get("title")
        url = source.get("article_url") or source.get("url")
        section = source.get("section_title")
        return bool(title and url and section and isinstance(source.get("chunk_index"), int))

    if source_type in SUPPLEMENTAL_SOURCE_TYPES:
        return bool(source.get("source_id") and source.get("title"))

    return False


def expected_article_hit(sources: list[dict[str, Any]], expected_article_ids: Iterable[str]) -> bool:
    expected = {str(item) for item in expected_article_ids}
    if not expected:
        return True
    actual = {article_id for source in sources if (article_id := source_article_id(source))}
    return bool(actual & expected)


def retrieval_hit_at_k(sources: list[dict[str, Any]], expected_article_ids: Iterable[str], *, k: int) -> bool:
    return expected_article_hit(sources[: max(0, k)], expected_article_ids)


def expected_chunk_hit(sources: list[dict[str, Any]], expected_chunk_index: int | None) -> bool:
    if expected_chunk_index is None:
        return True
    return any(source.get("chunk_index") == expected_chunk_index for source in sources)


def is_refusal(answer: str, refusal_reason: str | None) -> bool:
    if refusal_reason:
        return True
    return any(marker in answer for marker in NO_SOURCE_MARKERS)


def quiz_questions_have_sources(quiz_questions: list[dict[str, Any]]) -> bool:
    if not quiz_questions:
        return False
    return all(question.get("sources") for question in quiz_questions)


def no_fake_sources(sources: list[dict[str, Any]], valid_article_ids: set[str]) -> bool:
    for source in sources:
        source_type = source.get("source_type")
        article_id = source_article_id(source)
        if source_type in ARTICLE_SOURCE_TYPES and article_id not in valid_article_ids:
            return False
        if source_type not in ARTICLE_SOURCE_TYPES and source_type not in SUPPLEMENTAL_SOURCE_TYPES:
            return False
    return True


def result_case_metrics(case: EvalCase, result: EvalResult, valid_article_ids: set[str]) -> dict[str, Any]:
    citation_required = (not case.expected_refusal) and case.min_sources > 0 and len(result.sources) >= case.min_sources
    refusal = is_refusal(result.answer, result.refusal_reason)
    refusal_correct = refusal if case.expected_refusal else not refusal
    return {
        "expected_article_hit": expected_article_hit(result.sources, case.expected_source_article_ids),
        "retrieval_hit_at_k": retrieval_hit_at_k(
            result.sources,
            case.expected_source_article_ids,
            k=max(1, case.top_k),
        ),
        "expected_chunk_hit": expected_chunk_hit(result.sources, case.expected_chunk_index),
        "citation_required": citation_required,
        "non_empty_sources": bool(result.sources),
        "source_schema_valid": all(has_valid_source_schema(source) for source in result.sources),
        "no_fake_source": no_fake_sources(result.sources, valid_article_ids),
        "expected_refusal": case.expected_refusal,
        "refusal_correct": refusal_correct,
        "quiz_questions_have_sources": quiz_questions_have_sources(result.quiz_questions),
        "research_local_only": _research_local_only(result),
    }


def calculate_suite_metrics(inputs: MetricInputs) -> EvalMetricSummary:
    results_by_case = {result.case_id: result for result in inputs.results}
    paired = [(case, results_by_case[case.case_id]) for case in inputs.cases if case.case_id in results_by_case]
    case_metric_rows = [
        result.metrics or result_case_metrics(case, result, inputs.valid_article_ids)
        for case, result in paired
    ]

    expected_source_rows = [
        row for case, row in zip((case for case, _ in paired), case_metric_rows) if case.expected_source_article_ids
    ]
    source_required_rows = [
        row
        for case, row in zip((case for case, _ in paired), case_metric_rows)
        if (not case.expected_refusal) and case.min_sources > 0
    ]
    results_with_sources = [row for row, result in zip(case_metric_rows, (result for _, result in paired)) if result.sources]
    no_source_rows = [
        row for case, row in zip((case for case, _ in paired), case_metric_rows) if case.expected_refusal
    ]
    explain_rows = _mode_rows(paired, case_metric_rows, "tutor_explain", expected_refusal=False)
    derive_insufficient_rows = _mode_rows(paired, case_metric_rows, "tutor_derive", expected_refusal=True)
    qa_rows = _mode_rows(paired, case_metric_rows, "tutor_qa", expected_refusal=False)
    quiz_rows = _mode_rows(paired, case_metric_rows, "tutor_quiz", expected_refusal=False)
    research_rows = _mode_rows(paired, case_metric_rows, "tutor_research", expected_refusal=False)

    no_source_fabrications = 0
    answer_without_sources = 0
    quiz_without_sources = 0
    for case, result in paired:
        refusal = is_refusal(result.answer, result.refusal_reason)
        if case.expected_refusal and not refusal:
            no_source_fabrications += 1
        if (not case.expected_refusal) and case.min_sources > 0 and not result.sources:
            answer_without_sources += 1
        if case.task_type == "tutor_quiz" and not quiz_questions_have_sources(result.quiz_questions):
            quiz_without_sources += 1

    return EvalMetricSummary(
        case_count=len(paired),
        retrieval_hit_at_k=_rate(row["retrieval_hit_at_k"] for row in expected_source_rows),
        expected_article_hit=_rate(row["expected_article_hit"] for row in expected_source_rows),
        expected_chunk_hit=_rate(row["expected_chunk_hit"] for row in case_metric_rows),
        retrieved_source_count=sum(len(result.sources) for _, result in paired),
        citation_required_pass_rate=_rate(row["citation_required"] for row in source_required_rows),
        non_empty_sources_rate=_rate(row["non_empty_sources"] for row in source_required_rows),
        source_schema_valid_rate=_rate(row["source_schema_valid"] for row in results_with_sources),
        no_fake_source_rate=_rate(row["no_fake_source"] for row in case_metric_rows),
        no_source_refusal_rate=_rate(row["refusal_correct"] for row in no_source_rows),
        unsupported_query_refusal_rate=_rate(row["refusal_correct"] for row in no_source_rows),
        explain_grounded_rate=_rate(row["citation_required"] and row["source_schema_valid"] for row in explain_rows),
        derive_refusal_when_insufficient_rate=_rate(row["refusal_correct"] for row in derive_insufficient_rows),
        qa_sources_required_rate=_rate(row["citation_required"] for row in qa_rows),
        quiz_question_sources_rate=_rate(row["quiz_questions_have_sources"] for row in quiz_rows),
        research_local_only_rate=_rate(row["research_local_only"] for row in research_rows),
        no_source_answer_fabrication_count=no_source_fabrications,
        answer_without_sources_count=answer_without_sources,
        quiz_without_sources_count=quiz_without_sources,
    )


def _mode_rows(
    paired: list[tuple[EvalCase, EvalResult]],
    rows: list[dict[str, Any]],
    task_type: str,
    *,
    expected_refusal: bool,
) -> list[dict[str, Any]]:
    return [
        row
        for (case, _result), row in zip(paired, rows)
        if case.task_type == task_type and case.expected_refusal is expected_refusal
    ]


def _rate(values: Iterable[bool]) -> float:
    items = list(values)
    if not items:
        return 1.0
    return sum(1 for item in items if item) / len(items)


def _research_local_only(result: EvalResult) -> bool:
    if result.task_type != "tutor_research":
        return True
    text = result.answer
    return "仅基于本地" in text and "不能视为完整文献综述" in text and bool(result.sources)
