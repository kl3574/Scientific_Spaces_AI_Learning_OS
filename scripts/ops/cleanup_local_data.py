from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.operations.cleanup import VALID_CATEGORIES, cleanup_local_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely clean selected local runtime data categories.")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--category", action="append", choices=sorted(VALID_CATEGORIES), required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true", help="Apply the deletion plan.")
    mode.add_argument("--dry-run", action="store_true", help="Print the plan without deleting (default).")
    parser.add_argument("--confirm-derived-delete", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = cleanup_local_data(
        args.data_root,
        categories=args.category,
        execute=args.execute,
        confirm_derived_delete=args.confirm_derived_delete,
    )
    print(json.dumps(result.to_dict(data_root=args.data_root.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
