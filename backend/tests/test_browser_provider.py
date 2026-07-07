import pytest

from app.crawler.browser import BrowserAccessError, BrowserArticleFetcher, BrowserFetchResult


def test_browser_article_fetcher_retries_and_returns_html_title_and_mathjax() -> None:
    attempts = {"count": 0}

    def loader(url: str) -> BrowserFetchResult:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("slow page")
        return BrowserFetchResult(
            url=url,
            html="<html><title>Article</title><body>content</body></html>",
            title="Article",
            status=200,
            mathjax_available=True,
        )

    fetcher = BrowserArticleFetcher(loader=loader, retries=2, backoff_seconds=0)
    result = fetcher.fetch("https://spaces.ac.cn/archives/11804")

    assert result.title == "Article"
    assert result.html.startswith("<html>")
    assert result.mathjax_available is True
    assert attempts["count"] == 2
    assert fetcher.failures == []


def test_browser_article_fetcher_records_failure_reason_after_bounded_retries() -> None:
    def loader(url: str) -> BrowserFetchResult:
        raise RuntimeError(f"blocked: {url}")

    fetcher = BrowserArticleFetcher(loader=loader, retries=2, backoff_seconds=0)

    with pytest.raises(BrowserAccessError) as exc_info:
        fetcher.fetch("https://spaces.ac.cn/archives/11787")

    assert exc_info.value.url == "https://spaces.ac.cn/archives/11787"
    assert "blocked" in exc_info.value.reason
    assert fetcher.failures == [
        {
            "url": "https://spaces.ac.cn/archives/11787",
            "reason": "RuntimeError: blocked: https://spaces.ac.cn/archives/11787",
        }
    ]
