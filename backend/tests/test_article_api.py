import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


def article_record(
    *,
    article_id: str,
    title: str,
    url: str,
    content: str,
    date: str,
    category: str,
) -> dict[str, Any]:
    return {
        "id": article_id,
        "title": title,
        "url": url,
        "content": content,
        "metadata": {
            "date": date,
            "category": category,
            "references": [],
            "images": [],
        },
    }


def default_articles() -> list[dict[str, Any]]:
    return [
        article_record(
            article_id="attention-001",
            title="Attention机制的一个直观解释",
            url="https://spaces.ac.cn/archives/6508",
            content="# Attention机制的一个直观解释\n\n关键词 Transformer 和 query key value。",
            date="2018-06-01",
            category="信息时代",
        ),
        article_record(
            article_id="matrix-002",
            title="矩阵函数近似中的暴力美学",
            url="https://spaces.ac.cn/archives/11787",
            content="# 矩阵函数近似中的暴力美学\n\n这里讨论矩阵函数和泰勒近似。",
            date="2026-06-25",
            category="数学研究",
        ),
    ]


def write_articles(path: Path, articles: list[dict[str, Any]] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(articles or default_articles(), ensure_ascii=False), encoding="utf-8")


def configured_client(tmp_path: Path, monkeypatch, articles: list[dict[str, Any]] | None = None) -> TestClient:
    article_file = tmp_path / "articles.json"
    write_articles(article_file, articles)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    monkeypatch.delenv("SCIENTIFIC_SPACES_ARTICLE_STORE", raising=False)
    return TestClient(app)


def test_get_articles_preserves_legacy_v1_contract_and_store_order(tmp_path: Path, monkeypatch) -> None:
    client = configured_client(tmp_path, monkeypatch)

    response = client.get("/articles")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "items": payload["items"],
        "total": 2,
        "query": None,
    }
    assert list(payload) == ["items", "total", "query"]
    assert [item["id"] for item in payload["items"]] == ["attention-001", "matrix-002"]
    assert all("content_preview" in item for item in payload["items"])
    assert all("content" not in item for item in payload["items"])


def test_get_articles_legacy_contract_does_not_truncate_37_records(tmp_path: Path, monkeypatch) -> None:
    articles = [
        article_record(
            article_id=f"article-{index:02d}",
            title=f"Article {index:02d}",
            url=f"https://spaces.ac.cn/archives/{10_000 + index}",
            content=f"content {index}",
            date=f"2026-01-{((index - 1) % 28) + 1:02d}",
            category="fixture",
        )
        for index in range(1, 38)
    ]
    client = configured_client(tmp_path, monkeypatch, articles)

    payload = client.get("/articles").json()

    assert payload["total"] == 37
    assert len(payload["items"]) == 37
    assert [item["id"] for item in payload["items"]] == [f"article-{index:02d}" for index in range(1, 38)]


def test_get_article_by_id_returns_detail_with_content(tmp_path: Path, monkeypatch) -> None:
    client = configured_client(tmp_path, monkeypatch)

    response = client.get("/articles/matrix-002")

    assert response.status_code == 200
    assert response.json()["id"] == "matrix-002"
    assert response.json()["title"] == "矩阵函数近似中的暴力美学"
    assert "泰勒近似" in response.json()["content"]
    assert response.json()["metadata"]["date"] == "2026-06-25"


def test_get_article_by_id_returns_404_for_missing_article(tmp_path: Path, monkeypatch) -> None:
    client = configured_client(tmp_path, monkeypatch)

    response = client.get("/articles/not-found")

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"


def test_openapi_separates_legacy_and_versioned_article_list_parameters() -> None:
    schema = app.openapi()

    legacy_parameters = [item["name"] for item in schema["paths"]["/articles"]["get"]["parameters"]]
    versioned_parameters = [
        item["name"] for item in schema["paths"]["/v1.1/articles"]["get"]["parameters"]
    ]

    assert legacy_parameters == ["q"]
    assert versioned_parameters == ["q", "page", "page_size", "category", "sort"]


def test_search_matches_title_content_chinese_and_casefolded_english(tmp_path: Path, monkeypatch) -> None:
    content_only = article_record(
        article_id="newer-content-only",
        title="A newer optimization note",
        url="https://spaces.ac.cn/archives/12000",
        content="This article mentions Attention only in its body.",
        date="2026-07-01",
        category="信息时代",
    )
    client = configured_client(tmp_path, monkeypatch, [*default_articles(), content_only])

    title_response = client.get("/v1.1/articles", params={"q": "attention"})
    uppercase_response = client.get("/v1.1/articles", params={"q": "TRANSFORMER"})
    chinese_response = client.get("/v1.1/articles", params={"q": "泰勒"})

    assert [item["id"] for item in title_response.json()["items"]] == ["attention-001", "newer-content-only"]
    assert title_response.json()["sort"] == "relevance"
    assert [item["id"] for item in uppercase_response.json()["items"]] == ["attention-001"]
    assert [item["id"] for item in chinese_response.json()["items"]] == ["matrix-002"]


def test_legacy_search_keeps_v1_response_shape_and_store_order(tmp_path: Path, monkeypatch) -> None:
    content_only = article_record(
        article_id="content-only",
        title="Optimization note",
        url="https://spaces.ac.cn/archives/12000",
        content="Attention appears only in the body.",
        date="2026-07-01",
        category="信息时代",
    )
    client = configured_client(tmp_path, monkeypatch, [*default_articles(), content_only])

    response = client.get("/articles", params={"q": "attention"})

    assert response.status_code == 200
    assert response.json() == {
        "items": response.json()["items"],
        "total": 2,
        "query": "attention",
    }
    assert [item["id"] for item in response.json()["items"]] == ["attention-001", "content-only"]


def test_legacy_query_length_remains_unconstrained_while_versioned_query_is_bounded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = configured_client(tmp_path, monkeypatch)
    long_query = "x" * 201

    legacy = client.get("/articles", params={"q": long_query})
    versioned = client.get("/v1.1/articles", params={"q": long_query})

    assert legacy.status_code == 200
    assert legacy.json() == {"items": [], "total": 0, "query": long_query}
    assert versioned.status_code == 422


def test_search_no_result_returns_empty_versioned_page(tmp_path: Path, monkeypatch) -> None:
    client = configured_client(tmp_path, monkeypatch)

    response = client.get("/v1.1/articles", params={"q": "不存在的测试关键词"})

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
    assert response.json()["total_pages"] == 0


def test_pagination_covers_first_middle_final_and_beyond_range(tmp_path: Path, monkeypatch) -> None:
    articles = [
        article_record(
            article_id=f"article-{index}",
            title=f"Article {index:02d}",
            url=f"https://spaces.ac.cn/archives/{1000 + index}",
            content=f"content {index}",
            date=f"2026-01-{index:02d}",
            category="信息时代",
        )
        for index in range(1, 6)
    ]
    client = configured_client(tmp_path, monkeypatch, articles)

    first = client.get("/v1.1/articles", params={"page": 1, "page_size": 2}).json()
    middle = client.get("/v1.1/articles", params={"page": 2, "page_size": 2}).json()
    final = client.get("/v1.1/articles", params={"page": 3, "page_size": 2}).json()
    beyond = client.get("/v1.1/articles", params={"page": 4, "page_size": 2}).json()

    assert [item["id"] for item in first["items"]] == ["article-5", "article-4"]
    assert [item["id"] for item in middle["items"]] == ["article-3", "article-2"]
    assert [item["id"] for item in final["items"]] == ["article-1"]
    assert beyond["items"] == []
    assert first["has_next"] is True and first["has_previous"] is False
    assert middle["has_next"] is True and middle["has_previous"] is True
    assert final["has_next"] is False and final["has_previous"] is True
    assert beyond["has_next"] is False and beyond["has_previous"] is True


def test_invalid_pagination_values_are_rejected(tmp_path: Path, monkeypatch) -> None:
    client = configured_client(tmp_path, monkeypatch)

    maximum = client.get("/v1.1/articles", params={"page_size": 100})

    assert maximum.status_code == 200
    assert maximum.json()["page_size"] == 100
    assert client.get("/v1.1/articles", params={"page": 0}).status_code == 422
    assert client.get("/v1.1/articles", params={"page_size": 0}).status_code == 422
    assert client.get("/v1.1/articles", params={"page_size": 101}).status_code == 422


def test_category_filter_and_deterministic_sort_options(tmp_path: Path, monkeypatch) -> None:
    client = configured_client(tmp_path, monkeypatch)

    category = client.get("/v1.1/articles", params={"category": "数学研究"}).json()
    title_sort = client.get("/v1.1/articles", params={"sort": "title_asc"}).json()
    archive_sort = client.get("/v1.1/articles", params={"sort": "archive_desc"}).json()

    assert [item["id"] for item in category["items"]] == ["matrix-002"]
    assert [item["id"] for item in title_sort["items"]] == ["attention-001", "matrix-002"]
    assert [item["id"] for item in archive_sort["items"]] == ["matrix-002", "attention-001"]


def test_duplicate_urls_are_collapsed_before_pagination(tmp_path: Path, monkeypatch) -> None:
    duplicate = article_record(
        article_id="attention-new",
        title="Attention updated",
        url="https://spaces.ac.cn/archives/6508",
        content="updated content",
        date="2026-07-01",
        category="信息时代",
    )
    client = configured_client(tmp_path, monkeypatch, [*default_articles(), duplicate])

    response = client.get("/v1.1/articles")

    assert response.json()["total"] == 2
    attention_items = [item for item in response.json()["items"] if item["url"].endswith("/6508")]
    assert [item["id"] for item in attention_items] == ["attention-new"]


def test_legacy_list_and_detail_do_not_drop_records_with_duplicate_urls(tmp_path: Path, monkeypatch) -> None:
    duplicate = article_record(
        article_id="attention-new",
        title="Attention updated",
        url="https://spaces.ac.cn/archives/6508",
        content="updated content",
        date="2026-07-01",
        category="信息时代",
    )
    client = configured_client(tmp_path, monkeypatch, [*default_articles(), duplicate])

    legacy = client.get("/articles")
    original_detail = client.get("/articles/attention-001")

    assert legacy.status_code == 200
    assert legacy.json()["total"] == 3
    assert [item["id"] for item in legacy.json()["items"]] == [
        "attention-001",
        "matrix-002",
        "attention-new",
    ]
    assert original_detail.status_code == 200
    assert original_detail.json()["title"] == "Attention机制的一个直观解释"


def test_full_corpus_alias_environment_variable_is_supported(tmp_path: Path, monkeypatch) -> None:
    article_file = tmp_path / "corpus" / "articles.json"
    write_articles(article_file)
    monkeypatch.delenv("SCIENTIFIC_SPACES_ARTICLES_FILE", raising=False)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLE_STORE", str(article_file))
    client = TestClient(app)

    response = client.get("/articles")

    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_article_cache_refreshes_when_store_file_changes(tmp_path: Path, monkeypatch) -> None:
    article_file = tmp_path / "articles.json"
    write_articles(article_file)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    client = TestClient(app)

    assert client.get("/articles").json()["total"] == 2

    write_articles(article_file, [default_articles()[0]])

    assert client.get("/articles").json()["total"] == 1


def test_get_articles_empty_dataset_returns_exact_legacy_response(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(tmp_path / "missing.json"))
    monkeypatch.delenv("SCIENTIFIC_SPACES_ARTICLE_STORE", raising=False)
    client = TestClient(app)

    response = client.get("/articles")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "query": None,
    }


def test_get_versioned_articles_empty_dataset_returns_empty_paginated_response(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(tmp_path / "missing.json"))
    monkeypatch.delenv("SCIENTIFIC_SPACES_ARTICLE_STORE", raising=False)
    client = TestClient(app)

    response = client.get("/v1.1/articles")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "query": None,
        "category": None,
        "sort": "date_desc",
        "page": 1,
        "page_size": 20,
        "total_pages": 0,
        "has_next": False,
        "has_previous": False,
    }
