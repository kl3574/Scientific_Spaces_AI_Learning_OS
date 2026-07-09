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

from app.corpus.audit import LocalCorpusAuditConfig, audit_local_corpus  # noqa: E402
from app.corpus.materialization import DEFAULT_ARTICLE_STORE_PATH, DEFAULT_LOCAL_LIBRARY_DIR  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit local corpus materialization without source access.")
    parser.add_argument("--article-store-path", type=Path, default=DEFAULT_ARTICLE_STORE_PATH)
    parser.add_argument("--local-library-dir", type=Path, default=DEFAULT_LOCAL_LIBRARY_DIR)
    parser.add_argument("--sample-size", type=int, default=5)
    args = parser.parse_args()

    summary = audit_local_corpus(
        LocalCorpusAuditConfig(
            article_store_path=args.article_store_path,
            local_library_dir=args.local_library_dir,
            sample_size=args.sample_size,
        )
    )
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 1 if summary.status == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
