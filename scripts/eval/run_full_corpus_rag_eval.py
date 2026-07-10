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

from app.evaluation.full_corpus import (  # noqa: E402
    FullCorpusEvaluationRunner,
    FullCorpusRetrievalCase,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local full-corpus RAG retrieval smoke tests.")
    parser.add_argument("--article-store", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, required=True)
    parser.add_argument(
        "--expected-article-count",
        type=int,
        default=1311,
        help="Strict input corpus count; defaults to the completed 1311-Article corpus.",
    )
    parser.add_argument(
        "--cases-file",
        type=Path,
        default=None,
        help="Optional JSON list of retrieval cases; defaults to the 12-case full-corpus suite.",
    )
    args = parser.parse_args()

    cases = None
    if args.cases_file:
        payload = json.loads(args.cases_file.read_text(encoding="utf-8"))
        cases = [FullCorpusRetrievalCase.from_dict(item) for item in payload]
    result = FullCorpusEvaluationRunner(
        article_store_path=args.article_store,
        index_dir=args.index_dir,
        cases=cases,
        expected_article_count=args.expected_article_count,
    ).run()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
