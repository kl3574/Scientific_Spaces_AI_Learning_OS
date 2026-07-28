from __future__ import annotations

import re
from typing import Any

import pytest

from app.storage.article_store import StoredArticle
from app.zotero.sync import (
    ARTICLE_ID_PREFIX,
    ZoteroArticleSync,
    ZoteroSyncError,
    canonicalize_article_url,
    render_article_ris,
)


def _article() -> StoredArticle:
    return StoredArticle(
        id="article-6508",
        title="科学空间浏览指南（FAQ）",
        url="https://spaces.ac.cn/archives/6508",
        content="正文",
        metadata={
            "date": "2019-03-26",
            "category": "大数据",
            "references": [],
            "images": [],
        },
    )


class FakeTransport:
    def __init__(
        self,
        *,
        collections: list[dict[str, Any]] | None = None,
        items: list[dict[str, Any]] | None = None,
    ) -> None:
        self.collections = (
            collections
            if collections is not None
            else [
                {
                    "key": "COLLECTION1",
                    "data": {"name": "苏剑林博客", "parentCollection": False},
                }
            ]
        )
        self.items = items if items is not None else []
        self.selected: tuple[str, str] | None = None
        self.import_count = 0
        self.import_error: ZoteroSyncError | None = None

    def find_collections(self, name: str) -> list[dict[str, Any]]:
        assert name == "苏剑林博客"
        return self.collections

    def list_collection_items(self, collection_key: str) -> list[dict[str, Any]]:
        assert collection_key == "COLLECTION1"
        return list(self.items)

    def select_collection(self, collection_key: str, collection_name: str) -> None:
        self.selected = (collection_key, collection_name)

    def import_ris(self, ris: str) -> None:
        if self.import_error is not None:
            raise self.import_error
        self.import_count += 1
        title = _ris_value(ris, "TI")
        url = _ris_value(ris, "UR")
        article_id_line = _ris_value(ris, "M2")
        self.items.append(
            {
                "key": "ITEM1",
                "data": {
                    "itemType": "webpage",
                    "title": title,
                    "url": url,
                    "extra": article_id_line,
                    "collections": ["COLLECTION1"],
                },
            }
        )


def test_render_article_ris_preserves_required_metadata() -> None:
    ris = render_article_ris(_article())

    assert "TY  - ELEC" in ris
    assert "TI  - 科学空间浏览指南（FAQ）" in ris
    assert "T2  - Scientific Spaces" in ris
    assert "UR  - https://spaces.ac.cn/archives/6508" in ris
    assert "DA  - 2019-03-26" in ris
    assert f"M2  - {ARTICLE_ID_PREFIX}article-6508" in ris
    assert "KW  - Scientific Spaces" in ris
    assert "KW  - 大数据" in ris


def test_sync_defaults_to_dry_run_without_writing() -> None:
    transport = FakeTransport()

    result = ZoteroArticleSync(transport).sync(_article())

    assert result.status == "dry_run"
    assert transport.selected is None
    assert transport.import_count == 0


def test_sync_creates_webpage_and_reads_it_back() -> None:
    transport = FakeTransport()

    result = ZoteroArticleSync(transport).sync(_article(), write=True)

    assert result.status == "created"
    assert result.item_key_fingerprint is not None
    assert transport.selected == ("COLLECTION1", "苏剑林博客")
    assert transport.import_count == 1
    assert transport.items[0]["data"]["extra"] == (
        f"{ARTICLE_ID_PREFIX}article-6508"
    )


def test_repeated_sync_is_idempotent() -> None:
    transport = FakeTransport()
    sync = ZoteroArticleSync(transport)

    first = sync.sync(_article(), write=True)
    second = sync.sync(_article(), write=True)

    assert first.status == "created"
    assert second.status == "existing"
    assert transport.import_count == 1


def test_sync_rejects_missing_or_duplicate_root_collection() -> None:
    missing = FakeTransport(collections=[])
    duplicate = FakeTransport(
        collections=[
            {
                "key": "COLLECTION1",
                "data": {"name": "苏剑林博客", "parentCollection": False},
            },
            {
                "key": "COLLECTION2",
                "data": {"name": "苏剑林博客", "parentCollection": False},
            },
        ]
    )

    with pytest.raises(ZoteroSyncError, match="not found"):
        ZoteroArticleSync(missing).sync(_article())
    with pytest.raises(ZoteroSyncError, match="not unique"):
        ZoteroArticleSync(duplicate).sync(_article())


def test_collection_resolution_ignores_non_exact_search_results() -> None:
    transport = FakeTransport(
        collections=[
            {
                "key": "OTHER",
                "data": {"name": "苏剑林博客旧目录", "parentCollection": False},
            },
            {
                "key": "COLLECTION1",
                "data": {"name": "苏剑林博客", "parentCollection": False},
            },
        ]
    )

    assert ZoteroArticleSync(transport).sync(_article()).status == "dry_run"


def test_sync_rejects_duplicate_or_conflicting_provenance() -> None:
    matching = {
        "key": "ITEM1",
        "data": {
            "itemType": "webpage",
            "url": _article().url,
            "extra": f"{ARTICLE_ID_PREFIX}{_article().id}",
        },
    }
    duplicate = FakeTransport(items=[matching, {**matching, "key": "ITEM2"}])
    conflict = FakeTransport(
        items=[
            {
                "key": "ITEM1",
                "data": {
                    "itemType": "webpage",
                    "url": _article().url,
                    "extra": f"{ARTICLE_ID_PREFIX}different-id",
                },
            }
        ]
    )

    with pytest.raises(ZoteroSyncError, match="Multiple Zotero items"):
        ZoteroArticleSync(duplicate).sync(_article())
    with pytest.raises(ZoteroSyncError, match="conflicting"):
        ZoteroArticleSync(conflict).sync(_article())


def test_sync_surfaces_connector_failure() -> None:
    transport = FakeTransport()
    transport.import_error = ZoteroSyncError("connector unavailable")

    with pytest.raises(ZoteroSyncError, match="connector unavailable"):
        ZoteroArticleSync(transport).sync(_article(), write=True)


def test_canonicalize_article_url_rejects_non_scientific_spaces_urls() -> None:
    assert canonicalize_article_url(
        "https://spaces.ac.cn/archives/6508/"
    ) == "https://spaces.ac.cn/archives/6508"

    with pytest.raises(ZoteroSyncError, match="Scientific Spaces"):
        canonicalize_article_url("https://example.com/archives/6508")


def _ris_value(ris: str, tag: str) -> str:
    match = re.search(rf"^{re.escape(tag)}  - (.+)$", ris, flags=re.MULTILINE)
    assert match is not None
    return match.group(1)
