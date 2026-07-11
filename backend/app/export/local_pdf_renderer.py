from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

_PLAYWRIGHT_IMPORT_ERROR: Exception | None = None

try:
    from playwright.sync_api import sync_playwright
except Exception as exc:  # pragma: no cover - exercised in integration tests
    sync_playwright = None  # type: ignore[assignment]
    _PLAYWRIGHT_IMPORT_ERROR = exc


@dataclass(frozen=True)
class PdfValidationResult:
    pdf_path: Path
    is_valid: bool
    page_count: int
    text_length: int
    has_title_or_article_id: bool
    suspicious_indicators: tuple[str, ...]
    errors: tuple[str, ...]
    pdf_size_bytes: int = 0


@dataclass(frozen=True)
class PdfRenderResult:
    output_path: Path
    temp_html_path: Path
    temp_pdf_path: Path
    blocked_request_count: int
    validation: PdfValidationResult
    renderer_version: str = "chromium-unknown"


class OfflinePdfRendererError(RuntimeError):
    """Raised when local Chromium rendering or validation fails."""

    def __init__(self, message: str, *, blocked_request_count: int = 0) -> None:
        super().__init__(message)
        self.blocked_request_count = blocked_request_count


_NETWORK_SCHEMES = ("http://", "https://", "ws://", "wss://")
_PAGE_COUNT_PATTERN = re.compile(r"^\s*Pages:\s+(\d+)", re.MULTILINE | re.IGNORECASE)
_PDF_HEADERS = (b"%PDF-",)
_COMMAND_TIMEOUT_SECONDS = 30
_MINIMUM_PDF_SIZE_BYTES = 1024
_MINIMUM_EXTRACTED_TEXT_LENGTH = 50
_PDF_PAGE_MARGINS = {"top": "12mm", "bottom": "14mm", "left": "10mm", "right": "10mm"}
_SUSPICIOUS_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("chrome error page marker", re.compile(r"chrome-error://", re.IGNORECASE)),
    ("chrome runtime marker", re.compile(r"\bruntime\b.*\berror\b", re.IGNORECASE)),
    ("net:: error marker", re.compile(r"net::\w+", re.IGNORECASE)),
)

_DOC_FONTS_READY_SCRIPT = "() => document.fonts.ready"
_DATA_IMAGE_DECODE_SCRIPT = """
() => Promise.all(
  Array.from(document.images)
    .filter((image) => image.currentSrc && image.currentSrc.startsWith('data:'))
    .map((image) => image.decode().catch(() => null))
)
"""
_KATEX_DISPLAY_STYLE = """
@media print {
  .katex-display {
    width: 100%;
    max-width: 100%;
    overflow-x: clip;
  }
}
"""
_KATEX_DISPLAY_SCALE_SCRIPT = """
() => {
  const nodes = Array.from(document.querySelectorAll('.katex-display'));
  const pageWidth = document.body ? document.body.clientWidth : window.innerWidth;
  if (!pageWidth) {
    return;
  }
  for (const node of nodes) {
    const logicalWidth = node.scrollWidth || node.clientWidth;
    if (!logicalWidth || logicalWidth <= pageWidth) {
      continue;
    }
    const scale = Math.min(1, pageWidth / logicalWidth);
    node.style.transformOrigin = 'left top';
    node.style.transform = `scale(${scale.toFixed(4)})`;
    node.style.maxWidth = '100%';
    node.style.width = `${pageWidth}px`;
  }
}
"""


def _parse_pdf_pages(output: str) -> int:
    match = _PAGE_COUNT_PATTERN.search(output)
    if not match:
        return 0
    return int(match.group(1))


def _check_suspicious_text(text: str) -> tuple[str, ...]:
    result: list[str] = []
    for label, pattern in _SUSPICIOUS_TEXT_PATTERNS:
        if pattern.search(text):
            result.append(label)
    return tuple(result)


def validate_pdf_artifact(
    pdf_path: Path | str,
    *,
    title: str | None = None,
    article_id: str | None = None,
    minimum_pdf_size_bytes: int = _MINIMUM_PDF_SIZE_BYTES,
    minimum_text_length: int = _MINIMUM_EXTRACTED_TEXT_LENGTH,
    forbidden_runtime_paths: tuple[str, ...] = (),
    required_text_probes: tuple[str, ...] = (),
) -> PdfValidationResult:
    path = Path(pdf_path)
    if not path.exists():
        raise OfflinePdfRendererError(f"PDF file missing: {path}")
    pdf_size_bytes = path.stat().st_size
    if pdf_size_bytes < minimum_pdf_size_bytes:
        raise OfflinePdfRendererError(
            f"PDF size {pdf_size_bytes} is below minimum {minimum_pdf_size_bytes}: {path}"
        )
    with path.open("rb") as handle:
        if not handle.read(5).startswith(_PDF_HEADERS[0]):
            raise OfflinePdfRendererError(f"Invalid PDF header: {path}")

    pdfinfo_path = shutil.which("pdfinfo")
    pdftotext_path = shutil.which("pdftotext")
    if pdfinfo_path is None:
        raise RuntimeError("pdfinfo is required for PDF validation")
    if pdftotext_path is None:
        raise RuntimeError("pdftotext is required for PDF validation")

    page_count = 0
    text = ""
    errors: list[str] = []

    info_result = subprocess.run(
        [pdfinfo_path, str(path)],
        capture_output=True,
        text=True,
        timeout=_COMMAND_TIMEOUT_SECONDS,
    )
    if info_result.returncode != 0:
        errors.append(f"pdfinfo failed: {info_result.stderr.strip()}")
    else:
        page_count = _parse_pdf_pages(info_result.stdout)
        if page_count < 1:
            errors.append(f"pdfinfo page_count={page_count}")

    text_result = subprocess.run(
        [pdftotext_path, str(path), "-"],
        capture_output=True,
        text=True,
        timeout=_COMMAND_TIMEOUT_SECONDS,
    )
    if text_result.returncode != 0:
        errors.append(f"pdftotext failed: {text_result.stderr.strip()}")
    else:
        text = text_result.stdout
        if not text.strip():
            errors.append("empty extracted text")
        normalized_text_length = len(re.sub(r"\s+", "", text))
        if normalized_text_length < minimum_text_length:
            errors.append(
                f"extracted text length {normalized_text_length} is below minimum {minimum_text_length}"
            )

    has_title_or_article_id = True
    if title or article_id:
        has_title_or_article_id = False
        lower_text = text.lower()
        if title and title.lower() in lower_text:
            has_title_or_article_id = True
        if article_id and article_id.lower() in lower_text:
            has_title_or_article_id = True
        if not has_title_or_article_id:
            errors.append("title/article_id not present in extracted text")

    suspicious = _check_suspicious_text(text)
    normalized_runtime_paths = tuple(
        value.replace("\\", "/").rstrip("/").lower()
        for value in forbidden_runtime_paths
        if value.strip()
    )
    normalized_text = text.replace("\\", "/").lower()
    leaked_runtime_paths = tuple(
        runtime_path for runtime_path in normalized_runtime_paths if runtime_path in normalized_text
    )
    if leaked_runtime_paths:
        suspicious = (*suspicious, "runtime path disclosure")
        errors.append("runtime path present in extracted text")
    if suspicious:
        if not leaked_runtime_paths:
            errors.append(f"suspicious content: {', '.join(suspicious)}")

    normalized_probe_text = "".join(
        character.casefold() for character in text if character.isalnum()
    )
    normalized_probes = tuple(
        normalized
        for probe in required_text_probes
        if (
            normalized := "".join(
                character.casefold() for character in probe if character.isalnum()
            )
        )
    )
    if normalized_probes and not any(probe in normalized_probe_text for probe in normalized_probes):
        errors.append("body text probes missing from extracted PDF text")

    return PdfValidationResult(
        pdf_path=path,
        is_valid=(len(errors) == 0),
        page_count=page_count,
        text_length=len(text),
        has_title_or_article_id=has_title_or_article_id,
        suspicious_indicators=suspicious,
        errors=tuple(errors),
        pdf_size_bytes=pdf_size_bytes,
    )


class OfflineChromiumPdfRenderer:
    """Offline renderer that reuses one Chromium browser/context/page pair."""

    def __init__(
        self,
        cache_dir: Path | str,
        *,
        minimum_pdf_size_bytes: int = _MINIMUM_PDF_SIZE_BYTES,
        minimum_text_length: int = _MINIMUM_EXTRACTED_TEXT_LENGTH,
        forbidden_runtime_paths: tuple[str, ...] = (),
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.minimum_pdf_size_bytes = minimum_pdf_size_bytes
        self.minimum_text_length = minimum_text_length
        self.forbidden_runtime_paths = forbidden_runtime_paths
        self._playwright_manager: Any | None = None
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._context: Any | None = None
        self._page: Any | None = None
        self._blocked_request_count = 0
        self.renderer_version = "chromium-unknown"

    def __enter__(self) -> "OfflineChromiumPdfRenderer":
        if sync_playwright is None:
            raise RuntimeError(
                f"playwright not available: {type(_PLAYWRIGHT_IMPORT_ERROR).__name__}: {_PLAYWRIGHT_IMPORT_ERROR}"
            )
        self._playwright_manager = sync_playwright()
        self._playwright = (
            self._playwright_manager.start()
            if hasattr(self._playwright_manager, "start")
            else self._playwright_manager.__enter__()
        )
        self._browser = self._playwright.chromium.launch(headless=True)
        browser_version = getattr(self._browser, "version", "unknown")
        self.renderer_version = f"chromium-{browser_version}"
        self._context = self._browser.new_context()
        self._context.route("**/*", self._route_block_external_requests)
        self._page = self._context.new_page()
        return self

    def __exit__(self, exc_type: type | None, exc: BaseException | None, tb: Any) -> None:
        if self._page is not None:
            try:
                self._page.close()
            except Exception:
                pass
            self._page = None
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright_manager is not None:
            stop = getattr(self._playwright_manager, "stop", None)
            if callable(stop):
                try:
                    stop()
                except Exception:
                    pass
            else:
                exit_ctx = getattr(self._playwright_manager, "__exit__", None)
                if callable(exit_ctx):
                    try:
                        exit_ctx(None, None, None)
                    except Exception:
                        pass
            self._playwright_manager = None
            self._playwright = None

    def _route_block_external_requests(self, route: Any) -> None:
        request = getattr(route, "request", None)
        url = getattr(request, "url", "")
        if isinstance(url, str) and url.lower().startswith(_NETWORK_SCHEMES):
            self._blocked_request_count += 1
            route.abort()
            return
        route.continue_()

    def render_html_to_pdf(
        self,
        html: str,
        output_path: Path | str,
        *,
        title: str | None = None,
        article_id: str | None = None,
        required_text_probes: tuple[str, ...] = (),
    ) -> PdfRenderResult:
        if self._page is None:
            raise RuntimeError("Renderer must be used inside a context manager")

        output = Path(output_path)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        output.parent.mkdir(parents=True, exist_ok=True)

        temp_html = self.cache_dir / f"tmp-{uuid4().hex}.html"
        temp_pdf = self.cache_dir / f"tmp-{uuid4().hex}.pdf"
        self._blocked_request_count = 0

        try:
            temp_html.write_text(html, encoding="utf-8")
            self._page.set_content(html, wait_until="load")
            self._page.emulate_media(media="print")
            self._page.add_style_tag(content=_KATEX_DISPLAY_STYLE)
            self._page.evaluate(_DOC_FONTS_READY_SCRIPT)
            self._page.evaluate(_KATEX_DISPLAY_SCALE_SCRIPT)
            self._page.evaluate(_DATA_IMAGE_DECODE_SCRIPT)
            self._page.pdf(
                path=str(temp_pdf),
                format="A4",
                print_background=True,
                margin=_PDF_PAGE_MARGINS,
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=(
                    '<div style="width:100%;font-size:8px;color:#666;text-align:center;">'
                    '<span class="pageNumber"></span> / <span class="totalPages"></span>'
                    "</div>"
                ),
            )
            if self._blocked_request_count != 0:
                raise OfflinePdfRendererError(
                    f"blocked {self._blocked_request_count} external network requests",
                    blocked_request_count=self._blocked_request_count,
                )

            validation = validate_pdf_artifact(
                temp_pdf,
                title=title,
                article_id=article_id,
                minimum_pdf_size_bytes=self.minimum_pdf_size_bytes,
                minimum_text_length=self.minimum_text_length,
                forbidden_runtime_paths=(
                    *self.forbidden_runtime_paths,
                    str(self.cache_dir.resolve()),
                    str(output.parent.resolve()),
                ),
                required_text_probes=required_text_probes,
            )
            if not validation.is_valid:
                raise OfflinePdfRendererError(f"PDF validation failed: {validation.errors}")

            os.replace(temp_pdf, output)
            return PdfRenderResult(
                output_path=output,
                temp_html_path=temp_html,
                temp_pdf_path=temp_pdf,
                blocked_request_count=self._blocked_request_count,
                validation=validation,
                renderer_version=self.renderer_version,
            )
        finally:
            if temp_html.exists():
                temp_html.unlink(missing_ok=True)
            if temp_pdf.exists():
                temp_pdf.unlink(missing_ok=True)
