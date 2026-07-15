from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


RUN_SCHEMA_VERSION = "provider-evaluation-run/v1"
CASE_SCHEMA_VERSION = "provider-evaluation-case/v1"
CASE_SET_SCHEMA_VERSION = "provider-evaluation-case-set/v1"
REQUEST_SCHEMA_VERSION = "provider-evaluation-request/v1"

TASK_TYPES = frozenset(
    {
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
)
DATA_CLASSIFICATIONS = frozenset({"public_fixture", "local_corpus_excerpt"})
CASE_STATUSES = frozenset(
    {"success", "timeout", "rate_limited", "provider_error", "validation_error", "budget_skipped"}
)
TERMINAL_ERROR_CLASSES = frozenset(
    {
        "consent_missing",
        "budget_invalid",
        "budget_stopped",
        "timeout",
        "rate_limited",
        "auth_error",
        "server_error",
        "malformed_response",
        "validation_error",
    }
)


@dataclass(frozen=True)
class ConsentRecord:
    real_provider_acknowledged: bool = False
    data_sent_acknowledged: bool = False
    public_data_only_acknowledged: bool = False

    @property
    def complete(self) -> bool:
        return all(
            (
                self.real_provider_acknowledged,
                self.data_sent_acknowledged,
                self.public_data_only_acknowledged,
            )
        )

    def to_dict(self) -> dict[str, bool]:
        return {
            "real_provider_acknowledged": self.real_provider_acknowledged,
            "data_sent_acknowledged": self.data_sent_acknowledged,
            "public_data_only_acknowledged": self.public_data_only_acknowledged,
        }


@dataclass(frozen=True)
class EvaluationLimits:
    max_requests: int
    max_estimated_cost: float
    currency: str
    max_context_chars: int
    max_output_chars: int
    timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: float = 0.0

    def retry_settings(self) -> dict[str, int | float]:
        return {
            "max_retries": self.max_retries,
            "backoff_seconds": self.retry_backoff_seconds,
        }


@dataclass(frozen=True)
class OutputPolicy:
    redaction_enabled: bool = True
    raw_output_enabled: bool = False
    redacted_retention_days: int = 30
    raw_retention_days: int | None = None
    aggregate_retention: str = "until_operator_deletion"

    def to_dict(self) -> dict[str, Any]:
        return {
            "redaction_enabled": self.redaction_enabled,
            "raw_output_enabled": self.raw_output_enabled,
            "redacted_retention_days": self.redacted_retention_days,
            "raw_retention_days": self.raw_retention_days,
            "aggregate_retention": self.aggregate_retention,
        }


@dataclass(frozen=True)
class ProviderEvaluationConfig:
    provider_kind: str
    provider_name: str
    model_name: str
    model_version_identifier: str | None
    endpoint_category: str
    case_set_id: str
    dry_run: bool
    consent: ConsentRecord
    data_categories_sent: tuple[str, ...]
    limits: EvaluationLimits
    output_policy: OutputPolicy = field(default_factory=OutputPolicy)
    pricing_metadata_source: str | None = None
    pricing_as_of: str | None = None
    embedding_dimension: int | None = None


@dataclass(frozen=True)
class EvidenceSnippet:
    source_id: str
    title: str
    section: str
    snippet: str


@dataclass(frozen=True)
class ProviderEvaluationCase:
    case_id: str
    task_type: str
    instruction: str
    expected_mode: str
    expected_source_ids: tuple[str, ...]
    expected_refusal: bool
    allowed_source_count: int
    sensitive_data_classification: str
    evidence: tuple[EvidenceSnippet, ...]
    fake_outcomes: tuple[str, ...]
    fake_response: str
    fake_source_ids: tuple[str, ...]
    fake_latency_ms: float
    estimated_cost: float
    human_review_rubric: tuple[str, ...]


@dataclass(frozen=True)
class ProviderEvaluationCaseSet:
    case_set_id: str
    cases: tuple[ProviderEvaluationCase, ...]


@dataclass(frozen=True)
class RequestEnvelope:
    case_id: str
    task_type: str
    instruction: str
    expected_mode: str
    expected_refusal: bool
    max_sources: int
    max_context_chars: int
    max_output_chars: int
    data_classification: str
    evidence: tuple[dict[str, str], ...]
    context_was_truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": REQUEST_SCHEMA_VERSION,
            "case_id": self.case_id,
            "task_type": self.task_type,
            "instruction": self.instruction,
            "protocol": {
                "expected_mode": self.expected_mode,
                "expected_refusal": self.expected_refusal,
                "max_sources": self.max_sources,
                "max_context_chars": self.max_context_chars,
                "max_output_chars": self.max_output_chars,
            },
            "data_classification": self.data_classification,
            "evidence": [dict(item) for item in self.evidence],
        }


@dataclass(frozen=True)
class AdapterResponse:
    response_text: str
    source_ids: tuple[str, ...]
    latency_ms: float
    input_tokens: int
    output_tokens: int
    embedding_tokens: int = 0
    provider_reported_cost: float | None = None


@dataclass(frozen=True)
class ProviderEvaluationCaseResult:
    run_id: str
    case_id: str
    task_type: str
    expected_mode: str
    expected_source_ids: tuple[str, ...]
    expected_refusal: bool
    allowed_source_count: int
    sensitive_data_classification: str
    request_index: int
    status: str
    latency_ms: float | None
    retry_count: int
    usage: dict[str, int]
    estimated_cost: float | None
    source_ids_returned: tuple[str, ...]
    metrics: dict[str, Any]
    response_digest: str | None
    redacted_response: str | None
    provider_error_code: str | None
    human_review: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CASE_SCHEMA_VERSION,
            "run_id": self.run_id,
            "case_id": self.case_id,
            "task_type": self.task_type,
            "expected_mode": self.expected_mode,
            "expected_source_ids": list(self.expected_source_ids),
            "expected_refusal": self.expected_refusal,
            "allowed_source_count": self.allowed_source_count,
            "sensitive_data_classification": self.sensitive_data_classification,
            "request_index": self.request_index,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "retry_count": self.retry_count,
            "usage": dict(self.usage),
            "estimated_cost": self.estimated_cost,
            "source_ids_returned": list(self.source_ids_returned),
            "metrics": dict(self.metrics),
            "response_digest": self.response_digest,
            "redacted_response": self.redacted_response,
            "provider_error_code": self.provider_error_code,
            "human_review": dict(self.human_review),
        }


@dataclass(frozen=True)
class ProviderEvaluationRun:
    run_id: str
    provider_kind: str
    provider_name: str
    model_name: str
    model_version_identifier: str | None
    endpoint_category: str
    requested_at: str
    completed_at: str | None
    configuration_fingerprint: str
    embedding_dimension: int | None
    context_limit: int
    output_limit: int
    retry_settings: dict[str, int | float]
    timeout_seconds: float
    pricing_metadata_source: str | None
    consent: dict[str, bool]
    data_categories_sent: tuple[str, ...]
    case_set_id: str
    case_count: int
    max_requests: int
    max_estimated_cost: float
    currency: str
    provider_reported_usage: dict[str, int]
    cost: dict[str, Any]
    result_counts: dict[str, int]
    status: str
    output_policy: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RUN_SCHEMA_VERSION,
            "run_id": self.run_id,
            "provider_kind": self.provider_kind,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "model_version_identifier": self.model_version_identifier,
            "endpoint_category": self.endpoint_category,
            "requested_at": self.requested_at,
            "completed_at": self.completed_at,
            "configuration_fingerprint": self.configuration_fingerprint,
            "embedding_dimension": self.embedding_dimension,
            "context_limit": self.context_limit,
            "output_limit": self.output_limit,
            "retry_settings": dict(self.retry_settings),
            "timeout_seconds": self.timeout_seconds,
            "pricing_metadata_source": self.pricing_metadata_source,
            "consent": dict(self.consent),
            "data_categories_sent": list(self.data_categories_sent),
            "case_set_id": self.case_set_id,
            "case_count": self.case_count,
            "max_requests": self.max_requests,
            "max_estimated_cost": self.max_estimated_cost,
            "currency": self.currency,
            "provider_reported_usage": dict(self.provider_reported_usage),
            "cost": dict(self.cost),
            "result_counts": dict(self.result_counts),
            "status": self.status,
            "output_policy": dict(self.output_policy),
        }


@dataclass(frozen=True)
class PreflightPlan:
    provider_kind: str
    provider_name: str
    model_name: str
    endpoint_category: str
    case_set_id: str
    case_count: int
    max_requests: int
    max_estimated_cost: float
    currency: str
    max_context_chars: int
    max_output_chars: int
    timeout_seconds: float
    max_retries: int
    pricing_metadata_source: str | None
    pricing_as_of: str | None
    data_categories_sent: tuple[str, ...]
    snippet_policy: str
    output_location: str
    excluded_data: tuple[str, ...]
    adapter_construction_authorized: bool
    network_authorized: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_kind": self.provider_kind,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "endpoint_category": self.endpoint_category,
            "case_set_id": self.case_set_id,
            "case_count": self.case_count,
            "max_requests": self.max_requests,
            "max_estimated_cost": self.max_estimated_cost,
            "currency": self.currency,
            "max_context_chars": self.max_context_chars,
            "max_output_chars": self.max_output_chars,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "pricing_metadata_source": self.pricing_metadata_source,
            "pricing_as_of": self.pricing_as_of,
            "data_categories_sent": list(self.data_categories_sent),
            "snippet_policy": self.snippet_policy,
            "output_location": self.output_location,
            "excluded_data": list(self.excluded_data),
            "adapter_construction_authorized": self.adapter_construction_authorized,
            "network_authorized": self.network_authorized,
        }


@dataclass(frozen=True)
class ProviderEvaluationOutcome:
    run: ProviderEvaluationRun
    cases: tuple[ProviderEvaluationCaseResult, ...]
    aggregate: dict[str, Any]
    preflight: PreflightPlan
    output_dir: Path | None


AdapterFactory = Callable[[ProviderEvaluationConfig], Any]
