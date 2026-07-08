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
            html='<html><title>Article</title><body><div class="Post">content</div></body></html>',
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


def test_browser_article_fetcher_retries_title_only_html_until_article_body_exists() -> None:
    attempts = {"count": 0}

    def loader(url: str) -> BrowserFetchResult:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return BrowserFetchResult(
                url=url,
                html="<html><title>矩阵函数近似中的暴力美学 - 科学空间|Scientific Spaces</title></html>",
                title="矩阵函数近似中的暴力美学",
                status=200,
                mathjax_available=False,
            )
        return BrowserFetchResult(
            url=url,
            html='<html><body><div id="content"><div class="Post">真实正文</div></div></body></html>',
            title="矩阵函数近似中的暴力美学",
            status=200,
            mathjax_available=True,
        )

    fetcher = BrowserArticleFetcher(loader=loader, retries=2, backoff_seconds=0)
    result = fetcher.fetch("https://spaces.ac.cn/archives/11787")

    assert attempts["count"] == 2
    assert 'class="Post"' in result.html
    assert fetcher.failures == []


def test_browser_article_fetcher_rejects_title_only_html_after_bounded_retries() -> None:
    def loader(url: str) -> BrowserFetchResult:
        return BrowserFetchResult(
            url=url,
            html="<html><title>矩阵函数近似中的暴力美学 - 科学空间|Scientific Spaces</title></html>",
            title="矩阵函数近似中的暴力美学",
            status=200,
            mathjax_available=False,
        )

    fetcher = BrowserArticleFetcher(loader=loader, retries=2, backoff_seconds=0)

    with pytest.raises(BrowserAccessError) as exc_info:
        fetcher.fetch("https://spaces.ac.cn/archives/11787")

    assert "article body not found" in exc_info.value.reason
    assert fetcher.failures == [
        {
            "url": "https://spaces.ac.cn/archives/11787",
            "reason": "BrowserAccessError: Failed to fetch https://spaces.ac.cn/archives/11787: article body not found",
        }
    ]


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
