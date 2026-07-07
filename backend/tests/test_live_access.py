import os
from pathlib import Path

import pytest

from app.crawler.cache import FileCache
from app.crawler.downloader import download_url
from app.crawler.discovery import discover_article_urls


pytestmark = pytest.mark.live


@pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="live source check is opt-in")
def test_live_scientific_spaces_index_is_accessible(tmp_path: Path) -> None:
    html = download_url(
        "https://spaces.ac.cn/",
        cache=FileCache(tmp_path / "cache"),
        retries=1,
        backoff_seconds=0,
    )

    urls = discover_article_urls(
        "https://spaces.ac.cn/",
        max_pages=1,
        fetch_html=lambda _url: html,
    )

    assert urls
