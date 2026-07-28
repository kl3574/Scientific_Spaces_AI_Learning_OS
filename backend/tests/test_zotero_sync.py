from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from app.storage.article_store import StoredArticle
from app.zotero.sync import (
    ARTICLE_ID_PREFIX,
    ZoteroArticleSync,
    ZoteroPdfMigrationCoordinator,
    ZoteroPdfMigrationTarget,
    ZoteroSyncError,
    canonicalize_article_url,
    inspect_pdf_bytes,
    render_article_item,
    render_article_ris,
)


def _article(
    article_id: str = "article-6508",
    archive_id: str = "6508",
) -> StoredArticle:
    return StoredArticle(
        id=article_id,
        title=f"科学空间文章 {archive_id}",
        url=f"https://spaces.ac.cn/archives/{archive_id}",
        content="这是一段包含中文正文和公式 $x^2+y^2=z^2$ 的文章内容。",
        metadata={
            "date": "2019-03-26",
            "category": "大数据",
            "references": [],
            "images": [],
        },
    )


def _pdf_bytes() -> bytes:
    return b"%PDF-1.7\n" + (b"printed-scientific-article\n" * 80) + b"%%EOF\n"


def _parent(article: StoredArticle, key: str) -> dict[str, Any]:
    return {
        "key": key,
        "data": {
            **render_article_item(article),
            "key": key,
            "collections": ["COLLECTION1"],
        },
    }


def _html_child(parent_key: str, key: str) -> dict[str, Any]:
    return {
        "key": key,
        "data": {
            "key": key,
            "itemType": "attachment",
            "parentItem": parent_key,
            "contentType": "text/html",
        },
    }


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
        self.children_by_parent: dict[str, list[dict[str, Any]]] = {}
        self.attachment_bytes: dict[str, bytes] = {}
        self.selected: tuple[str, str] | None = None
        self.import_count = 0
        self.import_error: ZoteroSyncError | None = None
        self.pdf_import_count = 0
        self.pdf_import_error: ZoteroSyncError | None = None

    def find_collections(self, name: str) -> list[dict[str, Any]]:
        assert name == "苏剑林博客"
        return self.collections

    def list_collection_items(self, collection_key: str) -> list[dict[str, Any]]:
        assert collection_key == "COLLECTION1"
        return list(self.items)

    def list_item_children(self, item_key: str) -> list[dict[str, Any]]:
        return list(self.children_by_parent.get(item_key, []))

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
                "key": f"ITEM{len(self.items) + 1}",
                "data": {
                    "itemType": "webpage",
                    "title": title,
                    "url": url,
                    "extra": article_id_line,
                    "collections": ["COLLECTION1"],
                },
            }
        )

    def save_item_with_pdf(
        self,
        item: dict[str, Any],
        pdf_bytes: bytes,
    ) -> None:
        if self.pdf_import_error is not None:
            raise self.pdf_import_error
        self.pdf_import_count += 1
        parent_key = f"ITEM{len(self.items) + 1}"
        attachment_key = f"PDF{self.pdf_import_count}"
        self.items.append(
            {
                "key": parent_key,
                "data": {
                    **item,
                    "key": parent_key,
                    "collections": ["COLLECTION1"],
                },
            }
        )
        self.children_by_parent[parent_key] = [
            {
                "key": attachment_key,
                "data": {
                    "key": attachment_key,
                    "itemType": "attachment",
                    "parentItem": parent_key,
                    "contentType": "application/pdf",
                    "url": item["url"],
                },
            }
        ]
        self.attachment_bytes[attachment_key] = pdf_bytes

    def read_attachment_bytes(self, attachment_key: str) -> bytes:
        return self.attachment_bytes[attachment_key]


class FakeDesktopBridge:
    def __init__(self, transport: FakeTransport) -> None:
        self.transport = transport
        self.attach_count = 0
        self.trash_count = 0

    def attach_pdf(
        self,
        target: ZoteroPdfMigrationTarget,
        pdf_path: Path,
        title: str,
    ) -> None:
        assert title.endswith(" - Printed PDF")
        self.attach_count += 1
        key = f"MIGRATEDPDF{self.attach_count}"
        self.transport.children_by_parent.setdefault(target.parent_key, []).append(
            {
                "key": key,
                "data": {
                    "key": key,
                    "itemType": "attachment",
                    "parentItem": target.parent_key,
                    "contentType": "application/pdf",
                    "url": target.article_url,
                },
            }
        )
        self.transport.attachment_bytes[key] = pdf_path.read_bytes()

    def trash_html(self, target: ZoteroPdfMigrationTarget) -> None:
        self.trash_count += 1
        self.transport.children_by_parent[target.parent_key] = [
            child
            for child in self.transport.children_by_parent[target.parent_key]
            if child["data"]["contentType"] != "text/html"
        ]


def test_render_article_ris_preserves_required_metadata() -> None:
    ris = render_article_ris(_article())

    assert "TY  - ELEC" in ris
    assert "TI  - 科学空间文章 6508" in ris
    assert "T2  - Scientific Spaces" in ris
    assert "UR  - https://spaces.ac.cn/archives/6508" in ris
    assert "DA  - 2019-03-26" in ris
    assert f"M2  - {ARTICLE_ID_PREFIX}article-6508" in ris
    assert "KW  - Scientific Spaces" in ris
    assert "KW  - 大数据" in ris


def test_render_article_item_preserves_required_metadata() -> None:
    item = render_article_item(_article())

    assert item["itemType"] == "webpage"
    assert item["title"] == "科学空间文章 6508"
    assert item["url"] == "https://spaces.ac.cn/archives/6508"
    assert item["date"] == "2019-03-26"
    assert item["websiteTitle"] == "Scientific Spaces"
    assert item["language"] == "zh-CN"
    assert item["extra"] == f"{ARTICLE_ID_PREFIX}article-6508"


def test_pdf_inspection_accepts_bounded_valid_pdf() -> None:
    inspection = inspect_pdf_bytes(_pdf_bytes())

    assert inspection.file_size_bytes == len(_pdf_bytes())
    assert len(inspection.sha256) == 64


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"%PDF-1.7\n%%EOF\n", "too short"),
        (b"not-a-pdf" * 200 + b"%%EOF", "header"),
        (b"%PDF-1.7\n" + b"x" * 2_000, "end marker"),
    ],
)
def test_pdf_inspection_rejects_invalid_payloads(
    payload: bytes,
    message: str,
) -> None:
    with pytest.raises(ZoteroSyncError, match=message):
        inspect_pdf_bytes(payload)


def test_metadata_sync_defaults_to_dry_run_without_writing() -> None:
    transport = FakeTransport()

    result = ZoteroArticleSync(transport).sync(_article())

    assert result.status == "dry_run"
    assert transport.selected is None
    assert transport.import_count == 0


def test_metadata_sync_creates_webpage_and_is_idempotent() -> None:
    transport = FakeTransport()
    sync = ZoteroArticleSync(transport)

    first = sync.sync(_article(), write=True)
    second = sync.sync(_article(), write=True)

    assert first.status == "created"
    assert second.status == "existing"
    assert transport.selected == ("COLLECTION1", "苏剑林博客")
    assert transport.import_count == 1


def test_pdf_sync_dry_run_does_not_write() -> None:
    transport = FakeTransport()

    result = ZoteroArticleSync(transport).sync(_article(), require_pdf=True)

    assert result.status == "dry_run"
    assert result.pdf_status == "pending"
    assert transport.pdf_import_count == 0


def test_pdf_sync_creates_parent_and_pdf_child() -> None:
    transport = FakeTransport()

    result = ZoteroArticleSync(transport).sync(
        _article(),
        write=True,
        require_pdf=True,
        pdf_bytes=_pdf_bytes(),
    )

    assert result.status == "created"
    assert result.pdf_status == "created"
    assert result.pdf_file_size_bytes == len(_pdf_bytes())
    assert result.pdf_sha256 is not None
    assert result.html_attachment_count == 0
    assert transport.pdf_import_count == 1


def test_repeated_pdf_sync_is_idempotent() -> None:
    transport = FakeTransport()
    sync = ZoteroArticleSync(transport)

    first = sync.sync(
        _article(),
        write=True,
        require_pdf=True,
        pdf_bytes=_pdf_bytes(),
    )
    second = sync.sync(_article(), write=True, require_pdf=True)

    assert first.status == "created"
    assert second.status == "existing"
    assert second.pdf_status == "existing"
    assert transport.pdf_import_count == 1


def test_existing_html_parent_requires_pdf_migration() -> None:
    article = _article()
    transport = FakeTransport(items=[_parent(article, "ITEM1")])
    transport.children_by_parent["ITEM1"] = [_html_child("ITEM1", "HTML1")]

    result = ZoteroArticleSync(transport).sync(article, require_pdf=True)
    target = ZoteroArticleSync(transport).pdf_migration_target(article)

    assert result.status == "migration_required"
    assert result.pdf_status == "pending"
    assert result.html_attachment_count == 1
    assert target.pdf_attachment_count == 0
    assert target.html_attachment_count == 1


def test_batch_migration_attaches_all_pdfs_before_trashing_html(
    tmp_path: Path,
) -> None:
    articles = [
        _article("article-8512", "8512"),
        _article("article-138", "138"),
        _article("article-1850", "1850"),
    ]
    transport = FakeTransport(
        items=[
            _parent(article, f"ITEM{index}")
            for index, article in enumerate(articles, start=1)
        ]
    )
    for index in range(1, 4):
        transport.children_by_parent[f"ITEM{index}"] = [
            _html_child(f"ITEM{index}", f"HTML{index}")
        ]
    bridge = FakeDesktopBridge(transport)
    sync = ZoteroArticleSync(
        transport,
        readback_attempts=1,
        readback_delay_seconds=0,
    )
    coordinator = ZoteroPdfMigrationCoordinator(sync, bridge)
    assignments = []
    for article in articles:
        path = tmp_path / f"{article.id}.pdf"
        path.write_bytes(_pdf_bytes())
        assignments.append((article, path))

    attached = coordinator.attach_existing_pdfs(assignments)
    final = coordinator.replace_html_after_verified_pdfs(articles)

    assert [result.pdf_status for result in attached] == ["existing"] * 3
    assert [result.pdf_status for result in final] == ["existing"] * 3
    assert [result.html_attachment_count for result in final] == [0, 0, 0]
    assert bridge.attach_count == 3
    assert bridge.trash_count == 3


def test_batch_migration_never_trashes_html_when_any_pdf_is_missing() -> None:
    first = _article("article-8512", "8512")
    second = _article("article-138", "138")
    transport = FakeTransport(
        items=[_parent(first, "ITEM1"), _parent(second, "ITEM2")]
    )
    transport.children_by_parent["ITEM1"] = [
        _html_child("ITEM1", "HTML1"),
        {
            "key": "PDF1",
            "data": {
                "itemType": "attachment",
                "parentItem": "ITEM1",
                "contentType": "application/pdf",
            },
        },
    ]
    transport.attachment_bytes["PDF1"] = _pdf_bytes()
    transport.children_by_parent["ITEM2"] = [_html_child("ITEM2", "HTML2")]
    bridge = FakeDesktopBridge(transport)
    coordinator = ZoteroPdfMigrationCoordinator(
        ZoteroArticleSync(
            transport,
            readback_attempts=1,
            readback_delay_seconds=0,
        ),
        bridge,
    )

    with pytest.raises(ZoteroSyncError, match="not visible"):
        coordinator.replace_html_after_verified_pdfs([first, second])

    assert bridge.trash_count == 0
    assert len(transport.children_by_parent["ITEM1"]) == 2
    assert len(transport.children_by_parent["ITEM2"]) == 1


@pytest.mark.parametrize("content_type", ["application/pdf", "text/html"])
def test_pdf_sync_rejects_duplicate_target_attachments(
    content_type: str,
) -> None:
    article = _article()
    transport = FakeTransport(items=[_parent(article, "ITEM1")])
    transport.children_by_parent["ITEM1"] = [
        {
            "key": f"CHILD{index}",
            "data": {
                "itemType": "attachment",
                "parentItem": "ITEM1",
                "contentType": content_type,
            },
        }
        for index in range(2)
    ]
    if content_type == "application/pdf":
        transport.attachment_bytes = {
            "CHILD0": _pdf_bytes(),
            "CHILD1": _pdf_bytes(),
        }

    with pytest.raises(ZoteroSyncError, match="duplicate"):
        ZoteroArticleSync(transport).sync(article, require_pdf=True)


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
    article = _article()
    matching = _parent(article, "ITEM1")
    duplicate = FakeTransport(
        items=[matching, {**matching, "key": "ITEM2"}]
    )
    conflict = FakeTransport(
        items=[
            {
                "key": "ITEM1",
                "data": {
                    "itemType": "webpage",
                    "title": article.title,
                    "url": article.url,
                    "extra": f"{ARTICLE_ID_PREFIX}different-id",
                },
            }
        ]
    )

    with pytest.raises(ZoteroSyncError, match="Multiple Zotero items"):
        ZoteroArticleSync(duplicate).sync(article)
    with pytest.raises(ZoteroSyncError, match="conflicting"):
        ZoteroArticleSync(conflict).sync(article)


def test_sync_surfaces_pdf_connector_failure() -> None:
    transport = FakeTransport()
    transport.pdf_import_error = ZoteroSyncError("connector unavailable")

    with pytest.raises(ZoteroSyncError, match="connector unavailable"):
        ZoteroArticleSync(transport).sync(
            _article(),
            write=True,
            require_pdf=True,
            pdf_bytes=_pdf_bytes(),
        )


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
