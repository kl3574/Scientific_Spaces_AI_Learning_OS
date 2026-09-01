# P3-020 Saved Learning Library Alignment

Canonical task:
`docs/tasks/P3-020_SAVED_LEARNING_LIBRARY.md`

Status: **PASS / CLOSED**

LOCAL ARTICLE / BOOKMARK / READING HISTORY / LEARNING STATE READ, LOCAL
APPLICATION RUNTIME, AND ISOLATED BROWSER VALIDATION AUTHORIZATION:
**GRANTED FOR P3-020**

FRONTEND / TEST / DOCUMENTATION MODIFICATION, LOCAL COMMIT / PUSH / CI
INSPECTION AUTHORIZATION: **GRANTED FOR P3-020**

BACKEND / FROZEN M1 / SOURCE RECORD / ARTICLE RECORD / DERIVED ASSET / PRIVATE
ZOTERO / REAL PROVIDER AUTHORIZATION: **NOT GRANTED**

DEPENDENCY / LOCKFILE / WORKFLOW / PUBLISHED API CONTRACT MODIFICATION
AUTHORIZATION: **NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-019 Global Search and Quick Navigation is PASS / CLOSED after both its
  implementation and docs-only closure exact-SHA main CI passed.
- Dashboard, Reader, References, Graph, Tutor, and global search are available,
  but saved and resumable learning material is still distributed across
  separate surfaces.
- Existing Bookmark, Reading History, Learning State, and Article contracts
  must be audited and reused. If they cannot support the required experience,
  implementation stops for a new alignment rather than widening Backend scope.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `ff3093c912d4a478e71be99819c2c1cf334fdb25`; entry worktree and index are
  clean with ahead / behind `0 / 0`.
- No REWORK or `.audit` blocker exists at task entry.

## 2. Requirements

1. Add a Saved Learning Library workspace using existing local contracts.
2. Present continue-learning, bookmarked, and recently read material in one
   coherent page without duplicating or changing persistence models.
3. Support bounded local filtering and sorting over the loaded saved-learning
   records.
4. Link every valid row back to the existing Article Reader with an accurate
   canonical return path.
5. Add the workspace to desktop and mobile Application Shell navigation and to
   empty-query global quick navigation.
6. Provide complete loading, empty, unavailable, and partial-data states.
7. Preserve keyboard navigation, visible focus, semantic landmarks,
   screen-reader feedback, reduced motion, and responsive behavior.
8. Validate at desktop and 390 px mobile widths with representative real local
   data and isolated mutable state.
9. Preserve all Backend, source, data, dependency, workflow, Provider, Zotero,
   release, and published-interface boundaries.

## 3. Purpose

Give learners one dependable place to resume study, revisit bookmarks, and
recover recently read Articles, reducing navigation cost and making the
existing learning-state capabilities visible and actionable.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Audit existing Bookmark, Reading History, Learning State, Article clients,
   route parameters, shell navigation, and Product E2E coverage.
3. Define a pure Frontend view model that joins only existing records and
   classifies continue-learning, bookmarked, and recently read entries.
4. Implement the responsive `/library` workspace with bounded filters, sort,
   stable Reader destinations, and complete state handling.
5. Integrate Library into desktop/mobile Shell navigation and global quick
   navigation without changing published API contracts.
6. Add focused Frontend tests and extend isolated Product E2E coverage.
7. Validate representative real local data at 1440 x 900 and 390 x 844 with
   mutable state isolated, fake providers, and non-loopback requests blocked.
8. Run Backend regression, Frontend, build, Product E2E, workflow,
   suppression, dependency, secret, SBOM, artifact, and protected-path gates.
9. Create and push an implementation commit and verify exact-SHA main CI.
10. Create and push a docs-only closure commit and verify exact-SHA main CI.

## 5. Selection Rationale

The Saved Learning Library is the highest-value next GUI improvement because
it exposes already-implemented learning state as a repeatable daily workflow.
It improves continuity without requiring a new Backend service, schema, source
operation, or Provider.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Saved Learning Library | Selected: improves resume and saved-material workflows using existing state |
| Pure visual-theme redesign | Deferred: high visual churn with less workflow value |
| First-run onboarding | Deferred: benefits initial use more than repeated study |
| New Backend library service | Rejected: Backend and contract expansion are unauthorized |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-020_SAVED_LEARNING_LIBRARY.md`
- updated `docs/tasks/CURRENT_TASK.md`
- `/library` workspace and supporting Frontend modules under `frontend/src/`
- Shell and global-search navigation integration
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_020_SAVED_LEARNING_LIBRARY_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- `/library` builds and renders from existing local contracts.
- Continue-learning, bookmarked, and recently read sections correctly reflect
  current state without creating a new persistence model.
- Filtering, sorting, and section counts are deterministic and bounded.
- Every valid result opens the correct Article Reader and retains a canonical
  Library return path.
- Library is reachable from desktop, mobile, and global quick navigation.
- Loading, empty, partial, and unavailable states are complete and non-blocking.
- Keyboard navigation, focus, semantic landmarks, reduced motion, and
  screen-reader feedback pass.
- At 1440 x 900 and 390 x 844, the workspace has no overlap, clipped controls,
  or horizontal page overflow.
- Representative real local data passes with isolated mutable state, fake
  providers, zero external requests, and no unexpected console/page errors.
- Three consecutive isolated Product E2E runs pass without state leakage.
- Backend full tests, focused Frontend tests, production build, dependency,
  secret, workflow, suppression, SBOM, artifact, and protected-path gates pass.
- Backend, frozen M1 paths, source records, Article records, derived assets,
  dependencies, lockfiles, workflows, and published API contracts remain
  unchanged.
- No source access, private Zotero operation, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Existing published contracts cannot support the accepted workspace without
  a Backend, schema, persistence, or API change.
- Completion requires frozen M1, source, Article, derived-asset, dependency,
  lockfile, workflow, or published-interface changes.
- Completion requires source access, private Zotero access, external search,
  or a real/paid Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.

## Closure Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 70 passed
- production build: PASS, 10 routes
- Product E2E: formal 3/3 plus stress 10/10, 42 checks each
- real local probe: 1,314-Article Store with isolated mutable learning state
- visual geometry: 1,440/390 px documents without overflow
- external requests, unexpected console errors, and page errors: 0 across the
  13 consecutive production runs
- workflow, suppression, dependency, secret, security utility, and temporary
  SBOM gates: PASS
- Article Store count and SHA-256: unchanged
- protected implementation/data/dependency/workflow paths: unchanged
- implementation commit:
  `c3baf32151bd0db5937df29de4419c8c77630851`
- implementation exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33460687127`
- required implementation CI jobs: PASS
- normal-main Docker and release-evidence jobs: skipped as designed
- uploaded workflow artifacts: 0
- status: P3-020 PASS / CLOSED
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
- next task: ALIGNMENT REQUIRED / NOT GRANTED
