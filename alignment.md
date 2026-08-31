# P3-016 Learning Dashboard Command Center Alignment

Canonical task:
`docs/tasks/P3-016_LEARNING_DASHBOARD_COMMAND_CENTER.md`

Status: **PASS / CLOSED**

LOCAL ARTICLE DATA READ / APPLICATION RUNTIME / COMPUTER USE AUTHORIZATION:
**CONSUMED / CLOSED**

FRONTEND / TEST / DOCUMENTATION MODIFICATION, COMMIT / PUSH / CI INSPECTION
AUTHORIZATION: **CONSUMED / CLOSED AFTER THE DOCS-ONLY CLOSURE COMMIT**

SOURCE NETWORK / PRIVATE ZOTERO READ-WRITE / REAL PROVIDER AUTHORIZATION:
**NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-015 Visual Knowledge Explorer is PASS / CLOSED with implementation and
  docs-only closure exact-SHA main CI passing.
- Dashboard currently exposes six equal-weight counters, one latest-history
  resume link, recent Articles, and three overlapping activity lists.
- Any Article or learning-stats request failure currently replaces the entire
  Dashboard, even when useful local or independently loaded data remains.
- Recent Sessions display raw Article IDs and duplicate information already
  shown by Recent Learning and browser-local Reading History.
- Existing Article, learning-state, bookmark, session, Reader progress, and
  Reading History interfaces are sufficient for a coherent command center;
  no Backend contract or persisted-data change is required.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `38e5d50990acb3886b84480417721806c1e6ec25`; entry worktree is clean.
- No REWORK or `.audit` blocker exists at task entry.

## 2. Requirements

1. Turn the Dashboard into a compact learning command center while retaining
   the project title and current route structure.
2. Present a meaningful learning overview with completion, active-reading,
   saved-item, and note signals instead of six unrelated counters alone.
3. Preserve one prioritized Continue Learning action with exact Article and
   Reader section progress.
4. Replace overlapping activity lists with one bounded chronological learning
   timeline that resolves human-readable Article titles.
5. Add a clear next-actions surface for Articles, Tutor, Graph, and Zotero
   using existing local routes.
6. Keep independently available Dashboard sections usable when one remote
   request fails; expose a bounded warning and retry action.
7. Preserve loading, empty, keyboard, focus, reduced-motion, and responsive
   behavior at desktop and mobile widths.
8. Reuse current Frontend clients and published APIs; add no Backend or data
   contract.
9. Add focused pure-model tests and extend isolated Product E2E coverage.
10. Run Backend, Frontend, E2E, dependency, secret, workflow, suppression,
    SBOM, artifact, and protected-path gates.

## 3. Purpose

Make the first screen answer four learner questions immediately: what is my
current state, where should I resume, what happened recently, and which
existing learning tool should I use next.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Audit the existing Dashboard model, local Reader state, learning APIs, and
   real local Article presentation at 1440 x 900 and 390 x 844.
3. Add a pure Dashboard presentation model for progress, resume selection,
   title resolution, bounded activity merging, and partial-data states.
4. Refactor `DashboardView` into a compact overview, Continue Learning,
   activity timeline, latest-library list, and next-action surface.
5. Keep independently successful data visible through `Promise.allSettled`
   loading and bounded partial-failure presentation.
6. Add pure helper tests and Dashboard browser regression checks.
7. Validate representative real local Articles with mutable state redirected
   to temporary storage and all external requests blocked.
8. Run all required local quality, compatibility, security, and artifact gates.
9. Create and push an implementation commit and verify exact-SHA main CI.
10. Create and push a docs-only closure commit and verify its exact-SHA main CI.

## 5. Selection Rationale

Reader, Tutor, Graph, Zotero, and learning-state capabilities already exist.
The Dashboard is the highest-leverage place to expose them as one coherent
daily workflow. A pure project-owned presentation model improves semantics,
testability, and partial-failure behavior without a new dependency or Backend
surface.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Learning Dashboard command center | Selected: improves the primary entry point using current contracts |
| Tutor-only GUI redesign | Deferred: valuable but limited to one downstream tool |
| Global visual restyling | Rejected: broad churn without a measurable workflow outcome |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-016_LEARNING_DASHBOARD_COMMAND_CENTER.md`
- updated `docs/tasks/CURRENT_TASK.md`
- `frontend/src/lib/dashboard.ts`
- bounded Dashboard component and style updates under `frontend/src/`
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_016_LEARNING_DASHBOARD_COMMAND_CENTER_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- Dashboard visibly presents learning overview, exact Continue Learning,
  bounded activity, latest Articles, and next actions.
- Completion percentage and counts are deterministic, bounded, and derived
  only from current API fields.
- Continue Learning preserves the exact Article and safe section anchor.
- Activity is reverse chronological, bounded, title-resolved where evidence is
  available, and avoids duplicate raw-ID-only lists.
- An Article or learning request can fail independently without hiding all
  successful local/remote Dashboard content; warning and retry remain visible.
- Existing fully empty and fully failed states are controlled.
- At 1440 x 900 and 390 x 844, primary content has stable dimensions with no
  page overflow, overlap, clipped action, or wrapped primary navigation.
- Primary controls are keyboard reachable, visibly focused, meaningfully
  named, and respect reduced-motion preference.
- Three to five real local Articles pass browser validation with mutable state
  isolated and zero external requests, console errors, and page errors.
- Three consecutive isolated Product E2E runs pass without state leakage.
- Backend full tests, all focused Frontend tests, production build, security,
  artifact, workflow, dependency, and SBOM gates pass.
- Backend, frozen M1 paths, Article records, derived assets, and published API
  contracts remain unchanged.
- No source access, private Zotero read/write, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Completion requires Backend, frozen M1, source-record, derived-asset, or
  published-interface changes.
- Completion requires source access, private Zotero access, or a real/paid
  Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.

## Closure Evidence

- local Backend, Frontend, real-Article browser, Product E2E, workflow,
  dependency, secret, suppression, SBOM, artifact, and protected-path gates:
  PASS
- implementation commit: `fe4cf5e50a2a4c39982ca0e879d0a18cd561e904`
- implementation exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33353446426`
- Backend, Frontend, Product E2E, workflow, dependency, secret, and SBOM jobs:
  PASS
- Docker compose smoke and release evidence: correctly skipped for a normal
  `main` push
- workflow artifacts: 0
- docs-only closure commit: this commit; exact-SHA CI must pass before final
  completion is reported
- next task: ALIGNMENT REQUIRED / NOT GRANTED
