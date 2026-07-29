#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.operations.derived_refresh import (  # noqa: E402
    DEFAULT_TARGET_ARCHIVE_IDS,
    DerivedRefreshConfig,
    DerivedRefreshError,
    refresh_derived_assets,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh local RAG, Graph, and Reference assets from an exact Article Store."
    )
    parser.add_argument("--article-store", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--expected-article-count", type=int, required=True)
    parser.add_argument("--expected-article-store-sha256", required=True)
    parser.add_argument("--expected-corpus-fingerprint", required=True)
    parser.add_argument("--target-archive-id", action="append", dest="target_archive_ids")
    parser.add_argument("--checkpoint-every", type=int, default=50)
    parser.add_argument("--minimum-review-cases", type=int, default=60)
    parser.add_argument("--min-available-disk-bytes", type=int, default=0)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Build, validate, back up, and install. The default is a read-only dry-run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    code_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    config = DerivedRefreshConfig(
        article_store=args.article_store,
        data_root=args.data_root,
        expected_article_count=args.expected_article_count,
        expected_article_store_sha256=args.expected_article_store_sha256,
        expected_corpus_fingerprint=args.expected_corpus_fingerprint,
        target_archive_ids=tuple(args.target_archive_ids or DEFAULT_TARGET_ARCHIVE_IDS),
        execute=args.execute,
        checkpoint_every=args.checkpoint_every,
        minimum_review_cases=args.minimum_review_cases,
        min_available_disk_bytes=args.min_available_disk_bytes,
        code_commit=code_commit,
    )
    try:
        result = refresh_derived_assets(config)
    except (DerivedRefreshError, ValueError) as exc:
        payload = {
            "status": "BLOCKED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "evidence": exc.evidence if isinstance(exc, DerivedRefreshError) else {},
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
