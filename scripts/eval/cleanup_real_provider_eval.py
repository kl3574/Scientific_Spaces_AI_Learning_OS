#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.evaluation.provider_eval.operations import apply_cleanup, plan_retention_cleanup  # noqa: E402
from app.evaluation.provider_eval.policy import DEFAULT_OUTPUT_ROOT, EvaluationPolicyError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or execute path-confined provider evaluation cleanup.")
    parser.add_argument("--older-than-days", type=int, default=30)
    parser.add_argument("--run-id")
    parser.add_argument("--delete-run", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Apply the plan; the default is dry-run.")
    args = parser.parse_args()

    try:
        plan = plan_retention_cleanup(
            DEFAULT_OUTPUT_ROOT,
            older_than_days=args.older_than_days,
            run_id=args.run_id,
            delete_run=args.delete_run,
            execute=args.execute,
        )
        removed = apply_cleanup(plan)
    except (EvaluationPolicyError, OSError, ValueError) as exc:
        code = getattr(exc, "code", "validation_error")
        print(f"Cleanup blocked: {code}: {exc}", file=sys.stderr)
        return 2

    mode = "DRY RUN" if plan.dry_run else "EXECUTED"
    print(f"Provider evaluation cleanup: {mode}")
    print(f"Reason: {plan.reason}")
    for target in plan.relative_targets():
        print(f"Target: {target}")
    print(f"Removed: {len(removed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
