from __future__ import annotations

from app.zotero.models import ZoteroCollection, ZoteroItem, ZoteroStatus


class FakeZoteroProvider:
    def __init__(self) -> None:
        self.items = [
            ZoteroItem(
                item_key="ABCD1234",
                bibtex_key="vaswani_attention_2017",
                title="Attention Is All You Need",
                creators=["Ashish Vaswani", "Noam Shazeer"],
                year="2017",
                item_type="journalArticle",
                publication_title="Advances in Neural Information Processing Systems",
                doi=None,
                url="https://arxiv.org/abs/1706.03762",
                abstract_note="Transformer architecture using attention mechanisms.",
                tags=["attention", "transformer"],
                collections=["deep-learning"],
                updated_at="2017-06-12T00:00:00Z",
            ),
            ZoteroItem(
                item_key="EFGH5678",
                bibtex_key="kay_crb_1993",
                title="Fundamentals of Statistical Signal Processing",
                creators=["Steven M. Kay"],
                year="1993",
                item_type="book",
                publication_title="Prentice Hall",
                doi=None,
                url=None,
                abstract_note="Reference text covering estimation theory and CRB.",
                tags=["estimation", "crb"],
                collections=["signal-processing"],
                updated_at="1993-01-01T00:00:00Z",
            ),
        ]

    def status(self) -> ZoteroStatus:
        return ZoteroStatus(provider="fake", available=True, read_only=True, version="fixture")

    def search(self, query: str, limit: int = 20) -> list[ZoteroItem]:
        normalized = query.strip().lower()
        if not normalized:
            return self.items[:limit]
        results = [
            item
            for item in self.items
            if normalized in item.title.lower()
            or normalized in " ".join(item.creators).lower()
            or normalized in " ".join(item.tags).lower()
            or normalized in (item.abstract_note or "").lower()
        ]
        return results[:limit]

    def get_item(self, item_key: str) -> ZoteroItem | None:
        for item in self.items:
            if item.item_key == item_key:
                return item
        return None

    def export_bibtex(self, item_keys: list[str] | None = None) -> str:
        selected = self.items if item_keys is None else [item for item in self.items if item.item_key in item_keys]
        return "\n\n".join(_bibtex_for(item) for item in selected)

    def list_collections(self) -> list[ZoteroCollection]:
        names = sorted({collection for item in self.items for collection in item.collections})
        return [ZoteroCollection(collection_key=name, name=name) for name in names]

    def list_tags(self) -> list[str]:
        return sorted({tag for item in self.items for tag in item.tags})


def _bibtex_for(item: ZoteroItem) -> str:
    entry_type = "book" if item.item_type == "book" else "article"
    fields = {
        "title": item.title,
        "author": " and ".join(item.creators),
        "year": item.year or "",
        "journal": item.publication_title or "",
        "doi": item.doi or "",
        "url": item.url or "",
    }
    body = ",\n".join(f"  {key} = {{{value}}}" for key, value in fields.items() if value)
    return f"@{entry_type}{{{item.bibtex_key},\n{body}\n}}"
