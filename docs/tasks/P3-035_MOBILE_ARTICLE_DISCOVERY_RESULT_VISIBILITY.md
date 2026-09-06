# P3-035 Mobile Article Discovery Result Visibility

## Status

PASS / CLOSED

## Task Identity

Make the first useful Article result visible in the initial mobile and
short-landscape viewport without removing search, sorting, pagination, or
Focused Session capture behavior.

## Authoritative Baseline

- Starting commit and cached `origin/main`:
  `c248eb43ce69ba14d8836f4a81a7f27f522d2ca0`
- Starting ahead / behind: `0 / 0`
- Entry worktree, index, and untracked set: clean
- Previous task: P3-034 PASS / CLOSED
- P3-034 docs-only closure exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34006691288`
- Required closure jobs: PASS; normal-main Docker and release jobs skipped as
  designed; uploaded artifacts: 0
- `REWORK.md` and `.audit`: absent
- Formal version: `v1.1.0`; candidate version: not assigned
- The product owner directed continued platform and GUI improvement with
  independent sub-agent review and no recurring plan-confirmation pauses.

## Background

Controlled local Chromium measurements against the existing isolated fixture
runtime show that the first Article begins at `y=712` in `390x844`, `y=780` in
`320x844`, and `y=491` in `720x450`. Search controls, top pagination, and the
always-expanded zero-selection Focused Session controls consume the result
viewport before the primary discovery content. The existing behavior is
functionally correct and horizontally responsive, but the information priority
is inverted on constrained screens.

## Goals

1. Surface the first Article title and useful preview content in portrait
   mobile viewports without initial scrolling.
2. Surface the first Article title in the `720x450` short-landscape viewport.
3. Keep search and sort usable at `320px` without horizontal overflow.
4. Keep Focused Session page selection, individual selection, add, clear,
   open, feedback, failure, and keyboard behavior complete.
5. Keep multi-page navigation complete while placing it after current results.

## Non-Goals

- Backend, API, persistence, source, Article record, corpus, Graph, Reference,
  Tutor, Zotero, or derived-asset changes
- Search ranking, page size, URL, history, or data-contract changes
- A site-wide redesign, localization project, or new navigation framework
- Dependency, lockfile, workflow, candidate, version, tag, Release, or
  attestation changes
- Source network, external search, private Zotero, or real/paid Provider access

## Public Test Seams

1. The rendered `/articles` workspace at `1440x900`, `390x844`, `320x844`, and
   `720x450`, observed through public controls and element bounding boxes.
2. Existing Article search, paging, selection, Focused Session, feedback, and
   keyboard interactions in Product E2E.

## Allowed Changes

- `frontend/src/components/ArticleListView.tsx`
- `scripts/e2e/run_product_e2e.py`
- this canonical task, `alignment.md`, `docs/tasks/CURRENT_TASK.md`,
  `docs/00_PROJECT_STATE.md`, `roadmap.md`, `docs/V1_2_ROADMAP.md`, `README.md`,
  and the P3-035 evidence report

## Prohibited Actions

- Any `backend/**`, API, persistence, storage, frozen M1, source/Article record,
  corpus, Graph/Reference data, matcher, provider, or derived-asset change
- Any dependency, lockfile, framework configuration, workflow, release/version,
  candidate, tag, Release, or attestation change
- Any source access, external search, private Zotero read/mutation, real/paid
  Provider call, or non-loopback browser request
- Force push, history rewrite, destructive Git action, or published-tag change
- Runtime/private artifacts, secrets, databases, PDFs, downloaded HTML, images,
  screenshots, traces, profiles, caches, or generated corpora in Git

## Deliverables

- Compact mobile Article discovery controls with unchanged functionality
- Result-following pagination
- Responsive first-result visibility assertions in Product E2E
- Regression evidence for search, paging, selection, feedback, and keyboard use
- `docs/P3_035_MOBILE_ARTICLE_DISCOVERY_RESULT_VISIBILITY_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. With loaded results and no selection, the first Article title and preview
   intersect the initial `390x844` and `320x844` viewports.
2. The first Article title intersects the initial `720x450` viewport.
3. Search input, sort, Search, and Clear remain visible, usable, and horizontally
   contained at every required viewport.
4. Pagination follows the current result list, is omitted when only one page is
   present, and preserves existing previous/next behavior when multiple pages
   exist.
5. Zero-selection Session capture exposes the useful selection/open actions
   without reserving space for unavailable mutations. Selecting one or a full
   page exposes Clear and Add actions and preserves all existing outcomes.
6. Keyboard order, focus feedback, storage failure, capacity, duplicate, stale
   result, query, sort, page, and browser history behavior remains correct.
7. No page-level horizontal overflow occurs at `1440x900`, `390x844`,
   `320x844`, or `720x450`.
8. Focused Frontend tests, production build, full Backend regression, three
   Product E2E runs, two independent final reviews, and repository safety gates
   pass.
9. Implementation and closure commits each pass exact-SHA main CI; final
   `main` is clean and synchronized.

### CONDITIONAL

No conditional closure. Loss of a discovery or Session action keeps the task
open.

### BLOCKED

- A required Article result remains outside its initial viewport target.
- Compaction hides or breaks a search, paging, selection, Session, feedback, or
  keyboard workflow.
- Correctness requires a prohibited Backend, API, data, dependency, workflow,
  external/private, Provider, or release change.
- A required test, review, safety, artifact, or exact-SHA CI gate cannot be
  repaired within the allowlist.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Preserve the measured browser RED evidence at the rendered workspace seam.
2. Compact the mobile search command layout.
3. Render selection-only Session mutations only when a selection exists.
4. Move pagination after results and omit it for a single result page.
5. Add bounded viewport and full interaction regression assertions.
6. Run focused/full local gates and obtain two independent final reviews.
7. Commit and non-force push implementation, verify exact-SHA CI, then create
   and push a docs-only closure commit and verify its exact-SHA CI.

## Verification Commands

- `npm --prefix frontend run test:articles`
- `npm --prefix frontend run test:references`
- `npm --prefix frontend run test:tutor`
- `npm --prefix frontend run test:graph`
- `npm --prefix frontend run build`
- `uv run --project backend --extra dev pytest -q`
- `uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
- repository workflow, suppression, dependency, secret, temporary SBOM,
  artifact, and protected-path gates
- exact-SHA GitHub Actions readback for implementation and closure commits

## Git Plan

- Implementation commit: `fix: prioritize mobile article results`
- Push: non-force `main` push after all local gates and final reviews pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-035 mobile article discovery`
- Push: non-force `main` push after implementation CI evidence is recorded
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Local Gate Result

PASS. Focused Frontend tests passed `139/139`; the production build produced 11
routes; Backend regression passed with 600 tests and 4 skips; Product E2E passed
3/3 complete runs with 221 checks per run, restart persistence PASS, and zero
external requests, unexpected console errors, or page errors. Two independent
final reviewers reported 0 Critical and 0 Important findings. Workflow,
suppression, dependency, secret, temporary SBOM, artifact, and protected-path
gates pass. Implementation commit
`6f5844c80b092a1919f20e5e93f75a9b6ae1e38a` passed exact-SHA main CI run
[`34010502972`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34010502972)
with every required job passing and zero uploaded artifacts. This docs-only
closure commit consumes the remaining P3-035 authorization and requires its own
exact-SHA main CI readback.

## Stop Conditions

Stop rather than widen scope if an unknown worktree change appears or correct
behavior needs any prohibited Backend, API, persistence, data, dependency,
workflow, external/private, Provider, or release change.
