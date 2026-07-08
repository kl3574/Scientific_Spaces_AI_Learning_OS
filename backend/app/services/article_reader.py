from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.storage.article_store import ArticleStore, StoredArticle

DEFAULT_ARTICLES_FILE = ".local_data/scientific_spaces/articles.json"


def article_store_path() -> Path:
    explicit_file = os.getenv("SCIENTIFIC_SPACES_ARTICLES_FILE")
    if explicit_file:
        return Path(explicit_file)

    data_dir = Path(os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
    return data_dir / "articles.json"


def list_articles(query: str | None = None) -> list[StoredArticle]:
    articles = ArticleStore(article_store_path()).list_articles()
    normalized_query = query.strip().lower() if query else ""
    if not normalized_query:
        return articles

    return [
        article
        for article in articles
        if normalized_query in article.title.lower() or normalized_query in article.content.lower()
    ]


def get_article(article_id: str) -> StoredArticle | None:
    for article in ArticleStore(article_store_path()).list_articles():
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
