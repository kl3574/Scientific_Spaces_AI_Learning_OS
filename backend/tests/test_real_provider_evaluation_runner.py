from __future__ import annotations

import json
import socket
import urllib.request
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from app.evaluation.provider_eval.models import ConsentRecord, EvaluationLimits, ProviderEvaluationConfig
from app.evaluation.provider_eval.operations import audit_evaluation_output
from app.evaluation.provider_eval.output import redact_text
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
        "limits": EvaluationLimits(25, 1.0, "USD", 512, 1_000, 10.0, 1),
    }
    values.update(overrides)
    return ProviderEvaluationConfig(**values)  # type: ignore[arg-type]


def _runner(tmp_path: Path, **kwargs: object) -> ProviderEvaluationRunner:
    moments = iter(
        [
            datetime(2026, 7, 15, 1, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 15, 1, 1, tzinfo=timezone.utc),
        ]
    )
    return ProviderEvaluationRunner(
        FIXTURE,
        tmp_path / "dry-run",
        allowed_output_root=tmp_path,
        clock=lambda: next(moments),
        run_id_factory=lambda: "fixed-run-id",
        **kwargs,  # type: ignore[arg-type]
    )


def test_fake_run_writes_bounded_redacted_artifacts(tmp_path: Path) -> None:
    outcome = _runner(tmp_path).run(_config())

    assert outcome.run.status == "completed"
    assert outcome.run.run_id == "fixed-run-id"
    assert outcome.output_dir == tmp_path / "dry-run" / "fixed-run-id"
    assert {path.name for path in outcome.output_dir.iterdir()} == {"run.json", "cases.jsonl", "aggregate.json"}
    assert not (outcome.output_dir / "raw").exists()
    assert outcome.aggregate["network_request_count"] == 0
    assert outcome.aggregate["quality"]["automated_heuristics_are_human_correctness"] is False

    run_payload = json.loads((outcome.output_dir / "run.json").read_text(encoding="utf-8"))
    case_rows = [
        json.loads(line)
        for line in (outcome.output_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert run_payload["schema_version"] == "provider-evaluation-run/v1"
    assert run_payload["output_policy"]["raw_output_enabled"] is False
    assert run_payload["output_policy"]["redacted_retention_days"] == 30
    assert all(row["run_id"] == "fixed-run-id" for row in case_rows)
    assert all(row["human_review"]["status"] == "not_reviewed" for row in case_rows)
    assert audit_evaluation_output(tmp_path).passed is True


def test_fake_run_makes_zero_network_attempts(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    attempts: list[str] = []

    def blocked(*args: object, **kwargs: object) -> None:
        attempts.append("network")
        raise AssertionError((args, kwargs))

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)

    outcome = _runner(tmp_path).run(_config())

    assert attempts == []
    assert outcome.aggregate["network_request_count"] == 0


def test_fake_run_covers_terminal_failure_taxonomy(tmp_path: Path) -> None:
    outcome = _runner(tmp_path).run(_config())
    errors = {case.provider_error_code for case in outcome.cases if case.provider_error_code}

    assert {"timeout", "rate_limited", "auth_error", "server_error", "malformed_response", "validation_error"} <= errors
    assert next(case for case in outcome.cases if case.case_id == "provider_timeout").retry_count == 1
    assert next(case for case in outcome.cases if case.case_id == "provider_rate_limited").status == "rate_limited"
    assert next(case for case in outcome.cases if case.case_id == "provider_malformed_response").status == "validation_error"


def test_usage_and_cost_reconcile_with_case_results(tmp_path: Path) -> None:
    outcome = _runner(tmp_path).run(_config())

    case_request_count = sum(case.usage["requests"] for case in outcome.cases)
    case_estimated_cost = sum(case.estimated_cost or 0.0 for case in outcome.cases)
    assert case_request_count == outcome.aggregate["request_count"]
    assert case_request_count == outcome.run.provider_reported_usage["requests"]
    assert round(case_estimated_cost, 8) == outcome.aggregate["estimated_cost"]
    assert outcome.run.cost["estimated"] == outcome.aggregate["estimated_cost"]
    assert outcome.aggregate["reliability"]["request_success_rate"] == 0.5


def test_request_cap_stops_before_additional_adapter_calls(tmp_path: Path) -> None:
    config = _config(limits=replace(_config().limits, max_requests=3))
    outcome = _runner(tmp_path).run(config)

    assert outcome.aggregate["request_count"] == 3
    assert outcome.aggregate["reliability"]["budget_stop_count"] == len(outcome.cases) - 3
    assert all(case.provider_error_code == "budget_stopped" for case in outcome.cases[3:])


def test_cost_cap_stops_before_case_that_would_exceed_it(tmp_path: Path) -> None:
    config = _config(limits=replace(_config().limits, max_estimated_cost=0.0025))
    outcome = _runner(tmp_path).run(config)

    successes = [case for case in outcome.cases if case.status == "success"]
    assert len(successes) == 2
    assert outcome.aggregate["estimated_cost"] == 0.002
    assert outcome.aggregate["reliability"]["budget_stop_count"] == len(outcome.cases) - 2


def test_context_and_output_bounds_are_enforced(tmp_path: Path) -> None:
    limits = replace(_config().limits, max_context_chars=80, max_output_chars=32)
    outcome = _runner(tmp_path).run(_config(limits=limits))
    long_case = next(case for case in outcome.cases if case.case_id == "long_context_bounded")

    assert long_case.metrics["context_was_truncated"] is True
    assert long_case.redacted_response is not None
    assert len(long_case.redacted_response) <= 32


def test_redaction_masks_secret_shapes_and_local_paths() -> None:
    secret = "sk-" + "x" * 16
    auth_header = "Authorization" + ": " + "Bearer " + "tokenvalue123"
    local_path = "/" + "home/example/private.txt"
    value = f"{auth_header} {secret} {local_path}"

    redacted = redact_text(value, max_chars=500)

    assert secret not in redacted
    assert "tokenvalue123" not in redacted
    assert local_path not in redacted
    assert redacted.count("[REDACTED_SECRET]") >= 1
    assert "[REDACTED_LOCAL_PATH]" in redacted


def test_fake_run_is_deterministic_except_explicit_identity_and_clock(tmp_path: Path) -> None:
    first = _runner(tmp_path / "first").run(_config())
    second = _runner(tmp_path / "second").run(_config())

    assert [case.to_dict() for case in first.cases] == [case.to_dict() for case in second.cases]
    assert first.aggregate == second.aggregate
    assert first.run.configuration_fingerprint == second.run.configuration_fingerprint


def test_provider_eval_package_has_no_network_or_secret_environment_access() -> None:
    package_root = Path(__file__).parents[1] / "app" / "evaluation" / "provider_eval"
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(package_root.glob("*.py")))

    assert "urllib.request" not in source
    assert "httpx" not in source
    assert "requests." not in source
    assert "socket." not in source
    assert "os.getenv" not in source
    assert "os.environ" not in source
