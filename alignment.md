# P3-019 Global Search and Quick Navigation Alignment

Canonical task:
`docs/tasks/P3-019_GLOBAL_SEARCH_AND_QUICK_NAVIGATION.md`

Status: **PASS / CLOSED**

LOCAL ARTICLE / STRUCTURED REFERENCE / GRAPH DATA READ, LOCAL APPLICATION
RUNTIME, AND ISOLATED BROWSER VALIDATION AUTHORIZATION: **GRANTED FOR P3-019**

FRONTEND / TEST / DOCUMENTATION MODIFICATION, LOCAL COMMIT / PUSH / CI
INSPECTION AUTHORIZATION: **GRANTED FOR P3-019**

BACKEND / FROZEN M1 / SOURCE RECORD / DERIVED ASSET / PRIVATE ZOTERO / REAL
PROVIDER AUTHORIZATION: **NOT GRANTED**

DEPENDENCY / LOCKFILE / WORKFLOW / PUBLISHED API CONTRACT MODIFICATION
AUTHORIZATION: **NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-018 Unified Application Shell and Navigation is PASS / CLOSED after its
  implementation, bounded hydration repair, and docs-only closure exact-SHA
  main CI passed.
- Dashboard, Articles, References, Graph, and Tutor now share one responsive
  shell, but learners must still enter each workspace before they can find a
  specific Article, structured Reference, or Graph concept.
- The published local Article, structured Reference, and Graph APIs already
  support bounded text search. The new interaction can therefore remain a
  Frontend aggregation layer with no Backend, data, or contract expansion.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `01b572ed2af8e32efa4e9bdb77a4f66628574054`; entry worktree and index are
  clean with ahead / behind `0 / 0`.
- No REWORK or `.audit` blocker exists at task entry.

## 2. Requirements

1. Add one global search and quick-navigation entry to the shared Application
   Shell on desktop and mobile.
2. Search existing Article title/content, structured Reference fields, and
   Graph node labels through the current published local APIs.
3. Show human-readable grouped results and never expose raw Article,
   Reference, or Graph identifiers as visible result labels.
4. Provide exact internal destinations for Article and Graph results and a
   source-Article destination for structured References.
5. Preserve valid Article search/list return context and existing learning
   workflow context when the search surface is opened or dismissed.
6. Support keyboard invocation, arrow-key result selection, Enter activation,
   Escape dismissal, focus trapping, focus restoration, and visible focus.
7. Make the interaction complete at desktop and 390 px mobile widths without
   overlap, clipping, or horizontal page overflow.
8. Present bounded idle, loading, partial-error, empty, and unavailable states
   without erasing usable results from healthy sources.
9. Validate the integrated behavior with focused Frontend tests, production
   build, repeated isolated Product E2E, and representative real local data.
10. Preserve frozen Backend, source, data, dependency, workflow, Provider,
    Zotero, release, and published-interface boundaries.

## 3. Purpose

Reduce the cost of finding and moving to learning material by turning the
shared shell into a direct, accessible entry point for Articles, structured
References, Graph concepts, and stable workspaces.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Audit current search APIs, Frontend clients, route parameters, shell focus
   behavior, and Product E2E coverage.
3. Define pure bounded query, result, destination, grouping, and partial-error
   helpers using existing clients.
4. Implement an accessible global search dialog and shell triggers for desktop
   and mobile, including quick workspace navigation.
5. Add safe Graph deep-link hydration and preserve canonical Article return
   paths without changing published API contracts.
6. Add focused Frontend tests and extend isolated Product E2E coverage.
7. Validate representative real local Article, Reference, and Graph searches
   at 1440 x 900 and 390 x 844 with mutable state isolated, fake providers,
   and all non-loopback browser requests blocked.
8. Run Backend regression, Frontend, build, Product E2E, workflow,
   suppression, dependency, secret, SBOM, artifact, and protected-path gates.
9. Create and push an implementation commit and verify exact-SHA main CI.
10. Create and push a docs-only closure commit and verify exact-SHA main CI.

## 5. Selection Rationale

P3-018 made location and movement predictable. A bounded search layer now
provides the highest-value next GUI improvement because it reuses every major
learning surface without requiring a new Backend service or data migration.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Global search and quick navigation | Selected: improves findability across all current workspaces using existing APIs |
| Pure visual-theme redesign | Deferred: high visual churn with less workflow value |
| First-run onboarding | Deferred: helps new users but not repeated daily navigation |
| New Backend search service | Rejected: current bounded APIs are sufficient and Backend expansion is unauthorized |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-019_GLOBAL_SEARCH_AND_QUICK_NAVIGATION.md`
- updated `docs/tasks/CURRENT_TASK.md`
- global-search model and accessible shell components under `frontend/src/`
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_019_GLOBAL_SEARCH_AND_QUICK_NAVIGATION_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- One global entry opens from desktop and mobile Shell controls and from the
  documented keyboard shortcut.
- Empty-query mode exposes all stable workspaces as quick navigation; bounded
  query mode searches Articles, structured References, and Graph nodes.
- Result groups use readable titles, source/type context, and accurate internal
  destinations without visible raw identifiers.
- Article results retain a canonical relevance-search return path; Graph
  results load the selected node; Reference results return to their source
  Article without opening an external URL.
- Stale responses cannot replace a newer query, and one failed source does not
  hide healthy-source results.
- Arrow keys, Enter, Escape, Tab/Shift+Tab focus trap, autofocus, and trigger
  focus restoration pass.
- At 1440 x 900 and 390 x 844, dialog, results, shell, and page content have no
  overlap, clipped controls, or horizontal page overflow.
- Keyboard access, semantic dialog/list landmarks, visible focus, reduced
  motion, and screen-reader status updates remain available.
- Representative real local Article, Reference, and Graph search flows pass
  with zero external requests and no unexpected console/page errors.
- Three consecutive isolated Product E2E runs pass without state leakage.
- Backend full tests, focused Frontend tests, production build, dependency,
  secret, workflow, suppression, SBOM, artifact, and protected-path gates
  pass.
- Backend, frozen M1 paths, source records, Article records, derived assets,
  dependencies, lockfiles, workflows, and published API contracts remain
  unchanged.
- No source access, private Zotero read/write, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Completion requires Backend, frozen M1, source-record, Article-record,
  derived-asset, dependency, lockfile, workflow, or published-interface
  changes.
- Completion requires source access, private Zotero access, or a real/paid
  Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.

## Closure Evidence

- local acceptance: PASS
- implementation commit:
  `c92b08990490b1d55296eaafbd829462394a2f21`
- implementation exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33389364565`
- required implementation CI jobs: PASS
- normal-main Docker and release-evidence jobs: skipped as designed
- uploaded workflow artifacts: 0
- status: P3-019 PASS / CLOSED
- next task: ALIGNMENT REQUIRED / NOT GRANTED
