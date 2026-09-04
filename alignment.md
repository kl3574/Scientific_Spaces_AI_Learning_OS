# P3-026 Trustworthy Article Discovery and Focused Session Capture Alignment

Canonical task:
`docs/tasks/P3-026_ARTICLE_DISCOVERY_TO_FOCUSED_SESSION.md`

Status: **PASS / CLOSED**

FRONTEND, FOCUSED TESTS, PRODUCT E2E, GOVERNANCE DOCUMENTATION, ISOLATED LOCAL
FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE PUSH TO `main`, AND EXACT-SHA
CI READBACK: **CONSUMED / CLOSED**

BACKEND, FROZEN M1, SOURCE OR ARTICLE RECORDS, DERIVED ASSETS, QUEUE SCHEMA OR
SEMANTICS, DEPENDENCIES, LOCKFILES, WORKFLOWS, PUBLISHED API CONTRACTS,
CANDIDATE, TAG, RELEASE, AND ATTESTATION CHANGES: **NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Make `/articles` a truthful, generation-safe discovery and explicit Focused
Session capture workflow using only existing Frontend clients and browser-local
queue contracts.

## Binding Scope

- Only the latest Article request generation can publish rows, pagination,
  error, loading, focus, or selection state.
- Learning State and Bookmark reads remain independent; failed state loading is
  `Status unavailable`, while omission after a successful read is `unread`.
- Selection is explicit, page-scoped, and cleared whenever query, sort, page,
  or retry starts a new result generation.
- Capture reloads the queue immediately before one bulk append and one save,
  preserving existing order and active identity.
- Outcomes for added, duplicate, invalid, capacity, unavailable storage, and
  failed save are truthful. Failure preserves selection for retry.
- Capture performs no server mutations, URL change, recommendation, or
  automatic navigation; `/session` remains an explicit handoff.

## Allowed Changes

- `frontend/src/components/ArticleListView.tsx`
- new pure `frontend/src/lib/articleSessionPlanning.ts`
- focused Article/Session tests and runners
- `scripts/e2e/run_product_e2e.py`
- P3-026 task/status/roadmap/README/alignment/report documentation

`frontend/src/lib/studySession.ts` is reused unchanged.

## Acceptance

- A-B-A result races and stale failures are generation-safe.
- Pending/failed searches expose no actionable stale rows.
- Badge partial failures remain independent and truthful.
- Latest-page selection and queue append order are deterministic.
- Queue reload, duplicate, capacity, invalid, and save-failure behavior pass.
- Same-tab/cross-tab refresh, keyboard operation, focus/live status, and four
  required viewport cases pass without overflow.
- Full Frontend/Backend/build/three-run E2E/security/artifact/protected-path
  gates and two independent final reviews pass.
- Implementation and docs-only closure commits each pass exact-SHA main CI.

## Stop Conditions

Stop rather than widen scope if any requirement needs Backend, API, queue,
data, dependency, workflow, external/private, Provider, or release changes, or
if an unknown worktree change, forbidden artifact, unrepairable gate, or CI
failure appears.

No v1.2 candidate is assigned.

## Local Evidence

- focused Frontend tests: 119 passed
- Backend regression: 600 passed / 4 skipped
- Next.js production build: PASS, 11 routes
- Product E2E: 3/3 formal PASS plus 10/10 single-core stress PASS,
  113 checks per run, restart persistence PASS
- Chromium: 149.0.7827.55
- non-loopback requests and unexpected console/page errors: 0
- workflow, suppression, dependency, secret, temporary SBOM, artifact, and
  protected-path gates: PASS
- independent final reviews: 2 PASS after all findings were repaired
- implementation commit:
  `57333916e668516ff8e04b3062ffbc3365b72236`
- exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33902645777`
- CI attempt 1 exposed one transient pre-existing Graph-to-Reader loading
  timeout; the same SHA passed all required jobs on attempt 2 after the 10-run
  single-core local stress remained clean
- docs-only closure commit: this commit; its exact-SHA CI is required before
  final reporting
