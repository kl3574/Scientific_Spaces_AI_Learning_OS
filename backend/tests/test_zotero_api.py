import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.zotero.fake import FakeZoteroProvider
from app.zotero.local_api import LocalZoteroProvider


def write_articles(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "id": "attention-001",
                    "title": "Attention机制的一个直观解释",
                    "url": "https://spaces.ac.cn/archives/6508",
                    "content": "# Attention机制\n\nAttention 用 query 和 key 计算相关性。",
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


def configure_files(tmp_path: Path, monkeypatch) -> None:
    article_file = tmp_path / "articles.json"
    learning_file = tmp_path / "learning.json"
    zotero_file = tmp_path / "zotero_links.json"
    write_articles(article_file)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    monkeypatch.setenv("SCIENTIFIC_SPACES_LEARNING_FILE", str(learning_file))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_FILE", str(zotero_file))
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_PROVIDER", "fake")


def test_local_zotero_status_without_running_api_is_unavailable() -> None:
    provider = LocalZoteroProvider(base_url="http://127.0.0.1:9")

    status = provider.status()

    assert status.provider == "local"
    assert status.available is False
    assert status.read_only is True
    assert status.error


def test_fake_zotero_provider_search_get_item_and_bibtex_export() -> None:
    provider = FakeZoteroProvider()

    results = provider.search("attention")
    item = provider.get_item("ABCD1234")
    bibtex = provider.export_bibtex(["ABCD1234"])

    assert [result.item_key for result in results] == ["ABCD1234"]
    assert item is not None
    assert item.item_key == "ABCD1234"
    assert item.bibtex_key == "vaswani_attention_2017"
    assert item.item_key != item.bibtex_key
    assert "@article{vaswani_attention_2017" in bibtex


def test_zotero_status_search_item_and_bibtex_api(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    status_response = client.get("/zotero/status")
    search_response = client.get("/zotero/items", params={"q": "attention"})
    item_response = client.get("/zotero/items/ABCD1234")
    export_response = client.post("/zotero/export/bibtex", json={"item_keys": ["ABCD1234"]})

    assert status_response.status_code == 200
    assert status_response.json()["provider"] == "fake"
    assert status_response.json()["available"] is True
    assert status_response.json()["read_only"] is True

    assert search_response.status_code == 200
    assert search_response.json()["total"] == 1
    item = search_response.json()["items"][0]
    assert item["item_key"] == "ABCD1234"
    assert item["bibtex_key"] == "vaswani_attention_2017"
    assert item["title"] == "Attention Is All You Need"

    assert item_response.status_code == 200
    assert item_response.json()["item_key"] == "ABCD1234"
    assert item_response.json()["creators"] == ["Ashish Vaswani", "Noam Shazeer"]

    assert export_response.status_code == 200
    assert export_response.json()["item_count"] == 1
    assert "@article{vaswani_attention_2017" in export_response.json()["bibtex"]


def test_zotero_api_local_provider_unavailable_does_not_crash(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_PROVIDER", "local")
    monkeypatch.setenv("SCIENTIFIC_SPACES_ZOTERO_BASE_URL", "http://127.0.0.1:9")
    client = TestClient(app)

    status_response = client.get("/zotero/status")
    search_response = client.get("/zotero/items", params={"q": "attention"})

    assert status_response.status_code == 200
    assert status_response.json()["provider"] == "local"
    assert status_response.json()["available"] is False
    assert status_response.json()["read_only"] is True
    assert search_response.status_code == 200
    assert search_response.json()["items"] == []


def test_article_zotero_link_create_list_and_delete(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    create_response = client.post(
        "/zotero/links/attention-001",
        json={"item_key": "ABCD1234", "relation_type": "background", "note": "Background reading"},
    )
    list_response = client.get("/zotero/links/attention-001")
    duplicate_response = client.post(
        "/zotero/links/attention-001",
        json={"item_key": "ABCD1234", "relation_type": "related", "note": "Updated note"},
    )
    delete_response = client.delete("/zotero/links/attention-001/ABCD1234")
    empty_response = client.get("/zotero/links/attention-001")

    assert create_response.status_code == 200
    assert create_response.json()["article_id"] == "attention-001"
    assert create_response.json()["zotero_item_key"] == "ABCD1234"
    assert create_response.json()["relation_type"] == "background"
    assert create_response.json()["note"] == "Background reading"
    assert create_response.json()["created_at"]

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    linked = list_response.json()["items"][0]
    assert linked["link"]["zotero_item_key"] == "ABCD1234"
    assert linked["item"]["title"] == "Attention Is All You Need"

    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["relation_type"] == "related"
    assert duplicate_response.json()["note"] == "Updated note"

    assert delete_response.status_code == 204
    assert empty_response.json()["items"] == []


def test_m2_m3_m4_regressions_remain_available(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    article_response = client.get("/articles")
    rag_index_response = client.post("/rag/index")
    rag_query_response = client.post("/rag/query", json={"question": "什么是Attention？", "top_k": 3})
    learning_response = client.get("/learning/stats")

    assert article_response.status_code == 200
    assert article_response.json()["items"][0]["id"] == "attention-001"
    assert rag_index_response.status_code == 200
    assert rag_index_response.json()["article_count"] == 1
    assert rag_query_response.status_code == 200
    assert rag_query_response.json()["sources"]
    assert learning_response.status_code == 200
    assert learning_response.json()["total_articles"] == 1
