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
    write_articles(article_file)
    monkeypatch.setenv("SCIENTIFIC_SPACES_ARTICLES_FILE", str(article_file))
    monkeypatch.setenv("SCIENTIFIC_SPACES_LEARNING_FILE", str(learning_file))


def test_learning_state_default_read_update_and_list(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    default_response = client.get("/learning/state/attention-001")
    update_response = client.put("/learning/state/attention-001", json={"status": "reading"})
    completed_response = client.put("/learning/state/attention-001", json={"status": "completed"})
    list_response = client.get("/learning/state")

    assert default_response.status_code == 200
    assert default_response.json()["article_id"] == "attention-001"
    assert default_response.json()["status"] == "unread"
    assert default_response.json()["read_count"] == 0

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "reading"
    assert update_response.json()["last_read_at"]
    assert update_response.json()["read_count"] == 1

    assert completed_response.status_code == 200
    assert completed_response.json()["status"] == "completed"
    assert completed_response.json()["completed_at"]
    assert completed_response.json()["read_count"] == 2

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["article_id"] == "attention-001"


def test_learning_state_rejects_invalid_status(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.put("/learning/state/attention-001", json={"status": "mastered"})

    assert response.status_code == 422


def test_bookmark_add_list_and_delete(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    add_response = client.post("/learning/bookmarks/attention-001")
    list_response = client.get("/learning/bookmarks")
    delete_response = client.delete("/learning/bookmarks/attention-001")
    empty_response = client.get("/learning/bookmarks")

    assert add_response.status_code == 200
    assert add_response.json()["article_id"] == "attention-001"
    assert add_response.json()["title"] == "Attention机制的一个直观解释"
    assert add_response.json()["url"] == "https://spaces.ac.cn/archives/6508"
    assert add_response.json()["created_at"]

    assert list_response.status_code == 200
    assert [item["article_id"] for item in list_response.json()["items"]] == ["attention-001"]

    assert delete_response.status_code == 204
    assert empty_response.json()["items"] == []


def test_notes_crud(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    create_response = client.post("/learning/notes/attention-001", json={"content": "注意 query/key 的相似度。"})
    note_id = create_response.json()["note_id"]
    list_response = client.get("/learning/notes/attention-001")
    update_response = client.put(f"/learning/notes/{note_id}", json={"content": "更新后的手写笔记。"})
    delete_response = client.delete(f"/learning/notes/{note_id}")
    empty_response = client.get("/learning/notes/attention-001")

    assert create_response.status_code == 200
    assert create_response.json()["article_id"] == "attention-001"
    assert create_response.json()["content"] == "注意 query/key 的相似度。"
    assert create_response.json()["created_at"]

    assert list_response.status_code == 200
    assert [item["note_id"] for item in list_response.json()["items"]] == [note_id]

    assert update_response.status_code == 200
    assert update_response.json()["content"] == "更新后的手写笔记。"
    assert update_response.json()["updated_at"] >= update_response.json()["created_at"]

    assert delete_response.status_code == 204
    assert empty_response.json()["items"] == []


def test_session_create_end_and_list(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    create_response = client.post("/learning/sessions", json={"article_id": "attention-001", "source": "reader"})
    session_id = create_response.json()["session_id"]
    end_response = client.put(f"/learning/sessions/{session_id}/end")
    list_response = client.get("/learning/sessions")

    assert create_response.status_code == 200
    assert create_response.json()["article_id"] == "attention-001"
    assert create_response.json()["source"] == "reader"
    assert create_response.json()["started_at"]
    assert create_response.json()["ended_at"] is None

    assert end_response.status_code == 200
    assert end_response.json()["ended_at"]
    assert end_response.json()["duration_seconds"] >= 0

    assert list_response.status_code == 200
    assert [item["session_id"] for item in list_response.json()["items"]] == [session_id]


def test_learning_stats_counts_states_bookmarks_notes_and_sessions(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    client.put("/learning/state/attention-001", json={"status": "completed"})
    client.post("/learning/bookmarks/attention-001")
    client.post("/learning/notes/attention-001", json={"content": "一条学习笔记"})
    session = client.post("/learning/sessions", json={"article_id": "attention-001", "source": "reader"}).json()
    client.put(f"/learning/sessions/{session['session_id']}/end")

    response = client.get("/learning/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_articles"] == 1
    assert payload["unread_count"] == 0
    assert payload["reading_count"] == 0
    assert payload["completed_count"] == 1
    assert payload["bookmark_count"] == 1
    assert payload["note_count"] == 1
    assert payload["recent_articles"][0]["article_id"] == "attention-001"
    assert payload["recent_sessions"][0]["article_id"] == "attention-001"


def test_m2_articles_and_m3_rag_contracts_remain_available(tmp_path: Path, monkeypatch) -> None:
    configure_files(tmp_path, monkeypatch)
    client = TestClient(app)

    articles_response = client.get("/articles")
    index_response = client.post("/rag/index")
    query_response = client.post("/rag/query", json={"question": "什么是Attention？", "top_k": 3})

    assert articles_response.status_code == 200
    assert articles_response.json()["items"][0]["id"] == "attention-001"
    assert "content_preview" in articles_response.json()["items"][0]

    assert index_response.status_code == 200
    assert index_response.json()["article_count"] == 1
    assert query_response.status_code == 200
    assert query_response.json()["sources"]
