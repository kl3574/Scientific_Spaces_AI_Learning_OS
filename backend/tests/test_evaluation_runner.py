from pathlib import Path
import subprocess
import sys

from app.evaluation.runner import EvaluationRunner, load_eval_dataset


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "evaluation"
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_eval_suite_loads_fixtures() -> None:
    dataset = load_eval_dataset(FIXTURE_DIR)

    assert len(dataset.articles) == 3
    assert len(dataset.cases) == 9
    assert dataset.articles[0]["id"] == "attention-basics"
    assert {case.task_type for case in dataset.cases} >= {
        "rag_query",
        "tutor_explain",
        "tutor_derive",
        "tutor_qa",
        "tutor_quiz",
        "tutor_research",
        "no_source",
    }


def test_rag_eval_case_runs_with_expected_source() -> None:
    result = EvaluationRunner(FIXTURE_DIR).run_case("rag_attention_sources")

    assert result.task_type == "rag_query"
    assert result.sources
    assert result.metrics["expected_article_hit"] is True
    assert result.metrics["citation_required"] is True


def test_tutor_explain_case_runs_grounded() -> None:
    result = EvaluationRunner(FIXTURE_DIR).run_case("tutor_explain_attention")

    assert result.mode == "explain"
    assert result.sources
    assert result.refusal_reason is None
    assert result.metrics["expected_article_hit"] is True
    assert result.follow_up_questions


def test_tutor_derive_insufficient_source_case_refuses() -> None:
    result = EvaluationRunner(FIXTURE_DIR).run_case("tutor_derive_insufficient_formula")

    assert result.mode == "derive"
    assert result.refusal_reason == "insufficient_formula_sources"
    assert result.metrics["expected_refusal"] is True
    assert result.metrics["refusal_correct"] is True


def test_tutor_quiz_case_requires_sources_per_question() -> None:
    result = EvaluationRunner(FIXTURE_DIR).run_case("tutor_quiz_crb_sources")

    assert result.task_type == "tutor_quiz"
    assert result.quiz_questions
    assert result.metrics["quiz_questions_have_sources"] is True


def test_tutor_research_case_is_local_only() -> None:
    result = EvaluationRunner(FIXTURE_DIR).run_case("tutor_research_local_only")

    assert result.mode == "research"
    assert result.sources
    assert result.metrics["research_local_only"] is True
    assert "不能视为完整文献综述" in result.answer


def test_eval_suite_aggregate_metrics_are_deterministic() -> None:
    first = EvaluationRunner(FIXTURE_DIR).run()
    second = EvaluationRunner(FIXTURE_DIR).run()

    assert first.metrics.to_dict() == second.metrics.to_dict()
    assert first.metrics.case_count == 9
    assert first.metrics.retrieval_hit_at_k == 1.0
    assert first.metrics.citation_required_pass_rate == 1.0
    assert first.metrics.no_source_refusal_rate == 1.0
    assert first.metrics.quiz_question_sources_rate == 1.0
    assert first.metrics.research_local_only_rate == 1.0
    assert first.passed is True


def test_eval_runner_does_not_create_runtime_artifacts_in_fixture_dir() -> None:
    before = {path.name for path in FIXTURE_DIR.iterdir()}
    EvaluationRunner(FIXTURE_DIR).run()
    after = {path.name for path in FIXTURE_DIR.iterdir()}

    assert after == before


def test_eval_cli_prints_summary_without_default_artifact() -> None:
    before = {path.name for path in FIXTURE_DIR.iterdir()}
    completed = subprocess.run(
        [sys.executable, "scripts/eval/run_rag_tutor_eval.py"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    after = {path.name for path in FIXTURE_DIR.iterdir()}

    assert "RAG/Tutor Evaluation Baseline" in completed.stdout
    assert "Cases: 9" in completed.stdout
    assert "Overall: PASS" in completed.stdout
    assert after == before
