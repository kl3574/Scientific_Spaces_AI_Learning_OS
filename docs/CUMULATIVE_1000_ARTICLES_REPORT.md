# Cumulative 1000 Articles Report

## Current Status

- P1-013 Cumulative 1000-Article Batch: PASS
- Target: cumulative 1000 valid Article records
- Result: 1000 valid Article records
- Recommendation: A: Ready for P1-014 Full Corpus Final Batch Planning

This phase extends the P1-012 700-article runtime state to 1000 cumulative valid Articles. It is a bounded cumulative batch, not a full corpus crawl. It did not execute a 1326 full corpus batch, did not perform year-based legacy stress, did not generate PDFs, did not commit runtime corpus data, and does not make year-based coverage claims.

## Scope

| Item | Result |
| --- | ---: |
| target_count | 1000 |
| existing_runtime_count | 700 |
| cumulative_valid_count | 1000 |
| newly_attempted_count | 308 |
| newly_imported_count | 300 |
| full corpus | No |
| year-based legacy stress | No |
| PDF batch | No |
| artifact commit | No |

Source seed:

```text
/home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

The seed file was used only as operator-local runtime metadata input. It was not copied into the repository and remains outside git.

## Implementation Changes

Files changed:

- `README.md`
- `backend/app/corpus/pilot.py`
- `backend/tests/test_full_corpus_pilot.py`
- `backend/tests/test_seed_list.py`
- `docs/00_PROJECT_STATE.md`
- `docs/CUMULATIVE_1000_ARTICLES_REPORT.md`
- `scripts/corpus/run_full_corpus_pilot.py`

Behavioral changes:

- Raised the bounded P1 pilot cap from 700 to 1000.
- Raised the CLI `--max-limit` default from 700 to 1000.
- Preserved `concurrency = 1`.
- Preserved `delay_seconds >= 8` for cumulative limits above 100.
- Preserved `max_consecutive_failures <= 5`.
- Added regression coverage for cumulative 1000 resume, idempotent rerun, bounded candidate failure behavior, and CLI default max-limit behavior.

Growth command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 1000 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Resume behavior:

- The run resumed from 700 existing valid runtime Articles.
- It attempted only the bounded candidate window needed to reach 1000 valid Articles plus replacements for failed candidates.
- Existing successful runtime state was preserved.

Final idempotent rerun behavior:

- The same command returned `attempted_count=0`.
- The satisfied 1000-article runtime state used local runtime data and did not refetch source content.

Materialization refresh behavior:

- The local Markdown library was refreshed from the local Article store after the 1000 batch.
- The materializer did not access source pages and did not generate PDFs.

## Discovery and Canonicalization

| Metric | Growth run |
| --- | ---: |
| seed source | approved local seed file |
| discovered_url_count | 1326 |
| canonical_url_count | 1326 |
| selected_count | 1000 |
| duplicate_count | 0 |
| rejected URLs | 0 |

Canonicalization accepted only Scientific Spaces archive URLs shaped as `/archives/{numeric_id}` and preserved the final canonical form:

```text
https://spaces.ac.cn/archives/{id}
```

No search pages, category pages, tag pages, comments, attachments, PDFs, or search-engine results were used.

## Polite Crawling Evidence

| Policy | Result |
| --- | ---: |
| concurrency | 1 |
| delay_seconds | 8.0 |
| bounded retry/backoff | enabled |
| max_consecutive_failures | 5 |
| consecutive_failure_peak | 2 |
| elapsed_seconds | 5047.17 |

The run did not lower delay, did not increase concurrency, did not access search pages, and did not perform unbounded archive ID probing.

Transient failure classification:

| Category | Count |
| --- | ---: |
| browser_transient | 0 |
| permanent_failure | 0 |
| skipped_non_article_or_legacy_page | 8 |

## Candidate Handling

| Metric | Growth run |
| --- | ---: |
| newly_attempted_count | 308 |
| newly_imported_count | 300 |
| failed_count | 8 |
| invalid_candidate_count | 8 |
| invalid_imported_content_count | 0 |
| skipped_non_article_or_legacy_page | 8 |

Invalid candidates were skipped and replaced. They were not written into Article storage.

Parser quality issues rejected before storage:

- `https://spaces.ac.cn/archives/9775`: sidebar/comment/share script/navigation contamination detected
- `https://spaces.ac.cn/archives/9444`: sidebar/comment/share script/navigation contamination detected
- `https://spaces.ac.cn/archives/4797`: formula delimiters look unbalanced
- `https://spaces.ac.cn/archives/3936`: formula delimiters look unbalanced
- `https://spaces.ac.cn/archives/3644`: formula delimiters look unbalanced
- `https://spaces.ac.cn/archives/3604`: formula delimiters look unbalanced
- `https://spaces.ac.cn/archives/2709`: content extraction failed: article body not detected
- `https://spaces.ac.cn/archives/1023`: formula delimiters look unbalanced

## Import and Validation Metrics

| Metric | Growth run |
| --- | ---: |
| status | PASS |
| cumulative_valid_count | 1000 |
| imported_count | 1000 |
| failed_count | 8 |
| skipped_count | 700 |
| duplicate_count | 0 |
| invalid_content_count | 8 |
| invalid_candidate_count | 8 |
| invalid_imported_content_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| short_content_count | 0 |
| parser_quality_issues | 8 |

Runtime Article store check:

| Metric | Value |
| --- | ---: |
| article_count | 1000 |
| unique_url_count | 1000 |
| duplicate_count | 0 |
| missing_content_count | 0 |

Sample article IDs:

```text
100, 10001, 10007, 10017, 10040, 10047, 10055, 10077, 1008, 10085,
10088, 10091, 101, 10114, 10122, 10137, 10145, 10162, 10180, 10197,
102, 10226, 10240, 10249, 10266, 1028, 10289, 10311, 10320, 10332,
9762, 9768, 9783, 9787, 979, 9797, 981, 9811, 9812, 9826,
9844, 985, 9855, 9859, 986, 9862, 988, 9881, 9889, 9902,
9907, 9920, 9931, 9938, 994, 9948, 9969, 9978, 998, 9984
```

## Resume / Checkpoint Evidence

| Metric | Value |
| --- | ---: |
| existing_runtime_count | 700 |
| newly_imported_count | 300 |
| resume_used | true |
| source transient handling | successful state preserved |

Final idempotent rerun command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 1000 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Final idempotent rerun result:

| Metric | Value |
| --- | ---: |
| status | PASS |
| discovered_url_count | 1000 |
| canonical_url_count | 1000 |
| selected_count | 1000 |
| attempted_count | 0 |
| imported_count | 1000 |
| failed_count | 0 |
| skipped_count | 1000 |
| duplicate_count | 0 |
| invalid_imported_content_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| consecutive_failure_peak | 0 |
| elapsed_seconds | 0.757 |

The final rerun used local runtime data only and did not refetch source content.

## Local Corpus Materialization Refresh

Command:

```bash
uv run --project backend python scripts/corpus/materialize_local_library.py \
  --article-store-path .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/corpus/local_library
```

Result:

| Metric | Value |
| --- | ---: |
| input Article store path | `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json` |
| article_count | 1000 |
| exported_markdown_count | 1000 |
| missing_content_count | 0 |
| output path | `.local_data/scientific_spaces/corpus/local_library` |
| no source fetch | true |

Generated ignored runtime files:

```text
.local_data/scientific_spaces/corpus/local_library/articles/*.md
.local_data/scientific_spaces/corpus/local_library/index/articles_index.json
.local_data/scientific_spaces/corpus/local_library/index/articles_index.csv
.local_data/scientific_spaces/corpus/local_library/reports/local_library_summary.json
```

## Artifact Policy

Runtime output path:

```text
.local_data/scientific_spaces/corpus/pilot
```

Local library output path:

```text
.local_data/scientific_spaces/corpus/local_library
```

Artifact check:

- `.local_data/` remains ignored.
- Runtime Article store was not committed.
- Local library Markdown/JSON/CSV outputs were not committed.
- Full `article_list.json` was not committed.
- No PDF, HTML dump, image, browser trace/profile/cache, FAISS index, embedding cache, DB file, `.env`, or `node_modules` was committed.
- Artifact grep matched only existing tracked test HTML fixtures and the committed materialization script, not runtime artifacts.

## Test Evidence

Targeted pilot/seed tests:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_full_corpus_pilot.py backend/tests/test_seed_list.py
```

Result:

```text
48 passed
```

Backend:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
166 passed, 2 skipped
```

Frontend:

```bash
npm run build
```

Result:

```text
PASS
```

RAG/Tutor eval:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Result:

```text
Overall: PASS
```

Live command result:

```text
status=PASS, attempted_count=308, imported_count=1000, failed_count=8
```

Final idempotent rerun result:

```text
status=PASS, attempted_count=0, imported_count=1000
```

Materialization command result:

```text
exported_markdown_count=1000, missing_content_count=0, no_source_fetch=true
```

## Risks

- Source volatility can still affect later batches.
- The approved seed lacks per-article year metadata, so this report makes no year-based coverage claim.
- Year-based legacy stress remains blocked pending a reliable year metadata source.
- Older articles may still be under-sampled by year until the final stage is planned.
- Parser drift remains possible as the candidate set reaches older or special pages.
- Browser runtime drift can affect later Playwright acquisition.
- Scaling from 1000 to 1326 should be planned as a separate final batch.
- The local Markdown library now contains 1000 ignored runtime files, so disk usage and review ergonomics should be considered before the next expansion.

## Recommendation

A: Ready for P1-014 Full Corpus Final Batch Planning

Do not directly execute the 1326 final batch from this report. The 1000 -> 1326 step should start with a final-batch planning gate that reviews remaining candidates, observed failure categories, estimated runtime, legacy risks, and local library size growth.
