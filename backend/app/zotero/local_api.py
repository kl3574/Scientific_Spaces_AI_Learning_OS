from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

from app.zotero.models import ZoteroCollection, ZoteroItem, ZoteroStatus


class LocalZoteroProvider:
    def __init__(self, *, base_url: str | None = None, timeout_seconds: int = 5) -> None:
        self.base_url = (base_url or os.getenv("SCIENTIFIC_SPACES_ZOTERO_BASE_URL") or "http://127.0.0.1:23119").rstrip("/")
        self.timeout_seconds = timeout_seconds

    def status(self) -> ZoteroStatus:
        try:
            payload = self._get_json("/api/")
            return ZoteroStatus(
                provider="local",
                available=True,
                read_only=True,
                base_url=self.base_url,
                version=str(payload.get("version") or payload.get("apiVersion") or "") or None,
            )
        except Exception as exc:  # noqa: BLE001 - status must never crash the app.
            return ZoteroStatus(
                provider="local",
                available=False,
                read_only=True,
                base_url=self.base_url,
                error=str(exc),
            )

    def search(self, query: str, limit: int = 20) -> list[ZoteroItem]:
        try:
            params = {"limit": str(limit)}
            if query.strip():
                params["q"] = query.strip()
            payload = self._get_json(f"/api/users/0/items?{urllib.parse.urlencode(params)}")
            return [_item_from_payload(item) for item in payload if _is_regular_item(item)]
        except Exception:
            return []

    def get_item(self, item_key: str) -> ZoteroItem | None:
        try:
            return _item_from_payload(self._get_json(f"/api/users/0/items/{urllib.parse.quote(item_key)}"))
        except Exception:
            return None

    def export_bibtex(self, item_keys: list[str] | None = None) -> str:
        try:
            params = {"format": "bibtex"}
            if item_keys:
                params["itemKey"] = ",".join(item_keys)
            return self._get_text(f"/api/users/0/items?{urllib.parse.urlencode(params)}")
        except Exception:
            return ""

    def list_collections(self) -> list[ZoteroCollection]:
        try:
            payload = self._get_json("/api/users/0/collections")
            return [
                ZoteroCollection(collection_key=str(item.get("key", "")), name=str(item.get("data", {}).get("name", "")))
                for item in payload
            ]
        except Exception:
            return []

    def list_tags(self) -> list[str]:
        try:
            payload = self._get_json("/api/users/0/tags")
            return sorted(str(item.get("tag", "")) for item in payload if item.get("tag"))
        except Exception:
            return []

    def _get_json(self, path: str) -> Any:
        return json.loads(self._get_text(path))

    def _get_text(self, path: str) -> str:
        request = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return response.read().decode("utf-8")


def _is_regular_item(payload: dict[str, Any]) -> bool:
    data = payload.get("data", {})
    return data.get("itemType") not in {"attachment", "note"}


def _item_from_payload(payload: dict[str, Any]) -> ZoteroItem:
    data = payload.get("data", {})
    creators = [_creator_name(creator) for creator in data.get("creators", [])]
    tags = [str(tag.get("tag", "")) for tag in data.get("tags", []) if tag.get("tag")]
    return ZoteroItem(
        item_key=str(payload.get("key") or data.get("key") or ""),
        bibtex_key=_bibtex_key(data),
        title=str(data.get("title") or ""),
        creators=[creator for creator in creators if creator],
        year=_year(data),
        item_type=str(data.get("itemType") or ""),
        publication_title=data.get("publicationTitle") or data.get("bookTitle") or data.get("publisher"),
        doi=data.get("DOI"),
        url=data.get("url"),
        abstract_note=data.get("abstractNote"),
        tags=tags,
        collections=[str(collection) for collection in data.get("collections", [])],
        updated_at=data.get("dateModified"),
    )


def _creator_name(creator: dict[str, Any]) -> str:
    if creator.get("name"):
        return str(creator["name"])
    return " ".join(part for part in [creator.get("firstName"), creator.get("lastName")] if part)


def _year(data: dict[str, Any]) -> str | None:
    date = str(data.get("date") or "")
    for token in date.replace("/", "-").split("-"):
        if len(token) == 4 and token.isdigit():
            return token
    return None


def _bibtex_key(data: dict[str, Any]) -> str | None:
    if data.get("citationKey"):
        return str(data["citationKey"])
    extra = str(data.get("extra") or "")
    for line in extra.splitlines():
        if line.lower().startswith("citation key:"):
            return line.split(":", 1)[1].strip()
    return None
