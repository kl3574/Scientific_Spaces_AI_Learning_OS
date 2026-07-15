from __future__ import annotations

from typing import Protocol

from app.evaluation.provider_eval.models import (
    AdapterResponse,
    ProviderEvaluationCase,
    ProviderEvaluationConfig,
    RequestEnvelope,
)


class ProviderAdapterError(RuntimeError):
    def __init__(self, error_class: str) -> None:
        super().__init__(error_class)
        self.error_class = error_class


class ProviderEvaluationAdapter(Protocol):
    def execute(
        self,
        envelope: RequestEnvelope,
        case: ProviderEvaluationCase,
        *,
        attempt_index: int,
    ) -> AdapterResponse:
        """Execute one bounded evaluation attempt."""


class FakeProviderEvaluationAdapter:
    """Deterministic adapter with no credential or network capability."""

    def __init__(self, config: ProviderEvaluationConfig) -> None:
        if config.provider_kind != "fake":
            raise ValueError("The fake adapter accepts provider_kind=fake only")
        self.config = config

    def execute(
        self,
        envelope: RequestEnvelope,
        case: ProviderEvaluationCase,
        *,
        attempt_index: int,
    ) -> AdapterResponse:
        outcome_index = min(attempt_index, len(case.fake_outcomes) - 1)
        outcome = case.fake_outcomes[outcome_index]
        if outcome != "success":
            raise ProviderAdapterError(outcome)

        context_chars = sum(len(item["untrusted_excerpt"]) for item in envelope.evidence)
        response = case.fake_response[: self.config.limits.max_output_chars]
        return AdapterResponse(
            response_text=response,
            source_ids=case.fake_source_ids[: case.allowed_source_count],
            latency_ms=case.fake_latency_ms,
            input_tokens=max(1, (len(case.instruction) + context_chars) // 4),
            output_tokens=max(1, len(response) // 4),
            embedding_tokens=0,
            provider_reported_cost=None,
        )
