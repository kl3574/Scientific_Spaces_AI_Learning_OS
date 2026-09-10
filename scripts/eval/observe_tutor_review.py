#!/usr/bin/env python3
"""Offline product-request observations for the pending human review candidate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.evaluation.tutor_review_observation import (  # noqa: E402
    DEFAULT_CANDIDATE_DIR, observe_candidate, write_review_observation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New ignored eval_outputs/tutor_generation/review-observation- directory")
    args = parser.parse_args()
    summary, rows = observe_candidate(args.candidate_dir)
    summary["output_audit"] = write_review_observation(summary, rows, output_dir=args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
