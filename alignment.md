# P3-036 Workspace Mutation Focus Continuity Alignment

Canonical task:
`docs/tasks/P3-036_WORKSPACE_MUTATION_FOCUS_CONTINUITY.md`

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

BOUNDED FRONTEND FOCUS OWNERSHIP, PRODUCT E2E, GOVERNANCE DOCUMENTATION,
ISOLATED LOCAL FAKE-RUNTIME VALIDATION, TWO INDEPENDENT SUB-AGENT REVIEWS, LOCAL
COMMITS, NON-FORCE PUSH TO `main`, AND EXACT-SHA CI READBACK: **GRANTED / ACTIVE**

BACKEND, API, PROVIDER, PERSISTENCE, STORAGE SCHEMA, FROZEN M1, SOURCE OR ARTICLE
RECORDS, CORPUS, GRAPH OR REFERENCE DATA, MATCHING, DERIVED ASSETS, DEPENDENCIES,
LOCKFILES, WORKFLOWS, VERSION/CANDIDATE, TAG, RELEASE, ATTESTATION, SOURCE NETWORK,
EXTERNAL SEARCH, PRIVATE ZOTERO, REAL/PAID PROVIDERS, DESTRUCTIVE GIT ACTIONS, AND
HISTORY REWRITING: **NOT GRANTED**

## Objective

Make every reproduced in-page learning mutation retain an explicit, visible,
semantically related focus owner when its initiating control disables,
unmounts, or switches rendering mode, without changing data or route behavior.

## Binding Contract

- No required operation settles on `BODY`, a disconnected element, or an
  unrelated Shell fallback.
- Stable targets are local to the operation: capture/status regions, matching
  note editors/actions, search inputs, result headings, changed/surviving queue
  items, or empty-state recovery actions.
- Async results may not steal focus after a newer user interaction, route,
  modal, or request supersedes the initiating operation.
- Existing request counts, storage writes, URLs, history, feedback, and
  business outcomes remain unchanged.
- Existing correct focus contracts remain correct.

## Allowed Changes

- the nine bounded Frontend components named by the canonical task
- focused pure Frontend tests only if a reusable state helper is necessary
- `scripts/e2e/run_product_e2e.py`
- the canonical task, evidence report, `alignment.md`,
  `docs/tasks/CURRENT_TASK.md`, `docs/00_PROJECT_STATE.md`, `roadmap.md`,
  `docs/V1_2_ROADMAP.md`, and `README.md`

## Acceptance

- Every exact focus target in the canonical task is verified through public
  rendered interactions and visible focus.
- Async ownership and all current success/error/storage/race outcomes remain
  correct.
- Required desktop and mobile viewports have no page-level overflow or clipped
  focused targets.
- Focused Frontend suites, production build, full Backend regression, three
  Product E2E runs, repository safety gates, and two independent final reviews
  pass.
- Implementation and docs-only closure commits each pass exact-SHA main CI and
  final `main` is clean and synchronized.

## Authorization Basis

The product owner explicitly directed continued platform and GUI improvement,
independent sub-agent review, and automatic execution without recurring plan
confirmation. Two independent reviews and controlled Chromium produced current,
reproducible Important evidence at the rendered GUI seam. This standing
direction authorizes only the exact bounded scope above.

## Stop Conditions

Stop rather than widen scope if correct behavior requires Backend, API, data,
provider, persistence, dependency, workflow, external/private, or release
changes, or if an unknown worktree change, forbidden artifact, unrepairable
gate, or exact-SHA CI failure appears.

No v1.2 candidate is assigned.

## Git Plan

- Implementation commit: `fix: preserve workspace mutation focus`
- Non-force push to `main`, followed by exact-SHA implementation CI readback
- Docs-only closure commit: `docs: close P3-036 mutation focus continuity`
- Non-force push to `main`, followed by exact-SHA closure CI readback
- Tag and Release operations are not authorized

## Current Gate

All local behavior, regression, build, Backend, three-run Product E2E, review,
and offline repository-safety gates pass. Create the authorized implementation
commit, push it without force, and require exact-SHA main CI before closure.
