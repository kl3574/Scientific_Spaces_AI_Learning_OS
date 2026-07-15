from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.references.models import ReferenceRecord, ZoteroMatchCandidate, canonical_json, sha256_text, stable_id
from app.references.normalization import normalize_arxiv, normalize_doi, normalize_url
from app.zotero.models import ZoteroItem


MATCHER_VERSION = "p3-003-matcher/v1"
_ARXIV_IN_URL = re.compile(r"(?i)arxiv\.org/(?:abs|pdf)/([^?#]+)")


@dataclass(frozen=True)
class MatchSummary:
    candidates: list[ZoteroMatchCandidate]
    automatic_write_count: int = 0
    false_exact_fixture_count: int = 0


def match_reference_records(
    records: Iterable[ReferenceRecord],
    items: Iterable[ZoteroItem] | None,
    *,
    provider_available: bool = True,
    max_candidates_per_reference: int = 20,
) -> MatchSummary:
    item_list = sorted(list(items or []), key=lambda item: item.item_key) if provider_available else []
    output: list[ZoteroMatchCandidate] = []
    for record in sorted(records, key=lambda item: item.reference_id):
        matches = [_compare(record, item) for item in item_list]
        matches = [item for item in matches if item is not None]
        matches.sort(key=lambda item: (-item.match_score, item.zotero_item_key or ""))
        if not matches:
            output.append(_unmatched(record))
        else:
            output.extend(matches[:max_candidates_per_reference])
    return MatchSummary(sorted(output, key=lambda item: item.candidate_id))


def _compare(record: ReferenceRecord, item: ZoteroItem) -> ZoteroMatchCandidate | None:
    item_doi = _item_doi(item)
    item_arxiv, item_arxiv_version = _item_arxiv(item)
    item_url = _item_url(item)
    matched: list[str] = []
    conflicts: list[str] = []

    if record.doi and item_doi:
        (matched if record.doi == item_doi else conflicts).append("doi")
    if record.arxiv_id and item_arxiv:
        if record.arxiv_id == item_arxiv and _version_compatible(record.arxiv_version, item_arxiv_version):
            matched.append("arxiv")
        else:
            conflicts.append("arxiv")
    if record.normalized_url and item_url and record.normalized_url == item_url:
        matched.append("url")

    title_score = _title_similarity(record.normalized_identifier or record.evidence_text, item.title)
    if title_score >= 0.75:
        matched.append("title")

    if not matched:
        return None

    strong = [field for field in matched if field in {"doi", "arxiv"}]
    if strong and not conflicts:
        decision = "exact"
        method = "doi_exact" if "doi" in strong else "arxiv_exact"
        score = 1.0
    elif conflicts:
        decision = "rejected" if not matched else "ambiguous"
        method = "combined"
        score = 0.2
    elif "url" in matched:
        decision = "probable"
        method = "url_normalized"
        score = 0.8
    elif "title" in matched:
        decision = "ambiguous"
        method = "title_creator_year"
        score = min(0.74, title_score)
    else:
        return None

    minimal = {
        "item_key": item.item_key,
        "item_type": item.item_type,
        "title": item.title[:500],
        "doi": item_doi,
        "url": item_url,
        "arxiv_id": item_arxiv,
        "arxiv_version": item_arxiv_version,
    }
    snapshot = sha256_text(canonical_json(minimal))
    identity = f"{record.reference_id}\0{item.item_key}\0{MATCHER_VERSION}"
    return ZoteroMatchCandidate(
        candidate_id=stable_id("zmc", "zotero-candidate-id/v1", identity),
        reference_id=record.reference_id,
        zotero_item_key=item.item_key,
        item_type=item.item_type,
        title=item.title[:500],
        doi=item_doi,
        url=item_url,
        arxiv_id=item_arxiv,
        arxiv_version=item_arxiv_version,
        match_method=method,
        match_score=round(score, 6),
        matched_fields=sorted(set(matched)),
        conflicting_fields=sorted(set(conflicts)),
        provenance={"evidence_ids": record.evidence_ids[:20], "matcher_version": MATCHER_VERSION},
        decision=decision,
        matcher_version=MATCHER_VERSION,
        zotero_snapshot_fingerprint=snapshot,
    )


def _unmatched(record: ReferenceRecord) -> ZoteroMatchCandidate:
    identity = f"{record.reference_id}\0__unmatched__\0{MATCHER_VERSION}"
    return ZoteroMatchCandidate(
        candidate_id=stable_id("zmc", "zotero-candidate-id/v1", identity),
        reference_id=record.reference_id,
        zotero_item_key=None,
        item_type=None,
        title=None,
        doi=None,
        url=None,
        arxiv_id=None,
        arxiv_version=None,
        match_method="combined",
        match_score=0.0,
        matched_fields=[],
        conflicting_fields=[],
        provenance={"evidence_ids": record.evidence_ids[:20], "matcher_version": MATCHER_VERSION},
        decision="unmatched",
        matcher_version=MATCHER_VERSION,
        zotero_snapshot_fingerprint=None,
    )


def _item_doi(item: ZoteroItem) -> str | None:
    if not item.doi:
        return None
    result = normalize_doi(item.doi)
    return result.doi if result.reference_type == "doi" else None


def _item_arxiv(item: ZoteroItem) -> tuple[str | None, int | None]:
    if not item.url:
        return None, None
    match = _ARXIV_IN_URL.search(item.url)
    if match is None:
        return None, None
    result = normalize_arxiv(match.group(1))
    return result.arxiv_id, result.arxiv_version


def _item_url(item: ZoteroItem) -> str | None:
    if not item.url:
        return None
    result = normalize_url(item.url, article_url="https://spaces.ac.cn/")
    return result.normalized_url


def _version_compatible(left: int | None, right: int | None) -> bool:
    return left == right or left is None or right is None


def _title_similarity(left: str, right: str) -> float:
    left_tokens = set(re.findall(r"[\w]+", left.casefold()))
    right_tokens = set(re.findall(r"[\w]+", right.casefold()))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
