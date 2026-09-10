from app.evaluation.tutor_generation import fingerprint, load_fixture_groups, observe_modes


def test_same_question_same_evidence_has_five_distinct_generation_requests() -> None:
    rows, counters = observe_modes(load_fixture_groups()[1])
    assert all(row["response"]["refusal_reason"] is None for row in rows)
    assert [len(row["calls"]) for row in rows] == [1] * 5
    assert len({fingerprint([source["source_id"] for source in row["response"]["sources"]]) for row in rows}) == 1
    assert len({fingerprint(row["calls"]) for row in rows}) == 5
    assert counters == {"network_attempt_count": 0, "external_request_count": 0}


import json
import os
import socket
from pathlib import Path

import pytest

from app.evaluation import tutor_generation as evaluation
from app.evaluation.tutor_generation import (
    fixture_arithmetic_observation,
    run_evaluation,
    synthetic_runtime,
    write_evaluation,
)


@pytest.fixture(scope="module")
def evaluated_suite():
    return run_evaluation()


def test_results_separate_contract_fixture_pending_review_and_unrun_provider(evaluated_suite) -> None:
    summary, rows = evaluated_suite
    assert summary["contract_results"]["status"] == "PASS"
    checks = summary["contract_results"]["checks"]
    assert summary["contract_results"]["executed_denominator"] == sum(
        check["status"] in {"PASS", "FAIL"} for check in checks
    )
    assert summary["contract_results"]["failed"] == []
    assert {check["status"] for check in summary["contract_results"]["skipped"]} == {
        "NOT_APPLICABLE", "NOT_IMPLEMENTED",
    }
    assert summary["fixture_results"]["status"] == "PASS"
    assert summary["human_review"] == {
        "status": "PENDING", "completed": 0, "sample_denominator": len(rows) + 2,
        "mathematical_correctness": None, "evidence_support": None, "teaching_clarity": None,
    }
    assert summary["real_provider_results"] == {
        "status": "NOT_RUN", "reason": "Not authorized in this task", "sample_count": 0,
        "quality": None, "latency": None, "cost": None,
    }
    metadata = summary["metadata"]
    assert len(metadata["head"]) == 40
    assert len(metadata["worktree_change_sha256"]) == len(metadata["fixture_sha256"]) == 64
    assert metadata["network_attempt_count"] == metadata["external_request_count"] == 0


def test_development_and_acceptance_are_topic_and_article_disjoint(evaluated_suite) -> None:
    summary, _ = evaluated_suite
    development = summary["fixture_results"]["splits"]["development"]
    acceptance = summary["fixture_results"]["splits"]["acceptance"]
    assert set(development["article_ids"]).isdisjoint(acceptance["article_ids"])
    assert development["topic"] != acceptance["topic"]
    assert all(split["data_role"] == "development/regression" and split["unseen_holdout"] is False
               for split in (development, acceptance))
    assert not development["controlled_mode_comparison"]
    assert acceptance["controlled_mode_comparison"]
    assert acceptance["observed_ordered_source_variants"] == 1
    assert acceptance["exact_synthetic_chunk_content"] == {
        "numerator": 10, "denominator": 10, "value": 1.0,
    }


def test_correct_source_ids_do_not_turn_wrong_product_claim_into_semantic_success(evaluated_suite) -> None:
    summary, _ = evaluated_suite
    positive, negative = summary["fixture_results"]["contrast_cases"]
    assert positive["source_ids_valid"] and negative["source_ids_valid"]
    assert positive["fixture_arithmetic_relation"] == "supported"
    assert negative["fixture_arithmetic_relation"] == "contradicted"
    assert negative["observed_x"] == 99
    assert positive["expected_x"] == negative["expected_x"] == 3
    assert all(case["semantic_correctness"] is None for case in (positive, negative))
    # Existing grounding checks source presence; it cannot detect this wrong assertion.
    assert negative["service_refusal_reason"] is None


@pytest.mark.parametrize("answer,expected", [
    ("The result is x=3.", "supported"),
    ("The result is x=99.", "contradicted"),
    ("No numerical answer is available.", "unresolved"),
    ("x=3 or x=99", "unresolved"),
    ("x=3e2", "unresolved"),
    ("x=3/5", "unresolved"),
])
def test_arithmetic_contrast_reads_returned_text_not_scenario_identity(answer, expected) -> None:
    truth = {"a": 2, "b": 1, "y": 7}
    assert fixture_arithmetic_observation(answer, truth)["fixture_arithmetic_relation"] == expected


def test_runtime_overrides_private_and_real_configuration_and_denies_network(monkeypatch) -> None:
    monkeypatch.setenv("SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SCIENTIFIC_SPACES_RAG_INDEX_DIR", "/private-sentinel-index")
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", "/private-sentinel-article")
    with synthetic_runtime(load_fixture_groups()[1]["articles"]) as counters:
        assert os.environ["SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER"] == "fake"
        assert "SCIENTIFIC_SPACES_RAG_INDEX_DIR" not in os.environ
        assert os.environ["SCIENTIFIC_SPACES_ARTICLES_FILE"] != "/private-sentinel-article"
        with pytest.raises(RuntimeError, match="Network access is disabled"):
            socket.create_connection(("example.test", 443))
    assert counters == {"network_attempt_count": 1, "external_request_count": 0}
    assert os.environ["SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER"] == "openai"
    assert os.environ["SCIENTIFIC_SPACES_ARTICLES_FILE"] == "/private-sentinel-article"


def test_reused_output_audit_and_ignored_path_confinement(tmp_path: Path, monkeypatch, evaluated_suite) -> None:
    summary, rows = evaluated_suite
    monkeypatch.setattr(evaluation, "REPO_ROOT", tmp_path)
    run_dir = tmp_path / "eval_outputs" / "tutor_generation" / "run-1"
    audit = write_evaluation(summary, rows, output_dir=run_dir)
    assert audit["passed"] and audit["findings"] == []
    assert audit["file_count"] == 3
    assert set(path.name for path in run_dir.iterdir()) == {"run.json", "cases.jsonl", "aggregate.json"}
    assert json.loads((run_dir / "aggregate.json").read_text())["human_review"]["status"] == "PENDING"
    with pytest.raises(ValueError):
        write_evaluation(summary, rows, output_dir=tmp_path / "public-summary")
    with pytest.raises(FileExistsError):
        write_evaluation(summary, rows, output_dir=run_dir)


def test_output_rejects_symlinked_parent_before_writing(tmp_path: Path, monkeypatch, evaluated_suite) -> None:
    summary, rows = evaluated_suite
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "eval_outputs").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(evaluation, "REPO_ROOT", root)
    with pytest.raises(ValueError):
        write_evaluation(summary, rows, output_dir=root / "eval_outputs" / "tutor_generation" / "run")
    assert list(outside.iterdir()) == []
