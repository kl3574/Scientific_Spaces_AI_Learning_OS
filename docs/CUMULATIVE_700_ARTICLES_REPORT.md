# Cumulative 700 Articles Report

## Current Status

- P1-012 Cumulative 700-Article Batch: PASS
- Target: cumulative 700 valid Article records
- Result: 700 valid Article records
- Recommendation: A: Ready for P1-013 Cumulative 1000-Article Batch

This phase extends the P1-011 400-article runtime state to 700 cumulative valid Articles. It is a bounded cumulative batch, not a full corpus crawl. It did not execute a 1000/1326 batch, did not perform year-based legacy stress, did not generate PDFs, did not commit runtime corpus data, and does not make year-based coverage claims.

## Scope

| Item | Result |
| --- | --- |
| target_count | 700 |
| existing_runtime_count | 400 |
| cumulative_valid_count | 700 |
| newly_imported_count | 300 |
| source seed | `/home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json` |
| full corpus | No |
| year-based legacy stress | No |
| PDF batch | No |
| artifact commit | No |

## Implementation Changes

Files changed:

- `README.md`
- `backend/app/corpus/pilot.py`
- `backend/tests/test_full_corpus_pilot.py`
- `docs/00_PROJECT_STATE.md`
- `docs/CUMULATIVE_700_ARTICLES_REPORT.md`
- `scripts/corpus/run_full_corpus_pilot.py`

Behavioral changes:

- Raised the bounded P1 pilot cap from 400 to 700.
- Raised the CLI `--max-limit` default from 400 to 700.
- Preserved `concurrency = 1`.
- Preserved `delay_seconds >= 8` for cumulative limits above 100.
- Preserved `max_consecutive_failures <= 5`.
- Added `max_consecutive_failures` and `consecutive_failure_peak` to the pilot summary.
- Added regression coverage for cumulative 700 resume, idempotent rerun, and bounded candidate failure behavior.

CLI used:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 700 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Resume behavior:

- The run resumed from 400 existing valid runtime Articles.
- It attempted only the candidate window needed to reach 700 valid Articles plus bounded replacements for failed candidates.
- The final idempotent rerun used local runtime data and did not refetch source content.

## Discovery and Canonicalization

| Metric | Growth run |
| --- | ---: |
| discovered_url_count | 1326 |
| canonical_url_count | 1326 |
| selected_count | 700 |
| duplicate_count | 0 |
| rejected_urls | 0 |

The approved local seed file was used only as runtime URL metadata input. It was not copied into the repository and remains outside git.

## Polite Crawling Evidence

| Policy | Result |
| --- | ---: |
| concurrency | 1 |
| delay_seconds | 8.0 |
| bounded retry/backoff | enabled |
| max_consecutive_failures | 5 |
| consecutive_failure_peak | 3 |
| elapsed_seconds | 9554.658 |

The run did not lower delay, did not increase concurrency, did not access search pages, and did not perform unbounded archive ID probing.

Transient failure classification:

| Category | Count |
| --- | ---: |
| browser_transient | 34 |
| permanent_failure | 10 |
| skipped_non_article_or_legacy_page | 7 |

## Candidate Handling

| Metric | Growth run |
| --- | ---: |
| newly_attempted_count | 351 |
| newly_imported_count | 300 |
| failed_count | 51 |
| invalid_candidate_count | 7 |
| invalid_imported_content_count | 0 |
| skipped_non_article_or_legacy_page | 7 |

Invalid candidates were skipped and replaced. They were not written into Article storage.

Parser quality issues rejected before storage:

- `https://spaces.ac.cn/archives/9775`: sidebar/comment/share script/navigation contamination detected
- `https://spaces.ac.cn/archives/9444`: sidebar/comment/share script/navigation contamination detected
- `https://spaces.ac.cn/archives/4797`: formula delimiters look unbalanced
- `https://spaces.ac.cn/archives/3936`: formula delimiters look unbalanced
- `https://spaces.ac.cn/archives/3644`: formula delimiters look unbalanced
- `https://spaces.ac.cn/archives/3604`: formula delimiters look unbalanced
- `https://spaces.ac.cn/archives/2709`: content extraction failed: article body not detected

## Import and Validation Metrics

| Metric | Growth run |
| --- | ---: |
| cumulative_valid_count | 700 |
| imported_count | 700 |
| failed_count | 51 |
| skipped_count | 400 |
| duplicate_count | 0 |
| invalid_content_count | 7 |
| invalid_candidate_count | 7 |
| invalid_imported_content_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| short_content_count | 0 |

Runtime Article store check:

| Metric | Value |
| --- | ---: |
| article_count | 700 |
| unique_url_count | 700 |
| duplicate_url_count | 0 |

Sample article IDs:

```text
100, 10001, 10007, 10017, 10040, 10047, 10055, 10077, 10085, 10088,
10114, 10122, 10137, 10145, 10162, 10180, 10226, 10240, 10266, 10289,
11738, 11750, 11760, 11767, 11772, 11777, 11782, 11784, 11787, 11804,
2136, 2177, 2185, 2192, 2195, 2208, 2215, 2219, 2222, 2231,
6508, 6534, 6540, 6549, 6575, 6583, 6620, 6621, 6671, 6704,
9403, 9431, 9461, 9473, 9509, 9526, 9577, 9632, 9706, 9984
```

## Resume / Checkpoint Evidence

| Metric | Value |
| --- | ---: |
| existing_runtime_count | 400 |
| newly_imported_count | 300 |
| resume_used | true |
| source transient handling | successful state preserved |

Final idempotent rerun command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 700 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Final idempotent rerun result:

| Metric | Value |
| --- | ---: |
| status | PASS |
| discovered_url_count | 700 |
| canonical_url_count | 700 |
| selected_count | 700 |
| attempted_count | 0 |
| imported_count | 700 |
| failed_count | 0 |
| skipped_count | 700 |
| duplicate_count | 0 |
| invalid_imported_content_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| elapsed_seconds | 0.426 |

The satisfied 700-article runtime state used local runtime data only and did not refetch source content.

## Artifact Policy

Runtime output path:

```text
.local_data/scientific_spaces/corpus/pilot
```

Git ignore coverage:

- `.local_data/` is ignored.
- Runtime progress, validation summary, failed URL log, inventory output, HTML dumps/snapshots, browser traces/profiles, PDFs, FAISS indexes, embedding caches, and DB files are ignored.

Artifact check:

- No runtime Article store committed.
- No `progress.json`, `failed_urls.jsonl`, or `validation_summary.json` committed.
- No full `article_list.json` committed.
- No PDF, HTML dump, image, browser trace/profile/cache, FAISS index, embedding cache, DB file, `.env`, or `node_modules` committed.
- The artifact grep matched only pre-existing tracked test HTML fixtures, not runtime artifacts.

## Test Evidence

Backend:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
155 passed, 2 skipped in 17.69s
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

Targeted pilot tests:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_full_corpus_pilot.py
```

Result:

```text
40 passed
```

Live command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 700 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Live result:

```text
PASS
```

Final idempotent rerun result:

```text
PASS, attempted_count=0, duplicate_count=0, invalid_imported_content_count=0
```

## Risks

- Scientific Spaces source availability and browser runtime behavior can still fluctuate.
- The approved seed lacks per-article year metadata.
- Year-based legacy stress remains blocked until an approved year metadata source exists.
- Older articles are included through cumulative seed order only; no year-based coverage claim is made.
- Parser drift can still appear in later legacy-heavy candidates.
- Browser runtime drift can change fetch timing and transient failure rates.
- Scaling from 700 to 1000 should remain a separate bounded gate with the same artifact policy and idempotent rerun requirement.

## Recommendation

A: Ready for P1-013 Cumulative 1000-Article Batch

Continue cumulative-only expansion. Keep year-based legacy stress blocked, do not make year-based claims, and reopen P1-009 only with an approved `content.html` snapshot or another trusted archive index source.
