#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.export.local_pdf import (  # noqa: E402
    DEFAULT_ARTICLE_STORE_PATH,
    DEFAULT_OUTPUT_DIR,
    PdfExportConfig,
    export_local_pdf_library,
)


def build_parser() -> argparse.ArgumentParser:
    default_article_store = Path(
        os.getenv("SCIENTIFIC_SPACES_ARTICLE_STORE", str(DEFAULT_ARTICLE_STORE_PATH))
    )
    default_output_dir = Path(
        os.getenv("SCIENTIFIC_SPACES_PDF_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR))
    )
    default_mode = os.getenv("SCIENTIFIC_SPACES_PDF_MODE", "offline")
    default_workers = int(os.getenv("SCIENTIFIC_SPACES_PDF_WORKERS", "2"))
    parser = argparse.ArgumentParser(
        description="Export the local Scientific Spaces Article corpus to offline PDFs."
    )
    parser.add_argument("--article-store", type=Path, default=default_article_store)
    parser.add_argument("--markdown-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=default_output_dir)
    parser.add_argument("--mode", choices=("offline", "source-probe"), default=default_mode)
    parser.add_argument("--article-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse validated PDFs with matching content/template/renderer versions.",
    )
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--workers", type=int, default=default_workers)
    parser.add_argument("--allow-source-access", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    return parser


def _progress(payload: dict[str, object]) -> None:
    completed = int(payload["completed"])
    selected = int(payload["selected"])
    if completed == selected or completed == 1 or completed % 25 == 0:
        print(
            (
                f"[pdf-export] {completed}/{selected} "
                f"exported={payload['exported']} regenerated={payload['regenerated']} "
                f"unchanged={payload['unchanged']} failed={payload['failed']}"
            ),
            file=sys.stderr,
            flush=True,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = PdfExportConfig(
            article_store_path=args.article_store,
            markdown_dir=args.markdown_dir,
            output_dir=args.output_dir,
            mode=args.mode,
            article_id=args.article_id,
            limit=args.limit,
            resume=args.resume,
            rebuild=args.rebuild,
            workers=args.workers,
            allow_source_access=args.allow_source_access,
            delay_seconds=args.delay_seconds,
        )
        summary = export_local_pdf_library(config=config, progress_callback=_progress)
    except (OSError, RuntimeError, ValueError, NotImplementedError) as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return 0 if summary.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
