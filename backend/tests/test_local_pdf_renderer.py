import os
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.export.local_pdf_renderer import (
    OfflineChromiumPdfRenderer,
    OfflinePdfRendererError,
    PdfRenderResult,
    PdfValidationResult,
    validate_pdf_artifact,
)


VALID_PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n" + (b"0" * 2048) + b"\n%%EOF\n"
NETWORK_HTML = """
<html>
  <body>
    <img src="https://cdn.example.com/formula.png" />
    <img src="wss://api.example.com/socket" />
    <span class="katex-display">x=1+1</span>
  </body>
</html>
"""


class FakeRequest:
    def __init__(self, url: str) -> None:
        self.url = url


class FakeRoute:
    def __init__(self, request: FakeRequest) -> None:
        self.request = request
        self.aborted = False
        self.continued = False

    def abort(self) -> None:
        self.aborted = True

    def continue_(self) -> None:
        self.continued = True


class FakePage:
    def __init__(self, context: "FakeContext") -> None:
        self.context = context
        self.set_content_calls: list[tuple[str, str | None]] = []
        self.pdf_calls: list[tuple[str, dict[str, object]]] = []
        self.evaluate_calls: list[str] = []
        self.style_calls: list[str] = []
        self.emulate_media_calls: list[str] = []
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def set_content(self, html: str, wait_until: str | None = None) -> None:
        self.set_content_calls.append((html, wait_until))
        for url in _extract_urls(html):
            for handler in self.context.route_handlers:
                route = FakeRoute(FakeRequest(url))
                handler(route)
                if route.aborted:
                    self.context.blocked_request_count += 1

    def add_style_tag(self, content: str | None = None, **kwargs: object) -> None:
        if content is not None:
            self.style_calls.append(content)

    def evaluate(self, script: str) -> object:
        self.evaluate_calls.append(script)
        return True

    def emulate_media(self, *, media: str) -> None:
        self.emulate_media_calls.append(media)

    def pdf(self, **kwargs: object) -> None:
        self.pdf_calls.append((str(kwargs["path"]), dict(kwargs)))
        path = Path(str(kwargs["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(VALID_PDF_BYTES)


class FakeContext:
    def __init__(self) -> None:
        self.route_handlers: list[object] = []
        self.pages: list[FakePage] = []
        self.new_page_calls = 0
        self.new_page_page: FakePage | None = None
        self.blocked_request_count = 0
        self.closed = False

    def route(self, pattern: str, handler) -> None:
        self.route_handlers.append(handler)

    def new_page(self) -> FakePage:
        self.new_page_calls += 1
        self.new_page_page = FakePage(self)
        self.pages.append(self.new_page_page)
        return self.new_page_page

    def close(self) -> None:
        self.closed = True

    @property
    def blocked_requests(self) -> int:
        return self.blocked_request_count

    @property
    def route_handler_count(self) -> int:
        return len(self.route_handlers)


class FakeBrowser:
    def __init__(self) -> None:
        self.version = "149.0.0"
        self.context = FakeContext()
        self.new_context_calls = 0
        self.new_context_args: list[dict[str, object]] = []
        self.launch_calls: list[dict[str, object]] = []
        self.closed = False

    def new_context(self, **kwargs: object) -> FakeContext:
        self.new_context_calls += 1
        self.new_context_args.append(dict(kwargs))
        return self.context

    def close(self) -> None:
        self.closed = True


class FakePlaywright:
    def __init__(self, browser: FakeBrowser) -> None:
        self.browser = browser
        self.chromium = SimpleNamespace(launch=self._launch)
        self.launch_calls: list[dict[str, object]] = []

    def _launch(self, **kwargs: object) -> FakeBrowser:
        self.launch_calls.append(dict(kwargs))
        self.launch_kwargs = dict(kwargs)
        return self.browser


class FakePlaywrightManager:
    def __init__(self) -> None:
        self.browser = FakeBrowser()
        self.playwright = FakePlaywright(self.browser)
        self.started = False
        self.stopped = False

    def start(self) -> FakePlaywright:
        self.started = True
        return self.playwright

    def stop(self) -> None:
        self.stopped = True


def _install_fake_playwright(monkeypatch: pytest.MonkeyPatch) -> FakePlaywrightManager:
    manager = FakePlaywrightManager()
    monkeypatch.setattr("app.export.local_pdf_renderer.sync_playwright", lambda: manager)
    return manager


def _extract_urls(html: str) -> list[str]:
    pattern = re.compile(r"(?:https?://[^\"'\\s]+|wss?://[^\"'\\s]+)")
    return pattern.findall(html)


def test_validate_pdf_artifact_parses_pdfinfo_and_pdftotext(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(VALID_PDF_BYTES)

    def fake_which(cmd: str) -> str:
        return f"/usr/bin/{cmd}"

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if cmd[0].endswith("pdfinfo"):
            return subprocess.CompletedProcess(cmd, 0, stdout="Title:  Article\nPages:          2\n", stderr="")
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="Example title with Article and enough extracted article body text for validation.",
            stderr="",
        )

    monkeypatch.setattr("app.export.local_pdf_renderer.shutil.which", fake_which)
    monkeypatch.setattr("app.export.local_pdf_renderer.subprocess.run", fake_run)

    result = validate_pdf_artifact(pdf, title="Article")

    assert result.is_valid is True
    assert result.page_count == 2
    assert result.text_length > 0
    assert result.has_title_or_article_id is True


def test_validate_pdf_artifact_fail_fast_if_missing_pdfinfo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(VALID_PDF_BYTES)

    def fake_which(cmd: str) -> str | None:
        if cmd == "pdfinfo":
            return None
        return f"/usr/bin/{cmd}"

    monkeypatch.setattr("app.export.local_pdf_renderer.shutil.which", fake_which)

    with pytest.raises(RuntimeError, match="pdfinfo"):
        validate_pdf_artifact(pdf)


def test_validate_pdf_artifact_rejects_suspicious_error_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(VALID_PDF_BYTES)

    monkeypatch.setattr("app.export.local_pdf_renderer.shutil.which", lambda cmd: f"/usr/bin/{cmd}")

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if cmd[0].endswith("pdfinfo"):
            return subprocess.CompletedProcess(cmd, 0, stdout="Pages: 1", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="chrome-error://page runtime error", stderr="")

    monkeypatch.setattr("app.export.local_pdf_renderer.subprocess.run", fake_run)

    result = validate_pdf_artifact(pdf, title="Article")

    assert result.is_valid is False
    assert result.suspicious_indicators
    assert "chrome error page marker" in result.suspicious_indicators


def test_validate_pdf_artifact_rejects_short_text_and_runtime_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(VALID_PDF_BYTES)
    runtime_path = str((tmp_path / "private-runtime").resolve())
    monkeypatch.setattr("app.export.local_pdf_renderer.shutil.which", lambda cmd: f"/usr/bin/{cmd}")

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if cmd[0].endswith("pdfinfo"):
            return subprocess.CompletedProcess(cmd, 0, stdout="Pages: 1", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=f"Article {runtime_path}", stderr="")

    monkeypatch.setattr("app.export.local_pdf_renderer.subprocess.run", fake_run)

    result = validate_pdf_artifact(
        pdf,
        article_id="Article",
        minimum_text_length=100,
        forbidden_runtime_paths=(runtime_path,),
    )

    assert result.is_valid is False
    assert result.pdf_size_bytes == len(VALID_PDF_BYTES)
    assert any("text length" in error for error in result.errors)
    assert any("runtime path" in error for error in result.errors)


def test_validate_pdf_artifact_requires_body_derived_text_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(VALID_PDF_BYTES)
    monkeypatch.setattr("app.export.local_pdf_renderer.shutil.which", lambda cmd: f"/usr/bin/{cmd}")

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if cmd[0].endswith("pdfinfo"):
            return subprocess.CompletedProcess(cmd, 0, stdout="Pages: 1", stderr="")
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="Article metadata is present but the actual body is missing from this PDF.",
            stderr="",
        )

    monkeypatch.setattr("app.export.local_pdf_renderer.subprocess.run", fake_run)

    result = validate_pdf_artifact(
        pdf,
        title="Article",
        required_text_probes=("正文唯一标记",),
    )

    assert result.is_valid is False
    assert any("body text probe" in error for error in result.errors)


def test_validate_pdf_artifact_accepts_any_matching_body_probe(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "input.pdf"
    pdf.write_bytes(VALID_PDF_BYTES)
    monkeypatch.setattr("app.export.local_pdf_renderer.shutil.which", lambda cmd: f"/usr/bin/{cmd}")

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if cmd[0].endswith("pdfinfo"):
            return subprocess.CompletedProcess(cmd, 0, stdout="Pages: 1", stderr="")
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout="Article and enough text with 正文开头唯一标记 to validate the rendered body.",
            stderr="",
        )

    monkeypatch.setattr("app.export.local_pdf_renderer.subprocess.run", fake_run)

    result = validate_pdf_artifact(
        pdf,
        title="Article",
        required_text_probes=("正文开头唯一标记", "公式分页后可能被改写"),
    )

    assert result.is_valid is True


def test_offline_renderer_reuses_persistent_browser_context_and_page(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manager = _install_fake_playwright(monkeypatch)
    monkeypatch.setattr(
        "app.export.local_pdf_renderer.validate_pdf_artifact",
        lambda *args, **kwargs: PdfValidationResult(
            pdf_path=Path(args[0]),
            is_valid=True,
            page_count=1,
            text_length=20,
            has_title_or_article_id=True,
            suspicious_indicators=(),
            errors=(),
        ),
    )

    cache_dir = tmp_path / "cache"
    output = tmp_path / "out" / "article.pdf"
    with OfflineChromiumPdfRenderer(cache_dir=cache_dir) as renderer:
        first = renderer.render_html_to_pdf("<html><body>first</body></html>", output, title="first")
        second = renderer.render_html_to_pdf(
            "<html><body>second</body></html>",
            output,
            title="second",
        )

    browser = manager.browser
    context = browser.context
    page = context.pages[0]
    assert isinstance(first, PdfRenderResult)
    assert isinstance(second, PdfRenderResult)
    assert manager.playwright.launch_calls == [ {"headless": True} ]
    assert browser.new_context_calls == 1
    assert context.new_page_calls == 1
    assert context.route_handler_count == 1
    assert len(page.evaluate_calls) >= 3
    assert any("document.fonts.ready" in call for call in page.evaluate_calls)
    assert any("image.currentSrc" in call for call in page.evaluate_calls)
    assert any("katex-display" in style for style in page.style_calls)
    assert any(call["format"] == "A4" for _, call in page.pdf_calls)
    assert all(call["print_background"] is True for _, call in page.pdf_calls)
    assert all(call["display_header_footer"] is True for _, call in page.pdf_calls)
    assert any("pageNumber" in str(call["footer_template"]) for _, call in page.pdf_calls)
    assert page.emulate_media_calls == ["print", "print"]
    assert first.renderer_version.startswith("chromium-")


def test_offline_renderer_blocks_http_ws_requests_and_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    manager = _install_fake_playwright(monkeypatch)
    cache_dir = tmp_path / "cache"
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"kept")

    monkeypatch.setattr(
        "app.export.local_pdf_renderer.validate_pdf_artifact",
        lambda *args, **kwargs: PdfValidationResult(
            pdf_path=Path(args[0]),
            is_valid=True,
            page_count=1,
            text_length=10,
            has_title_or_article_id=True,
            suspicious_indicators=(),
            errors=(),
        ),
    )

    with OfflineChromiumPdfRenderer(cache_dir=cache_dir) as renderer:
        with pytest.raises(OfflinePdfRendererError, match="blocked 2 external network requests"):
            renderer.render_html_to_pdf(NETWORK_HTML, output, article_id="article-1")

    assert output.read_bytes() == b"kept"
    assert list(cache_dir.glob("*.html")) == []
    assert list(cache_dir.glob("*.pdf")) == []
    assert manager.browser.context.blocked_requests == 2


def test_offline_renderer_replaces_output_after_validation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_fake_playwright(monkeypatch)
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"old")
    cache_dir = tmp_path / "cache"

    def fake_validate(*args: object, **_: object) -> PdfValidationResult:
        return PdfValidationResult(
            pdf_path=Path(args[0]),
            is_valid=True,
            page_count=1,
            text_length=100,
            has_title_or_article_id=True,
            suspicious_indicators=(),
            errors=(),
        )

    monkeypatch.setattr("app.export.local_pdf_renderer.validate_pdf_artifact", fake_validate)

    with OfflineChromiumPdfRenderer(cache_dir=cache_dir) as renderer:
        result = renderer.render_html_to_pdf("<html><body>safe</body></html>", output)

    assert result.output_path == output
    assert output.read_bytes() == VALID_PDF_BYTES
    assert list(cache_dir.glob("*.html")) == []
    assert list(cache_dir.glob("*.pdf")) == []


def test_offline_renderer_keeps_existing_pdf_when_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_fake_playwright(monkeypatch)
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"old-content")
    cache_dir = tmp_path / "cache"

    def fake_validate(*args: object, **_: object) -> PdfValidationResult:
        return PdfValidationResult(
            pdf_path=Path(args[0]),
            is_valid=False,
            page_count=0,
            text_length=0,
            has_title_or_article_id=False,
            suspicious_indicators=("chrome error page marker",),
            errors=("invalid",),
        )

    monkeypatch.setattr("app.export.local_pdf_renderer.validate_pdf_artifact", fake_validate)

    with OfflineChromiumPdfRenderer(cache_dir=cache_dir) as renderer:
        with pytest.raises(OfflinePdfRendererError, match="PDF validation failed"):
            renderer.render_html_to_pdf("<html><body>safe</body></html>", output)

    assert output.read_bytes() == b"old-content"
    assert list(cache_dir.glob("*.html")) == []
    assert list(cache_dir.glob("*.pdf")) == []


@pytest.mark.skipif(
    os.getenv("RUN_LOCAL_PDF_INTEGRATION") != "1",
    reason="Enable with RUN_LOCAL_PDF_INTEGRATION=1",
)
def test_local_pdf_renderer_integration_smoke(tmp_path: Path) -> None:
    if shutil.which("pdfinfo") is None or shutil.which("pdftotext") is None:
        pytest.skip("pdfinfo/pdftotext missing")

    output = tmp_path / "integration-output.pdf"
    with OfflineChromiumPdfRenderer(cache_dir=tmp_path / "cache") as renderer:
        result = renderer.render_html_to_pdf(
            "<html><head><meta charset='utf-8'/></head><body><h1>integration</h1></body></html>",
            output,
            title="integration",
        )

    assert result.output_path == output
    assert result.validation.is_valid
