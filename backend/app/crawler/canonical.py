from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urlsplit, urlunsplit

ARTICLE_HOST = "spaces.ac.cn"
ALIAS_HOSTS = {"spaces.ac.cn", "www.spaces.ac.cn", "kexue.fm", "www.kexue.fm"}
ARCHIVE_PATH = re.compile(r"^/archives/(\d+)/?$")


@dataclass(frozen=True)
class RejectedUrl:
    original_url: str
    reason: str


@dataclass(frozen=True)
class CanonicalizationSummary:
    discovered_count: int
    canonical_urls: list[str]
    duplicate_count: int
    rejected_urls: list[RejectedUrl] = field(default_factory=list)

    @property
    def canonical_url_count(self) -> int:
        return len(self.canonical_urls)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_urls)


def extract_archive_id(url: str) -> str | None:
    parts = urlsplit(urldefrag(url.strip())[0])
    match = ARCHIVE_PATH.match(parts.path)
    return match.group(1) if match else None


def canonicalize_article_url(url: str) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None

    absolute, _fragment = urldefrag(raw)
    parts = urlsplit(absolute)
    if parts.scheme not in {"http", "https"}:
        return None

    host = parts.netloc.lower()
    if host not in ALIAS_HOSTS:
        return None

    archive_id = extract_archive_id(absolute)
    if not archive_id:
        return None

    return urlunsplit(("https", ARTICLE_HOST, f"/archives/{archive_id}", "", ""))


def canonicalize_article_urls(urls: list[str]) -> CanonicalizationSummary:
    canonical_urls: list[str] = []
    rejected_urls: list[RejectedUrl] = []
    seen: set[str] = set()
    duplicate_count = 0

    for original_url in urls:
        canonical_url = canonicalize_article_url(original_url)
        if canonical_url is None:
            rejected_urls.append(RejectedUrl(original_url=original_url, reason="not an article URL"))
            continue
        if canonical_url in seen:
            duplicate_count += 1
            continue
        canonical_urls.append(canonical_url)
        seen.add(canonical_url)

    return CanonicalizationSummary(
        discovered_count=len(urls),
        canonical_urls=canonical_urls,
        duplicate_count=duplicate_count,
        rejected_urls=rejected_urls,
    )
