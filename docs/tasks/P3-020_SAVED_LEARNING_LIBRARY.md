# P3-020 Saved Learning Library

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

## Objective

Create a responsive Saved Learning Library that joins existing Bookmark,
Reading History, Learning State, and Article data into one actionable workspace
without changing Backend contracts or persistence models.

## Entry Evidence

- branch: `main`
- entry commit: `ff3093c912d4a478e71be99819c2c1cf334fdb25`
- cached `origin/main`: `ff3093c912d4a478e71be99819c2c1cf334fdb25`
- ahead / behind: `0 / 0`
- worktree and index: clean
- REWORK / `.audit`: absent
- predecessor: P3-019 PASS / CLOSED

## In Scope

- audit and reuse existing Article, Bookmark, Reading History, and Learning
  State Frontend clients and published local APIs
- `/library` workspace with continue-learning, bookmarked, and recently read
  sections
- deterministic bounded filter, sort, counts, and stable Reader destinations
- desktop/mobile Shell and global quick-navigation integration
- complete loading, empty, partial-data, and unavailable states
- keyboard, focus, semantic, screen-reader, reduced-motion, and responsive UX
- focused Frontend tests, isolated Product E2E, and real local-data probes
- governance, implementation evidence, commits, push, and exact-SHA CI closure

## Out Of Scope

- Backend or published API changes
- new persistence schema or business entity
- frozen M1/source pipeline changes
- source, Article, or derived-data mutations or rebuilds
- dependency, lockfile, or workflow changes
- private Zotero access or mutation
- source-site access or external search
- real or paid Provider calls
- candidate, tag, Release, or attestation actions
- authentication, multi-user state, hosted deployment, or synchronization

## Planned Changes

- Library page, view model, and components under `frontend/src/`
- existing Shell and global-search presentation for navigation integration
- focused tests under `frontend/tests/`
- Library regression coverage in `scripts/e2e/run_product_e2e.py`
- `alignment.md`, task/status/report/roadmap/README documentation

## Acceptance

1. `/library` renders using only existing local contracts.
2. Continue-learning, bookmarked, and recently read sections reflect current
   records without creating or mutating a new store.
3. Local filtering, sorting, and counts are deterministic and bounded.
4. Valid entries open the correct Reader destination with a canonical Library
   return path.
5. Desktop, mobile, and global quick navigation reach Library.
6. Loading, empty, partial-data, and unavailable states are usable.
7. Keyboard, focus, semantic, screen-reader, reduced-motion, and 390 px mobile
   behavior pass without overlap or overflow.
8. Representative real local data and three repeated isolated Product E2E
   runs pass with fake providers, isolated mutable state, zero external
   requests, and no unexpected console/page errors.
9. Full local quality, security, artifact, and protected-path gates pass with
   zero Backend, dependency, lockfile, workflow, data, or API changes.
10. Implementation and docs-only closure commits each pass exact-SHA main CI;
    final `main` is clean and synchronized.

## Authorization

- local Article/Bookmark/History/Learning State reads, local application
  runtime, and isolated browser validation: GRANTED FOR P3-020
- Frontend/tests/docs edits, local commits, push, and CI inspection: GRANTED
  FOR P3-020
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
- focused Frontend: 70 passed
- production build: PASS, 10 routes
- Product E2E: 3/3 formal and 10/10 stress runs, 42 checks each
- real local data: 1,314 Articles; isolated Bookmark, Learning State, History,
  and Reader Progress; desktop/mobile PASS
- external requests, unexpected console errors, and page errors: 0 across 13
  consecutive production runs
- workflow, suppression, dependency, secret, security utility, temporary SBOM,
  artifact, and protected-path gates: PASS
- implementation exact-SHA main CI: pending
