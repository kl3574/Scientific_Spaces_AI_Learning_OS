# Full Corpus Final Batch Plan

## Current Status

- P1-013 Cumulative 1000-Article Batch: PASS
- P1-014 Full Corpus Final Batch Planning: PASS
- Full corpus final batch execution: NOT STARTED
- 1150 batch execution: NOT STARTED
- PDF export batch: NOT STARTED
- Year-based legacy stress: BLOCKED by unavailable per-article year metadata

This planning gate prepares the final 1000 to 1326 corpus expansion. It does not run the final batch, does not fetch article body pages, does not generate PDFs, does not commit runtime corpus data, does not commit the full seed list, and does not create or move a release tag.

## Evidence from 1000-Article Batch

Primary evidence:

- Report: `docs/CUMULATIVE_1000_ARTICLES_REPORT.md`
- Runtime Article store: ignored under `.local_data/scientific_spaces/corpus/pilot`
- Local Markdown library: ignored under `.local_data/scientific_spaces/corpus/local_library`

P1-013 growth run:

| Metric | Value |
| --- | ---: |
| cumulative_valid_count | 1000 |
| existing_runtime_count | 700 |
| newly_attempted_count | 308 |
| newly_imported_count | 300 |
| failed_count | 8 |
| invalid_candidate_count | 8 |
| invalid_imported_content_count | 0 |
| browser_transient_failures | 0 |
| permanent_failures | 0 |
| skipped_non_article_or_legacy_page | 8 |
| consecutive_failure_peak | 2 |
| elapsed_seconds | 5047.17 |
| delay_seconds | 8.0 |
| concurrency | 1 |

P1-013 final idempotent rerun:

| Metric | Value |
| --- | ---: |
| status | PASS |
| attempted_count | 0 |
| imported_count | 1000 |
| duplicate_count | 0 |
| invalid_imported_content_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| elapsed_seconds | 0.757 |

P1-013 materialization refresh:

| Metric | Value |
| --- | ---: |
| article_count | 1000 |
| exported_markdown_count | 1000 |
| missing_content_count | 0 |
| no_source_fetch | true |

Assessment:

- The 1000 batch failure rate was acceptable: `8 / 308 = 2.6%` candidate failures.
- All failures were invalid or legacy candidates rejected before storage.
- `invalid_imported_content_count=0` confirms no storage pollution.
- `browser_transient_failures=0` and `consecutive_failure_peak=2` indicate source pressure was stable at `delay_seconds=8`.
- The final rerun proved resume/idempotent behavior at the 1000-article state.
- The local Markdown library can be refreshed from Article storage without source access.

## Final Corpus Scope

Final corpus scope is the approved Scientific Spaces seed inventory:

| Metric | Value |
| --- | ---: |
| total_seed_count | 1326 |
| canonical_url_count | 1326 |
| duplicate_count | 0 |
| rejected_url_count | 0 |
| current_valid_runtime_articles | 1000 |
| remaining_seed_window | about 326 canonical URLs |

Included:

- Canonical archive URLs shaped as `https://spaces.ac.cn/archives/{numeric_id}`.
- `spaces.ac.cn` and approved `kexue.fm` archive aliases only after canonicalization.
- Article records that pass the frozen Article schema: `id`, `title`, `url`, `content`, `metadata`.
- Metadata keys: `date`, `category`, `images`, `references`.

Excluded:

- Search, category, tag, comment, login, attachment, static asset, PDF, and non-article paths.
- Search-engine scraping.
- Unbounded archive ID probing.
- Year-based coverage claims.
- PDF export batch.
- Runtime artifact commits.

The final seed target is 1326 canonical seed URLs. The final valid Article target must be defined by importability, not by forcing all 1326 canonical URLs into storage.

## Completion Definition

Final corpus completion has two layers.

### Seed Complete

Seed complete means:

- `total_seed_count=1326`.
- `canonical_url_count=1326`.
- `duplicate_count=0`.
- `rejected_url_count=0`.
- Every canonical seed URL is either already imported, attempted in the final run, or explicitly classified from previous runtime evidence.

### Import Complete

Two definitions were considered.

#### Option A: Strict 1326 Valid Articles

Requirements:

- `cumulative_valid_count=1326`.
- `invalid_imported_content_count=0`.

Pros:

- Simple count target.
- Easy to communicate.

Cons:

- Known legacy/special pages can be non-importable.
- `archives/12` and later parser-quality rejects show that some canonical URLs may not safely produce Article content.
- This can incentivize weakening parser quality gates or polluting storage.

Decision:

- Not recommended as the final completion definition.

#### Option B: All Importable Canonical Articles Completed

Requirements:

- All 1326 canonical seed URLs are imported or classified.
- Valid imported Articles equal `importable_success_count`.
- Non-importable, legacy, invalid, or parser-quality candidates are classified in the final report.
- `remaining_unclassified_seed_count=0`.
- `invalid_imported_content_count=0`.
- `duplicate_count=0`.
- No sidebar/comment/share script/navigation contamination enters storage.
- The final report explicitly states that not every canonical seed URL necessarily produces importable `Article.content`.

Pros:

- Preserves Article.content fidelity.
- Keeps storage clean.
- Matches the local learning corpus goal: import all safely importable articles.
- Handles known legacy/special pages without weakening validation.

Cons:

- The final valid Article count may be lower than 1326.
- Requires precise failure classification and audit evidence.

Decision:

- Recommended.

Final corpus complete should mean: seed complete plus all importable canonical articles completed, with zero invalid imported content and zero unclassified seed URLs.

## Final Batch Options

### Option A: Direct Cumulative 1326 Final Batch

Shape:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 1326 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Pros:

- Simple direct path from 1000 to final seed scope.
- One execution report.
- P1-013 evidence shows stable source pressure.

Cons:

- The current bounded pilot cap is 1000; P1-015 would need a controlled cap revision or completion mode before this command can run.
- A strict `--limit 1326` valid Article target can block if non-importable candidates exist.
- The remaining seed window may contain older legacy structures.

Assessment:

- Viable only if implemented with the Option B completion definition and bounded failure classification.

### Option B: Two-Step Final Batch

Shape:

```text
P1-015 Cumulative 1150-Article Batch
P1-016 Final Corpus Completion Batch
```

Pros:

- More conservative.
- Provides an intermediate review point.
- Easier to detect rising legacy/parser failure rates before the final pass.

Cons:

- Adds another report and commit.
- P1-013 already shows low failure rate and stable source pressure.
- More operational overhead.

Assessment:

- Useful if the operator wants a lower-risk staged path, but not required by current evidence.

### Option C: Final All-Remaining Completion Attempt

Shape:

```text
Current 1000 valid runtime Articles
+ remaining canonical seed URLs
-> attempt/classify all remaining candidates under bounded policy
-> import all valid Articles
-> classify all non-importable candidates
-> final idempotent rerun
-> materialization refresh
-> local corpus quality audit
```

Pros:

- Matches the recommended completion definition.
- Avoids forcing invalid or legacy pages into storage.
- Keeps the final target as all 1326 canonical seed URLs while allowing valid Article count to equal importable success count.
- Explicitly separates seed completion from Article importability.

Cons:

- Requires final report metrics for attempted/classified/unclassified seed URLs.
- May require a small runner revision in P1-015 because current `--limit` semantics are count-target based.

Assessment:

- Recommended.

## Recommended Strategy

Recommendation:

B. P1-015 Final Corpus Completion Batch

The recommended next task should implement a controlled final completion mode or controlled 1326 cap revision, then execute one final all-remaining completion batch using the Option B completion definition.

Required P1-015 behavior:

- Use the approved seed file as local runtime input only.
- Start from the existing 1000 valid runtime Article store.
- Do not run a year-based batch.
- Do not claim year-based coverage.
- Attempt or classify all remaining canonical seed URLs.
- Import only candidates that pass Article quality gates.
- Record all non-importable candidates without writing them to storage.
- Preserve `invalid_imported_content_count=0`.
- End with final idempotent rerun evidence.
- Refresh local Markdown materialization.
- Run a final local corpus quality audit.

Why this can proceed directly instead of a 1150 midpoint:

- P1-013 failure rate was low at about 2.6%.
- Source transient failures were zero.
- Consecutive failure peak was 2, below the stop threshold of 5.
- The runner preserved successful state and idempotent rerun behavior.
- Remaining work is about 326 canonical seed URLs, not a full fresh corpus run.

Use the two-step 1150 strategy only if the operator wants a stricter human review checkpoint before final completion.

## Runtime Estimate

P1-013 timing:

- `308` attempts took `5047.17` seconds.
- Average elapsed time was about `16.4` seconds per attempted candidate.
- The average includes `8` seconds delay, browser acquisition, parsing, validation, storage, and retry overhead.

Estimated final completion runtime:

| Scenario | Attempt count | Estimate |
| --- | ---: | ---: |
| Low-failure direct completion | 326 | about 1.5 hours |
| More legacy/parser rejects | 340-380 | about 1.6-1.8 hours |
| Delay raised to 10 seconds | 326 | about 1.7-1.9 hours |

Delay recommendation:

- Continue with `delay_seconds=8` by default.
- Raise to `delay_seconds=10` only if transient browser failures, 403, 429, TLS, or timeout clusters rise during P1-015.
- Never reduce delay below 8 seconds.
- Never increase concurrency above 1.

## Polite Crawling Policy

P1-015 must enforce:

- `concurrency=1`.
- `delay_seconds >= 8`.
- `delay_seconds=10` allowed only as a more conservative response to transient failures.
- `max_consecutive_failures <= 5`.
- Bounded retry and exponential backoff.
- Classification for timeout, 403, 429, TLS, parser invalidity, legacy/special pages, and permanent failures.
- Stop condition for repeated 403/429/TLS/timeout clusters.
- No search pages.
- No category, tag, comment, login, attachment, static asset, or PDF paths.
- No search engine scraping.
- No unbounded archive ID probing.

## Candidate / Failure Handling

P1-015 must keep these semantics:

- `invalid_candidate_count`: fetched or parsed candidate cannot be safely imported and was not written to storage.
- `invalid_imported_content_count`: invalid content found after storage. This must remain `0`.
- `skipped_non_article_or_legacy_page`: canonical seed URL is a legacy/special/non-article-like page and was skipped before storage.
- `non_importable_candidate_count`: final count of canonical seed URLs that did not produce valid Article content but were classified.
- `remaining_unclassified_seed_count`: must be `0` for final completion.

Allowed final outcome:

- `imported_count < 1326` is acceptable only if every non-imported canonical seed URL is classified and `remaining_unclassified_seed_count=0`.

Blocked final outcome:

- `invalid_imported_content_count > 0`.
- Parser contamination enters storage.
- Formula validity regresses.
- Metadata collapses.
- Duplicate count rises above 0.
- Runtime artifacts are staged or tracked.
- Unclassified seed URLs remain after claiming final completion.

## Validation Gates

P1-015 final report must include:

- `total_seed_count`.
- `canonical_url_count`.
- `cumulative_valid_count`.
- `total_attempted_seed_count`.
- `imported_count`.
- `failed_count`.
- `invalid_candidate_count`.
- `skipped_non_article_or_legacy_page`.
- `non_importable_candidate_count`.
- `invalid_imported_content_count`.
- `duplicate_count`.
- `missing_content_count`.
- `content_completeness_rate`.
- `formula_valid_rate`.
- `metadata_completeness_rate`.
- `final_idempotent_rerun_result`.
- `local_materialization_exported_count`.
- `local_materialization_missing_content_count`.
- `final_completion_definition_used`.
- `remaining_unimported_seed_count`.
- `remaining_unclassified_seed_count`.

Pass thresholds:

- `invalid_imported_content_count=0`.
- `duplicate_count=0`.
- `missing_content_count=0`.
- `content_completeness_rate >= 0.95`.
- `formula_valid_rate >= 0.98`.
- `metadata_completeness_rate >= 0.95`.
- `remaining_unclassified_seed_count=0` for final completion.
- Final idempotent rerun does not refetch source if final state is satisfied.

## Local Materialization Requirement

After P1-015 final completion passes, refresh the local Markdown library:

```bash
uv run --project backend python scripts/corpus/materialize_local_library.py \
  --article-store-path .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/corpus/local_library
```

Requirements:

- No source fetch.
- No PDF generation.
- `exported_markdown_count` equals final valid Article count.
- `missing_content_count=0`.
- Index JSON is generated.
- Index CSV is generated.
- Summary JSON is generated.
- All output remains under ignored `.local_data/`.

## Final Local Corpus Audit Requirement

P1-015 must include a local-only audit after materialization:

- Article store record count.
- Unique URL count.
- Duplicate count.
- Missing content count.
- Required metadata key completeness.
- Content completeness rate.
- Formula delimiter balance.
- Page chrome contamination scan.
- Local Markdown file count.
- Local index entry count.
- Local library summary consistency.
- No source fetch during audit.
- No runtime artifact staged or tracked.

The audit should be a final gate before claiming full corpus completion.

## Artifact Policy

Runtime Article store:

```text
.local_data/scientific_spaces/corpus/pilot/article_store/articles.json
```

Local Markdown library:

```text
.local_data/scientific_spaces/corpus/local_library/
```

Policy:

- Runtime Article store is local learning data and must remain under `.local_data/`.
- Local Markdown library is local learning material and must remain under `.local_data/`.
- Neither Article store nor local library output is committed to git.
- Git commits only code, tests, reports, and README updates.
- Full seed list remains outside git.
- PDF export is a later independent task.
- PDF success is not an Article.content success criterion.
- No PDF, HTML dump, image, trace/profile/cache, DB, `.env`, `node_modules`, FAISS index, embedding cache, progress file, failed URL log, validation summary, inventory JSON, or full `article_list.json` may be committed.

## Post-Full-Corpus Product Tasks

After final corpus completion, plan these product tasks separately:

1. RAG index rebuild for the local corpus.
2. RAG index size and chunk count report.
3. Graph scaling, pagination, filtering, and large-corpus navigation checks.
4. Tutor source selection over the larger corpus.
5. Evaluation harness extension beyond fixed fixtures.
6. Search UI and reader performance check.
7. SQLite / JSON store pressure review for Article, learning, graph, and tutor data.
8. Local library navigation and browsing UX.
9. Optional PDF export workflow as a separate batch task.

Do not implement these in P1-014 or P1-015 unless a future task explicitly scopes them.

## Go / No-Go Criteria

Go for P1-015 Final Corpus Completion Batch if:

- Runtime Article store still has 1000 valid Articles.
- `duplicate_count=0`.
- `missing_content_count=0`.
- `invalid_imported_content_count=0`.
- Approved seed file is available locally.
- Final runner behavior is updated through a controlled P1-015 task to support the completion definition.
- Operator accepts `concurrency=1` and `delay_seconds >= 8`.
- No full seed list or runtime artifacts are staged.

No-go if:

- Runtime store is missing or polluted.
- Source access shows repeated 403/429/TLS/timeout clusters before final run.
- Parser quality gates need changes without a targeted revision task.
- Year-based claims are required before per-article year metadata exists.
- The operator requires strict 1326 valid Articles regardless of importability.
- Runtime artifacts, PDFs, HTML dumps, or full seed lists are staged.

## Recommended Next Task

B. P1-015 Final Corpus Completion Batch

P1-015 should execute a controlled final all-remaining completion batch using the Option B completion definition: all importable canonical Articles completed, all non-importable canonical seed URLs classified, and zero invalid imported content.
