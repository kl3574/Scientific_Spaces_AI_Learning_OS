# Medium Batch 100 Articles Plan

## Current Status

- P1-001 Pilot: PASS
- P1-002 Plan: PASS
- Scope: planning and gate definition only
- Recommendation: A: Ready for P1-003 20-article medium batch phase

This document defines the controlled path from the successful 10-article pilot to a 100-article Scientific Spaces medium batch. It does not execute the medium batch, does not run a full crawl, does not generate PDFs, does not store article corpus artifacts in git, and does not modify frozen M1-M7 contracts.

## Pilot Evidence

Baseline evidence comes from `docs/FULL_CORPUS_PILOT_REPORT.md`.

Pilot result:

| Metric | Value |
|---|---:|
| selected_count | 10 |
| attempted_count | 10 |
| imported_count | 10 |
| failed_count | 0 |
| duplicate_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| invalid_content_count | 0 |
| browser_transient_failures | 0 |
| permanent_failures | 0 |

Pilot safeguards:

- RSS recent discovery from `https://spaces.ac.cn/feed`.
- Canonical URL validation before browser access.
- Playwright Chromium browser access with article-body quality gate.
- Parser/converter validation before storage.
- Runtime Article store under ignored `.local_data/`.
- Resume from progress or existing Article store.
- No PDF, HTML dump, browser profile, trace, image, FAISS index, embedding cache, or article corpus file committed.

Post-pilot limitation:

- The existing pilot runner is intentionally capped at 30 articles.
- The 100-article batch must be executed through a separate P1 implementation gate or an explicitly approved medium-batch runner, not by weakening the pilot cap in place.

## Scope

P1-002 scope:

- Define a 100-article medium-batch plan.
- Preserve the M1 source pipeline freeze and P1 pilot constraints.
- Define discovery, execution, validation, artifact, and human-review gates.
- Prepare the next execution task without running it.

100-article medium batch scope:

- Process up to 100 canonical Scientific Spaces article URLs.
- Use only approved discovery inputs.
- Store only validated Article records in ignored runtime storage.
- Produce aggregate runtime summaries outside git.
- Confirm idempotent re-run behavior.

Out of scope:

- Full corpus processing.
- PDF batch generation.
- Search-page crawling.
- Unbounded archive ID probing.
- High-concurrency crawling.
- Bypassing source access controls.
- Changing M1 RSS discovery, browser access, parser, converter, storage schema, sync contract, or validation standards directly.
- Changing M2-M7 product contracts.
- Committing article corpus JSON, HTML, PDFs, screenshots, images, traces, profiles, cache, runtime databases, FAISS indexes, or embedding caches.

## Discovery Input Strategy

Approved input sources:

1. RSS recent URLs
   - Source: `https://spaces.ac.cn/feed`
   - Use for freshness and recent-window sanity checks.
   - Do not treat RSS alone as historical full-corpus coverage.

2. Approved seed list
   - Operator-provided list of candidate article URLs.
   - Must contain only article candidates or clearly documented provenance.
   - Must remain under ignored runtime paths if it contains real corpus data.
   - Must be canonicalized before browser access.

3. Previously verified local runtime Article records
   - May be used for idempotency and resume validation.
   - Must not be committed to git.

Disallowed automated inputs:

- Search result pages.
- Site search pages.
- Category or archive pagination traversal.
- Comment, login, admin, attachment, PDF, image, or static asset paths.
- Unbounded numeric archive ID probing.

Canonical URL format:

```text
https://spaces.ac.cn/archives/{numeric_id}
```

Canonicalization requirements:

- Accept only `spaces.ac.cn`, `www.spaces.ac.cn`, `kexue.fm`, or `www.kexue.fm` archive URLs.
- Normalize to HTTPS `spaces.ac.cn`.
- Remove query strings and fragments.
- Reject non-numeric archive paths.
- Deduplicate before browser access.
- Track duplicate and rejected URL counts in ignored runtime diagnostics.

## Execution Phases

### Phase 0: Dry Run

Goal:

- Validate discovery input without browser fetching.

Actions:

- Load RSS and approved seed URLs.
- Canonicalize candidates.
- Reject invalid paths.
- Deduplicate.
- Produce a runtime-only dry-run summary.

Gate:

- `canonical_url_count >= 100` if the goal is a full 100-article batch.
- `duplicate_count` is understood and bounded.
- Rejected URL reasons are auditable.
- No browser fetch occurs.

### Phase 1: 20 Articles

Goal:

- Confirm the pilot behavior still holds beyond the original 10-article sample.

Actions:

- Process 20 canonical URLs.
- Use concurrency `1`.
- Use delay at least `5` seconds between article fetches.
- Apply bounded retry/backoff.
- Store only validated Article records.
- Repeat the same run to confirm idempotency.

Gate:

- `imported_count=20`.
- `duplicate_count=0`.
- `invalid_content_count=0`.
- `content_completeness_rate >= 0.95`.
- `formula_valid_rate >= 0.98`.
- `metadata_completeness_rate >= 0.95`.
- No sidebar, comment, share script, navigation, or page-shell contamination in stored content.

### Phase 2: 50 Articles

Goal:

- Check medium-batch stability before the 100-article gate.

Actions:

- Process 50 canonical URLs from the same approved input strategy.
- Preserve Phase 1 crawling and validation controls.
- Review failure categories before continuing.

Gate:

- All Phase 1 quality thresholds pass.
- Permanent failure rate `<= 10%`.
- Consecutive source failures do not exceed `5`.
- No data-quality blocker appears.
- Idempotent repeat run keeps `duplicate_count=0`.

### Phase 3: 100 Articles

Goal:

- Complete the planned medium batch without treating it as a full crawl.

Actions:

- Process exactly 100 selected canonical URLs unless stop conditions trigger earlier.
- Keep concurrency `1`.
- Keep delay at least `5` seconds, with operator option to increase to `10` seconds if source pressure appears.
- Stop on source-policy concerns or quality blockers.
- Produce ignored runtime summaries and a committed aggregate handoff report only if a later task requests it.

Gate:

- `selected_count=100`.
- `duplicate_count=0`.
- `invalid_content_count=0`.
- `content_completeness_rate >= 0.95`.
- `formula_valid_rate >= 0.98`.
- `metadata_completeness_rate >= 0.95`.
- `sidebar_comment_script_contamination_count=0`.
- `quality_gate_failed_count=0` for stored records.
- Idempotent re-run produces no duplicate records.

## Polite Crawling Policy

Required policy:

- Concurrency: `1`.
- Delay: at least `5` seconds between article fetches for medium batch.
- Retry: at most `2` retries after the first attempt.
- Backoff: exponential or bounded backoff with jitter, starting at `3` seconds and capped at `60` seconds.
- Browser context: non-persistent.
- Downloads: disabled.
- PDF requests: not executed in this task.
- User agent: project-identifying, reasonable, and non-deceptive.
- Robots/source policy: checked before new source strategy or domain-policy changes.

Stop conditions:

- Repeated `403` or `429` cluster.
- TLS/timeout cluster exceeding `5` consecutive source failures.
- Permanent failure rate above `10%`.
- Any evidence that the source is denying or throttling access.
- Any data-quality failure that would write invalid Article content.

Non-blocking risk classification:

- Single timeout or one-off transient browser failure can be recorded as non-blocking only if the phase still has enough successful, validated articles and all quality thresholds pass.
- Any invalid stored content is a blocker, not a transient risk.

## Resume / Checkpoint Strategy

Runtime state:

- `progress.json`
- `failed_urls.jsonl`
- `validation_summary.json`
- runtime Article store under `.local_data/scientific_spaces/`

Resume requirements:

- Skip canonical URLs already stored successfully.
- Reconstruct progress from Article storage if progress metadata is missing.
- Preserve existing successful state if RSS or source discovery fails transiently.
- Retry transient failures only within configured retry limits.
- Do not overwrite a successful validation summary with a misleading failure-only state without preserving the earlier successful state.

Checkpoint cadence:

- Write progress after each successful Article upsert.
- Write failure records with URL, category, and reason.
- Write aggregate validation summary at the end of each phase.
- Keep all runtime checkpoint files ignored by git.

Rollback:

- Stop the batch.
- Preserve runtime directory for diagnosis if needed.
- Roll back by restoring a prior runtime backup or deleting the batch runtime directory.
- Never repair a failed medium batch by committing runtime data.

## Validation Metrics

Required metrics:

- `discovered_url_count`
- `canonical_url_count`
- `duplicate_count`
- `selected_count`
- `attempted_count`
- `imported_count`
- `failed_count`
- `skipped_count`
- `content_completeness_rate`
- `formula_valid_rate`
- `metadata_completeness_rate`
- `short_content_count`
- `invalid_content_count`
- `parser_quality_issues`
- `browser_transient_failures`
- `permanent_failures`
- `failed_url_categories`

Recommended additional metrics:

- `rss_url_count`
- `seed_url_count`
- `canonical_alias_count`
- `rejected_url_count`
- `quality_gate_failed_count`
- `image_valid_rate`
- `reference_metadata_presence_rate`
- `mathjax_available_rate`
- `article_body_selector_missing_count`
- `sidebar_comment_script_contamination_count`
- `retry_success_count`
- `retry_exhausted_count`
- `elapsed_seconds`

Medium-batch thresholds:

| Metric | Threshold |
|---|---:|
| `duplicate_count` after canonicalization | `0` |
| `content_completeness_rate` | `>= 0.95` |
| `formula_valid_rate` | `>= 0.98` |
| `metadata_completeness_rate` | `>= 0.95` |
| `invalid_content_count` | `0` |
| `sidebar_comment_script_contamination_count` | `0` |
| `quality_gate_failed_count` for stored records | `0` |
| `permanent_failure_rate` | `<= 0.10` |
| consecutive source failure threshold | `<= 5` |

Formula checks:

- Inline `$...$` delimiter balance.
- Block `$$...$$` delimiter balance.
- MathJax/LaTeX source preserved.
- No half-truncated formula fragments in sampled content.

Metadata checks:

- `date`
- `category`
- `references`
- `images`

## Artifact Policy

Allowed runtime paths:

```text
.local_data/scientific_spaces/corpus/medium_batch/
corpus_runs/
corpus_outputs/
```

Required git policy:

- Runtime Article stores remain ignored.
- Seed inputs containing real corpus URLs remain ignored unless they are tiny synthetic fixtures.
- Aggregate committed reports must not include article bodies or full HTML.
- Do not commit PDFs, HTML dumps, screenshots, images, traces, profiles, Playwright reports, cache, FAISS indexes, embedding caches, runtime databases, or article corpus JSON.

Pre-commit artifact check:

```bash
git status --short
git diff --stat
git ls-files | grep -E '(\.env$|\.sqlite$|\.sqlite3$|\.db$|\.pdf$|\.html$|node_modules|\.local_data|corpus_runs|pdf_exports|trace|profile|FAISS|faiss|embedding.*cache)' || true
git ls-files -o --exclude-standard
```

Current ignore status:

- `.gitignore` already covers `.local_data/`, corpus runtime directories, progress/failure/validation files, PDFs, HTML snapshots, traces, profiles, FAISS indexes, embedding caches, and Node/Python caches.

## Human Review Plan

Each phase requires a small manual review sample before moving forward.

Sample requirements:

- At least 5 articles after each phase.
- Include formula-heavy content when available.
- Include at least one article with images when available.
- Include at least one short or unusual article when available.
- Include older seed-list articles when the approved seed input contains them.

Review checklist:

- Title is correct.
- Content starts with article body, not page chrome.
- Content length is reasonable for the article type.
- Sidebar/comment/share script/navigation content is absent.
- Markdown heading structure is preserved.
- Formula delimiters are balanced.
- Images metadata is preserved.
- References metadata field is preserved.
- Article URL is canonical.

## Risks

1. RSS coverage scope
   - RSS remains a recent-window source and cannot provide historical corpus coverage by itself.

2. Seed coverage bias
   - Human-provided seed lists may overrepresent specific eras or topics.

3. Browser runtime dependency
   - Playwright Chromium availability, browser version drift, and local network conditions can affect batch stability.

4. Source volatility
   - Scientific Spaces access behavior, HTML structure, RSS output, or robots policy can change.

5. Parser drift
   - Unseen historical article structures may expose parser edge cases.

6. Runtime storage size
   - JSON Article storage remains acceptable for planning and bounded pilots, but full corpus durability should follow the persistence roadmap.

7. Repeated source pressure
   - Medium batch size increases cumulative requests and must remain low-frequency, interruptible, and review-gated.

8. PDF coupling risk
   - PDF export is independently feasible but must not be coupled into the Article import batch without a separate export gate.

## Recommendation

Recommendation:

A: Ready for P1-003 20-article medium batch phase

Rationale:

- P1-001 successfully imported and validated 10 real articles with no duplicate or content-quality failures.
- Current safeguards cover canonicalization, polite browser access, parser quality gates, runtime-only storage, and artifact exclusion.
- The existing pilot cap remains correct; a 100-article batch should proceed only through phased approval, starting with a 20-article execution gate.

Next task:

- Execute P1-003 as a 20-article medium-batch phase or create the required medium-batch runner revision if the current 30-article pilot cap is insufficient for the planned staged execution.
