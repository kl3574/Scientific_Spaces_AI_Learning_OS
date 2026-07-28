#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.export.browser_print import BrowserPrintConfig  # noqa: E402
from app.export.webbridge_print import (  # noqa: E402
    DEFAULT_WEBBRIDGE_SESSION,
    DEFAULT_WEBBRIDGE_URL,
    webbridge_session_factory,
)
from app.storage.article_store import ArticleStore, StoredArticle  # noqa: E402
from app.zotero.bulk_pdf import (  # noqa: E402
    BulkZoteroPdfSync,
    CheckpointJournal,
    ExclusiveRunLock,
    ProbeTier,
    file_sha256,
    run_throughput_probe,
    select_probe_articles,
    write_json_atomic,
)
from app.zotero.sync import (  # noqa: E402
    DEFAULT_COLLECTION_NAME,
    LocalZoteroSyncTransport,
    ZoteroSyncError,
)

RUNTIME_ROOT = (
    REPO_ROOT
    / ".local_data"
    / "scientific_spaces"
    / "zotero_pdf_sync"
)
DEFAULT_ARTICLE_STORE = (
    REPO_ROOT
    / ".local_data"
    / "scientific_spaces"
    / "corpus"
    / "pilot"
    / "article_store"
    / "articles.json"
)
DEFAULT_PROBE_EVIDENCE = RUNTIME_ROOT / "throughput_probe.json"
DEFAULT_CHECKPOINT = RUNTIME_ROOT / "checkpoint.jsonl"
DEFAULT_STAGING_DIR = RUNTIME_ROOT / "staging"
DEFAULT_SYNC_SUMMARY = RUNTIME_ROOT / "full_sync_summary.json"
WEBBRIDGE_PROBE_TIERS = (
    ProbeTier(1, 8.0, 3),
    ProbeTier(1, 6.0, 3),
    ProbeTier(1, 4.0, 3),
)
DEFAULT_WEBBRIDGE_SETTLE_MS = 2_500
DEFAULT_PLAYWRIGHT_SETTLE_MS = 10_000
FULL_RUN_STOP_FAILURE_CLASSES = frozenset(
    {
        "http_403",
        "http_429",
        "http_status",
        "timeout",
        "content_quality",
        "pdf_quality",
        "browser",
        "browser_provider",
    }
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Probe and run bounded full-corpus browser-printed PDF "
            "synchronization into Zotero."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser(
        "probe",
        help="Run a bounded provider-specific throughput ladder.",
    )
    probe.add_argument("--article-store", type=Path, default=DEFAULT_ARTICLE_STORE)
    probe.add_argument("--evidence", type=Path, default=DEFAULT_PROBE_EVIDENCE)
    probe.add_argument("--runtime-dir", type=Path, default=RUNTIME_ROOT / "probe")
    probe.add_argument(
        "--provider",
        choices=("webbridge", "playwright"),
        default="webbridge",
    )
    probe.add_argument("--webbridge-url", default=DEFAULT_WEBBRIDGE_URL)
    probe.add_argument("--webbridge-session", default=DEFAULT_WEBBRIDGE_SESSION)
    probe.add_argument("--settle-ms", type=int)

    sync = subparsers.add_parser(
        "sync",
        help="Run or dry-run the resumable full Zotero PDF synchronization.",
    )
    sync.add_argument("--article-store", type=Path, default=DEFAULT_ARTICLE_STORE)
    sync.add_argument("--probe-evidence", type=Path, default=DEFAULT_PROBE_EVIDENCE)
    sync.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    sync.add_argument("--staging-dir", type=Path, default=DEFAULT_STAGING_DIR)
    sync.add_argument("--summary", type=Path, default=DEFAULT_SYNC_SUMMARY)
    sync.add_argument("--collection-name", default=DEFAULT_COLLECTION_NAME)
    sync.add_argument("--provider", choices=("webbridge", "playwright"))
    sync.add_argument("--webbridge-url", default=DEFAULT_WEBBRIDGE_URL)
    sync.add_argument("--webbridge-session", default=DEFAULT_WEBBRIDGE_SESSION)
    sync.add_argument("--workers", type=int)
    sync.add_argument("--interval-seconds", type=float)
    sync.add_argument("--settle-ms", type=int)
    sync.add_argument("--readback-batch-size", type=int, default=8)
    sync.add_argument("--article-id", action="append", default=[])
    sync.add_argument("--limit", type=int)
    sync.add_argument(
        "--write",
        action="store_true",
        help="Perform private Zotero writes. Without this flag the run is read-only.",
    )

    args = parser.parse_args()
    try:
        if args.command == "probe":
            return _run_probe(args)
        return _run_sync(args)
    except (OSError, ValueError, ZoteroSyncError) as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


def _run_probe(args: argparse.Namespace) -> int:
    articles = ArticleStore(args.article_store).list_articles()
    tiers = (
        WEBBRIDGE_PROBE_TIERS
        if args.provider == "webbridge"
        else None
    )
    probe_url_count = (
        sum(tier.article_count for tier in tiers)
        if tiers is not None
        else 24
    )
    selected = select_probe_articles(articles, count=probe_url_count)
    settle_ms = _resolve_settle_ms(args.provider, args.settle_ms)
    session_factory = (
        webbridge_session_factory(
            base_url=args.webbridge_url,
            session_name=args.webbridge_session,
        )
        if args.provider == "webbridge"
        else None
    )
    probe_kwargs: dict[str, Any] = {
        "session_factory": session_factory,
        "settle_ms": settle_ms,
    }
    if tiers is not None:
        probe_kwargs["tiers"] = tiers
    outcome = run_throughput_probe(
        selected,
        args.runtime_dir,
        **probe_kwargs,
    )
    payload = {
        "status": outcome.status,
        "source_access": {
            "provider": args.provider,
            "webbridge_session": (
                args.webbridge_session
                if args.provider == "webbridge"
                else None
            ),
            "settle_ms": settle_ms,
            "maximum_safe_workers": (
                1 if args.provider == "webbridge" else 4
            ),
        },
        "article_store": {
            "path": str(args.article_store),
            "sha256": file_sha256(args.article_store),
            "article_count": len(articles),
        },
        "probe": outcome.to_dict(),
    }
    write_json_atomic(args.evidence, payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if outcome.status == "PASS" else 1


def _run_sync(args: argparse.Namespace) -> int:
    articles = ArticleStore(args.article_store).list_articles()
    articles = _select_articles(
        articles,
        requested_ids=args.article_id,
        limit=args.limit,
    )
    provider, workers, interval = _resolve_tier(
        args.probe_evidence,
        provider=args.provider,
        workers=args.workers,
        interval_seconds=args.interval_seconds,
        write=args.write,
    )
    settle_ms = _resolve_settle_ms(provider, args.settle_ms)
    session_factory = (
        webbridge_session_factory(
            base_url=args.webbridge_url,
            session_name=args.webbridge_session,
        )
        if provider == "webbridge"
        else None
    )
    checkpoint = CheckpointJournal(args.checkpoint)
    transport = LocalZoteroSyncTransport(timeout_seconds=30)
    runner = BulkZoteroPdfSync(
        transport,
        browser_config=BrowserPrintConfig(
            workers=workers,
            navigation_interval_seconds=interval,
            retries=3,
            settle_ms=settle_ms,
            stop_failure_classes=FULL_RUN_STOP_FAILURE_CLASSES,
        ),
        checkpoint=checkpoint,
        staging_dir=args.staging_dir,
        collection_name=args.collection_name,
        readback_batch_size=args.readback_batch_size,
        session_factory=session_factory,
    )
    lock_path = Path(args.checkpoint).with_suffix(".lock")
    with ExclusiveRunLock(lock_path):
        summary = runner.run(articles, write=args.write)
        payload = {
            "status": summary.status,
            "write": args.write,
            "article_store": {
                "path": str(args.article_store),
                "sha256": file_sha256(args.article_store),
                "article_count": len(articles),
            },
            "selected_tier": {
                "provider": provider,
                "workers": workers,
                "navigation_interval_seconds": interval,
                "settle_ms": settle_ms,
            },
            "summary": summary.to_dict(),
        }
        write_json_atomic(args.summary, payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if summary.status in {"PASS", "DRY_RUN"} else 1


def _resolve_tier(
    evidence_path: Path,
    *,
    provider: str | None,
    workers: int | None,
    interval_seconds: float | None,
    write: bool,
) -> tuple[str, int, float]:
    if (workers is None) != (interval_seconds is None):
        raise ValueError("--workers and --interval-seconds must be set together")
    payload: dict[str, Any] | None = None
    selected: dict[str, Any] | None = None
    evidence_provider: str | None = None
    if evidence_path.exists():
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
        source_access = payload.get("source_access", {})
        if isinstance(source_access, dict):
            raw_provider = source_access.get("provider")
            if isinstance(raw_provider, str):
                evidence_provider = raw_provider
        probe = payload.get("probe", {})
        if isinstance(probe, dict):
            raw_selected = probe.get("selected_tier")
            if isinstance(raw_selected, dict):
                selected = raw_selected

    if write and (
        payload is None
        or payload.get("status") != "PASS"
        or selected is None
    ):
        raise ValueError(
            "A successful throughput probe is required before a write run"
        )

    resolved_provider = provider or evidence_provider or "playwright"
    if (
        write
        and evidence_provider is not None
        and resolved_provider != evidence_provider
    ):
        raise ValueError(
            "Write provider must match the successful throughput probe"
        )

    if workers is not None and interval_seconds is not None:
        resolved_workers = workers
        resolved_interval = interval_seconds
        if write and selected is not None and (
            resolved_workers != int(selected["workers"])
            or resolved_interval
            != float(selected["navigation_interval_seconds"])
        ):
            raise ValueError(
                "Write tier must match the successful throughput probe"
            )
    elif (
        selected is not None
        and payload is not None
        and payload.get("status") == "PASS"
    ):
        resolved_workers = int(selected["workers"])
        resolved_interval = float(selected["navigation_interval_seconds"])
    else:
        resolved_workers = 1
        resolved_interval = 8.0

    if resolved_provider == "webbridge" and resolved_workers != 1:
        raise ValueError("WebBridge source access supports exactly one worker")
    config = BrowserPrintConfig(
        workers=resolved_workers,
        navigation_interval_seconds=resolved_interval,
    )
    config.validate()
    return resolved_provider, resolved_workers, resolved_interval


def _resolve_settle_ms(provider: str, requested: int | None) -> int:
    settle_ms = (
        requested
        if requested is not None
        else (
            DEFAULT_WEBBRIDGE_SETTLE_MS
            if provider == "webbridge"
            else DEFAULT_PLAYWRIGHT_SETTLE_MS
        )
    )
    if settle_ms < 0:
        raise ValueError("--settle-ms must be non-negative")
    return settle_ms


def _select_articles(
    articles: list[StoredArticle],
    *,
    requested_ids: list[str],
    limit: int | None,
) -> list[StoredArticle]:
    if requested_ids:
        if len(set(requested_ids)) != len(requested_ids):
            raise ValueError("Duplicate --article-id values are not allowed")
        by_id = {article.id: article for article in articles}
        missing = [article_id for article_id in requested_ids if article_id not in by_id]
        if missing:
            raise ValueError(f"Unknown Article IDs: {len(missing)}")
        articles = [by_id[article_id] for article_id in requested_ids]
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be positive")
        articles = articles[:limit]
    return articles


if __name__ == "__main__":
    raise SystemExit(main())
