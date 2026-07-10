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

from app.rag.full_corpus import build_full_corpus_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the local full-corpus FAISS index.")
    parser.add_argument("--article-store", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--provider", choices=("fake", "openai"), default="fake")
    parser.add_argument(
        "--expected-article-count",
        type=int,
        default=1311,
        help="Strict input corpus count; defaults to the completed 1311-Article corpus.",
    )
    parser.add_argument("--embedding-batch-size", type=int, default=128)
    parser.add_argument(
        "--embedding-dimension",
        type=int,
        default=None,
        help="Embedding dimension; defaults to 128 for fake and 1536 for openai.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Replace a stale index; an unchanged fingerprint still produces a no-op.",
    )
    parser.add_argument(
        "--allow-real-provider",
        action="store_true",
        help="Required with provider=openai; disabled in CI and never enabled by default.",
    )
    args = parser.parse_args()

    result = build_full_corpus_index(
        article_store_path=args.article_store,
        output_dir=args.output_dir,
        provider_name=args.provider,
        rebuild=args.rebuild,
        embedding_batch_size=args.embedding_batch_size,
        embedding_dimension=args.embedding_dimension,
        expected_article_count=args.expected_article_count,
        allow_real_provider=args.allow_real_provider,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
