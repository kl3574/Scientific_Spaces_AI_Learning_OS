# P3-013 Reader Workspace and Learning Continuity

## Status

LOCAL GATES PASS / EXACT-SHA CI PENDING

## Objective

Turn Article Detail into a structured, resumable scientific reading workspace
using only existing Article and learning contracts.

## Authoritative Alignment

`alignment.md`

## Entry State

- branch: `main`
- entry commit: `6b297d8ae21b1b43ef2e6e7a1b0bef51e5d71b83`
- P3-012: PASS / CLOSED
- exact local corpus: 1,314 Articles with matching derived assets
- candidate version: not assigned

## In Scope

- deterministic Markdown outline and unique anchors
- current-section and progress feedback
- local per-Article resume state
- local reader display preferences
- Dashboard Continue Reading entry
- desktop/mobile, keyboard, reduced-motion, and content-format verification
- focused Frontend and isolated product E2E coverage
- task evidence, implementation/closure commits, push, and exact-SHA CI

## Protected Boundaries

- no frozen M1 or Article source-record changes
- no Backend or published API contract changes
- no source-site access or private Zotero reads/writes
- no real or paid Provider calls
- no candidate, tag, Release, or attestation
- no committed runtime stores, databases, screenshots, traces, profiles,
  credentials, secrets, corpus files, or generated assets

## Deliverables

- Article reading-workspace helpers and components
- Article Detail and Dashboard integration
- focused tests and expanded product E2E
- `docs/P3_013_READER_WORKSPACE_REPORT.md`
- governance updates and two-commit exact-SHA CI closure

## Acceptance

- stable unique outline anchors and keyboard navigation
- active section, bounded progress, and local resume behavior pass
- Dashboard Continue Reading and empty behavior pass
- reversible local display preferences pass
- desktop/mobile content and accessibility gates pass
- three isolated E2E runs and all repository quality gates pass
- protected boundaries remain unchanged
- final branch is clean and synchronized

## Stop Rule

Stop without widening scope if completion requires a protected contract,
external side effect, private data action, release action, or unresolved
critical regression.

## Local Evidence

- real-corpus Chromium: 5 Articles, 74/74 unique anchors, desktop/mobile PASS
- resume closure: saved and restored the same meaningful section
- Backend: 600 passed, 4 skipped
- focused Frontend: 35 passed
- production build: PASS
- isolated product E2E: 3/3 runs, 19 checks per run, 0 external requests
- workflow, suppression, dependency, secret, artifact, and SBOM gates: PASS
- report: `docs/P3_013_READER_WORKSPACE_REPORT.md`
- implementation exact-SHA main CI: pending
