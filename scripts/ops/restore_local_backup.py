from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.operations.restore import restore_backup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore a local backup into an isolated directory.")
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--target-dir", type=Path, required=True)
    parser.add_argument("--protected-data-root", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = restore_backup(
        args.backup,
        args.target_dir,
        overwrite=args.overwrite,
        verify=args.verify,
        protected_data_root=args.protected_data_root,
        workers=args.workers,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
