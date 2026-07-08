from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ArticleChunk:
    article_id: str
    article_title: str
    article_url: str
    section_title: str
    chunk_index: int
    content: str

    def source(self) -> dict[str, object]:
        return {
            "article_id": self.article_id,
            "article_title": self.article_title,
            "article_url": self.article_url,
            "section_title": self.section_title,
            "chunk_index": self.chunk_index,
        }


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def chunk_article(
    *,
    article_id: str,
    article_title: str,
    article_url: str,
    content: str,
) -> list[ArticleChunk]:
    sections = _split_markdown_sections(content)
    chunks: list[ArticleChunk] = []
    for section_title, section_content in sections:
        normalized = section_content.strip()
        if not normalized:
            continue
        chunks.append(
            ArticleChunk(
                article_id=article_id,
                article_title=article_title,
                article_url=article_url,
                section_title=section_title or article_title,
                chunk_index=len(chunks),
                content=normalized,
            )
        )
    return chunks


def _split_markdown_sections(content: str) -> list[tuple[str, str]]:
    current_title = "Article"
    current_lines: list[str] = []
    sections: list[tuple[str, str]] = []
    in_fence = False
    in_equation = False

    for line in content.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            current_lines.append(line)
            in_fence = not in_fence
            continue

        if stripped == "$$":
            current_lines.append(line)
            in_equation = not in_equation
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match and not in_fence and not in_equation:
            _append_section(sections, current_title, current_lines)
            current_title = heading_match.group(2).strip()
            current_lines = [line]
            continue

        current_lines.append(line)

    _append_section(sections, current_title, current_lines)
    return sections


def _append_section(sections: list[tuple[str, str]], title: str, lines: list[str]) -> None:
    content = "\n".join(lines).strip()
    if content:
        sections.append((title, content))
