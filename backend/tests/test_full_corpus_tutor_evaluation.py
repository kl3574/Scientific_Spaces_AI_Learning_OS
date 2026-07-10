from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from app.tutor.models import EvidenceSummary, QuizQuestion, SelectionSummary, TutorResponse, TutorSource


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "evaluation" / "full_corpus_tutor_cases.json"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _source(article_id: str = "article-a") -> TutorSource:
    return TutorSource(
        source_type="article_chunk",
        source_id=f"{article_id}:0",
        title="Safe title",
        url="https://spaces.example/article-a",
        section_title="Safe section",
        chunk_index=0,
    )


class _FakeTutorService:
    def __init__(self) -> None:
        self.requests = []

    def answer(self, request):
        self.requests.append(request)
        if request.mode == "research":
            answer = "仅基于本地语料；资料缺口：未覆盖外部文献。"
        elif request.question.startswith("unsupported"):
            return TutorResponse(
                answer="无法基于当前资料回答。",
                mode=request.mode,
                sources=[],
                refusal_reason="no_sources",
                selection_summary=SelectionSummary(),
                evidence_summary=EvidenceSummary(
                    source_schema_valid=True,
                    unsupported_or_out_of_scope=True,
                    refusal_reason="unsupported_query",
                ),
            )
        else:
            answer = "Grounded answer."
        graph_context = {"nodes": [], "edges": []}
        if request.node_id:
            graph_context = {
                "nodes": [
                    {
                        "node_id": request.node_id,
                        "node_type": "concept",
                        "label": "attention",
                        "metadata": {
                            "source_count": 21,
                            "truncated": True,
                            "sources": [{"article_id": "a"}, {"article_id": "b"}],
                        },
                    },
                ],
                "edges": [{"edge_id": "edge:test"}],
            }
        sources = [_source(request.article_id or "article-a")]
        if request.mode == "research":
            sources.append(_source("article-b"))
        return TutorResponse(
            answer=answer,
            mode=request.mode,
            sources=sources,
            graph_context=graph_context,
            selection_summary=SelectionSummary(
                candidate_count=2,
                selected_article_count=len(sources),
                selected_chunk_count=len(sources),
                graph_node_count=len(graph_context["nodes"]),
                graph_edge_count=len(graph_context["edges"]),
                graph_latency_ms=0.5,
                context_character_count=120,
                estimated_token_count=30,
                truncated=False,
            ),
            evidence_summary=EvidenceSummary(
                source_count=len(sources),
                article_count=len(sources),
                has_formula_evidence=True,
                has_definition_evidence=True,
                has_answerable_evidence=True,
                source_schema_valid=True,
            ),
        )

    def quiz(self, *, article_id=None, node_id=None, topic=None, num_questions=3):
        source = _source(article_id or "article-a")
        return [
            QuizQuestion(
                question=f"{topic} evidence question {index + 1}",
                options=None,
                correct_answer="Answer not persisted",
                explanation="Explanation not persisted",
                sources=[source],
            )
            for index in range(min(num_questions, 2))
        ]


def _case(
    case_id: str,
    mode: str,
    *,
    unsupported: bool = False,
    expected_refusal: bool | None = None,
    node_id: str | None = None,
):
    from app.evaluation.tutor_full_corpus import FullCorpusTutorCase

    expects_refusal = unsupported if expected_refusal is None else expected_refusal
    return FullCorpusTutorCase(
        case_id=case_id,
        mode=mode,
        question=(
            "unsupported question"
            if unsupported
            else "derive refusal question"
            if expects_refusal
            else "Sensitive question not persisted"
        ),
        expected_article_ids=("article-a",),
        min_sources=0 if expects_refusal else 1,
        max_sources=6,
        expected_evidence_type="unsupported" if unsupported else "article",
        expected_refusal=expects_refusal,
        unsupported=unsupported,
        article_id="article-a",
        node_id=node_id,
        expected_question_count=2 if mode == "quiz" else None,
    )


def _canonical_cases():
    from app.evaluation.tutor_full_corpus import FullCorpusTutorCase

    cases = []
    counts = {"explain": 8, "derive": 8, "qa": 8, "quiz": 8, "research": 6, "unsupported": 4}
    for mode, count in counts.items():
        for index in range(count):
            unsupported = mode == "unsupported"
            derive_refusal = mode == "derive" and index >= 5
            expected_refusal = unsupported or derive_refusal
            question = f"{mode} supported question {index}"
            if unsupported:
                question = f"unsupported question {index}"
            elif derive_refusal:
                question = f"derive refusal question {index}"
            cases.append(
                FullCorpusTutorCase(
                    case_id=f"{mode}-{index}",
                    mode=mode,
                    question=question,
                    expected_article_ids=() if unsupported else ("expected-article",),
                    min_sources=0 if expected_refusal else (2 if mode == "research" else 1),
                    max_sources=10,
                    expected_evidence_type=(
                        "unsupported"
                        if unsupported
                        else "multi_article"
                        if mode == "research"
                        else "formula"
                        if mode == "derive"
                        else "article"
                    ),
                    expected_refusal=expected_refusal,
                    unsupported=unsupported,
                    article_id=None if mode in {"research", "unsupported"} else "actual-article",
                    node_id="concept:attention" if mode == "explain" and index == 0 else None,
                    expected_question_count=2 if mode == "quiz" else None,
                )
            )
    return cases


class _ContractTutorService:
    def __init__(self) -> None:
        self.requests = []
        self.quiz_requests = []

    def answer(self, request):
        self.requests.append(request)
        if request.question.startswith("unsupported"):
            return TutorResponse(
                answer="无法基于当前资料回答。",
                mode=request.mode,
                sources=[],
                refusal_reason="no_sources",
                selection_summary=SelectionSummary(),
                evidence_summary=EvidenceSummary(
                    source_schema_valid=True,
                    unsupported_or_out_of_scope=True,
                    refusal_reason="unsupported_query",
                ),
            )
        if request.question.startswith("derive refusal"):
            source = _source("actual-article")
            return TutorResponse(
                answer="当前资料不足以完整推导。",
                mode=request.mode,
                sources=[source],
                refusal_reason="insufficient_formula_sources",
                selection_summary=SelectionSummary(
                    selected_article_count=1,
                    selected_chunk_count=1,
                ),
                evidence_summary=EvidenceSummary(
                    source_count=1,
                    article_count=1,
                    has_answerable_evidence=True,
                    source_schema_valid=True,
                    refusal_reason="insufficient_formula_evidence",
                ),
            )

        article_sources = [_source("actual-article")]
        if request.mode == "research":
            article_sources.append(_source("second-actual-article"))
            answer = "仅基于本地语料；资料缺口：未覆盖外部文献。"
        else:
            answer = "Grounded answer."
        graph_context = {"nodes": [], "edges": []}
        if request.node_id:
            graph_context = {
                "nodes": [
                    {
                        "node_id": request.node_id,
                        "node_type": "concept",
                        "label": "attention",
                        "metadata": {
                            "source_count": 21,
                            "truncated": True,
                            "sources": [{"article_id": "a"}, {"article_id": "b"}],
                        },
                    },
                ],
                "edges": [],
            }
        return TutorResponse(
            answer=answer,
            mode=request.mode,
            sources=article_sources,
            graph_context=graph_context,
            selection_summary=SelectionSummary(
                candidate_count=len(article_sources),
                selected_article_count=len(article_sources),
                selected_chunk_count=len(article_sources),
                graph_node_count=len(graph_context["nodes"]),
                context_character_count=120,
                estimated_token_count=30,
            ),
            evidence_summary=EvidenceSummary(
                source_count=len(article_sources),
                article_count=len(article_sources),
                has_formula_evidence=request.mode == "derive",
                has_definition_evidence=True,
                has_answerable_evidence=True,
                source_schema_valid=True,
            ),
        )

    def quiz(self, *, article_id=None, node_id=None, topic=None, num_questions=3):
        self.quiz_requests.append(num_questions)
        if topic and topic.startswith("empty quiz"):
            return []
        sources = [] if topic and topic.startswith("unsourced quiz") else [_source(article_id or "actual-article")]
        return [
            QuizQuestion(
                question=f"{topic} evidence question {index + 1}",
                options=None,
                correct_answer="Answer not persisted",
                explanation="Explanation not persisted",
                sources=sources,
            )
            for index in range(num_questions)
        ]


def _minimal_runner_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    article_store = tmp_path / "articles.json"
    rag_index = tmp_path / "rag-index"
    graph_dir = tmp_path / "graph"
    article_store.write_text("[]", encoding="utf-8")
    rag_index.mkdir()
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text("{}", encoding="utf-8")
    return article_store, rag_index, graph_dir


def test_loader_requires_the_committed_42_case_distribution(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorFixtureError, load_full_corpus_tutor_cases

    cases = load_full_corpus_tutor_cases(FIXTURE_PATH)

    assert len(cases) == 42
    assert {case.mode for case in cases} == {"explain", "derive", "qa", "quiz", "research", "unsupported"}

    invalid_fixture = tmp_path / "invalid.json"
    invalid_fixture.write_text(json.dumps([cases[0].to_dict()]), encoding="utf-8")
    with pytest.raises(FullCorpusTutorFixtureError, match="expected 42 cases"):
        load_full_corpus_tutor_cases(invalid_fixture)

    wrong_distribution = [case.to_dict() for case in cases]
    wrong_distribution[-1]["mode"] = "explain"
    wrong_distribution[-1]["unsupported"] = False
    wrong_distribution[-1]["expected_refusal"] = False
    invalid_fixture.write_text(json.dumps(wrong_distribution), encoding="utf-8")
    with pytest.raises(FullCorpusTutorFixtureError, match="invalid 42-case distribution"):
        load_full_corpus_tutor_cases(invalid_fixture)


def test_loader_requires_exact_derive_refusals_and_explicit_attention_node() -> None:
    from app.evaluation.tutor_full_corpus import load_full_corpus_tutor_cases

    cases = load_full_corpus_tutor_cases(FIXTURE_PATH)

    assert sum(case.mode == "derive" and case.expected_refusal for case in cases) == 3
    assert [case.case_id for case in cases if case.node_id == "concept:attention"]
    quiz_cases = [case for case in cases if case.mode == "quiz"]
    assert len(quiz_cases) == 8
    assert all(case.expected_question_count == 2 for case in quiz_cases)
    assert all("2 题" in case.question for case in quiz_cases)
    albert_electra = next(case for case in cases if case.case_id == "P2-004-QA-03")
    assert albert_electra.expected_evidence_type == "article"


def test_loader_requires_expected_question_count_only_for_quiz_cases(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorFixtureError, load_full_corpus_tutor_cases

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    quiz_case = next(item for item in payload if item["mode"] == "quiz")
    quiz_case.pop("expected_question_count")
    fixture = tmp_path / "quiz-count-missing.json"
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(FullCorpusTutorFixtureError, match="Quiz.*expected_question_count"):
        load_full_corpus_tutor_cases(fixture)

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    non_quiz_case = next(item for item in payload if item["mode"] != "quiz")
    non_quiz_case["expected_question_count"] = 2
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(FullCorpusTutorFixtureError, match="only Quiz.*expected_question_count"):
        load_full_corpus_tutor_cases(fixture)

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    quiz_case = next(item for item in payload if item["mode"] == "quiz")
    quiz_case["expected_question_count"] = True
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(FullCorpusTutorFixtureError, match="expected_question_count.*integer"):
        load_full_corpus_tutor_cases(fixture)


@pytest.mark.parametrize(
    "extra_field",
    ["body", "content", "answer", "snippet", "chunk", "candidate", "url", "path"],
)
def test_loader_rejects_all_non_metadata_case_fields(tmp_path: Path, extra_field: str) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorFixtureError, load_full_corpus_tutor_cases

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload[0][extra_field] = "forbidden"
    fixture = tmp_path / "extra-field.json"
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(FullCorpusTutorFixtureError, match="unexpected|metadata-only"):
        load_full_corpus_tutor_cases(fixture)


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "https://example.invalid/private",
        "/tmp/private/corpus.json",
        r"C:\\private\\corpus.json",
        r"\\\\server\\share\\corpus.json",
        "../private/corpus.json",
        r"..\\private\\corpus.json",
    ],
)
def test_loader_rejects_urls_and_local_paths_in_any_string_field(tmp_path: Path, unsafe_value: str) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorFixtureError, load_full_corpus_tutor_cases

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload[0]["question"] = unsafe_value
    fixture = tmp_path / "unsafe-value.json"
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(FullCorpusTutorFixtureError, match="URL|path|metadata-only"):
        load_full_corpus_tutor_cases(fixture)


def test_loader_rejects_any_derive_refusal_count_other_than_three(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorFixtureError, load_full_corpus_tutor_cases

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    extra_refusal = next(item for item in payload if item["mode"] == "derive" and not item["expected_refusal"])
    extra_refusal["expected_refusal"] = True
    extra_refusal["min_sources"] = 0
    fixture = tmp_path / "derive-refusals.json"
    fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(FullCorpusTutorFixtureError, match="exactly 3 Derive"):
        load_full_corpus_tutor_cases(fixture)


def test_fake_local_runner_aggregates_safe_metrics_and_writes_atomically(tmp_path: Path, monkeypatch) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    def reject_network(*_args, **_kwargs):
        raise AssertionError("the fake evaluation must not access the network")

    monkeypatch.setattr("urllib.request.urlopen", reject_network)
    article_store = tmp_path / "articles.json"
    rag_index = tmp_path / "rag-index"
    graph_dir = tmp_path / "graph"
    article_store.write_text("[]", encoding="utf-8")
    rag_index.mkdir()
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text("{}", encoding="utf-8")
    output_path = tmp_path / ".local_data" / "reports" / "summary.json"

    result = FullCorpusTutorEvaluationRunner(
        cases=[
            _case("qa-1", "qa", node_id="concept:attention"),
            _case("quiz-1", "quiz"),
            _case("research-1", "research"),
            _case("unsupported-1", "unsupported", unsupported=True),
        ],
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=_FakeTutorService,
    ).run(output_path=output_path)

    assert result["provider"] == "fake"
    assert result["input_kinds"] == {"article": 1, "rag": 1, "graph": 1}
    assert result["metrics"]["expected_article_recall"] == 1.0
    assert result["metrics"]["quiz_question_source_coverage"] == 1.0
    assert result["metrics"]["research_local_only_pass_rate"] == 1.0
    assert result["metrics"]["research_gap_rate"] == 1.0
    assert result["metrics"]["high_degree_concept_checked_count"] == 1
    assert result["metrics"]["high_degree_concept_overexpansion_count"] == 0
    assert result["timings_ms"]["tutor"]["count"] == 4
    assert output_path.is_file()
    assert not list(output_path.parent.glob(".summary.json.tmp-*"))

    persisted = output_path.read_text(encoding="utf-8")
    assert "Sensitive question" not in persisted
    assert "Grounded answer" not in persisted
    assert "Question not persisted" not in persisted
    assert "https://spaces.example" not in persisted
    assert "article-a:0" not in persisted
    assert "candidates" not in persisted


def test_expected_article_misses_are_diagnostic_and_all_hard_metrics_gate_pass(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    service = _ContractTutorService()
    result = FullCorpusTutorEvaluationRunner(
        cases=_canonical_cases(),
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=lambda: service,
    ).run()

    assert result["status"] == "PASS"
    assert result["hard_metric_failures"] == {}
    assert result["failed_case_ids"] == {}
    assert result["metrics"]["expected_article_hit_rate"] == 0.0
    assert result["metrics"]["expected_article_recall"] == 0.0
    assert result["diagnostic_case_ids"]["expected_article_miss_ids"]
    assert result["metrics"]["high_degree_concept_checked_count"] == 1
    assert result["metrics"]["high_degree_concept_overexpansion_count"] == 0
    assert result["metrics"]["source_diversity_rate"] < 1.0
    assert any(request.node_id == "concept:attention" for request in service.requests)
    assert all(request.node_id is None for request in service.requests if request.question != "explain supported question 0")
    assert service.quiz_requests == [2] * 8

    expected_thresholds = {
        "source_schema_valid_rate": 1.0,
        "source_title_present_rate": 1.0,
        "source_url_present_rate": 1.0,
        "supported_case_non_empty_source_rate": 1.0,
        "citation_required_pass_rate": 1.0,
        "no_source_refusal_rate": 1.0,
        "derive_insufficient_evidence_refusal_rate": 1.0,
        "unsupported_answer_fabrication_count": 0,
        "answer_without_sources_count": 0,
        "quiz_question_source_coverage": 1.0,
        "research_local_only_pass_rate": 1.0,
        "source_budget_violation_count": 0,
        "graph_budget_violation_count": 0,
        "high_degree_concept_overexpansion_count": 0,
        "expected_evidence_type_pass_rate": 1.0,
        "supported_derive_formula_evidence_rate": 1.0,
        "research_multi_article_evidence_rate": 1.0,
        "quiz_requested_question_count_pass_rate": 1.0,
        "quiz_normalized_unique_question_rate": 1.0,
        "quiz_topic_relevance_rate": 1.0,
        "quiz_source_mapping_rate": 1.0,
    }
    assert result["hard_metric_thresholds"] == expected_thresholds
    assert all(result["metrics"][name] == threshold for name, threshold in expected_thresholds.items())


def test_hard_metric_failure_blocks_status_even_without_case_level_exception(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    class MissingUrlTutorService(_ContractTutorService):
        def answer(self, request):
            response = super().answer(request)
            if response.sources and not response.refusal_reason:
                bad_sources = [replace(source, url=None) for source in response.sources]
                return replace(response, sources=bad_sources)
            return response

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    result = FullCorpusTutorEvaluationRunner(
        cases=_canonical_cases(),
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=MissingUrlTutorService,
    ).run()

    assert result["status"] == "BLOCKED"
    assert result["metrics"]["source_url_present_rate"] < 1.0
    assert result["hard_metric_failures"]["source_url_present_rate"] == {
        "actual": result["metrics"]["source_url_present_rate"],
        "required": 1.0,
    }


def test_supported_derive_requires_formula_evidence_and_expected_evidence_type(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    class MissingFormulaTutorService(_ContractTutorService):
        def answer(self, request):
            response = super().answer(request)
            if request.question == "derive supported question 0":
                return replace(
                    response,
                    evidence_summary=replace(response.evidence_summary, has_formula_evidence=False),
                )
            return response

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    result = FullCorpusTutorEvaluationRunner(
        cases=_canonical_cases(),
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=MissingFormulaTutorService,
    ).run()

    assert result["status"] == "BLOCKED"
    assert result["metrics"]["supported_derive_formula_evidence_rate"] == pytest.approx(4 / 5)
    assert "supported_derive_formula_evidence_rate" in result["hard_metric_failures"]
    assert result["failed_case_ids"]["supported_derive_formula_evidence_failure_ids"] == ["derive-0"]
    assert result["metrics"]["expected_evidence_type_pass_rate"] < 1.0
    assert result["failed_case_ids"]["expected_evidence_type_failure_ids"] == ["derive-0"]


@pytest.mark.parametrize(
    ("outward_reason", "internal_reason"),
    [
        ("no_sources", "insufficient_formula_evidence"),
        ("insufficient_formula_sources", "no_relevant_source"),
    ],
)
def test_derive_refusal_requires_exact_outward_and_internal_reasons(
    tmp_path: Path,
    outward_reason: str,
    internal_reason: str,
) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    class InvalidDeriveRefusalTutorService(_ContractTutorService):
        def answer(self, request):
            response = super().answer(request)
            if request.question == "derive refusal question 5":
                return replace(
                    response,
                    refusal_reason=outward_reason,
                    evidence_summary=replace(response.evidence_summary, refusal_reason=internal_reason),
                )
            return response

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    result = FullCorpusTutorEvaluationRunner(
        cases=_canonical_cases(),
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=InvalidDeriveRefusalTutorService,
    ).run()

    assert result["metrics"]["derive_insufficient_evidence_refusal_rate"] == pytest.approx(2 / 3)
    assert "derive_insufficient_evidence_refusal_rate" in result["hard_metric_failures"]
    assert result["failed_case_ids"]["derive_refusal_failure_ids"] == ["derive-5"]


def test_unsupported_refusal_requires_exact_outward_no_sources_reason(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    class InvalidUnsupportedRefusalTutorService(_ContractTutorService):
        def answer(self, request):
            response = super().answer(request)
            if request.question == "unsupported question 0":
                return replace(response, refusal_reason="unsupported_query")
            return response

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    result = FullCorpusTutorEvaluationRunner(
        cases=_canonical_cases(),
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=InvalidUnsupportedRefusalTutorService,
    ).run()

    assert result["metrics"]["no_source_refusal_rate"] == pytest.approx(3 / 4)
    assert "no_source_refusal_rate" in result["hard_metric_failures"]
    assert result["failed_case_ids"]["no_source_refusal_failure_ids"] == ["unsupported-0"]


def test_multi_article_research_requires_two_distinct_article_ids(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    class SingleArticleResearchTutorService(_ContractTutorService):
        def answer(self, request):
            response = super().answer(request)
            if request.question == "research supported question 0":
                return replace(
                    response,
                    sources=response.sources[:1],
                    selection_summary=replace(
                        response.selection_summary,
                        selected_article_count=1,
                        selected_chunk_count=1,
                    ),
                    evidence_summary=replace(response.evidence_summary, source_count=1, article_count=1),
                )
            return response

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    result = FullCorpusTutorEvaluationRunner(
        cases=_canonical_cases(),
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=SingleArticleResearchTutorService,
    ).run()

    assert result["metrics"]["research_multi_article_evidence_rate"] == pytest.approx(5 / 6)
    assert "research_multi_article_evidence_rate" in result["hard_metric_failures"]
    assert result["failed_case_ids"]["research_multi_article_evidence_failure_ids"] == ["research-0"]
    assert result["failed_case_ids"]["expected_evidence_type_failure_ids"] == ["research-0"]


def test_quiz_coverage_penalizes_empty_suites_and_identifies_each_unsourced_case(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    cases = _canonical_cases()
    first_quiz = next(index for index, case in enumerate(cases) if case.mode == "quiz")
    cases[first_quiz] = replace(cases[first_quiz], question="empty quiz case")
    result = FullCorpusTutorEvaluationRunner(
        cases=cases,
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=_ContractTutorService,
    ).run()

    assert result["metrics"]["empty_quiz_suite_count"] == 1
    assert result["metrics"]["quiz_question_source_coverage"] < 1.0
    assert result["status"] == "BLOCKED"

    cases = _canonical_cases()
    quiz_indexes = [index for index, case in enumerate(cases) if case.mode == "quiz"]
    failing_case_id = cases[quiz_indexes[1]].case_id
    cases[quiz_indexes[1]] = replace(cases[quiz_indexes[1]], question="unsourced quiz case")
    result = FullCorpusTutorEvaluationRunner(
        cases=cases,
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=_ContractTutorService,
    ).run()

    assert result["metrics"]["quiz_question_source_coverage"] < 1.0
    assert result["failed_case_ids"]["quiz_coverage_failure_ids"] == [failing_case_id]


@pytest.mark.parametrize(
    ("defect", "metric_name", "failure_key"),
    [
        ("quantity", "quiz_requested_question_count_pass_rate", "quiz_question_count_failure_ids"),
        ("duplicate", "quiz_normalized_unique_question_rate", "quiz_duplicate_question_ids"),
        ("topic", "quiz_topic_relevance_rate", "quiz_topic_relevance_failure_ids"),
        ("mapping", "quiz_source_mapping_rate", "quiz_source_mapping_failure_ids"),
    ],
)
def test_quiz_gate_audits_quantity_duplicates_topic_and_source_mapping(
    tmp_path: Path,
    defect: str,
    metric_name: str,
    failure_key: str,
) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    class DefectiveQuizTutorService(_ContractTutorService):
        def quiz(self, *, article_id=None, node_id=None, topic=None, num_questions=3):
            questions = super().quiz(
                article_id=article_id,
                node_id=node_id,
                topic=topic,
                num_questions=num_questions,
            )
            if topic != "quiz supported question 0":
                return questions
            if defect == "quantity":
                return questions[:1]
            if defect == "duplicate":
                questions[1] = replace(
                    questions[1],
                    question=f"  {questions[0].question.upper()} !!! ",
                )
            elif defect == "topic":
                questions[1] = replace(questions[1], question="unrelated evidence question")
            elif defect == "mapping":
                questions[1] = replace(questions[1], sources=[_source("unmapped-article")])
            return questions

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    result = FullCorpusTutorEvaluationRunner(
        cases=_canonical_cases(),
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=DefectiveQuizTutorService,
    ).run()

    assert result["status"] == "BLOCKED"
    assert result["metrics"][metric_name] < 1.0
    assert metric_name in result["hard_metric_failures"]
    assert result["failed_case_ids"][failure_key] == ["quiz-0"]


def test_irrelevant_article_rate_uses_articles_not_chunks(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    class TwoChunkTutorService:
        def answer(self, request):
            first = _source("irrelevant-article")
            second = replace(first, source_id="irrelevant-article:1", chunk_index=1)
            return TutorResponse(
                answer="Grounded answer.",
                mode=request.mode,
                sources=[first, second],
                selection_summary=SelectionSummary(selected_article_count=1, selected_chunk_count=2),
                evidence_summary=EvidenceSummary(
                    source_count=2,
                    article_count=1,
                    has_answerable_evidence=True,
                    source_schema_valid=True,
                ),
            )

        def quiz(self, **_kwargs):
            return []

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    result = FullCorpusTutorEvaluationRunner(
        cases=[_case("qa-two-chunks", "qa")],
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=TwoChunkTutorService,
    ).run()

    assert result["metrics"]["irrelevant_article_rate"] == 1.0


def test_graph_expansion_without_node_id_is_a_budget_violation_and_zero_high_degree_checks_block(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    class UnexpectedGraphTutorService(_ContractTutorService):
        def answer(self, request):
            response = super().answer(request)
            graph_context = {
                "nodes": [{"node_id": "concept:unexpected", "metadata": {"source_count": 1}}],
                "edges": [],
            }
            return replace(
                response,
                graph_context=graph_context,
                selection_summary=replace(response.selection_summary, graph_node_count=1),
            )

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    cases = [replace(case, node_id=None) for case in _canonical_cases()]
    result = FullCorpusTutorEvaluationRunner(
        cases=cases,
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=UnexpectedGraphTutorService,
    ).run()

    assert result["metrics"]["graph_budget_violation_count"] == 42
    assert result["metrics"]["high_degree_concept_checked_count"] == 0
    assert "high_degree_concept_checked_count" in result["evaluation_validity_failures"]
    assert result["status"] == "BLOCKED"


def test_timings_separate_components_include_quiz_and_skip_failed_samples(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import FullCorpusTutorEvaluationRunner

    class Retriever:
        def retrieve(self, *_args, **_kwargs):
            time.sleep(0.001)

    class Selector:
        def select(self, *_args, **_kwargs):
            time.sleep(0.001)

    class TimedTutorService:
        def __init__(self) -> None:
            self.retriever = Retriever()
            self.source_selector = Selector()

        def _collect_graph_context(self, _request):
            time.sleep(0.001)

        def answer(self, request):
            self._collect_graph_context(request)
            self.retriever.retrieve(request=request, candidate_limit=20)
            self.source_selector.select()
            if request.question.startswith("fail"):
                raise RuntimeError("expected execution failure")
            return TutorResponse(
                answer="Grounded answer.",
                mode=request.mode,
                sources=[_source("article-a")],
                selection_summary=SelectionSummary(selected_article_count=1, selected_chunk_count=1),
                evidence_summary=EvidenceSummary(
                    source_count=1,
                    article_count=1,
                    has_answerable_evidence=True,
                    source_schema_valid=True,
                ),
            )

        def quiz(self, **_kwargs):
            time.sleep(0.02)
            return [
                QuizQuestion(
                    question="Timed question",
                    options=None,
                    correct_answer="Timed answer",
                    explanation="Timed explanation",
                    sources=[_source("article-a")],
                )
            ]

    article_store, rag_index, graph_dir = _minimal_runner_inputs(tmp_path)
    quiz_case = _case("quiz-timed", "quiz")
    failed_case = replace(_case("qa-failed", "qa"), question="fail this case")
    result = FullCorpusTutorEvaluationRunner(
        cases=[quiz_case, failed_case],
        article_store_path=article_store,
        rag_index_dir=rag_index,
        graph_dir=graph_dir,
        service_factory=TimedTutorService,
    ).run()

    assert result["metrics"]["execution_error_count"] == 1
    assert result["timings_ms"]["retrieval"]["count"] == 1
    assert result["timings_ms"]["graph"]["count"] == 1
    assert result["timings_ms"]["selection"]["count"] == 1
    assert result["timings_ms"]["tutor"]["count"] == 1
    assert result["timings_ms"]["tutor"]["min"] >= 15.0


@pytest.mark.parametrize("status", ["BLOCKED", "CONDITIONAL"])
def test_cli_returns_nonzero_for_every_non_pass_status(monkeypatch, status: str) -> None:
    script_path = REPOSITORY_ROOT / "scripts" / "eval" / "run_full_corpus_tutor_eval.py"
    spec = importlib.util.spec_from_file_location("run_full_corpus_tutor_eval_for_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class StubRunner:
        def __init__(self, **_kwargs):
            pass

        def run(self, **_kwargs):
            return {
                "status": status,
                "case_count": 42,
                "hard_metric_failures": {},
                "evaluation_validity_failures": {},
            }

    monkeypatch.setattr(module, "load_full_corpus_tutor_cases", lambda _path: [object()])
    monkeypatch.setattr(module, "FullCorpusTutorEvaluationRunner", StubRunner)

    assert module.main([]) == 1


def _write_tiny_persisted_resources(tmp_path: Path) -> tuple[Path, Path, Path, str, str]:
    from app.graph.full_corpus import build_full_corpus_graph
    from app.rag.full_corpus import build_full_corpus_index

    article_store = tmp_path / "persisted" / "articles.json"
    rag_index_dir = tmp_path / "persisted" / "rag"
    graph_dir = tmp_path / "persisted" / "graph"
    formula_article_id = "tiny-formula"
    plain_article_id = "tiny-plain-1"
    articles = []
    for index in range(7):
        article_id = formula_article_id if index == 0 else f"tiny-plain-{index}"
        formula = "\n\nDerivation proof with local formula evidence:\n\n$$\ny = x + 1\n$$" if index == 0 else ""
        articles.append(
            {
                "id": article_id,
                "title": f"Attention local evidence study {index}",
                "url": f"https://spaces.ac.cn/archives/tiny-{index}",
                "content": (
                    f"# Attention section {index}\n\n"
                    "Attention local evidence is defined as a bounded, answerable concept. "
                    "This local section compares attention evidence for study and research."
                    f"{formula}\n\n"
                    f"## Attention bounded comparison {index}\n\n"
                    "Attention local evidence supports a second bounded comparison unit. "
                    "This section contrasts attention definitions, mechanisms, and evaluation evidence."
                ),
                "metadata": {
                    "date": "2026-01-01",
                    "category": "attention",
                    "references": [],
                    "images": [],
                },
            }
        )
    article_store.parent.mkdir(parents=True)
    article_store.write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")
    build_full_corpus_index(
        article_store_path=article_store,
        output_dir=rag_index_dir,
        provider_name="fake",
        rebuild=True,
    )
    build_full_corpus_graph(
        article_store_path=article_store,
        output_dir=graph_dir,
        rebuild=True,
    )
    return article_store, rag_index_dir, graph_dir, formula_article_id, plain_article_id


def _write_tiny_42_case_fixture(
    path: Path,
    *,
    formula_article_id: str,
    plain_article_id: str,
    block_one_quiz: bool = False,
) -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    explicit_graph_added = False
    blocked_quiz_added = False
    for index, case in enumerate(payload):
        case.pop("article_id", None)
        case.pop("node_id", None)
        mode = case["mode"]
        if mode == "unsupported":
            case["question"] = f"real-time weather unsupported request {index}"
            case["expected_article_ids"] = []
            case["min_sources"] = 0
            case["max_sources"] = 0
            continue
        if mode == "derive" and case["expected_refusal"]:
            case["question"] = f"attention local evidence without formula {index}"
            case["expected_article_ids"] = [plain_article_id]
            case["article_id"] = plain_article_id
            case["min_sources"] = 0
            continue
        if mode == "research":
            case["question"] = f"research attention local evidence comparison {index}"
            case["expected_article_ids"] = [formula_article_id, plain_article_id]
            case["min_sources"] = 2
            continue

        case["question"] = f"{mode} attention local evidence formula proof {index}"
        if block_one_quiz and mode == "quiz" and not blocked_quiz_added:
            case["question"] = "real-time weather unsupported quiz request"
            blocked_quiz_added = True
        case["expected_article_ids"] = [formula_article_id]
        case["article_id"] = formula_article_id
        case["min_sources"] = 1
        if mode == "explain" and not explicit_graph_added:
            case["node_id"] = "concept:attention"
            explicit_graph_added = True
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_real_runner_rejects_expected_or_scoped_article_ids_absent_from_persisted_corpus(tmp_path: Path) -> None:
    from app.evaluation.tutor_full_corpus import (
        FullCorpusTutorEvaluationRunner,
        load_full_corpus_tutor_cases,
    )

    article_store, rag_index_dir, graph_dir, formula_id, plain_id = _write_tiny_persisted_resources(tmp_path)
    fixture = tmp_path / "tiny-42-cases.json"
    _write_tiny_42_case_fixture(
        fixture,
        formula_article_id=formula_id,
        plain_article_id=plain_id,
    )
    base_case = load_full_corpus_tutor_cases(fixture)[0]
    invalid_cases = [
        replace(base_case, expected_article_ids=(formula_id, "missing-expected-article")),
        replace(base_case, expected_article_ids=(formula_id,), article_id="missing-scoped-article"),
    ]

    for invalid_case in invalid_cases:
        missing_id = next(
            article_id
            for article_id in (*invalid_case.expected_article_ids, invalid_case.article_id)
            if article_id is not None and article_id.startswith("missing-")
        )
        runner = FullCorpusTutorEvaluationRunner(
            cases=[invalid_case],
            article_store_path=article_store,
            rag_index_dir=rag_index_dir,
            graph_dir=graph_dir,
            provider="fake",
        )
        with pytest.raises(ValueError, match=missing_id):
            runner.run()


def test_real_tiny_persisted_42_case_cli_path_is_pass_and_fail_closed(tmp_path: Path) -> None:
    article_store, rag_index_dir, graph_dir, formula_id, plain_id = _write_tiny_persisted_resources(tmp_path)
    fixture = tmp_path / "tiny-42-cases.json"
    blocked_fixture = tmp_path / "tiny-42-cases-blocked.json"
    output = tmp_path / ".local_data" / "evaluation" / "summary.json"
    blocked_output = tmp_path / ".local_data" / "evaluation" / "blocked-summary.json"
    _write_tiny_42_case_fixture(
        fixture,
        formula_article_id=formula_id,
        plain_article_id=plain_id,
    )
    _write_tiny_42_case_fixture(
        blocked_fixture,
        formula_article_id=formula_id,
        plain_article_id=plain_id,
        block_one_quiz=True,
    )
    script = REPOSITORY_ROOT / "scripts" / "eval" / "run_full_corpus_tutor_eval.py"

    def run_cli(*, fixture_path: Path, graph_path: Path = graph_dir, target: Path = output):
        return subprocess.run(
            [
                sys.executable,
                str(script),
                "--fixture",
                str(fixture_path),
                "--article-store",
                str(article_store),
                "--rag-index-dir",
                str(rag_index_dir),
                "--graph-dir",
                str(graph_path),
                "--provider",
                "fake",
                "--output",
                str(target),
            ],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    completed = run_cli(fixture_path=fixture)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["case_count"] == 42
    assert summary["metrics"]["derive_insufficient_evidence_refusal_rate"] == 1.0
    assert summary["metrics"]["high_degree_concept_checked_count"] == 1
    assert summary["metrics"]["high_degree_concept_overexpansion_count"] == 0
    assert summary["timings_ms"]["retrieval"]["count"] == 42
    assert summary["timings_ms"]["selection"]["count"] == 42
    assert summary["timings_ms"]["tutor"]["count"] == 42

    blocked = run_cli(fixture_path=blocked_fixture, target=blocked_output)
    assert blocked.returncode == 1, blocked.stderr or blocked.stdout
    assert json.loads(blocked.stdout)["status"] == "BLOCKED"

    missing = run_cli(fixture_path=fixture, graph_path=tmp_path / "missing-graph")
    assert missing.returncode == 2
    assert "directory containing graph.json" in missing.stderr

    rag_manifest_path = rag_index_dir / "index" / "manifest.json"
    rag_manifest = json.loads(rag_manifest_path.read_text(encoding="utf-8"))
    original_rag_fingerprint = rag_manifest["corpus_fingerprint"]
    rag_manifest["corpus_fingerprint"] = "mismatched-corpus"
    rag_manifest_path.write_text(json.dumps(rag_manifest), encoding="utf-8")
    mismatched_rag = run_cli(fixture_path=fixture)
    assert mismatched_rag.returncode == 2
    assert "RAG index fingerprint" in mismatched_rag.stderr
    rag_manifest["corpus_fingerprint"] = original_rag_fingerprint
    rag_manifest_path.write_text(json.dumps(rag_manifest), encoding="utf-8")

    graph_manifest_path = graph_dir / "manifest.json"
    graph_manifest = json.loads(graph_manifest_path.read_text(encoding="utf-8"))
    graph_manifest["corpus_fingerprint"] = "mismatched-corpus"
    graph_manifest_path.write_text(json.dumps(graph_manifest), encoding="utf-8")
    mismatched_graph = run_cli(fixture_path=fixture)
    assert mismatched_graph.returncode == 2
    assert "Graph corpus fingerprint" in mismatched_graph.stderr


def test_atomic_ignored_output_preserves_previous_result_on_replace_failure(tmp_path: Path, monkeypatch) -> None:
    import app.evaluation.tutor_full_corpus as module

    output_path = tmp_path / ".local_data" / "reports" / "summary.json"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("old-summary", encoding="utf-8")

    def fail_replace(*_args, **_kwargs):
        raise OSError("simulated atomic publish failure")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated atomic publish failure"):
        module._write_ignored_json_atomic(output_path, {"case_count": 1})

    assert output_path.read_text(encoding="utf-8") == "old-summary"
    assert not list(output_path.parent.glob(".summary.json.tmp-*"))


@pytest.mark.parametrize(
    ("provider", "allow_real_provider", "ci", "has_api_key", "message"),
    [
        ("openai", False, False, True, "explicit opt-in"),
        ("openai", True, True, True, "CI"),
        ("openai", True, False, False, "OPENAI_API_KEY"),
    ],
)
def test_real_provider_is_fail_closed(provider, allow_real_provider, ci, has_api_key, message) -> None:
    from app.evaluation.tutor_full_corpus import RealProviderNotAllowed, validate_tutor_evaluation_provider

    with pytest.raises(RealProviderNotAllowed, match=message):
        validate_tutor_evaluation_provider(
            provider,
            allow_real_provider=allow_real_provider,
            ci=ci,
            api_key="test-key" if has_api_key else None,
        )


def test_fake_provider_is_default_and_does_not_require_an_api_key(monkeypatch) -> None:
    from app.evaluation.tutor_full_corpus import validate_tutor_evaluation_provider

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert validate_tutor_evaluation_provider(None) == "fake"
