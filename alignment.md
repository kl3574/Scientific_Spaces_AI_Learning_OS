# P3-022 Session-Aware Learning Dashboard Alignment

Canonical task:
`docs/tasks/P3-022_LEARNING_DASHBOARD.md`

Status: **PASS / CLOSED**

LOCAL ARTICLE / SAVED LIBRARY / READING HISTORY / READER PROGRESS / FOCUSED
SESSION READ, LOCAL APPLICATION RUNTIME, TEMPORARY ISOLATED MUTABLE STATE, AND
BROWSER VALIDATION AUTHORIZATION: **GRANTED FOR P3-022**

FRONTEND / TEST / DOCUMENTATION MODIFICATION, LOCAL COMMIT / PUSH / CI
INSPECTION AUTHORIZATION: **GRANTED FOR P3-022**

BACKEND / FROZEN M1 / SOURCE RECORD / ARTICLE RECORD / DERIVED ASSET / PRIVATE
ZOTERO / REAL PROVIDER AUTHORIZATION: **NOT GRANTED**

DEPENDENCY / LOCKFILE / WORKFLOW / PUBLISHED API CONTRACT MODIFICATION
AUTHORIZATION: **NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-016 Learning Dashboard Command Center and P3-021 Focused Study Session
  are PASS / CLOSED.
- The existing Dashboard already provides learning metrics, latest Articles,
  activity, and exact single-Article resume behavior.
- P3-021 added a bounded browser-local study queue after P3-016, but the
  Dashboard does not expose that queue or its current Article. Its header still
  sends every learner to Saved Learning even when a focused session exists.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `4c9ade019692173a3884fa7c60860aff04307a38`; entry worktree and index are
  clean with ahead / behind `0 / 0`.
- No REWORK or `.audit` blocker exists at task entry.
- No v1.2 candidate version is assigned.

## 2. Requirements

1. Enhance the existing Dashboard rather than creating a duplicate workspace.
2. Load the versioned P3-021 Focused Session through its public Frontend
   contract and expose its current Article, queue position, queue size, next
   Article, and Reader progress when available.
3. Make the primary Dashboard action resume the focused session when one
   exists and retain Saved Learning as the empty-session starting point.
4. Keep the exact single-Article Continue Learning action available alongside
   the session-aware resume path.
5. React to same-tab session change events, cross-tab storage events, and page
   refreshes without introducing a new persistence model.
6. Provide controlled empty, unavailable-storage, and recovered-state
   feedback without exposing raw Article identifiers.
7. Preserve existing Dashboard partial-remote-data behavior, activity,
   overview, latest Articles, navigation, and responsive density.
8. Preserve keyboard navigation, visible focus, semantic landmarks,
   screen-reader feedback, reduced motion, and mobile behavior.
9. Preserve all Backend, source, data, dependency, workflow, Provider, Zotero,
   release, and published-interface boundaries.

## 3. Purpose

Close the continuity gap between the completed Focused Study Session and the
existing learning command center so that opening the product immediately
answers what the learner is studying now and provides the shortest safe route
back into that work.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Audit the existing Dashboard model/view, Focused Session contract, Reader
   destinations, current tests, and Product E2E workflow.
3. Add failing pure-model tests for deterministic session summary selection,
   safe Reader destinations, progress resolution, and empty behavior.
4. Add failing browser assertions for empty and populated Dashboard session
   states.
5. Implement a session-aware Dashboard presentation model and responsive
   Focused Session surface using the existing browser-local store.
6. Subscribe to bounded same-tab and cross-tab session updates and preserve
   all existing Dashboard failure behavior.
7. Validate representative real local data at 1440 x 900 and 390 x 844 with
   temporary mutable state, fake providers, and non-loopback requests blocked.
8. Run Backend regression, focused Frontend, production build, Product E2E,
   workflow, suppression, dependency, secret, SBOM, artifact, and
   protected-path gates.
9. Create and push an implementation commit and verify exact-SHA main CI.
10. Create and push a docs-only closure commit and verify exact-SHA main CI.

## 5. Selection Rationale

Enhancing the existing Command Center reuses the strongest completed product
surface and gives P3-021 a first-class daily entry point. It avoids a duplicate
Dashboard, a second queue model, and any Backend or persistence expansion.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Session-aware existing Dashboard | Selected: closes a verified continuity gap using completed contracts |
| Rebuild or duplicate the Dashboard | Rejected: P3-016 already provides the command-center foundation |
| Reader-only visual polish | Deferred: does not connect the new Session to product entry |
| Backend analytics or planning service | Rejected: requires unauthorized schema and API expansion |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-022_LEARNING_DASHBOARD.md`
- updated `docs/tasks/CURRENT_TASK.md`
- session-aware Dashboard model and view changes under `frontend/src/`
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_022_IMPLEMENTATION_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- The existing `/` Dashboard renders a Focused Session surface without adding
  a duplicate route or persistence model.
- A healthy non-empty queue shows its safe current title, exact position,
  bounded count, next title when present, and Reader progress when available.
- The primary Dashboard action opens `/session` when the queue is non-empty;
  an exact current-Article Reader action preserves the canonical `/session`
  return path.
- An empty queue points to Saved Learning and leaves Continue Learning usable.
- Same-tab change events, cross-tab storage events, and refresh recovery update
  the surface deterministically.
- Missing, malformed, or inaccessible browser storage fails closed without raw
  identifiers, crashes, or loss of independently available Dashboard content.
- Existing overview, activity, latest Articles, partial-failure Retry, Shell,
  and global navigation behavior remains intact.
- Keyboard navigation, visible focus, semantic landmarks, reduced motion, and
  screen-reader feedback pass.
- At 1440 x 900 and 390 x 844, the Dashboard has no overlap, clipped controls,
  or horizontal page overflow.
- Representative real local data passes with temporary isolated state, fake
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

## Confirmed Test Seams

1. Pure Dashboard session model: active selection, position, safe Reader href,
   progress, next Article, and empty behavior.
2. Browser workflow: empty Dashboard, populated queue, same-tab update,
   refresh, current Reader return path, recovery/unavailable states, and mobile
   geometry.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Existing contracts cannot support the accepted workflow without a Backend,
  schema, persistence API, or published-contract change.
- Completion requires frozen M1, source, Article, derived-asset, dependency,
  lockfile, workflow, or published-interface changes.
- Completion requires source access, private Zotero access, external search,
  or a real/paid Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.

## Local Acceptance Record

- Dashboard Session model and browser workflow: PASS
- Backend: 600 passed / 4 skipped
- focused Frontend: 80 passed
- production build: PASS, 11 routes
- Product E2E: 3/3 production runs, 51 checks each
- real local probe: 1,314 Articles at 1440 px and 390 px widths
- same-tab, cross-tab, recovered, unavailable, and exact Reader return states:
  PASS
- external requests, unexpected console errors, and page errors: 0
- workflow, suppression, dependency, secret, security utility, reproducible
  SBOM, artifact, and protected-path gates: PASS
- implementation commit:
  `13af4c0898bbea6a86172c924ad255702ebc8d06`
- initial implementation CI run `33588352098`: BLOCKED by a low-resource,
  repeated-hard-navigation Product E2E hydration race; all non-E2E required
  jobs passed and uploaded artifacts were zero
- E2E isolation repair commit:
  `eeef48fbd982621da1e02553f34edefe8f53f8c5`
- repair exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33590335784`
- repair CI required jobs: PASS; normal-main Docker and release-evidence jobs
  skipped as designed; uploaded artifacts: 0

## Closure Record

- local acceptance: PASS
- exact-SHA implementation plus E2E isolation repair CI: PASS
- P3-022: PASS / CLOSED
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
