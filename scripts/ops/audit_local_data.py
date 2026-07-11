from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.operations.health import audit_storage_capacity
from app.operations.inventory import build_local_data_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit local Scientific Spaces data assets.")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-write", action="store_true", help="Inspect without updating the runtime manifest.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_local_data_manifest(
        args.data_root,
        manifest_path=args.manifest_path,
        workers=args.workers,
        write=not args.no_write,
    )
    capacity = audit_storage_capacity(args.data_root)
    payload = {
        "status": "WARN" if capacity.status == "WARN" else "PASS",
        "manifest": manifest.to_dict(),
        "capacity": capacity.to_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
