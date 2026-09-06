# P3-035 Mobile Article Discovery Result Visibility Alignment

Canonical task:
`docs/tasks/P3-035_MOBILE_ARTICLE_DISCOVERY_RESULT_VISIBILITY.md`

Status: **PASS / CLOSED**

BOUNDED ARTICLE LIST FRONTEND, PRODUCT E2E, GOVERNANCE DOCUMENTATION, ISOLATED
LOCAL FAKE-RUNTIME VALIDATION, TWO INDEPENDENT SUB-AGENT REVIEWS, LOCAL COMMITS,
NON-FORCE PUSH TO `main`, AND EXACT-SHA CI READBACK: **CONSUMED / CLOSED AFTER
THIS DOCS-ONLY CLOSURE COMMIT**

BACKEND, API, PROVIDER, PERSISTENCE, STORAGE SCHEMA, FROZEN M1, SOURCE OR ARTICLE
RECORDS, CORPUS, GRAPH OR REFERENCE DATA, MATCHING, DERIVED ASSETS, DEPENDENCIES,
LOCKFILES, WORKFLOWS, CANDIDATE, VERSION, TAG, RELEASE, AND ATTESTATION CHANGES:
**NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Make the first useful Article result visible in constrained initial viewports
while preserving every existing search, sort, pagination, Focused Session,
feedback, keyboard, route, and data contract.

## Binding Contract

- The first Article title and preview intersect the initial `390x844` and
  `320x844` viewports at `scrollY === 0`.
- The first Article title intersects the initial `720x450` viewport.
- Search and sort remain complete at every required viewport.
- Multi-page navigation follows current results and remains functional; no
  pagination is shown for a single-page result set.
- Select page and Open Focused Session remain available before selection.
- Clear and Add mutations appear when at least one current-page Article is
  selected and preserve all existing feedback/failure behavior.
- No horizontal overflow, focus loss, route change, or data mutation is added.

## Allowed Changes

- `frontend/src/components/ArticleListView.tsx`
- `scripts/e2e/run_product_e2e.py`
- `docs/tasks/P3-035_MOBILE_ARTICLE_DISCOVERY_RESULT_VISIBILITY.md`
- `docs/P3_035_MOBILE_ARTICLE_DISCOVERY_RESULT_VISIBILITY_REPORT.md`
- `alignment.md`
- `docs/tasks/CURRENT_TASK.md`
- `docs/00_PROJECT_STATE.md`
- `roadmap.md`
- `docs/V1_2_ROADMAP.md`
- `README.md`

## Acceptance

- Initial viewport result visibility satisfies the exact portrait and
  short-landscape contract above.
- Search, sort, paging, page selection, individual selection, add, clear, open,
  duplicate, capacity, failure, retry, live feedback, and keyboard behavior
  remains complete.
- Existing URL/query/history contracts remain unchanged.
- Required desktop and mobile viewports have no page-level overflow or clipped
  controls.
- Focused Frontend suites, production build, full Backend regression, three
  Product E2E runs, repository safety gates, and two independent final reviews
  pass.
- Implementation and docs-only closure commits each pass exact-SHA main CI;
  final `main` is clean and synchronized.

## Authorization Basis

The product owner explicitly directed continued platform and GUI improvement,
independent sub-agent review, and automatic execution without recurring plan
confirmation. Controlled Chromium measured the first result at `y=712`,
`y=780`, and `y=491` in the three constrained viewports. An independent
responsive reviewer reproduced the same Important information-priority defect;
the other reviewer did not complete equivalent bounding-box measurements and
therefore neither confirmed nor contradicted it. This standing direction
authorizes only the exact bounded scope above.

## Deferred Review Findings

The reviewers separately reported Reader mutation focus loss, stale Article
IDs, Reader duplicate H1 semantics, and extraction-noise presentation. These
cross different ownership boundaries and are not silently included in P3-035;
they remain evidence for later bounded tasks.

## Stop Conditions

Stop rather than widen scope if correct behavior requires Backend, API, data,
provider, persistence, dependency, workflow, external/private, or release
changes, or if an unknown worktree change, forbidden artifact, unrepairable
gate, or exact-SHA CI failure appears.

No v1.2 candidate is assigned.

## Git Plan

- Implementation commit: `fix: prioritize mobile article results`
- Non-force push to `main`, followed by exact-SHA implementation CI readback
- Docs-only closure commit: `docs: close P3-035 mobile article discovery`
- Non-force push to `main`, followed by exact-SHA closure CI readback
- Tag and Release operations are not authorized

## Current Gate

All required local implementation, focused Frontend, production build, full
Backend, three-run Product E2E, two-reviewer, security, SBOM, artifact, and
protected-path gates pass. Implementation commit
`6f5844c80b092a1919f20e5e93f75a9b6ae1e38a` passed exact-SHA main CI run
[`34010502972`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34010502972)
with every required job passing and zero uploaded artifacts. This docs-only
closure commit consumes the remaining P3-035 authorization; no later task is
staged or authorized.
