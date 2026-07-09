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

from app.corpus.inventory import DEFAULT_INVENTORY_OUTPUT_DIR, analyze_seed_inventory  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Scientific Spaces seed inventory dry-run.")
    parser.add_argument("--seed-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_INVENTORY_OUTPUT_DIR)
    parser.add_argument("--targets", default="200,400,700,1000,1326")
    parser.add_argument("--completed-count", type=int, default=100)
    parser.add_argument("--year-partition", default="true", choices=("true", "false"))
    args = parser.parse_args()

    targets = tuple(int(item.strip()) for item in args.targets.split(",") if item.strip())
    summary = analyze_seed_inventory(
        args.seed_file,
        output_dir=args.output_dir,
        cumulative_targets=targets,
        completed_count=args.completed_count,
    )
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 1 if summary.inventory_status == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
