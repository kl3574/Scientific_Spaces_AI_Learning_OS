from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.crawler.browser import BrowserFetchResult
from app.crawler.rss import (
    DEFAULT_FEED_URL,
    default_fetch_xml,
    discover_rss_article_urls,
)
from app.export.browser_print import (
    BrowserPrintConfig,
    NavigationRateLimiter,
)
from app.export.webbridge_print import (
    DEFAULT_WEBBRIDGE_GROUP,
    WebBridgeClient,
    WebBridgeCommandError,
)
from app.parser.article import ParsedArticle, parse_article_html
from app.storage.article_store import ArticleStore, StoredArticle
from app.validation.quality import ArticleQualityValidator
from app.zotero.bulk_pdf import BulkSyncSummary, BulkZoteroPdfSync
from app.zotero.sync import canonicalize_article_url

MAX_FEED_ITEMS = 100
MIN_ARTICLE_BODY_CHARS = 100


class IncrementalSyncError(RuntimeError):
    pass


class ArticleHtmlFetcher(Protocol):
    navigation_attempt_count: int

    def fetch(self, url: str) -> BrowserFetchResult: ...


SourceFetcherFactory = Callable[
    [],
    AbstractContextManager[ArticleHtmlFetcher],
]
BulkSyncFactory = Callable[[], BulkZoteroPdfSync]


@dataclass(frozen=True)
class IncrementalSyncSummary:
    status: str
    write: bool
    feed_url: str
    feed_article_count: int
    store_before_count: int
    store_after_count: int
    missing_before_count: int
    acquired_count: int
    stored_count: int
    source_navigation_count: int
    existing_records_unchanged: bool
    backup_created: bool
    store_sha256_before: str | None
    store_sha256_after: str | None
    zotero: dict[str, Any] | None
    failures: tuple[dict[str, str], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "write": self.write,
            "feed_url": self.feed_url,
            "feed_article_count": self.feed_article_count,
            "store_before_count": self.store_before_count,
            "store_after_count": self.store_after_count,
            "missing_before_count": self.missing_before_count,
            "acquired_count": self.acquired_count,
            "stored_count": self.stored_count,
            "source_navigation_count": self.source_navigation_count,
            "existing_records_unchanged": self.existing_records_unchanged,
            "backup_created": self.backup_created,
            "store_sha256_before": self.store_sha256_before,
            "store_sha256_after": self.store_sha256_after,
            "zotero": self.zotero,
            "failures": list(self.failures),
        }


class IncrementalCheckpointJournal:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, **evidence: Any) -> None:
        payload = {
            "record_type": "incremental_source",
            "recorded_at_unix": round(time.time(), 3),
            "event": event,
            **evidence,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        )
        try:
            with self.path.open("a", encoding="utf-8") as file:
                file.write(encoded + "\n")
                file.flush()
                os.fsync(file.fileno())
        except OSError as exc:
            raise IncrementalSyncError(
                "Unable to persist the incremental checkpoint"
            ) from exc


class IncrementalBlogZoteroSync:
    def __init__(
        self,
        *,
        store: ArticleStore,
        bulk_sync_factory: BulkSyncFactory,
        checkpoint: IncrementalCheckpointJournal,
        source_fetcher_factory: SourceFetcherFactory | None = None,
        feed_url: str = DEFAULT_FEED_URL,
        rss_fetch_xml: Callable[[str], str] = default_fetch_xml,
        max_feed_items: int = 50,
        backup_path: Path | str | None = None,
    ) -> None:
        if max_feed_items < 1 or max_feed_items > MAX_FEED_ITEMS:
            raise ValueError(
                f"max_feed_items must be between 1 and {MAX_FEED_ITEMS}"
            )
        self.store = store
        self.bulk_sync_factory = bulk_sync_factory
        self.checkpoint = checkpoint
        self.source_fetcher_factory = source_fetcher_factory
        self.feed_url = feed_url
        self.rss_fetch_xml = rss_fetch_xml
        self.max_feed_items = max_feed_items
        self.backup_path = Path(backup_path) if backup_path else None

    def run(self, *, write: bool) -> IncrementalSyncSummary:
        before_articles = self.store.list_articles()
        before_by_url = {article.url: article for article in before_articles}
        if len(before_by_url) != len(before_articles):
            raise IncrementalSyncError(
                "Article Store contains duplicate URLs"
            )
        before_digests = _record_digests(before_articles)
        store_sha_before = _optional_file_sha256(self.store.path)
        feed_urls = discover_rss_article_urls(
            self.feed_url,
            fetch_xml=self.rss_fetch_xml,
            max_items=self.max_feed_items,
        )
        missing_urls = [url for url in feed_urls if url not in before_by_url]
        self.checkpoint.record(
            "feed_discovered",
            feed_url=self.feed_url,
            feed_article_count=len(feed_urls),
            missing_article_count=len(missing_urls),
            write=write,
        )

        parsed_articles: list[ParsedArticle] = []
        failures: list[dict[str, str]] = []
        source_navigation_count = 0
        if write and missing_urls:
            if self.source_fetcher_factory is None:
                raise IncrementalSyncError(
                    "A source fetcher is required for a write run with missing Articles"
                )
            with self.source_fetcher_factory() as fetcher:
                for url in missing_urls:
                    try:
                        fetched = fetcher.fetch(url)
                        parsed = parse_article_html(fetched.html, url=url)
                        _validate_parsed_article(parsed)
                    except Exception as exc:  # noqa: BLE001 - classify source failures.
                        failures.append(
                            {
                                "url": url,
                                "stage": "source_acquisition",
                                "reason": f"{type(exc).__name__}: {exc}",
                            }
                        )
                        self.checkpoint.record(
                            "article_failed",
                            url=url,
                            stage="source_acquisition",
                            reason=f"{type(exc).__name__}: {exc}",
                        )
                        continue
                    parsed_articles.append(parsed)
                    self.checkpoint.record(
                        "article_acquired",
                        url=url,
                        title=parsed.title,
                        content_length=len(parsed.content),
                        date=parsed.date,
                        category=parsed.category,
                        image_count=len(parsed.images),
                        reference_count=len(parsed.references),
                        mathjax_available=fetched.mathjax_available,
                    )
                source_navigation_count = fetcher.navigation_attempt_count

        if failures:
            return self._blocked_summary(
                write=write,
                feed_urls=feed_urls,
                before_articles=before_articles,
                missing_urls=missing_urls,
                acquired_count=len(parsed_articles),
                source_navigation_count=source_navigation_count,
                before_digests=before_digests,
                store_sha_before=store_sha_before,
                failures=failures,
            )

        stored_count = 0
        backup_created = False
        if write and parsed_articles:
            backup_created = _ensure_backup(
                self.store.path,
                self.backup_path,
            )
            new_articles = append_articles_atomically(
                self.store,
                parsed_articles,
            )
            stored_count = len(new_articles)
            self.checkpoint.record(
                "article_store_updated",
                previous_count=len(before_articles),
                current_count=self.store.count(),
                stored_count=stored_count,
            )

        after_articles = self.store.list_articles()
        existing_unchanged = _existing_records_unchanged(
            before_digests,
            after_articles,
        )
        if not existing_unchanged:
            raise IncrementalSyncError(
                "Existing Article records changed during incremental update"
            )
        if write and len(after_articles) != len(before_articles) + len(
            parsed_articles
        ):
            raise IncrementalSyncError(
                "Article Store count does not match the validated delta"
            )

        zotero_summary = self.bulk_sync_factory().run(
            after_articles,
            write=write,
        )
        status = _overall_status(write=write, zotero=zotero_summary)
        summary = IncrementalSyncSummary(
            status=status,
            write=write,
            feed_url=self.feed_url,
            feed_article_count=len(feed_urls),
            store_before_count=len(before_articles),
            store_after_count=len(after_articles),
            missing_before_count=len(missing_urls),
            acquired_count=len(parsed_articles),
            stored_count=stored_count,
            source_navigation_count=source_navigation_count,
            existing_records_unchanged=existing_unchanged,
            backup_created=backup_created,
            store_sha256_before=store_sha_before,
            store_sha256_after=_optional_file_sha256(self.store.path),
            zotero=zotero_summary.to_dict(),
        )
        self.checkpoint.record(
            "run_completed" if status in {"PASS", "DRY_RUN"} else "run_blocked",
            summary=summary.to_dict(),
        )
        return summary

    def _blocked_summary(
        self,
        *,
        write: bool,
        feed_urls: list[str],
        before_articles: list[StoredArticle],
        missing_urls: list[str],
        acquired_count: int,
        source_navigation_count: int,
        before_digests: dict[str, str],
        store_sha_before: str | None,
        failures: list[dict[str, str]],
    ) -> IncrementalSyncSummary:
        after_articles = self.store.list_articles()
        summary = IncrementalSyncSummary(
            status="BLOCKED",
            write=write,
            feed_url=self.feed_url,
            feed_article_count=len(feed_urls),
            store_before_count=len(before_articles),
            store_after_count=len(after_articles),
            missing_before_count=len(missing_urls),
            acquired_count=acquired_count,
            stored_count=0,
            source_navigation_count=source_navigation_count,
            existing_records_unchanged=_existing_records_unchanged(
                before_digests,
                after_articles,
            ),
            backup_created=False,
            store_sha256_before=store_sha_before,
            store_sha256_after=_optional_file_sha256(self.store.path),
            zotero=None,
            failures=tuple(failures),
        )
        self.checkpoint.record("run_blocked", summary=summary.to_dict())
        return summary


class WebBridgeArticleHtmlFetcher:
    def __init__(
        self,
        config: BrowserPrintConfig,
        *,
        client: WebBridgeClient | None = None,
        group_title: str = DEFAULT_WEBBRIDGE_GROUP,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        config.validate()
        if config.workers != 1:
            raise ValueError(
                "WebBridge incremental acquisition supports exactly one tab"
            )
        self.config = config
        self.client = client or WebBridgeClient()
        self.group_title = group_title
        self.sleeper = sleeper
        self.navigation_attempt_count = 0
        self._has_tab = False
        self._limiter = NavigationRateLimiter(
            config.navigation_interval_seconds
        )

    def __enter__(self) -> WebBridgeArticleHtmlFetcher:
        tabs = self.client.command("list_tabs", {}).get("tabs")
        if not isinstance(tabs, list):
            raise IncrementalSyncError("WebBridge tab list is invalid")
        if tabs:
            active = next(
                (
                    tab
                    for tab in tabs
                    if isinstance(tab, dict) and tab.get("active")
                ),
                tabs[-1],
            )
            if not isinstance(active, dict) or not active.get("url"):
                raise IncrementalSyncError(
                    "WebBridge tab identity is invalid"
                )
            self.client.command(
                "find_tab",
                {"url": str(active["url"])},
            )
            self._has_tab = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> None:
        # The task browser tab remains visible until the user asks to close it.
        return None

    def fetch(self, url: str) -> BrowserFetchResult:
        last_error = "unknown WebBridge source acquisition error"
        last_failure_class = "browser"
        for attempt in range(1, self.config.retries + 1):
            try:
                self._limiter.acquire()
                self.navigation_attempt_count += 1
                self._navigate(url)
                state = self._evaluate_article_snapshot()
                return _browser_result_from_state(url, state)
            except _SourceAttemptError as exc:
                last_error = str(exc)
                last_failure_class = exc.failure_class
            except WebBridgeCommandError as exc:
                last_error = str(exc)
                last_failure_class = "browser"
                self._reset_tab()

            if last_failure_class in {"http_403", "http_429"}:
                self._limiter.backoff(60)
                break
            if attempt < self.config.retries:
                self._limiter.backoff(
                    max(
                        30.0,
                        self.config.navigation_interval_seconds * 2,
                    )
                )

        raise IncrementalSyncError(
            f"Failed to acquire {url}: {last_failure_class}: {last_error}"
        )

    def _navigate(self, url: str) -> None:
        if not self._has_tab:
            result = self.client.command(
                "navigate",
                {
                    "url": url,
                    "newTab": True,
                    "group_title": self.group_title,
                },
            )
            if result.get("success") is not True:
                raise _SourceAttemptError(
                    "browser",
                    "WebBridge navigation did not succeed",
                )
            self._has_tab = True
            return
        self.client.command(
            "cdp",
            {
                "method": "Page.navigate",
                "params": {"url": url},
            },
        )

    def _evaluate_article_snapshot(self) -> dict[str, Any]:
        deadline = time.monotonic() + (
            self.config.article_ready_timeout_ms
            + self.config.mathjax_timeout_ms
            + self.config.settle_ms
            + 10_000
        ) / 1_000
        while True:
            try:
                data = self.client.command(
                    "cdp",
                    {
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": _article_snapshot_script(
                                settle_ms=self.config.settle_ms,
                                article_ready_timeout_ms=(
                                    self.config.article_ready_timeout_ms
                                ),
                                mathjax_timeout_ms=(
                                    self.config.mathjax_timeout_ms
                                ),
                            ),
                            "awaitPromise": True,
                            "returnByValue": True,
                        },
                    },
                )
            except WebBridgeCommandError as exc:
                if (
                    "navigated or closed" in str(exc).lower()
                    and time.monotonic() < deadline
                ):
                    self.sleeper(0.5)
                    continue
                raise
            result = data.get("result")
            value = result.get("value") if isinstance(result, dict) else None
            if (
                not isinstance(result, dict)
                or result.get("type") != "object"
                or not isinstance(value, dict)
            ):
                raise WebBridgeCommandError(
                    "WebBridge Article snapshot is invalid"
                )
            return value

    def _reset_tab(self) -> None:
        if not self._has_tab:
            return
        try:
            self.client.command(
                "cdp",
                {"method": "Page.stop", "params": {}},
            )
            self.client.command(
                "cdp",
                {
                    "method": "Page.navigate",
                    "params": {"url": "about:blank"},
                },
            )
        except WebBridgeCommandError:
            return


class _SourceAttemptError(RuntimeError):
    def __init__(self, failure_class: str, message: str) -> None:
        super().__init__(message)
        self.failure_class = failure_class


def append_articles_atomically(
    store: ArticleStore,
    parsed_articles: list[ParsedArticle],
) -> list[StoredArticle]:
    if not parsed_articles:
        return []
    existing = store.list_articles()
    existing_urls = {article.url for article in existing}
    incoming_urls = [article.url for article in parsed_articles]
    if len(set(incoming_urls)) != len(incoming_urls):
        raise IncrementalSyncError(
            "Validated source delta contains duplicate URLs"
        )
    if existing_urls.intersection(incoming_urls):
        raise IncrementalSyncError(
            "Validated source delta overlaps the existing Article Store"
        )
    before_digests = _record_digests(existing)
    temporary = store.path.with_suffix(store.path.suffix + ".m1-4.tmp")
    temporary.unlink(missing_ok=True)
    try:
        if store.path.exists():
            shutil.copy2(store.path, temporary)
        else:
            temporary.write_text("[]", encoding="utf-8")
        temporary_store = ArticleStore(temporary)
        for parsed in parsed_articles:
            temporary_store.upsert(parsed)
        candidate = temporary_store.list_articles()
        if len(candidate) != len(existing) + len(parsed_articles):
            raise IncrementalSyncError(
                "Candidate Article Store count is inconsistent"
            )
        if not _existing_records_unchanged(before_digests, candidate):
            raise IncrementalSyncError(
                "Candidate Article Store changed an existing record"
            )
        with temporary.open("rb") as file:
            os.fsync(file.fileno())
        os.replace(temporary, store.path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    by_url = {article.url: article for article in store.list_articles()}
    return [by_url[url] for url in incoming_urls]


def _ensure_backup(
    source: Path,
    backup: Path | None,
) -> bool:
    if backup is None:
        return False
    if not source.exists():
        raise IncrementalSyncError(
            "Cannot back up a missing Article Store"
        )
    backup.parent.mkdir(parents=True, exist_ok=True)
    temporary = backup.with_suffix(backup.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        shutil.copy2(source, temporary)
        with temporary.open("rb") as file:
            os.fsync(file.fileno())
        os.replace(temporary, backup)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return True


def _validate_parsed_article(article: ParsedArticle) -> None:
    canonical = canonicalize_article_url(article.url)
    if canonical != article.url:
        raise IncrementalSyncError(
            "Parsed Article URL is not canonical"
        )
    report = ArticleQualityValidator(sample_size=1).validate([article])
    if report.issues or not report.formulas_valid:
        reason = "; ".join(report.issues) or "formula validation failed"
        raise IncrementalSyncError(
            f"Parsed Article quality validation failed: {reason}"
        )


def _browser_result_from_state(
    requested_url: str,
    state: dict[str, Any],
) -> BrowserFetchResult:
    status = state.get("responseStatus")
    if status == 403:
        raise _SourceAttemptError("http_403", "HTTP status 403")
    if status == 429:
        raise _SourceAttemptError("http_429", "HTTP status 429")
    if not isinstance(status, int) or not 200 <= status < 300:
        raise _SourceAttemptError(
            "http_status",
            f"HTTP status {status}",
        )
    actual_url = str(state.get("url") or "")
    if canonicalize_article_url(actual_url) != canonicalize_article_url(
        requested_url
    ):
        raise _SourceAttemptError(
            "content_quality",
            "WebBridge landed on the wrong Article URL",
        )
    title = str(state.get("title") or "").strip()
    html = str(state.get("html") or "")
    body_length = state.get("maxBodyTextLength")
    if not title:
        raise _SourceAttemptError(
            "content_quality",
            "source page title is empty",
        )
    if (
        not isinstance(body_length, int)
        or body_length < MIN_ARTICLE_BODY_CHARS
        or not html.strip()
    ):
        raise _SourceAttemptError(
            "content_quality",
            "source Article body is unavailable",
        )
    return BrowserFetchResult(
        url=requested_url,
        html=html,
        title=title,
        status=status,
        mathjax_available=bool(state.get("mathjaxAvailable")),
    )


def _record_digests(
    articles: list[StoredArticle],
) -> dict[str, str]:
    return {
        article.id: hashlib.sha256(
            json.dumps(
                article.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        for article in articles
    }


def _existing_records_unchanged(
    before_digests: dict[str, str],
    articles: list[StoredArticle],
) -> bool:
    after_digests = _record_digests(articles)
    return all(
        after_digests.get(article_id) == digest
        for article_id, digest in before_digests.items()
    )


def _optional_file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _overall_status(
    *,
    write: bool,
    zotero: BulkSyncSummary,
) -> str:
    if not write and zotero.status == "DRY_RUN":
        return "DRY_RUN"
    if write and zotero.status == "PASS":
        return "PASS"
    return "BLOCKED"


def _article_snapshot_script(
    *,
    settle_ms: int,
    article_ready_timeout_ms: int,
    mathjax_timeout_ms: int,
) -> str:
    return f"""
(async () => {{
  const selectors = [
    "#content > .Post",
    "#content .Post",
    ".Post",
    "article",
    ".post",
    ".entry",
    "#article"
  ];
  const sleep = (milliseconds) =>
    new Promise((resolve) => setTimeout(resolve, milliseconds));
  const deadline = Date.now() + {article_ready_timeout_ms};
  let maxBodyTextLength = 0;
  while (Date.now() < deadline) {{
    const nodes = selectors.flatMap(
      (selector) => Array.from(document.querySelectorAll(selector))
    );
    const lengths = nodes.map(
      (node) => String(node.innerText || "").trim().length
    );
    maxBodyTextLength = lengths.length ? Math.max(...lengths) : 0;
    if (maxBodyTextLength >= {MIN_ARTICLE_BODY_CHARS}) {{
      break;
    }}
    await sleep(250);
  }}
  await sleep({settle_ms});
  const mathJax = window.MathJax;
  const mathjaxAvailable = Boolean(
    mathJax ||
    document.querySelector(
      'script[src*="MathJax"], script[src*="mathjax"], .MathJax, mjx-container, .katex'
    )
  );
  if (mathJax && mathJax.startup && mathJax.startup.promise) {{
    await Promise.race([
      mathJax.startup.promise.catch(() => true),
      sleep({mathjax_timeout_ms})
    ]);
  }} else if (mathJax && typeof mathJax.typesetPromise === "function") {{
    await Promise.race([
      mathJax.typesetPromise().catch(() => true),
      sleep({mathjax_timeout_ms})
    ]);
  }} else if (mathJax && mathJax.Hub && mathJax.Hub.Queue) {{
    await Promise.race([
      new Promise((resolve) => mathJax.Hub.Queue(() => resolve(true))),
      sleep({mathjax_timeout_ms})
    ]);
  }}
  const navigation = performance.getEntriesByType("navigation")[0];
  return {{
    url: location.href,
    title: document.title,
    responseStatus:
      navigation && "responseStatus" in navigation
        ? navigation.responseStatus
        : null,
    maxBodyTextLength,
    mathjaxAvailable,
    html: document.documentElement.outerHTML
  }};
}})()
""".strip()
