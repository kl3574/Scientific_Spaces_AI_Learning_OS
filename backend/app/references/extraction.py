from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, replace

from app.references.models import sha256_text
from app.references.normalization import (
    NormalizationResult,
    normalize_arxiv,
    normalize_citation_text,
    normalize_doi,
    normalize_url,
)
from app.storage.article_store import StoredArticle


EXTRACTION_RULE_VERSION = "p3-003-extractor/v2"
MAX_CANDIDATES_PER_ARTICLE = 512
MAX_RAW_CANDIDATE_LENGTH = 2048
MAX_EVIDENCE_LENGTH = 500

_DOI = re.compile(
    r"(?i)(?:(?:https?://(?:dx\.)?doi\.org/)|(?:doi\s*:\s*))?"
    r"10\.\d{4,9}/[-._;()/:A-Z0-9+@%]+"
)
_DOI_WRAPPER = re.compile(r"(?i)doi\s*:\s*[^\s<>\"'`]+")
_ARXIV = re.compile(
    r"(?i)(?:(?:https?://arxiv\.org/(?:abs|pdf)/)|(?:arxiv\s*:\s*))"
    r"(?:\d{4}\.\d{4,5}|[a-z][a-z0-9.-]*(?:\.[a-z]{2})?/\d{7})(?:v\d+)?(?:\.pdf)?"
)
_ARXIV_WRAPPER = re.compile(r"(?i)arxiv\s*:\s*[^\s<>\"'`]+")
_URL = re.compile(r"(?i)https?://[^\s<>\"'`\]\}]+")
_MARKDOWN_LINK = re.compile(r"!?\[[^\]\n]{0,500}\]\((?P<target>[^)\n]{1,2048})\)")
_UNSAFE_SCHEME = re.compile(r"(?i)(?:file|javascript|data|ftp)\s*:[^\s)<>\"']+")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_REFERENCE_HEADING = re.compile(r"(?i)(?:参考文献|参考资料|引用|references?|bibliography|文献)")
_NUMBERED_CITATION = re.compile(r"^\s*(?:\[\d+\]|\d+[.)])\s+\S+")


@dataclass(frozen=True)
class ExtractedCandidate:
    source_article_id: str
    source_article_title: str
    source_article_url: str
    source_section: str
    source_span_start: int | None
    source_span_end: int | None
    evidence_text: str
    raw_reference: str
    raw_reference_hash: str
    candidate_ordinal: int
    extraction_rule: str
    normalization: NormalizationResult


@dataclass(frozen=True)
class ArticleExtraction:
    article_id: str
    status: str
    candidates: list[ExtractedCandidate]
    detected_candidate_count: int
    overflow_candidate_count: int


@dataclass(frozen=True)
class _PendingCandidate:
    start: int
    end: int
    raw: str
    rule: str
    kind: str


def extract_article_references(
    article: StoredArticle,
    *,
    max_candidates: int = MAX_CANDIDATES_PER_ARTICLE,
) -> ArticleExtraction:
    if max_candidates < 1:
        raise ValueError("max_candidates must be >= 1")
    content = article.content
    headings, code_ranges, reference_ranges = _markdown_context(content)
    pending: list[_PendingCandidate] = []
    occupied_strong: list[tuple[int, int]] = []

    def add_matches(pattern: re.Pattern[str], kind: str, rule: str, *, strong: bool = False) -> None:
        for match in pattern.finditer(content):
            start, end = match.span()
            raw = match.group(0)
            if strong and _overlaps(start, end, occupied_strong):
                continue
            pending.append(_PendingCandidate(start, end, raw, rule, kind))
            if strong:
                occupied_strong.append((start, end))

    add_matches(_DOI, "doi", "doi_candidate", strong=True)
    add_matches(_ARXIV, "arxiv", "arxiv_candidate", strong=True)
    add_matches(_DOI_WRAPPER, "doi", "doi_malformed_candidate")
    add_matches(_ARXIV_WRAPPER, "arxiv", "arxiv_malformed_candidate")

    for match in _MARKDOWN_LINK.finditer(content):
        target = _markdown_link_destination(match.group("target"))
        if not target:
            continue
        start, _target_end = match.span("target")
        relative_offset = match.group("target").find(target)
        start += relative_offset
        end = start + len(target)
        if _overlaps(start, end, occupied_strong):
            continue
        pending.append(_PendingCandidate(start, end, target, "markdown_link", "url"))
        occupied_strong.append((start, end))
    add_matches(_URL, "url", "http_url", strong=True)
    add_matches(_UNSAFE_SCHEME, "url", "unsafe_url", strong=True)

    pending.extend(_citation_text_candidates(content, reference_ranges, occupied_strong))
    pending = _deduplicate_pending(pending)
    detected_count = len(pending)
    overflow_count = max(0, detected_count - max_candidates)
    selected = pending[:max_candidates]
    if overflow_count:
        marker = f"<{overflow_count} candidates over configured limit>"
        selected.append(_PendingCandidate(-1, -1, marker, "candidate_limit", "over_limit"))

    candidates: list[ExtractedCandidate] = []
    heading_offsets = [offset for offset, _heading in headings]
    for ordinal, item in enumerate(selected):
        in_code = item.start >= 0 and _offset_in_ranges(item.start, code_ranges)
        normalization = _normalize(item.kind, item.raw, article.url)
        if in_code:
            normalization = NormalizationResult(
                reference_type="unsupported",
                classification="rejected",
                canonical_key=None,
                display_value=_bounded(item.raw),
                confidence=0.0,
            )
        if len(item.raw) > MAX_RAW_CANDIDATE_LENGTH:
            normalization = NormalizationResult(
                reference_type="unsupported",
                classification="unsupported",
                canonical_key=None,
                display_value=_bounded(item.raw),
                confidence=0.0,
            )
        section = _section_for(item.start, headings, heading_offsets)
        evidence = _evidence_context(content, item.start, item.end) if item.start >= 0 else item.raw
        serialized_raw = normalization.display_value if normalization.classification == "rejected" else item.raw
        candidates.append(
            ExtractedCandidate(
                source_article_id=article.id,
                source_article_title=article.title,
                source_article_url=article.url,
                source_section=section,
                source_span_start=item.start if item.start >= 0 else None,
                source_span_end=item.end if item.end >= 0 else None,
                evidence_text=_bounded(evidence, MAX_EVIDENCE_LENGTH),
                raw_reference=_bounded(serialized_raw or item.raw, MAX_RAW_CANDIDATE_LENGTH),
                raw_reference_hash=sha256_text(item.raw),
                candidate_ordinal=ordinal,
                extraction_rule=item.rule,
                normalization=normalization,
            )
        )
    status = "classified" if candidates else "no_reference"
    return ArticleExtraction(article.id, status, candidates, detected_count, overflow_count)


def _normalize(kind: str, raw: str, article_url: str) -> NormalizationResult:
    if kind == "doi":
        return normalize_doi(raw)
    if kind == "arxiv":
        return normalize_arxiv(raw)
    if kind == "url":
        return normalize_url(raw, article_url=article_url)
    if kind == "citation_text":
        return normalize_citation_text(raw)
    return NormalizationResult("unsupported", "unsupported", None, display_value=_bounded(raw), confidence=0.0)


def _markdown_context(content: str) -> tuple[list[tuple[int, str]], list[tuple[int, int]], list[tuple[int, int]]]:
    headings: list[tuple[int, str]] = []
    code_ranges: list[tuple[int, int]] = []
    reference_ranges: list[tuple[int, int]] = []
    offset = 0
    in_code = False
    code_start = 0
    current_reference_start: int | None = None
    for line in content.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if not in_code:
                in_code = True
                code_start = offset
            else:
                in_code = False
                code_ranges.append((code_start, offset + len(line)))
            offset += len(line)
            continue
        if not in_code:
            match = _HEADING.match(line.rstrip("\r\n"))
            if match:
                heading = match.group(2).strip()
                headings.append((offset, heading))
                if current_reference_start is not None:
                    reference_ranges.append((current_reference_start, offset))
                    current_reference_start = None
                if _REFERENCE_HEADING.search(heading):
                    current_reference_start = offset + len(line)
        offset += len(line)
    if in_code:
        code_ranges.append((code_start, len(content)))
    if current_reference_start is not None:
        reference_ranges.append((current_reference_start, len(content)))
    return headings, code_ranges, reference_ranges


def _citation_text_candidates(
    content: str,
    reference_ranges: list[tuple[int, int]],
    occupied: list[tuple[int, int]],
) -> list[_PendingCandidate]:
    results: list[_PendingCandidate] = []
    offset = 0
    for line in content.splitlines(keepends=True):
        text = line.strip()
        start = offset + (len(line) - len(line.lstrip()))
        end = offset + len(line.rstrip("\r\n"))
        in_reference_section = _offset_in_ranges(start, reference_ranges)
        if text and (in_reference_section or _NUMBERED_CITATION.match(line)) and not _overlaps(start, end, occupied):
            results.append(_PendingCandidate(start, end, text, "citation_line", "citation_text"))
        offset += len(line)
    return results


def _deduplicate_pending(values: list[_PendingCandidate]) -> list[_PendingCandidate]:
    unique: dict[tuple[int, int, str], _PendingCandidate] = {}
    priority = {"doi": 0, "arxiv": 1, "url": 2, "citation_text": 3, "over_limit": 4}
    for value in values:
        key = (value.start, value.end, value.kind)
        unique.setdefault(key, value)
    return sorted(unique.values(), key=lambda item: (item.start, item.end, priority.get(item.kind, 9), item.rule))


def _section_for(start: int, headings: list[tuple[int, str]], heading_offsets: list[int]) -> str:
    if start < 0 or not headings:
        return "__article_root__"
    index = bisect.bisect_right(heading_offsets, start) - 1
    return headings[index][1] if index >= 0 else "__article_root__"


def _evidence_context(content: str, start: int, end: int, radius: int = 120) -> str:
    left = max(0, start - radius)
    right = min(len(content), end + radius)
    return re.sub(r"\s+", " ", content[left:right]).strip()


def _offset_in_ranges(offset: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= offset < end for start, end in ranges)


def _overlaps(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < other_end and end > other_start for other_start, other_end in ranges)


def _bounded(value: str, limit: int = 240) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _markdown_link_destination(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("<") and ">" in stripped:
        return stripped[1 : stripped.index(">")]
    match = re.match(r"^(\S+?)(?:\s+[\"'].*)?$", stripped)
    return match.group(1) if match else stripped
