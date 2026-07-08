from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

LearningBackend = Literal["json", "sqlite"]


def data_dir() -> Path:
    return Path(os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))


def database_path() -> Path:
    explicit_file = os.getenv("SCIENTIFIC_SPACES_DB_FILE")
    if explicit_file:
        return Path(explicit_file)
    return data_dir() / "scientific_spaces.db"


def learning_backend() -> LearningBackend:
    value = os.getenv("SCIENTIFIC_SPACES_LEARNING_BACKEND", "json").strip().lower()
    if value not in {"json", "sqlite"}:
        raise ValueError("SCIENTIFIC_SPACES_LEARNING_BACKEND must be 'json' or 'sqlite'")
    return value  # type: ignore[return-value]
