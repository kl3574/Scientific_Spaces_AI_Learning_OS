from __future__ import annotations

import json
import os
from pathlib import Path

from app.graph.models import GraphDocument

DEFAULT_GRAPH_FILE = ".local_data/scientific_spaces/knowledge_graph.json"


def graph_store_path() -> Path:
    explicit_file = os.getenv("SCIENTIFIC_SPACES_GRAPH_FILE")
    if explicit_file:
        return Path(explicit_file)
    data_dir = Path(os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
    return data_dir / "knowledge_graph.json"


class GraphStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else graph_store_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> GraphDocument:
        if not self.path.exists():
            return GraphDocument()
        return GraphDocument.from_dict(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, graph: GraphDocument) -> GraphDocument:
        self.path.write_text(json.dumps(graph.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return graph

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
