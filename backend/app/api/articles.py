from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.services.article_reader import article_detail, article_summary, get_article, list_articles

router = APIRouter()


@router.get("/articles")
def articles(
    q: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category: Annotated[str | None, Query(max_length=200)] = None,
    sort: Annotated[Literal["date_desc", "archive_desc", "title_asc", "relevance"] | None, Query()] = None,
) -> dict[str, object]:
    query = q.strip() if q and q.strip() else None
    selected_category = category.strip() if category and category.strip() else None
    effective_sort = sort or ("relevance" if query else "date_desc")
    matched = list_articles(query, category=selected_category, sort=effective_sort)
    total = len(matched)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    items = [article_summary(article) for article in matched[start : start + page_size]]
    return {
        "items": items,
        "total": total,
        "query": query,
        "category": selected_category,
        "sort": effective_sort,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": total_pages > 0 and page > 1,
    }


@router.get("/articles/{article_id}")
def article(article_id: str) -> dict[str, object]:
    stored_article = get_article(article_id)
    if stored_article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article_detail(stored_article)
