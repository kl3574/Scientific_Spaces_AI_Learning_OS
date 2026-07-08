from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.tutor.models import TutorMode, TutorSession

DEFAULT_TUTOR_FILE = ".local_data/scientific_spaces/tutor_sessions.json"


def tutor_store_path() -> Path:
    explicit_file = os.getenv("SCIENTIFIC_SPACES_TUTOR_FILE")
    if explicit_file:
        return Path(explicit_file)
    data_dir = Path(os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
    return data_dir / "tutor_sessions.json"


class TutorSessionStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else tutor_store_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def create_session(self, *, mode: TutorMode, article_id: str | None = None, node_id: str | None = None) -> TutorSession:
        data = self._read()
        now = _now()
        session = TutorSession(
            session_id=uuid4().hex,
            mode=mode,
            article_id=article_id,
            node_id=node_id,
            created_at=now,
            updated_at=now,
            turns=[],
        )
        data[session.session_id] = session.to_dict()
        self._write(data)
        return session

    def list_sessions(self) -> list[TutorSession]:
        sessions = [TutorSession.from_dict(item) for item in self._read().values()]
        return sorted(sessions, key=lambda session: session.updated_at, reverse=True)

    def get_session(self, session_id: str) -> TutorSession | None:
        item = self._read().get(session_id)
        if item is None:
            return None
        return TutorSession.from_dict(item)

    def append_turn(self, session_id: str, turn: dict[str, object]) -> TutorSession | None:
        data = self._read()
        item = data.get(session_id)
        if item is None:
            return None
        turns = list(item.get("turns") or [])
        turns.append(turn)
        item["turns"] = turns
        item["updated_at"] = _now()
        data[session_id] = item
        self._write(data)
        return TutorSession.from_dict(item)

    def _read(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, dict[str, object]]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
