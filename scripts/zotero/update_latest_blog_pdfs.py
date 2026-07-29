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
    WebBridgeClient,
    webbridge_session_factory,
)
from app.storage.article_store import ArticleStore  # noqa: E402
from app.zotero.bulk_pdf import (  # noqa: E402
    BulkZoteroPdfSync,
    CheckpointJournal,
    ExclusiveRunLock,
    write_json_atomic,
)
from app.zotero.incremental_sync import (  # noqa: E402
    IncrementalBlogZoteroSync,
    IncrementalCheckpointJournal,
    IncrementalSyncError,
    WebBridgeArticleHtmlFetcher,
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
    / "incremental_zotero_sync"
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
DEFAULT_PROBE_EVIDENCE = (
    REPO_ROOT
    / ".local_data"
    / "scientific_spaces"
    / "zotero_pdf_sync"
    / "throughput_probe.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Incrementally import latest Scientific Spaces RSS Articles and "
            "browser-printed PDFs into Zotero."
        )
    )
    parser.add_argument(
        "--article-store",
        type=Path,
        default=DEFAULT_ARTICLE_STORE,
    )
    parser.add_argument(
        "--feed-url",
        default="https://spaces.ac.cn/feed",
    )
    parser.add_argument("--max-feed-items", type=int, default=50)
    parser.add_argument(
        "--probe-evidence",
        type=Path,
        default=DEFAULT_PROBE_EVIDENCE,
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=RUNTIME_ROOT / "incremental_checkpoint.jsonl",
    )
    parser.add_argument(
        "--pdf-checkpoint",
        type=Path,
        default=RUNTIME_ROOT / "pdf_checkpoint.jsonl",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=RUNTIME_ROOT / "staging",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=RUNTIME_ROOT / "summary.json",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        default=RUNTIME_ROOT / "backups" / "articles-before-latest-update.json",
    )
    parser.add_argument(
        "--collection-name",
        default=DEFAULT_COLLECTION_NAME,
    )
    parser.add_argument(
        "--webbridge-url",
        default=DEFAULT_WEBBRIDGE_URL,
    )
    parser.add_argument(
        "--webbridge-session",
        default=DEFAULT_WEBBRIDGE_SESSION,
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write new Articles and Zotero PDFs. Default is read-only.",
    )
    args = parser.parse_args()

    try:
        provider, workers, interval, settle_ms = _load_probe_tier(
            args.probe_evidence
        )
        if provider != "webbridge" or workers != 1:
            raise IncrementalSyncError(
                "Incremental writes require the validated one-tab WebBridge tier"
            )
        browser_config = BrowserPrintConfig(
            workers=workers,
            navigation_interval_seconds=interval,
            retries=3,
            settle_ms=settle_ms,
            stop_failure_classes=frozenset(
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
            ),
        )
        transport = LocalZoteroSyncTransport(timeout_seconds=30)

        def source_factory() -> WebBridgeArticleHtmlFetcher:
            return WebBridgeArticleHtmlFetcher(
                browser_config,
                client=WebBridgeClient(
                    base_url=args.webbridge_url,
                    session_name=args.webbridge_session,
                ),
                group_title="M1.4 增量博客同步",
            )

        def bulk_factory() -> BulkZoteroPdfSync:
            return BulkZoteroPdfSync(
                transport,
                browser_config=browser_config,
                checkpoint=CheckpointJournal(args.pdf_checkpoint),
                staging_dir=args.staging_dir,
                collection_name=args.collection_name,
                readback_batch_size=8,
                session_factory=webbridge_session_factory(
                    base_url=args.webbridge_url,
                    session_name=args.webbridge_session,
                    group_title="M1.4 增量博客同步",
                ),
            )

        runner = IncrementalBlogZoteroSync(
            store=ArticleStore(args.article_store),
            bulk_sync_factory=bulk_factory,
            checkpoint=IncrementalCheckpointJournal(args.checkpoint),
            source_fetcher_factory=source_factory,
            feed_url=args.feed_url,
            max_feed_items=args.max_feed_items,
            backup_path=args.backup,
        )
        lock_path = args.checkpoint.with_suffix(".lock")
        with ExclusiveRunLock(lock_path):
            summary = runner.run(write=args.write)
            payload = {
                "status": summary.status,
                "selected_tier": {
                    "provider": provider,
                    "workers": workers,
                    "navigation_interval_seconds": interval,
                    "settle_ms": settle_ms,
                },
                "summary": summary.to_dict(),
            }
            write_json_atomic(args.summary, payload)
    except (
        IncrementalSyncError,
        ZoteroSyncError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
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

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary.status in {"PASS", "DRY_RUN"} else 1


def _load_probe_tier(
    path: Path,
) -> tuple[str, int, float, int]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    source = payload.get("source_access")
    probe = payload.get("probe")
    if (
        payload.get("status") != "PASS"
        or not isinstance(source, dict)
        or not isinstance(probe, dict)
        or not isinstance(probe.get("selected_tier"), dict)
    ):
        raise IncrementalSyncError(
            "A successful P3-009 throughput probe is required"
        )
    selected = probe["selected_tier"]
    provider = str(source.get("provider") or "")
    workers = int(selected["workers"])
    interval = float(selected["navigation_interval_seconds"])
    settle_ms = int(source.get("settle_ms") or 2_500)
    BrowserPrintConfig(
        workers=workers,
        navigation_interval_seconds=interval,
        settle_ms=settle_ms,
    ).validate()
    return provider, workers, interval, settle_ms


if __name__ == "__main__":
    raise SystemExit(main())
