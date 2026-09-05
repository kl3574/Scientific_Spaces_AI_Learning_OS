# P3-030 Shell Modal-Origin Route Focus Continuity Alignment

Canonical task:
`docs/tasks/P3-030_SHELL_MODAL_ORIGIN_ROUTE_FOCUS_CONTINUITY.md`

Status: **PASS / CLOSED**

BOUNDED SHELL FRONTEND, PURE TESTS, PRODUCT E2E, GOVERNANCE DOCUMENTATION,
ISOLATED LOCAL FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE PUSH TO `main`,
AND EXACT-SHA CI READBACK: **CONSUMED / CLOSED**

BACKEND, FROZEN M1, SOURCE OR ARTICLE RECORDS, DERIVED ASSETS, GRAPH/READER/TUTOR
ROUTE IMPLEMENTATION, PERSISTENCE OR PUBLISHED API CONTRACTS, DEPENDENCIES,
LOCKFILES, WORKFLOWS, CANDIDATE, TAG, RELEASE, AND ATTESTATION CHANGES:
**NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Keep keyboard focus coherent when Global Search or the mobile navigation drawer
originates a local route transition, while preserving focus deliberately owned
by destination workspaces.

## Binding Scope

- Distinguish modal dismissal from accepted same-tab local navigation.
- Observe committed pathname and query changes and close stale Shell modals.
- Move focus to persistent `main#main-content` only when the destination has not
  already claimed focus.
- Cancel stale deferred focus work across overlapping modal and route actions.
- Preserve Graph, Reader, and other route-local focus ownership.
- Preserve modified-click and new-tab behavior.

## Allowed Changes

- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/GlobalSearchDialog.tsx`
- `frontend/src/components/PrimaryNav.tsx`
- `frontend/src/lib/navigation.ts`
- `frontend/tests/navigation.test.ts`
- `frontend/scripts/test-articles.sh`
- `scripts/e2e/run_product_e2e.py`
- P3-030 task/status/roadmap/README/alignment/report documentation

## Acceptance

- Search and Drawer cross-route navigation never leaves focus on `body`.
- Same-URL activation closes the modal, adds no history entry, and focuses the
  current main region.
- Pathname/query Back and Forward close stale modals without focusing behind an
  active modal.
- Destination-owned Graph/Reader focus wins over the Shell fallback.
- Escape, close, and backdrop dismissal restore the opener.
- Modified/new-tab navigation does not close the current modal or arm stale
  focus work.
- Focused/full tests, build, three Product E2E runs, safety gates, and two final
  reviews pass.
- Implementation and docs-only closure commits each pass exact-SHA main CI.

## Authorization Basis

The product owner explicitly directed the agent to stop repeated plan
confirmations and automatically execute bounded work after independent
sub-agent review. Two independent reviews approved this frontend-only repair
and identified the same modal-origin focus defect. This standing direction is
authorization for the exact scope above and no broader action.

## Stop Conditions

Stop rather than widen scope if correct behavior requires Backend, API,
persistence, route-view, dependency, workflow, external/private, Provider, or
release changes, or if an unknown worktree change, forbidden artifact,
unrepairable gate, or exact-SHA CI failure appears.

No v1.2 candidate is assigned.

## Local Gate Result

The bounded implementation, 112 focused Frontend tests, 11-route production
build, 600 Backend tests with 4 skipped, three 177-check Product E2E runs,
security/repository gates, and two independent final reviews pass.

## Closure Evidence

- implementation commit:
  `eabccf1d20d62e12dc5bf4d85181a4c66fe68ad3`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33948697098`
- Frontend build, Backend pytest, three-run Product E2E, dependency audit,
  workflow/suppression policy, secret audit, and SBOM validation: PASS
- normal-main Docker compose smoke and release evidence: skipped as designed
- uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI is required before
  final reporting
- next bounded candidate: none staged
