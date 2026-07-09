from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from bs4 import BeautifulSoup

from app.corpus.inventory import DEFAULT_INVENTORY_OUTPUT_DIR, DEFAULT_YEAR_PARTITIONS
from app.crawler.canonical import canonicalize_article_url, canonicalize_article_urls, extract_archive_id

DEFAULT_ARCHIVE_INDEX_URL = "https://spaces.ac.cn/content.html"
YEAR_HEADING_PATTERN = re.compile(r"^(20\d{2}|19\d{2})(?:\s*年)?$")
YEAR_PATTERN = re.compile(r"\b(20\d{2}|19\d{2})\b")


@dataclass(frozen=True)
class ArchiveYearMapping:
    article_id: str
    url: str
    year: int
    confidence: str = "high"


@dataclass(frozen=True)
class ArchiveIndexParseSummary:
    mappings: dict[str, ArchiveYearMapping]
    parsed_link_count: int
    duplicate_archive_link_count: int
    rejected_url_count: int


@dataclass(frozen=True)
class SeedYearEnrichmentSummary:
    seed_source: str
    seed_count: int
    canonical_seed_count: int
    duplicate_seed_url_count: int
    rejected_seed_url_count: int
    archive_index_source: str
    archive_index_fetch_attempted: bool
    archive_index_fetched_live: bool
    mapped_article_count: int
    unknown_year_count: int
    year_stats_from_seed: dict[str, int]
    year_stats_from_mapping: dict[str, int]
    year_stats_match: bool
    mismatch_count: int
    missing_from_archive_index_count: int
    extra_in_archive_index_count: int
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int
    sample_mapped_ids: list[str]
    sample_unknown_ids: list[str]
    year_based_partition_counts: list[dict[str, int | str]]
    archive_index_parsed_link_count: int
    archive_index_duplicate_count: int
    archive_index_rejected_url_count: int
    status: str
    runtime_output_path: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def parse_archive_index_year_mapping(
    html: str,
    *,
    base_url: str = DEFAULT_ARCHIVE_INDEX_URL,
) -> ArchiveIndexParseSummary:
    soup = BeautifulSoup(html, "html.parser")
    current_year: int | None = None
    mappings: dict[str, ArchiveYearMapping] = {}
    duplicate_count = 0
    rejected_count = 0
    parsed_count = 0

    for element in soup.find_all(True):
        heading_year = _year_from_heading(element)
        if heading_year is not None:
            current_year = heading_year

        if element.name != "a":
            continue
        href = element.get("href")
        if not isinstance(href, str):
            continue
        canonical_url = _canonicalize_archive_href(href, base_url=base_url)
        if canonical_url is None:
            rejected_count += 1
            continue
        if current_year is None:
            rejected_count += 1
            continue
        parsed_count += 1
        article_id = extract_archive_id(canonical_url)
        if article_id is None:
            rejected_count += 1
            continue
        if article_id in mappings:
            duplicate_count += 1
            continue
        mappings[article_id] = ArchiveYearMapping(
            article_id=article_id,
            url=canonical_url,
            year=current_year,
            confidence="high",
        )

    return ArchiveIndexParseSummary(
        mappings=mappings,
        parsed_link_count=parsed_count,
        duplicate_archive_link_count=duplicate_count,
        rejected_url_count=rejected_count,
    )


def enrich_seed_year_metadata(
    seed_file: Path | str,
    *,
    archive_html: str | None = None,
    archive_url: str = DEFAULT_ARCHIVE_INDEX_URL,
    archive_index_source: str | None = None,
    live_archive_index_fetch: bool = False,
    fetch_archive_index: Callable[[str], str] | None = None,
    output_dir: Path | str = DEFAULT_INVENTORY_OUTPUT_DIR,
    write_runtime_output: bool = True,
) -> SeedYearEnrichmentSummary:
    seed_path = Path(seed_file)
    output_path = Path(output_dir)
    seed_payload = _read_seed_payload(seed_path)
    raw_articles = _seed_articles(seed_payload)
    seed_urls = [_url_from_item(item) for item in raw_articles]
    canonical = canonicalize_article_urls(seed_urls)
    seed_ids = [extract_archive_id(url) for url in canonical.canonical_urls]
    seed_ids = [article_id for article_id in seed_ids if article_id is not None]
    year_stats_from_seed = _seed_global_year_stats(seed_payload)
    fetched_live = False
    live_fetch_attempted = False
    notes: list[str] = []

    if archive_html is None and live_archive_index_fetch:
        live_fetch_attempted = True
        fetcher = fetch_archive_index or fetch_archive_index_html
        try:
            archive_html = fetcher(archive_url)
            fetched_live = True
        except Exception as exc:  # noqa: BLE001 - diagnostics must preserve source-access failures without retrying elsewhere.
            notes.append(f"archive index fetch failed: {exc}")

    if archive_html:
        archive_summary = parse_archive_index_year_mapping(archive_html, base_url=archive_url)
    else:
        archive_summary = ArchiveIndexParseSummary(mappings={}, parsed_link_count=0, duplicate_archive_link_count=0, rejected_url_count=0)
        if live_fetch_attempted:
            notes.append("archive index HTML was unavailable after the live archive index fetch attempt")
        else:
            notes.append("archive index HTML was not provided; live archive index fetch was not enabled")

    article_years: dict[str, int] = {}
    unknown_ids: list[str] = []
    confidence_counts = Counter()

    for article_id in seed_ids:
        mapping = archive_summary.mappings.get(article_id)
        if mapping is None:
            unknown_ids.append(article_id)
            continue
        article_years[article_id] = mapping.year
        confidence_counts[mapping.confidence] += 1

    mapping_stats = dict(sorted(Counter(str(year) for year in article_years.values()).items()))
    mismatch_count = count_year_stats_mismatches(year_stats_from_seed, mapping_stats) if year_stats_from_seed else 0
    year_stats_match = bool(year_stats_from_seed) and mismatch_count == 0
    if not year_stats_from_seed:
        notes.append("seed global year_stats were not available for aggregate validation")
    if mismatch_count:
        notes.append("mapping year statistics differ from seed global year_stats")

    archive_ids = set(archive_summary.mappings)
    seed_id_set = set(seed_ids)
    missing_from_archive = len([article_id for article_id in seed_ids if article_id not in archive_ids])
    extra_in_archive = len(archive_ids - seed_id_set)
    status = _enrichment_status(
        canonical_seed_count=len(seed_ids),
        mapped_article_count=len(article_years),
        high_confidence_count=confidence_counts["high"],
        archive_html_available=archive_html is not None,
        mismatch_count=mismatch_count,
        year_stats_available=bool(year_stats_from_seed),
    )

    summary = SeedYearEnrichmentSummary(
        seed_source=str(seed_path),
        seed_count=len(raw_articles),
        canonical_seed_count=len(seed_ids),
        duplicate_seed_url_count=canonical.duplicate_count,
        rejected_seed_url_count=canonical.rejected_count,
        archive_index_source=archive_index_source or (archive_url if live_fetch_attempted else "not provided"),
        archive_index_fetch_attempted=live_fetch_attempted,
        archive_index_fetched_live=fetched_live,
        mapped_article_count=len(article_years),
        unknown_year_count=len(unknown_ids),
        year_stats_from_seed=year_stats_from_seed,
        year_stats_from_mapping=mapping_stats,
        year_stats_match=year_stats_match,
        mismatch_count=mismatch_count,
        missing_from_archive_index_count=missing_from_archive,
        extra_in_archive_index_count=extra_in_archive,
        high_confidence_count=confidence_counts["high"],
        medium_confidence_count=confidence_counts["medium"],
        low_confidence_count=confidence_counts["low"],
        sample_mapped_ids=[article_id for article_id in seed_ids if article_id in article_years][:10],
        sample_unknown_ids=unknown_ids[:10],
        year_based_partition_counts=_partition_counts(article_years),
        archive_index_parsed_link_count=archive_summary.parsed_link_count,
        archive_index_duplicate_count=archive_summary.duplicate_archive_link_count,
        archive_index_rejected_url_count=archive_summary.rejected_url_count,
        status=status,
        runtime_output_path=str(output_path),
        notes=notes,
    )

    if write_runtime_output:
        output_path.mkdir(parents=True, exist_ok=True)
        runtime_payload = summary.to_dict()
        runtime_payload["article_years"] = dict(sorted(article_years.items(), key=lambda item: int(item[0])))
        (output_path / "year_enrichment.json").write_text(
            json.dumps(runtime_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return summary


def fetch_archive_index_html(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ScientificSpacesAILearningOS/1.0 seed-year-enrichment (+https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(content_type, errors="replace")


def count_year_stats_mismatches(seed_stats: dict[str, int], mapping_stats: dict[str, int]) -> int:
    keys = set(seed_stats) | set(mapping_stats)
    return sum(1 for key in keys if int(seed_stats.get(key, 0)) != int(mapping_stats.get(key, 0)))


def _read_seed_payload(seed_path: Path) -> Any:
    text = seed_path.read_text(encoding="utf-8")
    if seed_path.suffix == ".json":
        return json.loads(text)
    return {"articles": [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]}


def _seed_articles(seed_payload: Any) -> list[Any]:
    if isinstance(seed_payload, dict):
        articles = seed_payload.get("articles")
        if not isinstance(articles, list):
            raise ValueError("--seed-file JSON object must contain an articles list")
        return articles
    if isinstance(seed_payload, list):
        return seed_payload
    raise ValueError("--seed-file JSON must contain a URL list or an object with articles")


def _seed_global_year_stats(seed_payload: Any) -> dict[str, int]:
    if not isinstance(seed_payload, dict):
        return {}
    raw_stats = seed_payload.get("year_stats")
    if not isinstance(raw_stats, dict):
        return {}
    stats: dict[str, int] = {}
    for key, value in raw_stats.items():
        year_match = YEAR_PATTERN.search(str(key))
        if not year_match:
            continue
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        stats[year_match.group(1)] = count
    return dict(sorted(stats.items()))


def _url_from_item(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict) and isinstance(item.get("url"), str):
        return item["url"]
    return ""


def _year_from_heading(element: Any) -> int | None:
    if element.name not in {"h1", "h2", "h3", "h4", "h5", "h6", "dt", "strong"}:
        return None
    text = element.get_text(" ", strip=True)
    match = YEAR_HEADING_PATTERN.match(text)
    if not match:
        return None
    year = int(match.group(1))
    return year if 1900 <= year <= 2100 else None


def _canonicalize_archive_href(href: str, *, base_url: str) -> str | None:
    raw = href.strip()
    if raw.startswith("//"):
        raw = f"https:{raw}"
    elif raw.startswith("/"):
        raw = f"https://spaces.ac.cn{raw}"
    elif raw.startswith("archives/"):
        raw = f"https://spaces.ac.cn/{raw}"
    return canonicalize_article_url(raw)


def _partition_counts(article_years: dict[str, int]) -> list[dict[str, int | str]]:
    partitions: list[dict[str, int | str]] = []
    for label, start_year, end_year in DEFAULT_YEAR_PARTITIONS:
        ids = [article_id for article_id, year in article_years.items() if start_year <= year <= end_year]
        numeric_ids = sorted(int(article_id) for article_id in ids if article_id.isdigit())
        article_count = len(ids)
        partitions.append(
            {
                "label": label,
                "start_year": start_year,
                "end_year": end_year,
                "article_count": article_count,
                "oldest_id": str(numeric_ids[0]) if numeric_ids else "",
                "newest_id": str(numeric_ids[-1]) if numeric_ids else "",
                "legacy_risk_level": _legacy_risk_level(end_year),
                "recommended_stress_sample_count": min(max(article_count, 0), 10) if article_count else 0,
            }
        )
    return partitions


def _legacy_risk_level(end_year: int) -> str:
    if end_year <= 2014:
        return "high"
    if end_year <= 2017:
        return "medium"
    return "low"


def _enrichment_status(
    *,
    canonical_seed_count: int,
    mapped_article_count: int,
    high_confidence_count: int,
    archive_html_available: bool,
    mismatch_count: int,
    year_stats_available: bool,
) -> str:
    if canonical_seed_count == 0:
        return "BLOCKED"
    if not archive_html_available:
        return "CONDITIONAL"
    if mapped_article_count == 0:
        return "BLOCKED"
    coverage = mapped_article_count / canonical_seed_count
    high_confidence_coverage = high_confidence_count / canonical_seed_count
    if coverage >= 0.99 and high_confidence_coverage >= 0.99 and (mismatch_count == 0 or not year_stats_available):
        return "PASS"
    return "CONDITIONAL"
