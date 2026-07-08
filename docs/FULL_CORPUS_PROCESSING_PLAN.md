# Full Scientific Spaces Corpus Processing Plan

## Current Status

Scientific Spaces AI Learning OS v1.0.0 MVP is complete.

Current verified baseline:

- M1 Source Pipeline: PASS
- M1 Verification: PASS
- M1 Final Freeze: PASS
- M1 PDF Export Capability: PASS
- M2-M7 verification gates: PASS
- Post-MVP release readiness: PASS
- Production deployment profile: PASS
- Security and privacy baseline: PASS
- RAG and tutor evaluation harness: PASS

This document is a P1 planning artifact only. It does not execute full-corpus sync, generate PDFs, store article bodies, modify frozen M1-M7 contracts, move the `v1.0.0` tag, or create a new release.

Relevant baseline evidence:

- `docs/M1_FINAL_FREEZE_REPORT.md` freezes RSS discovery, Playwright browser article access, parser, converter, storage, validation, and independent PDF export interfaces.
- `docs/M1_BROWSER_ACCESS_QUALITY_REVISION.md` verifies that browser acquisition rejects title-only or shell HTML without an article body.
- `docs/M1_SOURCE_ACCESS_STRATEGY_REVISION.md` records RSS discovery as the replacement for blocked homepage/archive discovery for recent articles.
- `docs/M1_PDF_EXPORT_EVALUATION.md` records independent PDF export feasibility with 5/5 live PDF exports.
- `docs/PRODUCTION_DEPLOYMENT_PROFILE.md` records local runtime data paths and deployment boundaries.
- `docs/SECURITY_PRIVACY_BASELINE.md` records artifact, privacy, provider, and local data constraints.

Documentation hygiene note:

- `docs/31_MVP_BOUNDARY.md` is absent in the current repository and is already recorded as a post-MVP documentation gap. This plan follows the verified MVP boundary reports instead.

## Scope

Full corpus scope means a controlled, source-policy-compliant attempt to process Scientific Spaces article pages that satisfy all of these conditions:

- The URL canonically resolves to an article path shaped as `/archives/{numeric_id}`.
- The URL is discovered from an approved source: RSS/feed, explicit seed list, prior verified project data, or a separately approved low-frequency backfill method.
- The page can be fetched through the existing browser access provider without bypassing access controls.
- The parsed result satisfies Article quality gates before storage.
- The stored record uses the frozen Article schema:
  - `id`
  - `title`
  - `url`
  - `content`
  - `metadata`

Out of scope for this plan:

- Full crawl execution.
- Full PDF export execution.
- Search-page scraping.
- Unbounded archive pagination.
- High-concurrency crawling.
- Bypassing site access controls.
- Changing M1 RSS discovery, browser provider, parser, converter, storage schema, sync contract, or validation standards directly.
- Changing M2-M7 product contracts.
- Committing article corpus files, PDFs, HTML dumps, images, browser profiles, traces, FAISS indexes, embedding caches, or runtime progress files.

Corpus range definition:

- Initial corpus target: Scientific Spaces article URLs under `https://spaces.ac.cn/archives/{id}`.
- Alias handling target: if `https://kexue.fm/archives/{id}` appears in seed data, canonicalize the stored URL to the equivalent `spaces.ac.cn` archive URL only after URL-shape validation. Retain the original source URL in run diagnostics, not in Article metadata, unless a future contract revision explicitly adds provenance fields.
- Excluded paths: homepage, search pages, category pages, comment endpoints, login endpoints, static assets, attachments, PDFs, downloadable archives, and non-article paths.

## Existing Capabilities

Current M1 Source Pipeline can support a bounded full-corpus pilot, not uncontrolled full-corpus execution.

Available interfaces:

- RSS Discovery:
  - `backend/app/crawler/rss.py`
  - `discover_rss_article_urls(feed_url, fetch_xml, max_items) -> list[str]`
  - Verified input: `https://spaces.ac.cn/feed`
  - Verified output shape: `https://spaces.ac.cn/archives/{numeric_id}`

- Browser Access:
  - `backend/app/crawler/browser.py`
  - `BrowserArticleFetcher.fetch(url) -> BrowserFetchResult`
  - `BrowserArticleFetcher.fetch_many(urls) -> list[BrowserFetchResult]`
  - Enforces approved article body selectors before success.
  - Rejects empty HTML, non-2xx status, and HTML without an article body.

- Parser and Converter:
  - `backend/app/parser/article.py`
  - `backend/app/converter/markdown.py`
  - Preserve article body, Markdown structure, images, references, and MathJax/LaTeX delimiters.

- Storage:
  - `backend/app/storage/article_store.py`
  - JSON Article store with URL-based upsert behavior.
  - Produces frozen Article records for M2-M7 consumers.

- Validation:
  - `backend/app/validation/quality.py`
  - Validates title presence, content completeness, image URL shape, formula delimiter balance, and extraction-failure signals.

- Sync:
  - `backend/app/sync.py`
  - Supports `--max-articles`, `--source-strategy`, RSS/browser default strategy, report output, and idempotent upsert.
  - Current default max is intentionally small and must remain bounded for pilots.

- PDF Export:
  - `backend/app/export/pdf.py`
  - Independent `ArticlePdfExporter`.
  - Not wired into source sync.
  - Requires separate batch-export approval and artifact policy.

Current limits:

- RSS discovery should be treated as a recent-window discovery source, not a historical full archive source.
- The current Article store is JSON and local-first. It is acceptable for pilots, but full-corpus durability and concurrent operations require a future persistence task.
- Browser acquisition depends on Playwright Chromium and can fail transiently due to network, TLS, timeout, or site behavior.
- The existing sync command imports from the latest RSS window only unless a future P1 implementation adds seed input or dry-run/backfill controls.

## Discovery Strategy

### Candidate A: RSS / Feed

Status: approved for recent discovery.

- URL: `https://spaces.ac.cn/feed`
- Expected output: recent article links in `/archives/{numeric_id}` format.
- Strengths:
  - Official public feed.
  - Structured XML.
  - Low request count.
  - Already verified by M1.
- Limits:
  - Feed window is limited and cannot be assumed to cover the historical corpus.
  - Feed ordering and retention can change.
- Recommendation:
  - Use RSS as the first discovery source for recent articles and pilot sanity checks.

### Candidate B: Approved Seed List

Status: recommended primary strategy for full-corpus pilot and historical backfill.

Seed list sources may include:

- A manually reviewed URL list assembled from official/public references.
- Prior verified project Article records.
- Previously verified RSS-discovered URLs.
- A future operator-provided file containing only candidate article URLs.

Seed list requirements:

- Plain text or JSON input stored outside git or as a small test fixture only.
- One candidate URL per entry.
- Canonicalization dry-run before any browser access.
- Duplicates removed before fetching.
- Invalid paths rejected before fetching.
- Original source list preserved only as ignored runtime input if it contains large corpus data.

Recommendation:

- Use seed list discovery as the main historical-corpus mechanism because it avoids uncontrolled site traversal and keeps operator intent explicit.

### Candidate C: Official Archive / Index

Status: not recommended as a current primary strategy.

Evidence:

- M1 source access records show homepage and archive/index access returned `403` in the current environment.
- The implemented M1 strategy superseded homepage/archive discovery with RSS plus browser article access.

Policy:

- Do not rely on archive/index pages unless a future source access strategy revision proves a low-frequency compliant access path.
- Do not modify M1 verification standards to accept archive/index failures.

### Candidate D: Search Engine Discovery

Status: not recommended for automated corpus processing.

Assessment:

- Search queries such as `site:spaces.ac.cn/archives` can discover URLs, but automated search scraping adds source-policy, rate-limit, and terms-of-service risk.
- Search engine results can be incomplete, duplicate, canonicalization-unfriendly, or stale.

Policy:

- Do not scrape search pages.
- Allow search-engine-derived URLs only when a human exports a small reviewed seed list for a pilot.
- Record the seed provenance in runtime diagnostics, not in committed article data.

### Candidate E: Archive ID Probing

Status: low-frequency, restricted fallback only.

Assessment:

- Numeric archive IDs suggest a possible ID-space backfill, but probing every ID would be a crawl and can generate many unnecessary requests.
- This should not be the first full-corpus strategy.

Policy:

- Use only after seed-list and RSS strategies are insufficient and a separate implementation gate approves it.
- Default concurrency: `1`.
- Delay: `3-10` seconds between attempts.
- Stop after a configured consecutive-failure threshold.
- Never probe search, comment, login, asset, or attachment paths.
- Treat repeated `403`, `429`, TLS, and timeout clusters as a stop condition.
- Persist only ignored progress metadata, not HTML or article bodies.

## Recommended Strategy

Recommended phased strategy:

```text
RSS recent discovery
+ approved seed list
-> canonical URL dry-run
-> small pilot browser fetch
-> parser / converter
-> Article storage in ignored runtime path
-> validation report
-> medium batch only after pilot gate
-> full corpus only after medium-batch gate
-> optional PDF export as a separate batch
```

Primary discovery decision:

- Use approved seed lists as the primary full-corpus strategy.
- Use RSS as a recent-article discovery and freshness source.
- Keep archive ID probing as a low-frequency, separately approved fallback.
- Do not use search pages as an automated input.

M1 frozen-contract handling:

- Do not modify existing M1 behavior in-place for full-corpus work.
- Any implementation change must be created as a new P1/M1.x revision task with tests and a gate.
- The first implementation task should add dry-run and seed/canonicalization support without changing the existing RSS/browser default behavior.

Operational flow for P1-001:

1. Load seed candidates from an ignored runtime file or small fixture.
2. Canonicalize URLs and generate a dry-run report.
3. Fetch at most `10-30` pilot articles with Playwright Chromium.
4. Parse and validate each article before writing.
5. Skip quality-gate failures without writing to storage.
6. Write Article records only to an ignored runtime data directory.
7. Emit a validation summary with counts, rates, failure reasons, and stop-condition status.

## Canonical URL Policy

Canonical article URL format:

```text
https://spaces.ac.cn/archives/{numeric_id}
```

Canonicalization rules:

- Accept only `http` or `https` URLs with host `spaces.ac.cn`, `www.spaces.ac.cn`, `kexue.fm`, or `www.kexue.fm`.
- Convert `http` to `https`.
- Convert `www.spaces.ac.cn` to `spaces.ac.cn`.
- Convert `kexue.fm` and `www.kexue.fm` archive URLs to `spaces.ac.cn` archive URLs after path validation.
- Remove query strings and fragments.
- Strip trailing slash.
- Reject non-numeric archive paths.
- Reject PDFs, images, static assets, search pages, category pages, comment pages, login pages, attachment paths, and external hosts.

Duplicate policy:

- Deduplicate by canonical URL before browser access.
- Store Article records under the canonical URL.
- Track duplicate counts in runtime reports.
- Preserve original seed URL only in ignored run diagnostics so the Article schema remains unchanged.

Redirect policy:

- Browser fetch may observe redirects, but the stored URL remains the prevalidated canonical URL unless a future contract revision explicitly records final URL provenance.
- If a canonical URL redirects to a non-article path or external host, mark it as a permanent failure and do not store it.

## Polite Crawling Policy

Default execution policy:

- Concurrency: `1`.
- Request delay: randomized `3-10` seconds between article fetches.
- Retry count: at most `2` retries after the first attempt.
- Backoff: exponential backoff with jitter, starting at `3` seconds and capped at `60` seconds.
- Browser timeout: bounded per existing provider policy.
- User agent: project-identifying, reasonable, and non-deceptive.
- Downloads: disabled; PDF/archive requests aborted unless running the separately approved PDF export task.
- Browser context: non-persistent, no profile reuse committed.

Robots and source policy:

- Check `robots.txt` before each new source strategy or domain policy change.
- Do not access disallowed paths.
- Do not access search pages.
- Do not traverse comment, login, admin, static asset, attachment, or API paths.
- Do not bypass access controls.
- Do not use high-frequency retries to overcome `403`, `429`, or timeouts.

Failure classification:

| Failure | Classification | Default action |
|---|---|---|
| Single timeout | Browser transient failure | Retry with backoff; record if retry succeeds |
| TLS handshake timeout | Browser/source transient failure | Retry with backoff; stop if clustered |
| Single `403` | Access failure | Record and skip; do not bypass |
| Repeated `403` cluster | Stop-condition risk | Stop batch and require human review |
| `429` | Rate-limit signal | Stop batch or pause according to configured cooldown |
| Non-article HTML | Invalid content failure | Do not store; record blocker for that URL |
| Missing article body selector | Invalid content failure | Do not store; record parser/browser quality issue |
| Formula delimiter imbalance | Data-quality blocker | Do not store or quarantine; require parser/validation revision |
| Sidebar/comment/script contamination | Data-quality blocker | Do not store; require parser/validation revision |

Quality-gate rule:

- Quality gate failures must never be written into Article storage.
- Invalid imported content is a blocker for that batch phase.
- Transient browser failures are non-blocking only when enough successful articles remain to satisfy that phase's validation gate and failure thresholds.

Default stop conditions:

- `invalid_content_count > 0` for pilot.
- `duplicate_count > 0` after canonicalization for pilot.
- `content_completeness_rate < 0.95`.
- `formula_valid_rate < 0.98`.
- `metadata_completeness_rate < 0.95`.
- Consecutive source failures exceed `5`.
- Overall permanent failure rate exceeds `10%`.
- Any evidence of forbidden content contamination in stored Article content.

## Storage and Artifact Policy

Runtime storage policy:

- Article runtime storage remains outside git under `.local_data/scientific_spaces/` or another ignored operator-selected directory.
- Full-corpus run reports, checkpoints, failure logs, seed inputs, and progress files must be written only to ignored runtime paths.
- Do not commit article corpus JSON files.
- Do not commit PDFs.
- Do not commit HTML dumps.
- Do not commit images, attachments, browser profiles, traces, screenshots, Playwright reports, FAISS indexes, embedding caches, or runtime databases.

Recommended ignored runtime layout:

```text
.local_data/scientific_spaces/
  articles.json
  validation_report.json
  corpus_runs/
    <run-id>/
      seed_input.json
      canonicalization_report.json
      progress.json
      failures.json
      validation_summary.json
      pdf_exports/
```

Commit policy:

- Commit only code, tests, small synthetic fixtures, and documentation.
- Keep real corpus inputs and outputs untracked.
- Before committing any corpus-processing task, run:

```bash
git status --short
git diff --stat
git ls-files | grep -E '(\.env$|\.sqlite$|\.sqlite3$|\.db$|\.pdf$|\.html$|node_modules|\.local_data|corpus_runs|pdf_exports|trace|profile|FAISS|faiss|embedding.*cache)' || true
git ls-files -o --exclude-standard
```

Persistence note:

- JSON Article storage is acceptable for the pilot.
- Medium and full-corpus phases should be evaluated against the persistence roadmap before becoming default workflows.
- Full-corpus Article storage migration to SQLite or another durable store should be a separate persistence task, not part of the pilot.

## Validation Metrics

Every pilot or batch run must record:

- `discovered_url_count`
- `canonical_url_count`
- `duplicate_count`
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

Pilot validation gate:

| Metric | Required pilot threshold |
|---|---:|
| `attempted_count` | `10-30` |
| `duplicate_count` after canonicalization | `0` |
| `content_completeness_rate` | `>= 0.95` |
| `formula_valid_rate` | `>= 0.98` |
| `metadata_completeness_rate` | `>= 0.95` |
| `invalid_content_count` | `0` |
| `sidebar_comment_script_contamination_count` | `0` |
| `quality_gate_failed_count` | `0` stored; skipped URLs allowed only with explicit reasons |
| `permanent_failure_rate` | `<= 0.10` |

Medium-batch validation gate:

- Attempt exactly `100` canonical URLs unless stop conditions trigger earlier.
- Preserve all pilot thresholds.
- Require idempotent re-run with `duplicate_count=0`.
- Require validation summary to be stable across repeat run.

Full-corpus gate:

- Requires successful medium batch.
- Requires approved operator seed strategy.
- Requires persistence and backup plan.
- Requires runbook for pause, resume, rollback, and cleanup.
- Requires explicit go/no-go review before execution.

## Pilot Plan

### Phase 1: Seed List Evaluation and Canonicalization

Goal:

- Validate the discovery input before any browser access.

Inputs:

- RSS recent URLs.
- Approved seed list of candidate archive URLs.

Actions:

- Parse seed entries.
- Canonicalize URLs.
- Reject invalid hosts and paths.
- Deduplicate.
- Produce dry-run counts.

Stop condition:

- Any seed source includes non-article paths at a rate above `5%`.
- Canonicalization produces duplicate ambiguity that cannot be explained.
- Source provenance is unknown or not approved.

Validation gate:

- `canonical_url_count > 0`
- `duplicate_count=0` after canonicalization
- `rejected_url_count` explained by reason
- No browser fetch performed in this phase

Artifact policy:

- Runtime seed and canonicalization reports stay under ignored `corpus_runs/<run-id>/`.
- Commit only tiny synthetic canonicalization fixtures if tests are added.

Rollback / resume behavior:

- Dry-run only; delete the run directory to rollback.
- Resume by reusing the same seed input and run ID.

### Phase 2: Small Pilot Import, 10-30 Articles

Goal:

- Prove the full source pipeline works beyond the RSS freeze sample without scaling risk.

Actions:

- Fetch `10-30` canonical article URLs.
- Use Playwright Chromium with concurrency `1`.
- Apply delay, retry, and failure logging.
- Parse, convert, validate, and store only passing Article records.
- Run duplicate/idempotency check by repeating the same pilot.

Stop condition:

- `invalid_content_count > 0`
- `formula_valid_rate < 0.98`
- `content_completeness_rate < 0.95`
- `duplicate_count > 0`
- Repeated `403`, `429`, timeout, or TLS cluster exceeds threshold.

Validation gate:

- Pilot thresholds in `Validation Metrics` pass.
- Repeat run imports no duplicate records.
- No sidebar/comment/share/script/navigation contamination.
- Validation issues are empty or only clearly classified non-blocking transient fetch failures.

Artifact policy:

- Article store, validation report, failure log, and progress file are ignored runtime files.
- No PDFs or HTML dumps are generated.

Rollback / resume behavior:

- Rollback by deleting the pilot runtime directory.
- Resume from progress file by skipping already imported canonical URLs and retrying failed transient URLs only within retry limits.

### Phase 3: Medium Batch, 100 Articles

Goal:

- Validate operational stability before full corpus processing.

Actions:

- Process `100` canonical URLs from the approved seed list.
- Keep concurrency `1`.
- Keep delay `3-10` seconds.
- Enforce all pilot quality gates.
- Produce a batch summary with failure taxonomy.

Stop condition:

- Any data-quality blocker.
- Permanent failure rate above `10%`.
- Transient failures cluster by source or time window.
- Runtime storage corruption or non-idempotent upsert behavior.

Validation gate:

- Pilot thresholds still pass.
- Re-run against the same seed range produces `duplicate_count=0`.
- Failure reasons are auditable and bounded.

Artifact policy:

- Runtime batch directory remains ignored.
- Commit only aggregate report templates or code/tests if a separate implementation task is approved.

Rollback / resume behavior:

- Resume from checkpoint after operator confirmation.
- Rollback by restoring prior runtime data backup or deleting the batch runtime directory.

### Phase 4: Full Corpus Processing

Goal:

- Process the approved corpus range under controlled operational limits.

Prerequisites:

- Phase 1-3 gates pass.
- Human go decision recorded.
- Persistence and backup policy accepted.
- Source access strategy reviewed.
- Runtime disk space and browser dependency verified.

Actions:

- Process in small windows.
- Pause after each window for validation summary review.
- Preserve idempotent upsert behavior.
- Keep failure logs and progress checkpoints ignored.

Stop condition:

- Any source-policy concern.
- Data-quality blocker.
- Site-side rate-limit or access-change signal.
- Validation rate below thresholds.
- Operator cancels or disk/runtime limits are reached.

Validation gate:

- Each window passes validation before the next window starts.
- Final run report records all required metrics.
- M2-M7 consumers can read the resulting Article store without contract changes.

Artifact policy:

- Full corpus Article store remains a private runtime artifact.
- No article bodies, PDFs, images, HTML, or runtime reports are committed.

Rollback / resume behavior:

- Resume by checkpoint window and canonical URL.
- Rollback by restoring runtime backup taken before the full run.

### Phase 5: Optional Batch PDF Export

Goal:

- Generate PDFs only after Article content processing is independently accepted.

Actions:

- Use `ArticlePdfExporter` in a separate command or task.
- Process only approved canonical article URLs.
- Store PDFs under ignored runtime export directories.
- Validate each PDF exists, has size greater than zero, and has a valid `%PDF-` header.

Stop condition:

- PDF success rate below an approved threshold.
- MathJax availability drops unexpectedly.
- Generated PDFs include layout defects that make formulas unreadable.
- Source access returns repeated `403`, `429`, or timeouts.

Validation gate:

- PDF technical validity passes.
- MathJax rendering evidence is recorded.
- All generated artifacts remain ignored.

Artifact policy:

- PDFs are never committed.
- PDF export is not wired into `python -m app.sync`.
- PDF export remains independent from RAG and reader content pipelines.

Rollback / resume behavior:

- Delete the ignored PDF export directory to rollback.
- Resume by skipping existing valid PDFs only within the ignored runtime directory.

## PDF Export Plan

PDF export should remain separate from Article content processing.

Reasons:

- Article content storage is the source of truth for Reader, RAG, Learning, Graph, and Tutor.
- PDF generation is slower and heavier than article parsing.
- PDF output can create large copyrighted/runtime artifacts.
- PDF visual quality may need a separate print-style review.

Recommended batch PDF boundaries:

- Separate operator command.
- Separate ignored output root.
- Explicit URL or Article ID input.
- Concurrency `1`.
- Delay `3-10` seconds.
- Bounded retry and failure logging.
- Validate PDF file existence, non-zero size, and `%PDF-` header.
- Delete failed partial PDFs immediately.
- Do not commit PDF artifacts.

Batch PDF should not proceed until:

- Article pilot and medium-batch gates pass.
- Export output directory policy is approved.
- Disk usage limits are configured.
- Copyright/source-use expectations are reviewed by the operator.

## Risks

RSS coverage scope:

- RSS is reliable for recent discovery but not a full historical archive.
- Mitigation: seed list strategy for historical backfill.

Seed list quality:

- Human or external seed lists can contain duplicates, aliases, stale URLs, or non-article paths.
- Mitigation: dry-run canonicalization and rejection report before browser access.

Browser runtime dependency:

- Playwright Chromium must be installed and stable.
- Mitigation: preflight check and bounded pilot before medium/full batch.

Transient browser/source access fluctuation:

- Timeout, TLS, `403`, or `429` can happen independently of code quality.
- Mitigation: retry with backoff, failure taxonomy, and stop conditions.

Invalid content failure:

- Source HTML can be title-only, shell-only, or structurally changed.
- Mitigation: existing article body selector gate plus parser validation before storage.

External site changes:

- DOM structure or feed behavior may change.
- Mitigation: keep selector changes behind M1.x revision tasks and regression tests.

Storage scale:

- JSON Article storage may become large and less robust for full corpus.
- Mitigation: pilot with JSON, then assess persistence upgrade before full run.

Artifact/privacy/copyright risk:

- Full article bodies, PDFs, images, and HTML dumps are runtime artifacts and must not be committed.
- Mitigation: strict `.gitignore`, pre-commit artifact checks, and runtime-only output directories.

Downstream rebuild cost:

- Larger Article sets can increase RAG indexing, graph building, and frontend response costs.
- Mitigation: batch validation, benchmark tasks, and keep FAISS/vector indexes rebuildable.

Scope creep:

- Corpus processing can accidentally become search/RAG/tutor enhancement work.
- Mitigation: keep P1-001 limited to discovery, canonicalization, pilot import, validation, and reports.

## Go / No-Go Criteria

### Phase 1 Go

Proceed to small pilot only if:

- Approved seed input exists.
- Canonicalization accepts article URLs and rejects invalid paths.
- `duplicate_count=0` after canonicalization.
- No browser access was needed to validate the seed shape.

### Phase 2 Go

Proceed to medium batch only if:

- `10-30` article pilot completes.
- `content_completeness_rate >= 0.95`.
- `formula_valid_rate >= 0.98`.
- `metadata_completeness_rate >= 0.95`.
- `invalid_content_count=0`.
- `duplicate_count=0`.
- No sidebar/comment/script contamination is detected.
- Repeat run remains idempotent.

### Phase 3 Go

Proceed to full corpus only if:

- `100` article batch passes the same quality thresholds.
- Permanent failure rate is `<= 10%`.
- Transient failure clusters are understood.
- Runtime storage backup/restore procedure is documented.
- Operator approves full corpus execution.

### Phase 4 Go

Accept full-corpus output only if:

- Every processing window passes validation.
- Final report contains all required metrics.
- Article schema remains unchanged.
- No runtime corpus artifact is committed.
- Downstream M2-M7 consumers can operate on the Article store without contract changes.

### Phase 5 Go

Proceed with optional batch PDF export only if:

- Article content processing is accepted.
- PDF output directory and cleanup policy are approved.
- Runtime disk and time budget are explicit.
- PDF artifacts remain ignored and uncommitted.

No-go conditions:

- Any attempt to bypass access controls.
- Any high-frequency or uncontrolled crawling.
- Any data-quality blocker in stored Articles.
- Any forbidden artifact staged for commit.
- Any required M1-M7 contract change outside an approved revision task.

## Recommended Next Task

P1-001 Full Corpus Pilot Implementation / Gate
