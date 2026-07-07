from pathlib import Path

from app.parser.article import ParsedArticle
from app.storage.article_store import ArticleStore
from app.sync import SyncRunner
from app.validation.quality import ArticleQualityValidator
from app.crawler.browser import BrowserFetchResult


FIXTURE = Path(__file__).parent / "fixtures" / "scientific_spaces_article.html"


def make_article(url: str = "https://spaces.ac.cn/archives/1234") -> ParsedArticle:
    return ParsedArticle(
        title="Attention机制的一个直观解释",
        url=url,
        date="2024-01-02",
        category="信息时代",
        content="# Attention机制的一个直观解释\n\n公式 $QK^T$。\n\n![图](https://spaces.ac.cn/a.png)",
        images=["https://spaces.ac.cn/a.png"],
        references=[{"title": "Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762"}],
    )


def test_article_store_upserts_by_url_without_duplicates(tmp_path: Path) -> None:
    store = ArticleStore(tmp_path / "articles.json")

    first = store.upsert(make_article())
    second = store.upsert(make_article())

    articles = store.list_articles()
    assert first.id == second.id
    assert len(articles) == 1
    assert articles[0].title == "Attention机制的一个直观解释"
    assert articles[0].metadata["date"] == "2024-01-02"
    assert articles[0].metadata["images"] == ["https://spaces.ac.cn/a.png"]


def test_quality_validator_reports_title_content_image_and_formula_status() -> None:
    report = ArticleQualityValidator(sample_size=10, min_content_chars=10).validate([make_article()])

    assert report.total_checked == 1
    assert report.title_presence_rate == 1
    assert report.content_completeness_rate == 1
    assert report.images_valid is True
    assert report.formulas_valid is True


def test_sync_runner_imports_articles_and_is_idempotent(tmp_path: Path) -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    store = ArticleStore(tmp_path / "articles.json")
    runner = SyncRunner(
        start_url="https://spaces.ac.cn/",
        max_pages=1,
        store=store,
        fetch_html=lambda _url: '<a href="/archives/1234">article</a>',
        download_html=lambda _url: html,
        report_path=tmp_path / "validation_report.json",
    )

    first = runner.run()
    second = runner.run()

    assert first.imported_count == 1
    assert second.imported_count == 1
    assert store.count() == 1
    assert (tmp_path / "validation_report.json").exists()


def test_sync_runner_imports_rss_browser_articles_and_is_idempotent(tmp_path: Path) -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    store = ArticleStore(tmp_path / "articles.json")

    feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <item><link>https://spaces.ac.cn/archives/100</link></item>
        <item><link>https://spaces.ac.cn/archives/101</link></item>
      </channel>
    </rss>
    """

    class FakeBrowserFetcher:
        failures: list[dict[str, str]] = []

        def fetch_many(self, urls: list[str]) -> list[BrowserFetchResult]:
            return [
                BrowserFetchResult(
                    url=url,
                    html=html,
                    title="Attention机制的一个直观解释",
                    status=200,
                    mathjax_available=True,
                )
                for url in urls
            ]

    runner = SyncRunner(
        source_strategy="rss-browser",
        max_articles=2,
        store=store,
        rss_fetch_xml=lambda _url: feed_xml,
        browser_fetcher=FakeBrowserFetcher(),
        report_path=tmp_path / "validation_report.json",
    )

    first = runner.run()
    second = runner.run()

    assert first.discovered_count == 2
    assert first.imported_count == 2
    assert first.failed_count == 0
    assert second.imported_count == 2
    assert store.count() == 2
    assert (tmp_path / "validation_report.json").exists()
