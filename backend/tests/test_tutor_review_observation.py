from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.evaluation import tutor_review_observation as observation
from app.evaluation.tutor_generation import FIXTURE_DIR
from app.evaluation.tutor_review_observation import (
    ORACLE_FIELDS, mutate_oracle, observe_review_cases, project_product_input,
)


@pytest.fixture
def review_inputs():
    articles = json.loads((FIXTURE_DIR / "acceptance_articles.json").read_text(encoding="utf-8"))
    case = {
        "case_id": "request-isolation-example", "mode": "qa",
        "question": "Affine calibration inverse conditions and example. What is x for a=2, b=1, y=7?",
        "question_zh": "仅供人工阅读的问题翻译。",
        "target_claim": "x=3", "reference_answer": "x=3",
        "must_include": ["a is nonzero"], "must_not_claim": ["x=99"],
        "proposed_relation": "SUPPORTED", "answer_behavior": "ANSWER",
        "required_source_ids": [f"{article['id']}:0" for article in articles],
        "allowed_evidence": [{"article_id": article["id"], "source_id": f"{article['id']}:0"}
                             for article in articles],
    }
    return articles, {"candidate_version": "test-review/v1", "cases": [case]}, {"criteria": ["evidence support"]}


def test_all_oracle_channels_change_but_actual_product_requests_do_not(review_inputs) -> None:
    articles, cases, rubric = review_inputs
    before = copy.deepcopy((articles, cases, rubric))
    summary, rows = observe_review_cases(articles, cases, rubric)
    assert (articles, cases, rubric) == before
    assert summary["status"] == "PASS"
    assert summary["case_count"] == 1 and summary["case_path_denominator"] == 2
    assert summary["actual_product_invocations"] == 4
    assert {row["provider_path"] for row in rows} == {"legacy", "structured"}
    for path in ("legacy", "structured"):
        original, changed = [row for row in rows if row["provider_path"] == path]
        assert original["request_serialization"] == changed["request_serialization"]
        assert original["provider_call_count"] == changed["provider_call_count"] == 1
        assert original["calls"] and changed["calls"]
        assert "ORACLE_ONLY_CANARY_" not in changed["request_serialization"]
        # Ordinary answer literals also appear in the allowed Article, which is not oracle leakage.
        assert "x=3" in original["request_serialization"]
    assert all(result["oracle_isolation_status"] == "PASS" for result in summary["results"])
    assert summary["network_attempt_count"] == summary["external_request_count"] == 0


def test_canary_mutation_replaces_every_declared_oracle_channel(review_inputs) -> None:
    _, cases, rubric = review_inputs
    mutated, mutated_rubric = mutate_oracle(cases["cases"][0], rubric, nonce="UNIQUE_TEST_NONCE")
    for field in ORACLE_FIELDS:
        assert "UNIQUE_TEST_NONCE" in mutated[field]
        assert mutated[field] != cases["cases"][0][field]
    assert "UNIQUE_TEST_NONCE" in json.dumps(mutated_rubric)
    assert mutated["question"] == cases["cases"][0]["question"]
    assert mutated["mode"] == cases["cases"][0]["mode"]
    assert mutated["allowed_evidence"] == cases["cases"][0]["allowed_evidence"]


def test_differential_check_detects_a_deliberately_leaking_product_projection(review_inputs, monkeypatch) -> None:
    articles, cases, rubric = review_inputs
    real_projection = observation.project_product_input

    def leaking_projection(articles, case):
        product = real_projection(articles, case)
        product["question"] += " " + str(case["reference_answer"])
        return product

    monkeypatch.setattr(observation, "project_product_input", leaking_projection)
    summary, _ = observe_review_cases(articles, cases, rubric)
    assert summary["status"] == "FAIL"
    assert summary["oracle_isolation_passed"] == 0
    for result in summary["results"]:
        assert result["oracle_isolation_status"] == "FAIL"
        assert not result["same_actual_request_bytes"]
        assert not result["same_product_input"]
        assert not result["dedicated_canary_absent"]


def test_input_projection_is_whitelisted_and_selects_only_allowed_articles(review_inputs) -> None:
    articles, cases, _ = review_inputs
    case = copy.deepcopy(cases["cases"][0])
    case.update(question_zh="SHOULD_NEVER_BE_SENT", target_claim="SHOULD_NEVER_BE_SENT",
                reference_answer="SHOULD_NEVER_BE_SENT", unexpected_system_prompt="SHOULD_NEVER_BE_SENT")
    case["allowed_evidence"] = case["allowed_evidence"][:1]
    product = project_product_input(articles, case)
    assert set(product) == {"question", "mode", "articles"}
    assert product["question"] == case["question"]
    assert len(product["articles"]) == 1
    assert "SHOULD_NEVER_BE_SENT" not in json.dumps(product)
    product["articles"][0]["content"] = "changed projection"
    assert articles[0]["content"] != "changed projection"


def test_retrieval_failure_does_not_relabel_oracle_or_pass_empty_capture(review_inputs) -> None:
    articles, cases, rubric = review_inputs
    cases["cases"][0]["question"] = "volcanic obsidian petrology"
    summary, rows = observe_review_cases(articles, cases, rubric)
    assert summary["status"] == "FAIL" and summary["retrieval_passed"] == 0
    assert summary["oracle_isolation_passed"] == 0
    for result in summary["results"]:
        assert result["retrieval_status"] == "FAIL"
        assert result["missing_retrieved_source_ids"] == sorted(cases["cases"][0]["required_source_ids"])
        assert result["oracle_relation_preserved"] == "SUPPORTED"
        assert result["oracle_answer_behavior_preserved"] == "ANSWER"
        assert result["oracle_isolation_status"] == "NOT_RUN"
        assert result["refusal_reason"] == "no_sources"
    assert cases["cases"][0]["proposed_relation"] == "SUPPORTED"
    assert all(row["calls"] == [] for row in rows)
    assert len(summary["not_run"]) == 2
    assert summary["skipped"] == []


def test_spy_and_asserted_input_approval_cannot_create_human_or_answer_quality_approval(review_inputs) -> None:
    articles, cases, rubric = review_inputs
    cases["human_review"] = {"status": "APPROVED", "reviewer": "not-an-actual-human-decision"}
    summary, _ = observe_review_cases(articles, cases, rubric)
    assert summary["human_review"] == {"status": "PENDING", "reviewer": None, "approved_at": None}
    assert summary["product_answer_quality"]["status"] == "NOT_RUN"
    assert summary["product_answer_quality"]["score"] is None
    assert all(result["product_answer_quality"]["status"] == "NOT_RUN" for result in summary["results"])


def test_observation_output_does_not_overwrite_prior_run(tmp_path: Path, review_inputs, monkeypatch) -> None:
    from app.evaluation import tutor_generation

    monkeypatch.setattr(tutor_generation, "REPO_ROOT", tmp_path)
    summary, rows = observe_review_cases(*review_inputs)
    output = tmp_path / "eval_outputs" / "tutor_generation" / "review-observation-test"
    audit = observation.write_review_observation(summary, rows, output_dir=output)
    assert audit["passed"] and audit["file_count"] == 3
    before = (output / "cases.jsonl").read_bytes()
    with pytest.raises(FileExistsError):
        observation.write_review_observation(summary, rows, output_dir=output)
    assert (output / "cases.jsonl").read_bytes() == before
    with pytest.raises(ValueError, match="review-observation"):
        observation.write_review_observation(summary, rows, output_dir=output.parent / "final")


def test_empty_observation_set_cannot_claim_pass(review_inputs) -> None:
    articles, cases, rubric = review_inputs
    cases["cases"] = []
    with pytest.raises(ValueError, match="at least one"):
        observe_review_cases(articles, cases, rubric)


def test_invalid_candidate_is_rejected_before_any_product_invocation(tmp_path: Path, monkeypatch) -> None:
    def unexpected_product(*args, **kwargs):
        pytest.fail("Invalid candidate reached a product invocation")

    monkeypatch.setattr(observation, "_observe", unexpected_product)
    with pytest.raises(ValueError, match="candidate validation failed"):
        observation.observe_candidate(tmp_path)


def test_loaded_content_must_match_validated_snapshot_before_product_calls(tmp_path: Path, review_inputs, monkeypatch) -> None:
    from app.evaluation import tutor_review

    articles, cases, rubric = review_inputs
    for name, payload in (("articles.json", articles), ("cases.json", cases), ("rubric.json", rubric)):
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(tutor_review, "validate_review_candidate", lambda root: {
        "valid": True, "content_sha256": {"articles.json": "0" * 64}, "candidate_digest": "1" * 64,
    })
    monkeypatch.setattr(observation, "_observe", lambda *args, **kwargs: pytest.fail("Mismatched input reached product"))
    with pytest.raises(ValueError, match="differs from the validated snapshot"):
        observation.observe_candidate(tmp_path)


def test_candidate_change_during_observation_cannot_keep_valid_snapshot_claim(tmp_path: Path, review_inputs, monkeypatch) -> None:
    import hashlib
    from app.evaluation import tutor_review

    articles, cases, rubric = review_inputs
    hashes = {}
    for name, payload in (("articles.json", articles), ("cases.json", cases), ("rubric.json", rubric)):
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
        hashes[name] = hashlib.sha256(tutor_review.canonical_bytes(payload)).hexdigest()
    validations = iter([
        {"valid": True, "content_sha256": hashes, "candidate_digest": "1" * 64},
        {"valid": True, "content_sha256": hashes, "candidate_digest": "2" * 64},
    ])
    monkeypatch.setattr(tutor_review, "validate_review_candidate", lambda root: next(validations))
    with pytest.raises(ValueError, match="changed during product observations"):
        observation.observe_candidate(tmp_path)
