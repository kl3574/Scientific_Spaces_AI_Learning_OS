# P3-014 Integrated Learning Workflow

## Status

PASS / CLOSED

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

## Closure Evidence

- real-corpus Chromium: 5 Articles, desktop/mobile workflow PASS
- Backend: 600 passed, 4 skipped
- focused Frontend: 41 passed
- production build: PASS
- isolated Product E2E: 10/10 repair stress runs, 20 checks per run, 0 external requests
- workflow, suppression, dependency, secret, artifact, and SBOM gates: PASS
- initial implementation commit: `9e52b1730b32ba81766a5cf674605bb788aff629`
- initial main CI: run `33349166132` exposed an E2E write-sequencing race
- repair commit: `82eab2386c703b0768806900402771e7911f8f58`
- repair exact-SHA main CI: PASS,
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33349379685`
- task closure: PASS / CLOSED; the docs-only closure commit must pass its own
  exact-SHA main CI before final synchronized completion is reported
