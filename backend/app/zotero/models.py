from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ZoteroRelationType = Literal["related", "cites", "background"]


@dataclass(frozen=True)
class ZoteroStatus:
    provider: str
    available: bool
    read_only: bool
    base_url: str | None = None
    version: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "available": self.available,
            "read_only": self.read_only,
            "base_url": self.base_url,
            "version": self.version,
            "error": self.error,
        }


@dataclass(frozen=True)
class ZoteroCollection:
    collection_key: str
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {"collection_key": self.collection_key, "name": self.name}


@dataclass(frozen=True)
class ZoteroItem:
    item_key: str
    bibtex_key: str | None
    title: str
    creators: list[str]
    year: str | None
    item_type: str
    publication_title: str | None
    doi: str | None
    url: str | None
    abstract_note: str | None
    tags: list[str]
    collections: list[str]
    updated_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_key": self.item_key,
            "bibtex_key": self.bibtex_key,
            "title": self.title,
            "creators": self.creators,
            "year": self.year,
            "item_type": self.item_type,
            "publication_title": self.publication_title,
            "doi": self.doi,
            "url": self.url,
            "abstract_note": self.abstract_note,
            "tags": self.tags,
            "collections": self.collections,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ZoteroArticleLink:
    article_id: str
    zotero_item_key: str
    relation_type: ZoteroRelationType
    created_at: str
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "zotero_item_key": self.zotero_item_key,
            "relation_type": self.relation_type,
            "created_at": self.created_at,
            "note": self.note,
        }
