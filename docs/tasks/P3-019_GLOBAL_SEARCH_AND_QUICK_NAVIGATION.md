# P3-019 Global Search and Quick Navigation

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

## Objective

Add a responsive, accessible global search and quick-navigation interaction to
the existing Application Shell using only current Frontend clients, published
local APIs, route contracts, and dependencies.

## Entry Evidence

- branch: `main`
- entry commit: `01b572ed2af8e32efa4e9bdb77a4f66628574054`
- cached `origin/main`: `01b572ed2af8e32efa4e9bdb77a4f66628574054`
- ahead / behind: `0 / 0`
- worktree and index: clean
- REWORK / `.audit`: absent
- predecessor: P3-018 PASS / CLOSED

## In Scope

- global Shell search triggers on desktop and mobile
- stable-workspace quick navigation
- bounded Article, structured Reference, and Graph-node search
- readable grouped results and safe internal destinations
- Article relevance-return context and Graph node deep links
- stale-query protection and partial-source failure handling
- keyboard, focus, screen-reader, reduced-motion, and responsive behavior
- focused Frontend tests, isolated Product E2E, and real local-data probes
- governance, implementation evidence, commits, push, and exact-SHA CI closure

## Out of Scope

- Backend or published API changes
- frozen M1/source pipeline changes
- source, Article, or derived-data mutations or rebuilds
- dependency, lockfile, or workflow changes
- private Zotero access or mutation
- source-site access
- real or paid Provider calls
- external/web search
- candidate, tag, Release, or attestation actions
- authentication, multi-user state, or hosted deployment

## Planned Changes

- search model and components under `frontend/src/`
- existing Shell and Graph presentation only where required for integration
- focused tests under `frontend/tests/`
- search regression coverage in `scripts/e2e/run_product_e2e.py`
- `alignment.md`, task/status/report/roadmap/README documentation

## Acceptance

1. One global search entry is available from desktop, mobile, and keyboard.
2. Empty-query quick navigation covers every stable workspace.
3. Article, structured Reference, and Graph search use existing local APIs and
   readable bounded groups.
4. Result links are accurate, preserve valid context, and do not show raw IDs.
5. Stale responses are ignored and partial source failures retain healthy
   results with an explicit bounded notice.
6. Arrow keys, Enter, Escape, focus trap, autofocus, and focus restoration
   behave predictably.
7. Desktop and 390 px mobile are complete and overflow-free.
8. Real local-data search and three repeated isolated Product E2E runs pass
   with fake providers, isolated mutable state, zero external requests, and no
   unexpected console/page errors.
9. Full local quality, security, artifact, and protected-path gates pass
   without Backend, dependency, lockfile, workflow, data, or API changes.
10. Implementation and docs-only closure commits each pass exact-SHA main CI;
    final `main` is clean and synchronized.

## Authorization

- local Article/Reference/Graph data reads, local application runtime, and
  isolated browser validation: GRANTED FOR P3-019
- Frontend/tests/docs edits, local commits, push, and CI inspection: GRANTED
  FOR P3-019
- Backend/frozen M1/source records/Article records/derived assets: NOT GRANTED
- dependency/lockfile/workflow/published API changes: NOT GRANTED
- source network/private Zotero/real Provider/external search: NOT GRANTED
- candidate/tag/Release/attestation: NOT GRANTED

## Stop Conditions

Stop if an unknown worktree change appears, an in-scope gate cannot be fixed
without widening scope, a protected path or artifact changes, external/private
access becomes necessary, or any release action becomes necessary.

## Local Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 64 passed
- production build: PASS, 9 routes
- Product E2E: 3/3 runs, 37 checks each
- real local search: 1,314 Articles; five desktop/mobile queries; all Article,
  Reference, and Graph sources exercised
- visual geometry: 1,440/390 px documents without overflow
- external requests, unexpected console errors, and page errors: 0
- workflow, suppression, dependency, secret, security utility, and temporary
  SBOM gates: PASS
- protected implementation/data/dependency/workflow paths: unchanged
- implementation exact-SHA main CI: pending
