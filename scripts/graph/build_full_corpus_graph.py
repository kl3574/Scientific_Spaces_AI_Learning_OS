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

from app.graph.full_corpus import build_full_corpus_graph  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and audit the local full-corpus knowledge graph.")
    parser.add_argument("--article-store", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--expected-article-count",
        type=int,
        default=1311,
        help="Strict input corpus count; defaults to the completed 1311-Article corpus.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Atomically replace a stale graph; an unchanged corpus and extraction version produce a no-op.",
    )
    args = parser.parse_args()

    result = build_full_corpus_graph(
        article_store_path=args.article_store,
        output_dir=args.output_dir,
        rebuild=args.rebuild,
        expected_article_count=args.expected_article_count,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
