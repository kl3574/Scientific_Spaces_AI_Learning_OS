from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from app.storage.article_store import StoredArticle

ARTICLE_ID_PREFIX = "Scientific Spaces Article ID: "
DEFAULT_COLLECTION_NAME = "苏剑林博客"
DEFAULT_ZOTERO_BASE_URL = "http://127.0.0.1:23119"
SCIENTIFIC_SPACES_HOSTS = {"spaces.ac.cn", "www.spaces.ac.cn"}


class ZoteroSyncError(RuntimeError):
    pass


class ZoteroSyncTransport(Protocol):
    def find_collections(self, name: str) -> list[dict[str, Any]]: ...

    def list_collection_items(self, collection_key: str) -> list[dict[str, Any]]: ...

    def select_collection(self, collection_key: str, collection_name: str) -> None: ...

    def import_ris(self, ris: str) -> None: ...


@dataclass(frozen=True)
class ZoteroSyncResult:
    status: str
    article_id: str
    article_url: str
    collection_name: str
    collection_key_fingerprint: str
    item_key_fingerprint: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "status": self.status,
            "article_id": self.article_id,
            "article_url": self.article_url,
            "collection_name": self.collection_name,
            "collection_key_fingerprint": self.collection_key_fingerprint,
            "item_key_fingerprint": self.item_key_fingerprint,
        }


class LocalZoteroSyncTransport:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 5,
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
        items: list[dict[str, Any]] = []
        start = 0
        limit = 100
        quoted_key = urllib.parse.quote(collection_key, safe="")
        while True:
            query = urllib.parse.urlencode({"limit": limit, "start": start})
            payload = self._get_json(
                f"/api/users/0/collections/{quoted_key}/items/top?{query}"
            )
            if not isinstance(payload, list):
                raise ZoteroSyncError("Zotero collection items response is not a list")
            items.extend(payload)
            if len(payload) < limit:
                return items
            start += limit

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
            raise ZoteroSyncError("Unable to select the Zotero target collection") from exc

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

    def _get_json(self, path: str) -> Any:
        return json.loads(self._request(path, method="GET").decode("utf-8"))

    def _post_json(self, path: str, payload: dict[str, Any]) -> Any:
        body = json.dumps(payload).encode("utf-8")
        response = self._request(
            path,
            method="POST",
            body=body,
            content_type="application/json",
        )
        return json.loads(response.decode("utf-8"))

    def _request(
        self,
        path: str,
        *,
        method: str,
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> bytes:
        headers = {"X-Zotero-Connector-API-Version": "3"}
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except Exception as exc:  # noqa: BLE001 - normalize connector and HTTP failures.
            raise ZoteroSyncError(f"Zotero {method} request failed") from exc


class ZoteroArticleSync:
    def __init__(
        self,
        transport: ZoteroSyncTransport,
        *,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        readback_attempts: int = 20,
        readback_delay_seconds: float = 0.1,
    ) -> None:
        self.transport = transport
        self.collection_name = collection_name
        self.readback_attempts = readback_attempts
        self.readback_delay_seconds = readback_delay_seconds

    def sync(self, article: StoredArticle, *, write: bool = False) -> ZoteroSyncResult:
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
            return ZoteroSyncResult(
                status="existing",
                article_id=article.id,
                article_url=canonical_url,
                collection_name=self.collection_name,
                collection_key_fingerprint=collection_fingerprint,
                item_key_fingerprint=_item_fingerprint(existing[0]),
            )
        if not write:
            return ZoteroSyncResult(
                status="dry_run",
                article_id=article.id,
                article_url=canonical_url,
                collection_name=self.collection_name,
                collection_key_fingerprint=collection_fingerprint,
            )

        self.transport.select_collection(collection_key, self.collection_name)
        self.transport.import_ris(render_article_ris(article))
        created = self._wait_for_readback(
            collection_key,
            article_id=article.id,
            canonical_url=canonical_url,
        )
        return ZoteroSyncResult(
            status="created",
            article_id=article.id,
            article_url=canonical_url,
            collection_name=self.collection_name,
            collection_key_fingerprint=collection_fingerprint,
            item_key_fingerprint=_item_fingerprint(created),
        )

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
            key = str(payload.get("key") or data.get("key") or "")
            if key:
                matches.append(key)
        if not matches:
            raise ZoteroSyncError(f"Root Zotero collection not found: {self.collection_name}")
        if len(matches) > 1:
            raise ZoteroSyncError(
                f"Root Zotero collection is not unique: {self.collection_name}"
            )
        return matches[0]

    def _wait_for_readback(
        self,
        collection_key: str,
        *,
        article_id: str,
        canonical_url: str,
    ) -> dict[str, Any]:
        for attempt in range(self.readback_attempts):
            matches = self._matching_items(
                self.transport.list_collection_items(collection_key),
                article_id=article_id,
                canonical_url=canonical_url,
            )
            if len(matches) > 1:
                raise ZoteroSyncError(
                    "Zotero readback found duplicate items for the imported article"
                )
            if matches:
                data = _item_data(matches[0])
                if str(data.get("itemType") or "") != "webpage":
                    raise ZoteroSyncError("Imported Zotero item is not a Web Page")
                if article_id not in _article_ids(data):
                    raise ZoteroSyncError(
                        "Imported Zotero item is missing Scientific Spaces Article ID provenance"
                    )
                return matches[0]
            if attempt + 1 < self.readback_attempts:
                time.sleep(self.readback_delay_seconds)
        raise ZoteroSyncError("Imported Zotero item was not visible during readback")

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


def canonicalize_article_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in SCIENTIFIC_SPACES_HOSTS:
        raise ZoteroSyncError("Article URL is not an HTTPS Scientific Spaces URL")
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(("https", host, path, parsed.query, ""))


def _article_ids(data: dict[str, Any]) -> set[str]:
    extra = str(data.get("extra") or "")
    return {
        line[len(ARTICLE_ID_PREFIX) :].strip()
        for line in extra.splitlines()
        if line.startswith(ARTICLE_ID_PREFIX) and line[len(ARTICLE_ID_PREFIX) :].strip()
    }


def _item_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    return data if isinstance(data, dict) else {}


def _item_fingerprint(payload: dict[str, Any]) -> str | None:
    data = _item_data(payload)
    key = str(payload.get("key") or data.get("key") or "")
    return _fingerprint(key) if key else None


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _single_line(value: str) -> str:
    return " ".join(value.split())
