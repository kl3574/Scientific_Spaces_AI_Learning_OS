from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from app.export.local_pdf_html import HtmlRenderResult, NodeMarkdownRenderer
from app.export.local_pdf_renderer import OfflineChromiumPdfRenderer, PdfRenderResult

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_DIR = REPO_ROOT / ".local_data" / "local_pdf_cache"
TEMPLATE_VERSION = "local-pdf-v5"


@dataclass(frozen=True)
class LocalPdfArticleRenderResult:
    pdf_size_bytes: int
    page_count: int
    text_length: int
    formula_count: int
    formula_render_failure_count: int
    delimiter_balanced: bool
    image_reference_count: int
    local_image_embedded_count: int
    remote_image_placeholder_count: int
    broken_image_count: int
    external_network_request_count: int
    renderer_version: str
    template_version: str


class _ArticleLike(Protocol):
    id: str
    title: str
    url: str
    content: str
    metadata: Mapping[str, Any]


def _as_metadata_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _as_references(value: object) -> tuple[str | Mapping[str, Any], ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray, Mapping)):
        return tuple(value)
    if isinstance(value, Mapping):
        return (value,)
    return (value,)


class LocalPdfArticleRenderer:
    def __init__(
        self,
        *,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        allowed_image_roots: Sequence[Path] = (),
        content_root: Path | None = None,
        minimum_pdf_size_bytes: int = 1024,
        minimum_text_length: int = 50,
        template_version: str = TEMPLATE_VERSION,
        markdown_renderer: NodeMarkdownRenderer | None = None,
        pdf_renderer: OfflineChromiumPdfRenderer | None = None,
    ) -> None:
        self._markdown_renderer = markdown_renderer or NodeMarkdownRenderer()
        self._pdf_renderer = pdf_renderer or OfflineChromiumPdfRenderer(
            cache_dir=cache_dir,
            minimum_pdf_size_bytes=minimum_pdf_size_bytes,
            minimum_text_length=minimum_text_length,
            forbidden_runtime_paths=(str(REPO_ROOT),),
        )
        self._allowed_image_roots = tuple(Path(path) for path in allowed_image_roots)
        self._content_root = Path(content_root) if content_root is not None else None
        self._template_version = template_version
        self._in_context = False

    def __enter__(self) -> "LocalPdfArticleRenderer":
        if not self._in_context:
            self._markdown_renderer.__enter__()
            try:
                self._pdf_renderer.__enter__()
            except BaseException:
                self._markdown_renderer.__exit__(None, None, None)
                raise
            self._in_context = True
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._in_context:
            self._pdf_renderer.__exit__(exc_type, exc, tb)
            self._markdown_renderer.__exit__(exc_type, exc, tb)
            self._in_context = False

    def close(self) -> None:
        self.__exit__(None, None, None)

    def _build_result(
        self,
        markdown_result: HtmlRenderResult,
        pdf_result: PdfRenderResult,
    ) -> LocalPdfArticleRenderResult:
        image_summary = markdown_result.image_summary
        return LocalPdfArticleRenderResult(
            pdf_size_bytes=pdf_result.validation.pdf_size_bytes,
            page_count=pdf_result.validation.page_count,
            text_length=pdf_result.validation.text_length,
            formula_count=markdown_result.metrics.formula_count,
            formula_render_failure_count=markdown_result.metrics.formula_render_failure_count,
            delimiter_balanced=markdown_result.metrics.delimiter_balanced,
            image_reference_count=markdown_result.metrics.image_count,
            local_image_embedded_count=len(
                [
                    image
                    for image in image_summary
                    if image.status == "inlined" and image.kind == "local"
                ]
            ),
            remote_image_placeholder_count=len(
                [
                    image
                    for image in image_summary
                    if image.kind == "remote" and image.status == "placeholder"
                ]
            ),
            broken_image_count=len(
                [image for image in image_summary if image.status == "placeholder" and image.kind != "remote"]
            ),
            external_network_request_count=pdf_result.blocked_request_count,
            renderer_version=pdf_result.renderer_version,
            template_version=self._template_version,
        )

    def render(
        self,
        article: _ArticleLike,
        output_path: Path | str,
    ) -> LocalPdfArticleRenderResult:
        if not self._in_context:
            raise RuntimeError("LocalPdfArticleRenderer must be used as a context manager")

        metadata = article.metadata if isinstance(article.metadata, Mapping) else {}
        date = _as_metadata_text(metadata.get("date"))
        category = _as_metadata_text(metadata.get("category"))
        references = _as_references(metadata.get("references"))

        html_result = self._markdown_renderer.render_article(
            article_id=article.id,
            title=article.title,
            url=article.url,
            markdown=article.content,
            date=date,
            category=category,
            references=references,
            allowed_image_roots=self._allowed_image_roots,
            content_root=self._content_root,
        )

        if not html_result.metrics.delimiter_balanced:
            raise RuntimeError("Article markdown contains unbalanced formula delimiters")

        if html_result.metrics.formula_render_failure_count > 0:
            raise RuntimeError("Article contains formula render failures")

        if not html_result.body_text_probes:
            raise RuntimeError("Rendered article body has no validation text probe")

        pdf_result = self._pdf_renderer.render_html_to_pdf(
            html_result.html,
            output_path,
            title=article.title,
            article_id=article.id,
            required_text_probes=html_result.body_text_probes,
        )

        if pdf_result.blocked_request_count != 0:
            raise RuntimeError(f"Blocked external network requests: {pdf_result.blocked_request_count}")

        return self._build_result(html_result, pdf_result)
