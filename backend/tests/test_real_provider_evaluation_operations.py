from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.evaluation.provider_eval.operations import (
    apply_cleanup,
    audit_evaluation_output,
    plan_retention_cleanup,
)
from app.evaluation.provider_eval.policy import EvaluationPolicyError


def _write_run(root: Path, run_id: str, completed_at: str) -> Path:
    run_dir = root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(
        json.dumps({"run_id": run_id, "requested_at": completed_at, "completed_at": completed_at}),
        encoding="utf-8",
    )
    (run_dir / "cases.jsonl").write_text(json.dumps({"case_id": "safe"}) + "\n", encoding="utf-8")
    (run_dir / "aggregate.json").write_text(json.dumps({"network_request_count": 0}), encoding="utf-8")
    return run_dir


def test_retention_cleanup_defaults_to_dry_run_and_preserves_aggregate(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "old-run", "2026-06-01T00:00:00Z")
    now = datetime(2026, 7, 15, tzinfo=timezone.utc)

    plan = plan_retention_cleanup(tmp_path, now=now, older_than_days=30)
    removed = apply_cleanup(plan)

    assert plan.dry_run is True
    assert plan.relative_targets() == ("old-run/cases.jsonl",)
    assert removed == ()
    assert (run_dir / "cases.jsonl").exists()
    assert (run_dir / "aggregate.json").exists()


def test_retention_cleanup_execute_removes_only_redacted_cases(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "old-run", "2026-06-01T00:00:00Z")
    now = datetime(2026, 7, 15, tzinfo=timezone.utc)

    plan = plan_retention_cleanup(tmp_path, now=now, older_than_days=30, execute=True)
    removed = apply_cleanup(plan)

    assert removed == ("old-run/cases.jsonl",)
    assert not (run_dir / "cases.jsonl").exists()
    assert (run_dir / "run.json").exists()
    assert (run_dir / "aggregate.json").exists()
    assert audit_evaluation_output(tmp_path).passed is True


def test_full_run_deletion_requires_explicit_run_id(tmp_path: Path) -> None:
    _write_run(tmp_path, "old-run", "2026-06-01T00:00:00Z")

    with pytest.raises(EvaluationPolicyError, match="explicit run ID"):
        plan_retention_cleanup(tmp_path, delete_run=True)

    plan = plan_retention_cleanup(tmp_path, run_id="old-run", delete_run=True, execute=True)
    assert apply_cleanup(plan) == ("old-run",)
    assert not (tmp_path / "old-run").exists()


def test_cleanup_rejects_symlinks(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(EvaluationPolicyError, match="symlink"):
        plan_retention_cleanup(tmp_path)


def test_artifact_audit_rejects_raw_output_secret_and_local_path(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "unsafe-run", "2026-07-15T00:00:00Z")
    secret = "sk-" + "z" * 16
    (run_dir / "cases.jsonl").write_text(
        json.dumps({"redacted_response": f"{secret} /home/example/private.txt"}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "raw").mkdir()

    result = audit_evaluation_output(tmp_path)

    assert result.passed is False
    assert any("unexpected entries" in finding for finding in result.findings)
    assert any("possible secret" in finding for finding in result.findings)
    assert any("local absolute path" in finding for finding in result.findings)


def test_artifact_audit_reports_relative_paths_only(tmp_path: Path) -> None:
    _write_run(tmp_path, "safe-run", "2026-07-15T00:00:00Z")

    result = audit_evaluation_output(tmp_path)

    assert result.passed is True
    assert set(result.file_digests) == {
        "safe-run/run.json",
        "safe-run/cases.jsonl",
        "safe-run/aggregate.json",
    }
    assert str(tmp_path) not in json.dumps(result.to_dict())
