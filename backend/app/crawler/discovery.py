from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

ARTICLE_PATH = re.compile(r"^/archives/\d+/?$")
NEXT_TEXT = {"下一页", "下页", "older", "next", ">", "›", "»"}


def _canonical_url(base_url: str, href: str) -> str:
    absolute = urljoin(base_url, href)
    absolute, _fragment = urldefrag(absolute)
    parts = urlsplit(absolute)
    path = parts.path.rstrip("/") if ARTICLE_PATH.match(parts.path) else parts.path
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def _is_article_url(url: str) -> bool:
    return bool(ARTICLE_PATH.match(urlsplit(url).path))


def _extract_article_urls(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        candidate = _canonical_url(page_url, str(link["href"]))
        if _is_article_url(candidate) and candidate not in seen:
            urls.append(candidate)
            seen.add(candidate)
    return urls


def _find_next_page(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    rel_next = soup.find("a", rel=lambda rel: rel and "next" in rel)
    if rel_next and rel_next.get("href"):
        return _canonical_url(page_url, str(rel_next["href"]))

    for link in soup.find_all("a", href=True):
        classes = " ".join(link.get("class", []))
        text = link.get_text(" ", strip=True).lower()
        if "next" in classes.lower() or text in NEXT_TEXT or "下一页" in text:
            return _canonical_url(page_url, str(link["href"]))
    return None


def discover_article_urls(
    start_url: str,
    *,
    max_pages: int = 1,
    fetch_html: Callable[[str], str],
) -> list[str]:
    discovered: list[str] = []
    seen_articles: set[str] = set()
    seen_pages: set[str] = set()
    page_url: str | None = start_url

    for _page_index in range(max_pages):
        if not page_url or page_url in seen_pages:
            break
        seen_pages.add(page_url)
        html = fetch_html(page_url)
        for article_url in _extract_article_urls(html, page_url):
            if article_url not in seen_articles:
                discovered.append(article_url)
                seen_articles.add(article_url)
        page_url = _find_next_page(html, page_url)

    return discovered
