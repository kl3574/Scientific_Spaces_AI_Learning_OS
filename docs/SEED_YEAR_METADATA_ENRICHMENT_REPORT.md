# Seed Year Metadata Enrichment Report

## Current Status

- P1-009 Seed Year Metadata Enrichment: CONDITIONAL
- Seed URL inventory: PASS
- Year enrichment workflow: IMPLEMENTED
- Reliable per-article year mapping: CONDITIONAL
- Recommendation: C: Need seed/archive source decision

P1-009 implemented an auditable year metadata enrichment workflow, but it cannot mark the year metadata gate as PASS yet. The approved local seed has full URL inventory and global `year_stats`, but per-article seed entries still do not include date/year fields. The recommended high-confidence source is the official archive index section structure, but the live archive index request returned HTTP 403 and no approved offline archive index snapshot is currently available.

This task did not execute a 400-article batch, did not execute full corpus processing, did not fetch article body pages, did not call `BrowserArticleFetcher`, did not generate PDFs, and did not commit full seed or runtime enrichment artifacts.

## Problem Statement

P1-007 found that the approved seed list is strong enough for corpus URL inventory:

- `seed_count=1326`
- `canonical_url_count=1326`
- `duplicate_count=0`
- `rejected_url_count=0`

The blocker is year partitioning. Each seed article entry contains `id`, `url`, and `title`, but not a reliable per-article `date` or `year`. The seed file contains global `year_stats`, which can validate aggregate counts, but cannot by itself map a specific article ID to a specific year.

## Sources Analyzed

### Source A: Seed File Article Entries

Status: INSUFFICIENT

Observed entry keys:

```text
id, title, url
```

Assessment:

- Good for canonical URL inventory.
- Good for archive ID extraction.
- Missing per-article `year` / `date`.
- Cannot directly drive year-based partitions.

### Source B: Seed File Global `year_stats`

Status: VALIDATION SOURCE ONLY

Observed aggregate stats:

| Year | Count |
|---:|---:|
| 2009 | 197 |
| 2010 | 157 |
| 2011 | 83 |
| 2012 | 75 |
| 2013 | 81 |
| 2014 | 83 |
| 2015 | 45 |
| 2016 | 69 |
| 2017 | 53 |
| 2018 | 53 |
| 2019 | 58 |
| 2020 | 63 |
| 2021 | 60 |
| 2022 | 54 |
| 2023 | 52 |
| 2024 | 52 |
| 2025 | 62 |
| 2026 | 29 |

Assessment:

- Useful to validate an independently derived article ID -> year mapping.
- Not sufficient as the only per-article source.
- Archive ID order plus global counts remains a low-confidence heuristic and is not approved for year-based stress batches.

### Source C: Official Archive Index / `content.html`

Status: RECOMMENDED SOURCE, CURRENTLY UNAVAILABLE LIVE

Implemented strategy:

```text
content.html year section
-> archive links under that section
-> article_id -> year mapping
-> high confidence
```

Live access result:

| Field | Value |
|---|---|
| URL | `https://spaces.ac.cn/content.html` |
| request count | 1 |
| article body pages fetched | 0 |
| result | HTTP 403 |
| status impact | CONDITIONAL |

Assessment:

- This is the recommended high-confidence source if an approved archive index snapshot or successful live access is available.
- The current environment could not access the live index.
- No fallback body crawling was attempted.

### Source D: Existing Runtime Article Metadata

Status: PARTIAL VALIDATION ONLY

Observed local runtime Article metadata:

| Metric | Value |
|---|---:|
| runtime Article records | 200 |
| records with date metadata | 200 |

Observed runtime year sample:

| Year | Runtime count |
|---:|---:|
| 2009 | 5 |
| 2015 | 1 |
| 2019 | 1 |
| 2022 | 5 |
| 2023 | 49 |
| 2024 | 48 |
| 2025 | 62 |
| 2026 | 29 |

Assessment:

- Useful for partial validation of already imported Articles.
- Cannot cover all 1326 seed URLs.
- Cannot be the only full-seed enrichment source.

### Source E: Archive ID Order Heuristic

Status: NOT RECOMMENDED AS PRIMARY

Assessment:

- Archive IDs roughly correlate with time, but are not reliable metadata.
- Combining seed order with global `year_stats` would create low-confidence synthetic dates.
- This should not be used for year-based legacy stress planning.

## Recommended Source

Use archive index section parsing as the high-confidence enrichment source.

Recommended next source decision:

1. Provide an approved offline `content.html` archive index snapshot, or
2. Re-run the live archive index fetch only after source access is confirmed, or
3. Continue with cumulative 400-article processing while keeping year-based legacy stress blocked.

## Implementation Changes

Files changed:

- `backend/app/corpus/year_enrichment.py`
- `backend/tests/test_seed_year_enrichment.py`
- `scripts/corpus/run_seed_year_enrichment.py`
- `docs/SEED_YEAR_METADATA_ENRICHMENT_REPORT.md`
- `docs/00_PROJECT_STATE.md`
- `README.md`
- `.gitignore`

CLI command:

```bash
uv run --project backend python scripts/corpus/run_seed_year_enrichment.py \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json \
  --archive-url https://spaces.ac.cn/content.html \
  --output-dir .local_data/scientific_spaces/corpus/inventory \
  --no-live-fetch
```

Optional live archive index command:

```bash
uv run --project backend python scripts/corpus/run_seed_year_enrichment.py \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json \
  --archive-url https://spaces.ac.cn/content.html \
  --output-dir .local_data/scientific_spaces/corpus/inventory \
  --live-archive-index-fetch
```

No-body-fetch guarantee:

- The helper accepts archive index HTML directly or fetches only the configured archive index URL.
- It does not import or call `BrowserArticleFetcher`.
- It does not call parser/converter/storage.
- It does not access `https://spaces.ac.cn/archives/{id}`.
- It writes only ignored runtime metadata under `.local_data`.

## Year Mapping Result

No-live default result:

| Metric | Value |
|---|---:|
| seed_count | 1326 |
| canonical_seed_count | 1326 |
| duplicate_seed_url_count | 0 |
| rejected_seed_url_count | 0 |
| archive_index_fetch_attempted | false |
| archive_index_fetched_live | false |
| mapped_article_count | 0 |
| unknown_year_count | 1326 |
| high_confidence_count | 0 |
| medium_confidence_count | 0 |
| low_confidence_count | 0 |
| year_stats_match | false |
| mismatch_count | 18 |
| status | CONDITIONAL |

Live archive index attempt:

| Metric | Value |
|---|---|
| URL | `https://spaces.ac.cn/content.html` |
| request count | 1 |
| result | HTTP 403 |
| article body fetches | 0 |
| status | CONDITIONAL |

Sample unknown IDs:

```text
11804, 11787, 11784, 11782, 11777, 11772, 11767, 11760, 11750, 11738
```

Sample mapped IDs:

```text
none
```

## Year-Based Partition Counts

Reliable year-based partition counts are not available because high-confidence article ID -> year mapping was not established.

The following aggregate counts are derived from seed global `year_stats` only. They are useful as planning context, but are not approved for selecting individual articles in a year-based stress batch.

| Partition | Seed aggregate count | Reliable mapped count | Legacy risk level | Approved for year stress |
|---|---:|---:|---|---|
| 2026-2024 | 143 | 0 | low | no |
| 2023-2021 | 166 | 0 | low | no |
| 2020-2018 | 174 | 0 | low | no |
| 2017-2015 | 167 | 0 | medium | no |
| 2014-2012 | 239 | 0 | high | no |
| 2011-2009 | 437 | 0 | high | no |

## Artifact Policy

Runtime output path:

```text
.local_data/scientific_spaces/corpus/inventory/year_enrichment.json
```

Artifact policy:

- Runtime output is ignored and must not be committed.
- Full `article_list.json` remains outside git.
- Full enriched seed JSON must not be committed.
- Archive HTML snapshots must not be committed unless explicitly approved as small fixtures.
- No PDF, article body HTML, browser profile, trace, cache, Article corpus store, FAISS index, or embedding cache is part of this task.

## Test Evidence

Targeted P1-009 tests:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_seed_year_enrichment.py
```

Result:

```text
13 passed
```

Backend test suite:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
147 passed, 2 skipped
```

Frontend build:

```bash
npm run build
```

Result:

```text
Compiled successfully
```

RAG/Tutor evaluation:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Result:

```text
Overall: PASS
```

Enrichment command result:

```text
status=CONDITIONAL
seed_count=1326
canonical_seed_count=1326
mapped_article_count=0
unknown_year_count=1326
```

## Risks

- Live archive index access currently returns HTTP 403 in this environment.
- Archive index HTML structure can drift.
- Seed freshness depends on the external approved seed generator.
- Seed titles can be truncated and should not be used as Article content truth.
- Existing runtime Article metadata covers only 200 of 1326 seed entries.
- Older article DOM and legacy content paths still require staged content batches; year metadata alone does not prove import quality.

## Recommendation

C: Need seed/archive source decision

Rationale:

- The enrichment workflow and tests are implemented.
- The approved seed has useful global `year_stats`, but not per-article years.
- The recommended archive index source is currently unavailable live due HTTP 403.
- No approved offline archive index snapshot is available.
- Year-based legacy stress remains blocked.
- Cumulative 400-article processing can continue independently, but it should not be treated as year-based stress coverage.
