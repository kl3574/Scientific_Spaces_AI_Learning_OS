# P3-024 Graph Master-Detail Navigation and Focus Continuity

## Status

LOCAL VALIDATION PASS / IMPLEMENTATION CI PENDING

## Objective

Make Graph result selection, detail inspection, Knowledge Context, browser
history, focus, and responsive navigation operate as one coherent workspace
without changing Backend or Graph contracts.

## Authoritative Alignment

`alignment.md`

## Entry State

- branch: `main`
- entry commit: `5448ca90ce8557e99d15d5ff4b3768910a3a5cc6`
- cached `origin/main`: exact match
- ahead / behind: `0 / 0`
- worktree, index, and untracked set: clean
- P3-023: PASS / CLOSED
- REWORK / `.audit`: absent
- independent revised-scope reviews: 2 PASS
- candidate version: not assigned

## In Scope

- Explore / Knowledge Context workspace mode
- responsive Results / Selected navigation below desktop width
- bounded scrollable desktop detail inspector
- stable detail focus target and deterministic result-focus restoration
- canonical node-selection URL and push/replace history behavior
- reload and Back/Forward selection restoration
- safe bounded live announcements
- existing Concept context-action integration
- focused Frontend, Product E2E, read-only real-data, and governance evidence
- ordinary commits, non-force push, and exact-SHA CI closure

## Protected Boundaries

- no Backend, schema, API, Graph builder, Graph asset, or persistence changes
- no source, Article, frozen M1, Tutor, Reader, Session, or learning contract
  changes
- no ranking, traversal-bound, node-page-size, or Graph-semantic changes
- no dependency, lockfile, or workflow changes
- no source network, external search, private Zotero, or real/paid Provider
- no candidate, tag, Release, attestation, force push, or history rewrite
- no committed runtime/private artifact, PDF, HTML, image, trace, profile,
  cache, database, corpus, credential, or secret

## Product Contract

- Deep-linked selection is directly reachable on narrow and zoomed layouts.
- Desktop retains simultaneous results and detail inspection.
- Workspace mode is local UI state and never creates browser history.
- Different-node selections push one canonical entry; same-node selection is a
  no-op; canonicalization and restoration never push.
- Canonical URLs contain only validated node, applied query, and typed Article
  workflow parameters.
- Node-only navigation preserves current in-memory filters and page.
- Detail focus persists through asynchronous state replacement.
- Context selection remains in Context and retains map recentering.
- No live or visible message exposes raw node IDs.

## Deliverables

- Graph workspace and canonical navigation implementation under `frontend/src/`
- focused tests and expanded Product E2E
- `docs/P3_024_GRAPH_MASTER_DETAIL_NAVIGATION_REPORT.md`
- synchronized task, state, roadmap, README, and alignment documents
- implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance

- viewport-intersection, focus, URL, reload, Back/Forward, and error tests pass
  at desktop, 390 x 844, 320 CSS px, and 720 x 450 zoom-equivalent
- Back to results restores the origin or Results fallback without URL mutation
- Context is one action away and Map/List/Inspect selected remain coherent
- sticky long details expose first and last controls to keyboard navigation
- semantic button groups, labelled regions, visible focus, and safe live status
  pass without horizontal overflow
- existing Graph, Article-origin, Concept Study Set, Tutor, Reader, and Session
  behavior does not regress
- three isolated Product E2E runs and all repository gates pass
- protected implementation/data boundaries remain unchanged
- implementation and closure exact-SHA CI pass; final branch is synchronized

## Confirmed Test Seams

1. Pure Graph URL ownership and workspace navigation model.
2. Browser Graph result/detail/context, focus, and history behavior.

## Local Validation Evidence

- Backend: 600 passed, 4 skipped
- focused Frontend: 97 passed
- Next.js production build: PASS, 11 routes
- production Product E2E: 3/3 complete runs, 73 checks per run
- Product E2E external requests / console errors / page errors: 0 / 0 / 0
- read-only local data: 1,314 Articles, 53,046 Graph nodes, 82,584 edges
- workflow, suppression, dependency, secret, and temporary SBOM gates: PASS
- independent final implementation reviews: 2 PASS
- protected-path and tracked-artifact gates: PASS
- remaining closure gate: implementation and docs-only exact-SHA main CI

## Stop Rule

Stop without widening scope when completion requires a protected contract,
external/private side effect, new dependency, release action, or unresolved
critical regression.
