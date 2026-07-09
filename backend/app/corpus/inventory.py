from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.crawler.canonical import canonicalize_article_url, canonicalize_article_urls, extract_archive_id

DEFAULT_INVENTORY_OUTPUT_DIR = Path(".local_data/scientific_spaces/corpus/inventory")
DEFAULT_CUMULATIVE_TARGETS = (200, 400, 700, 1000, 1326)
DEFAULT_YEAR_PARTITIONS = (
    ("2026-2024", 2024, 2026),
    ("2023-2021", 2021, 2023),
    ("2020-2018", 2018, 2020),
    ("2017-2015", 2015, 2017),
    ("2014-2012", 2012, 2014),
    ("2011-2009", 2009, 2011),
)
YEAR_PATTERN = re.compile(r"\b(20\d{2}|19\d{2})\b")


@dataclass(frozen=True)
class SeedInventoryEntry:
    id: str
    url: str
    title: str
    year: int | None


@dataclass(frozen=True)
class SeedInventorySummary:
    seed_source: str
    raw_seed_count: int
    parsed_seed_count: int
    canonical_url_count: int
    duplicate_count: int
    rejected_url_count: int
    non_article_url_count: int
    missing_id_count: int
    missing_title_count: int
    missing_url_count: int
    kexue_alias_count: int
    spaces_canonical_count: int
    year_stats: dict[str, int]
    unknown_year_count: int
    min_archive_id: int | None
    max_archive_id: int | None
    sample_first_10_ids: list[str]
    sample_last_10_ids: list[str]
    cumulative_targets: list[dict[str, int]]
    year_based_partitions: list[dict[str, int | str | bool]]
    inventory_status: str
    runtime_output_path: str
    rejected_urls: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def analyze_seed_inventory(
    seed_file: Path | str,
    *,
    output_dir: Path | str = DEFAULT_INVENTORY_OUTPUT_DIR,
    cumulative_targets: tuple[int, ...] = DEFAULT_CUMULATIVE_TARGETS,
    completed_count: int = 100,
    write_runtime_output: bool = True,
) -> SeedInventorySummary:
    seed_path = Path(seed_file)
    output_path = Path(output_dir)
    entries = _load_seed_entries(seed_path)
    urls = [entry.url for entry in entries]
    canonical = canonicalize_article_urls(urls)
    archive_ids = [_archive_id_from_canonical(url) for url in canonical.canonical_urls]
    numeric_archive_ids = [int(archive_id) for archive_id in archive_ids if archive_id is not None]
    missing_url_count = sum(1 for entry in entries if not entry.url)
    year_counts = Counter(str(entry.year) for entry in entries if entry.year is not None)
    unknown_year_count = sum(1 for entry in entries if entry.year is None)
    rejected_urls = [asdict(item) for item in canonical.rejected_urls]

    summary = SeedInventorySummary(
        seed_source=str(seed_path),
        raw_seed_count=len(entries),
        parsed_seed_count=len(entries),
        canonical_url_count=canonical.canonical_url_count,
        duplicate_count=canonical.duplicate_count,
        rejected_url_count=canonical.rejected_count,
        non_article_url_count=max(canonical.rejected_count - missing_url_count, 0),
        missing_id_count=sum(1 for entry in entries if not entry.id),
        missing_title_count=sum(1 for entry in entries if not entry.title),
        missing_url_count=missing_url_count,
        kexue_alias_count=sum(1 for entry in entries if _host(entry.url).endswith("kexue.fm")),
        spaces_canonical_count=sum(1 for url in canonical.canonical_urls if _host(url) == "spaces.ac.cn"),
        year_stats=dict(sorted(year_counts.items())),
        unknown_year_count=unknown_year_count,
        min_archive_id=min(numeric_archive_ids) if numeric_archive_ids else None,
        max_archive_id=max(numeric_archive_ids) if numeric_archive_ids else None,
        sample_first_10_ids=[archive_id for archive_id in archive_ids[:10] if archive_id is not None],
        sample_last_10_ids=[archive_id for archive_id in archive_ids[-10:] if archive_id is not None],
        cumulative_targets=_cumulative_targets(cumulative_targets, completed_count=completed_count, canonical_count=canonical.canonical_url_count),
        year_based_partitions=_year_partitions(entries),
        inventory_status=_inventory_status(
            canonical_url_count=canonical.canonical_url_count,
            duplicate_count=canonical.duplicate_count,
            rejected_url_count=canonical.rejected_count,
            unknown_year_count=unknown_year_count,
            parsed_seed_count=len(entries),
        ),
        runtime_output_path=str(output_path),
        rejected_urls=rejected_urls,
    )

    if write_runtime_output:
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "inventory_summary.json").write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return summary


def _load_seed_entries(seed_path: Path) -> list[SeedInventoryEntry]:
    text = seed_path.read_text(encoding="utf-8")
    if seed_path.suffix == ".json":
        raw_items = _items_from_json(json.loads(text))
    else:
        raw_items = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]
    return [_entry_from_item(item) for item in raw_items]


def _items_from_json(data: Any) -> list[Any]:
    if isinstance(data, dict):
        articles = data.get("articles")
        if not isinstance(articles, list):
            raise ValueError("--seed-file JSON object must contain an articles list")
        return articles
    if isinstance(data, list):
        return data
    raise ValueError("--seed-file JSON must contain a URL list or an object with articles")


def _entry_from_item(item: Any) -> SeedInventoryEntry:
    if isinstance(item, str):
        url = item.strip()
        return SeedInventoryEntry(id=extract_archive_id(url) or "", url=url, title="", year=None)
    if not isinstance(item, dict):
        return SeedInventoryEntry(id="", url="", title="", year=None)

    url = _string_value(item.get("url"))
    seed_id = _string_value(item.get("id")) or extract_archive_id(url) or ""
    return SeedInventoryEntry(
        id=seed_id,
        url=url,
        title=_string_value(item.get("title")),
        year=_year_from_item(item),
    )


def _year_from_item(item: dict[str, Any]) -> int | None:
    for key in ("year", "date", "published", "created_at", "updated_at", "time"):
        value = item.get(key)
        if value is None:
            continue
        match = YEAR_PATTERN.search(str(value))
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2100:
                return year
    return None


def _cumulative_targets(targets: tuple[int, ...], *, completed_count: int, canonical_count: int) -> list[dict[str, int]]:
    partitions: list[dict[str, int]] = []
    for target in targets:
        capped_target = min(target, canonical_count)
        already_completed = min(completed_count, capped_target)
        partitions.append(
            {
                "target": target,
                "already_completed": already_completed,
                "new_needed": max(capped_target - already_completed, 0),
                "candidate_end_index": capped_target,
            }
        )
    return partitions


def _year_partitions(entries: list[SeedInventoryEntry]) -> list[dict[str, int | str | bool]]:
    partitions: list[dict[str, int | str | bool]] = []
    for label, start_year, end_year in DEFAULT_YEAR_PARTITIONS:
        count = sum(1 for entry in entries if entry.year is not None and start_year <= entry.year <= end_year)
        partitions.append(
            {
                "label": label,
                "start_year": start_year,
                "end_year": end_year,
                "count": count,
                "legacy_heavy": end_year <= 2015,
            }
        )
    return partitions


def _inventory_status(
    *,
    canonical_url_count: int,
    duplicate_count: int,
    rejected_url_count: int,
    unknown_year_count: int,
    parsed_seed_count: int,
) -> str:
    if canonical_url_count == 0:
        return "BLOCKED"
    if duplicate_count > 0 or rejected_url_count > 0:
        return "CONDITIONAL"
    if parsed_seed_count > 0 and unknown_year_count == parsed_seed_count:
        return "CONDITIONAL"
    return "PASS"


def _host(url: str) -> str:
    return urlsplit(url).netloc.lower()


def _archive_id_from_canonical(url: str) -> str | None:
    canonical_url = canonicalize_article_url(url)
    return extract_archive_id(canonical_url or "")


def _string_value(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""
