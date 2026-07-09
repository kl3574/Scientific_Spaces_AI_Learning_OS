from __future__ import annotations

import json
from pathlib import Path

from app.corpus.inventory import analyze_seed_inventory


def _write_seed(path: Path, articles: list[dict[str, object] | str]) -> Path:
    path.write_text(json.dumps({"articles": articles}, ensure_ascii=False), encoding="utf-8")
    return path


def test_seed_inventory_parses_object_format_and_canonicalizes_urls(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent", "date": "2026-01-02"},
            {"id": "6508", "url": "https://kexue.fm/archives/6508?alias=1", "title": "Alias", "date": "2019-04-01"},
        ],
    )

    summary = analyze_seed_inventory(seed_path, output_dir=tmp_path / ".local_data" / "inventory")

    assert summary.raw_seed_count == 2
    assert summary.parsed_seed_count == 2
    assert summary.canonical_url_count == 2
    assert summary.duplicate_count == 0
    assert summary.rejected_url_count == 0
    assert summary.kexue_alias_count == 1
    assert summary.spaces_canonical_count == 2
    assert summary.year_stats == {"2019": 1, "2026": 1}
    assert summary.inventory_status == "PASS"
    assert summary.sample_first_10_ids == ["11804", "6508"]


def test_seed_inventory_rejects_non_article_urls_and_dedupes_archive_ids(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent", "date": "2026"},
            {"id": "11804", "url": "https://kexue.fm/archives/11804?from=alias", "title": "Duplicate", "date": "2026"},
            {"id": "search", "url": "https://spaces.ac.cn/search?q=attention", "title": "Search", "date": "2026"},
            {"id": "external", "url": "https://example.com/archives/1", "title": "External", "date": "2026"},
        ],
    )

    summary = analyze_seed_inventory(seed_path, output_dir=tmp_path / ".local_data" / "inventory")

    assert summary.raw_seed_count == 4
    assert summary.canonical_url_count == 1
    assert summary.duplicate_count == 1
    assert summary.rejected_url_count == 2
    assert summary.non_article_url_count == 2
    assert summary.inventory_status == "CONDITIONAL"


def test_seed_inventory_counts_missing_title_without_blocking_valid_url(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "100", "url": "https://spaces.ac.cn/archives/100", "title": "", "date": "2009"},
        ],
    )

    summary = analyze_seed_inventory(seed_path, output_dir=tmp_path / ".local_data" / "inventory")

    assert summary.missing_title_count == 1
    assert summary.missing_url_count == 0
    assert summary.rejected_url_count == 0
    assert summary.inventory_status == "PASS"


def test_seed_inventory_rejects_missing_url(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "100", "title": "No URL", "date": "2009"},
        ],
    )

    summary = analyze_seed_inventory(seed_path, output_dir=tmp_path / ".local_data" / "inventory")

    assert summary.missing_url_count == 1
    assert summary.rejected_url_count == 1
    assert summary.canonical_url_count == 0
    assert summary.inventory_status == "BLOCKED"


def test_seed_inventory_computes_cumulative_and_year_partitions(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "A", "date": "2026-01-02"},
            {"id": "11000", "url": "https://spaces.ac.cn/archives/11000", "title": "B", "date": "2024-03-02"},
            {"id": "9000", "url": "https://spaces.ac.cn/archives/9000", "title": "C", "date": "2021-03-02"},
            {"id": "6508", "url": "https://spaces.ac.cn/archives/6508", "title": "D", "date": "2019-03-02"},
            {"id": "100", "url": "https://spaces.ac.cn/archives/100", "title": "E", "date": "2009-03-02"},
        ],
    )

    summary = analyze_seed_inventory(
        seed_path,
        output_dir=tmp_path / ".local_data" / "inventory",
        cumulative_targets=(2, 4, 5),
        completed_count=1,
    )

    assert summary.cumulative_targets == [
        {"target": 2, "already_completed": 1, "new_needed": 1, "candidate_end_index": 2},
        {"target": 4, "already_completed": 1, "new_needed": 3, "candidate_end_index": 4},
        {"target": 5, "already_completed": 1, "new_needed": 4, "candidate_end_index": 5},
    ]
    assert {partition["label"]: partition["count"] for partition in summary.year_based_partitions} == {
        "2026-2024": 2,
        "2023-2021": 1,
        "2020-2018": 1,
        "2017-2015": 0,
        "2014-2012": 0,
        "2011-2009": 1,
    }


def test_seed_inventory_without_year_metadata_is_conditional(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"},
        ],
    )

    summary = analyze_seed_inventory(seed_path, output_dir=tmp_path / ".local_data" / "inventory")

    assert summary.year_stats == {}
    assert summary.unknown_year_count == 1
    assert summary.inventory_status == "CONDITIONAL"


def test_seed_inventory_writes_only_runtime_inventory_summary(tmp_path: Path) -> None:
    output_dir = tmp_path / ".local_data" / "scientific_spaces" / "corpus" / "inventory"
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent", "date": "2026"},
        ],
    )

    summary = analyze_seed_inventory(seed_path, output_dir=output_dir)

    assert ".local_data" in Path(summary.runtime_output_path).parts
    assert (output_dir / "inventory_summary.json").exists()
    assert not (output_dir / "article_store").exists()
    assert json.loads((output_dir / "inventory_summary.json").read_text(encoding="utf-8"))["canonical_url_count"] == 1
