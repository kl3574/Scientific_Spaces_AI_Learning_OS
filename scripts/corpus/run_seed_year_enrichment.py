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

from app.corpus.inventory import DEFAULT_INVENTORY_OUTPUT_DIR  # noqa: E402
from app.corpus.year_enrichment import DEFAULT_ARCHIVE_INDEX_URL, enrich_seed_year_metadata  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Scientific Spaces seed year metadata enrichment.")
    parser.add_argument("--seed-file", type=Path, required=True)
    parser.add_argument("--archive-url", default=DEFAULT_ARCHIVE_INDEX_URL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_INVENTORY_OUTPUT_DIR)
    parser.add_argument("--offline-archive-html", type=Path)
    parser.add_argument("--live-archive-index-fetch", action="store_true")
    parser.add_argument("--no-live-fetch", action="store_true")
    args = parser.parse_args()

    if args.offline_archive_html and args.live_archive_index_fetch:
        parser.error("--offline-archive-html and --live-archive-index-fetch are mutually exclusive")

    archive_html = None
    archive_source = None
    if args.offline_archive_html:
        archive_html = args.offline_archive_html.read_text(encoding="utf-8")
        archive_source = str(args.offline_archive_html)
    elif args.no_live_fetch:
        archive_source = "not provided"

    summary = enrich_seed_year_metadata(
        args.seed_file,
        archive_html=archive_html,
        archive_url=args.archive_url,
        archive_index_source=archive_source,
        live_archive_index_fetch=args.live_archive_index_fetch,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 1 if summary.status == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
