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

from app.corpus.materialization import (  # noqa: E402
    DEFAULT_ARTICLE_STORE_PATH,
    DEFAULT_LOCAL_LIBRARY_DIR,
    LocalCorpusMaterializationConfig,
    materialize_local_corpus,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize local Markdown files from the runtime Article store.")
    parser.add_argument("--article-store-path", type=Path, default=DEFAULT_ARTICLE_STORE_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_LOCAL_LIBRARY_DIR)
    args = parser.parse_args()

    summary = materialize_local_corpus(
        LocalCorpusMaterializationConfig(article_store_path=args.article_store_path, output_dir=args.output_dir)
    )
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
