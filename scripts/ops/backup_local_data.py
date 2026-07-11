from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.operations.backup import create_backup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a private local data backup archive.")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--profile", choices=("essential", "complete"), default="essential")
    pdf = parser.add_mutually_exclusive_group()
    pdf.add_argument("--include-pdf", dest="include_pdf", action="store_true")
    pdf.add_argument("--exclude-pdf", dest="include_pdf", action="store_false")
    parser.set_defaults(include_pdf=None)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.profile == "complete" and args.include_pdf is None:
        parser.error("complete profile requires --include-pdf or --exclude-pdf")
    if args.profile == "essential" and args.include_pdf:
        parser.error("essential profile cannot use --include-pdf")
    if args.include_pdf is None:
        args.include_pdf = False
    return args


def main() -> int:
    args = parse_args()
    result = create_backup(
        args.data_root,
        args.output_dir,
        profile=args.profile,
        include_pdf=args.include_pdf,
        workers=args.workers,
        verify=args.verify,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
