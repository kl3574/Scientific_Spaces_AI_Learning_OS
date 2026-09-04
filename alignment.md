# P3-028 Graph-Reader Round-Trip Reliability Alignment

Canonical task:
`docs/tasks/P3-028_GRAPH_READER_ROUND_TRIP_RELIABILITY.md`

Status: **LOCAL PASS / IMPLEMENTATION READY; EXACT-SHA CI PENDING**

BOUNDED GRAPH/READER FRONTEND, FOCUSED TESTS, PRODUCT E2E, GOVERNANCE DOCUMENTATION,
ISOLATED LOCAL FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE PUSH TO `main`,
AND EXACT-SHA CI READBACK: **GRANTED**

BACKEND, FROZEN M1, SOURCE OR ARTICLE RECORDS, DERIVED ASSETS, GRAPH DATA OR
BUILDERS, PERSISTENCE OR PROVIDER CONTRACTS, DEPENDENCIES, LOCKFILES, WORKFLOWS,
PUBLISHED API CONTRACTS, CANDIDATE, TAG, RELEASE, AND ATTESTATION CHANGES:
**NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Preserve exact safe Graph context through an Article round trip, provide
deterministic keyboard destination focus and bounded Reader loading recovery,
and replace ambiguous browser assertions with URL-first Reader-root evidence.

## Binding Scope

- Preserve only canonical local Graph `node_id` and normalized `q` state.
- Selected-node, provenance, and Concept Study Set Article actions use the
  existing Article detail href contract.
- Reader and Graph destinations provide useful keyboard focus.
- Loading remains truthful, failures are recoverable, and stale generations
  cannot render or persist.
- Existing Graph semantics, Articles, APIs, records, AppShell hydration logic,
  dependencies, and Providers remain unchanged.
- No loading root-cause fix is claimed without a deterministic causal red/green
  reproduction.

## Allowed Changes

- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/components/ConceptStudySetPanel.tsx`
- `frontend/src/components/GraphNodeDetail.tsx`
- `frontend/src/components/GraphView.tsx`
- bounded abort support in `frontend/src/lib/articles.ts`
- `frontend/src/lib/learningWorkflow.ts`
- bounded navigation/focus state in `frontend/src/lib/graphWorkspace.ts`
- `frontend/tests/learningWorkflow.test.ts`
- `frontend/tests/graphWorkspace.test.ts`
- `frontend/tests/articles.test.ts` only for abort-signal contract coverage
- `scripts/e2e/run_product_e2e.py`
- P3-028 task/status/roadmap/README/alignment/report documentation

## Acceptance

- Exact safe Graph node/query state survives Graph to Reader to Graph, including
  Reader hard reload.
- Unsafe, malformed, unknown, recursive, or external state is excluded.
- Keyboard entry and return focus useful destinations without extra history.
- Loading uses truthful busy/live semantics; failure and timeout expose retry;
  stale generations have no render or persistence effect.
- Browser checks prove URL first and scope content to the Reader root.
- Round-trip controls fit all required desktop/mobile/zoom-equivalent viewports.
- Corrected transition stress passes 100/100 without external requests or
  unexpected console/page errors.
- Full Frontend/Backend/build/three-run E2E/security/artifact/protected-path
  gates and two independent final reviews pass.
- Implementation and docs-only closure commits each pass exact-SHA main CI.

## Entry Evidence

- deterministic browser reproduction: Graph origin
  `/graph?node_id=article%3Acrb-formula&q=CRB` becomes Reader
  `/articles/crb-formula` with `Back to articles`
- existing E2E searches for an unscoped title before proving the route changed
- corrected 100-transition local stress: 100/100, all Article responses 200,
  zero external requests, console errors, or page errors
- independent scope audits: 2 PASS
- starting commit and cached `origin/main`:
  `4daac776bd706cc27c646b31f17fee03c8edeb01`
- P3-027 docs-only closure CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33915076653` PASS

## Local Verification

- focused Frontend: 125/125 PASS
- production build: PASS, Next.js 15.5.21, 11 routes
- Backend regression: 600 passed / 4 skipped
- Product E2E: 3/3 PASS, 154 checks per run, restart persistence PASS
- corrected Graph-to-Reader stress: 100/100 PASS under CPU throttle 4 with
  cache disabled; 301/301 Article responses HTTP 200
- non-loopback requests, unexpected console errors, and page errors: 0
- four required viewports, saved-progress preservation, storage denial,
  timeout/retry, stale-generation, and exact focus fallback: PASS
- independent final implementation reviews: 2 PASS, 0 Critical / 0 Important
- exact-SHA implementation and closure CI: pending

## Stop Conditions

Stop rather than widen scope if any requirement needs Backend, API, data,
AppShell hydration, dependency, workflow, external/private, Provider, or
release changes, or if an unknown worktree change, forbidden artifact,
unrepairable gate, or CI failure appears.

No v1.2 candidate is assigned.
