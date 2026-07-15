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

from app.references.audit import audit_repository_artifacts  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit tracked P3-003 runtime/private artifacts and secrets.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--reference-store", type=Path, required=True)
    parser.add_argument("--redact", action="store_true", help="Retained for an explicit no-secret-output contract.")
    args = parser.parse_args()
    result = audit_repository_artifacts(args.repo_root, args.reference_store)
    print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
