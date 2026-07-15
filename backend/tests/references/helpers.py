from __future__ import annotations

from app.references.deduplication import ReferenceBuildData, build_reference_data
from app.references.extraction import extract_article_references
from app.references.models import sha256_text
from app.storage.article_store import StoredArticle


def article(
    article_id: str,
    content: str,
    *,
    title: str | None = None,
    url: str | None = None,
) -> StoredArticle:
    return StoredArticle(
        id=article_id,
        title=title or f"Article {article_id}",
        url=url or f"https://spaces.ac.cn/archives/{article_id}",
        content=content,
        metadata={"date": "2020-01-01", "category": "test", "references": [], "images": []},
    )


def reference_data(*articles: StoredArticle, build_id: str = "fixture-build") -> ReferenceBuildData:
    corpus_fingerprint = sha256_text("fixture-corpus")
    return build_reference_data(
        [extract_article_references(item) for item in articles],
        corpus_fingerprint=corpus_fingerprint,
        build_id=build_id,
    )
