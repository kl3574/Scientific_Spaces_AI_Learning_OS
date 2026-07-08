from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.article_reader import article_detail, article_summary, get_article, list_articles

router = APIRouter()


@router.get("/articles")
def articles(q: str | None = None) -> dict[str, object]:
    items = [article_summary(article) for article in list_articles(q)]
    return {"items": items, "total": len(items), "query": q}


@router.get("/articles/{article_id}")
def article(article_id: str) -> dict[str, object]:
    stored_article = get_article(article_id)
    if stored_article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article_detail(stored_article)
