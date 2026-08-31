# P3-014 Integrated Learning Workflow

## Status

ACTIVE / IMPLEMENTATION AUTHORIZED

## Objective

Connect the existing Dashboard, Reader, Tutor, Graph, and learning-state
surfaces into a coherent, context-preserving study journey using only existing
contracts.

## Authoritative Alignment

`alignment.md`

## Entry State

- branch: `main`
- entry commit: `5be49f05d1bf8055a8e844237fc7a058ca7c90d7`
- cached `origin/main`: exact match
- worktree: clean
- P3-013: PASS / CLOSED
- candidate version: not assigned

## In Scope

- real local desktop/mobile learning-journey audit
- platform-neutral repository governance cleanup in `AGENTS.md`
- Frontend-only workflow and GUI improvements selected from evidence
- Article-context and safe-return-path continuity
- Dashboard, Article, Tutor, Graph, notes/bookmark integration using existing
  contracts
- controlled loading, empty, error, and 404 states
- keyboard, focus, reduced-motion, and responsive verification
- focused Frontend and isolated Product E2E coverage
- evidence report, implementation/closure commits, push, and exact-SHA CI

## Protected Boundaries

- no Backend or published API contract changes
- no frozen M1, Article source-record, or derived-asset changes
- no source-site access or private Zotero reads/writes
- no real or paid Provider calls
- no candidate, tag, Release, or attestation
- no committed runtime stores, databases, screenshots, traces, profiles,
  credentials, secrets, corpus files, or generated assets

## Deliverables

- bounded Frontend workflow helpers/components
- concise platform-neutral `AGENTS.md`
- Dashboard, Article, Tutor, and Graph context integration as evidence requires
- focused tests and expanded Product E2E
- `docs/P3_014_INTEGRATED_LEARNING_WORKFLOW_REPORT.md`
- governance updates and two-commit exact-SHA CI closure

## Acceptance

- three to five real local Articles validate the complete desktop/mobile flow
- Dashboard -> Article -> two learning tools -> Article return works
- Article identity, safe return path, and resume state remain intact
- no overflow, overlap, inaccessible primary control, or uncontrolled state
- content formats and external-image safety remain intact
- three isolated Product E2E runs and all repository quality gates pass
- protected boundaries remain unchanged
- generated agent-specific repository instructions are absent
- final branch is clean and synchronized

## Stop Rule

Stop without widening scope if completion requires a protected contract,
external side effect, private-data action, release action, or unresolved
critical regression.
