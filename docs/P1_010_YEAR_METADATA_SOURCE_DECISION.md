# P1-010 Year Metadata Source Decision

## Current Status

- P1-009: CONDITIONAL
- P1-010 Source Decision: PASS
- Decision: B: Continue cumulative-only expansion; defer year-based legacy stress
- Recommended next task: P1-011 Cumulative 400-Article Batch

This is a source decision record only. It does not fetch article body pages, does not execute the 400-article batch, does not execute full corpus processing, does not generate PDFs, and does not commit runtime artifacts or the full `article_list.json`.

## Problem

P1-007 verified the approved seed URL inventory:

- `seed_count=1326`
- `canonical_url_count=1326`
- `duplicate_count=0`
- `rejected_url_count=0`

P1-009 then implemented a year metadata enrichment workflow, but could not produce a high-confidence per-article year map:

- Seed article entries contain `id`, `url`, and `title`.
- Seed article entries do not contain reliable per-article `year` or `date`.
- Seed global `year_stats` exists, but it is aggregate-only and cannot map an individual article ID to a year.
- Live access to `https://spaces.ac.cn/content.html` returned HTTP 403.
- No approved offline archive index snapshot is available.
- `mapped_article_count=0`.
- `unknown_year_count=1326`.
- No article body fetch was performed.
- No `Article.content` import was performed.

The result is that year-based legacy stress remains blocked, but cumulative content expansion is not blocked. The cumulative path only needs a canonical URL list and the existing Article quality gates, both of which are already available.

## Options Considered

### Option A: Approved Offline `content.html` Snapshot

Description:

- Use a user-provided, approved snapshot of `https://spaces.ac.cn/content.html`.
- Parse year sections from the archive index.
- Build a high-confidence `article_id -> year` mapping without visiting article body pages.
- Validate derived `year_stats` against seed global `year_stats`.

Pros:

- Preserves the original year-based legacy stress design.
- Does not require article body fetches.
- Produces auditable high-confidence per-article year metadata if the archive index is complete.
- Can reopen P1-009 as a targeted P1-009.1 revision.

Cons:

- Requires the user to provide an approved archive index snapshot.
- Current live access returns HTTP 403.
- Snapshot freshness and provenance must be checked.
- Mapping still needs aggregate validation against seed global `year_stats`.

Decision:

- Keep as the preferred future path for year-based stress.
- Do not block cumulative 400 on this missing source.

### Option B: Cumulative-Only 400 Batch

Description:

- Continue from 200 valid Articles to 400 valid Articles using the approved seed URL inventory.
- Preserve cumulative staged execution gates.
- Keep year-based legacy claims out of scope.

Pros:

- P1-008 already proved the cumulative path to 200 valid Articles.
- Does not depend on `content.html` or per-article year metadata.
- Continues to test browser acquisition, parser quality gates, storage, resume, idempotency, and source pressure.
- Avoids waiting on an unavailable archive index.
- Keeps full corpus processing staged rather than one-shot.

Cons:

- Does not provide explicit year-based legacy coverage.
- Old-article coverage is controlled by seed order, not high-confidence year partitions.
- Later full corpus planning still needs a year metadata source decision if year-based stress remains required.

Decision:

- Selected.

### Option C: Runtime Article Metadata Partial Enrichment

Description:

- Use date metadata from already imported runtime Articles.
- Build partial year evidence for the 200 imported Article subset.

Pros:

- Requires no archive index access.
- Uses already validated imported Articles.
- Useful as a sanity check for currently imported runtime data.

Cons:

- Covers only imported runtime Articles, not the 1326-entry seed.
- Cannot generate full seed year partitions.
- Cannot replace archive index mapping for year-based legacy stress.

Decision:

- Allow as auxiliary validation only.
- Do not treat as a full seed year metadata source.

### Option D: Archive ID Heuristic

Description:

- Infer year from archive ID order and seed global `year_stats`.

Pros:

- Does not need additional source access.
- Could produce a synthetic partition quickly.

Cons:

- Archive IDs are not authoritative year metadata.
- The result would be low-confidence.
- It risks false year-based stress claims.
- It is not suitable for precise legacy stress planning.

Decision:

- Rejected as a primary source.
- Do not use archive ID order to claim year-based coverage.

## Decision

B: Continue cumulative-only expansion; defer year-based legacy stress.

P1-011 should execute the cumulative 400-article batch without claiming year-based coverage. P1-009 remains CONDITIONAL. Year-based legacy stress remains blocked until high-confidence per-article year mapping exists.

## Rationale

Cumulative 400 is not blocked by year metadata because it does not require selecting articles by year. It requires:

- A canonical seed URL inventory.
- A bounded fetch policy.
- Browser acquisition and parser quality gates.
- Storage idempotency.
- No invalid imported content.
- Runtime artifact isolation.

Those requirements are satisfied by the current P1 path:

- P1-007 validated 1326 canonical seed URLs.
- P1-008 imported 200 valid Articles with `duplicate_count=0`.
- P1-008 ended with `invalid_imported_content_count=0`.
- P1-008 recorded `content_completeness_rate=1.0`, `formula_valid_rate=1.0`, and `metadata_completeness_rate=1.0`.
- P1-008 verified final idempotent rerun with `attempted_count=0`.

The missing year source only blocks year-based legacy stress and year partition claims. It does not block the next cumulative count expansion.

## Constraints for Next Batch

P1-011 Cumulative 400-Article Batch must follow these constraints:

- Do not make year-based coverage claims.
- Do not claim legacy stress completion.
- Use `delay_seconds >= 8`.
- Keep `concurrency = 1`.
- Keep `max_consecutive_failures <= 5`.
- Require `invalid_imported_content_count = 0`.
- Require duplicate count to remain 0.
- Preserve parser quality gates.
- Preserve final idempotent rerun evidence.
- Do not commit the full seed list.
- Do not commit runtime Article store, progress, failed URL log, validation summary, or enrichment output.
- Do not generate PDFs.
- Do not execute full corpus processing.
- Do not access search/category/tag/comment pages.

## Reopen Criteria for Year Metadata

Open a P1-009.1 Year Metadata Source Revision only when at least one of these is true:

- The user provides an approved offline `content.html` archive index snapshot.
- A different trusted archive index source is approved.
- Live `https://spaces.ac.cn/content.html` access is restored and can be fetched with one low-frequency request.
- Existing runtime or future imported Article metadata is explicitly approved as a partial-only source for a scoped validation task.

P1-009.1 can mark year enrichment PASS only if:

- Per-article year mapping covers at least 99% of seed articles.
- High-confidence mapping covers at least 99% of seed articles.
- Derived mapping `year_stats` matches seed global `year_stats`, or all differences have a clear explanation.
- Unknown year count is small and justified.
- No article body fetch is required.
- No full seed or enriched seed runtime artifact is committed.

## Recommended Next Task

P1-011 Cumulative 400-Article Batch

Expected scope:

- Continue cumulative-only import from 200 to 400 valid Articles.
- Keep year-based legacy stress out of scope.
- Keep the full corpus path staged and bounded.
- Preserve source pressure constraints and artifact policy.
