from __future__ import annotations

import os
import queue
import resource
import statistics
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ContextManager, Protocol

from app.export.printed_pdf import (
    PrintedPdfInspection,
    PrintedPdfValidationError,
    inspect_printed_article_pdf,
)
from app.storage.article_store import StoredArticle

MAX_BROWSER_WORKERS = 4
MIN_NAVIGATION_INTERVAL_SECONDS = 4.0
ARTICLE_BODY_SELECTORS = (
    "#content > .Post",
    "#content .Post",
    ".Post",
    "article",
    ".post",
    ".entry",
    "#article",
)


class BrowserPrintError(RuntimeError):
    pass


@dataclass(frozen=True)
class BrowserPrintConfig:
    workers: int = 1
    navigation_interval_seconds: float = 8.0
    retries: int = 2
    timeout_ms: int = 45_000
    settle_ms: int = 10_000
    mathjax_timeout_ms: int = 10_000
    article_ready_timeout_ms: int = 20_000
    stop_failure_classes: frozenset[str] = frozenset(
        {"http_403", "http_429"}
    )

    def validate(self) -> None:
        if not 1 <= self.workers <= MAX_BROWSER_WORKERS:
            raise ValueError(
                f"workers must be between 1 and {MAX_BROWSER_WORKERS}"
            )
        if self.navigation_interval_seconds < MIN_NAVIGATION_INTERVAL_SECONDS:
            raise ValueError(
                "navigation interval must be at least "
                f"{MIN_NAVIGATION_INTERVAL_SECONDS:g} seconds"
            )
        if self.retries < 1 or self.retries > 3:
            raise ValueError("retries must be between 1 and 3")
        if self.timeout_ms < 1 or self.settle_ms < 0:
            raise ValueError("browser timeouts must be non-negative")


@dataclass(frozen=True)
class BrowserPrintResult:
    article_id: str
    url: str
    status: str
    output_path: Path
    title: str = ""
    http_status: int | None = None
    duration_seconds: float = 0.0
    navigation_wait_seconds: float = 0.0
    attempts: int = 0
    mathjax_available: bool = False
    inspection: PrintedPdfInspection | None = None
    failure_class: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "url": self.url,
            "status": self.status,
            "title": self.title,
            "http_status": self.http_status,
            "duration_seconds": round(self.duration_seconds, 3),
            "navigation_wait_seconds": round(
                self.navigation_wait_seconds,
                3,
            ),
            "attempts": self.attempts,
            "mathjax_available": self.mathjax_available,
            "inspection": (
                self.inspection.to_dict() if self.inspection else None
            ),
            "failure_class": self.failure_class,
            "error": self.error,
        }


@dataclass(frozen=True)
class SystemResourceSnapshot:
    load_1m: float
    available_memory_bytes: int | None
    process_max_rss_bytes: int

    def to_dict(self) -> dict[str, float | int | None]:
        return {
            "load_1m": round(self.load_1m, 3),
            "available_memory_bytes": self.available_memory_bytes,
            "process_max_rss_bytes": self.process_max_rss_bytes,
        }


class NavigationRateLimiter:
    def __init__(
        self,
        interval_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if interval_seconds < MIN_NAVIGATION_INTERVAL_SECONDS:
            raise ValueError(
                "navigation interval is below the task safety floor"
            )
        self.interval_seconds = interval_seconds
        self._clock = clock
        self._sleeper = sleeper
        self._lock = threading.Lock()
        self._next_start = 0.0

    def acquire(self, stop_event: threading.Event | None = None) -> float:
        with self._lock:
            now = self._clock()
            reserved = max(now, self._next_start)
            self._next_start = reserved + self.interval_seconds
        wait_seconds = max(0.0, reserved - self._clock())
        deadline = self._clock() + wait_seconds
        while True:
            if stop_event is not None and stop_event.is_set():
                raise BrowserPrintError("browser print run stopped")
            remaining = deadline - self._clock()
            if remaining <= 0:
                return wait_seconds
            self._sleeper(min(remaining, 0.25))

    def backoff(self, seconds: float) -> None:
        if seconds <= 0:
            return
        with self._lock:
            self._next_start = max(
                self._next_start,
                self._clock() + seconds,
            )


class BrowserPrintSession(Protocol):
    def render(
        self,
        article: StoredArticle,
        output_path: Path,
        limiter: NavigationRateLimiter,
        stop_event: threading.Event,
    ) -> BrowserPrintResult: ...


SessionFactory = Callable[
    [BrowserPrintConfig],
    ContextManager[BrowserPrintSession],
]


class BrowserPrintPool:
    def __init__(
        self,
        config: BrowserPrintConfig,
        *,
        session_factory: SessionFactory | None = None,
    ) -> None:
        config.validate()
        self.config = config
        self.session_factory = session_factory or _PlaywrightBrowserSession

    def iter_render(
        self,
        articles: Iterable[StoredArticle],
        output_dir: Path | str,
    ) -> Iterator[BrowserPrintResult]:
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        limiter = NavigationRateLimiter(
            self.config.navigation_interval_seconds
        )
        stop_event = threading.Event()
        tasks: queue.Queue[StoredArticle | None] = queue.Queue(
            maxsize=max(1, self.config.workers * 2)
        )
        results: queue.Queue[BrowserPrintResult | BaseException] = queue.Queue()
        threads = [
            threading.Thread(
                target=self._worker,
                name=f"browser-print-{index + 1}",
                args=(tasks, results, directory, limiter, stop_event),
            )
            for index in range(self.config.workers)
        ]
        for thread in threads:
            thread.start()

        iterator = iter(articles)
        submitted = 0
        completed = 0
        exhausted = False
        try:
            for _ in range(tasks.maxsize):
                try:
                    tasks.put(next(iterator))
                    submitted += 1
                except StopIteration:
                    exhausted = True
                    break

            while completed < submitted or not exhausted:
                result = results.get()
                if isinstance(result, BaseException):
                    stop_event.set()
                    raise BrowserPrintError(
                        f"browser worker failed: {type(result).__name__}: {result}"
                    ) from result
                completed += 1
                if (
                    result.failure_class
                    and result.failure_class in self.config.stop_failure_classes
                ):
                    stop_event.set()
                if not exhausted and not stop_event.is_set():
                    try:
                        tasks.put(next(iterator))
                        submitted += 1
                    except StopIteration:
                        exhausted = True
                elif stop_event.is_set():
                    exhausted = True
                yield result
        finally:
            stop_event.set()
            while True:
                try:
                    tasks.get_nowait()
                except queue.Empty:
                    break
            for _ in threads:
                tasks.put(None)
            for thread in threads:
                thread.join(timeout=max(5.0, self.config.timeout_ms / 1_000 + 5))
            if any(thread.is_alive() for thread in threads):
                raise BrowserPrintError("browser workers did not stop cleanly")

    def _worker(
        self,
        tasks: queue.Queue[StoredArticle | None],
        results: queue.Queue[BrowserPrintResult | BaseException],
        output_dir: Path,
        limiter: NavigationRateLimiter,
        stop_event: threading.Event,
    ) -> None:
        try:
            with self.session_factory(self.config) as session:
                while True:
                    article = tasks.get()
                    if article is None:
                        return
                    output_path = output_dir / f"{article.id}.pdf"
                    if stop_event.is_set():
                        results.put(
                            BrowserPrintResult(
                                article_id=article.id,
                                url=article.url,
                                status="cancelled",
                                output_path=output_path,
                                failure_class="cancelled",
                                error="run stopped after a hard failure",
                            )
                        )
                        continue
                    result = session.render(
                        article,
                        output_path,
                        limiter,
                        stop_event,
                    )
                    results.put(result)
                    if (
                        result.failure_class
                        and result.failure_class
                        in self.config.stop_failure_classes
                    ):
                        stop_event.set()
        except BaseException as exc:  # noqa: BLE001 - propagate worker startup failures.
            results.put(exc)


class _RenderAttemptError(RuntimeError):
    def __init__(
        self,
        failure_class: str,
        message: str,
        *,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.failure_class = failure_class
        self.http_status = http_status


class _PlaywrightBrowserSession:
    def __init__(self, config: BrowserPrintConfig) -> None:
        self.config = config
        self._manager: Any = None
        self._browser: Any = None
        self._context: Any = None

    def __enter__(self) -> _PlaywrightBrowserSession:
        from playwright.sync_api import sync_playwright

        self._manager = sync_playwright()
        playwright = self._manager.start()
        self._browser = playwright.chromium.launch(
            headless=True,
            timeout=self.config.timeout_ms,
        )
        self._context = self._browser.new_context(accept_downloads=False)
        self._context.route("**/*", self._route_download_safety)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._manager is not None:
            self._manager.__exit__(exc_type, exc, traceback)

    def render(
        self,
        article: StoredArticle,
        output_path: Path,
        limiter: NavigationRateLimiter,
        stop_event: threading.Event,
    ) -> BrowserPrintResult:
        started_at = time.monotonic()
        total_navigation_wait = 0.0
        last_error = "unknown browser print error"
        last_failure_class = "browser"
        last_http_status: int | None = None

        for attempt in range(1, self.config.retries + 1):
            page = self._context.new_page()
            try:
                if output_path.exists():
                    output_path.unlink()
                total_navigation_wait += limiter.acquire(stop_event)
                response = page.goto(
                    article.url,
                    wait_until="commit",
                    timeout=self.config.timeout_ms,
                )
                http_status = response.status if response else None
                last_http_status = http_status
                if http_status == 403:
                    raise _RenderAttemptError(
                        "http_403",
                        "HTTP status 403",
                        http_status=http_status,
                    )
                if http_status == 429:
                    raise _RenderAttemptError(
                        "http_429",
                        "HTTP status 429",
                        http_status=http_status,
                    )
                if not isinstance(http_status, int) or not 200 <= http_status < 300:
                    raise _RenderAttemptError(
                        "http_status",
                        f"HTTP status {http_status}",
                        http_status=http_status,
                    )
                page.wait_for_selector(
                    ", ".join(ARTICLE_BODY_SELECTORS),
                    state="attached",
                    timeout=self.config.article_ready_timeout_ms,
                )
                page.wait_for_timeout(self.config.settle_ms)
                mathjax_available = self._wait_for_mathjax(page)
                title = page.title()
                if not title.strip():
                    raise _RenderAttemptError(
                        "content_quality",
                        "source page title is empty",
                    )
                page.emulate_media(media="print")
                page.pdf(
                    path=str(output_path),
                    format="A4",
                    print_background=True,
                )
                inspection = inspect_printed_article_pdf(
                    article,
                    output_path,
                    mathjax_rendered=mathjax_available,
                )
                return BrowserPrintResult(
                    article_id=article.id,
                    url=article.url,
                    status="success",
                    output_path=output_path,
                    title=title,
                    http_status=http_status,
                    duration_seconds=time.monotonic() - started_at,
                    navigation_wait_seconds=total_navigation_wait,
                    attempts=attempt,
                    mathjax_available=mathjax_available,
                    inspection=inspection,
                )
            except _RenderAttemptError as exc:
                last_error = str(exc)
                last_failure_class = exc.failure_class
                last_http_status = exc.http_status or last_http_status
            except PrintedPdfValidationError as exc:
                last_error = str(exc)
                last_failure_class = "pdf_quality"
            except Exception as exc:  # noqa: BLE001 - preserve Playwright failure detail.
                last_error = f"{type(exc).__name__}: {exc}"
                last_failure_class = _classify_browser_exception(exc)
            finally:
                page.close()

            if output_path.exists():
                output_path.unlink()
            if last_failure_class in {"http_403", "http_429"}:
                limiter.backoff(60.0)
                break
            if attempt < self.config.retries:
                limiter.backoff(
                    max(8.0, self.config.navigation_interval_seconds * 2)
                )

        return BrowserPrintResult(
            article_id=article.id,
            url=article.url,
            status="failed",
            output_path=output_path,
            http_status=last_http_status,
            duration_seconds=time.monotonic() - started_at,
            navigation_wait_seconds=total_navigation_wait,
            attempts=min(self.config.retries, max(1, attempt)),
            failure_class=last_failure_class,
            error=last_error,
        )

    def _wait_for_mathjax(self, page: Any) -> bool:
        try:
            available = bool(page.evaluate(_MATHJAX_AVAILABLE_CHECK))
        except Exception:
            return False
        if not available:
            return False
        try:
            page.wait_for_function(
                _MATHJAX_READY_CHECK,
                timeout=self.config.mathjax_timeout_ms,
            )
        except Exception:
            return available
        return True

    @staticmethod
    def _route_download_safety(route: Any) -> None:
        url = route.request.url.lower()
        if url.endswith((".pdf", ".zip", ".rar", ".7z")):
            route.abort()
            return
        route.continue_()


def system_resource_snapshot() -> SystemResourceSnapshot:
    available_memory: int | None = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                available_memory = int(line.split()[1]) * 1_024
                break
    except (OSError, ValueError, IndexError):
        available_memory = None
    max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    max_rss_bytes = max_rss if os.uname().sysname == "Darwin" else max_rss * 1_024
    return SystemResourceSnapshot(
        load_1m=os.getloadavg()[0],
        available_memory_bytes=available_memory,
        process_max_rss_bytes=max_rss_bytes,
    )


def duration_summary(results: list[BrowserPrintResult]) -> dict[str, float | None]:
    durations = [
        result.duration_seconds
        for result in results
        if result.status == "success"
    ]
    if not durations:
        return {"median_seconds": None, "max_seconds": None}
    return {
        "median_seconds": round(statistics.median(durations), 3),
        "max_seconds": round(max(durations), 3),
    }


def _classify_browser_exception(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timeout" in message:
        return "timeout"
    if "browser" in message or "target" in message:
        return "browser"
    return "content_quality"


_MATHJAX_AVAILABLE_CHECK = """
() => Boolean(
  window.MathJax ||
  document.querySelector('script[src*="MathJax"], script[src*="mathjax"], .MathJax, mjx-container') ||
  document.querySelector('.katex, script[src*="KaTeX"], script[src*="katex"]')
)
"""


_MATHJAX_READY_CHECK = """
() => {
  const mathJax = window.MathJax;
  if (!mathJax) {
    return true;
  }
  if (mathJax.startup && mathJax.startup.promise) {
    return mathJax.startup.promise.then(() => true).catch(() => true);
  }
  if (mathJax.Hub && mathJax.Hub.Queue) {
    return new Promise((resolve) => mathJax.Hub.Queue(() => resolve(true)));
  }
  if (typeof mathJax.typesetPromise === 'function') {
    return mathJax.typesetPromise().then(() => true).catch(() => true);
  }
  return true;
}
"""
