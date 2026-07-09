# Cumulative 400 Articles Report

## Current Status

- P1-011 Cumulative 400-Article Batch: PASS
- Target: cumulative 400 valid Article records
- Result: 400 valid Article records
- Recommendation: A: Ready for P1-012 Cumulative 700-Article Batch

This phase extends the P1-008 200-article runtime state to 400 cumulative valid Articles. It is a bounded cumulative batch, not a full corpus crawl. It did not generate PDFs, did not execute a 700/1000/1326 article content run, did not make year-based coverage claims, and did not commit runtime corpus data.

## Scope

| Item | Result |
| --- | --- |
| existing_runtime_count | 200 |
| target_count | 400 |
| cumulative_valid_count | 400 |
| new_valid_articles | 200 |
| source seed | `/home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json` |
| seed entries | 1326 |
| full crawl | No |
| PDF batch | No |
| year-based claim | No |

## Implementation Changes

- Raised the bounded P1 pilot cap from 200 to 400.
- Raised the CLI `--max-limit` default from 200 to 400.
- Preserved `concurrency = 1`.
- Preserved `delay_seconds >= 8` for cumulative limits above 100.
- Preserved `max_consecutive_failures <= 5`.
- Added regression coverage for cumulative 400 resume, idempotent rerun, and bounded candidate failure behavior.

## Discovery and Canonicalization

Growth run command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 400 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

| Metric | Growth run |
| --- | --- |
| status | PASS |
| discovered_url_count | 1326 |
| canonical_url_count | 1326 |
| duplicate_count | 0 |
| selected_count | 400 |
| attempted_count | 230 |
| imported_count | 400 |
| skipped_count | 200 |
| rejected_urls | 0 |

The approved local seed file was used only as runtime input. It was not copied into the repository and must remain outside git.

## Polite Crawling Evidence

| Policy | Result |
| --- | --- |
| concurrency | 1 |
| request_delay_seconds | 8.0 |
| bounded retry/backoff | Preserved |
| max_consecutive_failures | 5 |
| elapsed_seconds | 6512.687 |

The run did not lower delay, did not increase concurrency, and did not perform search-page scraping or full-site scanning.

## Candidate Handling

| Metric | Growth run |
| --- | --- |
| failed_count | 30 |
| browser_transient_failures | 22 |
| permanent_failures | 6 |
| skipped_non_article_or_legacy_page | 2 |
| invalid_candidate_count | 2 |
| invalid_imported_content_count | 0 |

Invalid candidates were skipped and replaced. They were not written into Article storage.

Skipped parser-quality candidates:

- `https://spaces.ac.cn/archives/9775`: sidebar/comment/share script/navigation contamination detected
- `https://spaces.ac.cn/archives/9444`: sidebar/comment/share script/navigation contamination detected

## Import and Validation Metrics

| Metric | Growth run |
| --- | --- |
| imported_count | 400 |
| article_count | 400 |
| unique_url_count | 400 |
| duplicate_url_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| short_content_count | 0 |
| invalid_imported_content_count | 0 |

No invalid imported content polluted the runtime Article store.

## Resume / Checkpoint Evidence

Final idempotent rerun used the same command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 400 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

| Metric | Final idempotent rerun |
| --- | --- |
| status | PASS |
| discovered_url_count | 400 |
| canonical_url_count | 400 |
| duplicate_count | 0 |
| selected_count | 400 |
| attempted_count | 0 |
| imported_count | 400 |
| failed_count | 0 |
| skipped_count | 400 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| invalid_imported_content_count | 0 |
| elapsed_seconds | 0.402 |

The satisfied 400-article runtime state used local runtime data only and did not refetch source content.

## Artifact Policy

Runtime files remain under ignored `.local_data/` paths. The seed file remains outside the repository. No PDF, HTML dump, image, browser trace/profile/cache, FAISS index, embedding cache, Article corpus JSON, progress file, failed URL log, validation summary, or local runtime database is intended for git.

## Test Evidence

| Check | Result |
| --- | --- |
| targeted pilot pytest | `36 passed` |
| backend pytest | `151 passed, 2 skipped` |
| frontend build | PASS |
| RAG/Tutor eval | PASS |

RAG/Tutor evaluation summary:

- Retrieval hit@k: 100%
- Citation required pass rate: 100%
- No-source refusal rate: 100%
- Source schema valid rate: 100%
- No fake source rate: 100%
- Overall: PASS

## Risks

- Source access remains dependent on Scientific Spaces availability and browser runtime behavior.
- Transient browser failures occurred during the growth run but did not prevent the target from being reached.
- Special/legacy pages can still appear in candidate sets; quality gates must continue to skip them without storage pollution.
- The seed file remains an operator-supplied local runtime input and must not be committed.
- This batch does not establish year-based coverage or completeness claims.

## Recommendation

A: Ready for P1-012 Cumulative 700-Article Batch

Proceed only through a new bounded staged task with the same artifact policy, idempotent rerun requirement, and polite crawling constraints.
