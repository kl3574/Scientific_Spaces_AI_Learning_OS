#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.evaluation.provider_eval import (  # noqa: E402
    ConsentRecord,
    EvaluationLimits,
    EvaluationPolicyError,
    ProviderEvaluationConfig,
    ProviderEvaluationRunner,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the P3-004 fake evaluation or produce a no-network real-provider preflight plan."
    )
    parser.add_argument("--provider", choices=("fake", "real"), required=True)
    parser.add_argument("--provider-name")
    parser.add_argument("--model-name")
    parser.add_argument("--model-version")
    parser.add_argument("--endpoint-category", choices=("embedding", "chat", "combined"), default="combined")
    parser.add_argument("--case-set", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-requests", type=int, default=25)
    parser.add_argument("--max-estimated-cost", type=float, default=1.0)
    parser.add_argument("--currency", default="USD")
    parser.add_argument("--max-context-chars", type=int, default=512)
    parser.add_argument("--max-output-chars", type=int, default=1_000)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--pricing-source")
    parser.add_argument("--pricing-as-of")
    parser.add_argument("--data-category", action="append", dest="data_categories")
    parser.add_argument("--acknowledge-real-provider", action="store_true")
    parser.add_argument("--acknowledge-data-sent", action="store_true")
    parser.add_argument("--acknowledge-public-data-only", action="store_true")
    args = parser.parse_args()

    provider_name = args.provider_name or ("deterministic-fake" if args.provider == "fake" else "")
    model_name = args.model_name or ("fake-evaluation-v1" if args.provider == "fake" else "")
    data_categories = tuple(args.data_categories or ["public_fixture"])

    try:
        runner = ProviderEvaluationRunner(args.case_set, args.output_dir)
        config = ProviderEvaluationConfig(
            provider_kind=args.provider,
            provider_name=provider_name,
            model_name=model_name,
            model_version_identifier=args.model_version,
            endpoint_category=args.endpoint_category,
            case_set_id=runner.case_set.case_set_id,
            dry_run=args.dry_run,
            consent=ConsentRecord(
                real_provider_acknowledged=args.acknowledge_real_provider,
                data_sent_acknowledged=args.acknowledge_data_sent,
                public_data_only_acknowledged=args.acknowledge_public_data_only,
            ),
            data_categories_sent=data_categories,
            limits=EvaluationLimits(
                max_requests=args.max_requests,
                max_estimated_cost=args.max_estimated_cost,
                currency=args.currency,
                max_context_chars=args.max_context_chars,
                max_output_chars=args.max_output_chars,
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
            ),
            pricing_metadata_source=args.pricing_source,
            pricing_as_of=args.pricing_as_of,
        )
        outcome = runner.run(config)
    except (EvaluationPolicyError, OSError, ValueError, json.JSONDecodeError) as exc:
        code = getattr(exc, "code", "validation_error")
        print(f"Provider evaluation blocked: {code}: {exc}", file=sys.stderr)
        return 2

    print("P3-004 Provider Evaluation")
    print(json.dumps(outcome.preflight.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    print(f"Status: {outcome.run.status}")
    print(f"Network requests: {outcome.aggregate['network_request_count']}")
    print(f"Configured output: {args.output_dir}")
    if outcome.output_dir is not None:
        print(f"Artifacts: {args.output_dir}/{outcome.run.run_id}")
    else:
        print("Artifacts: none (preflight plan only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
