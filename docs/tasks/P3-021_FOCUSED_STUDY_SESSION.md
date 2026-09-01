# P3-021 Focused Study Session

Status: **PASS / CLOSED**

## Objective

Create a responsive Focused Study Session that turns existing Saved Library
records into a bounded, resumable multi-Article queue without changing Backend
contracts or persistence models.

## Entry Evidence

- branch: `main`
- entry commit: `da426dc7edab1176b2fab2bbc1df8345ec30c771`
- cached `origin/main`: `da426dc7edab1176b2fab2bbc1df8345ec30c771`
- ahead / behind: `0 / 0`
- worktree and index: clean
- REWORK / `.audit`: absent
- predecessor: P3-020 PASS / CLOSED
- v1.2 candidate: not assigned

## In Scope

- audit and reuse existing Article, Saved Library, Reading History, Reader
  Progress, workflow, and navigation contracts
- `/session` workspace with a versioned browser-local queue capped at 20
  readable unique Articles
- add, deduplicate, reorder, remove, clear, active-position, and recovery
  behavior
- Saved Library add action and Reader previous/next/return navigation
- desktop/mobile Shell and global quick-navigation integration
- complete empty, stale, bounded, and unavailable states
- keyboard, focus, semantic, screen-reader, reduced-motion, and responsive UX
- focused Frontend tests, isolated Product E2E, and real local-data probes
- governance, implementation evidence, commits, push, and exact-SHA CI closure

## Out Of Scope

- Backend or published API changes
- server-side learning-plan schema, entity, or synchronization
- frozen M1/source pipeline changes
- source, Article, or derived-data mutations or rebuilds
- dependency, lockfile, or workflow changes
- private Zotero access or mutation
- source-site access or external search
- real or paid Provider calls
- candidate, tag, Release, or attestation actions
- authentication, multi-user state, hosted deployment, or cross-device sync

## Planned Changes

- Session page, queue model/store, and components under `frontend/src/`
- existing Library, Reader, Shell, and global-search presentation integration
- focused tests under `frontend/tests/`
- Session regression coverage in `scripts/e2e/run_product_e2e.py`
- `alignment.md`, task/status/report/roadmap/README documentation

## Confirmed Test Seams

1. Pure queue model public functions and browser-store serialization.
2. Browser-visible `/library` -> `/session` -> Reader -> `/session` workflow.

## Acceptance

1. `/session` renders with existing Article contracts and one versioned
   browser-local queue.
2. The queue accepts no more than 20 valid, readable, unique Article records.
3. Add, deduplicate, reorder, remove, clear, active position, and refresh
   recovery are deterministic.
4. Library state remains intact when adding an Article to the queue.
5. Reader previous, next, and return controls target the correct queue records
   through a canonical Session return path.
6. Malformed or stale records fail closed without exposing raw identifiers or
   hiding healthy entries.
7. Desktop, mobile, and global quick navigation reach Session.
8. Accessibility, 1440 x 900, and 390 x 844 behavior pass without overlap or
   overflow.
9. Representative real local data and three repeated isolated Product E2E
   runs pass with fake providers, isolated mutable state, zero external
   requests, and no unexpected console/page errors.
10. Full local quality, security, artifact, and protected-path gates pass with
    zero Backend, dependency, lockfile, workflow, data, or API changes.
11. Implementation and docs-only closure commits each pass exact-SHA main CI;
    final `main` is clean and synchronized.

## Authorization

- local Article/Library/History/Progress reads, bounded browser-local session
  state, local application runtime, and isolated browser validation: GRANTED
  FOR P3-021
- Frontend/tests/docs edits, local commits, push, and CI inspection: GRANTED
  FOR P3-021
- Backend/frozen M1/source records/Article records/derived assets: NOT GRANTED
- dependency/lockfile/workflow/published API changes: NOT GRANTED
- source network/private Zotero/real Provider/external search: NOT GRANTED
- candidate/tag/Release/attestation: NOT GRANTED

## Stop Conditions

Stop if an unknown worktree change appears, existing contracts are
insufficient without widening scope, a protected path or artifact changes,
external/private access becomes necessary, or any release action becomes
necessary.

## Local Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 77 passed
- production build: PASS, 11 routes
- Product E2E: 3/3 formal runs, 48 checks each
- real local data: 1,314 Articles; two real Chinese mathematics Articles in
  isolated Library and Session state; desktop/mobile PASS
- external requests, unexpected console errors, and page errors: 0
- workflow, suppression, dependency, secret, security utility, temporary SBOM,
  artifact, and protected-path gates: PASS
- implementation commit:
  `df4500c17b2456aedde36a039a60a92f631e6ea9`
- implementation exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33489296319`
- required implementation CI jobs: PASS
- normal-main Docker and release-evidence jobs: skipped as designed
- uploaded workflow artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
