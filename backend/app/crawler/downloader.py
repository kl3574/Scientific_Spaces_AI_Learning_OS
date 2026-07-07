from __future__ import annotations

import time
from collections.abc import Callable
from urllib.request import Request, urlopen

from app.crawler.cache import FileCache


class DownloadError(RuntimeError):
    pass


def default_fetcher(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ScientificSpacesAILearningOS/0.2"})
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def download_url(
    url: str,
    *,
    cache: FileCache,
    fetcher: Callable[[str], str] = default_fetcher,
    retries: int = 3,
    backoff_seconds: float = 0.5,
) -> str:
    cached = cache.get(url)
    if cached is not None:
        return cached

    last_error: Exception | None = None
    for attempt in range(max(retries, 1)):
        try:
            html = fetcher(url)
        except Exception as exc:  # noqa: BLE001 - convert external fetch failures.
            last_error = exc
            if attempt < retries - 1 and backoff_seconds:
                time.sleep(backoff_seconds * (attempt + 1))
            continue
        cache.set(url, html)
        return html

    raise DownloadError(f"Failed to download {url}") from last_error
