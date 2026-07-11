from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.operations.health import check_local_system


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local corpus, derived assets, configuration, and capacity.")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = check_local_system(
        args.data_root,
        manifest_path=args.manifest_path,
        workers=args.workers,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.status == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
