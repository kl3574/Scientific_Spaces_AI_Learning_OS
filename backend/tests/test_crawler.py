from pathlib import Path

import pytest

from app.crawler.cache import FileCache
from app.crawler.discovery import discover_article_urls
from app.crawler.downloader import DownloadError, download_url


def test_discover_article_urls_follows_pagination_and_filters_archives() -> None:
    pages = {
        "https://spaces.ac.cn/": """
            <a href="/archives/100">first</a>
            <a href="https://spaces.ac.cn/archives/101#comments">duplicate with fragment</a>
            <a href="/category/big-data/">category</a>
            <a class="next" href="/page/2/">下一页</a>
        """,
        "https://spaces.ac.cn/page/2/": """
            <a href="/archives/102">second page</a>
            <a href="/archives/100">duplicate</a>
        """,
    }

    urls = discover_article_urls(
        "https://spaces.ac.cn/",
        max_pages=3,
        fetch_html=lambda url: pages[url],
    )

    assert urls == [
        "https://spaces.ac.cn/archives/100",
        "https://spaces.ac.cn/archives/101",
        "https://spaces.ac.cn/archives/102",
    ]


def test_download_url_retries_and_uses_cache(tmp_path: Path) -> None:
    attempts = {"count": 0}

    def flaky_fetcher(url: str) -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise OSError("temporary network failure")
        return f"<html>{url}</html>"

    cache = FileCache(tmp_path)

    first = download_url(
        "https://spaces.ac.cn/archives/100",
        cache=cache,
        fetcher=flaky_fetcher,
        retries=2,
        backoff_seconds=0,
    )
    second = download_url(
        "https://spaces.ac.cn/archives/100",
        cache=cache,
        fetcher=flaky_fetcher,
        retries=1,
        backoff_seconds=0,
    )

    assert first == "<html>https://spaces.ac.cn/archives/100</html>"
    assert second == first
    assert attempts["count"] == 2


def test_download_url_raises_after_retry_exhaustion(tmp_path: Path) -> None:
    cache = FileCache(tmp_path)

    with pytest.raises(DownloadError):
        download_url(
            "https://spaces.ac.cn/archives/500",
            cache=cache,
            fetcher=lambda _url: (_ for _ in ()).throw(OSError("offline")),
            retries=2,
            backoff_seconds=0,
        )
