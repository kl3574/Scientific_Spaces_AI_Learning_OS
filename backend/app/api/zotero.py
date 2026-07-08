from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app.zotero.models import ZoteroRelationType
from app.zotero.provider import get_zotero_provider
from app.zotero.store import ZoteroLinkStore, zotero_store_path

router = APIRouter(prefix="/zotero")


class BibtexExportRequest(BaseModel):
    item_keys: list[str] | None = None


class ZoteroLinkWrite(BaseModel):
    item_key: str = Field(min_length=1)
    relation_type: ZoteroRelationType = "related"
    note: str | None = None


def get_zotero_link_store() -> ZoteroLinkStore:
    return ZoteroLinkStore(zotero_store_path())


@router.get("/status")
def zotero_status() -> dict[str, object]:
    return get_zotero_provider().status().to_dict()


@router.get("/items")
def search_zotero_items(q: str = "", limit: int = 20) -> dict[str, object]:
    items = [item.to_dict() for item in get_zotero_provider().search(q, limit=max(1, min(limit, 100)))]
    return {"items": items, "total": len(items), "query": q}


@router.get("/items/{item_key}")
def get_zotero_item(item_key: str) -> dict[str, object]:
    item = get_zotero_provider().get_item(item_key)
    if item is None:
        return {"item": None}
    return item.to_dict()


@router.post("/export/bibtex")
def export_zotero_bibtex(request: BibtexExportRequest) -> dict[str, object]:
    bibtex = get_zotero_provider().export_bibtex(request.item_keys)
    return {"bibtex": bibtex, "item_count": len(request.item_keys or _entry_keys(bibtex))}


@router.get("/links/{article_id}")
def list_zotero_links(article_id: str) -> dict[str, object]:
    provider = get_zotero_provider()
    links = get_zotero_link_store().list_links(article_id)
    items = []
    for link in links:
        item = provider.get_item(link.zotero_item_key)
        items.append({"link": link.to_dict(), "item": item.to_dict() if item else None})
    return {"items": items, "total": len(items)}


@router.post("/links/{article_id}")
def create_zotero_link(article_id: str, request: ZoteroLinkWrite) -> dict[str, object]:
    link = get_zotero_link_store().upsert_link(
        article_id=article_id,
        zotero_item_key=request.item_key,
        relation_type=request.relation_type,
        note=request.note,
    )
    return link.to_dict()


@router.delete("/links/{article_id}/{item_key}", status_code=204)
def delete_zotero_link(article_id: str, item_key: str) -> Response:
    get_zotero_link_store().delete_link(article_id=article_id, zotero_item_key=item_key)
    return Response(status_code=204)


def _entry_keys(bibtex: str) -> list[str]:
    return [line for line in bibtex.splitlines() if line.startswith("@")]
