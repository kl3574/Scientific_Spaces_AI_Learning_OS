# P3-033 Structured Reference Review Round Trip and Context Ownership Alignment

Canonical task:
`docs/tasks/P3-033_STRUCTURED_REFERENCE_REVIEW_ROUND_TRIP.md`

Status: **LOCAL IMPLEMENTATION PASS / IMPLEMENTATION CI PENDING**

BOUNDED REFERENCE/READER FRONTEND, PURE TESTS, PRODUCT E2E, GOVERNANCE
DOCUMENTATION, ISOLATED LOCAL FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE
PUSH TO `main`, AND EXACT-SHA CI READBACK: **GRANTED / ACTIVE**

BACKEND, API, PROVIDER, PERSISTENCE, STORAGE SCHEMA, FROZEN M1, SOURCE OR ARTICLE
RECORDS, CORPUS, GRAPH OR REFERENCE DATA, MATCHING, DERIVED ASSETS, DEPENDENCIES,
LOCKFILES, WORKFLOWS, CANDIDATE, TAG, RELEASE, AND ATTESTATION CHANGES:
**NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Connect each Article structured reference to its exact standalone review,
preserve canonical URL/history and a safe Article return, bind list/detail/
candidate reads to the selected record, and make evidence review accessible
and responsive.

## Binding Contract

- Query, type, classification, page, selected reference, candidate filter, and
  sanitized Article return are canonical URL state.
- Only the owned local source Article can be a rendered return target.
- List, detail, and candidate reads have independent generation/request owners.
- Selection immediately hides prior detail and candidates; response identity
  must equal the current selected reference before rendering.
- Deep-linked records remain reviewable outside the visible result page.
- Article return restores the reference page and exact asynchronous row focus.
- Loading, empty, failed, retry, selected, and filtered-empty states are
  distinct and truthful.
- Standalone evidence is concise while every occurrence exposed by the frozen
  20-row v1.2 detail bound, complete occurrence count, truthful truncation, and
  existing Reader evidence remain available. Unbounded provenance pagination
  is a separate API-revision candidate.

## Allowed Changes

- `frontend/src/app/zotero/page.tsx`
- `frontend/src/components/ZoteroLibraryView.tsx`
- `frontend/src/components/ZoteroReferenceReview.tsx`
- `frontend/src/components/StructuredReferencesPanel.tsx`
- `frontend/src/lib/references.ts`
- `frontend/src/lib/referenceReview.ts`
- `frontend/tests/references.test.ts`
- `frontend/tests/referenceReview.test.ts`
- `frontend/scripts/test-references.sh`
- `scripts/e2e/run_product_e2e.py`
- the exact P3-033 canonical, alignment, current-state, roadmap, README, and
  report files enumerated by the canonical task

## Acceptance

- Article reference actions deep-link to the exact selected record and can
  return to the owned Article row with visible focus.
- Search, filters, pagination, selection, and candidate filter survive reload
  and Back/Forward through bounded canonical URL state.
- Delayed or stale list/detail/candidate results never render under newer state.
- Evidence, provenance, candidate identity, and loading/empty/error/retry state
  remain truthful and accessible.
- Desktop integration covers the complete deep-link, filter, failure/retry,
  race, history, and return semantics. Four required viewports cover
  representative selected-detail and candidate-filter focus plus long-content
  master-detail layout without horizontal overflow.
- Focused/full tests, build, three Product E2E runs, safety gates, and two final
  reviews pass with zero unexpected external/console/page activity.
- Implementation and docs-only closure commits each pass exact-SHA main CI.

## Authorization Basis

The product owner explicitly directed the agent to stop recurring plan
confirmations and automatically execute bounded platform and GUI improvements
after sub-agent review. Two independent reviewers completed the GUI audit. The
product-flow Important finding is incorporated here; the separate application-
wide ordinary-route focus finding remains deferred. This standing direction
authorizes only the exact scope above.

## Stop Conditions

Stop rather than widen scope if correct behavior requires Backend, API,
provider, persistence, dependency, workflow, external/private, or release
changes, or if an unknown worktree change, forbidden artifact, unrepairable
gate, or exact-SHA CI failure appears.

No v1.2 candidate is assigned.

## Local Gate Result

The final worktree passes 131 focused Frontend tests, the 11-route production
build, 600 Backend tests with 4 skipped, three complete Product E2E runs,
restart persistence, two independent final reviews, and all local non-network
safety gates. External requests and unexpected console/page errors are zero.
The granted implementation push and exact-SHA CI gate remain pending.
