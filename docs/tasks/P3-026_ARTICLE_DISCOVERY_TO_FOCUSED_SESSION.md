# P3-026 Trustworthy Article Discovery and Focused Session Capture

## Status

PASS / CLOSED

## Task Identity

Make `/articles` a truthful, stale-safe discovery workspace from which a
learner can explicitly append selected visible Articles to the existing
browser-local Focused Session.

## Authoritative Baseline

- Starting commit: `bc722e31884994b389a8a1704157d257769884e6`
- Cached `origin/main`: `bc722e31884994b389a8a1704157d257769884e6`
- Starting ahead / behind: `0 / 0`
- Previous task: P3-025 PASS / CLOSED
- Previous exact-SHA CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33894354091`
- Formal version: `v1.1.0`
- Candidate version: not assigned
- Entry worktree, index, and untracked set: clean
- `REWORK.md` and `.audit`: absent
- Two independent product/UX reviews selected this bounded task and passed its
  automatic implementation alignment.

## Background

- Article result requests have no generation ownership. An older success or
  failure can overwrite the current query, sort, or page.
- Learning State and Bookmark reads use one all-or-nothing request. Either
  failure discards both datasets, and failed Learning State is presented as
  canonical `unread`.
- The existing Article list supports reading and source navigation but not
  direct capture into the P3-021 Focused Session. Learners must detour through
  Reader, Bookmark, and Saved Learning.
- The frozen queue already has bounded bulk append, deduplication, capacity,
  active-pointer, storage recovery, and same-tab notification behavior.

## Goals

1. Make Article result ownership generation-safe across query, sort, page,
   retry, and A-B-A request ordering.
2. Show Learning State and Bookmark availability independently and truthfully.
3. Let learners select one or more Articles on the latest committed result
   page and append them to the existing Focused Session in visible order.
4. Preserve queue order, active Article, Article URL state, and all server
   records; expose an explicit Session handoff without automatic navigation.

## Non-Goals

- Cross-page selection, recommendations, prerequisites, ranking, or generated
  study plans
- Learning State, Bookmark, progress, completion, or Article mutations
- Queue schema, item limit, order, active-pointer, or completion changes
- Reader, Dashboard, Saved Learning, Session, Graph, Tutor, or global-search
  redesign
- Backend, API, source, corpus, Graph, RAG, Reference, or Zotero changes

## Canonical Article Request Contract

1. Every result load owns a monotonically increasing generation.
2. Only the latest generation may update rows, pagination, errors, status,
   selection, or focus.
3. Query, sort, page, and explicit retry each start a new generation.
4. While the latest generation is pending or failed, previous rows are not
   actionable and selection is empty.
5. Selection is ephemeral, page-scoped, and limited to IDs in the latest
   successfully committed response.
6. A new result generation clears selection before its request resolves.

## Learning Badge Contract

1. Learning State and Bookmark requests are independent and retryable.
2. A successful Learning State list that omits an Article means canonical
   `unread`.
3. A failed or unavailable Learning State request means `Status unavailable`;
   it must never be represented as `unread`.
4. Bookmark failure does not erase or misrepresent a successful Learning State
   response, and vice versa.
5. Badge availability is informational and never controls capture eligibility
   or triggers a write.

## Focused Session Capture Contract

1. The UI provides per-row checkboxes and one explicit `Add selected to
   session` command. It does not auto-select or auto-capture.
2. Immediately before mutation, reload the current browser-local queue.
3. Append selected Articles once, in current visible result order, through one
   existing `addStudySessionItems` call and one save attempt.
4. Existing queue order and active Article remain unchanged. An empty queue
   activates the first accepted Article through existing queue semantics.
5. Duplicate, invalid, capacity-omitted, unavailable-storage, and failed-save
   outcomes are reported explicitly. Failed persistence never reports success.
6. Failed storage preserves current selection for retry. Successful persistence
   clears only Articles that were added or were already present.
7. Capture never changes query, sort, page, Bookmark, Learning State, or
   navigation. An explicit `/session` link is always available with current
   queue count.
8. Same-tab and cross-tab storage events refresh `In session` state and count.

## Accessibility And Responsive Contract

- Selection uses native labelled checkboxes and one clearly named bulk action.
- Loading and error states cannot expose actionable stale rows.
- Capture feedback uses one persistent polite, atomic live region and receives
  deterministic programmatic focus after the explicit capture command.
- Capture failure returns a usable retry path without losing selection.
- Controls and feedback fit without horizontal overflow at 1440 x 900,
  390 x 844, 320 x 844, and 720 x 450.

## Allowed Changes

- `frontend/src/components/ArticleListView.tsx`
- `frontend/src/lib/articleSessionPlanning.ts` (new pure helper)
- focused Article and Study Session tests and runners
- `scripts/e2e/run_product_e2e.py`
- P3-026 canonical, alignment, current-state, roadmap, README, and report files

`frontend/src/lib/studySession.ts` must be reused without schema or semantic
changes.

## Prohibited Actions

- Backend, published API, frozen M1, Article/source records, derived assets,
  queue schema, Learning State, Bookmark, or persistence contract changes
- Dependency, lockfile, workflow, or release metadata changes
- Source access, external search, private Zotero, real/paid Provider, or other
  non-loopback network access
- Candidate, tag, Release, attestation, force push, or history rewrite
- Runtime/private artifacts, secrets, generated corpus, PDFs, HTML dumps,
  screenshots, traces, profiles, caches, or local databases in Git

## Deliverables

- Generation-safe Article discovery and independent badge state
- Page-scoped Article selection and truthful bulk Session capture
- Pure planning tests and focused Product E2E coverage
- `docs/P3_026_ARTICLE_DISCOVERY_TO_FOCUSED_SESSION_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. A-B-A query, sort, page, and retry races cannot commit stale success or
   stale failure.
2. Pending and failed result generations expose no actionable stale rows.
3. Learning State omission after a successful read displays `unread`; failed
   state loading displays `Status unavailable`.
4. Learning State and Bookmark partial-failure directions preserve successful
   data and provide independent retry.
5. Selection resets on generation change and never includes an Article outside
   the latest committed visible page.
6. Capture reloads the queue, appends once in visible order, preserves order
   and active identity, and uses the existing 20-item limit.
7. Duplicate, capacity, invalid, storage-unavailable, and failed-save results
   are truthful; storage failure preserves selection and reports no success.
8. Capture performs zero Learning State/Bookmark writes, does not change the
   Article-list URL, and never navigates automatically.
9. Same-tab and cross-tab changes refresh queue count and `In session` state.
10. Keyboard selection, focus, live announcement, viewport intersection, and
    horizontal-overflow checks pass at all four required viewports.
11. Focused Frontend suites, production build, full Backend regression, and
    three isolated Product E2E runs pass with zero external requests and zero
    unexpected browser errors.
12. Two independent final reviews and workflow, dependency, secret, SBOM,
    artifact, and protected-path gates pass.
13. Implementation and closure commits each pass exact-SHA main CI; final
    `main` is clean and synchronized.

### CONDITIONAL

No conditional closure. An unverified state or persistence claim remains open.

### BLOCKED

- A correctness or accessibility acceptance item cannot be repaired within the
  allowed Frontend/test/documentation paths.
- A required gate fails or needs a protected-path, dependency, API, data,
  external, private, or release action.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Persist this task and alignment.
2. Add failing pure tests for selection reconciliation and capture planning.
3. Implement pure planning helpers and integrate generation-safe result loads,
   independent badges, selection, queue refresh, and capture feedback.
4. Extend Product E2E for races, partial failures, queue freshness, storage
   failures, duplicate/capacity outcomes, keyboard/focus, and responsive cases.
5. Run focused and full validation, then obtain two independent implementation
   reviews and repair in-scope findings.
6. Commit and push implementation, verify exact-SHA CI, then commit and push a
   docs-only closure and verify its exact-SHA CI.

## Verification Commands

- focused Article, Study Session, and related Frontend test runners
- `npm --prefix frontend run build`
- `uv run --project backend --extra dev pytest -q`
- `uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
- repository workflow, suppression, dependency, secret, SBOM, artifact, and
  protected-path gates
- exact-SHA GitHub Actions readback for implementation and closure commits

## Artifact And Secret Policy

Only source, tests, and bounded text evidence may be committed. All runtime
stores and generated evidence remain in temporary or ignored locations and are
deleted after validation.

## Git Plan

- Implementation commit: `feat: add article discovery session capture`
- Push: non-force `main` push after all local gates pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-026 article session capture`
- Push: non-force `main` push after closure evidence is complete
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Stop Conditions

- Unknown worktree changes or conflicts appear.
- Correct behavior requires Backend, API, queue, persistence, data, dependency,
  lockfile, workflow, external/private, Provider, or release changes.
- Tests, build, E2E, security, artifact, review, or exact-SHA CI fail without a
  deterministic in-scope repair.

## Completion Evidence

- focused Frontend tests: 119 passed
- Backend regression: 600 passed / 4 skipped
- production build: PASS, 11 routes
- Product E2E: 3/3 formal PASS plus 10/10 single-core stress PASS, 113 checks
  per run, restart persistence PASS,
  Chromium 149.0.7827.55, zero non-loopback requests, and zero unexpected
  console/page errors
- workflow, suppression, dependency, secret, temporary SBOM, artifact, and
  protected-path gates: PASS
- independent final implementation reviews: 2 PASS
- implementation commit:
  `57333916e668516ff8e04b3062ffbc3365b72236`
- exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33902645777`
- exact-SHA CI attempt 1 exposed one transient existing Graph-to-Reader
  loading timeout; attempt 2 passed every required job on the unchanged SHA
- Report: `docs/P3_026_ARTICLE_DISCOVERY_TO_FOCUSED_SESSION_REPORT.md`

## Next Task

After this docs-only closure commit passes exact-SHA main CI, run a bounded
product and GUI audit that compares the recorded transient Graph-to-Reader
transition with the Tutor result/Quiz accessibility debt. No v1.2 candidate is
assigned.
