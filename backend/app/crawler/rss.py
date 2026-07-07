from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urldefrag, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

DEFAULT_FEED_URL = "https://spaces.ac.cn/feed"
ARTICLE_URL = re.compile(r"^https://spaces\.ac\.cn/archives/\d+$")


class RssDiscoveryError(RuntimeError):
    pass


def default_fetch_xml(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ScientificSpacesAILearningOS/0.2"})
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_rss_article_urls(xml_text: str, *, max_items: int | None = None) -> list[str]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise RssDiscoveryError("Failed to parse RSS feed") from exc

    discovered: list[str] = []
    seen: set[str] = set()
    items_seen = 0

    for item in _iter_items(root):
        if max_items is not None and items_seen >= max_items:
            break
        items_seen += 1
        url = _canonical_article_url(_item_text(item, "link") or _item_text(item, "guid"))
        if url and url not in seen:
            discovered.append(url)
            seen.add(url)

    return discovered


def discover_rss_article_urls(
    feed_url: str = DEFAULT_FEED_URL,
    *,
    fetch_xml: Callable[[str], str] = default_fetch_xml,
    max_items: int | None = None,
) -> list[str]:
    return parse_rss_article_urls(fetch_xml(feed_url), max_items=max_items)


def _iter_items(root: ElementTree.Element) -> list[ElementTree.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == "item"]


def _item_text(item: ElementTree.Element, child_name: str) -> str | None:
    for child in item:
        if _local_name(child.tag) == child_name and child.text:
            return child.text.strip()
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _canonical_article_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    absolute, _fragment = urldefrag(raw_url.strip())
    parts = urlsplit(absolute)
    path = parts.path.rstrip("/")
    candidate = urlunsplit((parts.scheme, parts.netloc, path, "", ""))
    return candidate if ARTICLE_URL.match(candidate) else None
