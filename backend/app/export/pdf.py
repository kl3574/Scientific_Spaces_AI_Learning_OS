from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PdfExportResult:
    url: str
    output_path: Path
    status: str
    title: str
    http_status: int | None
    file_size_bytes: int
    duration_seconds: float
    mathjax_available: bool
    error: str | None = None


class PdfExportError(RuntimeError):
    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"Failed to export {url}: {reason}")
        self.url = url
        self.reason = reason


Renderer = Callable[[str, Path], PdfExportResult]


class ArticlePdfExporter:
    def __init__(
        self,
        *,
        renderer: Renderer | None = None,
        retries: int = 2,
        backoff_seconds: float = 1.0,
        timeout_ms: int = 30_000,
        settle_ms: int = 3_000,
        mathjax_timeout_ms: int = 10_000,
    ) -> None:
        self.renderer = renderer
        self.retries = max(retries, 1)
        self.backoff_seconds = backoff_seconds
        self.timeout_ms = timeout_ms
        self.settle_ms = settle_ms
        self.mathjax_timeout_ms = mathjax_timeout_ms
        self.failures: list[dict[str, str]] = []

    def export(self, url: str, output_path: Path | str) -> PdfExportResult:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        last_reason = "unknown error"

        for attempt in range(self.retries):
            try:
                if path.exists():
                    path.unlink()
                started_at = time.monotonic()
                result = self._render(url, path)
                file_size = validate_pdf_file(path, url=url)
                return PdfExportResult(
                    url=result.url,
                    output_path=path,
                    status="success",
                    title=result.title,
                    http_status=result.http_status,
                    file_size_bytes=file_size,
                    duration_seconds=max(result.duration_seconds, time.monotonic() - started_at),
                    mathjax_available=result.mathjax_available,
                    error=None,
                )
            except Exception as exc:  # noqa: BLE001 - preserve Playwright and renderer detail.
                if path.exists():
                    path.unlink()
                last_reason = _failure_reason(exc)
                if attempt < self.retries - 1 and self.backoff_seconds:
                    time.sleep(self.backoff_seconds * (attempt + 1))

        self._record_failure(url, last_reason)
        raise PdfExportError(url, last_reason)

    def _render(self, url: str, output_path: Path) -> PdfExportResult:
        if self.renderer is not None:
            return self.renderer(url, output_path)
        return self._render_with_playwright(url, output_path)

    def _render_with_playwright(self, url: str, output_path: Path) -> PdfExportResult:
        from playwright.sync_api import sync_playwright

        started_at = time.monotonic()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, timeout=self.timeout_ms)
            context = browser.new_context(accept_downloads=False)
            context.route("**/*", self._route_download_safety)
            page = context.new_page()
            try:
                response = page.goto(url, wait_until="commit", timeout=self.timeout_ms)
                page.wait_for_timeout(self.settle_ms)
                mathjax_available = self._wait_for_mathjax(page)
                title = page.title()
                http_status = response.status if response else None
                if not isinstance(http_status, int) or not 200 <= http_status < 300:
                    raise PdfExportError(url, f"HTTP status {http_status}")
                page.emulate_media(media="print")
                page.pdf(path=str(output_path), format="A4", print_background=True)
                return PdfExportResult(
                    url=url,
                    output_path=output_path,
                    status="success",
                    title=title,
                    http_status=http_status,
                    file_size_bytes=0,
                    duration_seconds=time.monotonic() - started_at,
                    mathjax_available=mathjax_available,
                    error=None,
                )
            finally:
                page.close()
                context.close()
                browser.close()

    def _wait_for_mathjax(self, page: Any) -> bool:
        mathjax_available = False
        try:
            mathjax_available = bool(page.evaluate(_MATHJAX_AVAILABLE_CHECK))
        except Exception:
            return False

        if not mathjax_available:
            return False

        try:
            page.wait_for_function(_MATHJAX_READY_CHECK, timeout=self.mathjax_timeout_ms)
        except Exception:
            return mathjax_available

        try:
            return bool(page.evaluate(_MATHJAX_AVAILABLE_CHECK))
        except Exception:
            return mathjax_available

    def _route_download_safety(self, route: Any) -> None:
        url = route.request.url.lower()
        if url.endswith((".pdf", ".zip", ".rar", ".7z")):
            route.abort()
            return
        route.continue_()

    def _record_failure(self, url: str, reason: str) -> None:
        self.failures.append({"url": url, "reason": reason})


def validate_pdf_file(path: Path | str, *, url: str = "") -> int:
    pdf_path = Path(path)
    source_url = url or str(pdf_path)
    if not pdf_path.exists():
        raise PdfExportError(source_url, "PDF file does not exist")
    file_size = pdf_path.stat().st_size
    if file_size <= 0:
        raise PdfExportError(source_url, "PDF file is empty")
    with pdf_path.open("rb") as file:
        header = file.read(5)
    if header != b"%PDF-":
        raise PdfExportError(source_url, "invalid PDF header")
    return file_size


def _failure_reason(exc: Exception) -> str:
    if isinstance(exc, PdfExportError):
        return exc.reason
    return f"{type(exc).__name__}: {exc}"


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
