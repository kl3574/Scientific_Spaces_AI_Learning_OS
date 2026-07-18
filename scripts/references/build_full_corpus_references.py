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

from app.references.full_corpus import (  # noqa: E402
    EXPECTED_INTERRUPTION_EXIT_CODE,
    ControlledInterruption,
    FullCorpusReferenceConfig,
    FullCorpusReferenceError,
    run_full_corpus_reference_build,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the deterministic P3-006 offline full-corpus Reference Store."
    )
    parser.add_argument("--article-store", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-article-count", type=int, required=True)
    parser.add_argument("--expected-article-store-sha256", required=True)
    parser.add_argument("--expected-corpus-fingerprint", required=True)
    parser.add_argument("--checkpoint-every", type=int, default=50)
    parser.add_argument("--simulate-interruption-after", type=int)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--resume", action="store_true")
    mode.add_argument("--rebuild", action="store_true")
    parser.add_argument("--no-network", action="store_true", required=True)
    args = parser.parse_args()

    config = FullCorpusReferenceConfig(
        article_store=args.article_store,
        output_dir=args.output_dir,
        expected_article_count=args.expected_article_count,
        expected_article_store_sha256=args.expected_article_store_sha256,
        expected_corpus_fingerprint=args.expected_corpus_fingerprint,
        checkpoint_every=args.checkpoint_every,
        resume=args.resume,
        rebuild=args.rebuild,
        simulate_interruption_after=args.simulate_interruption_after,
        no_network=args.no_network,
    )
    try:
        result = run_full_corpus_reference_build(config)
    except ControlledInterruption as exc:
        print(json.dumps(exc.evidence, ensure_ascii=False, sort_keys=True, indent=2))
        return EXPECTED_INTERRUPTION_EXIT_CODE
    except (FullCorpusReferenceError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result.status in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
