from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.export.local_pdf_worker import TEMPLATE_VERSION, LocalPdfArticleRenderer
from app.export.local_pdf_html import (
    HtmlRenderMetrics,
    HtmlRenderResult,
    ImageSummary,
)
from app.export.local_pdf_renderer import OfflineChromiumPdfRenderer, PdfRenderResult, PdfValidationResult


@dataclass(frozen=True)
class StoredArticleStub:
    id: str
    title: str
    url: str
    content: str
    metadata: dict[str, object]


def _article(*, content: str = "正文", metadata: dict[str, object] | None = None) -> StoredArticleStub:
    return StoredArticleStub(
        id="art-001",
        title="测试标题",
        url="https://spaces.ac.cn/archives/6508",
        content=content,
        metadata=metadata or {},
    )


def _html_result(
    *,
    metrics: HtmlRenderMetrics | None = None,
    references: tuple[object, ...] | None = None,
    image_summary: tuple[ImageSummary, ...] | None = None,
) -> HtmlRenderResult:
    return HtmlRenderResult(
        title="测试标题",
        url="https://spaces.ac.cn/archives/6508",
        date="2026-07-01",
        category="数学",
        reference_count=0 if references is None else len(references),
        references=references or (),
        image_summary=image_summary or (),
        html="<html><body><p>body</p></body></html>",
        body_html="<p>body</p>",
        body_text_probes=("body",),
        metrics=metrics
        or HtmlRenderMetrics(
            markdown_input_chars=4,
            sanitized_markdown_chars=4,
            rendered_body_chars=10,
            output_html_chars=20,
            image_count=len(image_summary or ()),
            local_images_inlined=0,
            remote_images_replaced=0,
            images_placeholder=0,
            render_duration_ms=0.1,
            katex_css_length=3,
            expected_formula_count=0,
            formula_count=0,
            formula_render_failure_count=0,
            delimiter_balanced=True,
        ),
    )


def _pdf_result(*, output_path: Path, blocked_request_count: int = 0) -> PdfRenderResult:
    return PdfRenderResult(
        output_path=output_path,
        temp_html_path=output_path.parent / "tmp-html.html",
        temp_pdf_path=output_path.parent / "tmp-pdf.pdf",
        blocked_request_count=blocked_request_count,
        validation=PdfValidationResult(
            pdf_path=output_path,
            is_valid=True,
            page_count=3,
            text_length=128,
            has_title_or_article_id=True,
            suspicious_indicators=(),
            errors=(),
            pdf_size_bytes=4096,
        ),
        renderer_version="chromium-stub-v1",
    )


@dataclass
class FakeMarkdownRenderer:
    result: HtmlRenderResult
    enters: int = 0
    exits: int = 0
    calls: list[
        tuple[str, str | None, str | None, tuple[object, ...] | None, tuple[Path, ...], Path | None]
    ] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.calls = []

    def __enter__(self) -> "FakeMarkdownRenderer":
        self.enters += 1
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.exits += 1

    def render_article(
        self,
        *,
        article_id: str = "",
        title: str = "",
        url: str = "",
        markdown: str = "",
        date: str | None = None,
        category: str | None = None,
        references: object = (),
        allowed_image_roots: object = (),
        content_root: Path | None = None,
    ) -> HtmlRenderResult:
        self.calls.append(
            (
                title,
                date,
                category,
                tuple(references) if isinstance(references, tuple) else None,
                tuple(allowed_image_roots),
                content_root,
            )
        )
        return self.result

class FakePdfRenderer(OfflineChromiumPdfRenderer):
    enters: int = 0
    exits: int = 0
    calls: list[tuple[str, Path, str | None, str | None, tuple[str, ...]]] = []
    result: PdfRenderResult

    def __init__(self, result: PdfRenderResult) -> None:
        self.result = result
        self.enters = 0
        self.exits = 0
        self.calls = []

    def __enter__(self) -> "FakePdfRenderer":
        self.enters += 1
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.exits += 1

    def render_html_to_pdf(
        self,
        html: str,
        output_path: Path | str,
        *,
        title: str | None = None,
        article_id: str | None = None,
        required_text_probes: tuple[str, ...] = (),
    ) -> PdfRenderResult:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"pdf bytes")
        self.calls.append((html, output, title, article_id, required_text_probes))
        return self.result


def _images() -> tuple[ImageSummary, ...]:
    return (
        ImageSummary(source="assets/local.png", status="inlined", kind="local"),
        ImageSummary(source="https://example.com/remote.png", status="placeholder", kind="remote"),
        ImageSummary(source="broken.png", status="placeholder", kind="local"),
    )


def test_render_success_returns_expected_local_pdf_article_result(tmp_path: Path) -> None:
    output_path = tmp_path / "article.pdf"
    article = _article(
        content="$x$",
        metadata={
            "date": "2026-07-11",
            "category": "AI",
            "references": ["Ref A", {"title": "Ref B"}],
        },
    )
    html = _html_result(
        image_summary=_images(),
        metrics=HtmlRenderMetrics(
            markdown_input_chars=2,
            sanitized_markdown_chars=2,
            rendered_body_chars=7,
            output_html_chars=33,
            image_count=3,
            local_images_inlined=1,
            remote_images_replaced=1,
            images_placeholder=2,
            render_duration_ms=1.2,
            katex_css_length=16,
            expected_formula_count=1,
            formula_count=1,
            formula_render_failure_count=0,
            delimiter_balanced=True,
        ),
    )
    pdf = _pdf_result(output_path=output_path, blocked_request_count=0)

    markdown_renderer = FakeMarkdownRenderer(html)
    pdf_renderer = FakePdfRenderer(pdf)
    with LocalPdfArticleRenderer(
        markdown_renderer=markdown_renderer,
        pdf_renderer=pdf_renderer,
    ) as renderer:
        result = renderer.render(article, output_path)

    assert result.pdf_size_bytes == 4096
    assert result.page_count == 3
    assert result.text_length == 128
    assert result.formula_count == 1
    assert result.formula_render_failure_count == 0
    assert result.delimiter_balanced is True
    assert result.image_reference_count == 3
    assert result.local_image_embedded_count == 1
    assert result.remote_image_placeholder_count == 1
    assert result.broken_image_count == 1
    assert result.external_network_request_count == 0
    assert result.renderer_version == "chromium-stub-v1"
    assert result.template_version == TEMPLATE_VERSION
    assert output_path.exists()
    assert pdf_renderer.calls[0][-1] == ("body",)
    assert markdown_renderer.calls == [
        ("测试标题", "2026-07-11", "AI", ("Ref A", {"title": "Ref B"}), (), None)
    ]


def test_render_fails_when_delimiters_unbalanced_and_no_pdf_render(tmp_path: Path) -> None:
    article = _article()
    html = _html_result(
        metrics=HtmlRenderMetrics(
            markdown_input_chars=2,
            sanitized_markdown_chars=2,
            rendered_body_chars=7,
            output_html_chars=33,
            image_count=0,
            local_images_inlined=0,
            remote_images_replaced=0,
            images_placeholder=0,
            render_duration_ms=1.2,
            katex_css_length=16,
            expected_formula_count=1,
            formula_count=0,
            formula_render_failure_count=0,
            delimiter_balanced=False,
        ),
    )
    fake_pdf = _pdf_result(output_path=tmp_path / "article.pdf", blocked_request_count=0)
    markdown_renderer = FakeMarkdownRenderer(html)
    pdf_renderer = FakePdfRenderer(fake_pdf)

    with LocalPdfArticleRenderer(
        markdown_renderer=markdown_renderer,
        pdf_renderer=pdf_renderer,
    ) as renderer:
        with pytest.raises(RuntimeError, match="unbalanced"):
            renderer.render(article, tmp_path / "article.pdf")

    assert not pdf_renderer.calls


def test_render_fails_when_formula_render_failed_and_no_pdf_render(tmp_path: Path) -> None:
    article = _article()
    html = _html_result(
        metrics=HtmlRenderMetrics(
            markdown_input_chars=2,
            sanitized_markdown_chars=2,
            rendered_body_chars=7,
            output_html_chars=33,
            image_count=0,
            local_images_inlined=0,
            remote_images_replaced=0,
            images_placeholder=0,
            render_duration_ms=1.2,
            katex_css_length=16,
            expected_formula_count=1,
            formula_count=0,
            formula_render_failure_count=1,
            delimiter_balanced=True,
        ),
    )
    fake_pdf = _pdf_result(output_path=tmp_path / "article.pdf", blocked_request_count=0)
    markdown_renderer = FakeMarkdownRenderer(html)
    pdf_renderer = FakePdfRenderer(fake_pdf)

    with LocalPdfArticleRenderer(
        markdown_renderer=markdown_renderer,
        pdf_renderer=pdf_renderer,
    ) as renderer:
        with pytest.raises(RuntimeError, match="formula render failures"):
            renderer.render(article, tmp_path / "article.pdf")

    assert not pdf_renderer.calls


def test_render_fails_when_external_requests_blocked(tmp_path: Path) -> None:
    article = _article()
    html = _html_result()
    output_path = tmp_path / "article.pdf"
    fake_pdf = _pdf_result(output_path=output_path, blocked_request_count=2)
    markdown_renderer = FakeMarkdownRenderer(html)
    pdf_renderer = FakePdfRenderer(fake_pdf)

    with LocalPdfArticleRenderer(
        markdown_renderer=markdown_renderer,
        pdf_renderer=pdf_renderer,
    ) as renderer:
        with pytest.raises(RuntimeError, match="Blocked external network requests"):
            renderer.render(article, output_path)

    assert output_path.exists() is True


def test_render_passes_local_image_policy_and_custom_template_version(tmp_path: Path) -> None:
    output_path = tmp_path / "article.pdf"
    markdown_renderer = FakeMarkdownRenderer(_html_result())
    pdf_renderer = FakePdfRenderer(_pdf_result(output_path=output_path))
    image_root = tmp_path / "images"

    with LocalPdfArticleRenderer(
        markdown_renderer=markdown_renderer,
        pdf_renderer=pdf_renderer,
        allowed_image_roots=(image_root,),
        content_root=image_root,
        template_version="local-pdf-test-2",
    ) as renderer:
        result = renderer.render(_article(), output_path)

    assert result.template_version == "local-pdf-test-2"
    assert markdown_renderer.calls[0][-2:] == ((image_root,), image_root)


def test_context_manager_reuses_renderers_and_closes_once(tmp_path: Path) -> None:
    article = _article()
    html = _html_result()
    output_a = tmp_path / "article-a.pdf"
    output_b = tmp_path / "article-b.pdf"
    pdf_a = _pdf_result(output_path=output_a, blocked_request_count=0)
    pdf_b = _pdf_result(output_path=output_b, blocked_request_count=0)

    class TwoCallFakePdfRenderer(FakePdfRenderer):
        def __init__(self) -> None:
            self.calls_results = [pdf_a, pdf_b]
            super().__init__(pdf_a)

        def render_html_to_pdf(
            self,
            html: str,
            output_path: Path | str,
            *,
            title: str | None = None,
            article_id: str | None = None,
            required_text_probes: tuple[str, ...] = (),
        ) -> PdfRenderResult:
            self.calls.append((Path(output_path), required_text_probes))
            if Path(output_path) == output_a:
                return self.calls_results[0]
            if Path(output_path) == output_b:
                return self.calls_results[1]
            return self.calls_results[0]

    markdown_renderer = FakeMarkdownRenderer(html)
    pdf_renderer = TwoCallFakePdfRenderer()

    with LocalPdfArticleRenderer(
        markdown_renderer=markdown_renderer,
        pdf_renderer=pdf_renderer,
    ) as renderer:
        renderer.render(article, output_a)
        renderer.render(article, output_b)

    assert markdown_renderer.enters == 1
    assert markdown_renderer.exits == 1
    assert pdf_renderer.enters == 1
    assert pdf_renderer.exits == 1
