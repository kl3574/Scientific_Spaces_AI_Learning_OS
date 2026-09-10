#!/usr/bin/env python3
"""Observe synthetic Tutor generation through the product service, without networking."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.evaluation.tutor_generation import run_evaluation, write_evaluation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="New directory beneath eval_outputs/tutor_generation")
    parser.add_argument("--baseline", type=Path, help="Previously captured five-mode synthetic baseline JSON")
    args = parser.parse_args()
    baseline = None
    if args.baseline:
        if args.baseline.stat().st_size > 1_000_000:
            parser.error("Baseline capture exceeds the bounded input size")
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    summary, rows = run_evaluation(baseline=baseline)
    if args.output_dir:
        summary["output_audit"] = write_evaluation(summary, rows, output_dir=args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["contract_results"]["status"] == summary["fixture_results"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
