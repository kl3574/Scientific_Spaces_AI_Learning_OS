from __future__ import annotations

import os
from typing import Protocol

from app.zotero.models import ZoteroCollection, ZoteroItem, ZoteroStatus


class ZoteroProvider(Protocol):
    def status(self) -> ZoteroStatus:
        """Return provider readiness without raising on unavailable Zotero."""

    def search(self, query: str, limit: int = 20) -> list[ZoteroItem]:
        """Return read-only Zotero metadata search results."""

    def get_item(self, item_key: str) -> ZoteroItem | None:
        """Return a single Zotero item by Zotero item key."""

    def export_bibtex(self, item_keys: list[str] | None = None) -> str:
        """Return BibTeX for selected item keys or a small provider-defined set."""

    def list_collections(self) -> list[ZoteroCollection]:
        """Return Zotero collections where available."""

    def list_tags(self) -> list[str]:
        """Return Zotero tags where available."""


def get_zotero_provider() -> ZoteroProvider:
    provider_name = os.getenv("SCIENTIFIC_SPACES_ZOTERO_PROVIDER", "fake").strip().lower()
    if provider_name == "local":
        from app.zotero.local_api import LocalZoteroProvider

        return LocalZoteroProvider()
    from app.zotero.fake import FakeZoteroProvider

    return FakeZoteroProvider()
