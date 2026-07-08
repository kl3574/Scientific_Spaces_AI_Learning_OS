from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.zotero.models import ZoteroArticleLink, ZoteroRelationType

DEFAULT_ZOTERO_LINKS_FILE = ".local_data/scientific_spaces/zotero_links.json"


def zotero_store_path() -> Path:
    explicit_file = os.getenv("SCIENTIFIC_SPACES_ZOTERO_FILE")
    if explicit_file:
        return Path(explicit_file)

    data_dir = Path(os.getenv("SCIENTIFIC_SPACES_DATA_DIR", ".local_data/scientific_spaces"))
    return data_dir / "zotero_links.json"


class ZoteroLinkStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_links(self, article_id: str) -> list[ZoteroArticleLink]:
        links = [
            ZoteroArticleLink(**item)
            for item in self._read().get(article_id, {}).values()
        ]
        return sorted(links, key=lambda item: item.created_at, reverse=True)

    def upsert_link(
        self,
        *,
        article_id: str,
        zotero_item_key: str,
        relation_type: ZoteroRelationType,
        note: str | None = None,
    ) -> ZoteroArticleLink:
        data = self._read()
        article_links = data.setdefault(article_id, {})
        existing = article_links.get(zotero_item_key)
        created_at = existing["created_at"] if existing else _now()
        link = ZoteroArticleLink(
            article_id=article_id,
            zotero_item_key=zotero_item_key,
            relation_type=relation_type,
            created_at=created_at,
            note=note,
        )
        article_links[zotero_item_key] = link.to_dict()
        self._write(data)
        return link

    def delete_link(self, *, article_id: str, zotero_item_key: str) -> None:
        data = self._read()
        article_links = data.get(article_id, {})
        article_links.pop(zotero_item_key, None)
        if not article_links:
            data.pop(article_id, None)
        self._write(data)

    def _read(self) -> dict[str, dict[str, dict[str, object]]]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, dict[str, dict[str, object]]]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
