from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from app.storage.article_store import ArticleStore, StoredArticle

DEFAULT_ARTICLES_FILE = ".local_data/scientific_spaces/articles.json"
ArticleSort = Literal["date_desc", "archive_desc", "title_asc", "relevance"]
_ARCHIVE_ID_PATTERN = re.compile(r"/archives/(\d+)(?:/)?$")


def article_store_path() -> Path:
    explicit_file = os.getenv("SCIENTIFIC_SPACES_ARTICLES_FILE")
    if explicit_file:
        return Path(explicit_file)

    full_corpus_file = os.getenv("SCIENTIFIC_SPACES_ARTICLE_STORE")
    if full_corpus_file:
        return Path(full_corpus_file)

    data_dir = Path(os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
    return data_dir / "articles.json"


def list_articles(
    query: str | None = None,
    *,
    category: str | None = None,
    sort: ArticleSort | None = None,
) -> list[StoredArticle]:
    articles = list(_load_articles(article_store_path()))
    normalized_query = query.strip().casefold() if query else ""
    normalized_category = category.strip().casefold() if category else ""

    if normalized_query:
        articles = [
            article
            for article in articles
            if normalized_query in article.title.casefold() or normalized_query in article.content.casefold()
        ]
    if normalized_category:
        articles = [
            article
            for article in articles
            if str(article.metadata.get("category") or "").casefold() == normalized_category
        ]
    if sort:
        articles = _sort_articles(articles, sort, query=normalized_query)
    return articles


def list_legacy_articles(query: str | None = None) -> list[StoredArticle]:
    articles = list(_load_store_articles(article_store_path()))
    normalized_query = query.strip().lower() if query else ""
    if not normalized_query:
        return articles
    return [
        article
        for article in articles
        if normalized_query in article.title.lower() or normalized_query in article.content.lower()
    ]


def get_article(article_id: str) -> StoredArticle | None:
    for article in _load_store_articles(article_store_path()):
        if article.id == article_id:
            return article
    return None


def article_summary(article: StoredArticle) -> dict[str, Any]:
    return {
        "id": article.id,
        "title": article.title,
        "url": article.url,
        "metadata": article.metadata,
        "content_preview": _content_preview(article.content),
    }


def article_detail(article: StoredArticle) -> dict[str, Any]:
    return article.to_dict()


def _content_preview(content: str, max_chars: int = 240) -> str:
    collapsed = " ".join(line.strip() for line in content.splitlines() if line.strip())
    if len(collapsed) <= max_chars:
        return collapsed
    return f"{collapsed[: max_chars - 1].rstrip()}..."


def _load_articles(path: Path) -> tuple[StoredArticle, ...]:
    by_url: dict[str, StoredArticle] = {}
    for article in _load_store_articles(path):
        by_url[article.url] = article
    return tuple(by_url.values())


def _load_store_articles(path: Path) -> tuple[StoredArticle, ...]:
    try:
        stat = path.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
    except FileNotFoundError:
        signature = None
    return _cached_store_articles(str(path.resolve()), signature)


@lru_cache(maxsize=8)
def _cached_store_articles(path: str, signature: tuple[int, int] | None) -> tuple[StoredArticle, ...]:
    del signature
    return tuple(ArticleStore(Path(path)).list_articles())


def _sort_articles(
    articles: list[StoredArticle],
    sort: ArticleSort,
    *,
    query: str = "",
) -> list[StoredArticle]:
    if sort == "relevance" and query:
        return sorted(articles, key=lambda article: _relevance_sort_key(article, query), reverse=True)
    if sort == "title_asc":
        return sorted(articles, key=lambda article: (article.title.casefold(), article.id))
    if sort == "archive_desc":
        return sorted(articles, key=_archive_sort_key, reverse=True)
    return sorted(articles, key=_date_sort_key, reverse=True)


def _date_sort_key(article: StoredArticle) -> tuple[str, int, str]:
    date = str(article.metadata.get("date") or "")
    return (date, _archive_id(article.url), article.id)


def _archive_sort_key(article: StoredArticle) -> tuple[int, str]:
    return (_archive_id(article.url), article.id)


def _relevance_sort_key(article: StoredArticle, query: str) -> tuple[int, str, int, str]:
    title = article.title.casefold()
    title_rank = 2 if title == query else 1 if query in title else 0
    date = str(article.metadata.get("date") or "")
    return (title_rank, date, _archive_id(article.url), article.id)


def _archive_id(url: str) -> int:
    match = _ARCHIVE_ID_PATTERN.search(url)
    return int(match.group(1)) if match else -1
