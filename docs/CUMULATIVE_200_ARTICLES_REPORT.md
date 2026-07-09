# Cumulative 200 Articles Report

## Current Status

- P1-008 Cumulative 200-Article Batch: PASS
- Target: cumulative 200 valid Article records
- Result: 200 valid Article records
- Recommendation: A: Ready for P1-009 Seed Year Metadata Enrichment

This phase extends the P1-005 100-article runtime state to 200 cumulative valid Articles. It is a bounded cumulative batch, not a full corpus crawl. It did not generate PDFs, did not execute a 400+ article run, and did not commit runtime corpus data.

## Scope

| Field | Value |
|---|---:|
| target_count | 200 |
| cumulative_valid_count | 200 |
| existing_runtime_count | 100 |
| newly_attempted_count | 107 |
| newly_imported_count | 100 |
| failed_count | 7 |
| skipped_count | 100 |

Scope boundaries:

- Used the approved local seed list only as runtime URL metadata input.
- Did not commit the full 1326-entry seed list.
- Did not visit search pages.
- Did not scrape search engines.
- Did not perform archive ID range probing.
- Did not generate Article PDFs.
- Did not run a 400, 700, 1000, or 1326 article content batch.
- Did not submit `.local_data` runtime Article storage, progress, or validation files.

## Implementation Changes

Changed files:

- `backend/app/corpus/pilot.py`
- `backend/tests/test_full_corpus_pilot.py`
- `scripts/corpus/run_full_corpus_pilot.py`
- `docs/CUMULATIVE_200_ARTICLES_REPORT.md`
- `docs/00_PROJECT_STATE.md`
- `README.md`

Behavioral changes:

- Raised the bounded P1 pilot cap from 100 to 200.
- Raised the CLI `--max-limit` default from 100 to 200.
- Preserved `concurrency=1`.
- Preserved the medium-batch delay rule: limits above 30 require `delay_seconds >= 5`.
- Added the cumulative 200 delay rule: limits above 100 require `delay_seconds >= 8`.
- Preserved the explicit `max_consecutive_failures <= 5` guard.
- Added regression coverage for 200-article resume, idempotent rerun, and bounded candidate failure behavior.

## Discovery and Canonicalization

Seed input:

```text
/home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Seed assessment:

| Metric | Value |
|---|---:|
| seed object format | JSON object with `articles` list |
| source article entries | 1326 |
| discovered_url_count | 1326 |
| canonical_url_count | 1326 |
| duplicate_count | 0 |
| rejected_urls | 0 |

Canonicalization policy:

- Accepted only Scientific Spaces archive URLs shaped as `/archives/{numeric_id}`.
- Normalized supported archive URLs to `https://spaces.ac.cn/archives/{id}`.
- Rejected non-article paths before browser access.

## Polite Crawling Evidence

Live command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 200 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Polite crawling settings:

| Setting | Value |
|---|---:|
| concurrency | 1 |
| delay_seconds | 8.0 |
| max_consecutive_failures | 5 |
| bounded retry | enabled by BrowserArticleFetcher |
| elapsed_seconds | 2749.5 |

Source pressure handling:

- The run did not increase concurrency.
- The run did not reduce delay.
- The run did not access search, category, tag, comment, login, attachment, or PDF paths.
- The run stopped after reaching the bounded 200-article target.
- Reducing `delay_seconds` below 8 is not acceptable for this gate because it would violate the P1-008 acceptance boundary and increase source pressure.

## Candidate Handling

Growth run result:

| Metric | Value |
|---|---:|
| attempted_count | 107 |
| newly_imported_count | 100 |
| cumulative_imported_count | 200 |
| failed_count | 7 |
| browser_transient_failures | 5 |
| permanent_failures | 0 |
| invalid_candidate_count | 2 |
| invalid_imported_content_count | 0 |
| skipped_non_article_or_legacy_page | 2 |

Failed URL categories:

| Category | Count |
|---|---:|
| browser_transient | 5 |
| skipped_non_article_or_legacy_page | 2 |

Parser quality issues rejected before storage:

- `https://spaces.ac.cn/archives/9775`: sidebar/comment/share script/navigation contamination detected
- `https://spaces.ac.cn/archives/9444`: sidebar/comment/share script/navigation contamination detected

Candidate decision:

- Failed candidates were not written to storage.
- Invalid candidates were rejected before import.
- No invalid imported content polluted the runtime Article store.
- Replacement behavior remained bounded: 107 article candidates were attempted to add 100 valid new Articles.

## Import and Validation Metrics

Final cumulative metrics after the growth run:

| Metric | Value |
|---|---:|
| status | PASS |
| target_count | 200 |
| selected_count | 200 |
| imported_count | 200 |
| duplicate_count | 0 |
| invalid_content_count | 2 |
| invalid_candidate_count | 2 |
| invalid_imported_content_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| short_content_count | 0 |
| parser_quality_issues | 2 |

Runtime store check:

| Metric | Value |
|---|---:|
| article_count | 200 |
| unique_url_count | 200 |
| duplicate_count | 0 |

Sample article IDs:

```text
100, 10001, 10007, 10040, 10047, 10055, 10085, 10088, 10091, 101,
10114, 10122, 10145, 10162, 10180, 10197, 102, 10226, 10240, 10249,
10266, 10289, 10311, 10320, 10332, 10347, 10352, 10366, 10373, 10394,
10407, 10427, 10474, 10489, 10501, 10519, 10542, 10563, 10567, 10588,
10592, 10617, 10633, 10648, 10657, 10662, 10667, 10684, 10699, 10711,
10735, 10739, 10757, 10770, 10795, 10815, 10831, 10847, 10862, 10869
```

## Resume / Checkpoint Evidence

The run resumed from the existing P1-005 runtime state:

| Metric | Value |
|---|---:|
| existing_runtime_count | 100 |
| newly_imported_count | 100 |
| final_runtime_count | 200 |
| resume_used | true |

Final idempotent rerun command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 200 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Final idempotent result:

| Metric | Value |
|---|---:|
| status | PASS |
| discovered_url_count | 200 |
| canonical_url_count | 200 |
| selected_count | 200 |
| attempted_count | 0 |
| imported_count | 200 |
| failed_count | 0 |
| skipped_count | 200 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| elapsed_seconds | 0.186 |

Decision:

- The satisfied 200-article runtime state used local runtime data only.
- No external source refetch was needed on the final idempotent rerun.
- The runtime store remained duplicate-free.

## Artifact Policy

Runtime outputs remain ignored under:

```text
.local_data/scientific_spaces/corpus/pilot
```

No PDF, HTML dump, image, browser trace/profile/cache, FAISS index, embedding cache, full seed list, Article corpus JSON, progress file, failed URL log, validation summary, or local runtime database is intended for git.

## Test Evidence

Targeted P1 pilot tests:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_full_corpus_pilot.py
```

Result:

```text
32 passed
```

Backend test suite:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
134 passed, 2 skipped
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

## Risks

- External browser access can still fail transiently.
- Seed-list ordering biases which articles enter cumulative batches.
- Parser quality gates can reject candidates with contamination risk; this is acceptable when invalid content is not imported.
- Runtime Article store remains local-first JSON, which is acceptable for staged P1 batches but should be revisited before durable full-corpus operations.
- The 1326-entry seed list remains an operator-supplied runtime input and must stay outside git.
- The current seed lacks date/year metadata, so year-based partitions remain blocked until P1-009 or an equivalent metadata enrichment task.

## Recommendation

A: Ready for P1-009 Seed Year Metadata Enrichment

Rationale:

- Cumulative valid Articles reached 200.
- Duplicate count is 0.
- Invalid imported content count is 0.
- Content completeness, formula validity, and metadata completeness all passed.
- Final idempotent rerun did not refetch source.
- Runtime artifacts remain ignored and uncommitted.
- Year metadata enrichment is the next highest-value step before larger year-aware corpus batches.
