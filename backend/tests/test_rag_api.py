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
                    "content": "# Attention机制\n\nAttention 用 query 和 key 计算相关性。\n\n## 数学形式\n\n$$\nQK^T\n$$\n",
                    "metadata": {
                        "date": "2018-06-01",
                        "category": "信息时代",
                        "references": [],
                        "images": [],
                    },
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_rag_index_and_query_return_cited_answer(tmp_path: Path, monkeypatch) -> None:
    article_file = tmp_path / "articles.json"
    write_articles(article_file)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    client = TestClient(app)

    index_response = client.post("/rag/index")
    query_response = client.post("/rag/query", json={"question": "什么是Attention？", "top_k": 3})

    assert index_response.status_code == 200
    assert index_response.json()["article_count"] == 1
    assert index_response.json()["chunk_count"] >= 1
    assert query_response.status_code == 200
    payload = query_response.json()
    assert "Attention" in payload["answer"]
    assert payload["sources"]
    assert payload["sources"][0]["article_title"] == "Attention机制的一个直观解释"
    assert payload["sources"][0]["article_url"] == "https://spaces.ac.cn/archives/6508"
    assert payload["sources"][0]["section_title"] in {"Attention机制", "数学形式"}
    assert isinstance(payload["sources"][0]["chunk_index"], int)


def test_rag_query_without_sources_refuses_to_answer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(tmp_path / "missing.json"))
    client = TestClient(app)

    index_response = client.post("/rag/index")
    query_response = client.post("/rag/query", json={"question": "什么是Attention？", "top_k": 3})

    assert index_response.status_code == 200
    assert index_response.json()["chunk_count"] == 0
    assert query_response.status_code == 200
    assert "无法基于当前资料回答" in query_response.json()["answer"]
    assert query_response.json()["sources"] == []
