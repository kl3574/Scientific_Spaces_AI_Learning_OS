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

from app.evaluation.runner import DEFAULT_FIXTURE_DIR, EvaluationRunner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic RAG/Tutor evaluation baseline.")
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=DEFAULT_FIXTURE_DIR,
        help="Directory containing articles.json and expected_cases.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path. Must be under eval_outputs/ or evaluation_outputs/.",
    )
    args = parser.parse_args()

    suite = EvaluationRunner(args.fixture_dir).run()
    if args.output:
        output_path = _validated_output_path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(suite.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    metrics = suite.metrics
    print("RAG/Tutor Evaluation Baseline")
    print(f"Cases: {metrics.case_count}")
    print(f"Retrieval hit@k: {_pct(metrics.retrieval_hit_at_k)}")
    print(f"Citation required pass rate: {_pct(metrics.citation_required_pass_rate)}")
    print(f"No-source refusal rate: {_pct(metrics.no_source_refusal_rate)}")
    print(f"Source schema valid rate: {_pct(metrics.source_schema_valid_rate)}")
    print(f"No fake source rate: {_pct(metrics.no_fake_source_rate)}")
    print(f"Quiz source coverage: {_pct(metrics.quiz_question_sources_rate)}")
    print(f"Research local-only checks: {'PASS' if metrics.research_local_only_rate == 1.0 else 'FAIL'}")
    print(f"Unsupported answer fabrications: {metrics.no_source_answer_fabrication_count}")
    print(f"Answers without sources: {metrics.answer_without_sources_count}")
    print(f"Quiz without sources: {metrics.quiz_without_sources_count}")
    print(f"Overall: {'PASS' if suite.passed else 'FAIL'}")
    return 0 if suite.passed else 1


def _validated_output_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    allowed_dirs = {"eval_outputs", "evaluation_outputs"}
    if not any(part in allowed_dirs for part in resolved.parts):
        raise SystemExit("--output must be under eval_outputs/ or evaluation_outputs/")
    if resolved.suffix not in {".json", ".jsonl"} and not resolved.name.endswith(".eval.json"):
        raise SystemExit("--output must be a JSON or JSONL file")
    return resolved


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


if __name__ == "__main__":
    raise SystemExit(main())
