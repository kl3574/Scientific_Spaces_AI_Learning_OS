from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.persistence.learning_migrator import migrate_sqlite_to_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate LearningStore SQLite -> JSON file.")
    parser.add_argument("--sqlite-path", type=Path, required=True, help="Source learning sqlite database.")
    parser.add_argument("--json-path", type=Path, required=True, help="Target learning.json file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = migrate_sqlite_to_json(args.sqlite_path, args.json_path)
    except Exception as exc:
        print(f"migration failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
