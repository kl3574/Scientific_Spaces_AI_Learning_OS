# P3-016 Learning Dashboard Command Center

## Status

LOCAL PASS / IMPLEMENTATION CI PENDING

## Objective

Turn the existing Dashboard into a compact, resilient learning command center
without changing Backend interfaces or persisted product data.

## Authoritative Alignment

`alignment.md`

## Entry State

- branch: `main`
- entry commit: `38e5d50990acb3886b84480417721806c1e6ec25`
- cached `origin/main`: exact match
- worktree: clean
- P3-015: PASS / CLOSED
- candidate version: not assigned

## In Scope

- pure Dashboard presentation model
- learning overview and deterministic progress semantics
- exact Continue Learning resume action
- bounded unified activity timeline with resolved titles
- latest-library and next-action surfaces
- independent partial-data failure and retry behavior
- keyboard, focus, reduced-motion, responsive, loading, and empty states
- focused Frontend and isolated Product E2E coverage
- read-only real local Article browser validation with temporary mutable state
- evidence report, implementation/closure commits, push, and exact-SHA CI

## Protected Boundaries

- no Backend or published interface changes
- no frozen M1, Article source-record, or derived RAG/Graph/Reference changes
- no source-site access or private Zotero reads/writes
- no real or paid Provider calls
- no candidate, tag, Release, or attestation
- no committed runtime stores, databases, screenshots, traces, profiles,
  credentials, secrets, corpus files, or generated assets

## Deliverables

- Dashboard presentation model and command-center integration
- focused tests and expanded Product E2E
- `docs/P3_016_LEARNING_DASHBOARD_COMMAND_CENTER_REPORT.md`
- governance updates and two-commit exact-SHA CI closure

## Acceptance

- overview, exact resume, unified activity, latest Articles, and next actions work
- partial failures preserve independently available content and expose retry
- desktop/mobile geometry, keyboard, and reduced-motion checks pass
- three isolated Product E2E runs and all repository quality gates pass
- protected implementation and data boundaries remain unchanged
- final branch is clean and synchronized

## Stop Rule

Stop without widening scope if completion requires a protected interface,
external data side effect, private-data action, release action, or unresolved
critical regression.
