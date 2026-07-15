from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

from app.evaluation.provider_eval.models import ProviderEvaluationOutcome
from app.evaluation.provider_eval.policy import EvaluationPolicyError, ValidatedOutputPath


_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)authorization\s*:\s*[^\s]+(?:\s+[^\s]+)?"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~-]{8,}"),
)
_UNIX_PATH_RE = re.compile(r"(?<!:)\/(?:home|Users|tmp|var|etc)\/[^\s\]\[(){}<>\"']+")
_WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s\]\[(){}<>\"']+")


def redact_text(value: str, *, max_chars: int) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    redacted = _UNIX_PATH_RE.sub("[REDACTED_LOCAL_PATH]", redacted)
    redacted = _WINDOWS_PATH_RE.sub("[REDACTED_LOCAL_PATH]", redacted)
    return redacted[:max_chars]


def write_outcome_artifacts(
    outcome: ProviderEvaluationOutcome,
    validated_path: ValidatedOutputPath,
) -> Path:
    run_dir = validated_path.output_dir / outcome.run.run_id
    _ensure_safe_child(run_dir, validated_path.root)
    run_dir.mkdir(parents=True, exist_ok=False)

    _write_json_atomic(run_dir / "run.json", outcome.run.to_dict())
    _write_jsonl_atomic(run_dir / "cases.jsonl", (case.to_dict() for case in outcome.cases))
    _write_json_atomic(run_dir / "aggregate.json", outcome.aggregate)
    if (run_dir / "raw").exists():
        raise EvaluationPolicyError("validation_error", "Raw output must remain disabled")
    return run_dir


def _write_json_atomic(path: Path, payload: Any) -> None:
    _write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _write_jsonl_atomic(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    _write_text_atomic(path, content)


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _ensure_safe_child(path: Path, root: Path) -> None:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise EvaluationPolicyError("validation_error", "Output escaped the evaluation root") from exc
    current = resolved_root
    for part in relative.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise EvaluationPolicyError("validation_error", "Output cannot traverse a symlink")
