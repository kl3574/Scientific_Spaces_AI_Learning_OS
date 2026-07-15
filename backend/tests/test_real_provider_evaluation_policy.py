from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.evaluation.provider_eval.models import ConsentRecord, EvaluationLimits, ProviderEvaluationConfig
from app.evaluation.provider_eval.policy import (
    EvaluationPolicyError,
    build_request_envelope,
    load_case_set,
    validate_request_envelope,
)
from app.evaluation.provider_eval.runner import ProviderEvaluationRunner


FIXTURE = Path(__file__).parent / "fixtures" / "evaluation" / "provider_cases.json"


def _config(**overrides: object) -> ProviderEvaluationConfig:
    values: dict[str, object] = {
        "provider_kind": "fake",
        "provider_name": "deterministic-fake",
        "model_name": "fake-evaluation-v1",
        "model_version_identifier": "fixture-v1",
        "endpoint_category": "combined",
        "case_set_id": "p3-004-provider-safety-v1",
        "dry_run": True,
        "consent": ConsentRecord(),
        "data_categories_sent": ("public_fixture",),
        "limits": EvaluationLimits(
            max_requests=25,
            max_estimated_cost=1.0,
            currency="USD",
            max_context_chars=512,
            max_output_chars=1_000,
            timeout_seconds=10.0,
            max_retries=1,
        ),
    }
    values.update(overrides)
    return ProviderEvaluationConfig(**values)  # type: ignore[arg-type]


def test_case_set_covers_the_approved_taxonomy() -> None:
    case_set = load_case_set(FIXTURE)

    assert case_set.case_set_id == "p3-004-provider-safety-v1"
    assert {case.task_type for case in case_set.cases} == {
        "explain",
        "derive",
        "qa",
        "quiz",
        "research",
        "unsupported",
        "no_source",
        "citation_conflict",
        "long_context",
        "provider_error",
    }
    assert {case.sensitive_data_classification for case in case_set.cases} == {"public_fixture"}


def test_case_set_rejects_unknown_fields(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["cases"][0]["private_notes"] = "not allowed"
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvaluationPolicyError, match="unexpected") as error:
        load_case_set(invalid)

    assert error.value.code == "validation_error"


def test_runner_rejects_arbitrary_case_set_path(tmp_path: Path) -> None:
    copied = tmp_path / "copied-cases.json"
    copied.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(EvaluationPolicyError, match="approved fixture root"):
        ProviderEvaluationRunner(copied, tmp_path / "run", allowed_output_root=tmp_path)


def test_case_set_rejects_secret_shaped_or_local_path_material(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["cases"][0]["instruction"] = "token " + "sk-" + "x" * 16
    invalid = tmp_path / "unsafe.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvaluationPolicyError, match="prohibited secret"):
        load_case_set(invalid)


def test_case_set_requires_boolean_refusal_flag(tmp_path: Path) -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["cases"][0]["expected_refusal"] = "false"
    invalid = tmp_path / "invalid-bool.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvaluationPolicyError, match="must be boolean"):
        load_case_set(invalid)


def test_request_envelope_is_allowlisted_and_prompt_injection_stays_untrusted() -> None:
    case = next(case for case in load_case_set(FIXTURE).cases if case.task_type == "long_context")
    envelope = build_request_envelope(
        case,
        EvaluationLimits(
            max_requests=10,
            max_estimated_cost=1.0,
            currency="USD",
            max_context_chars=180,
            max_output_chars=200,
            timeout_seconds=5.0,
            max_retries=0,
        ),
    )
    payload = envelope.to_dict()

    assert set(payload) == {
        "schema_version",
        "case_id",
        "task_type",
        "instruction",
        "protocol",
        "data_classification",
        "evidence",
    }
    assert set(payload["protocol"]) == {
        "expected_mode",
        "expected_refusal",
        "max_sources",
        "max_context_chars",
        "max_output_chars",
    }
    assert set(payload["evidence"][0]) == {"source_id", "title", "section", "untrusted_excerpt"}
    assert payload["protocol"]["expected_mode"] == "explain"
    assert envelope.context_was_truncated is True
    assert "<<<UNTRUSTED_ARTICLE_EVIDENCE>>>" in payload["evidence"][0]["untrusted_excerpt"]
    validate_request_envelope(payload)


def test_request_envelope_rejects_non_allowlisted_key() -> None:
    case = load_case_set(FIXTURE).cases[0]
    payload = build_request_envelope(case, _config().limits).to_dict()
    payload["api_key"] = "placeholder"

    with pytest.raises(EvaluationPolicyError) as error:
        validate_request_envelope(payload)

    assert error.value.code == "validation_error"


def test_missing_real_consent_fails_before_adapter_construction(tmp_path: Path) -> None:
    constructions = 0

    def forbidden_factory(config: ProviderEvaluationConfig) -> object:
        nonlocal constructions
        constructions += 1
        raise AssertionError(config)

    runner = ProviderEvaluationRunner(
        FIXTURE,
        tmp_path / "run",
        allowed_output_root=tmp_path,
        adapter_factory=forbidden_factory,
    )
    config = _config(
        provider_kind="real",
        provider_name="named-provider",
        model_name="named-model",
        pricing_metadata_source="public pricing page",
        pricing_as_of="2026-07-15",
    )

    with pytest.raises(EvaluationPolicyError) as error:
        runner.run(config)

    assert error.value.code == "consent_missing"
    assert constructions == 0


def test_valid_real_preflight_is_plan_only_and_never_constructs_adapter(tmp_path: Path) -> None:
    constructions = 0

    def forbidden_factory(config: ProviderEvaluationConfig) -> object:
        nonlocal constructions
        constructions += 1
        raise AssertionError(config)

    runner = ProviderEvaluationRunner(
        FIXTURE,
        tmp_path / "run",
        allowed_output_root=tmp_path,
        adapter_factory=forbidden_factory,
        run_id_factory=lambda: "real-plan",
    )
    config = _config(
        provider_kind="real",
        provider_name="named-provider",
        model_name="named-model",
        consent=ConsentRecord(True, True, True),
        pricing_metadata_source="dated public pricing metadata",
        pricing_as_of="2026-07-15",
    )

    outcome = runner.run(config)

    assert outcome.run.status == "planned"
    assert outcome.output_dir is None
    assert outcome.cases == ()
    assert outcome.preflight.adapter_construction_authorized is False
    assert outcome.preflight.network_authorized is False
    assert outcome.preflight.max_context_chars == 512
    assert outcome.preflight.max_output_chars == 1_000
    assert outcome.preflight.max_retries == 1
    assert outcome.preflight.pricing_as_of == "2026-07-15"
    assert outcome.preflight.output_location == "ignored local evaluation root"
    assert outcome.aggregate["network_request_count"] == 0
    assert constructions == 0


@pytest.mark.parametrize(
    ("limits", "code"),
    [
        (EvaluationLimits(0, 1.0, "USD", 512, 100, 10.0, 1), "budget_invalid"),
        (EvaluationLimits(5, -1.0, "USD", 512, 100, 10.0, 1), "budget_invalid"),
        (EvaluationLimits(5, 1.0, "USD", 0, 100, 10.0, 1), "budget_invalid"),
        (EvaluationLimits(5, 1.0, "USD", 512, 0, 10.0, 1), "budget_invalid"),
        (EvaluationLimits(5, 1.0, "USD", 512, 100, 0.0, 1), "budget_invalid"),
        (EvaluationLimits(5, 1.0, "USD", 512, 100, 10.0, 4), "budget_invalid"),
    ],
)
def test_invalid_limits_fail_closed(tmp_path: Path, limits: EvaluationLimits, code: str) -> None:
    runner = ProviderEvaluationRunner(FIXTURE, tmp_path / "run", allowed_output_root=tmp_path)

    with pytest.raises(EvaluationPolicyError) as error:
        runner.run(_config(limits=limits))

    assert error.value.code == code


def test_unknown_real_pricing_fails_closed(tmp_path: Path) -> None:
    runner = ProviderEvaluationRunner(FIXTURE, tmp_path / "run", allowed_output_root=tmp_path)
    config = _config(
        provider_kind="real",
        provider_name="named-provider",
        model_name="named-model",
        consent=ConsentRecord(True, True, True),
        pricing_metadata_source=None,
        pricing_as_of=None,
    )

    with pytest.raises(EvaluationPolicyError) as error:
        runner.run(config)

    assert error.value.code == "budget_invalid"


def test_output_must_remain_under_configured_root(tmp_path: Path) -> None:
    runner = ProviderEvaluationRunner(FIXTURE, tmp_path.parent / "outside", allowed_output_root=tmp_path)

    with pytest.raises(EvaluationPolicyError, match="evaluation root"):
        runner.run(_config())


def test_real_mode_requires_positive_cost_cap(tmp_path: Path) -> None:
    runner = ProviderEvaluationRunner(FIXTURE, tmp_path / "run", allowed_output_root=tmp_path)
    zero_cost_limits = replace(_config().limits, max_estimated_cost=0.0)
    config = _config(
        provider_kind="real",
        provider_name="named-provider",
        model_name="named-model",
        consent=ConsentRecord(True, True, True),
        pricing_metadata_source="dated public pricing metadata",
        pricing_as_of="2026-07-15",
        limits=zero_cost_limits,
    )

    with pytest.raises(EvaluationPolicyError) as error:
        runner.run(config)

    assert error.value.code == "budget_invalid"


def test_runner_rejects_non_path_safe_run_id(tmp_path: Path) -> None:
    runner = ProviderEvaluationRunner(
        FIXTURE,
        tmp_path / "run",
        allowed_output_root=tmp_path,
        run_id_factory=lambda: "../escaped",
    )

    with pytest.raises(ValueError, match="path-safe"):
        runner.run(_config())
