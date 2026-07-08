from __future__ import annotations

import os
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from app.crawler.cache import FileCache
from app.crawler.browser import BrowserArticleFetcher, BrowserFetchResult
from app.crawler.discovery import discover_article_urls
from app.crawler.downloader import download_url
from app.crawler.rss import DEFAULT_FEED_URL, default_fetch_xml, discover_rss_article_urls
from app.parser.article import ParsedArticle, parse_article_html
from app.storage.article_store import ArticleStore
from app.validation.quality import ArticleQualityValidator, ValidationReport

DEFAULT_START_URL = "https://spaces.ac.cn/"
DEFAULT_MAX_ARTICLES = 5


@dataclass(frozen=True)
class SyncResult:
    discovered_count: int
    imported_count: int
    report: ValidationReport
    failed_count: int = 0
    failures: list[dict[str, str]] = field(default_factory=list)


class SyncRunner:
    def __init__(
        self,
        *,
        start_url: str = DEFAULT_START_URL,
        feed_url: str = DEFAULT_FEED_URL,
        max_pages: int = 1,
        max_articles: int = DEFAULT_MAX_ARTICLES,
        source_strategy: str = "auto",
        store: ArticleStore | None = None,
        cache: FileCache | None = None,
        fetch_html: Callable[[str], str] | None = None,
        download_html: Callable[[str], str] | None = None,
        rss_fetch_xml: Callable[[str], str] | None = None,
        browser_fetcher: BrowserArticleFetcher | None = None,
        report_path: Path | str | None = None,
    ) -> None:
        data_dir = Path(os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
        self.start_url = start_url
        self.feed_url = feed_url
        self.max_pages = max_pages
        self.max_articles = max_articles
        self.source_strategy = source_strategy
        self.cache = cache or FileCache(data_dir / "cache")
        self.store = store or ArticleStore(data_dir / "articles.json")
        self.fetch_html = fetch_html
        self.download_html = download_html
        self.rss_fetch_xml = rss_fetch_xml
        self.browser_fetcher = browser_fetcher
        self.report_path = Path(report_path) if report_path else data_dir / "validation_report.json"

    def run(self) -> SyncResult:
        article_urls = self._discover_urls()
        imported = 0
        failures: list[dict[str, str]] = []

        for result in self._fetch_articles(article_urls):
            article = parse_article_html(result.html, url=result.url)
            import_issue = _article_import_issue(article)
            if import_issue is not None:
                failures.append({"url": article.url, "reason": import_issue})
                continue
            self.store.upsert(article)
            imported += 1

        if self._uses_browser_source():
            fetcher = self.browser_fetcher
            if fetcher is not None:
                failures.extend(fetcher.failures)

        report = ArticleQualityValidator().validate(self.store.list_articles())
        report.write_json(self.report_path)
        return SyncResult(
            discovered_count=len(article_urls),
            imported_count=imported,
            report=report,
            failed_count=len(failures),
            failures=failures,
        )

    def _discover_urls(self) -> list[str]:
        if not self._uses_browser_source():
            fetch_html = self.fetch_html or (lambda url: download_url(url, cache=self.cache))
            return discover_article_urls(
                self.start_url,
                max_pages=self.max_pages,
                fetch_html=fetch_html,
            )

        return discover_rss_article_urls(
            self.feed_url,
            fetch_xml=self.rss_fetch_xml or default_fetch_xml,
            max_items=self.max_articles,
        )

    def _fetch_articles(self, article_urls: list[str]) -> list[BrowserFetchResult]:
        if not self._uses_browser_source():
            download_html = self.download_html or (lambda url: download_url(url, cache=self.cache))
            return [
                BrowserFetchResult(
                    url=url,
                    html=download_html(url),
                    title="",
                    status=200,
                    mathjax_available=False,
                )
                for url in article_urls
            ]

        fetcher = self.browser_fetcher or BrowserArticleFetcher()
        self.browser_fetcher = fetcher
        return fetcher.fetch_many(article_urls)

    def _uses_browser_source(self) -> bool:
        if self.source_strategy == "rss-browser":
            return True
        if self.source_strategy == "legacy":
            return False
        return self.fetch_html is None and self.download_html is None


def main() -> None:
    args = _parse_args()
    data_dir = Path(args.data_dir or os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
    fetch_html = _index_file_fetcher(Path(args.index_file)) if args.index_file else None
    download_html = _article_dir_downloader(Path(args.article_dir)) if args.article_dir else None
    store = ArticleStore(data_dir / "articles.json")
    cache = FileCache(data_dir / "cache")
    max_pages = args.max_pages if args.max_pages is not None else int(os.getenv("SCIENTIFIC_SPACES_MAX_PAGES", "1"))
    max_articles = args.max_articles if args.max_articles is not None else int(
        os.getenv("SCIENTIFIC_SPACES_MAX_ARTICLES", str(DEFAULT_MAX_ARTICLES))
    )
    source_strategy = args.source_strategy
    if fetch_html is not None or download_html is not None:
        source_strategy = "legacy"
    result = SyncRunner(
        start_url=args.start_url,
        feed_url=args.feed_url,
        max_pages=max_pages,
        max_articles=max_articles,
        source_strategy=source_strategy,
        store=store,
        cache=cache,
        fetch_html=fetch_html,
        download_html=download_html,
        report_path=data_dir / "validation_report.json",
    ).run()
    print(
        "Scientific Spaces sync completed: "
        f"discovered={result.discovered_count}, imported={result.imported_count}, "
        f"failed={result.failed_count}, validated={result.report.total_checked}"
    )


def _parse_args() -> Namespace:
    parser = ArgumentParser(description="Sync Scientific Spaces source articles.")
    parser.add_argument("--start-url", default=os.getenv("SCIENTIFIC_SPACES_START_URL", DEFAULT_START_URL))
    parser.add_argument("--feed-url", default=os.getenv("SCIENTIFIC_SPACES_FEED_URL", DEFAULT_FEED_URL))
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-articles", type=int, default=None)
    parser.add_argument(
        "--source-strategy",
        choices=("auto", "legacy", "rss-browser"),
        default=os.getenv("SCIENTIFIC_SPACES_SOURCE_STRATEGY", "auto"),
    )
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--index-file", default=os.getenv("SCIENTIFIC_SPACES_INDEX_FILE"))
    parser.add_argument("--article-dir", default=os.getenv("SCIENTIFIC_SPACES_ARTICLE_DIR"))
    return parser.parse_args()


def _index_file_fetcher(index_file: Path) -> Callable[[str], str]:
    def fetch(_url: str) -> str:
        return index_file.read_text(encoding="utf-8")

    return fetch


def _article_dir_downloader(article_dir: Path) -> Callable[[str], str]:
    def download(url: str) -> str:
        article_id = Path(urlsplit(url).path).name
        return (article_dir / f"{article_id}.html").read_text(encoding="utf-8")

    return download


def _article_import_issue(article: ParsedArticle) -> str | None:
    report = ArticleQualityValidator(sample_size=1).validate([article])
    if report.issues:
        return "; ".join(issue.split(": ", 1)[1] for issue in report.issues)
    return None


if __name__ == "__main__":
    main()
