from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.corpus.year_enrichment import (
    enrich_seed_year_metadata,
    parse_archive_index_year_mapping,
)


def _write_seed(path: Path, articles: list[dict[str, object]], year_stats: dict[str, int] | None = None) -> Path:
    payload: dict[str, object] = {"articles": articles}
    if year_stats is not None:
        payload["year_stats"] = year_stats
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


ARCHIVE_INDEX_HTML = """
<html>
  <body>
    <h2>2026</h2>
    <ul>
      <li><a href="/archives/11804">Recent article</a></li>
      <li><a href="https://kexue.fm/archives/11787?from=index">Alias article</a></li>
      <li><a href="/search?q=attention">Search page</a></li>
    </ul>
    <h2>2025 年</h2>
    <ul>
      <li><a href="https://spaces.ac.cn/archives/11000#comments">Older article</a></li>
      <li><a href="/archives/11000?duplicate=1">Duplicate older article</a></li>
    </ul>
  </body>
</html>
"""


def test_parse_archive_index_groups_article_links_by_year() -> None:
    parsed = parse_archive_index_year_mapping(ARCHIVE_INDEX_HTML)

    assert parsed.mappings["11804"].year == 2026
    assert parsed.mappings["11787"].year == 2026
    assert parsed.mappings["11000"].year == 2025
    assert parsed.mappings["11000"].confidence == "high"
    assert parsed.duplicate_archive_link_count == 1
    assert parsed.rejected_url_count == 1


def test_year_enrichment_maps_seed_articles_and_matches_seed_year_stats(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"},
            {"id": "11787", "url": "https://spaces.ac.cn/archives/11787", "title": "Alias"},
            {"id": "11000", "url": "https://spaces.ac.cn/archives/11000", "title": "Older"},
        ],
        {"2025": 1, "2026": 2},
    )

    summary = enrich_seed_year_metadata(
        seed_path,
        archive_html=ARCHIVE_INDEX_HTML,
        archive_index_source="fixture",
        output_dir=tmp_path / ".local_data" / "inventory",
    )

    assert summary.status == "PASS"
    assert summary.seed_count == 3
    assert summary.mapped_article_count == 3
    assert summary.unknown_year_count == 0
    assert summary.high_confidence_count == 3
    assert summary.year_stats_from_seed == {"2025": 1, "2026": 2}
    assert summary.year_stats_from_mapping == {"2025": 1, "2026": 2}
    assert summary.year_stats_match is True
    assert summary.mismatch_count == 0
    assert summary.year_based_partition_counts[0]["label"] == "2026-2024"
    assert summary.year_based_partition_counts[0]["article_count"] == 3


def test_year_enrichment_counts_unknown_seed_articles(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"},
            {"id": "99999", "url": "https://spaces.ac.cn/archives/99999", "title": "Missing"},
        ],
        {"2026": 1},
    )

    summary = enrich_seed_year_metadata(
        seed_path,
        archive_html=ARCHIVE_INDEX_HTML,
        archive_index_source="fixture",
        output_dir=tmp_path / ".local_data" / "inventory",
    )

    assert summary.status == "CONDITIONAL"
    assert summary.mapped_article_count == 1
    assert summary.unknown_year_count == 1
    assert summary.sample_unknown_ids == ["99999"]
    assert summary.high_confidence_count == 1


def test_year_enrichment_marks_year_stats_mismatch_conditional(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"},
            {"id": "11787", "url": "https://spaces.ac.cn/archives/11787", "title": "Alias"},
        ],
        {"2025": 2},
    )

    summary = enrich_seed_year_metadata(
        seed_path,
        archive_html=ARCHIVE_INDEX_HTML,
        archive_index_source="fixture",
        output_dir=tmp_path / ".local_data" / "inventory",
    )

    assert summary.status == "CONDITIONAL"
    assert summary.year_stats_from_mapping == {"2026": 2}
    assert summary.year_stats_match is False
    assert summary.mismatch_count == 2


def test_year_enrichment_rejects_non_article_seed_urls(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [
            {"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"},
            {"id": "search", "url": "https://spaces.ac.cn/search?q=attention", "title": "Search"},
        ],
        {"2026": 1},
    )

    summary = enrich_seed_year_metadata(
        seed_path,
        archive_html=ARCHIVE_INDEX_HTML,
        archive_index_source="fixture",
        output_dir=tmp_path / ".local_data" / "inventory",
    )

    assert summary.seed_count == 2
    assert summary.canonical_seed_count == 1
    assert summary.rejected_seed_url_count == 1
    assert summary.status == "PASS"


def test_year_enrichment_without_archive_html_is_conditional_and_does_not_fetch_body(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [{"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"}],
        {"2026": 1},
    )

    def fail_if_called(_url: str) -> str:
        raise AssertionError("live fetch should be disabled by default")

    summary = enrich_seed_year_metadata(
        seed_path,
        output_dir=tmp_path / ".local_data" / "inventory",
        fetch_archive_index=fail_if_called,
    )

    assert summary.status == "CONDITIONAL"
    assert summary.archive_index_fetched_live is False
    assert summary.mapped_article_count == 0
    assert summary.unknown_year_count == 1


def test_year_enrichment_live_fetch_uses_only_archive_index_url(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [{"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"}],
        {"2026": 1},
    )
    calls: list[str] = []

    def fetch_archive_index(url: str) -> str:
        calls.append(url)
        return ARCHIVE_INDEX_HTML

    summary = enrich_seed_year_metadata(
        seed_path,
        archive_url="https://spaces.ac.cn/content.html",
        live_archive_index_fetch=True,
        output_dir=tmp_path / ".local_data" / "inventory",
        fetch_archive_index=fetch_archive_index,
    )

    assert summary.status == "PASS"
    assert calls == ["https://spaces.ac.cn/content.html"]
    assert all("/archives/" not in call for call in calls)
    assert summary.archive_index_fetched_live is True


def test_year_enrichment_live_fetch_failure_is_conditional(tmp_path: Path) -> None:
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [{"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"}],
        {"2026": 1},
    )

    def fetch_archive_index(_url: str) -> str:
        raise TimeoutError("archive index timed out")

    summary = enrich_seed_year_metadata(
        seed_path,
        archive_url="https://spaces.ac.cn/content.html",
        live_archive_index_fetch=True,
        output_dir=tmp_path / ".local_data" / "inventory",
        fetch_archive_index=fetch_archive_index,
    )

    assert summary.status == "CONDITIONAL"
    assert summary.archive_index_source == "https://spaces.ac.cn/content.html"
    assert summary.archive_index_fetch_attempted is True
    assert summary.archive_index_fetched_live is False
    assert summary.mapped_article_count == 0
    assert any("archive index fetch failed" in note for note in summary.notes)
    assert all("not enabled" not in note for note in summary.notes)


def test_year_enrichment_writes_only_runtime_summary(tmp_path: Path) -> None:
    output_dir = tmp_path / ".local_data" / "scientific_spaces" / "corpus" / "inventory"
    seed_path = _write_seed(
        tmp_path / "seed.json",
        [{"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"}],
        {"2026": 1},
    )

    summary = enrich_seed_year_metadata(
        seed_path,
        archive_html=ARCHIVE_INDEX_HTML,
        archive_index_source="fixture",
        output_dir=output_dir,
    )

    output_file = output_dir / "year_enrichment.json"
    assert ".local_data" in Path(summary.runtime_output_path).parts
    assert output_file.exists()
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["mapped_article_count"] == 1
    assert "enriched_articles" not in payload


def test_cumulative_inventory_behavior_remains_unchanged(tmp_path: Path) -> None:
    from app.corpus.inventory import analyze_seed_inventory

    seed_path = _write_seed(
        tmp_path / "seed.json",
        [{"id": "11804", "url": "https://spaces.ac.cn/archives/11804", "title": "Recent"}],
        {"2026": 1},
    )

    summary = analyze_seed_inventory(seed_path, output_dir=tmp_path / ".local_data" / "inventory")

    assert summary.canonical_url_count == 1
    assert summary.cumulative_targets[0]["target"] == 200


@pytest.mark.parametrize(
    ("seed_stats", "mapping_stats", "expected"),
    [
        ({"2026": 2}, {"2026": 2}, 0),
        ({"2026": 1}, {"2026": 2}, 1),
        ({"2025": 2}, {"2026": 2}, 2),
    ],
)
def test_year_stats_mismatch_count(seed_stats: dict[str, int], mapping_stats: dict[str, int], expected: int) -> None:
    from app.corpus.year_enrichment import count_year_stats_mismatches

    assert count_year_stats_mismatches(seed_stats, mapping_stats) == expected
