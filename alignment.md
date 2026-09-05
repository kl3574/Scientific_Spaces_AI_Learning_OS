# P3-032 Related-Paper Context Ownership and Accessible Feedback Alignment

Canonical task:
`docs/tasks/P3-032_RELATED_PAPER_CONTEXT_OWNERSHIP_AND_ACCESSIBLE_FEEDBACK.md`

Status: **PASS / CLOSED**

BOUNDED RELATED-PAPERS FRONTEND, PURE TESTS, PRODUCT E2E, GOVERNANCE
DOCUMENTATION, ISOLATED LOCAL FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE
PUSH TO `main`, AND EXACT-SHA CI READBACK: **CONSUMED / CLOSED**

BACKEND, API, PROVIDER, PERSISTENCE, STORAGE SCHEMA, FROZEN M1, SOURCE OR ARTICLE
RECORDS, CORPUS, GRAPH OR REFERENCE DATA, DERIVED ASSETS, DEPENDENCIES, LOCKFILES,
WORKFLOWS, CANDIDATE, TAG, RELEASE, AND ATTESTATION CHANGES: **NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Make Related Papers reads, searches, mutations, and exports Article-owned;
require safe unlink confirmation and truthful reconciliation; and provide
accessible, responsive loading, feedback, and BibTeX states.

## Binding Contract

- Every operation is owned by Article, generation, operation, and relevant
  query/item/link fingerprint.
- Loading, empty, unavailable, error, pending, success, and uncertain states are
  distinct and truthful.
- Search supersession is latest-owned; duplicate submission is inert.
- One panel-wide mutation lane prevents duplicate or competing POST/DELETE.
- Unlink is two-phase; cancel, Escape, and navigation send zero DELETEs;
  confirmation sends exactly one.
- Mutation failure performs one read-only reconciliation, never replay, and
  blocks further mutation only when persistence remains unconfirmed.
- Provider availability does not hide locally stored project links.
- BibTeX is a current-link-set-owned accessible disclosure.
- Stale completion and deferred focus work cannot cross Article generations.

## Allowed Changes

- `frontend/src/components/ZoteroLinksPanel.tsx`
- `frontend/src/components/ArticleDetailView.tsx` only for an Article key, the
  Reading tools grid item's min-width constraint, and a synchronous ordinary
  Article-to-Article main / destination-heading focus handoff
- `frontend/src/lib/zotero.ts`
- `frontend/src/lib/zoteroLinkOperations.ts`
- `frontend/tests/zoteroLinkOperations.test.ts`
- `frontend/scripts/test-references.sh`
- `scripts/e2e/run_product_e2e.py`
- the exact P3-032 canonical, alignment, current-state, roadmap, README, and
  report files enumerated by the canonical task

## Acceptance

- Delayed or stale reads cannot mutate another Article or target it with an old
  item key.
- Search, Link, Unlink, reconciliation, and export satisfy exact request counts.
- Unlink confirmation, provider availability, loading/empty/error truth, live
  feedback, target names, and continuous panel/route focus behavior are
  accessible.
- Four required viewports support populated, pending, failure, confirmation,
  and long BibTeX states without horizontal overflow.
- Focused/full tests, build, three Product E2E runs, safety gates, and two final
  reviews pass with zero unexpected external/console/page activity.
- Implementation and docs-only closure commits each pass exact-SHA main CI.

## Authorization Basis

The product owner explicitly directed the agent to stop recurring plan
confirmations and automatically execute bounded platform and GUI improvements
after sub-agent review. Two independent reviewers converged on this contract;
their Critical and Important findings are incorporated above. This standing
direction authorizes only the exact scope above.

## Stop Conditions

Stop rather than widen scope if correct behavior requires Backend, API,
provider, persistence, dependency, workflow, external/private, or release
changes, or if an unknown worktree change, forbidden artifact, unrepairable
gate, or exact-SHA CI failure appears.

No v1.2 candidate is assigned.

## Local Gate Result

The final worktree passes 120 focused Frontend tests, the 11-route production
build, 600 Backend tests with 4 skipped, three complete Product E2E runs,
restart persistence, two independent final reviews, and all local non-network
safety gates. External requests and unexpected console/page errors are zero.
Exact-SHA implementation main CI passed; this docs-only closure commit still
requires its own exact-SHA main CI before final reporting.

## Closure Evidence

- implementation commit:
  `e7b317042df728e568bb5f4d328c678ac3102f0a`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33965187190`
- Frontend, Backend, three-run Product E2E, dependency,
  workflow/suppression, secret, and SBOM jobs: PASS
- normal-main Docker and release-evidence jobs: skipped as designed
- uploaded workflow artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI is required before
  final reporting
- next bounded task or candidate: none staged
