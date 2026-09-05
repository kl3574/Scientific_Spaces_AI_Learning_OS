# P3-031 Reader Note Deletion Safety Alignment

Canonical task:
`docs/tasks/P3-031_READER_NOTE_DELETION_SAFETY.md`

Status: **PASS / CLOSED**

BOUNDED READER FRONTEND, PURE TESTS, PRODUCT E2E, GOVERNANCE DOCUMENTATION,
ISOLATED LOCAL FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE PUSH TO `main`,
AND EXACT-SHA CI READBACK: **CONSUMED / CLOSED**

BACKEND, API, PERSISTENCE, STORAGE SCHEMA, FROZEN M1, SOURCE OR ARTICLE RECORDS,
CORPUS, GRAPH DATA, DERIVED ASSETS, DEPENDENCIES, LOCKFILES, WORKFLOWS,
CANDIDATE, TAG, RELEASE, AND ATTESTATION CHANGES: **NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Require an Article/generation/note-owned confirmation before permanent Reader
note deletion and keep focus, duplicate prevention, and uncertain-result
feedback coherent through every terminal and stale path.

## Binding Contract

- First Delete activation creates intent and sends zero DELETE requests.
- Inline confirmation explains that deletion is permanent and cannot be undone.
- Opening focuses Cancel; deterministic keyboard order reaches Delete permanently.
- All competing Notes mutation launchers remain locked while confirmation is
  awaiting a decision or the DELETE is in flight.
- Cancel and Escape send zero DELETE and restore the exact initiating control.
- Confirm sends exactly one DELETE through existing P3-029 ownership guards.
- Pending keeps confirmation mounted; success focuses visible Notes status.
- Rejection or response loss is unconfirmed, preserves only current rendering,
  never auto-replays, and instructs reload before retry.
- Article/history/reload changes invalidate old intent and focus work without a
  DELETE or cross-Article side effect.

## Allowed Changes

- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/lib/readerLearningMutations.ts`
- `frontend/tests/readerLearningMutations.test.ts`
- `scripts/e2e/run_product_e2e.py`
- the exact P3-031 canonical, alignment, current-state, roadmap, README, and
  report files enumerated by the canonical task

## Acceptance

- Mouse and keyboard open/cancel/confirm paths satisfy exact request counts.
- Pending, success, rejection, and response-loss states preserve P3-029
  identity and uncertainty semantics.
- Focus never falls to `body`, disconnects, or crosses Article generations.
- Article change, Back/Forward, reload, and stale completions are inert.
- Four required viewports have usable controls and no horizontal overflow.
- Focused/full tests, build, three Product E2E runs, safety gates, and two final
  reviews pass with zero unexpected external/console/page activity.
- Implementation and docs-only closure commits each pass exact-SHA main CI.

## Authorization Basis

The product owner explicitly directed the agent to stop recurring plan
confirmations and automatically execute bounded platform and GUI improvements
after independent sub-agent review. Two independent reviewers approved this
revised contract with no remaining Critical or Important gaps. This standing
direction authorizes only the exact scope above.

## Stop Conditions

Stop rather than widen scope if correct behavior requires Backend, API,
persistence, dependency, workflow, external/private, Provider, or release
changes, or if an unknown worktree change, forbidden artifact, unrepairable
gate, or exact-SHA CI failure appears.

No v1.2 candidate is assigned.

## Local Gate Result

All local acceptance gates pass: 113 focused Frontend tests, the 11-route
production build, 600 Backend tests with 4 skipped, three Product E2E runs with
177 checks each, two final independent reviews, and all local safety gates.
External requests and unexpected console/page errors are zero.

## Closure Evidence

- implementation commit:
  `f944d2df79505bcca0f22276b1138d84fe1f161b`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33956965124`
- unchanged-SHA attempt 2 passed Frontend, Backend, three-run Product E2E,
  dependency, workflow/suppression, secret, and SBOM gates
- normal-main Docker and release evidence jobs skipped as designed
- uploaded artifacts: 0
- attempt 1 failed only at a pre-existing P3-028 Graph-origin Reader progress
  assertion; no P3-031 deletion-safety assertion failed
- docs-only closure commit: this commit; exact-SHA main CI is required before
  final reporting
- next bounded candidate: none staged
