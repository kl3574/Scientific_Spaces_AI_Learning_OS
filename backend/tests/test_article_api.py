import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def write_articles(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "id": "attention-001",
                    "title": "Attention机制的一个直观解释",
                    "url": "https://spaces.ac.cn/archives/6508",
                    "content": "# Attention机制的一个直观解释\n\n关键词 transformer 和 query key value。",
                    "metadata": {
                        "date": "2018-06-01",
                        "category": "信息时代",
                        "references": [],
                        "images": ["https://spaces.ac.cn/usr/uploads/a.png"],
                    },
                },
                {
                    "id": "matrix-002",
                    "title": "矩阵函数近似中的暴力美学",
                    "url": "https://spaces.ac.cn/archives/11787",
                    "content": "# 矩阵函数近似中的暴力美学\n\n这里讨论矩阵函数和泰勒近似。",
                    "metadata": {
                        "date": "2026-06-25",
                        "category": "数学研究",
                        "references": [],
                        "images": [],
                    },
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_get_articles_returns_list_with_preview(tmp_path: Path, monkeypatch) -> None:
    article_file = tmp_path / "articles.json"
    write_articles(article_file)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    client = TestClient(app)

    response = client.get("/articles")

    assert response.status_code == 200
    assert response.json()["total"] == 2
    first = response.json()["items"][0]
    assert first["id"] == "attention-001"
    assert first["title"] == "Attention机制的一个直观解释"
    assert first["url"] == "https://spaces.ac.cn/archives/6508"
    assert first["metadata"]["category"] == "信息时代"
    assert "content_preview" in first
    assert "transformer" in first["content_preview"]
    assert "content" not in first


def test_get_article_by_id_returns_detail(tmp_path: Path, monkeypatch) -> None:
    article_file = tmp_path / "articles.json"
    write_articles(article_file)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    client = TestClient(app)

    response = client.get("/articles/matrix-002")

    assert response.status_code == 200
    assert response.json()["id"] == "matrix-002"
    assert response.json()["title"] == "矩阵函数近似中的暴力美学"
    assert "泰勒近似" in response.json()["content"]
    assert response.json()["metadata"]["date"] == "2026-06-25"


def test_get_article_by_id_returns_404_for_missing_article(tmp_path: Path, monkeypatch) -> None:
    article_file = tmp_path / "articles.json"
    write_articles(article_file)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    client = TestClient(app)

    response = client.get("/articles/not-found")

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"


def test_search_articles_matches_title_and_content(tmp_path: Path, monkeypatch) -> None:
    article_file = tmp_path / "articles.json"
    write_articles(article_file)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    client = TestClient(app)

    title_response = client.get("/articles", params={"q": "Attention"})
    content_response = client.get("/articles", params={"q": "泰勒"})

    assert title_response.status_code == 200
    assert [item["id"] for item in title_response.json()["items"]] == ["attention-001"]
    assert content_response.status_code == 200
    assert [item["id"] for item in content_response.json()["items"]] == ["matrix-002"]


def test_get_articles_empty_dataset_returns_empty_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(tmp_path / "missing.json"))
    client = TestClient(app)

    response = client.get("/articles")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "query": None}
