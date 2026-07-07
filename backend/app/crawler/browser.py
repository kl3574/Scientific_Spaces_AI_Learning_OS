from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BrowserFetchResult:
    url: str
    html: str
    title: str
    status: int | None
    mathjax_available: bool


class BrowserAccessError(RuntimeError):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"Failed to fetch {url}: {reason}")
        self.url = url
        self.reason = reason


class BrowserArticleFetcher:
    def __init__(
        self,
        *,
        loader: Callable[[str], BrowserFetchResult] | None = None,
        retries: int = 2,
        backoff_seconds: float = 1.0,
        timeout_ms: int = 30_000,
        settle_ms: int = 3_000,
        mathjax_timeout_ms: int = 5_000,
    ) -> None:
        self.loader = loader
        self.retries = max(retries, 1)
        self.backoff_seconds = backoff_seconds
        self.timeout_ms = timeout_ms
        self.settle_ms = settle_ms
        self.mathjax_timeout_ms = mathjax_timeout_ms
        self.failures: list[dict[str, str]] = []

    def fetch(self, url: str) -> BrowserFetchResult:
        if self.loader is None:
            results = self.fetch_many([url])
            if results:
                return results[0]
            reason = self.failures[-1]["reason"] if self.failures else "no result"
            raise BrowserAccessError(url, reason)

        last_reason = "unknown error"
        for attempt in range(self.retries):
            try:
                result = self.loader(url)
                self._ensure_success(result)
                return result
            except Exception as exc:  # noqa: BLE001 - preserve external failure detail.
                last_reason = f"{type(exc).__name__}: {exc}"
                if attempt < self.retries - 1 and self.backoff_seconds:
                    time.sleep(self.backoff_seconds * (attempt + 1))

        self._record_failure(url, last_reason)
        raise BrowserAccessError(url, last_reason)

    def fetch_many(self, urls: list[str]) -> list[BrowserFetchResult]:
        if self.loader is not None:
            results: list[BrowserFetchResult] = []
            for url in urls:
                try:
                    results.append(self.fetch(url))
                except BrowserAccessError:
                    continue
            return results

        return self._fetch_many_with_playwright(urls)

    def _fetch_many_with_playwright(self, urls: list[str]) -> list[BrowserFetchResult]:
        from playwright.sync_api import sync_playwright

        results: list[BrowserFetchResult] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, timeout=self.timeout_ms)
            context = browser.new_context(accept_downloads=False)
            context.route("**/*", self._route_download_safety)
            try:
                for url in urls:
                    try:
                        results.append(self._fetch_with_context(context, url))
                    except BrowserAccessError:
                        continue
            finally:
                context.close()
                browser.close()
        return results

    def _fetch_with_context(self, context: Any, url: str) -> BrowserFetchResult:
        last_reason = "unknown error"
        for attempt in range(self.retries):
            page = context.new_page()
            try:
                response = page.goto(url, wait_until="commit", timeout=self.timeout_ms)
                page.wait_for_timeout(self.settle_ms)
                self._wait_for_mathjax(page)
                result = BrowserFetchResult(
                    url=url,
                    html=page.content(),
                    title=page.title(),
                    status=response.status if response else None,
                    mathjax_available=bool(page.evaluate(_MATHJAX_CHECK)),
                )
                self._ensure_success(result)
                return result
            except Exception as exc:  # noqa: BLE001 - preserve Playwright failure detail.
                last_reason = f"{type(exc).__name__}: {exc}"
                if attempt < self.retries - 1 and self.backoff_seconds:
                    time.sleep(self.backoff_seconds * (attempt + 1))
            finally:
                page.close()

        self._record_failure(url, last_reason)
        raise BrowserAccessError(url, last_reason)

    def _wait_for_mathjax(self, page: Any) -> None:
        try:
            page.wait_for_function(_MATHJAX_CHECK, timeout=self.mathjax_timeout_ms)
        except Exception:
            return

    def _route_download_safety(self, route: Any) -> None:
        url = route.request.url.lower()
        if url.endswith((".pdf", ".zip", ".rar", ".7z")):
            route.abort()
            return
        route.continue_()

    def _ensure_success(self, result: BrowserFetchResult) -> None:
        if not isinstance(result.status, int) or not 200 <= result.status < 300:
            raise BrowserAccessError(result.url, f"HTTP status {result.status}")
        if not result.html.strip():
            raise BrowserAccessError(result.url, "empty HTML")

    def _record_failure(self, url: str, reason: str) -> None:
        self.failures.append({"url": url, "reason": reason})


_MATHJAX_CHECK = """
() => Boolean(
  window.MathJax ||
  document.querySelector('script[src*="MathJax"], script[src*="mathjax"], .MathJax, mjx-container') ||
  document.querySelector('.katex, script[src*="KaTeX"], script[src*="katex"]')
)
"""
