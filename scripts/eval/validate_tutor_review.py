#!/usr/bin/env python3
"""Validate the synthetic affine review candidate without writing or approving it."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.evaluation.tutor_review import DEFAULT_CANDIDATE_DIR, validate_review_candidate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    args = parser.parse_args()
    result = validate_review_candidate(args.candidate_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
