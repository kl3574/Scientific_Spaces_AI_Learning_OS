from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.parser.article import ParsedArticle


@dataclass(frozen=True)
class StoredArticle:
    id: str
    title: str
    url: str
    content: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "metadata": self.metadata,
        }


def article_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


class ArticleStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> list[StoredArticle]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [StoredArticle(**item) for item in data]

    def _write(self, articles: list[StoredArticle]) -> None:
        self.path.write_text(
            json.dumps([article.to_dict() for article in articles], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def upsert(self, article: ParsedArticle) -> StoredArticle:
        stored = StoredArticle(
            id=article_id(article.url),
            title=article.title,
            url=article.url,
            content=article.content,
            metadata={
                "date": article.date,
                "category": article.category,
                "references": article.references,
                "images": article.images,
            },
        )
        articles = [existing for existing in self._read() if existing.url != stored.url]
        articles.append(stored)
        articles.sort(key=lambda item: item.url)
        self._write(articles)
        return stored

    def list_articles(self) -> list[StoredArticle]:
        return self._read()

    def count(self) -> int:
        return len(self._read())
