from __future__ import annotations

import base64
import html
import json
import mimetypes
import os
import re
import selectors
import subprocess
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FRONTEND_NODE_MODULES = REPO_ROOT / "frontend" / "node_modules"
DEFAULT_RENDER_SCRIPT = REPO_ROOT / "scripts" / "export" / "render_local_pdf_html.mjs"
DEFAULT_MAX_LOCAL_IMAGE_BYTES = 2 * 1024 * 1024
_PLACEHOLDER_IMAGE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="96" viewBox="0 0 720 96">'
    '<rect width="720" height="96" fill="#f3f4f6" stroke="#c7cbd1"/>'
    '<text x="24" y="55" fill="#555b66" font-family="sans-serif" font-size="18">'
    "Remote image unavailable in offline export"
    "</text></svg>"
)
DEFAULT_PLACEHOLDER_IMAGE_DATA_URI = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(_PLACEHOLDER_IMAGE_SVG.encode("utf-8")).decode("ascii")
)

ALLOWED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/bmp",
}
FONT_MIME_TYPES = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
    ".otf": "font/otf",
}

_CODE_SEGMENT_PATTERN = re.compile(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)")
_IMAGE_MARKDOWN_PATTERN = re.compile(r"!\[")
_FONT_URL_PATTERN = re.compile(r"url\((['\"]?)([^'\")]+)\1\)")
_NEWCOMMAND_INLINE_PATTERN = re.compile(r"(\\newcommand\{([A-Za-z][A-Za-z0-9]*)\}[^\n$]*?\\\2)\$\1\$")
_NEWCOMMAND_PATTERN = re.compile(r"\\newcommand\{([A-Za-z][A-Za-z0-9]*)\}")
_DISPLAY_MATH_QUOTE_PATTERN = re.compile(r"\$\$([\s\S]*?)\$\$")
_DISPLAY_MATH_ESCAPED_PATTERN = re.compile(r"(?<!\\)\\\[([\s\S]*?)(?<!\\)\\\]")
_INLINE_MATH_ESCAPED_OPEN = re.compile(r"(?<!\\)\\\(")
_INLINE_MATH_ESCAPED_CLOSE = re.compile(r"(?<!\\)\\\)")
_TEXT_COMMAND_PATTERN = re.compile(
    r"\\(text|textbf|textit|textrm|texttt|operatorname)\{([^{}]*)\}"
)
_UNTRUSTED_TEX_HREF_PATTERN = re.compile(
    r"\\href\s*\{[^{}]*\}\s*\{([^{}]*)\}",
    re.IGNORECASE,
)
_UNTRUSTED_TEX_URL_PATTERN = re.compile(r"\\url\s*\{[^{}]*\}", re.IGNORECASE)
_UNTRUSTED_TEX_IMAGE_PATTERN = re.compile(
    r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{[^{}]*\}",
    re.IGNORECASE,
)
_FILE_URI_PATTERN = re.compile(r"file:(?://)?[^\s{}$]+", re.IGNORECASE)
_CODE_HTML_PATTERN = re.compile(
    r"<(?:pre|code)\b[^>]*>[\s\S]*?</(?:pre|code)>",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ImageSummary:
    source: str
    status: str
    kind: str
    resolved_path: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class HtmlRenderMetrics:
    markdown_input_chars: int
    sanitized_markdown_chars: int
    rendered_body_chars: int
    output_html_chars: int
    image_count: int
    local_images_inlined: int
    remote_images_replaced: int
    images_placeholder: int
    render_duration_ms: float
    katex_css_length: int
    expected_formula_count: int
    formula_count: int
    formula_render_failure_count: int
    delimiter_balanced: bool


@dataclass(frozen=True)
class HtmlRenderResult:
    title: str
    url: str
    date: str | None
    category: str | None
    reference_count: int
    references: tuple[str, ...]
    image_summary: tuple[ImageSummary, ...]
    html: str
    body_html: str
    body_text_probes: tuple[str, ...]
    metrics: HtmlRenderMetrics


class NodeRenderError(RuntimeError):
    pass


def _readline_with_timeout(stream: Any, timeout_seconds: float) -> str:
    try:
        stream.fileno()
    except (AttributeError, OSError):
        return stream.readline()

    selector = selectors.DefaultSelector()
    try:
        selector.register(stream, selectors.EVENT_READ)
        if not selector.select(timeout_seconds):
            raise TimeoutError("stream read timed out")
        return stream.readline()
    finally:
        selector.close()


def _normalize_text_probe(value: str) -> str:
    return "".join(character.casefold() for character in value if character.isalnum())


def _build_body_text_probes(body_html: str) -> tuple[str, ...]:
    soup = BeautifulSoup(body_html or "", "html.parser")
    for node in soup.select("script, style, math, .katex"):
        node.decompose()
    normalized = _normalize_text_probe(soup.get_text(" ", strip=True))
    if not normalized:
        fallback = BeautifulSoup(body_html or "", "html.parser").get_text(" ", strip=True)
        normalized = _normalize_text_probe(fallback)
    if not normalized:
        return ()

    probe_length = min(20, len(normalized))
    offsets = (0, max((len(normalized) - probe_length) // 2, 0), max(len(normalized) - probe_length, 0))
    probes: list[str] = []
    for offset in offsets:
        probe = normalized[offset : offset + probe_length]
        if probe and probe not in probes:
            probes.append(probe)
    return tuple(probes)


def has_frontend_node_modules(node_modules_path: Path = DEFAULT_FRONTEND_NODE_MODULES) -> bool:
    return node_modules_path.is_dir() and (node_modules_path / "react").is_dir()


def has_node_binary() -> bool:
    from shutil import which

    return which("node") is not None


def prepare_markdown_for_math(content: str) -> str:
    """Normalize markdown math for remark-math compatibility with ArticleDetailView behavior."""

    normalized_chunks: list[str] = []
    for index, segment in enumerate(_CODE_SEGMENT_PATTERN.split(content or "")):
        if index % 2 == 1:
            normalized_chunks.append(segment)
            continue

        text = _NEWCOMMAND_INLINE_PATTERN.sub(
            lambda match: f"${_normalize_newcommand(match.group(1))}$", segment
        )
        text = _NEWCOMMAND_PATTERN.sub(lambda match: f"\\newcommand{{\\{match.group(1)}}}", text)
        text = _normalize_inline_math_boundaries(text)
        text = _DISPLAY_MATH_QUOTE_PATTERN.sub(
            lambda match: f"\n\n$$\n{match.group(1).strip()}\n$$\n\n", text
        )
        text = _DISPLAY_MATH_ESCAPED_PATTERN.sub(
            lambda match: f"\n\n$$\n{match.group(1).strip()}\n$$\n\n", text
        )
        text = _INLINE_MATH_ESCAPED_OPEN.sub("$", text)
        text = _INLINE_MATH_ESCAPED_CLOSE.sub("$", text)
        text = _normalize_latex_for_katex(text)
        normalized_chunks.append(text)

    return "".join(normalized_chunks)


def audit_markdown_math(content: str) -> tuple[int, bool]:
    segments = _CODE_SEGMENT_PATTERN.split(content or "")
    prose = "".join(segment for index, segment in enumerate(segments) if index % 2 == 0)
    display_matches = list(_DISPLAY_MATH_QUOTE_PATTERN.finditer(prose))
    without_display = _DISPLAY_MATH_QUOTE_PATTERN.sub("", prose)
    inline_matches = re.findall(r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$(?!\$)", without_display, re.DOTALL)
    unescaped_markers = len(re.findall(r"(?<!\\)\$", prose))
    balanced = unescaped_markers % 2 == 0
    return len(display_matches) + len(inline_matches), balanced


def _normalize_newcommand(formula: str) -> str:
    return _NEWCOMMAND_PATTERN.sub(lambda match: f"\\newcommand{{\\{match.group(1)}}}", formula)


def _is_escaped(value: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and value[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def _find_next_single_dollar(value: str, start: int) -> int | None:
    cursor = start
    while cursor < len(value):
        if value[cursor] != "$" or _is_escaped(value, cursor):
            cursor += 1
            continue
        if (cursor > 0 and value[cursor - 1] == "$") or (
            cursor + 1 < len(value) and value[cursor + 1] == "$"
        ):
            cursor += 1
            continue
        return cursor
    return None


def _normalize_inline_math_boundaries(value: str) -> str:
    result: list[str] = []
    cursor = 0
    search = 0
    while search < len(value):
        opening = _find_next_single_dollar(value, search)
        if opening is None:
            break
        closing = _find_next_single_dollar(value, opening + 1)
        if closing is None:
            break
        result.append(value[cursor:opening])
        formula = value[opening + 1 : closing]
        if re.search(r"\n\s*\n", formula):
            result.append("\n\n$$\n" + formula.strip() + "\n$$\n\n")
        else:
            before = value[opening - 1] if opening else ""
            after = value[closing + 1] if closing + 1 < len(value) else ""
            prefix = " " if before.isdigit() or before in "})]" else ""
            suffix = " " if after.isdigit() else ""
            result.append(prefix + "$" + formula + "$" + suffix)
        cursor = closing + 1
        search = closing + 1
    result.append(value[cursor:])
    return "".join(result)


def _normalize_latex_for_katex(value: str) -> str:
    normalized = _UNTRUSTED_TEX_HREF_PATTERN.sub(lambda match: match.group(1), value)
    normalized = _UNTRUSTED_TEX_URL_PATTERN.sub(r"\\text{[link removed]}", normalized)
    normalized = _UNTRUSTED_TEX_IMAGE_PATTERN.sub(r"\\text{[image removed]}", normalized)
    normalized = _FILE_URI_PATTERN.sub("[local-path-redacted]", normalized)
    normalized = re.sub(r"\\style(?=\{)", r"\\htmlStyle", normalized)
    normalized = re.sub(
        r"\\newcommand\{([A-Za-z][A-Za-z0-9]*)\}",
        lambda match: f"\\newcommand{{\\{match.group(1)}}}",
        normalized,
    )
    normalized = re.sub(r"\\newcommand(?=\s*\{)", r"\\providecommand", normalized)
    normalized = re.sub(
        r"([_^])(\\(?:boldsymbol|mathbf|mathrm|mathcal|mathbb)\{[^{}]+\})",
        lambda match: f"{match.group(1)}{{{match.group(2)}}}",
        normalized,
    )
    normalized = normalized.replace(
        r"\clip\nolimits",
        r"\mathop{\mathrm{clip}}\nolimits",
    )
    normalized = re.sub(
        r"\\begin\{eqnarray(?:\*|\\\*)?\}",
        r"\\begin{aligned}",
        normalized,
    )
    normalized = re.sub(
        r"\\end\{eqnarray(?:\*|\\\*)?\}",
        r"\\end{aligned}",
        normalized,
    )
    normalized = re.sub(
        r"\\begin\{array\}\{\\cdot\s*\{\d+\}\{([clr]+)\}\}",
        lambda match: f"\\begin{{array}}{{{match.group(1)}}}",
        normalized,
    )

    def escape_text_literal(match: re.Match[str]) -> str:
        content = re.sub(
            r"(?<!\\)([_%])",
            lambda token: f"\\{token.group(1)}",
            match.group(2),
        )
        return f"\\{match.group(1)}{{{content}}}"

    normalized = _TEXT_COMMAND_PATTERN.sub(escape_text_literal, normalized)
    normalized = re.sub(
        r"\\tag\{([^{}]*)\}",
        lambda match: f"\\quad\\text{{({match.group(1)})}}",
        normalized,
    )
    return normalized


def _count_unrendered_formula_markers(body_html: str) -> int:
    without_code = _CODE_HTML_PATTERN.sub("", body_html)
    visible_text = html.unescape(re.sub(r"<[^>]+>", "", without_code))
    display_matches = list(_DISPLAY_MATH_QUOTE_PATTERN.finditer(visible_text))
    without_display = _DISPLAY_MATH_QUOTE_PATTERN.sub("", visible_text)
    inline_matches = re.findall(
        r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$(?!\$)",
        without_display,
        re.DOTALL,
    )
    escaped_display = re.findall(
        r"(?<!\\)\\\[([\s\S]*?)(?<!\\)\\\]",
        visible_text,
    )
    escaped_inline = re.findall(
        r"(?<!\\)\\\(([\s\S]*?)(?<!\\)\\\)",
        visible_text,
    )
    return len(display_matches) + len(inline_matches) + len(escaped_display) + len(escaped_inline)


def _extract_image_source(raw_token: str) -> str:
    token = raw_token.strip()
    if token.startswith("<"):
        end = token.find(">")
        if end > 0:
            return token[1:end].strip()

    if token.startswith(("\"", "'")):
        quote = token[0]
        end = token.find(quote, 1)
        if end > 0:
            return token[1:end].strip()

    source_chars: list[str] = []
    quote: str | None = None
    paren_depth = 0
    escaped = False

    for char in token:
        if escaped:
            source_chars.append(char)
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if quote:
            if char == quote:
                quote = None
                continue
            source_chars.append(char)
            continue

        if char in ("'", '"'):
            quote = char
            continue

        if char == "(":
            paren_depth += 1
            source_chars.append(char)
            continue

        if char == ")" and paren_depth > 0:
            paren_depth -= 1
            source_chars.append(char)
            continue

        if char.isspace() and paren_depth == 0:
            break

        source_chars.append(char)

    return "".join(source_chars).strip()


def _is_remote_or_forbidden_source(source: str) -> bool:
    if source.startswith(("http://", "https://", "file:", "//")):
        return True

    parsed = urllib.parse.urlparse(source)
    if not parsed.scheme:
        return False

    if len(parsed.scheme) == 1 and parsed.scheme.isalpha():
        windows_path_prefix = f"{parsed.scheme}:\\"
        posix_path_prefix = f"{parsed.scheme}:/"
        if source.startswith(windows_path_prefix) or source.startswith(posix_path_prefix):
            return False

    return True


def _public_remote_image_url(source: str) -> str:
    candidate = f"https:{source}" if source.startswith("//") else source
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        port = parsed.port
    except ValueError:
        return ""
    if port is not None:
        host = f"{host}:{port}"
    return urllib.parse.urlunsplit((parsed.scheme.lower(), host, parsed.path, "", ""))


def _find_matching_paren(source: str, open_index: int) -> int | None:
    if open_index >= len(source) or source[open_index] != "(":
        return None

    depth = 0
    quote: str | None = None
    escaped = False

    for index, char in enumerate(source[open_index:], start=open_index):
        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if quote:
            if char == quote:
                quote = None
            continue

        if char in ("'", '"'):
            quote = char
            continue

        if char == "(":
            depth += 1
            continue

        if char == ")":
            depth -= 1
            if depth == 0:
                return index

    return None


def _find_markdown_image_token(markdown: str, start: int) -> tuple[str, str, int] | None:
    if start < 0 or start + 2 >= len(markdown) or not markdown.startswith("![", start):
        return None

    alt_end = markdown.find("](", start + 2)
    if alt_end < 0:
        return None
    if "\n" in markdown[start:alt_end]:
        return None

    close_paren = _find_matching_paren(markdown, alt_end + 1)
    if close_paren is None:
        return None
    if "\n" in markdown[alt_end:close_paren]:
        return None

    alt_text = markdown[start + 2 : alt_end]
    source = markdown[alt_end + 2 : close_paren]
    return alt_text, source, close_paren + 1


def sanitize_markdown_images(
    markdown: str,
    *,
    allowed_image_roots: Sequence[Path],
    content_root: Path | None = None,
    max_local_image_size_bytes: int = DEFAULT_MAX_LOCAL_IMAGE_BYTES,
    allowed_mime_types: set[str] = ALLOWED_IMAGE_MIME_TYPES,
) -> tuple[str, tuple[ImageSummary, ...]]:
    if not markdown:
        return "", ()

    resolved_roots = tuple(Path(root).resolve() for root in allowed_image_roots)

    summaries: list[ImageSummary] = []
    result_parts: list[str] = []
    cursor = 0

    while cursor < len(markdown):
        match = _IMAGE_MARKDOWN_PATTERN.search(markdown, cursor)
        if match is None:
            result_parts.append(markdown[cursor:])
            break

        image_start = match.start()
        result_parts.append(markdown[cursor:image_start])

        token = _find_markdown_image_token(markdown, image_start)
        if token is None:
            result_parts.append("[image:")
            cursor = image_start + 2
            continue

        alt_text, raw_source, next_cursor = token
        alt_text = re.sub(r"(?<!\\)\$", r"\\$", alt_text)
        source_token = _extract_image_source(raw_source)
        replacement, summary = _sanitize_single_image(
            source_token,
            allowed_roots=resolved_roots,
            content_root=content_root,
            max_local_image_size_bytes=max_local_image_size_bytes,
            allowed_mime_types=allowed_mime_types,
            original_source=source_token,
        )
        summaries.append(summary)
        result_parts.append(f"![{alt_text}]({replacement})")
        cursor = next_cursor

    sanitized = "".join(result_parts)
    return sanitized, tuple(summaries)


def _sanitize_single_image(
    source: str,
    *,
    allowed_roots: tuple[Path, ...],
    content_root: Path | None,
    max_local_image_size_bytes: int,
    allowed_mime_types: set[str],
    original_source: str,
) -> tuple[str, ImageSummary]:
    if not source:
        return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
            source=original_source,
            status="placeholder",
            kind="invalid",
            reason="empty image source",
        )

    if source.startswith("data:"):
        header, separator, payload = source.partition(",")
        mime_match = re.fullmatch(r"data:([^;,]+);base64", header, re.IGNORECASE)
        if not separator or mime_match is None or mime_match.group(1).lower() not in allowed_mime_types:
            return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
                source=original_source,
                status="placeholder",
                kind="data-uri",
                reason="unsupported data image",
            )
        try:
            decoded = base64.b64decode(payload, validate=True)
        except (ValueError, TypeError):
            return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
                source=original_source,
                status="placeholder",
                kind="data-uri",
                reason="invalid data image",
            )
        if not decoded or len(decoded) > max_local_image_size_bytes:
            return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
                source=original_source,
                status="placeholder",
                kind="data-uri",
                size_bytes=len(decoded),
                reason="data image size exceeds policy",
            )
        return source, ImageSummary(
            source=original_source,
            status="inlined",
            kind="data-uri",
            mime_type=mime_match.group(1).lower(),
            size_bytes=len(decoded),
        )

    if source.lower().startswith(("http://", "https://", "//")):
        return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
            source=_public_remote_image_url(original_source),
            status="placeholder",
            kind="remote",
        )

    if _is_remote_or_forbidden_source(source):
        return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
            source="",
            status="placeholder",
            kind="forbidden",
            reason="forbidden image source scheme",
        )

    if not allowed_roots:
        return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
            source=original_source,
            status="placeholder",
            kind="local",
            reason="local images disabled",
        )

    candidate = Path(urllib.parse.unquote(source))
    if not candidate.is_absolute():
        base = content_root or Path.cwd()
        candidate = (base / candidate)

    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError):
        return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
            source=original_source,
            status="placeholder",
            kind="local",
            reason="invalid filesystem path",
        )

    if allowed_roots and not any(resolved.is_relative_to(root) for root in allowed_roots):
        return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
            source=original_source,
            status="placeholder",
            kind="local",
            resolved_path=str(resolved),
            reason="path not in allowed roots",
        )

    if not resolved.exists() or not resolved.is_file():
        return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
            source=original_source,
            status="placeholder",
            kind="local",
            resolved_path=str(resolved),
            reason="file not found",
        )

    size_bytes = resolved.stat().st_size
    if size_bytes <= 0 or size_bytes > max_local_image_size_bytes:
        return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
            source=original_source,
            status="placeholder",
            kind="local",
            resolved_path=str(resolved),
            size_bytes=size_bytes,
            reason="image size exceeds policy",
        )

    mime_type, _ = mimetypes.guess_type(str(resolved))
    if not mime_type or mime_type not in allowed_mime_types:
        return DEFAULT_PLACEHOLDER_IMAGE_DATA_URI, ImageSummary(
            source=original_source,
            status="placeholder",
            kind="local",
            resolved_path=str(resolved),
            size_bytes=size_bytes,
            reason="unsupported MIME type",
        )

    data_uri = f"data:{mime_type};base64,{base64.b64encode(resolved.read_bytes()).decode()}"
    return data_uri, ImageSummary(
        source=original_source,
        status="inlined",
        kind="local",
        resolved_path=str(resolved),
        mime_type=mime_type,
        size_bytes=size_bytes,
    )


def _font_data_uri(font_path: Path) -> str:
    mime_type = FONT_MIME_TYPES.get(font_path.suffix.lower(), "font/unknown")
    return f"data:{mime_type};base64,{base64.b64encode(font_path.read_bytes()).decode()}"


def _inline_katex_fonts(css: str, frontend_node_modules: Path) -> str:
    font_dir = frontend_node_modules / "katex" / "dist" / "fonts"

    def _rewrite_font(match: re.Match[str]) -> str:
        relative = match.group(2)
        if relative.startswith("data:"):
            return match.group(0)
        font_path = font_dir / relative
        if not font_path.exists() or not font_path.is_file():
            return match.group(0)
        return f"url('{_font_data_uri(font_path)}')"

    return _FONT_URL_PATTERN.sub(_rewrite_font, css)


def _load_katex_css(frontend_node_modules: Path = DEFAULT_FRONTEND_NODE_MODULES) -> str:
    css_candidates = [
        frontend_node_modules / "katex" / "dist" / "katex.min.css",
        frontend_node_modules / "katex" / "dist" / "katex.css",
    ]
    css_path = next((path for path in css_candidates if path.is_file()), None)
    if css_path is None:
        raise FileNotFoundError("KaTeX stylesheet not found in frontend node_modules")

    css = css_path.read_text(encoding="utf-8")
    return _inline_katex_fonts(css, frontend_node_modules)


def build_local_html_document(
    *,
    title: str,
    url: str,
    date: str | None,
    category: str | None,
    references: Sequence[str],
    image_summary: Sequence[ImageSummary],
    body_html: str,
    katex_css: str,
    article_id: str = "",
) -> str:
    escaped_title = html.escape(title or "")
    escaped_url = html.escape(url or "")
    escaped_date = html.escape(date or "")
    escaped_category = html.escape(category or "")
    reference_rows = [f"<li>{html.escape(item)}</li>" for item in references]
    reference_section = (
        "<section><h2>References</h2><ol>" + "".join(reference_rows) + "</ol></section>"
        if reference_rows
        else "<section><h2>References</h2><p>None</p></section>"
    )

    image_rows = []
    for item in image_summary:
        description = f"{html.escape(item.kind)} image: {html.escape(item.status)}"
        if item.kind == "remote" and item.source:
            description += f" - <code>{html.escape(item.source)}</code>"
        image_rows.append(f"<li>{description}</li>")
    image_section = (
        "<section><h2>Image summary</h2><ol>" + "".join(image_rows) + "</ol></section>"
        if image_rows
        else "<section><h2>Image summary</h2><p>None</p></section>"
    )

    return (
        "<!doctype html>"
        "<html lang=\"en\">"
        "<head>"
        "<meta charset=\"utf-8\">"
        "<meta http-equiv=\"Content-Security-Policy\" "
        "content=\"default-src 'none'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "font-src data:; script-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'\">"
        f"<title>{escaped_title}</title>"
        "<style>\n"
        "@page { size: A4; margin: 12mm 10mm; }\n"
        "html,body { margin: 0; padding: 0; }\n"
        "body {"
        "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei',"
        " 'Hiragino Sans GB', 'Noto Sans CJK SC', Arial, sans-serif;"
        "color: #111; line-height: 1.7; }\n"
        "code, pre { overflow-wrap: anywhere; word-break: break-word; }\n"
        "pre { white-space: pre-wrap; }\n"
        "table { width: 100%; border-collapse: collapse; table-layout: fixed; word-break: break-word; }\n"
        "th, td { overflow-wrap: anywhere; word-break: break-word; }\n"
        "img { max-width: 100%; height: auto; }\n"
        "h1, h2, h3, h4, h5, h6 { page-break-after: avoid; page-break-inside: avoid; break-inside: avoid; }\n"
        "a { color: #0366d6; overflow-wrap: anywhere; word-break: break-word; }\n"
        "blockquote { margin: 0.8rem 0; padding: 0.2rem 0.8rem; border-left: 4px solid #ddd;"
        " color: #555; background: #f8f9fb; }\n"
        ".meta{display:grid;grid-template-columns:auto 1fr;row-gap:4px;column-gap:8px;max-width:100%;font-size:12px;}\n"
        ".meta dt{color:#444;font-weight:600;}\n"
        "main { margin-top: 10px; }\n"
        ".section{margin-top:12px; padding-top:8px; border-top:1px solid #ddd;}\n"
        "</style>\n"
        f"<style>{katex_css}</style>"
        "</head>"
        "<body>"
        "<main>"
        "<h1>" + escaped_title + "</h1>"
        "<dl class='meta'>"
        "<dt>Article ID</dt><dd>" + html.escape(article_id) + "</dd>"
        "<dt>URL</dt><dd>" + escaped_url + "</dd>"
        "<dt>Date</dt><dd>" + escaped_date + "</dd>"
        "<dt>Category</dt><dd>" + escaped_category + "</dd>"
        "</dl>"
        "<section class='section'>" + body_html + "</section>"
        + reference_section
        + image_section
        + "</main>"
        "</body></html>"
    )


class NodeMarkdownRenderer:
    def __init__(
        self,
        *,
        render_script_path: Path | None = None,
        frontend_node_modules_path: Path | None = None,
        node_binary: str = "node",
        response_timeout_seconds: float = 30.0,
    ) -> None:
        self.render_script_path = Path(render_script_path or DEFAULT_RENDER_SCRIPT)
        self.frontend_node_modules_path = Path(frontend_node_modules_path or DEFAULT_FRONTEND_NODE_MODULES)
        self.node_binary = node_binary
        if response_timeout_seconds <= 0:
            raise ValueError("response_timeout_seconds must be positive")
        self.response_timeout_seconds = response_timeout_seconds
        self._process: subprocess.Popen[str] | None = None
        self._closed = False
        self._node_binary = node_binary
        self._katex_css: str | None = None

    def __enter__(self) -> "NodeMarkdownRenderer":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stop_process()

    def _stop_process(self) -> None:
        if self._process is None:
            return
        process = self._process
        self._process = None

        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

    def _ensure_process(self) -> subprocess.Popen[str]:
        if self._closed:
            raise NodeRenderError("Node renderer is closed")
        if self._process is not None and self._process.poll() is None:
            return self._process

        env = os.environ.copy()
        env["NODE_PATH"] = str(self.frontend_node_modules_path)
        env["SCIENTIFIC_SPACES_FRONTEND_PACKAGE_JSON"] = str(
            self.frontend_node_modules_path.parent / "package.json"
        )
        self._process = subprocess.Popen(
            [self.node_binary, str(self.render_script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
        )
        return self._process

    def _render_markdown_with_node(self, markdown: str) -> str:
        process = self._ensure_process()
        request_id = os.urandom(8).hex()
        payload = json.dumps({"request_id": request_id, "markdown": markdown}) + "\n"
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(payload)
        process.stdin.flush()

        try:
            line = _readline_with_timeout(process.stdout, self.response_timeout_seconds)
        except TimeoutError as exc:
            self._stop_process()
            raise NodeRenderError(
                f"Node renderer timed out after {self.response_timeout_seconds:g} seconds"
            ) from exc
        if not line:
            stderr = ""
            if process.poll() is not None and process.stderr is not None:
                stderr = process.stderr.read().strip()
            detail = f": {stderr}" if stderr else ""
            raise NodeRenderError(f"No response from Node renderer{detail}")

        response = json.loads(line)
        if response.get("status") != "ok":
            raise NodeRenderError(response.get("error", "node render failed"))

        if response.get("request_id") != request_id:
            raise NodeRenderError("Node response request id mismatch")

        html_value = response.get("html")
        if not isinstance(html_value, str):
            raise NodeRenderError("Node renderer returned invalid HTML payload")
        return html_value

    def _load_katex_css(self) -> str:
        if self._katex_css is None:
            self._katex_css = _load_katex_css(self.frontend_node_modules_path)
        return self._katex_css

    def render_article(
        self,
        *,
        article_id: str = "",
        title: str,
        url: str,
        markdown: str,
        date: str | None = None,
        category: str | None = None,
        references: Sequence[str | Mapping[str, Any]] = (),
        allowed_image_roots: Sequence[Path] = (),
        content_root: Path | None = None,
        max_local_image_size_bytes: int = DEFAULT_MAX_LOCAL_IMAGE_BYTES,
    ) -> HtmlRenderResult:
        sanitized_markdown, image_summary = sanitize_markdown_images(
            markdown,
            allowed_image_roots=tuple(allowed_image_roots),
            content_root=content_root,
            max_local_image_size_bytes=max_local_image_size_bytes,
        )
        prepared_markdown = prepare_markdown_for_math(sanitized_markdown)
        expected_formula_count, delimiter_balanced = audit_markdown_math(prepared_markdown)
        start = time.perf_counter()
        body_html = self._render_markdown_with_node(prepared_markdown)
        render_duration_ms = (time.perf_counter() - start) * 1000

        normalized_references = tuple(_normalize_reference(reference) for reference in references)
        katex_css = self._load_katex_css() if expected_formula_count else ""
        html_output = build_local_html_document(
            title=title,
            url=url,
            date=date,
            category=category,
            references=normalized_references,
            image_summary=tuple(image_summary),
            body_html=body_html,
            katex_css=katex_css,
            article_id=article_id,
        )

        formula_count = len(re.findall(r'class=["\']katex["\']', body_html))
        explicit_formula_errors = len(re.findall(r'class=["\'][^"\']*katex-error[^"\']*["\']', body_html))
        expected_gap = max(
            expected_formula_count - formula_count - explicit_formula_errors,
            0,
        )
        unrendered_formula_count = min(
            _count_unrendered_formula_markers(body_html),
            expected_gap,
        )
        formula_render_failure_count = explicit_formula_errors + unrendered_formula_count
        body_text_probes = _build_body_text_probes(body_html)

        metrics = HtmlRenderMetrics(
            markdown_input_chars=len(markdown or ""),
            sanitized_markdown_chars=len(prepared_markdown),
            rendered_body_chars=len(body_html),
            output_html_chars=len(html_output),
            image_count=len(image_summary),
            local_images_inlined=len(
                [summary for summary in image_summary if summary.status == "inlined" and summary.kind == "local"]
            ),
            remote_images_replaced=len(
                [summary for summary in image_summary if summary.kind == "remote" and summary.status == "placeholder"]
            ),
            images_placeholder=len([summary for summary in image_summary if summary.status == "placeholder"]),
            render_duration_ms=render_duration_ms,
            katex_css_length=len(katex_css),
            expected_formula_count=expected_formula_count,
            formula_count=formula_count,
            formula_render_failure_count=formula_render_failure_count,
            delimiter_balanced=delimiter_balanced,
        )

        return HtmlRenderResult(
            title=title,
            url=url,
            date=date,
            category=category,
            reference_count=len(normalized_references),
            references=normalized_references,
            image_summary=tuple(image_summary),
            html=html_output,
            body_html=body_html,
            body_text_probes=body_text_probes,
            metrics=metrics,
        )


def _normalize_reference(reference: str | Mapping[str, Any]) -> str:
    if isinstance(reference, str):
        return reference

    if isinstance(reference, Mapping):
        title = reference.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
        source_url = reference.get("url")
        if isinstance(source_url, str) and source_url.strip():
            return source_url.strip()

    return ""
