from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.evaluation.tutor_full_corpus import (  # noqa: E402
    FullCorpusTutorEvaluationRunner,
    load_full_corpus_tutor_cases,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local-only full-corpus Tutor evaluation.")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=REPOSITORY_ROOT / "backend/tests/fixtures/evaluation/full_corpus_tutor_cases.json",
    )
    parser.add_argument(
        "--article-store",
        type=Path,
        default=REPOSITORY_ROOT / ".local_data/scientific_spaces/corpus/pilot/article_store/articles.json",
    )
    parser.add_argument(
        "--rag-index-dir",
        type=Path,
        default=REPOSITORY_ROOT / ".local_data/scientific_spaces/rag/full_corpus",
    )
    parser.add_argument(
        "--graph-dir",
        type=Path,
        default=REPOSITORY_ROOT / ".local_data/scientific_spaces/graph/full_corpus",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / ".local_data/scientific_spaces/evaluation/tutor_full_corpus/summary.json",
    )
    parser.add_argument("--provider", choices=("fake", "openai"), default="fake")
    parser.add_argument("--allow-real-provider", action="store_true")
    parser.add_argument("--max-failed-ids", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        cases = load_full_corpus_tutor_cases(args.fixture)
        result = FullCorpusTutorEvaluationRunner(
            cases=cases,
            article_store_path=args.article_store,
            rag_index_dir=args.rag_index_dir,
            graph_dir=args.graph_dir,
            provider=args.provider,
            allow_real_provider=args.allow_real_provider,
            max_failed_ids=args.max_failed_ids,
        ).run(output_path=args.output)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": result["status"],
                "case_count": result["case_count"],
                "hard_metric_failure_count": len(result["hard_metric_failures"]),
                "evaluation_validity_failure_count": len(result["evaluation_validity_failures"]),
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
