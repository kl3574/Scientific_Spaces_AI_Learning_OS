# P3-027 Tutor Request Ownership and Accessible Feedback Alignment

Canonical task:
`docs/tasks/P3-027_TUTOR_REQUEST_OWNERSHIP_AND_ACCESSIBLE_FEEDBACK.md`

Status: **LOCAL ACCEPTANCE PASS / IMPLEMENTATION EXACT-SHA CI PENDING**

BOUNDED TUTOR FRONTEND, FOCUSED TESTS, PRODUCT E2E, GOVERNANCE DOCUMENTATION,
ISOLATED LOCAL FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE PUSH TO `main`,
AND EXACT-SHA CI READBACK: **GRANTED / ACTIVE**

BACKEND, FROZEN M1, SOURCE OR ARTICLE RECORDS, DERIVED ASSETS, GRAPH DATA,
TUTOR PERSISTENCE OR PROVIDER CONTRACTS, DEPENDENCIES, LOCKFILES, WORKFLOWS,
PUBLISHED API CONTRACTS, CANDIDATE, TAG, RELEASE, AND ATTESTATION CHANGES:
**NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Bind every Tutor outcome to the exact submitted mode, prompt, Article, and
Graph context, then make loading, Answer, Quiz, score, reset, empty, and error
transitions perceivable and keyboard reachable.

## Binding Scope

- Only the latest immutable request context may publish output or activity.
- Visible context changes invalidate pending and completed output that no
  longer belongs to those controls.
- Study modes use coherent pressed-button semantics.
- Loading and completion are announced; result, error, Quiz, score, and reset
  transitions have deterministic focus.
- Existing grounded answers, sources, Quiz answer disclosure, recent activity,
  APIs, records, and Providers remain unchanged.
- The non-reproducing Graph-to-Reader timeout remains a separate bounded
  stress-diagnostic debt.

## Allowed Changes

- `frontend/src/components/TutorView.tsx`
- `frontend/src/components/TutorQuizWorkspace.tsx`
- bounded responsive containment in `TutorSourceList.tsx`
- bounded request/status changes in `TutorArticlePicker.tsx`
- `frontend/src/lib/tutorWorkspace.ts`
- `frontend/tests/tutor.test.ts`
- `scripts/e2e/run_product_e2e.py`
- P3-027 task/status/roadmap/README/alignment/report documentation

## Acceptance

- Prompt, Article, Graph, mode, and route changes cannot publish stale output,
  error, Quiz, or activity.
- Loading uses truthful busy/live semantics.
- Answer, empty, error, Quiz, score, and reset focus paths are deterministic.
- Quiz answers remain hidden before submission and keyboard-only completion
  works.
- Dynamic Tutor states fit all required desktop/mobile/zoom-equivalent
  viewports without document overflow.
- Full Frontend/Backend/build/three-run E2E/security/artifact/protected-path
  gates and two independent final reviews pass.
- Implementation and docs-only closure commits each pass exact-SHA main CI.

## Local Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 121 passed, including 22 Tutor tests
- production build: PASS, 11 routes
- Product E2E: 3/3 runs, 140 checks each, restart persistence PASS,
  0 external requests, unexpected console errors, or page errors
- request and activity ownership, deterministic result/Quiz focus, coherent
  mode semantics, and all four required viewports: PASS
- independent final reviews: 2 PASS
- local workflow, suppression, secret, SBOM, artifact, and protected-path
  checks: PASS
- implementation commit and exact-SHA main CI: pending

## Stop Conditions

Stop rather than widen scope if any requirement needs Backend, API, data,
dependency, workflow, external/private, Provider, or release changes, or if an
unknown worktree change, forbidden artifact, unrepairable gate, or CI failure
appears.

No v1.2 candidate is assigned.
