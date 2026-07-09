# Full Corpus Execution Plan

## Current Status

- P1-005 100-Article Medium Batch: PASS
- P1-006 Full Corpus Execution Planning Gate: PASS
- Full corpus execution status: NOT STARTED
- Recommended next task: A. P1-007 Full Seed Inventory Dry Run

This planning gate evaluates whether the project has enough evidence to move toward full Scientific Spaces corpus execution. It does not execute the full corpus, does not execute a 200/400/700/1000 batch, does not generate PDFs, does not commit Article content, and does not move release tags.

Decision:

- The project is ready to enter the next controlled pre-execution step: full seed inventory dry-run.
- The project is not approved for a one-shot 1326-article content import.
- Full content import should proceed only through staged P1 execution gates with reports, idempotent reruns, and artifact checks at every phase.

## Evidence from 100-Article Batch

Primary evidence:

- Report: `docs/MEDIUM_BATCH_100_ARTICLES_REPORT.md`
- Commit: `9fc4dbdc185a6c9376bb3915a267ea8b37f59020`
- Push CI: PASS on `main`
- Runtime Article store: ignored under `.local_data/scientific_spaces/corpus/pilot`

P1-005 growth run metrics:

| Metric | Value |
|---|---:|
| target_count | 100 |
| existing_runtime_count | 50 |
| cumulative_valid_count | 100 |
| attempted_count | 53 |
| newly_imported_count | 50 |
| failed_count | 3 |
| duplicate_count | 0 |
| invalid_candidate_count | 0 |
| skipped_non_article_or_legacy_page | 0 |
| invalid_imported_content_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| elapsed_seconds | 1063.109 |
| delay_seconds | 5.0 |
| concurrency | 1 |
| max_consecutive_failures | 5 |

Failure categories:

| Category | Count |
|---|---:|
| browser_transient | 2 |
| permanent_failure | 1 |

Final idempotent rerun:

| Metric | Value |
|---|---:|
| status | PASS |
| attempted_count | 0 |
| imported_count | 100 |
| failed_count | 0 |
| skipped_count | 100 |
| elapsed_seconds | 0.103 |

Interpretation:

- Resume and checkpoint behavior is strong enough for the next planning step.
- Failed candidates did not pollute storage.
- The 100-article batch does not prove full-corpus success. The historical corpus can contain more legacy pages, short posts, old DOM structures, image-heavy pages, and source-side transient failures than the 100-article sample.

## Full Corpus Scope

Included:

- Canonical Scientific Spaces article URLs:
  - `https://spaces.ac.cn/archives/{numeric_id}`
- `kexue.fm` archive aliases only after canonicalization to the `spaces.ac.cn` archive URL.
- Article records that pass the frozen Article contract:
  - `id`
  - `title`
  - `url`
  - `content`
  - `metadata`
- Metadata keys:
  - `date`
  - `category`
  - `images`
  - `references`

Excluded:

- search pages
- category pages
- tag pages
- comment pages
- RSS pages as Article records
- external links
- PDF output
- HTML dumps
- browser trace/profile artifacts
- image downloads
- attachment downloads
- search engine scraping
- unbounded archive ID probing

Domain policy:

- `spaces.ac.cn` is the canonical Article host.
- `kexue.fm` aliases are accepted only when they match `/archives/{numeric_id}` and are canonicalized to `spaces.ac.cn`.
- Dedupe is by archive ID / canonical URL.

## Seed Inventory

Approved local seed input:

```text
/home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

The seed file remains an operator-local runtime input and must not be committed.

Observed seed inventory from local metadata:

| Metric | Value |
|---|---:|
| JSON shape | object with `articles` list |
| seed entries | 1326 |
| URL entries | 1326 |
| archive ID entries | 1326 |
| unique archive IDs | 1326 |
| archive ID min | 4 |
| archive ID max | 11804 |
| tracked seed fields | `id`, `url`, `title` |
| date/year fields | not present |

Inventory implication:

- The seed is strong enough for canonical URL inventory.
- It is not sufficient by itself for year-based batching because the local seed only exposes `id`, `url`, and `title`.
- Year-based batching requires either imported Article metadata, a separate approved metadata inventory step, or a future seed enrichment task.

## Execution Strategy Options

### Option A: One-shot full run

Description:

- Continue directly from 100 to the full 1326 seed URLs in a single content import run.

Assessment:

- Not recommended.

Pros:

- Operationally simple.
- Produces the corpus quickly if nothing fails.

Cons:

- Long continuous browser runtime.
- Higher source pressure.
- Harder failure triage.
- Harder human review.
- Greater risk of storing a parser regression before it is noticed.
- Current P1 runner is capped at 100 and should not be force-expanded to 1326 without a separate execution gate.

### Option B: Cumulative staged batches

Description:

- Continue from the existing 100 valid Articles through cumulative targets:
  - 200
  - 400
  - 700
  - 1000
  - 1326

Assessment:

- Recommended as the main content-import path after seed inventory.

Pros:

- Each stage has a report and rollback point.
- Resume/idempotent behavior is easy to verify.
- Parser drift and source pressure can be detected early.
- Human review can happen between stages.
- Failed candidates remain bounded and diagnosable.

Cons:

- More reports and commits.
- Longer calendar time.
- Requires controlled runner cap revisions in later P1 tasks.

### Option C: Year-based batches

Description:

- Execute content import or stress checks by year windows, for example:
  - 2026-2024
  - 2023-2021
  - 2020-2018
  - 2017-2015
  - 2014-2012
  - 2011-2009

Assessment:

- Recommended as a legacy stress strategy, not as the first full-corpus execution path.

Pros:

- Makes historical DOM drift easier to isolate.
- Gives explicit old-article coverage.
- Fits human review sampling well.

Cons:

- Current seed file has no date/year metadata.
- Requires seed enrichment, imported metadata filtering, or a separate inventory helper.
- Year metadata quality must be validated before it drives execution.

### Option D: Metadata-first then content import

Description:

- First canonicalize and validate the full 1326 seed inventory without browser content import.
- Then run staged Article.content import.

Assessment:

- Recommended as Phase 0 before content execution.

Pros:

- Confirms corpus inventory without source pressure.
- Catches malformed URLs, duplicates, and out-of-scope paths before browser access.
- Produces a clean target count and planning baseline.

Cons:

- Requires an extra inventory report.
- Does not prove browser content access for old pages.

## Recommended Strategy

Recommended sequence:

1. Phase 0: Full seed inventory dry-run
   - Input: approved local seed file.
   - Output: aggregate inventory report only.
   - No browser content fetch.
   - No Article.content import.
   - No PDF export.

2. Phase 1: Cumulative 200 articles
   - Continue from the existing 100 valid runtime Articles.
   - Use `delay_seconds >= 8`.
   - Run final idempotent rerun.
   - Commit report only.

3. Phase 2: Cumulative 400 articles
   - Same gates as Phase 1.
   - Add human review sampling for old and formula-heavy pages.

4. Phase 3: Year-based legacy stress batch
   - Requires metadata/year filtering from inventory or imported metadata.
   - Focus on old pages and known legacy structures.
   - This phase is for risk reduction, not corpus count alone.

5. Phase 4: Cumulative 700 articles
   - Proceed only if legacy stress is acceptable.

6. Phase 5: Cumulative 1000 articles
   - Recheck storage pressure, RAG indexing time, graph size, and eval harness runtime.

7. Phase 6: Cumulative full corpus, target 1326
   - Execute only if all previous phases pass and artifact checks remain clean.

Each phase must enforce:

- `concurrency=1`
- `delay_seconds >= 8` recommended
- `max_consecutive_failures <= 5`
- no PDF batch
- no HTML dump
- no runtime artifact commit
- `invalid_imported_content_count=0`
- `duplicate_count=0`
- `content_completeness_rate >= 0.95`
- `formula_valid_rate >= 0.98`
- `metadata_completeness_rate >= 0.95`
- final idempotent rerun
- report committed only, runtime data ignored

## Estimated Runtime

Observed P1-005 model:

| Metric | Value |
|---|---:|
| attempted_count | 53 |
| newly_imported_count | 50 |
| elapsed_seconds | 1063.109 |
| average seconds per successful import | 21.26 |
| average seconds per attempt | 20.06 |
| observed attempts per successful import | 1.06 |

Remaining corpus from current 100 to 1326:

| Delay | Expected attempts | Observed-model runtime | Conservative planning window |
|---|---:|---:|---:|
| 5s | 1300 | 7.24 hours | 9-12 hours |
| 8s | 1300 | 8.33 hours | 10-14 hours |
| 10s | 1300 | 9.05 hours | 12-16 hours |

Full corpus from zero for comparison:

| Delay | Expected attempts | Observed-model runtime | Conservative planning window |
|---|---:|---:|---:|
| 5s | 1406 | 7.83 hours | 10-13 hours |
| 8s | 1406 | 9.00 hours | 11-15 hours |
| 10s | 1406 | 9.79 hours | 13-18 hours |

Recommended staged estimates from current 100 Articles:

| Stage | New target articles | Expected attempts | 8s observed-model runtime |
|---|---:|---:|---:|
| 100 -> 200 | 100 | 106 | 0.68 hours |
| 200 -> 400 | 200 | 212 | 1.36 hours |
| 400 -> 700 | 300 | 318 | 2.04 hours |
| 700 -> 1000 | 300 | 318 | 2.04 hours |
| 1000 -> 1326 | 326 | 346 | 2.22 hours |

Conservative estimate:

- Use the 8s delay plan as the minimum acceptable full-corpus execution profile.
- Reserve 10-14 hours for the remaining corpus under normal source behavior.
- Reserve 14-20 hours if transient failures, old-page parser drift, or source throttling increases.
- Do not mechanically extrapolate the 100-article 1.0 quality metrics to the full 1326 corpus.

## Polite Crawling Policy

Required policy:

- `concurrency=1`
- `delay_seconds >= 8` for future content-import phases
- bounded retry only
- exponential backoff retained
- `max_consecutive_failures <= 5`
- no search pages
- no category/tag/comment/login/static/PDF/attachment paths
- no full-site traversal
- no archive ID probing unless a separate gate approves it
- no bypass of access controls

Stop conditions:

- repeated `403` or `429`
- repeated TLS/timeout failures
- source policy or robots uncertainty
- invalid imported content
- parser contamination
- formula delimiter regression
- metadata collapse
- accidental runtime artifact staging

Source pressure decision:

- If transient failures increase but no invalid content is stored, preserve existing runtime state and mark the phase CONDITIONAL or BLOCKED according to whether the target was reached.
- Do not compensate for failures by increasing concurrency, lowering delay, expanding to unbounded candidates, or scraping search pages.

## Resume / Checkpoint Policy

The execution path must be resumable and idempotent.

Required behavior:

- Existing valid runtime Articles count toward the cumulative target before source access.
- Completed URLs are read from ignored runtime progress or reconstructed from the Article store.
- Failed candidates are logged in aggregate reports without storing HTML or article body dumps.
- The Article store must use URL-based idempotent upsert semantics.
- A final idempotent rerun must report `attempted_count=0` when the target is already satisfied.

Runtime files remain ignored:

- Article store JSON
- progress files
- validation summaries
- failed URL logs
- browser caches/profiles/traces

Report policy:

- Commit aggregate metrics only.
- Commit limited URLs/IDs only when needed for diagnosis.
- Do not commit article bodies.

## Candidate / Failure Handling

Candidate taxonomy:

- `invalid_candidate_count`: candidate failed quality gates before storage and was not written.
- `invalid_imported_content_count`: invalid Article content already in storage.
- `skipped_non_article_or_legacy_page`: candidate page is legacy, special, or page-shell and should not be forced into storage.
- `browser_transient`: timeout, TLS, 403, 429, or similar source/browser fluctuation.
- `permanent_failure`: policy failure, unsupported source shape, or non-recoverable candidate error.

Rules:

- Invalid candidates may be replaced by later approved seed URLs within bounded execution.
- Invalid imported content is a blocker.
- Legacy/special pages must be skipped or separately analyzed, not padded with page chrome.
- A failed candidate must not lower content quality thresholds.
- The final report must distinguish candidate failure from storage pollution.

## Validation Gates

Every content-import phase must verify:

1. Article count reaches the cumulative target or the phase is marked CONDITIONAL/BLOCKED.
2. `duplicate_count=0`.
3. `invalid_imported_content_count=0`.
4. `content_completeness_rate >= 0.95`.
5. `formula_valid_rate >= 0.98`.
6. `metadata_completeness_rate >= 0.95`.
7. Formula delimiters are balanced.
8. Article content is not title-only.
9. Sidebar/comment/share/navigation/script contamination is absent.
10. Metadata keys include `date`, `category`, `images`, and `references`.
11. Final idempotent rerun does not refetch source when target is satisfied.
12. Artifact check is clean.

Backend/frontend/eval evidence for each execution phase:

```bash
uv run --project backend --extra dev pytest -q
npm run build
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

## Human Review Sampling

After each content-import phase, perform human review sampling and record summary only.

Minimum sampling:

- 5 random imported articles
- 2 formula-heavy articles
- 2 short articles, if any
- 2 old articles
- 2 articles with images/references
- any skipped legacy/special page

Review checks:

- title matches page subject
- content starts from article body
- no sidebar/comment/share/navigation contamination
- formula delimiters and visual math source are preserved
- images/references metadata shape is preserved
- short posts are true short posts, not extraction failures

Do not commit article body excerpts, full HTML, screenshots, PDFs, or downloaded images as review evidence.

## Artifact / Privacy / License Policy

Required policy:

1. Runtime Article store is not committed.
2. Full corpus Article.content is not committed.
3. PDFs are not committed.
4. HTML dumps are not committed.
5. Browser trace/profile/cache artifacts are not committed.
6. Full `article_list.json` is not committed unless a separate decision explicitly approves a reduced/public fixture.
7. Reports contain aggregate metrics and limited URLs/IDs only.
8. Scientific Spaces content is for local learning use in this project.
9. PDF export remains an independent workflow and is not part of full corpus Article.content import.
10. The project remains local-first and single-user unless a later deployment/security task changes that boundary.

Copyright and local-use caveat:

- Imported Article.content should remain in ignored local runtime storage.
- The repository should not redistribute Scientific Spaces article bodies, full HTML, images, attachments, or PDFs.
- Future publication, hosting, sharing, or multi-user deployment requires a separate content rights and retention review.

## RAG / Graph / Tutor Scaling Risks

Full corpus Article import can affect downstream systems even if this P1 task does not modify them.

RAG risks:

- Chunk count will increase materially.
- Indexing time will grow with Article count and chunk density.
- FAISS/vector store size will grow.
- Fake embeddings are deterministic for tests, but real embeddings would introduce cost, rate, and cache policy questions.
- Retrieval quality may require re-tuning chunk size, top-k, and citation selection.

Graph risks:

- Concept and section node counts can grow sharply.
- Edge density may make graph build and serialization slower.
- Frontend graph UI may need filtering, pagination, or level-of-detail rendering.
- Provenance metadata must remain attached to generated concepts and relationships.

Tutor risks:

- Tutor source selection must remain citation-grounded and avoid unsupported synthesis.
- Larger corpora can increase ambiguous retrieval contexts.
- Eval fixtures may need old-article, formula-heavy, and multi-source cases.
- Research mode must remain local-only unless a separate task changes that boundary.

Storage risks:

- JSON Article storage is acceptable for pilots and medium batches, but full corpus size can increase write/read latency.
- SQLite currently covers Learning data only as an opt-in slice.
- Article storage migration should be considered after full seed inventory and before repeated large content-import phases if JSON runtime pressure appears.

These risks are follow-up planning inputs only. This P1-006 task does not change RAG, Graph, Tutor, or persistence defaults.

## Go / No-Go Criteria

Go conditions before content execution beyond 100:

1. P1-005 100 articles PASS.
2. Push CI PASS.
3. Full seed inventory dry-run PASS.
4. Artifact policy confirmed.
5. Full seed list not committed.
6. Storage/resume path stable.
7. Source delay `>= 8s` approved.
8. Human review sampling policy defined.
9. Parser contamination guard stable.
10. License/local-use caveat documented.
11. Next runner cap expansion is reviewed in a dedicated P1 execution task.

No-Go conditions:

1. Source shows repeated `403` or `429`.
2. `invalid_imported_content_count > 0`.
3. Runtime artifacts are staged or tracked.
4. Parser contamination appears.
5. Formula validity regresses.
6. Metadata collapses.
7. Full seed is accidentally committed.
8. Full run cannot resume safely.
9. Human review sampling finds systematic extraction drift.
10. RAG/Graph/Tutor scaling checks become too slow or unstable after a staged batch.

## Recommended Next Task

A. P1-007 Full Seed Inventory Dry Run

The next task should validate the full 1326-entry seed inventory without browser content import. It should produce aggregate counts, canonical URL validation, duplicate/rejected URL reporting, archive ID coverage, and artifact checks. It should not import Article.content, generate PDFs, or commit the full seed file.
