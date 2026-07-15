from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from app.evaluation.provider_eval.models import (
    CASE_SET_SCHEMA_VERSION,
    DATA_CLASSIFICATIONS,
    TASK_TYPES,
    EvidenceSnippet,
    EvaluationLimits,
    PreflightPlan,
    ProviderEvaluationCase,
    ProviderEvaluationCaseSet,
    ProviderEvaluationConfig,
    RequestEnvelope,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local_data" / "scientific_spaces" / "evaluation" / "real_provider"
DEFAULT_CASE_SET_ROOT = REPO_ROOT / "backend" / "tests" / "fixtures" / "evaluation"

MAX_REQUESTS = 100
MAX_CONTEXT_CHARS = 50_000
MAX_OUTPUT_CHARS = 10_000
MAX_TIMEOUT_SECONDS = 120.0
MAX_RETRIES = 3
MAX_ESTIMATED_COST = 1_000.0
MAX_INSTRUCTION_CHARS = 2_000
MAX_SNIPPET_CHARS = 4_000

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_ALLOWED_CASE_SET_KEYS = {"schema_version", "case_set_id", "cases"}
_ALLOWED_CASE_KEYS = {
    "case_id",
    "task_type",
    "instruction",
    "expected_mode",
    "expected_source_ids",
    "expected_refusal",
    "allowed_source_count",
    "sensitive_data_classification",
    "evidence",
    "fake_outcomes",
    "fake_response",
    "fake_source_ids",
    "fake_latency_ms",
    "estimated_cost",
    "human_review_rubric",
}
_ALLOWED_EVIDENCE_KEYS = {"source_id", "title", "section", "snippet"}
_REQUEST_TOP_LEVEL_KEYS = {
    "schema_version",
    "case_id",
    "task_type",
    "instruction",
    "protocol",
    "data_classification",
    "evidence",
}
_REQUEST_PROTOCOL_KEYS = {
    "expected_mode",
    "expected_refusal",
    "max_sources",
    "max_context_chars",
    "max_output_chars",
}
_REQUEST_EVIDENCE_KEYS = {"source_id", "title", "section", "untrusted_excerpt"}
_UNSAFE_TEXT_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)authorization\s*:\s*[^\s]+(?:\s+[^\s]+)?"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~-]{8,}"),
    re.compile(r"(?<!:)\/(?:home|Users|tmp|var|etc)\/[^\s\]\[(){}<>\"']+"),
    re.compile(r"\b[A-Za-z]:\\[^\s\]\[(){}<>\"']+"),
)


class EvaluationPolicyError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ValidatedOutputPath:
    root: Path
    output_dir: Path


def validate_case_set_path(
    path: Path | str,
    *,
    allowed_case_set_root: Path | str = DEFAULT_CASE_SET_ROOT,
) -> Path:
    raw_root = Path(allowed_case_set_root).expanduser()
    raw_source = Path(path).expanduser()
    if raw_root.is_symlink() or raw_source.is_symlink():
        raise EvaluationPolicyError("validation_error", "Case-set paths cannot be symlinks")
    root = raw_root.resolve()
    source = raw_source.resolve()
    try:
        relative = source.relative_to(root)
    except ValueError as exc:
        raise EvaluationPolicyError("validation_error", "Case set must remain under the approved fixture root") from exc
    _reject_symlink_chain(root, relative)
    if not source.is_file() or source.suffix != ".json":
        raise EvaluationPolicyError("validation_error", "Case set must be an approved JSON fixture")
    return source


def load_case_set(path: Path | str) -> ProviderEvaluationCaseSet:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    _require_exact_keys(payload, _ALLOWED_CASE_SET_KEYS, "case set")
    if payload.get("schema_version") != CASE_SET_SCHEMA_VERSION:
        raise EvaluationPolicyError("validation_error", "Unsupported provider evaluation case-set schema")

    case_set_id = _required_string(payload, "case_set_id", "case set")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise EvaluationPolicyError("validation_error", "Case set must contain at least one case")

    cases = tuple(_parse_case(item) for item in raw_cases)
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise EvaluationPolicyError("validation_error", "Case IDs must be unique")
    return ProviderEvaluationCaseSet(case_set_id=case_set_id, cases=cases)


def validate_preflight(
    config: ProviderEvaluationConfig,
    case_set: ProviderEvaluationCaseSet,
    output_dir: Path | str,
    *,
    allowed_output_root: Path | str = DEFAULT_OUTPUT_ROOT,
) -> tuple[PreflightPlan, ValidatedOutputPath]:
    if config.provider_kind not in {"fake", "real"}:
        raise EvaluationPolicyError("validation_error", "Provider kind must be fake or real")
    if not config.dry_run:
        raise EvaluationPolicyError("validation_error", "P3-004 permits dry-run execution only")
    if config.case_set_id != case_set.case_set_id:
        raise EvaluationPolicyError("validation_error", "Configured case-set identity does not match the fixture")
    if config.endpoint_category not in {"embedding", "chat", "combined"}:
        raise EvaluationPolicyError("validation_error", "Unsupported endpoint category")
    if not config.provider_name.strip() or not config.model_name.strip():
        raise EvaluationPolicyError("validation_error", "Provider and model names are required")
    _validate_safe_text(config.provider_name, "provider name")
    _validate_safe_text(config.model_name, "model name")
    if config.model_version_identifier:
        _validate_safe_text(config.model_version_identifier, "model version")
    if config.pricing_metadata_source:
        _validate_safe_text(config.pricing_metadata_source, "pricing metadata source")

    _validate_limits(config.limits, real_mode=config.provider_kind == "real")
    _validate_output_policy(config)
    _validate_data_categories(config, case_set)
    validated_path = validate_output_path(output_dir, allowed_output_root=allowed_output_root)

    if config.provider_kind == "real":
        _validate_real_consent_and_pricing(config)

    plan = PreflightPlan(
        provider_kind=config.provider_kind,
        provider_name=config.provider_name,
        model_name=config.model_name,
        endpoint_category=config.endpoint_category,
        case_set_id=config.case_set_id,
        case_count=len(case_set.cases),
        max_requests=config.limits.max_requests,
        max_estimated_cost=config.limits.max_estimated_cost,
        currency=config.limits.currency,
        max_context_chars=config.limits.max_context_chars,
        max_output_chars=config.limits.max_output_chars,
        timeout_seconds=config.limits.timeout_seconds,
        max_retries=config.limits.max_retries,
        pricing_metadata_source=config.pricing_metadata_source,
        pricing_as_of=config.pricing_as_of,
        data_categories_sent=config.data_categories_sent,
        snippet_policy="bounded approved public-corpus excerpts delimited as untrusted evidence",
        output_location="ignored local evaluation root",
        excluded_data=(
            "credentials and authorization headers",
            "private user and learning data",
            "private Zotero metadata",
            "complete corpus and arbitrary files",
        ),
        adapter_construction_authorized=config.provider_kind == "fake",
        network_authorized=False,
    )
    return plan, validated_path


def build_request_envelope(case: ProviderEvaluationCase, limits: EvaluationLimits) -> RequestEnvelope:
    remaining = limits.max_context_chars
    evidence: list[dict[str, str]] = []
    truncated = False
    for item in case.evidence[: case.allowed_source_count]:
        bounded = item.snippet[: min(MAX_SNIPPET_CHARS, remaining)]
        if len(bounded) < len(item.snippet):
            truncated = True
        remaining -= len(bounded)
        evidence.append(
            {
                "source_id": item.source_id,
                "title": item.title,
                "section": item.section,
                "untrusted_excerpt": (
                    "<<<UNTRUSTED_ARTICLE_EVIDENCE>>>\n"
                    f"{bounded}\n"
                    "<<<END_UNTRUSTED_ARTICLE_EVIDENCE>>>"
                ),
            }
        )
        if remaining <= 0:
            if len(case.evidence) > len(evidence):
                truncated = True
            break

    envelope = RequestEnvelope(
        case_id=case.case_id,
        task_type=case.task_type,
        instruction=case.instruction,
        expected_mode=case.expected_mode,
        expected_refusal=case.expected_refusal,
        max_sources=case.allowed_source_count,
        max_context_chars=limits.max_context_chars,
        max_output_chars=limits.max_output_chars,
        data_classification=case.sensitive_data_classification,
        evidence=tuple(evidence),
        context_was_truncated=truncated,
    )
    validate_request_envelope(envelope.to_dict())
    return envelope


def validate_request_envelope(payload: dict[str, Any]) -> None:
    _require_exact_keys(payload, _REQUEST_TOP_LEVEL_KEYS, "request envelope")
    protocol = payload.get("protocol")
    if not isinstance(protocol, dict):
        raise EvaluationPolicyError("validation_error", "Request protocol must be an object")
    _require_exact_keys(protocol, _REQUEST_PROTOCOL_KEYS, "request protocol")
    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise EvaluationPolicyError("validation_error", "Request evidence must be a list")
    for item in evidence:
        if not isinstance(item, dict):
            raise EvaluationPolicyError("validation_error", "Request evidence entries must be objects")
        _require_exact_keys(item, _REQUEST_EVIDENCE_KEYS, "request evidence")


def configuration_fingerprint(config: ProviderEvaluationConfig) -> str:
    safe_payload = {
        "provider_kind": config.provider_kind,
        "provider_name": config.provider_name,
        "model_name": config.model_name,
        "model_version_identifier": config.model_version_identifier,
        "endpoint_category": config.endpoint_category,
        "case_set_id": config.case_set_id,
        "data_categories_sent": list(config.data_categories_sent),
        "limits": {
            "max_requests": config.limits.max_requests,
            "max_estimated_cost": config.limits.max_estimated_cost,
            "currency": config.limits.currency,
            "max_context_chars": config.limits.max_context_chars,
            "max_output_chars": config.limits.max_output_chars,
            "timeout_seconds": config.limits.timeout_seconds,
            "max_retries": config.limits.max_retries,
        },
        "pricing_metadata_source": config.pricing_metadata_source,
        "pricing_as_of": config.pricing_as_of,
        "output_policy": config.output_policy.to_dict(),
    }
    serialized = json.dumps(safe_payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_output_path(
    output_dir: Path | str,
    *,
    allowed_output_root: Path | str = DEFAULT_OUTPUT_ROOT,
) -> ValidatedOutputPath:
    raw_root = Path(allowed_output_root).expanduser()
    raw_candidate = Path(output_dir).expanduser()
    if raw_root.is_symlink() or raw_candidate.is_symlink():
        raise EvaluationPolicyError("validation_error", "Evaluation output paths cannot be symlinks")
    root = raw_root.resolve()
    candidate = raw_candidate.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise EvaluationPolicyError("validation_error", "Output must remain under the evaluation root") from exc

    _reject_symlink_chain(root, relative)
    if candidate == root:
        raise EvaluationPolicyError("validation_error", "Output directory must identify a run container")
    return ValidatedOutputPath(root=root, output_dir=candidate)


def _parse_case(payload: Any) -> ProviderEvaluationCase:
    if not isinstance(payload, dict):
        raise EvaluationPolicyError("validation_error", "Each case must be an object")
    _require_exact_keys(payload, _ALLOWED_CASE_KEYS, "case")

    task_type = _required_string(payload, "task_type", "case")
    if task_type not in TASK_TYPES:
        raise EvaluationPolicyError("validation_error", f"Unsupported task type: {task_type}")
    classification = _required_string(payload, "sensitive_data_classification", "case")
    if classification not in DATA_CLASSIFICATIONS:
        raise EvaluationPolicyError("validation_error", "Private or unknown case data is prohibited")

    instruction = _required_string(payload, "instruction", "case")
    if len(instruction) > MAX_INSTRUCTION_CHARS:
        raise EvaluationPolicyError("validation_error", "Case instruction exceeds the fixed bound")
    _validate_safe_text(instruction, "case instruction")

    raw_evidence = payload.get("evidence")
    if not isinstance(raw_evidence, list):
        raise EvaluationPolicyError("validation_error", "Case evidence must be a list")
    evidence = tuple(_parse_evidence(item) for item in raw_evidence)
    allowed_source_count = _required_nonnegative_int(payload, "allowed_source_count", "case")
    if allowed_source_count > len(evidence):
        raise EvaluationPolicyError("validation_error", "Allowed source count exceeds available evidence")

    fake_outcomes = _required_string_tuple(payload, "fake_outcomes", "case")
    allowed_outcomes = {
        "success",
        "timeout",
        "rate_limited",
        "auth_error",
        "server_error",
        "malformed_response",
        "validation_error",
    }
    if not fake_outcomes or not set(fake_outcomes) <= allowed_outcomes:
        raise EvaluationPolicyError("validation_error", "Case contains an unsupported fake outcome")

    fake_latency_ms = _required_number(payload, "fake_latency_ms", "case")
    estimated_cost = _required_number(payload, "estimated_cost", "case")
    if fake_latency_ms < 0 or estimated_cost < 0:
        raise EvaluationPolicyError("validation_error", "Latency and estimated cost cannot be negative")

    fake_response = _required_string(payload, "fake_response", "case", allow_empty=True)
    _validate_safe_text(fake_response, "fake response")
    return ProviderEvaluationCase(
        case_id=_required_string(payload, "case_id", "case"),
        task_type=task_type,
        instruction=instruction,
        expected_mode=_required_string(payload, "expected_mode", "case"),
        expected_source_ids=_required_string_tuple(payload, "expected_source_ids", "case"),
        expected_refusal=_required_bool(payload, "expected_refusal", "case"),
        allowed_source_count=allowed_source_count,
        sensitive_data_classification=classification,
        evidence=evidence,
        fake_outcomes=fake_outcomes,
        fake_response=fake_response,
        fake_source_ids=_required_string_tuple(payload, "fake_source_ids", "case"),
        fake_latency_ms=fake_latency_ms,
        estimated_cost=estimated_cost,
        human_review_rubric=_required_string_tuple(payload, "human_review_rubric", "case"),
    )


def _parse_evidence(payload: Any) -> EvidenceSnippet:
    if not isinstance(payload, dict):
        raise EvaluationPolicyError("validation_error", "Evidence entries must be objects")
    _require_exact_keys(payload, _ALLOWED_EVIDENCE_KEYS, "evidence")
    values = {
        key: _required_string(payload, key, "evidence", allow_empty=key == "snippet")
        for key in _ALLOWED_EVIDENCE_KEYS
    }
    for key, value in values.items():
        _validate_safe_text(value, f"evidence {key}")
    return EvidenceSnippet(
        source_id=values["source_id"],
        title=values["title"],
        section=values["section"],
        snippet=values["snippet"],
    )


def _validate_limits(limits: EvaluationLimits, *, real_mode: bool) -> None:
    if not 0 < limits.max_requests <= MAX_REQUESTS:
        raise EvaluationPolicyError("budget_invalid", f"max_requests must be between 1 and {MAX_REQUESTS}")
    if not 0 < limits.max_context_chars <= MAX_CONTEXT_CHARS:
        raise EvaluationPolicyError("budget_invalid", "Context limit must be positive and bounded")
    if not 0 < limits.max_output_chars <= MAX_OUTPUT_CHARS:
        raise EvaluationPolicyError("budget_invalid", "Output limit must be positive and bounded")
    if not 0 < limits.timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise EvaluationPolicyError("budget_invalid", "Timeout must be positive and bounded")
    if not 0 <= limits.max_retries <= MAX_RETRIES:
        raise EvaluationPolicyError("budget_invalid", "Retry count must be bounded")
    if limits.retry_backoff_seconds < 0:
        raise EvaluationPolicyError("budget_invalid", "Retry backoff cannot be negative")
    if not _CURRENCY_RE.fullmatch(limits.currency):
        raise EvaluationPolicyError("budget_invalid", "Currency must be a three-letter ISO code")
    if limits.max_estimated_cost < 0 or limits.max_estimated_cost > MAX_ESTIMATED_COST:
        raise EvaluationPolicyError("budget_invalid", "Estimated-cost cap is invalid")
    if real_mode and limits.max_estimated_cost <= 0:
        raise EvaluationPolicyError("budget_invalid", "Real-mode preflight requires a positive cost cap")


def _validate_output_policy(config: ProviderEvaluationConfig) -> None:
    policy = config.output_policy
    if not policy.redaction_enabled or policy.raw_output_enabled:
        raise EvaluationPolicyError("validation_error", "P3-004 requires redaction with raw output disabled")
    if policy.redacted_retention_days != 30 or policy.raw_retention_days is not None:
        raise EvaluationPolicyError("validation_error", "P3-004 retention policy must remain 30-day redacted/raw-off")


def _validate_data_categories(config: ProviderEvaluationConfig, case_set: ProviderEvaluationCaseSet) -> None:
    if not config.data_categories_sent:
        raise EvaluationPolicyError("validation_error", "At least one approved data category is required")
    if not set(config.data_categories_sent) <= DATA_CLASSIFICATIONS:
        raise EvaluationPolicyError("validation_error", "Private or unknown data categories are prohibited")
    case_categories = {case.sensitive_data_classification for case in case_set.cases}
    if not case_categories <= set(config.data_categories_sent):
        raise EvaluationPolicyError("validation_error", "Case-set data categories exceed the declaration")


def _validate_real_consent_and_pricing(config: ProviderEvaluationConfig) -> None:
    if not config.consent.complete:
        raise EvaluationPolicyError("consent_missing", "All real-provider consent acknowledgements are required")
    if not config.pricing_metadata_source or not config.pricing_as_of:
        raise EvaluationPolicyError("budget_invalid", "Known pricing source and date are required")
    try:
        date.fromisoformat(config.pricing_as_of)
    except ValueError as exc:
        raise EvaluationPolicyError("budget_invalid", "Pricing date must use ISO YYYY-MM-DD") from exc


def _reject_symlink_chain(root: Path, relative: Path) -> None:
    if root.exists() and root.is_symlink():
        raise EvaluationPolicyError("validation_error", "Evaluation root cannot be a symlink")
    current = root
    for part in relative.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise EvaluationPolicyError("validation_error", "Evaluation output cannot traverse a symlink")


def _validate_safe_text(value: str, label: str) -> None:
    if any(pattern.search(value) for pattern in _UNSAFE_TEXT_PATTERNS):
        raise EvaluationPolicyError("validation_error", f"{label} contains prohibited secret or local-path material")


def _require_exact_keys(payload: dict[str, Any], allowed: set[str], label: str) -> None:
    keys = set(payload)
    if keys != allowed:
        unexpected = sorted(keys - allowed)
        missing = sorted(allowed - keys)
        raise EvaluationPolicyError(
            "validation_error",
            f"Invalid {label} keys; unexpected={unexpected}, missing={missing}",
        )


def _required_string(payload: dict[str, Any], key: str, label: str, *, allow_empty: bool = False) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise EvaluationPolicyError("validation_error", f"{label}.{key} must be a string")
    return value


def _required_string_tuple(payload: dict[str, Any], key: str, label: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise EvaluationPolicyError("validation_error", f"{label}.{key} must be a string list")
    return tuple(value)


def _required_nonnegative_int(payload: dict[str, Any], key: str, label: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EvaluationPolicyError("validation_error", f"{label}.{key} must be a nonnegative integer")
    return value


def _required_bool(payload: dict[str, Any], key: str, label: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise EvaluationPolicyError("validation_error", f"{label}.{key} must be boolean")
    return value


def _required_number(payload: dict[str, Any], key: str, label: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise EvaluationPolicyError("validation_error", f"{label}.{key} must be numeric")
    return float(value)
