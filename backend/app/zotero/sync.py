from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.storage.article_store import StoredArticle

ARTICLE_ID_PREFIX = "Scientific Spaces Article ID: "
DEFAULT_COLLECTION_NAME = "苏剑林博客"
DEFAULT_ZOTERO_BASE_URL = "http://127.0.0.1:23119"
SCIENTIFIC_SPACES_HOSTS = {"spaces.ac.cn", "www.spaces.ac.cn"}
MAX_PDF_BYTES = 64 * 1024 * 1024
MIN_PDF_BYTES = 1_024


class ZoteroSyncError(RuntimeError):
    pass


class ZoteroSyncTransport(Protocol):
    def find_collections(self, name: str) -> list[dict[str, Any]]: ...

    def list_collection_items(self, collection_key: str) -> list[dict[str, Any]]: ...

    def list_item_children(self, item_key: str) -> list[dict[str, Any]]: ...

    def select_collection(self, collection_key: str, collection_name: str) -> None: ...

    def import_ris(self, ris: str) -> None: ...

    def save_item_with_pdf(
        self,
        item: dict[str, Any],
        pdf_bytes: bytes,
    ) -> None: ...

    def read_attachment_bytes(self, attachment_key: str) -> bytes: ...


class ZoteroDesktopPdfBridge(Protocol):
    def attach_pdf(
        self,
        target: ZoteroPdfMigrationTarget,
        pdf_path: Path,
        title: str,
    ) -> None: ...

    def trash_html(self, target: ZoteroPdfMigrationTarget) -> None: ...


@dataclass(frozen=True)
class PdfInspection:
    file_size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ZoteroPdfMigrationTarget:
    article_id: str
    article_url: str
    parent_key: str
    pdf_attachment_count: int
    html_attachment_count: int


@dataclass(frozen=True)
class ZoteroSyncResult:
    status: str
    article_id: str
    article_url: str
    collection_name: str
    collection_key_fingerprint: str
    item_key_fingerprint: str | None = None
    pdf_status: str = "not_requested"
    pdf_key_fingerprint: str | None = None
    pdf_file_size_bytes: int | None = None
    pdf_sha256: str | None = None
    html_attachment_count: int = 0

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "status": self.status,
            "article_id": self.article_id,
            "article_url": self.article_url,
            "collection_name": self.collection_name,
            "collection_key_fingerprint": self.collection_key_fingerprint,
            "item_key_fingerprint": self.item_key_fingerprint,
            "pdf_status": self.pdf_status,
            "pdf_key_fingerprint": self.pdf_key_fingerprint,
            "pdf_file_size_bytes": self.pdf_file_size_bytes,
            "pdf_sha256": self.pdf_sha256,
            "html_attachment_count": self.html_attachment_count,
        }


class LocalZoteroSyncTransport:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 10,
        selection_timeout_seconds: float = 5,
        zotero_binary: str | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("SCIENTIFIC_SPACES_ZOTERO_BASE_URL")
            or DEFAULT_ZOTERO_BASE_URL
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.selection_timeout_seconds = selection_timeout_seconds
        self.zotero_binary = (
            zotero_binary
            or os.getenv("SCIENTIFIC_SPACES_ZOTERO_BINARY")
            or "zotero"
        )

    def find_collections(self, name: str) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({"q": name})
        payload = self._get_json(f"/api/users/0/collections?{query}")
        if not isinstance(payload, list):
            raise ZoteroSyncError("Zotero collections response is not a list")
        return payload

    def list_collection_items(self, collection_key: str) -> list[dict[str, Any]]:
        quoted_key = urllib.parse.quote(collection_key, safe="")
        return self._get_paginated_items(
            f"/api/users/0/collections/{quoted_key}/items/top"
        )

    def list_item_children(self, item_key: str) -> list[dict[str, Any]]:
        quoted_key = urllib.parse.quote(item_key, safe="")
        return self._get_paginated_items(
            f"/api/users/0/items/{quoted_key}/children"
        )

    def select_collection(self, collection_key: str, collection_name: str) -> None:
        select_uri = f"zotero://select/library/collections/{collection_key}"
        try:
            subprocess.run(
                [self.zotero_binary, "-url", select_uri],
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ZoteroSyncError(
                "Unable to select the Zotero target collection"
            ) from exc

        deadline = time.monotonic() + self.selection_timeout_seconds
        while time.monotonic() < deadline:
            selected = self._post_json("/connector/getSelectedCollection", {})
            if (
                isinstance(selected, dict)
                and selected.get("name") == collection_name
                and selected.get("editable") is not False
            ):
                return
            time.sleep(0.1)
        raise ZoteroSyncError("Zotero did not confirm the requested target collection")

    def import_ris(self, ris: str) -> None:
        session = uuid.uuid4().hex
        self._request(
            f"/connector/import?{urllib.parse.urlencode({'session': session})}",
            method="POST",
            body=ris.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )

    def save_item_with_pdf(
        self,
        item: dict[str, Any],
        pdf_bytes: bytes,
    ) -> None:
        inspect_pdf_bytes(pdf_bytes)
        session_id = uuid.uuid4().hex
        self._post(
            "/connector/saveItems",
            {
                "sessionID": session_id,
                "uri": item["url"],
                "items": [item],
            },
        )
        metadata = {
            "sessionID": session_id,
            "parentItemID": item["id"],
            "title": f"{item['title']} - Printed PDF",
            "url": item["url"],
        }
        query = urllib.parse.urlencode({"sessionID": session_id})
        self._request(
            f"/connector/saveAttachment?{query}",
            method="POST",
            body=pdf_bytes,
            content_type="application/pdf",
            extra_headers={
                "X-Metadata": json.dumps(metadata, ensure_ascii=True),
            },
        )

    def read_attachment_bytes(self, attachment_key: str) -> bytes:
        quoted_key = urllib.parse.quote(attachment_key, safe="")
        file_url = self._get_text(
            f"/api/users/0/items/{quoted_key}/file/view/url"
        ).strip()
        parsed = urllib.parse.urlsplit(file_url)
        if parsed.scheme != "file":
            raise ZoteroSyncError("Zotero attachment did not resolve to a local file")
        path = Path(urllib.request.url2pathname(urllib.parse.unquote(parsed.path)))
        try:
            size = path.stat().st_size
            if size <= 0 or size > MAX_PDF_BYTES:
                raise ZoteroSyncError("Zotero PDF file size is invalid")
            return path.read_bytes()
        except ZoteroSyncError:
            raise
        except OSError as exc:
            raise ZoteroSyncError(
                "Zotero PDF file is unavailable or unreadable"
            ) from exc

    def _get_paginated_items(self, path: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        start = 0
        limit = 100
        while True:
            query = urllib.parse.urlencode({"limit": limit, "start": start})
            payload = self._get_json(f"{path}?{query}")
            if not isinstance(payload, list):
                raise ZoteroSyncError("Zotero items response is not a list")
            items.extend(payload)
            if len(payload) < limit:
                return items
            start += limit

    def _get_json(self, path: str) -> Any:
        return json.loads(self._get_text(path))

    def _get_text(self, path: str) -> str:
        return self._request(path, method="GET").decode("utf-8")

    def _post_json(self, path: str, payload: dict[str, Any]) -> Any:
        response = self._post(path, payload)
        return json.loads(response.decode("utf-8"))

    def _post(self, path: str, payload: dict[str, Any]) -> bytes:
        return self._request(
            path,
            method="POST",
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )

    def _request(
        self,
        path: str,
        *,
        method: str,
        body: bytes | None = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> bytes:
        headers = {"X-Zotero-Connector-API-Version": "3"}
        if content_type:
            headers["Content-Type"] = content_type
        if extra_headers:
            headers.update(extra_headers)
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise ZoteroSyncError(
                f"Zotero {method} request failed with HTTP {exc.code}"
            ) from exc
        except Exception as exc:  # noqa: BLE001 - normalize local connector failures.
            raise ZoteroSyncError(f"Zotero {method} request failed") from exc


class ZoteroArticleSync:
    def __init__(
        self,
        transport: ZoteroSyncTransport,
        *,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        readback_attempts: int = 30,
        readback_delay_seconds: float = 0.2,
    ) -> None:
        self.transport = transport
        self.collection_name = collection_name
        self.readback_attempts = readback_attempts
        self.readback_delay_seconds = readback_delay_seconds

    def sync(
        self,
        article: StoredArticle,
        *,
        write: bool = False,
        require_pdf: bool = False,
        pdf_bytes: bytes | None = None,
    ) -> ZoteroSyncResult:
        pdf_requested = require_pdf or pdf_bytes is not None
        if pdf_bytes is not None:
            inspect_pdf_bytes(pdf_bytes)

        canonical_url = canonicalize_article_url(article.url)
        collection_key = self._resolve_collection_key()
        collection_fingerprint = _fingerprint(collection_key)
        existing = self._matching_items(
            self.transport.list_collection_items(collection_key),
            article_id=article.id,
            canonical_url=canonical_url,
        )
        if len(existing) > 1:
            raise ZoteroSyncError(
                "Multiple Zotero items match the same Scientific Spaces article"
            )
        if existing:
            self._validate_parent(existing[0], article, canonical_url)
            if pdf_requested:
                target, pdf, inspection = self._pdf_state(
                    existing[0],
                    article,
                    canonical_url,
                )
                if pdf is None:
                    return self._result(
                        status="migration_required",
                        article=article,
                        canonical_url=canonical_url,
                        collection_fingerprint=collection_fingerprint,
                        parent=existing[0],
                        pdf_status="pending",
                        html_attachment_count=target.html_attachment_count,
                    )
                return self._result(
                    status="existing",
                    article=article,
                    canonical_url=canonical_url,
                    collection_fingerprint=collection_fingerprint,
                    parent=existing[0],
                    pdf_status="existing",
                    pdf=pdf,
                    inspection=inspection,
                    html_attachment_count=target.html_attachment_count,
                )
            return self._result(
                status="existing",
                article=article,
                canonical_url=canonical_url,
                collection_fingerprint=collection_fingerprint,
                parent=existing[0],
            )
        if not write:
            return self._result(
                status="dry_run",
                article=article,
                canonical_url=canonical_url,
                collection_fingerprint=collection_fingerprint,
                pdf_status="pending" if pdf_requested else "not_requested",
            )

        self.transport.select_collection(collection_key, self.collection_name)
        if pdf_requested:
            if pdf_bytes is None:
                raise ZoteroSyncError(
                    "PDF bytes are required for a printed-PDF Zotero write"
                )
            self.transport.save_item_with_pdf(
                render_article_item(article),
                pdf_bytes,
            )
        else:
            self.transport.import_ris(render_article_ris(article))

        created = self._wait_for_parent_readback(
            collection_key,
            article=article,
            canonical_url=canonical_url,
        )
        if pdf_requested:
            target, pdf, inspection = self._wait_for_pdf_readback(
                created,
                article,
                canonical_url,
            )
            return self._result(
                status="created",
                article=article,
                canonical_url=canonical_url,
                collection_fingerprint=collection_fingerprint,
                parent=created,
                pdf_status="created",
                pdf=pdf,
                inspection=inspection,
                html_attachment_count=target.html_attachment_count,
            )
        return self._result(
            status="created",
            article=article,
            canonical_url=canonical_url,
            collection_fingerprint=collection_fingerprint,
            parent=created,
        )

    def pdf_migration_target(
        self,
        article: StoredArticle,
    ) -> ZoteroPdfMigrationTarget:
        canonical_url = canonicalize_article_url(article.url)
        collection_key = self._resolve_collection_key()
        matches = self._matching_items(
            self.transport.list_collection_items(collection_key),
            article_id=article.id,
            canonical_url=canonical_url,
        )
        if len(matches) != 1:
            raise ZoteroSyncError(
                "Expected exactly one existing Zotero parent for PDF migration"
            )
        self._validate_parent(matches[0], article, canonical_url)
        target, _, _ = self._pdf_state(matches[0], article, canonical_url)
        return target

    def resolve_collection_key(self) -> str:
        return self._resolve_collection_key()

    def inspect_snapshot(
        self,
        article: StoredArticle,
        *,
        collection_key: str,
        items: list[dict[str, Any]],
        require_pdf: bool = False,
    ) -> ZoteroSyncResult:
        canonical_url = canonicalize_article_url(article.url)
        collection_fingerprint = _fingerprint(collection_key)
        existing = self._matching_items(
            items,
            article_id=article.id,
            canonical_url=canonical_url,
        )
        if len(existing) > 1:
            raise ZoteroSyncError(
                "Multiple Zotero items match the same Scientific Spaces article"
            )
        if not existing:
            return self._result(
                status="dry_run",
                article=article,
                canonical_url=canonical_url,
                collection_fingerprint=collection_fingerprint,
                pdf_status="pending" if require_pdf else "not_requested",
            )

        parent = existing[0]
        self._validate_parent(parent, article, canonical_url)
        if not require_pdf:
            return self._result(
                status="existing",
                article=article,
                canonical_url=canonical_url,
                collection_fingerprint=collection_fingerprint,
                parent=parent,
            )

        target, pdf, inspection = self._pdf_state(
            parent,
            article,
            canonical_url,
        )
        if pdf is None:
            return self._result(
                status="migration_required",
                article=article,
                canonical_url=canonical_url,
                collection_fingerprint=collection_fingerprint,
                parent=parent,
                pdf_status="pending",
                html_attachment_count=target.html_attachment_count,
            )
        return self._result(
            status="existing",
            article=article,
            canonical_url=canonical_url,
            collection_fingerprint=collection_fingerprint,
            parent=parent,
            pdf_status="existing",
            pdf=pdf,
            inspection=inspection,
            html_attachment_count=target.html_attachment_count,
        )

    def wait_for_existing_pdf(
        self,
        article: StoredArticle,
    ) -> ZoteroSyncResult:
        last_result: ZoteroSyncResult | None = None
        for attempt in range(self.readback_attempts):
            last_result = self.sync(article, require_pdf=True)
            if last_result.pdf_status == "existing":
                return last_result
            self._wait_before_next_attempt(attempt)
        raise ZoteroSyncError("Zotero PDF attachment was not visible during readback")

    def wait_for_html_removal(
        self,
        article: StoredArticle,
    ) -> ZoteroSyncResult:
        for attempt in range(self.readback_attempts):
            result = self.sync(article, require_pdf=True)
            if result.pdf_status == "existing" and result.html_attachment_count == 0:
                return result
            self._wait_before_next_attempt(attempt)
        raise ZoteroSyncError("Zotero HTML attachment remained visible after deletion")

    def _resolve_collection_key(self) -> str:
        matches: list[str] = []
        for payload in self.transport.find_collections(self.collection_name):
            data = payload.get("data", {})
            parent = data.get("parentCollection")
            if (
                data.get("name") != self.collection_name
                or parent not in {None, False, ""}
            ):
                continue
            key = _item_key(payload)
            if key:
                matches.append(key)
        if not matches:
            raise ZoteroSyncError(
                f"Root Zotero collection not found: {self.collection_name}"
            )
        if len(matches) > 1:
            raise ZoteroSyncError(
                f"Root Zotero collection is not unique: {self.collection_name}"
            )
        return matches[0]

    def _wait_for_parent_readback(
        self,
        collection_key: str,
        *,
        article: StoredArticle,
        canonical_url: str,
    ) -> dict[str, Any]:
        for attempt in range(self.readback_attempts):
            matches = self._matching_items(
                self.transport.list_collection_items(collection_key),
                article_id=article.id,
                canonical_url=canonical_url,
            )
            if len(matches) > 1:
                raise ZoteroSyncError(
                    "Zotero readback found duplicate items for the imported article"
                )
            if matches:
                self._validate_parent(matches[0], article, canonical_url)
                return matches[0]
            self._wait_before_next_attempt(attempt)
        raise ZoteroSyncError("Imported Zotero item was not visible during readback")

    def _wait_for_pdf_readback(
        self,
        parent: dict[str, Any],
        article: StoredArticle,
        canonical_url: str,
    ) -> tuple[ZoteroPdfMigrationTarget, dict[str, Any], PdfInspection]:
        last_error: ZoteroSyncError | None = None
        for attempt in range(self.readback_attempts):
            try:
                target, pdf, inspection = self._pdf_state(
                    parent,
                    article,
                    canonical_url,
                )
                if pdf is not None and inspection is not None:
                    return target, pdf, inspection
            except ZoteroSyncError as exc:
                last_error = exc
            self._wait_before_next_attempt(attempt)
        if last_error:
            raise last_error
        raise ZoteroSyncError(
            "Imported Zotero PDF attachment was not visible during readback"
        )

    def _pdf_state(
        self,
        parent: dict[str, Any],
        article: StoredArticle,
        canonical_url: str,
    ) -> tuple[
        ZoteroPdfMigrationTarget,
        dict[str, Any] | None,
        PdfInspection | None,
    ]:
        parent_key = _item_key(parent)
        if not parent_key:
            raise ZoteroSyncError("Matching Zotero parent has no item key")
        children = self.transport.list_item_children(parent_key)
        pdfs = _attachments_with_content_type(
            children,
            parent_key=parent_key,
            content_type="application/pdf",
        )
        html = _attachments_with_content_type(
            children,
            parent_key=parent_key,
            content_type="text/html",
        )
        if len(pdfs) > 1:
            raise ZoteroSyncError(
                "Existing Zotero parent has duplicate PDF attachments"
            )
        if len(html) > 1:
            raise ZoteroSyncError(
                "Existing Zotero parent has duplicate HTML attachments"
            )
        target = ZoteroPdfMigrationTarget(
            article_id=article.id,
            article_url=canonical_url,
            parent_key=parent_key,
            pdf_attachment_count=len(pdfs),
            html_attachment_count=len(html),
        )
        if not pdfs:
            return target, None, None
        key = _item_key(pdfs[0])
        if not key:
            raise ZoteroSyncError("Zotero PDF attachment has no item key")
        inspection = inspect_pdf_bytes(
            self.transport.read_attachment_bytes(key)
        )
        return target, pdfs[0], inspection

    @staticmethod
    def _validate_parent(
        parent: dict[str, Any],
        article: StoredArticle,
        canonical_url: str,
    ) -> None:
        data = _item_data(parent)
        if str(data.get("itemType") or "") != "webpage":
            raise ZoteroSyncError("Imported Zotero item is not a Web Page")
        if article.id not in _article_ids(data):
            raise ZoteroSyncError(
                "Imported Zotero item is missing Scientific Spaces Article ID provenance"
            )
        if canonicalize_article_url(str(data.get("url") or "")) != canonical_url:
            raise ZoteroSyncError("Imported Zotero item has the wrong canonical URL")
        if _single_line(str(data.get("title") or "")) != _single_line(article.title):
            raise ZoteroSyncError("Imported Zotero item has the wrong title")

    @staticmethod
    def _matching_items(
        items: list[dict[str, Any]],
        *,
        article_id: str,
        canonical_url: str,
    ) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for item in items:
            data = _item_data(item)
            item_url = str(data.get("url") or "").strip()
            try:
                url_matches = canonicalize_article_url(item_url) == canonical_url
            except ZoteroSyncError:
                url_matches = False
            ids = _article_ids(data)
            id_matches = article_id in ids
            if not (url_matches or id_matches):
                continue
            if url_matches and ids and not id_matches:
                raise ZoteroSyncError(
                    "Zotero URL match has conflicting Scientific Spaces Article ID provenance"
                )
            if id_matches and item_url and not url_matches:
                raise ZoteroSyncError(
                    "Zotero Article ID match has a conflicting canonical URL"
                )
            matches.append(item)
        return matches

    def _wait_before_next_attempt(self, attempt: int) -> None:
        if attempt + 1 < self.readback_attempts and self.readback_delay_seconds:
            time.sleep(self.readback_delay_seconds)

    def _result(
        self,
        *,
        status: str,
        article: StoredArticle,
        canonical_url: str,
        collection_fingerprint: str,
        parent: dict[str, Any] | None = None,
        pdf_status: str = "not_requested",
        pdf: dict[str, Any] | None = None,
        inspection: PdfInspection | None = None,
        html_attachment_count: int = 0,
    ) -> ZoteroSyncResult:
        return ZoteroSyncResult(
            status=status,
            article_id=article.id,
            article_url=canonical_url,
            collection_name=self.collection_name,
            collection_key_fingerprint=collection_fingerprint,
            item_key_fingerprint=_item_fingerprint(parent),
            pdf_status=pdf_status,
            pdf_key_fingerprint=_item_fingerprint(pdf),
            pdf_file_size_bytes=inspection.file_size_bytes if inspection else None,
            pdf_sha256=inspection.sha256 if inspection else None,
            html_attachment_count=html_attachment_count,
        )


class ZoteroPdfMigrationCoordinator:
    def __init__(
        self,
        sync: ZoteroArticleSync,
        bridge: ZoteroDesktopPdfBridge,
    ) -> None:
        self.sync = sync
        self.bridge = bridge

    def attach_existing_pdfs(
        self,
        assignments: list[tuple[StoredArticle, Path]],
    ) -> list[ZoteroSyncResult]:
        prepared: list[tuple[StoredArticle, Path, ZoteroPdfMigrationTarget]] = []
        for article, raw_path in assignments:
            path = raw_path.resolve()
            inspect_pdf_bytes(path.read_bytes())
            target = self.sync.pdf_migration_target(article)
            prepared.append((article, path, target))

        for article, path, target in prepared:
            if target.pdf_attachment_count == 0:
                self.bridge.attach_pdf(
                    target,
                    path,
                    f"{_single_line(article.title)} - Printed PDF",
                )

        return [
            self.sync.wait_for_existing_pdf(article)
            for article, _, _ in prepared
        ]

    def replace_html_after_verified_pdfs(
        self,
        articles: list[StoredArticle],
    ) -> list[ZoteroSyncResult]:
        # Complete all PDF readbacks before the first destructive action.
        verified = [
            self.sync.wait_for_existing_pdf(article)
            for article in articles
        ]
        if any(result.pdf_status != "existing" for result in verified):
            raise ZoteroSyncError(
                "All PDF attachments must pass readback before HTML deletion"
            )

        targets = [
            self.sync.pdf_migration_target(article)
            for article in articles
        ]
        if any(target.pdf_attachment_count != 1 for target in targets):
            raise ZoteroSyncError(
                "All PDF attachments must be unique before HTML deletion"
            )

        for target in targets:
            if target.html_attachment_count == 1:
                self.bridge.trash_html(target)

        return [
            self.sync.wait_for_html_removal(article)
            for article in articles
        ]


def render_article_item(article: StoredArticle) -> dict[str, Any]:
    canonical_url = canonicalize_article_url(article.url)
    category = _single_line(str(article.metadata.get("category") or ""))
    tags = [{"tag": "Scientific Spaces"}]
    if category:
        tags.append({"tag": category})
    return {
        "id": canonical_url,
        "itemType": "webpage",
        "title": _single_line(article.title),
        "url": canonical_url,
        "date": _single_line(str(article.metadata.get("date") or "")),
        "websiteTitle": "Scientific Spaces",
        "language": "zh-CN",
        "extra": f"{ARTICLE_ID_PREFIX}{_single_line(article.id)}",
        "creators": [],
        "tags": tags,
        "attachments": [],
    }


def render_article_ris(article: StoredArticle) -> str:
    canonical_url = canonicalize_article_url(article.url)
    date = _single_line(str(article.metadata.get("date") or ""))
    category = _single_line(str(article.metadata.get("category") or ""))
    lines = [
        "TY  - ELEC",
        f"TI  - {_single_line(article.title)}",
        "T2  - Scientific Spaces",
        f"UR  - {canonical_url}",
        "LA  - zh-CN",
        f"M2  - {ARTICLE_ID_PREFIX}{_single_line(article.id)}",
        "KW  - Scientific Spaces",
    ]
    if date:
        lines.append(f"DA  - {date}")
    if category:
        lines.append(f"KW  - {category}")
    lines.append("ER  -")
    return "\n".join(lines) + "\n"


def inspect_pdf_bytes(pdf_bytes: bytes) -> PdfInspection:
    size = len(pdf_bytes)
    if size < MIN_PDF_BYTES:
        raise ZoteroSyncError("PDF is too short to contain a printed article")
    if size > MAX_PDF_BYTES:
        raise ZoteroSyncError("PDF exceeds the bounded size limit")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ZoteroSyncError("PDF header is invalid")
    if b"%%EOF" not in pdf_bytes[-2_048:]:
        raise ZoteroSyncError("PDF end marker is missing")
    return PdfInspection(
        file_size_bytes=size,
        sha256=hashlib.sha256(pdf_bytes).hexdigest(),
    )


def canonicalize_article_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in SCIENTIFIC_SPACES_HOSTS:
        raise ZoteroSyncError("Article URL is not an HTTPS Scientific Spaces URL")
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(("https", host, path, parsed.query, ""))


def _attachments_with_content_type(
    children: list[dict[str, Any]],
    *,
    parent_key: str,
    content_type: str,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for child in children:
        data = _item_data(child)
        if data.get("itemType") != "attachment":
            continue
        if data.get("parentItem") not in {None, "", parent_key}:
            continue
        if str(data.get("contentType") or "").lower() == content_type:
            matches.append(child)
    return matches


def _article_ids(data: dict[str, Any]) -> set[str]:
    extra = str(data.get("extra") or "")
    return {
        line[len(ARTICLE_ID_PREFIX) :].strip()
        for line in extra.splitlines()
        if line.startswith(ARTICLE_ID_PREFIX)
        and line[len(ARTICLE_ID_PREFIX) :].strip()
    }


def _item_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    return data if isinstance(data, dict) else {}


def _item_key(payload: dict[str, Any]) -> str:
    data = _item_data(payload)
    return str(payload.get("key") or data.get("key") or "")


def _item_fingerprint(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    key = _item_key(payload)
    return _fingerprint(key) if key else None


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _single_line(value: str) -> str:
    return " ".join(value.split())
