# P3-018 Unified Application Shell and Navigation Alignment

Canonical task:
`docs/tasks/P3-018_UNIFIED_APPLICATION_SHELL_AND_NAVIGATION.md`

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

LOCAL ARTICLE DATA READ / LOCAL APPLICATION RUNTIME / ISOLATED BROWSER
VALIDATION AUTHORIZATION: **GRANTED FOR P3-018**

FRONTEND / TEST / DOCUMENTATION MODIFICATION, LOCAL COMMIT / PUSH / CI
INSPECTION AUTHORIZATION: **GRANTED FOR P3-018**

BACKEND / FROZEN M1 / SOURCE RECORD / DERIVED RAG-GRAPH-REFERENCE / PRIVATE
ZOTERO / REAL PROVIDER AUTHORIZATION: **NOT GRANTED**

DEPENDENCY / LOCKFILE / WORKFLOW / PUBLISHED API CONTRACT MODIFICATION
AUTHORIZATION: **NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-017 Guided Tutor Study Workspace is PASS / CLOSED with implementation
  and docs-only closure exact-SHA main CI complete.
- Dashboard, Articles, References, Graph, and Tutor are individually
  functional, while the integrated Workflow connects them through contextual
  actions. Their navigation and page framing must now be evaluated as one
  application rather than as separate feature surfaces.
- A unified application shell is the next bounded GUI improvement: it can
  clarify location, provide direct workspace transitions, and standardize
  responsive and system states without widening Backend or data contracts.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `abadf6d03aa5f7632085bb2393dfbad35c1ea6ff`; entry worktree and index are
  clean with ahead / behind `0 / 0`.
- No REWORK or `.audit` blocker exists at task entry.

## 2. Requirements

1. Establish one coherent Application Shell and global navigation across all
   primary learning workspaces.
2. Make the current workspace and active route unambiguous without exposing
   implementation identifiers.
3. Provide contextual return or breadcrumb affordances where a real route
   hierarchy exists; do not manufacture decorative hierarchy.
4. Preserve each workspace's existing user state and deep-link behavior while
   navigating through the shell.
5. Make desktop and 390 px mobile navigation complete, stable, and free of
   overlap, clipping, or horizontal page overflow.
6. Standardize bounded loading, empty, error, and unavailable presentation
   where existing shared behavior can be reused without rewriting feature
   business logic.
7. Preserve keyboard access, visible focus, reduced-motion behavior, and
   semantic navigation landmarks.
8. Validate the integrated shell with focused Frontend tests, the production
   build, repeated isolated Product E2E, and representative real local Article
   workflows.
9. Preserve all frozen Backend, Article, derived-data, source, Provider,
   Zotero, dependency, lockfile, workflow, and published-interface boundaries.

## 3. Purpose

Turn the existing collection of capable workspaces into a coherent learning
application in which learners can always identify where they are and move
between reading, study management, references, knowledge exploration, and
Tutor work without losing context or encountering inconsistent navigation.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Audit the existing route tree, layouts, navigation components, responsive
   behavior, system states, and Product E2E coverage.
3. Define a bounded project-owned shell model using the existing route and
   icon dependencies.
4. Implement the desktop and mobile shell, active-route indication,
   contextual return/breadcrumb behavior, and shared state presentation.
5. Integrate all primary workspaces without changing their business contracts
   or destroying route-local state.
6. Add focused Frontend tests and extend isolated Product E2E coverage.
7. Validate representative real local Article workflows at 1440 x 900 and
   390 x 844 with mutable state isolated, fake providers, and external
   requests blocked.
8. Run Backend regression, Frontend, build, Product E2E, workflow,
   suppression, dependency, secret, SBOM, artifact, and protected-path gates.
9. Create and push an implementation commit and verify exact-SHA main CI.
10. Create and push a docs-only closure commit and verify exact-SHA main CI.

## 5. Selection Rationale

The existing product surfaces already carry the required learning
capabilities. Improving the shared shell produces platform-wide GUI value and
reduces navigation cost while retaining the stable Backend and data contracts.
It is therefore the highest-leverage bounded next step after the Tutor
workspace.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Unified Application Shell and navigation | Selected: improves every current workspace without contract expansion |
| Continue enhancing only Tutor | Deferred: P3-017 already closed its bounded Tutor usability gaps |
| Full visual redesign | Rejected: broad visual churn without a bounded workflow result |
| Backend navigation or session API | Rejected: navigation is a Frontend responsibility and existing contracts are sufficient |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-018_UNIFIED_APPLICATION_SHELL_AND_NAVIGATION.md`
- updated `docs/tasks/CURRENT_TASK.md`
- project-owned shell, navigation, and bounded shared-state components under
  `frontend/src/`
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_018_UNIFIED_APPLICATION_SHELL_AND_NAVIGATION_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- Dashboard, Articles, References, Graph, and Tutor are directly reachable
  through one semantic global navigation model; the integrated learning
  Workflow remains available through its existing context-preserving actions.
- Current route and workspace are visually and programmatically identifiable.
- Contextual return/breadcrumb controls preserve valid existing deep-link and
  workflow state; primary navigation does not silently discard query state.
- At 1440 x 900 and 390 x 844, navigation and page content have no overlap,
  clipped actions, unusable controls, or horizontal page overflow.
- Mobile navigation opens, closes, focuses, and returns focus predictably;
  Escape and route selection close it.
- Keyboard navigation, visible focus, semantic landmarks, and reduced-motion
  behavior remain available.
- Shared loading, empty, error, and unavailable states are consistent and do
  not remove usable current workspace content during auxiliary failures.
- Representative real local Article workflows can move among Reader,
  Dashboard, Graph, and Tutor without external requests or console/page
  errors.
- Three consecutive isolated Product E2E runs pass without state leakage.
- Backend full tests, focused Frontend tests, production build, dependency,
  secret, workflow, suppression, SBOM, artifact, and protected-path gates
  pass.
- Backend, frozen M1 paths, Article records, derived RAG/Graph/Reference
  assets, dependencies, lockfiles, workflows, and published API contracts
  remain unchanged.
- No source access, private Zotero read/write, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Completion requires Backend, frozen M1, source-record, derived-asset,
  dependency, lockfile, workflow, or published-interface changes.
- Completion requires source access, private Zotero access, or a real/paid
  Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.

## Local Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 59 passed
- Next.js production build: PASS, 9 routes
- Product E2E: 3 of 3 runs, 32 checks per run
- real local Article shell probe: 5 of 5 PASS at 1440 x 900 and 390 x 844
- Reader / Graph / Tutor / References cross-workspace navigation: PASS
- external browser requests, unexpected console errors, and page errors: 0
- workflow policy, suppression policy, dependency audit, staged secret audit,
  security utility tests, and temporary SBOM validation: PASS
- implementation CI, commit, and closure evidence: pending
