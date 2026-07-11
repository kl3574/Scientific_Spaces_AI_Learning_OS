from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from app.export import local_pdf_html as pdf_html


def test_default_paths_resolve_from_repository_root() -> None:
    repository_root = Path(__file__).resolve().parents[2]

    assert pdf_html.DEFAULT_FRONTEND_NODE_MODULES == repository_root / "frontend" / "node_modules"
    assert pdf_html.DEFAULT_RENDER_SCRIPT == repository_root / "scripts" / "export" / "render_local_pdf_html.mjs"


def test_prepare_markdown_for_math_transforms_inline_and_single_line_display_math_and_preserves_code_blocks() -> None:

    content = (
        "中文段落 $$a+b=c$$ 与正文。\n\n"
        "```\n"
        "print(\"$$should_keep$$\")\n"
        "```\n\n"
        "这里是\\(x=1\\) 与\\[y=2\\] 的公式。"
    )

    prepared = pdf_html.prepare_markdown_for_math(content)

    assert "\n\n$$\na+b=c\n$$\n\n" in prepared
    assert "```\nprint(\"$$should_keep$$\")\n```" in prepared
    assert "$x=1$" in prepared
    assert "\n\n$$\ny=2\n$$\n\n" in prepared


def test_prepare_markdown_for_math_normalizes_legacy_mathjax_syntax_for_katex() -> None:
    content = (
        "$$\\style{border:1px solid #123456}{x}$$\n"
        "$$\\newcommand{\\argmin}{\\mathop{\\text{argmin}}}\\argmin_x x$$\n"
        "$$\\mathop{argmin}_\\boldsymbol{B} x$$\n"
        "$$\\clip\\nolimits_{[0,1]}(x)$$\n"
        "$$\\begin{eqnarray\\*}a&=&b\\\\c&=&d\\end{eqnarray\\*}$$\n"
        "$$\\begin{array}{\\cdot {20}{c}}a\\\\b\\end{array}$$\n"
        "$$\\text{head_dims} \\textbf{61.15%}$$\n"
        "$$\\begin{aligned}a&=b\\tag{1}\\\\c&=d\\tag{2}\\end{aligned}$$"
    )

    prepared = pdf_html.prepare_markdown_for_math(content)

    assert "\\htmlStyle{border:1px solid #123456}{x}" in prepared
    assert "\\providecommand{\\argmin}" in prepared
    assert "_{\\boldsymbol{B}}" in prepared
    assert "\\mathop{\\mathrm{clip}}\\nolimits" in prepared
    assert "\\begin{aligned}a&=b" in prepared
    assert "\\end{aligned}" in prepared
    assert "\\begin{array}{c}" in prepared
    assert "\\text{head\\_dims}" in prepared
    assert "\\textbf{61.15\\%}" in prepared
    assert "\\tag{" not in prepared


def test_prepare_markdown_for_math_stabilizes_numeric_and_multiline_inline_boundaries() -> None:
    content = (
        "value10171017$10^17$，next $\\phi(x)$0，e^{x}$\\phi(x)$ 1。\n\n"
        "那么$\\sum_{i=1}^n\n\nx_i$的最小值。"
    )

    prepared = pdf_html.prepare_markdown_for_math(content)

    assert "10171017 $10^17$，" in prepared
    assert "$\\phi(x)$ 0" in prepared
    assert "e^{x} $\\phi(x)$ 1" in prepared
    assert "\n\n$$\n\\sum_{i=1}^n\n\nx_i\n$$\n\n" in prepared


@pytest.mark.skipif(
    not pdf_html.has_node_binary() or not pdf_html.has_frontend_node_modules(),
    reason="local node renderer is unavailable",
)
def test_node_render_handles_numeric_and_multiline_inline_boundaries() -> None:
    markdown = (
        "value10171017$10^17$，next $\\phi(x)$0，e^{x}$\\phi(x)$ 1。\n\n"
        "那么$\\sum_{i=1}^n\n\nx_i$的最小值。"
    )
    with pdf_html.NodeMarkdownRenderer() as renderer:
        result = renderer.render_article(
            article_id="boundary-math",
            title="Boundary math",
            url="https://spaces.ac.cn/archives/5",
            markdown=markdown,
        )

    assert result.metrics.expected_formula_count == 4
    assert result.metrics.formula_count == 4
    assert result.metrics.formula_render_failure_count == 0


def test_sanitize_markdown_images_inlines_local_png_and_returns_summary(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    image_path = assets / "logo.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)

    markdown = "![logo](assets/logo.png)"
    sanitized, summaries = pdf_html.sanitize_markdown_images(
        markdown,
        allowed_image_roots=(assets,),
        content_root=tmp_path,
        max_local_image_size_bytes=64,
    )

    assert len(summaries) == 1
    assert summaries[0].status == "inlined"
    assert summaries[0].kind == "local"
    assert "assets/logo.png" not in sanitized
    assert sanitized.startswith("![logo](data:image/png;base64,")


def test_sanitize_markdown_images_requires_explicit_local_allowlist(tmp_path: Path) -> None:
    image_path = tmp_path / "private.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)

    sanitized, summaries = pdf_html.sanitize_markdown_images(
        f"![private]({image_path})",
        allowed_image_roots=(),
        content_root=tmp_path,
    )

    assert summaries[0].status == "placeholder"
    assert summaries[0].kind == "local"
    assert summaries[0].reason == "local images disabled"
    assert str(image_path) not in sanitized


def test_sanitize_markdown_images_validates_input_data_uri_mime_and_size() -> None:
    forbidden, forbidden_summary = pdf_html.sanitize_markdown_images(
        "![html](data:text/html;base64,PGgxPm5vdCBhbiBpbWFnZTwvaDE+)",
        allowed_image_roots=(),
    )
    oversized_source = "data:image/png;base64," + ("A" * 200)
    oversized, oversized_summary = pdf_html.sanitize_markdown_images(
        f"![large]({oversized_source})",
        allowed_image_roots=(),
        max_local_image_size_bytes=32,
    )

    assert forbidden_summary[0].status == "placeholder"
    assert forbidden_summary[0].reason == "unsupported data image"
    assert "data:text/html" not in forbidden
    assert oversized_summary[0].status == "placeholder"
    assert oversized_summary[0].reason == "data image size exceeds policy"
    assert oversized_source not in oversized


def test_sanitize_markdown_images_blocks_traversal_and_symlink_escape(tmp_path: Path) -> None:
    safe_root = tmp_path / "safe"
    safe_root.mkdir()
    outside_root = tmp_path / "outside"
    outside_root.mkdir()

    outside_image = outside_root / "secret.png"
    outside_image.write_bytes(b"outside")

    symlink = safe_root / "secret.png"
    symlink.symlink_to(outside_image)

    markdown = "![unsafe](safe/secret.png)"
    sanitized, summaries = pdf_html.sanitize_markdown_images(
        markdown,
        allowed_image_roots=(safe_root,),
        content_root=tmp_path,
    )

    assert summaries[0].status == "placeholder"
    assert summaries[0].kind == "local"
    assert "safe/secret.png" not in sanitized
    assert sanitized.startswith("![unsafe](data:image/")
    assert summaries[0].reason in {"path not in allowed roots", "invalid filesystem path", "unsupported MIME type", "image size exceeds policy", "file not found"}


def test_sanitize_markdown_images_marks_remote_as_placeholder_and_keeps_original_url() -> None:
    markdown = "![image](https://example.com/public/image.png)"
    sanitized, summaries = pdf_html.sanitize_markdown_images(markdown, allowed_image_roots=())

    assert len(summaries) == 1
    assert summaries[0].status == "placeholder"
    assert summaries[0].kind == "remote"
    assert summaries[0].source == "https://example.com/public/image.png"
    assert "https://example.com/public/image.png" not in sanitized
    assert "![image](data:image/svg+xml" in sanitized
    encoded_svg = pdf_html.DEFAULT_PLACEHOLDER_IMAGE_DATA_URI.split(",", 1)[1]
    decoded_svg = base64.b64decode(encoded_svg).decode("utf-8")
    assert 'xmlns="http://www.w3.org/2000/svg"' in decoded_svg
    assert "Remote image unavailable" in decoded_svg


def test_forbidden_file_image_source_is_redacted_from_rendered_document() -> None:
    private_path = "/home/user/private/token.png"
    sanitized, summaries = pdf_html.sanitize_markdown_images(
        f"![private](file://{private_path})",
        allowed_image_roots=(),
    )
    output = pdf_html.build_local_html_document(
        article_id="article-1",
        title="Private image",
        url="https://spaces.ac.cn/archives/1",
        date=None,
        category=None,
        references=(),
        image_summary=summaries,
        body_html="<p>body</p>",
        katex_css="",
    )

    assert summaries[0].kind == "forbidden"
    assert private_path not in sanitized
    assert private_path not in output


def test_remote_image_summary_strips_credentials_query_and_fragment() -> None:
    source = "https://user:secret@example.com/public/image.png?token=private#fragment"
    _, summaries = pdf_html.sanitize_markdown_images(
        f"![remote]({source})",
        allowed_image_roots=(),
    )
    output = pdf_html.build_local_html_document(
        article_id="article-1",
        title="Remote image",
        url="https://spaces.ac.cn/archives/1",
        date=None,
        category=None,
        references=(),
        image_summary=summaries,
        body_html="<p>body</p>",
        katex_css="",
    )

    assert "https://example.com/public/image.png" in output
    assert "user:secret" not in output
    assert "token=private" not in output
    assert "fragment" not in output


def test_malformed_remote_image_url_becomes_redacted_placeholder() -> None:
    sanitized, summaries = pdf_html.sanitize_markdown_images(
        "![remote](https://example.com:not-a-port/image.png?token=private)",
        allowed_image_roots=(),
    )

    assert summaries[0].kind == "remote"
    assert summaries[0].status == "placeholder"
    assert summaries[0].source == ""
    assert "token=private" not in sanitized


def test_sanitize_markdown_images_escapes_math_delimiters_in_image_alt_text() -> None:
    sanitized, summaries = pdf_html.sanitize_markdown_images(
        "![range $[0,1]$](https://example.com/range.png)",
        allowed_image_roots=(),
    )

    assert summaries[0].kind == "remote"
    assert "range \\$[0,1]\\$" in sanitized
    formula_count, balanced = pdf_html.audit_markdown_math(sanitized)
    assert formula_count == 0
    assert balanced is True


def test_sanitize_markdown_images_does_not_consume_body_after_malformed_multiline_image() -> None:
    markdown = (
        "![broken image label\n\n"
        "正文公式 $x+y$ 必须保留。\n\n"
        "](https://example.com/image.png)"
    )

    sanitized, summaries = pdf_html.sanitize_markdown_images(
        markdown,
        allowed_image_roots=(),
    )

    assert summaries == ()
    assert "![broken" not in sanitized
    assert "$x+y$" in sanitized
    assert "\\$x+y\\$" not in sanitized


def test_build_local_html_document_embeds_a4_css_and_metadata_without_external_network_paths() -> None:
    body = "<p>数学内容</p>"
    output = pdf_html.build_local_html_document(
        title="测试标题",
        url="https://spaces.ac.cn/6508",
        date="2026-07-11",
        category="数学",
        references=("参考资料",),
        image_summary=(
            pdf_html.ImageSummary(
                source="assets/logo.png",
                status="inlined",
                kind="local",
                resolved_path="/tmp/logo.png",
                mime_type="image/png",
                size_bytes=12,
                reason=None,
            ),
        ),
        body_html=body,
        katex_css=".katex{color:red}",
    )

    assert "@page" in output and "size: A4" in output
    assert "default-src 'none'" in output
    assert "测试标题" in output
    assert "2026-07-11" in output
    assert "数学" in output
    assert "参考资料" in output
    assert ".katex{color:red}" in output
    assert "file://" not in output
    assert "http://" not in output
    assert "https://" not in output or "https://spaces.ac.cn/6508" in output


def test_build_local_html_document_print_css_covers_layout_rules() -> None:
    output = pdf_html.build_local_html_document(
        title="样式校验",
        url="https://spaces.ac.cn/6509",
        date="2026-07-11",
        category="测试",
        references=(),
        image_summary=(),
        body_html=(
            "<section>"
            "<h1>标题</h1>"
            "<p>正文示例</p>"
            "<pre><code>long_code_block()</code></pre>"
            "<table><tr><td>单元格内容</td></tr></table>"
            "<img src=\"data:image/png;base64,Zm9v\">"
            "<a href=\"https://example.com/a/very/very/long/url/path/that/should/wrap/in/print\">"
            "https://example.com/a/very/very/long/url/path/that/should/wrap/in/print"
            "</a><blockquote>引用</blockquote></section>"
        ),
        katex_css="",
    )

    assert "font-family" in output and "PingFang SC" in output
    assert "line-height" in output
    assert "code" in output and "pre-wrap" in output and "word-break: break-word" in output
    assert "table" in output and "max-width:100%" in output
    assert "img" in output and "max-width:100%" in output
    assert "h1" in output and "page-break-after: avoid" in output
    assert "a {" in output and "overflow-wrap: anywhere" in output
    assert "blockquote" in output and "border-left" in output


def test_build_local_html_document_displays_remote_placeholder_url_without_remote_resource() -> None:
    remote_url = "https://cdn.example.test/article/image.png"

    output = pdf_html.build_local_html_document(
        article_id="article-1",
        title="Remote image",
        url="https://spaces.ac.cn/archives/1",
        date=None,
        category=None,
        references=(),
        image_summary=(
            pdf_html.ImageSummary(
                source=remote_url,
                status="placeholder",
                kind="remote",
            ),
        ),
        body_html="<p>body</p>",
        katex_css="",
    )

    assert remote_url in output
    assert f'src="{remote_url}"' not in output
    assert f"src='{remote_url}'" not in output
    assert f'href="{remote_url}"' not in output
    assert f"href='{remote_url}'" not in output
    assert "Article ID" in output and "article-1" in output


def test_sanitize_markdown_images_supports_title_angle_bracket_and_parenthesized_urls(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()

    for path in [assets / "photo(1).png", assets / "logo.png", assets / "diagram(2).png"]:
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)

    markdown = (
        "![has-title](assets/logo.png \"带标题\")\n"
        "![angle](<assets/diagram(2).png>)\n"
        "![paren](assets/photo(1).png)\n"
        "![remote](https://example.com/远程图片.png \"远程\")"
    )

    sanitized, summaries = pdf_html.sanitize_markdown_images(
        markdown,
        allowed_image_roots=(assets,),
        content_root=tmp_path,
    )

    assert len(summaries) == 4
    assert [item.kind for item in summaries][:3] == ["local", "local", "local"]
    assert [item.status for item in summaries][:3] == ["inlined", "inlined", "inlined"]
    assert summaries[3].kind == "remote"
    assert summaries[3].status == "placeholder"
    assert "https://example.com" not in sanitized
    assert sanitized.count("![") == 4
    assert sanitized.count("data:image/png") == 3
    assert sanitized.count("data:image/svg+xml") == 1


def test_sanitize_markdown_images_abs_path_stays_out_of_html_body_and_template(tmp_path: Path) -> None:
    image_path = tmp_path / "absolute.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)

    markdown = f"![abs]({image_path})"
    sanitized, summaries = pdf_html.sanitize_markdown_images(
        markdown,
        allowed_image_roots=(tmp_path,),
        content_root=tmp_path,
    )

    assert summaries and summaries[0].status == "inlined"
    assert summaries[0].kind == "local"
    assert str(image_path) not in sanitized

    output = pdf_html.build_local_html_document(
        title="abs path",
        url="https://spaces.ac.cn/6509",
        date="2026-07-11",
        category=None,
        references=(),
        image_summary=summaries,
        body_html="<p>abs</p>",
        katex_css="",
        article_id="article-abs",
    )

    assert str(image_path) not in output
    assert summaries[0].resolved_path is not None
    assert summaries[0].resolved_path not in output
def test_node_markdown_renderer_uses_single_persistent_process(monkeypatch, tmp_path: Path) -> None:
    class FakeStdin:
        def __init__(self) -> None:
            self.owner: "FakeNodeProcess"

        def write(self, value: str) -> int:  # pragma: no cover - interface match
            payload = json.loads(value)
            response = json.dumps({"request_id": payload["request_id"], "status": "ok", "html": "<p>ok</p>"})
            self.owner._responses.append(response + "\n")
            return len(value)

        def flush(self) -> None:
            return None

    class FakeStdout:
        def __init__(self) -> None:
            self.owner: "FakeNodeProcess"

        def readline(self) -> str:  # pragma: no cover - interface match
            return self.owner._responses.pop(0)

    class FakeNodeProcess:
        calls = 0

        def __init__(self) -> None:
            FakeNodeProcess.calls += 1
            self.stdin = FakeStdin()
            self.stdout = FakeStdout()
            self.stdin.owner = self
            self.stdout.owner = self
            self._responses: list[str] = []
            self.terminated = False

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            self.terminated = True

        def wait(self, timeout: float | None = None) -> int:  # noqa: ARG002
            return 0

        def kill(self) -> None:
            self.terminated = True

    def fake_popen(*_args: object, **_kwargs: object) -> FakeNodeProcess:
        return FakeNodeProcess()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    renderer = pdf_html.NodeMarkdownRenderer(
        render_script_path=tmp_path / "renderer.mjs",
        frontend_node_modules_path=tmp_path,
    )
    renderer._katex_css = ""

    first = renderer.render_article(
        title="t1",
        url="u1",
        markdown="a",
        date=None,
        category="",
        references=(),
    )
    second = renderer.render_article(
        title="t2",
        url="u2",
        markdown="b",
        date=None,
        category="",
        references=(),
    )

    assert first.html.startswith("<!doctype html>")
    assert "render-markdown" not in first.html
    assert FakeNodeProcess.calls == 1
    assert first.metrics.rendered_body_chars == len("<p>ok</p>")
    assert second.metrics.rendered_body_chars == len("<p>ok</p>")
    assert second.image_summary == ()

    renderer.close()


def test_node_markdown_renderer_times_out_and_restarts_child(tmp_path: Path) -> None:
    script = tmp_path / "renderer.py"
    script.write_text(
        "import json, sys, time\n"
        "for line in sys.stdin:\n"
        "    request = json.loads(line)\n"
        "    if request['markdown'] == 'slow':\n"
        "        time.sleep(2)\n"
        "    print(json.dumps({'request_id': request['request_id'], 'status': 'ok', 'html': '<p>fast body</p>'}), flush=True)\n",
        encoding="utf-8",
    )
    renderer = pdf_html.NodeMarkdownRenderer(
        render_script_path=script,
        frontend_node_modules_path=tmp_path,
        node_binary=sys.executable,
        response_timeout_seconds=0.05,
    )
    renderer._katex_css = ""

    started = time.monotonic()
    with pytest.raises(pdf_html.NodeRenderError, match="timed out"):
        renderer.render_article(title="Slow", url="u", markdown="slow")
    assert time.monotonic() - started < 1

    result = renderer.render_article(title="Fast", url="u", markdown="fast")
    assert result.body_html == "<p>fast body</p>"
    renderer.close()


def test_html_render_result_contains_body_derived_text_probes(monkeypatch, tmp_path: Path) -> None:
    renderer = pdf_html.NodeMarkdownRenderer(
        render_script_path=tmp_path / "renderer.mjs",
        frontend_node_modules_path=tmp_path,
    )
    renderer._katex_css = ""
    monkeypatch.setattr(
        renderer,
        "_render_markdown_with_node",
        lambda _markdown: "<h2>正文标题</h2><p>这是正文唯一内容标记 alpha beta gamma。</p>",
    )

    result = renderer.render_article(title="Probe", url="u", markdown="source")

    assert result.body_text_probes
    assert any("正文" in probe for probe in result.body_text_probes)


def test_formula_metrics_report_rendered_and_failed_math(monkeypatch, tmp_path: Path) -> None:
    renderer = pdf_html.NodeMarkdownRenderer(
        render_script_path=tmp_path / "renderer.mjs",
        frontend_node_modules_path=tmp_path,
    )
    renderer._katex_css = ""
    monkeypatch.setattr(
        renderer,
        "_render_markdown_with_node",
        lambda _markdown: '<p><span class="katex">ok</span><span class="katex-error">bad</span></p>',
    )

    result = renderer.render_article(
        article_id="article-1",
        title="Math",
        url="https://spaces.ac.cn/archives/1",
        markdown="$x$ and $y$",
    )

    assert result.metrics.expected_formula_count == 2
    assert result.metrics.formula_count == 1
    assert result.metrics.formula_render_failure_count == 1
    assert result.metrics.delimiter_balanced is True


def test_formula_metrics_detect_unrendered_raw_formula_but_ignore_code(monkeypatch, tmp_path: Path) -> None:
    renderer = pdf_html.NodeMarkdownRenderer(
        render_script_path=tmp_path / "renderer.mjs",
        frontend_node_modules_path=tmp_path,
    )
    renderer._katex_css = ""
    monkeypatch.setattr(
        renderer,
        "_render_markdown_with_node",
        lambda _markdown: "<p>$x$</p><pre><code>$not-math$</code></pre>",
    )

    result = renderer.render_article(
        article_id="article-raw",
        title="Raw",
        url="https://spaces.ac.cn/archives/3",
        markdown="$x$",
    )

    assert result.metrics.formula_count == 0
    assert result.metrics.formula_render_failure_count == 1


def test_formula_metrics_ignore_literal_dollar_delimiters_when_input_has_no_formula(
    monkeypatch,
    tmp_path: Path,
) -> None:
    renderer = pdf_html.NodeMarkdownRenderer(
        render_script_path=tmp_path / "renderer.mjs",
        frontend_node_modules_path=tmp_path,
    )
    monkeypatch.setattr(
        renderer,
        "_render_markdown_with_node",
        lambda _markdown: '<p>Split(Ts, "|$|")(1), then Split(Ts, "|$|")(0)</p>',
    )

    result = renderer.render_article(
        article_id="literal-dollar",
        title="Literal",
        url="https://spaces.ac.cn/archives/31",
        markdown='Split(Ts, "|\\$|")',
    )

    assert result.metrics.expected_formula_count == 0
    assert result.metrics.formula_render_failure_count == 0


def test_plain_markdown_does_not_load_or_embed_katex_assets(monkeypatch, tmp_path: Path) -> None:
    renderer = pdf_html.NodeMarkdownRenderer(
        render_script_path=tmp_path / "renderer.mjs",
        frontend_node_modules_path=tmp_path,
    )
    monkeypatch.setattr(renderer, "_render_markdown_with_node", lambda _markdown: "<p>plain text</p>")
    monkeypatch.setattr(
        renderer,
        "_load_katex_css",
        lambda: (_ for _ in ()).throw(AssertionError("KaTeX CSS should not load")),
    )

    result = renderer.render_article(
        article_id="plain-1",
        title="Plain",
        url="https://spaces.ac.cn/archives/2",
        markdown="No formula here.",
    )

    assert result.metrics.expected_formula_count == 0
    assert result.metrics.katex_css_length == 0
    assert "data:font/" not in result.html


@pytest.mark.skipif(
    not pdf_html.has_node_binary() or not pdf_html.has_frontend_node_modules(),
    reason="local node renderer is unavailable",
)
def test_node_render_supports_chinese_gfm_math_and_skips_raw_html() -> None:
    renderer = pdf_html.NodeMarkdownRenderer()

    try:
        result = renderer.render_article(
            article_id="article-6508",
            title="本地数学文章",
            url="https://spaces.ac.cn/6508",
            markdown=(
                "# 题目\n\n"
                "中文说明与公式：$a+b=c$ 与 $$E=mc^2$$。\n\n"
                "| h1 | h2 |\n|---|---|\n|1|2|\n"
                "<iframe src=\"https://example.com/frame\"></iframe>\n\n"
                "![remote](https://example.com/image.png)"
            ),
            date="2026-01-01",
            category="数学",
            references=(
                {
                    "title": "paper",
                    "url": "https://example.com/ref",
                },
            ),
            allowed_image_roots=(Path(".").resolve(),),
            content_root=Path(".").resolve(),
        )

        assert "<table" in result.html
        assert "katex" in result.html.lower()
        assert "<iframe" not in result.html
        assert "default-src 'none'" in result.html
        assert "class=\"reader-markdown\"" not in result.html
        assert "https://example.com/image.png" in result.html
        assert 'src="https://example.com/image.png"' not in result.html
        assert 'src="data:image/svg+xml;base64,' in result.body_html
        assert "https://example.com/frame" not in result.html
        assert result.metrics.formula_count == 2
        assert result.metrics.formula_render_failure_count == 0
        assert result.metrics.delimiter_balanced is True
    finally:
        renderer.close()


@pytest.mark.skipif(
    not pdf_html.has_node_binary() or not pdf_html.has_frontend_node_modules(),
    reason="local node renderer is unavailable",
)
def test_node_render_does_not_trust_katex_file_link_commands() -> None:
    with pdf_html.NodeMarkdownRenderer() as renderer:
        result = renderer.render_article(
            article_id="unsafe-link",
            title="Unsafe formula link",
            url="https://spaces.ac.cn/archives/1",
            markdown=r"$\href{file:///home/user/private.txt}{secret}$",
        )

    assert 'href="file:' not in result.body_html
    assert "file:///home/user/private.txt" not in result.body_html


@pytest.mark.skipif(
    not pdf_html.has_node_binary() or not pdf_html.has_frontend_node_modules(),
    reason="local node renderer is unavailable",
)
def test_node_render_supports_normalized_legacy_mathjax_formulas() -> None:
    markdown = (
        "$$\\style{border:1px solid #123456}{x}$$\n\n"
        "$$\\newcommand{\\argmin}{\\mathop{\\text{argmin}}}\\argmin_x x$$\n\n"
        "$$\\mathop{argmin}_\\boldsymbol{B} x$$\n\n"
        "$$\\clip\\nolimits_{[0,1]}(x)$$\n\n"
        "$$\\begin{eqnarray*}a&=&b\\\\c&=&d\\end{eqnarray*}$$\n\n"
        "$$\\begin{array}{\\cdot {20}{c}}a\\\\b\\end{array}$$\n\n"
        "$$\\text{head_dims} \\textbf{61.15%}$$\n\n"
        "$$\\begin{aligned}a&=b\\tag{1}\\\\c&=d\\tag{2}\\end{aligned}$$"
    )

    with pdf_html.NodeMarkdownRenderer() as renderer:
        result = renderer.render_article(
            article_id="legacy-math",
            title="Legacy math",
            url="https://spaces.ac.cn/archives/4",
            markdown=markdown,
        )

    assert result.metrics.expected_formula_count == 8
    assert result.metrics.formula_count == 8
    assert result.metrics.formula_render_failure_count == 0
    assert result.metrics.delimiter_balanced is True
    assert "katex-error" not in result.body_html
