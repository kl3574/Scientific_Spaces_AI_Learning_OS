from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.storage.article_store import StoredArticle


SELECTION_RULE_VERSION = "p3-003-selection/v1"
_REQUIRED_TAGS = (
    "doi",
    "arxiv",
    "url",
    "chinese_citation",
    "english_citation",
    "multi_link",
    "no_reference",
    "malformed_like",
    "duplicate_like",
    "long",
    "short",
    "legacy",
    "formula",
    "markdown",
    "code",
)


@dataclass(frozen=True)
class ArticleInventory:
    article_id: str
    date: str
    content_length: int
    formula_marker_count: int
    link_count: int
    reference_marker_count: int
    stable_rank: str
    tags: tuple[str, ...]

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "date": self.date,
            "content_length": self.content_length,
            "formula_marker_count": self.formula_marker_count,
            "link_count": self.link_count,
            "reference_marker_count": self.reference_marker_count,
            "stable_rank": self.stable_rank,
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class PilotSelection:
    selected_articles: list[StoredArticle]
    selected_inventory: list[ArticleInventory]
    inventory_article_count: int
    tag_counts: dict[str, int]
    selection_fingerprint: str
    unselected_reference_output_count: int = 0


def select_pilot_articles(articles: list[StoredArticle], *, sample_size: int = 75) -> PilotSelection:
    if not 50 <= sample_size <= 100:
        raise ValueError("sample_size must be between 50 and 100")
    if len(articles) < sample_size:
        raise ValueError("Article store has fewer Articles than requested sample_size")

    lengths = sorted(len(article.content) for article in articles)
    short_cutoff = lengths[max(0, len(lengths) // 4 - 1)]
    long_cutoff = lengths[min(len(lengths) - 1, (len(lengths) * 3) // 4)]
    inventory = [_inventory(article, short_cutoff=short_cutoff, long_cutoff=long_cutoff) for article in articles]
    by_id = {article.id: article for article in articles}
    selected_ids: set[str] = set()

    for tag in _REQUIRED_TAGS:
        candidates = sorted((item for item in inventory if tag in item.tags), key=lambda item: item.stable_rank)
        for item in candidates:
            selected_for_tag = sum(
                selected.article_id in selected_ids and tag in selected.tags
                for selected in inventory
            )
            if selected_for_tag >= 3:
                break
            selected_ids.add(item.article_id)

    fill_strata = (
        "date_legacy",
        "date_modern",
        "length_q1",
        "length_q2",
        "length_q3",
        "length_q4",
        "formula",
        "multi_link",
        "reference_dense",
    )
    buckets = {
        tag: sorted((item for item in inventory if tag in item.tags), key=lambda item: item.stable_rank)
        for tag in fill_strata
    }
    positions = {tag: 0 for tag in fill_strata}
    while len(selected_ids) < sample_size:
        changed = False
        for tag in fill_strata:
            bucket = buckets[tag]
            while positions[tag] < len(bucket) and bucket[positions[tag]].article_id in selected_ids:
                positions[tag] += 1
            if positions[tag] < len(bucket):
                selected_ids.add(bucket[positions[tag]].article_id)
                positions[tag] += 1
                changed = True
                if len(selected_ids) == sample_size:
                    break
        if not changed:
            break
    if len(selected_ids) < sample_size:
        for item in sorted(inventory, key=lambda value: value.stable_rank):
            selected_ids.add(item.article_id)
            if len(selected_ids) == sample_size:
                break

    selected_inventory = sorted(
        (item for item in inventory if item.article_id in selected_ids),
        key=lambda item: item.article_id,
    )
    selected_articles = [by_id[item.article_id] for item in selected_inventory]
    tag_counts = Counter(tag for item in inventory for tag in item.tags)
    fingerprint_payload = "\n".join(
        f"{item.article_id}\0{item.stable_rank}\0{','.join(item.tags)}" for item in selected_inventory
    )
    selection_fingerprint = hashlib.sha256(
        f"{SELECTION_RULE_VERSION}\0{sample_size}\0{fingerprint_payload}".encode("utf-8")
    ).hexdigest()
    return PilotSelection(
        selected_articles=selected_articles,
        selected_inventory=selected_inventory,
        inventory_article_count=len(inventory),
        tag_counts=dict(sorted(tag_counts.items())),
        selection_fingerprint=selection_fingerprint,
    )


def _inventory(article: StoredArticle, *, short_cutoff: int, long_cutoff: int) -> ArticleInventory:
    content = article.content
    lower = content.casefold()
    date = str(article.metadata.get("date") or "")
    year_match = re.match(r"(19|20)\d{2}", date)
    year = int(year_match.group(0)) if year_match else None
    urls = re.findall(r"(?i)https?://[^\s<>\"']+", content)
    dois = re.findall(r"(?i)10\.\d{4,9}/[^\s<>\"']+", content)
    arxiv = re.findall(r"(?i)(?:arxiv\s*:|arxiv\.org/(?:abs|pdf)/)", content)
    formula_count = content.count("$") + content.count("\\[") + content.count("\\(")
    reference_count = len(dois) + len(arxiv) + len(urls) + lower.count("参考文献") + lower.count("references")
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", content))
    english_count = len(re.findall(r"[A-Za-z]", content))
    tags: set[str] = set()
    if dois:
        tags.add("doi")
    if arxiv:
        tags.add("arxiv")
    if urls:
        tags.add("url")
    if chinese_count and ("参考" in content or "引用" in content):
        tags.add("chinese_citation")
    if english_count and ("reference" in lower or re.search(r"\[[0-9]+\]", content)):
        tags.add("english_citation")
    if len(urls) >= 3:
        tags.add("multi_link")
    if reference_count == 0:
        tags.add("no_reference")
    if re.search(r"(?i)(?:doi|arxiv)\s*:\s*(?!10\.|\d{4}\.|[a-z]+/)", content) or re.search(
        r"(?i)(?:javascript|file|data):", content
    ):
        tags.add("malformed_like")
    if len(urls) != len(set(urls)) or len(dois) != len(set(value.casefold() for value in dois)):
        tags.add("duplicate_like")
    if len(content) <= short_cutoff:
        tags.update(("short", "length_q1"))
    elif len(content) >= long_cutoff:
        tags.update(("long", "length_q4"))
    elif len(content) <= (short_cutoff + long_cutoff) // 2:
        tags.add("length_q2")
    else:
        tags.add("length_q3")
    if year is not None and year <= 2012:
        tags.update(("legacy", "date_legacy"))
    else:
        tags.add("date_modern")
    if formula_count:
        tags.add("formula")
    if re.search(r"(?m)^#{1,6}\s+", content) or re.search(r"\[[^\]]+\]\([^)]+\)", content):
        tags.add("markdown")
    if "```" in content or "~~~" in content:
        tags.add("code")
    if reference_count >= 5:
        tags.add("reference_dense")
    stable_rank = hashlib.sha256(f"{SELECTION_RULE_VERSION}\0{article.id}".encode("utf-8")).hexdigest()
    return ArticleInventory(
        article_id=article.id,
        date=date,
        content_length=len(content),
        formula_marker_count=formula_count,
        link_count=len(urls),
        reference_marker_count=reference_count,
        stable_rank=stable_rank,
        tags=tuple(sorted(tags)),
    )
