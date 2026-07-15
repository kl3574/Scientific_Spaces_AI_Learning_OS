from __future__ import annotations

import hashlib
import math
import re
import statistics
import uuid
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.evaluation.provider_eval.adapters import (
    FakeProviderEvaluationAdapter,
    ProviderAdapterError,
    ProviderEvaluationAdapter,
)
from app.evaluation.provider_eval.models import (
    AdapterResponse,
    AdapterFactory,
    ProviderEvaluationCase,
    ProviderEvaluationCaseResult,
    ProviderEvaluationConfig,
    ProviderEvaluationOutcome,
    ProviderEvaluationRun,
)
from app.evaluation.provider_eval.output import redact_text, write_outcome_artifacts
from app.evaluation.provider_eval.policy import (
    DEFAULT_OUTPUT_ROOT,
    build_request_envelope,
    configuration_fingerprint,
    load_case_set,
    validate_case_set_path,
    validate_preflight,
)


Clock = Callable[[], datetime]
RunIdFactory = Callable[[], str]
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class ProviderEvaluationRunner:
    def __init__(
        self,
        case_set_path: Path | str,
        output_dir: Path | str,
        *,
        allowed_output_root: Path | str = DEFAULT_OUTPUT_ROOT,
        adapter_factory: AdapterFactory = FakeProviderEvaluationAdapter,
        clock: Clock | None = None,
        run_id_factory: RunIdFactory | None = None,
    ) -> None:
        validated_case_set = validate_case_set_path(case_set_path)
        self.case_set = load_case_set(validated_case_set)
        self.output_dir = Path(output_dir)
        self.allowed_output_root = Path(allowed_output_root)
        self.adapter_factory = adapter_factory
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.run_id_factory = run_id_factory or (lambda: uuid.uuid4().hex)

    def run(self, config: ProviderEvaluationConfig) -> ProviderEvaluationOutcome:
        preflight, validated_path = validate_preflight(
            config,
            self.case_set,
            self.output_dir,
            allowed_output_root=self.allowed_output_root,
        )
        requested_at = _timestamp(self.clock())
        run_id = self.run_id_factory()
        if not _RUN_ID_RE.fullmatch(run_id):
            raise ValueError("Run ID must be a bounded path-safe local identifier")

        if config.provider_kind == "real":
            run = self._build_run(
                config,
                run_id=run_id,
                requested_at=requested_at,
                completed_at=None,
                status="planned",
                usage=_empty_usage(),
                estimated_cost=0.0,
                result_counts={},
            )
            return ProviderEvaluationOutcome(
                run=run,
                cases=(),
                aggregate=_planned_aggregate(preflight.to_dict()),
                preflight=preflight,
                output_dir=None,
            )

        adapter = self.adapter_factory(config)
        cases, usage, estimated_cost, request_count = self._run_fake_cases(config, adapter)
        completed_at = _timestamp(self.clock())
        aggregate = _aggregate_results(cases, usage, estimated_cost, request_count)
        run = self._build_run(
            config,
            run_id=run_id,
            requested_at=requested_at,
            completed_at=completed_at,
            status="completed",
            usage=usage,
            estimated_cost=estimated_cost,
            result_counts=aggregate["result_counts"],
        )
        cases = tuple(replace(case, run_id=run_id) for case in cases)
        outcome = ProviderEvaluationOutcome(
            run=run,
            cases=cases,
            aggregate=aggregate,
            preflight=preflight,
            output_dir=None,
        )
        run_dir = write_outcome_artifacts(outcome, validated_path)
        return replace(outcome, output_dir=run_dir)

    def _run_fake_cases(
        self,
        config: ProviderEvaluationConfig,
        adapter: ProviderEvaluationAdapter,
    ) -> tuple[tuple[ProviderEvaluationCaseResult, ...], dict[str, int], float, int]:
        results: list[ProviderEvaluationCaseResult] = []
        usage = _empty_usage()
        estimated_cost = 0.0
        request_count = 0

        for case in self.case_set.cases:
            if request_count >= config.limits.max_requests:
                results.append(_budget_result(case, request_count + 1))
                continue

            envelope = build_request_envelope(case, config.limits)
            initial_request_index = request_count + 1
            attempts = 0
            case_cost = 0.0
            while True:
                if request_count >= config.limits.max_requests:
                    result = _budget_result(
                        case,
                        initial_request_index,
                        retry_count=max(0, attempts - 1),
                        requests_consumed=attempts,
                        estimated_cost=case_cost,
                    )
                    results.append(result)
                    _add_usage(usage, result.usage)
                    break
                if estimated_cost + case.estimated_cost > config.limits.max_estimated_cost:
                    result = _budget_result(
                        case,
                        initial_request_index,
                        retry_count=max(0, attempts - 1),
                        requests_consumed=attempts,
                        estimated_cost=case_cost,
                    )
                    results.append(result)
                    _add_usage(usage, result.usage)
                    break
                request_count += 1
                attempts += 1
                estimated_cost += case.estimated_cost
                case_cost += case.estimated_cost
                try:
                    response = adapter.execute(envelope, case, attempt_index=attempts - 1)
                    if response.latency_ms > config.limits.timeout_seconds * 1_000:
                        raise ProviderAdapterError("timeout")
                    result = _success_result(
                        case,
                        envelope.context_was_truncated,
                        response,
                        request_index=initial_request_index,
                        retry_count=attempts - 1,
                        requests_consumed=attempts,
                        estimated_cost=case_cost,
                        max_output_chars=config.limits.max_output_chars,
                    )
                    results.append(result)
                    _add_usage(usage, result.usage)
                    break
                except ProviderAdapterError as exc:
                    retryable = exc.error_class in {"timeout", "rate_limited", "server_error"}
                    can_retry = attempts <= config.limits.max_retries
                    if retryable and can_retry:
                        continue
                    result = _error_result(
                        case,
                        error_class=exc.error_class,
                        request_index=initial_request_index,
                        retry_count=attempts - 1,
                        requests_consumed=attempts,
                        estimated_cost=case_cost,
                    )
                    results.append(result)
                    _add_usage(usage, result.usage)
                    break

        return tuple(results), usage, round(estimated_cost, 8), request_count

    def _build_run(
        self,
        config: ProviderEvaluationConfig,
        *,
        run_id: str,
        requested_at: str,
        completed_at: str | None,
        status: str,
        usage: dict[str, int],
        estimated_cost: float,
        result_counts: dict[str, int],
    ) -> ProviderEvaluationRun:
        return ProviderEvaluationRun(
            run_id=run_id,
            provider_kind=config.provider_kind,
            provider_name=config.provider_name,
            model_name=config.model_name,
            model_version_identifier=config.model_version_identifier,
            endpoint_category=config.endpoint_category,
            requested_at=requested_at,
            completed_at=completed_at,
            configuration_fingerprint=configuration_fingerprint(config),
            embedding_dimension=config.embedding_dimension,
            context_limit=config.limits.max_context_chars,
            output_limit=config.limits.max_output_chars,
            retry_settings=config.limits.retry_settings(),
            timeout_seconds=config.limits.timeout_seconds,
            pricing_metadata_source=config.pricing_metadata_source,
            consent=config.consent.to_dict(),
            data_categories_sent=config.data_categories_sent,
            case_set_id=config.case_set_id,
            case_count=len(self.case_set.cases),
            max_requests=config.limits.max_requests,
            max_estimated_cost=config.limits.max_estimated_cost,
            currency=config.limits.currency,
            provider_reported_usage=dict(usage),
            cost={
                "provider_reported": None,
                "estimated": estimated_cost,
                "currency": config.limits.currency,
                "pricing_as_of": config.pricing_as_of,
                "assumption": "fixture estimate for fake runs; no business-value projection",
            },
            result_counts=dict(result_counts),
            status=status,
            output_policy=config.output_policy.to_dict(),
        )


def _success_result(
    case: ProviderEvaluationCase,
    context_was_truncated: bool,
    response: AdapterResponse,
    *,
    request_index: int,
    retry_count: int,
    requests_consumed: int,
    estimated_cost: float,
    max_output_chars: int,
) -> ProviderEvaluationCaseResult:
    response_text = response.response_text
    source_ids = response.source_ids
    evidence_ids = {item.source_id for item in case.evidence}
    if len(source_ids) > case.allowed_source_count or not set(source_ids) <= evidence_ids:
        return _error_result(
            case,
            error_class="validation_error",
            request_index=request_index,
            retry_count=retry_count,
            requests_consumed=requests_consumed,
            estimated_cost=estimated_cost,
        )

    refused = response_text.startswith("REFUSAL:")
    usage = {
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "embedding_tokens": response.embedding_tokens,
        "requests": requests_consumed,
    }
    return ProviderEvaluationCaseResult(
        run_id="pending",
        case_id=case.case_id,
        task_type=case.task_type,
        expected_mode=case.expected_mode,
        expected_source_ids=case.expected_source_ids,
        expected_refusal=case.expected_refusal,
        allowed_source_count=case.allowed_source_count,
        sensitive_data_classification=case.sensitive_data_classification,
        request_index=request_index,
        status="success",
        latency_ms=response.latency_ms,
        retry_count=retry_count,
        usage=usage,
        estimated_cost=round(estimated_cost, 8),
        source_ids_returned=source_ids,
        metrics={
            "metric_class": "automated_heuristic_not_human_correctness",
            "citation_schema_valid": set(source_ids) <= evidence_ids,
            "expected_sources_returned": set(case.expected_source_ids) <= set(source_ids),
            "refusal_expectation_met": refused == case.expected_refusal,
            "context_was_truncated": context_was_truncated,
        },
        response_digest=hashlib.sha256(response_text.encode("utf-8")).hexdigest(),
        redacted_response=redact_text(response_text, max_chars=max_output_chars),
        provider_error_code=None,
        human_review=_empty_human_review(case),
    )


def _error_result(
    case: ProviderEvaluationCase,
    *,
    error_class: str,
    request_index: int,
    retry_count: int,
    requests_consumed: int = 1,
    estimated_cost: float | None = None,
) -> ProviderEvaluationCaseResult:
    status = {
        "timeout": "timeout",
        "rate_limited": "rate_limited",
        "malformed_response": "validation_error",
        "validation_error": "validation_error",
    }.get(error_class, "provider_error")
    return ProviderEvaluationCaseResult(
        run_id="pending",
        case_id=case.case_id,
        task_type=case.task_type,
        expected_mode=case.expected_mode,
        expected_source_ids=case.expected_source_ids,
        expected_refusal=case.expected_refusal,
        allowed_source_count=case.allowed_source_count,
        sensitive_data_classification=case.sensitive_data_classification,
        request_index=request_index,
        status=status,
        latency_ms=None,
        retry_count=retry_count,
        usage={"input_tokens": 0, "output_tokens": 0, "embedding_tokens": 0, "requests": requests_consumed},
        estimated_cost=None if estimated_cost is None else round(estimated_cost, 8),
        source_ids_returned=(),
        metrics={"metric_class": "automated_heuristic_not_human_correctness"},
        response_digest=None,
        redacted_response=None,
        provider_error_code=error_class,
        human_review=_empty_human_review(case),
    )


def _budget_result(
    case: ProviderEvaluationCase,
    request_index: int,
    *,
    retry_count: int = 0,
    requests_consumed: int = 0,
    estimated_cost: float = 0.0,
) -> ProviderEvaluationCaseResult:
    result = _error_result(
        case,
        error_class="budget_stopped",
        request_index=request_index,
        retry_count=retry_count,
        requests_consumed=requests_consumed,
        estimated_cost=estimated_cost,
    )
    return replace(result, status="budget_skipped")


def _empty_human_review(case: ProviderEvaluationCase) -> dict[str, object]:
    return {
        "status": "not_reviewed",
        "rubric": list(case.human_review_rubric),
        "correctness": None,
        "relevance": None,
        "completeness": None,
        "mathematical_consistency": None,
        "clarity": None,
        "reviewer_disagreement": None,
    }


def _aggregate_results(
    cases: tuple[ProviderEvaluationCaseResult, ...],
    usage: dict[str, int],
    estimated_cost: float,
    request_count: int,
) -> dict[str, object]:
    status_counts = Counter(case.status for case in cases)
    error_counts = Counter(case.provider_error_code for case in cases if case.provider_error_code)
    latencies = [case.latency_ms for case in cases if case.latency_ms is not None]
    success_count = status_counts.get("success", 0)
    result_counts = {
        **{status: status_counts.get(status, 0) for status in sorted(status_counts)},
        "errors": sum(count for status, count in status_counts.items() if status != "success"),
        "refusals": sum(1 for case in cases if case.redacted_response and case.redacted_response.startswith("REFUSAL:")),
        "pending_human_review": len(cases),
    }
    return {
        "schema_version": "provider-evaluation-aggregate/v1",
        "case_count": len(cases),
        "request_count": request_count,
        "result_counts": result_counts,
        "terminal_error_counts": dict(sorted(error_counts.items())),
        "reliability": {
            "request_success_rate": success_count / request_count if request_count else 0.0,
            "timeout_count": status_counts.get("timeout", 0),
            "rate_limit_count": status_counts.get("rate_limited", 0),
            "retry_count": sum(case.retry_count for case in cases),
            "validation_error_count": status_counts.get("validation_error", 0),
            "budget_stop_count": status_counts.get("budget_skipped", 0),
        },
        "latency_ms": _latency_summary(latencies),
        "usage": dict(usage),
        "estimated_cost": estimated_cost,
        "quality": {
            "automated_heuristics_are_human_correctness": False,
            "human_review_completed": 0,
        },
        "network_request_count": 0,
        "raw_output_enabled": False,
    }


def _latency_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"minimum": None, "mean": None, "median": None, "p95": None, "maximum": None}
    ordered = sorted(values)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "minimum": min(ordered),
        "mean": statistics.fmean(ordered),
        "median": statistics.median(ordered),
        "p95": ordered[p95_index],
        "maximum": max(ordered),
    }


def _planned_aggregate(preflight: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "provider-evaluation-aggregate/v1",
        "status": "planned",
        "preflight": preflight,
        "network_request_count": 0,
        "adapter_construction_count": 0,
        "raw_output_enabled": False,
    }


def _empty_usage() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "embedding_tokens": 0, "requests": 0}


def _add_usage(aggregate: dict[str, int], usage: dict[str, int]) -> None:
    for key in aggregate:
        aggregate[key] += usage.get(key, 0)


def _timestamp(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc).replace(microsecond=0)
    return normalized.isoformat().replace("+00:00", "Z")
