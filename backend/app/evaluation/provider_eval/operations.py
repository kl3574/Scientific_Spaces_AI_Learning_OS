from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.evaluation.provider_eval.policy import EvaluationPolicyError


_REQUIRED_RUN_FILES = {"run.json", "aggregate.json"}
_ALLOWED_RUN_FILES = _REQUIRED_RUN_FILES | {"cases.jsonl"}
_FORBIDDEN_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pdf",
    ".html",
    ".zip",
    ".tar",
    ".trace",
    ".prof",
}
_FORBIDDEN_KEYS = {
    "api_key",
    "authorization",
    "auth_header",
    "full_prompt",
    "local_path",
    "private_zotero",
    "learning_state",
    "tutor_history",
}
MAX_AUDIT_FILE_BYTES = 5 * 1024 * 1024
_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)authorization\s*:\s*[^\s]+(?:\s+[^\s]+)?"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~-]{8,}"),
)
_ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"(?<!:)\/(?:home|Users|tmp|var|etc)\/[^\s\]\[(){}<>\"']+"),
    re.compile(r"\b[A-Za-z]:\\[^\s\]\[(){}<>\"']+"),
)


@dataclass(frozen=True)
class AuditResult:
    passed: bool
    run_count: int
    file_count: int
    findings: tuple[str, ...]
    file_digests: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "run_count": self.run_count,
            "file_count": self.file_count,
            "findings": list(self.findings),
            "file_digests": dict(self.file_digests),
        }


@dataclass(frozen=True)
class CleanupPlan:
    root: Path
    targets: tuple[Path, ...]
    reason: str
    dry_run: bool

    def relative_targets(self) -> tuple[str, ...]:
        return tuple(str(path.relative_to(self.root)) for path in self.targets)


def audit_evaluation_output(root: Path | str) -> AuditResult:
    raw_root = Path(root).expanduser()
    if raw_root.is_symlink():
        raise EvaluationPolicyError("validation_error", "Evaluation output root cannot be a symlink")
    output_root = raw_root.resolve()
    if not output_root.exists():
        return AuditResult(passed=True, run_count=0, file_count=0, findings=(), file_digests={})
    _assert_safe_tree(output_root, output_root)

    findings: list[str] = []
    digests: dict[str, str] = {}
    run_dirs = sorted(path.parent for path in output_root.rglob("run.json"))
    for run_dir in run_dirs:
        relative_run = str(run_dir.relative_to(output_root))
        entries = {path.name for path in run_dir.iterdir()}
        unexpected = entries - _ALLOWED_RUN_FILES
        if unexpected:
            findings.append(f"{relative_run}: unexpected entries {sorted(unexpected)}")
        missing = _REQUIRED_RUN_FILES - entries
        if missing:
            findings.append(f"{relative_run}: missing entries {sorted(missing)}")

    files = sorted(path for path in output_root.rglob("*") if path.is_file())
    for path in files:
        relative = str(path.relative_to(output_root))
        if path.suffix.lower() in _FORBIDDEN_SUFFIXES:
            findings.append(f"{relative}: forbidden artifact type")
        if path.stat().st_size > MAX_AUDIT_FILE_BYTES:
            findings.append(f"{relative}: file exceeds the bounded audit size")
            continue
        content = path.read_text(encoding="utf-8")
        digests[relative] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        for pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(f"{relative}: possible secret or authorization value")
                break
        for pattern in _ABSOLUTE_PATH_PATTERNS:
            if pattern.search(content):
                findings.append(f"{relative}: local absolute path")
                break
        _scan_json_keys(path, content, findings, relative)

    return AuditResult(
        passed=not findings,
        run_count=len(run_dirs),
        file_count=len(files),
        findings=tuple(findings),
        file_digests=digests,
    )


def plan_retention_cleanup(
    root: Path | str,
    *,
    now: datetime | None = None,
    older_than_days: int = 30,
    run_id: str | None = None,
    delete_run: bool = False,
    execute: bool = False,
) -> CleanupPlan:
    if older_than_days < 0:
        raise EvaluationPolicyError("validation_error", "Retention age cannot be negative")
    raw_root = Path(root).expanduser()
    if raw_root.is_symlink():
        raise EvaluationPolicyError("validation_error", "Evaluation output root cannot be a symlink")
    output_root = raw_root.resolve()
    if not output_root.exists():
        return CleanupPlan(root=output_root, targets=(), reason="no output root", dry_run=not execute)
    _assert_safe_tree(output_root, output_root)
    current_time = now or datetime.now(timezone.utc)

    candidates: list[Path] = []
    run_dirs = sorted(path.parent for path in output_root.rglob("run.json"))
    if run_id is not None:
        run_dirs = [path for path in run_dirs if path.name == run_id]
        if not run_dirs:
            raise EvaluationPolicyError("validation_error", "Requested run ID was not found")
        if len(run_dirs) > 1:
            raise EvaluationPolicyError("validation_error", "Requested run ID is ambiguous")

    for run_dir in run_dirs:
        _assert_safe_path(run_dir, output_root)
        if delete_run:
            if run_id is None:
                raise EvaluationPolicyError("validation_error", "Deleting a full run requires an explicit run ID")
            candidates.append(run_dir)
            continue

        run_file = run_dir / "run.json"
        if run_file.stat().st_size > MAX_AUDIT_FILE_BYTES:
            raise EvaluationPolicyError("validation_error", "Run metadata exceeds the bounded operation size")
        run_payload = json.loads(run_file.read_text(encoding="utf-8"))
        terminal_time = run_payload.get("completed_at") or run_payload.get("requested_at")
        if not isinstance(terminal_time, str):
            raise EvaluationPolicyError("validation_error", "Run timestamp is missing")
        timestamp = datetime.fromisoformat(terminal_time.replace("Z", "+00:00"))
        age_days = (current_time - timestamp.astimezone(timezone.utc)).days
        if age_days >= older_than_days:
            cases_file = run_dir / "cases.jsonl"
            if cases_file.exists():
                candidates.append(cases_file)

    return CleanupPlan(
        root=output_root,
        targets=tuple(candidates),
        reason="explicit run deletion" if delete_run else f"redacted output age >= {older_than_days} days",
        dry_run=not execute,
    )


def apply_cleanup(plan: CleanupPlan) -> tuple[str, ...]:
    if plan.dry_run:
        return ()
    removed: list[str] = []
    for target in plan.targets:
        _assert_safe_path(target, plan.root)
        relative = str(target.relative_to(plan.root))
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)
        removed.append(relative)
    return tuple(removed)


def _scan_json_keys(path: Path, content: str, findings: list[str], relative: str) -> None:
    rows: list[Any]
    try:
        if path.suffix == ".jsonl":
            rows = [json.loads(line) for line in content.splitlines() if line.strip()]
        elif path.suffix == ".json":
            rows = [json.loads(content)]
        else:
            return
    except json.JSONDecodeError:
        findings.append(f"{relative}: invalid JSON")
        return

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key).lower() in _FORBIDDEN_KEYS:
                    findings.append(f"{relative}: forbidden field {key}")
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    for row in rows:
        visit(row)


def _assert_safe_tree(path: Path, root: Path) -> None:
    _assert_safe_path(path, root)
    for candidate in path.rglob("*"):
        if candidate.is_symlink():
            raise EvaluationPolicyError("validation_error", "Evaluation output cannot contain symlinks")
        _assert_safe_path(candidate, root)


def _assert_safe_path(path: Path, root: Path) -> None:
    resolved_root = root.resolve()
    if path.is_symlink():
        raise EvaluationPolicyError("validation_error", "Evaluation operation refuses symlinks")
    try:
        path.resolve().relative_to(resolved_root)
    except ValueError as exc:
        raise EvaluationPolicyError("validation_error", "Evaluation operation escaped its configured root") from exc
