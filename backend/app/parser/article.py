from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.converter.markdown import html_to_markdown


@dataclass(frozen=True)
class ParsedArticle:
    title: str
    url: str
    date: str | None
    category: str | None
    content: str
    images: list[str]
    references: list[dict[str, str]]


def _article_root(soup: BeautifulSoup) -> Tag:
    for selector in ("#content > .Post", "#content .Post", ".Post", "article", ".post", ".entry", "#article"):
        found = soup.select_one(selector)
        if isinstance(found, Tag):
            return found
    return soup


def _content_root(root: Tag) -> Tag:
    for selector in (".entry-content", ".post-content", ".article-content", ".content"):
        found = root.select_one(selector)
        if isinstance(found, Tag):
            return found
    return root


def _extract_title(root: Tag, soup: BeautifulSoup) -> str:
    heading = root.find("h1") or soup.find("h1") or soup.find("title")
    if not heading:
        return ""
    title = heading.get_text(" ", strip=True)
    return re.sub(r"\s+-\s+科学空间.*$", "", title).strip()


def _extract_date(text: str) -> str | None:
    match = re.search(r"((?:19|20)\d{2})[-./年](\d{1,2})[-./月](\d{1,2})", text)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _extract_category(root: Tag, fallback_root: Tag | None = None) -> str | None:
    search_roots = [root]
    if fallback_root is not None and fallback_root is not root:
        search_roots.append(fallback_root)

    for search_root in search_roots:
        category = _extract_category_from_root(search_root)
        if category:
            return category
    return None


def _extract_category_from_root(root: Tag) -> str | None:
    for text_node in root.find_all(string=re.compile("分类")):
        parent = text_node.parent
        if isinstance(parent, Tag):
            link = parent.find_next("a", href=re.compile(r"/category/"))
            if link:
                return link.get_text(" ", strip=True)
    link = root.find("a", href=re.compile(r"/category/"))
    return link.get_text(" ", strip=True) if link else None


def _extract_images(root: Tag, base_url: str) -> list[str]:
    images: list[str] = []
    seen: set[str] = set()
    for image in root.find_all("img"):
        source = image.get("src")
        if not source:
            continue
        absolute = urljoin(base_url, str(source))
        if absolute not in seen:
            images.append(absolute)
            seen.add(absolute)
    return images


def _reference_section(root: Tag) -> Tag | None:
    for heading in root.find_all(re.compile("^h[1-6]$")):
        if "参考" in heading.get_text(" ", strip=True):
            sibling = heading.find_next_sibling()
            while sibling is not None:
                if isinstance(sibling, Tag) and sibling.name in {"ol", "ul"}:
                    return sibling
                sibling = sibling.find_next_sibling()
    return None


def _extract_references(root: Tag) -> list[dict[str, str]]:
    section = _reference_section(root)
    if section is None:
        return []
    references: list[dict[str, str]] = []
    for link in section.find_all("a", href=True):
        references.append({"title": link.get_text(" ", strip=True), "url": str(link["href"])})
    return references


def parse_article_html(html: str, *, url: str) -> ParsedArticle:
    soup = BeautifulSoup(html, "html.parser")
    root = _article_root(soup)
    content_root = _content_root(root)
    fallback_root = root.parent if isinstance(root.parent, Tag) else soup
    return ParsedArticle(
        title=_extract_title(root, soup),
        url=url,
        date=_extract_date(root.get_text(" ", strip=True)),
        category=_extract_category(root, fallback_root),
        content=html_to_markdown(str(content_root), base_url=url),
        images=_extract_images(root, url),
        references=_extract_references(root),
    )
