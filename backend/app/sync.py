from __future__ import annotations

import os
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from app.crawler.cache import FileCache
from app.crawler.discovery import discover_article_urls
from app.crawler.downloader import download_url
from app.parser.article import parse_article_html
from app.storage.article_store import ArticleStore
from app.validation.quality import ArticleQualityValidator, ValidationReport

DEFAULT_START_URL = "https://spaces.ac.cn/"


@dataclass(frozen=True)
class SyncResult:
    discovered_count: int
    imported_count: int
    report: ValidationReport


class SyncRunner:
    def __init__(
        self,
        *,
        start_url: str = DEFAULT_START_URL,
        max_pages: int = 1,
        store: ArticleStore | None = None,
        cache: FileCache | None = None,
        fetch_html: Callable[[str], str] | None = None,
        download_html: Callable[[str], str] | None = None,
        report_path: Path | str | None = None,
    ) -> None:
        data_dir = Path(os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
        self.start_url = start_url
        self.max_pages = max_pages
        self.cache = cache or FileCache(data_dir / "cache")
        self.store = store or ArticleStore(data_dir / "articles.json")
        self.fetch_html = fetch_html or (lambda url: download_url(url, cache=self.cache))
        self.download_html = download_html or (lambda url: download_url(url, cache=self.cache))
        self.report_path = Path(report_path) if report_path else data_dir / "validation_report.json"

    def run(self) -> SyncResult:
        article_urls = discover_article_urls(
            self.start_url,
            max_pages=self.max_pages,
            fetch_html=self.fetch_html,
        )
        imported = 0
        for url in article_urls:
            html = self.download_html(url)
            article = parse_article_html(html, url=url)
            self.store.upsert(article)
            imported += 1

        report = ArticleQualityValidator().validate(self.store.list_articles())
        report.write_json(self.report_path)
        return SyncResult(
            discovered_count=len(article_urls),
            imported_count=imported,
            report=report,
        )


def main() -> None:
    args = _parse_args()
    data_dir = Path(args.data_dir or os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
    fetch_html = _index_file_fetcher(Path(args.index_file)) if args.index_file else None
    download_html = _article_dir_downloader(Path(args.article_dir)) if args.article_dir else None
    store = ArticleStore(data_dir / "articles.json")
    cache = FileCache(data_dir / "cache")
    max_pages = args.max_pages if args.max_pages is not None else int(os.getenv("SCIENTIFIC_SPACES_MAX_PAGES", "1"))
    result = SyncRunner(
        start_url=args.start_url,
        max_pages=max_pages,
        store=store,
        cache=cache,
        fetch_html=fetch_html,
        download_html=download_html,
        report_path=data_dir / "validation_report.json",
    ).run()
    print(
        "Scientific Spaces sync completed: "
        f"discovered={result.discovered_count}, imported={result.imported_count}, "
        f"validated={result.report.total_checked}"
    )


def _parse_args() -> Namespace:
    parser = ArgumentParser(description="Sync Scientific Spaces source articles.")
    parser.add_argument("--start-url", default=os.getenv("SCIENTIFIC_SPACES_START_URL", DEFAULT_START_URL))
    parser.add_argument("--max-pages", type=int, default=None)
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


if __name__ == "__main__":
    main()
