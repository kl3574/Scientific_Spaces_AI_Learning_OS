"""Fail-closed fake/dry-run provider evaluation boundary."""

from app.evaluation.provider_eval.adapters import FakeProviderEvaluationAdapter, ProviderAdapterError
from app.evaluation.provider_eval.models import (
    ConsentRecord,
    EvaluationLimits,
    OutputPolicy,
    ProviderEvaluationConfig,
    ProviderEvaluationOutcome,
)
from app.evaluation.provider_eval.policy import EvaluationPolicyError, load_case_set
from app.evaluation.provider_eval.runner import ProviderEvaluationRunner

__all__ = [
    "ConsentRecord",
    "EvaluationLimits",
    "EvaluationPolicyError",
    "FakeProviderEvaluationAdapter",
    "OutputPolicy",
    "ProviderAdapterError",
    "ProviderEvaluationConfig",
    "ProviderEvaluationOutcome",
    "ProviderEvaluationRunner",
    "load_case_set",
]
