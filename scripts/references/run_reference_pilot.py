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

from app.references.pilot import ReferencePilotConfig, run_reference_pilot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded, deterministic P3-003 offline reference pilot.")
    parser.add_argument("--article-store", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=75)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--no-network", action="store_true", required=True)
    args = parser.parse_args()
    result = run_reference_pilot(
        ReferencePilotConfig(
            article_store=args.article_store,
            output_dir=args.output_dir,
            sample_size=args.sample_size,
            no_network=args.no_network,
        )
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result.status in {"PASS", "PENDING_REVIEW"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
