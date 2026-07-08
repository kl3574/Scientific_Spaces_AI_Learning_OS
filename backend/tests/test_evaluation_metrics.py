from app.evaluation.metrics import (
    MetricInputs,
    calculate_suite_metrics,
    expected_article_hit,
    has_valid_source_schema,
    is_refusal,
    quiz_questions_have_sources,
    retrieval_hit_at_k,
)
from app.evaluation.models import EvalCase, EvalResult


def article_source(article_id: str = "attention-basics") -> dict[str, object]:
    return {
        "article_id": article_id,
        "article_title": "Attention机制入门",
        "article_url": "https://example.test/articles/attention-basics",
        "section_title": "Attention机制",
        "chunk_index": 0,
    }


def tutor_article_source(article_id: str = "attention-basics") -> dict[str, object]:
    return {
        "source_type": "article_chunk",
        "source_id": f"{article_id}:0",
        "title": "Attention机制入门",
        "url": "https://example.test/articles/attention-basics",
        "section_title": "Attention机制",
        "chunk_index": 0,
        "metadata": {"article_id": article_id},
    }


def test_source_schema_validation_accepts_rag_and_tutor_article_sources() -> None:
    assert has_valid_source_schema(article_source())
    assert has_valid_source_schema(tutor_article_source())


def test_source_schema_validation_rejects_missing_section_or_url() -> None:
    missing_url = dict(article_source())
    missing_url.pop("article_url")
    missing_section = dict(tutor_article_source())
    missing_section["section_title"] = None

    assert not has_valid_source_schema(missing_url)
    assert not has_valid_source_schema(missing_section)


def test_citation_hit_and_retrieval_metrics_are_deterministic() -> None:
    sources = [article_source("attention-basics"), article_source("crb-formula")]

    assert expected_article_hit(sources, ["crb-formula"])
    assert retrieval_hit_at_k(sources, ["crb-formula"], k=2)
    assert not retrieval_hit_at_k(sources, ["crb-formula"], k=1)


def test_no_source_refusal_pass_and_fail_detection() -> None:
    assert is_refusal("无法基于当前资料回答。", refusal_reason=None)
    assert is_refusal("当前资料不足以完整推导。", refusal_reason="insufficient_formula_sources")
    assert not is_refusal("这是一个没有来源的编造回答。", refusal_reason=None)


def test_quiz_source_validation_requires_each_question_source() -> None:
    sourced_questions = [
        {"question": "Q1", "correct_answer": "A1", "explanation": "E1", "sources": [tutor_article_source()]},
        {"question": "Q2", "correct_answer": "A2", "explanation": "E2", "sources": [tutor_article_source()]},
    ]
    unsourced_questions = [
        {"question": "Q1", "correct_answer": "A1", "explanation": "E1", "sources": [tutor_article_source()]},
        {"question": "Q2", "correct_answer": "A2", "explanation": "E2", "sources": []},
    ]

    assert quiz_questions_have_sources(sourced_questions)
    assert not quiz_questions_have_sources(unsourced_questions)


def test_aggregate_metrics_detect_unsupported_answer_and_missing_sources() -> None:
    cases = [
        EvalCase(
            case_id="supported",
            task_type="rag_query",
            question="什么是Attention？",
            expected_source_article_ids=["attention-basics"],
            expected_refusal=False,
            min_sources=1,
        ),
        EvalCase(
            case_id="unsupported",
            task_type="no_source",
            question="是否证明量子引力？",
            expected_refusal=True,
            min_sources=0,
        ),
        EvalCase(
            case_id="quiz",
            task_type="tutor_quiz",
            question="生成题目",
            article_id="attention-basics",
            expected_source_article_ids=["attention-basics"],
            expected_refusal=False,
            min_sources=1,
        ),
    ]
    results = [
        EvalResult(case_id="supported", task_type="rag_query", answer="有来源回答", sources=[article_source()]),
        EvalResult(case_id="unsupported", task_type="no_source", answer="无来源编造", sources=[]),
        EvalResult(
            case_id="quiz",
            task_type="tutor_quiz",
            answer="",
            sources=[tutor_article_source()],
            quiz_questions=[
                {"question": "Q1", "correct_answer": "A1", "explanation": "E1", "sources": []}
            ],
        ),
    ]

    summary = calculate_suite_metrics(
        MetricInputs(cases=cases, results=results, valid_article_ids={"attention-basics", "crb-formula"})
    )

    assert summary.citation_required_pass_rate == 1.0
    assert summary.no_source_refusal_rate == 0.0
    assert summary.no_source_answer_fabrication_count == 1
    assert summary.quiz_question_sources_rate == 0.0
    assert summary.quiz_without_sources_count == 1
