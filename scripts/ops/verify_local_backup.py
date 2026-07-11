from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.operations.backup import verify_backup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a Scientific Spaces local backup archive.")
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = verify_backup(args.backup, workers=args.workers)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
