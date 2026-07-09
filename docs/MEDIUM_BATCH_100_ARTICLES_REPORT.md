# Medium Batch 100 Articles Report

## Current Status

- P1-005 100-Article Medium Batch Phase: PASS
- Target: cumulative 100 valid Article records
- Result: 100 valid Article records
- Recommendation: A: Ready for full-corpus execution planning gate

This phase extends the P1-004 50-article runtime state to 100 cumulative valid Articles. It is a bounded medium batch, not a full corpus crawl. It did not generate PDFs, did not execute a full 1326-article run, and did not commit runtime corpus data.

## Scope

| Field | Value |
|---|---:|
| target_count | 100 |
| cumulative_valid_count | 100 |
| existing_runtime_count | 50 |
| newly_attempted_count | 53 |
| newly_imported_count | 50 |
| failed_count | 3 |
| skipped_count | 50 |

Scope boundaries:

- Used the approved local seed list only as runtime URL metadata input.
- Did not commit the full 1326-entry seed list.
- Did not visit search pages.
- Did not scrape search engines.
- Did not perform archive ID range probing.
- Did not generate Article PDFs.
- Did not submit `.local_data` runtime Article storage, progress, or validation files.

## Implementation Changes

Changed files:

- `backend/app/corpus/pilot.py`
- `backend/tests/test_full_corpus_pilot.py`
- `scripts/corpus/run_full_corpus_pilot.py`
- `docs/MEDIUM_BATCH_100_ARTICLES_REPORT.md`
- `docs/00_PROJECT_STATE.md`

Behavioral changes:

- Raised the bounded P1 pilot cap from 50 to 100.
- Raised the CLI `--max-limit` default from 50 to 100.
- Preserved `concurrency=1`.
- Preserved the medium-batch delay rule: limits above 30 require `delay_seconds >= 5`.
- Added an explicit `max_consecutive_failures <= 5` guard.
- Added regression coverage for 100-article resume, idempotent rerun, and bounded candidate failure behavior.

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
- Normalized `spaces.ac.cn` and `kexue.fm` archive aliases to `https://spaces.ac.cn/archives/{id}`.
- Rejected non-article paths before browser access.

## Polite Crawling Evidence

Live command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 100 \
  --delay-seconds 5 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Polite crawling settings:

| Setting | Value |
|---|---:|
| concurrency | 1 |
| delay_seconds | 5.0 |
| max_consecutive_failures | 5 |
| bounded retry | enabled by BrowserArticleFetcher |
| elapsed_seconds | 1063.109 |

Source pressure handling:

- The run did not increase concurrency.
- The run did not reduce delay.
- The run did not access search, category, tag, comment, login, attachment, or PDF paths.
- The run stopped after reaching the bounded 100-article target.

## Candidate Handling

Growth run result:

| Metric | Value |
|---|---:|
| attempted_count | 53 |
| newly_imported_count | 50 |
| failed_count | 3 |
| browser_transient_failures | 2 |
| permanent_failures | 1 |
| invalid_candidate_count | 0 |
| invalid_imported_content_count | 0 |
| skipped_non_article_or_legacy_page | 0 |

Failed URL categories:

| Category | Count |
|---|---:|
| browser_transient | 2 |
| permanent_failure | 1 |

Candidate decision:

- Failed candidates were not written to storage.
- Replacement behavior remained bounded: 53 article candidates were attempted to add 50 valid new Articles.
- No invalid candidate or invalid imported content polluted the runtime Article store.

## Import and Validation Metrics

Final cumulative metrics after the growth run:

| Metric | Value |
|---|---:|
| status | PASS |
| target_count | 100 |
| selected_count | 100 |
| imported_count | 100 |
| duplicate_count | 0 |
| invalid_content_count | 0 |
| invalid_candidate_count | 0 |
| invalid_imported_content_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| short_content_count | 0 |
| parser_quality_issues | 0 |

Runtime store check:

| Metric | Value |
|---|---:|
| article_count | 100 |
| unique_url_count | 100 |
| duplicate_count | 0 |

Sample article IDs:

```text
100, 101, 102, 10588, 10592, 10617, 10633, 10648, 10657, 10662,
10667, 10684, 10699, 10711, 10735, 10739, 10757, 10770, 10795,
10815, 10831, 10847, 10862, 10878, 10902, 10907, 10922, 10945,
10958, 10972, 10996, 11006, 11025, 11033, 11056, 11059, 11072,
11111, 11158, 11175, 11196, 11206, 11215, 11221, 11241, 11250,
11260, 11267, 11280, 11285, 11301, 11307, 11320, 11328, 11335,
11340, 11371, 11388, 11390, 11404, 11416, 11428, 11459, 11469,
11480, 11486, 11494, 11530, 11540, 11549, 11563, 11578, 11593,
11605, 11619, 11626, 11647, 11654, 11664, 11673, 11693, 11697,
11710, 11719, 11729, 11736, 11738, 11750, 11760, 11767, 11772,
11777, 11782, 11784, 11787, 11804, 119, 3319, 41, 6508
```

## Resume / Checkpoint Evidence

The run resumed from the existing P1-004 runtime state:

| Metric | Value |
|---|---:|
| existing_runtime_count | 50 |
| newly_imported_count | 50 |
| final_runtime_count | 100 |
| resume_used | true |

Final idempotent rerun command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 100 \
  --delay-seconds 5 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Final idempotent result:

| Metric | Value |
|---|---:|
| status | PASS |
| discovered_url_count | 100 |
| canonical_url_count | 100 |
| selected_count | 100 |
| attempted_count | 0 |
| imported_count | 100 |
| failed_count | 0 |
| skipped_count | 100 |
| elapsed_seconds | 0.103 |

Decision:

- The satisfied 100-article runtime state used local runtime data only.
- No external source refetch was needed on the final idempotent rerun.

## Artifact Policy

Runtime outputs remain ignored under:

```text
.local_data/scientific_spaces/corpus/pilot
```

No PDF, HTML dump, image, browser trace/profile/cache, FAISS index, embedding cache, full seed list, Article corpus JSON, progress file, failed URL log, or validation summary is intended for git.

## Test Evidence

Targeted P1 pilot tests:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_full_corpus_pilot.py
```

Result:

```text
27 passed
```

Backend test suite:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
122 passed, 2 skipped
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
- Seed-list ordering biases which historical articles enter medium batches.
- A permanent candidate failure can occur without storage pollution; future full-corpus planning needs a richer failure ledger outside committed artifacts.
- Runtime Article store remains local-first JSON, which is acceptable for P1 medium batches but should be revisited before durable full-corpus operations.
- The 1326-entry seed list remains an operator-supplied runtime input and must stay outside git.

## Recommendation

A: Ready for full-corpus execution planning gate

Rationale:

- Cumulative valid Articles reached 100.
- Duplicate count is 0.
- Invalid imported content count is 0.
- Content completeness, formula validity, and metadata completeness all passed.
- Final idempotent rerun did not refetch source.
- Runtime artifacts remain ignored and uncommitted.
