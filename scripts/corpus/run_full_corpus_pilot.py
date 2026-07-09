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

from app.corpus.pilot import DEFAULT_OUTPUT_DIR, FullCorpusPilot, PilotConfig  # noqa: E402
from app.corpus.seeds import load_seed_urls  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded Scientific Spaces full-corpus pilot.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max-limit", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--delay-seconds", type=float, default=3)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--feed-url", default="https://spaces.ac.cn/feed")
    parser.add_argument("--seed-file", type=Path, default=None)
    parser.add_argument("--manual-url", action="append", default=[])
    args = parser.parse_args()

    seed_urls = load_seed_urls(args.seed_file) if args.seed_file else []
    config = PilotConfig(
        limit=args.limit,
        max_limit=args.max_limit,
        concurrency=args.concurrency,
        delay_seconds=args.delay_seconds,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        feed_url=args.feed_url,
        seed_urls=tuple(seed_urls),
        manual_urls=tuple(args.manual_url),
    )
    summary = FullCorpusPilot(config).run()
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 1 if summary.status == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
