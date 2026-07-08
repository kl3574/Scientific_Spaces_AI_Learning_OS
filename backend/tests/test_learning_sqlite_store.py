from pathlib import Path

from app.learning.sqlite_store import LearningSQLiteStore


def test_sqlite_learning_state_crud(tmp_path: Path) -> None:
    store = LearningSQLiteStore(tmp_path / "learning.db")

    default_state = store.get_state("article-1")
    reading = store.update_state("article-1", "reading")
    completed = store.update_state("article-1", "completed")
    unread = store.update_state("article-1", "unread")
    states = store.list_states()

    assert default_state.status == "unread"
    assert default_state.read_count == 0

    assert reading.status == "reading"
    assert reading.last_read_at
    assert reading.read_count == 1

    assert completed.status == "completed"
    assert completed.completed_at
    assert completed.read_count == 2

    assert unread.status == "unread"
    assert unread.completed_at is None
    assert unread.read_count == 2

    assert [state.article_id for state in states] == ["article-1"]


def test_sqlite_bookmark_crud_is_idempotent(tmp_path: Path) -> None:
    store = LearningSQLiteStore(tmp_path / "learning.db")

    created = store.add_bookmark(article_id="article-1", title="Title", url="https://example.com/a")
    duplicate = store.add_bookmark(article_id="article-1", title="Changed", url="https://example.com/b")
    bookmarks = store.list_bookmarks()
    store.delete_bookmark("article-1")

    assert created == duplicate
    assert len(bookmarks) == 1
    assert bookmarks[0].title == "Title"
    assert store.list_bookmarks() == []


def test_sqlite_notes_crud(tmp_path: Path) -> None:
    store = LearningSQLiteStore(tmp_path / "learning.db")

    created = store.create_note(article_id="article-1", content="first note")
    listed = store.list_notes("article-1")
    updated = store.update_note(note_id=created.note_id, content="updated note")
    missing = store.update_note(note_id="missing", content="ignored")
    store.delete_note(created.note_id)

    assert listed == [created]
    assert updated is not None
    assert updated.note_id == created.note_id
    assert updated.article_id == "article-1"
    assert updated.content == "updated note"
    assert updated.created_at == created.created_at
    assert updated.updated_at >= created.updated_at
    assert missing is None
    assert store.list_notes("article-1") == []
    assert store.count_notes() == 0


def test_sqlite_session_create_end_and_list(tmp_path: Path) -> None:
    store = LearningSQLiteStore(tmp_path / "learning.db")

    created = store.create_session(article_id="article-1", source="reader")
    ended = store.end_session(created.session_id)
    missing = store.end_session("missing")
    sessions = store.list_sessions()

    assert created.article_id == "article-1"
    assert created.source == "reader"
    assert created.ended_at is None
    assert ended is not None
    assert ended.ended_at
    assert ended.duration_seconds is not None
    assert ended.duration_seconds >= 0
    assert missing is None
    assert [session.session_id for session in sessions] == [created.session_id]
