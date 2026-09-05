# P3-030 Shell Modal-Origin Route Focus Continuity

## Status

LOCAL IMPLEMENTATION PASS / EXACT-SHA CI PENDING

## Task Identity

Repair Shell-owned modal route transitions so Global Search and the mobile
navigation drawer close coherently and transfer focus without overriding focus
owned by the destination workspace.

## Authoritative Baseline

- Starting commit and cached `origin/main`:
  `01339ab40d778e29caef60b01e5b478223d7ea19`
- Starting ahead / behind: `0 / 0`
- Previous task: P3-029 PASS / CLOSED
- Entry worktree, index, and untracked set: clean
- `REWORK.md`, `.audit`, and repository-root `AGENTS.md`: absent
- Formal version: `v1.1.0`; candidate version: not assigned
- P3-029 closure exact-SHA CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33936738702`
- The product owner authorized autonomous continuation after independent
  sub-agent review within the bounded platform-improvement goal.

## Evidence

- Global Search and Drawer links close their modal from raw `onClick` handlers,
  before a committed destination can own focus.
- Cross-workspace navigation reproducibly settles on `document.body`.
- Shell observes pathname only, so query-only history transitions can leave a
  modal mounted above a destination that focused content behind it.
- Escape restoration uses uncancelled animation-frame callbacks that can race a
  later modal or route operation.
- Existing Graph query selection deliberately focuses its selected region and
  must remain the focus owner.

## Goals

1. Separate dismissal focus restoration from accepted local route navigation.
2. Track committed route identity as normalized pathname plus search string.
3. Close Shell modals for committed pathname or query transitions.
4. Give destination components first opportunity to focus meaningful content,
   then focus `main#main-content` only if focus is `body` or disconnected.
5. Cancel deferred focus callbacks once a newer modal or route operation owns
   the interaction.
6. Cover Search, Drawer, same-URL, query history, destination ownership,
   modified clicks, and stale callbacks with deterministic regression evidence.

## Non-Goals

- Generic focus policy for navigation outside Shell-owned modals
- Graph, Reader, Tutor, Session, Dashboard, or route-view implementation changes
- Backend, API, persistence, Article, source, corpus, or frozen M1 changes
- Dependency, lockfile, workflow, candidate, tag, Release, or attestation changes
- Source access, private Zotero, real/paid Providers, or non-loopback network

## Focus Contract

1. A committed route identity consists of normalized pathname and query; hash
   changes are outside this task.
2. A dismissal restores its recorded opener only while that dismissal remains
   the current Shell focus operation.
3. Accepted same-tab local navigation closes the originating modal and arms one
   route-focus operation. Modified or new-tab activation does neither.
4. On route commit, a connected active element other than `body` owns focus.
   Shell fallback cannot override it.
5. If no destination owns focus, Shell focuses persistent main after the route
   commit. Main remains outside sequential tab order and has visible focus.
6. Same-identity activation closes the modal, preserves history and URL, and
   applies the current-main fallback.
7. Query-only Back/Forward closes any stale Shell modal; route-local focus still
   has priority over fallback.
8. Every newer open, dismiss, navigate, or route operation invalidates older
   deferred focus callbacks.

## Allowed Changes

- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/GlobalSearchDialog.tsx`
- `frontend/src/components/PrimaryNav.tsx`
- `frontend/src/lib/navigation.ts`
- `frontend/tests/navigation.test.ts`
- `frontend/scripts/test-articles.sh`
- `scripts/e2e/run_product_e2e.py`
- P3-030 canonical, alignment, current-state, roadmap, README, and report files

## Prohibited Actions

- Backend, API, storage, frozen M1, source/Article records, derived assets,
  route-view, Graph, Reader, Tutor, Session, or Provider changes
- Dependency, lockfile, framework, workflow, or release metadata changes
- Source access, external search, private Zotero, real/paid Provider, or other
  non-loopback network access
- Candidate, tag, Release, attestation, force push, or history rewrite
- Runtime/private artifacts, credentials, generated corpus, PDFs, HTML dumps,
  screenshots, traces, profiles, caches, or local databases in Git

## Deliverables

- Route-identity and modal-origin focus helpers
- Shell integration using accepted Next.js navigation events
- Accessible persistent-main fallback with stale-operation cancellation
- Pure regression tests and deterministic Product E2E coverage
- `docs/P3_030_SHELL_MODAL_ORIGIN_ROUTE_FOCUS_CONTINUITY_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. Desktop Search navigation to workspace, Article, and Graph destinations does
   not leave focus on `body`.
2. Mobile Drawer cross-workspace navigation does not leave focus on `body`.
3. Same-URL activation closes the modal, creates no history entry, and places
   focus on current main when no route-local target owns it.
4. Pathname/query Back and Forward close stale Shell modals and never leave
   focus behind an active `aria-modal` surface.
5. Existing same-route Graph selection and Reader navigation focus targets win
   over Shell fallback.
6. Stale opener and main-focus callbacks are inert after a newer interaction.
7. Escape, Close, and backdrop dismissal restore the opener; modified/new-tab
   activation keeps the current modal open and arms no focus transfer.
8. Initial hydration causes no focus jump; URL, history, and scroll contracts
   remain stable.
9. Main is programmatically focusable, outside sequential tab order, and has a
   visible focus treatment.
10. Focused Frontend tests, production build, full Backend regression, three
    Product E2E runs, two independent final reviews, and repository safety gates
    pass with zero external requests or unexpected console/page errors.
11. Implementation and closure commits each pass exact-SHA main CI; final
    `main` is clean and synchronized.

### CONDITIONAL

No conditional closure. Unverified modal or route focus ownership keeps the
task open.

### BLOCKED

- Focus can remain on `body`, behind a modal, or be stolen from a destination.
- Correctness requires a prohibited Backend, route-view, dependency, workflow,
  external/private, Provider, or release change.
- A required test, review, security, artifact, or exact-SHA CI gate cannot be
  repaired within allowed paths.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Persist this bounded task and alignment.
2. Add failing pure and browser regression coverage.
3. Implement route identity, accepted-navigation handling, focus ownership, and
   stale-callback cancellation in the Shell boundary.
4. Run focused and full local gates; obtain two independent final reviews and
   repair every in-scope Critical or Important finding.
5. Commit and push implementation, verify exact-SHA CI, then create and push a
   docs-only closure commit and verify its exact-SHA CI.

## Verification Commands

- `npm --prefix frontend run test:articles`
- `npm --prefix frontend run test:references`
- `npm --prefix frontend run test:tutor`
- `npm --prefix frontend run test:graph`
- `npm --prefix frontend run build`
- `uv run --project backend --extra dev pytest -q`
- `uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
- repository workflow, suppression, dependency, secret, SBOM, artifact, and
  protected-path gates
- exact-SHA GitHub Actions readback for implementation and closure commits

## Git Plan

- Implementation commit: `fix: preserve Shell route focus continuity`
- Push: non-force `main` push after local gates pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-030 Shell focus continuity`
- Push: non-force `main` push after implementation CI evidence is recorded
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Local Evidence

- focused Frontend: 112/112 passed
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 runs, 177 checks each, restart persistence PASS
- external requests, unexpected console errors, and page errors: 0
- continuous modal focus traces, delayed route commit, overlap cancellation,
  Reader/Graph destination ownership, and SVG opener restoration: PASS
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- workflow, suppression, secret, temporary SBOM, artifact, and protected-path
  gates: PASS
- exact-SHA implementation main CI: pending

## Stop Conditions

Stop rather than widen scope if an unknown worktree change appears or correct
behavior needs any prohibited Backend, route-view, API, persistence, dependency,
workflow, external/private, Provider, or release change.
