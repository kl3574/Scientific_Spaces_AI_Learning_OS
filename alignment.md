# P3-021 Focused Study Session Alignment

Canonical task:
`docs/tasks/P3-021_FOCUSED_STUDY_SESSION.md`

Status: **PASS / CLOSED**

LOCAL ARTICLE / SAVED LIBRARY / READING HISTORY / READER PROGRESS READ, LOCAL
APPLICATION RUNTIME, BOUNDED BROWSER-LOCAL SESSION STATE, AND ISOLATED BROWSER
VALIDATION AUTHORIZATION: **GRANTED FOR P3-021**

FRONTEND / TEST / DOCUMENTATION MODIFICATION, LOCAL COMMIT / PUSH / CI
INSPECTION AUTHORIZATION: **GRANTED FOR P3-021**

BACKEND / FROZEN M1 / SOURCE RECORD / ARTICLE RECORD / DERIVED ASSET / PRIVATE
ZOTERO / REAL PROVIDER AUTHORIZATION: **NOT GRANTED**

DEPENDENCY / LOCKFILE / WORKFLOW / PUBLISHED API CONTRACT MODIFICATION
AUTHORIZATION: **NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-020 Saved Learning Library is PASS / CLOSED after its implementation and
  docs-only closure exact-SHA main CI passed.
- The product exposes bookmarks, recent reading, and progress in `/library`,
  but learners cannot yet organize several Articles into one continuous study
  session.
- Existing Article, Saved Library, Reading History, Reader Progress, and
  workflow contracts must be reused. No Backend learning-plan entity or API is
  authorized.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `da426dc7edab1176b2fab2bbc1df8345ec30c771`; entry worktree and index are
  clean with ahead / behind `0 / 0`.
- No REWORK or `.audit` blocker exists at task entry.
- No v1.2 candidate version is assigned.

## 2. Requirements

1. Add a `/session` Focused Study Session workspace.
2. Let learners add readable Saved Library Articles to a temporary bounded
   study queue.
3. Support deterministic add, deduplicate, reorder, remove, clear, and active
   position behavior.
4. Restore the queue and active position after a browser refresh using
   bounded browser-local state only.
5. Link the active queue item to the existing Article Reader and provide
   accurate previous, next, and return-to-session navigation.
6. Never render an internal Article identifier as the visible title of an
   unavailable record.
7. Integrate Session into desktop/mobile Application Shell navigation and
   empty-query global quick navigation.
8. Provide complete loading, empty, unavailable, stale-record, and bounded
   recovery states.
9. Preserve keyboard navigation, visible focus, semantic landmarks,
   screen-reader feedback, reduced motion, and responsive behavior.
10. Preserve all Backend, source, data, dependency, workflow, Provider,
    Zotero, release, and published-interface boundaries.

## 3. Purpose

Turn the Saved Learning Library into an executable multi-Article workflow so
learners can assemble, resume, and complete a focused study session without
losing their place or requiring a new server-side planning model.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Audit Saved Library, Article Reader, browser-local stores, route context,
   Shell navigation, and Product E2E coverage.
3. Use red-green TDD at two confirmed public seams: the pure study-session
   queue model and the browser-visible `/session` workflow.
4. Implement a versioned browser-local queue capped at 20 readable Articles,
   with safe identifiers and deterministic recovery.
5. Implement the responsive `/session` workspace and Saved Library queue
   actions.
6. Add Reader previous/next/return session controls while preserving existing
   Article, Tutor, and Graph return context.
7. Integrate Session into desktop/mobile Shell and global quick navigation.
8. Validate representative real local data at 1440 x 900 and 390 x 844 with
   mutable state isolated, fake providers, and non-loopback requests blocked.
9. Run Backend regression, focused Frontend, production build, Product E2E,
   workflow, suppression, dependency, secret, SBOM, artifact, and
   protected-path gates.
10. Create and push an implementation commit and verify exact-SHA main CI.
11. Create and push a docs-only closure commit and verify exact-SHA main CI.

## 5. Selection Rationale

A Focused Study Session is the next coherent extension of P3-020. It converts
saved material into a repeatable learning flow while remaining entirely on
existing Article and browser-local contracts.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Focused Study Session | Selected: directly improves continuous study using the completed Saved Library |
| Global visual-theme redesign | Deferred: broad visual churn with less workflow value |
| First-run onboarding | Deferred: primarily benefits initial use rather than daily study |
| Backend learning-plan service | Rejected: requires an unauthorized entity, schema, and API |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-021_FOCUSED_STUDY_SESSION.md`
- updated `docs/tasks/CURRENT_TASK.md`
- `/session` workspace and bounded browser-local queue modules under
  `frontend/src/`
- Saved Library, Reader, Shell, and global-search session integration
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_021_FOCUSED_STUDY_SESSION_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- `/session` builds and renders using only existing local Article contracts
  and one versioned browser-local queue.
- The queue accepts at most 20 readable, valid, unique Article records.
- Add, deduplicate, reorder, remove, clear, active-position, and refresh
  recovery behavior are deterministic and tested through the public model.
- Saved Library can add an Article to the queue without losing its current
  filter/view/sort state.
- Session opens the correct Reader destination; previous, next, and return
  controls preserve a canonical Session return path.
- Missing or malformed records fail closed without exposing raw identifiers,
  corrupting the queue, or preventing healthy entries from loading.
- Session is reachable from desktop, mobile, and global quick navigation.
- Loading, empty, stale, bounded, and unavailable states are complete and
  actionable.
- Keyboard navigation, visible focus, semantic landmarks, reduced motion, and
  screen-reader feedback pass.
- At 1440 x 900 and 390 x 844, the workspace has no overlap, clipped controls,
  or horizontal page overflow.
- Representative real local data passes with isolated mutable state, fake
  providers, zero external requests, and no unexpected console/page errors.
- Three consecutive isolated Product E2E runs pass without state leakage.
- Backend full tests, focused Frontend tests, production build, dependency,
  secret, workflow, suppression, SBOM, artifact, and protected-path gates
  pass.
- Backend, frozen M1 paths, source records, Article records, derived assets,
  dependencies, lockfiles, workflows, and published API contracts remain
  unchanged.
- No source access, private Zotero operation, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Confirmed Test Seams

1. Pure queue model: serialization, validation, bounds, deduplication,
   ordering, active position, and canonical Reader destinations.
2. Browser workflow: Saved Library add action, `/session` recovery and queue
   controls, Reader previous/next/return behavior, failure states, and mobile
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

## Closure Record

- local acceptance: PASS
- implementation commit:
  `df4500c17b2456aedde36a039a60a92f631e6ea9`
- implementation exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33489296319`
- required implementation CI jobs: PASS
- uploaded workflow artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
