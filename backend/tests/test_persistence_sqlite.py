from pathlib import Path

from app.persistence.config import database_path, learning_backend
from app.persistence.sqlite import initialize_schema, table_names


def test_database_path_uses_explicit_file(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "custom.db"
    monkeypatch.setenv("SCIENTIFIC_SPACES_DB_FILE", str(db_file))

    assert database_path() == db_file


def test_database_path_uses_data_dir_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SCIENTIFIC_SPACES_DB_FILE", raising=False)
    monkeypatch.setenv("SCIENTIFIC_SPACES_DATA_DIR", str(tmp_path / "data"))

    assert database_path() == tmp_path / "data" / "scientific_spaces.db"


def test_learning_backend_defaults_to_json_and_accepts_sqlite(monkeypatch) -> None:
    monkeypatch.delenv("SCIENTIFIC_SPACES_LEARNING_BACKEND", raising=False)
    assert learning_backend() == "json"

    monkeypatch.setenv("SCIENTIFIC_SPACES_LEARNING_BACKEND", "sqlite")
    assert learning_backend() == "sqlite"


def test_sqlite_schema_init_is_idempotent(tmp_path: Path) -> None:
    db_file = tmp_path / "scientific_spaces.db"

    initialize_schema(db_file)
    initialize_schema(db_file)

    assert table_names(db_file) >= {
        "learning_state",
        "bookmarks",
        "notes",
        "sessions",
    }
