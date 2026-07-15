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

from app.evaluation.provider_eval.operations import audit_evaluation_output  # noqa: E402
from app.evaluation.provider_eval.policy import DEFAULT_OUTPUT_ROOT, EvaluationPolicyError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit ignored provider evaluation output for unsafe artifacts.")
    parser.parse_args()
    try:
        result = audit_evaluation_output(DEFAULT_OUTPUT_ROOT)
    except (EvaluationPolicyError, OSError, ValueError) as exc:
        code = getattr(exc, "code", "validation_error")
        print(f"Audit blocked: {code}: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
