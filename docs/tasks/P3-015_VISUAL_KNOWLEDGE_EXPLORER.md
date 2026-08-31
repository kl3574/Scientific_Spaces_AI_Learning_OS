# P3-015 Visual Knowledge Explorer

## Status

LOCAL PASS / IMPLEMENTATION CI PENDING

## Objective

Turn the existing bounded Graph data into an interactive, accessible visual
knowledge explorer without changing Backend interfaces or derived Graph data.

## Authoritative Alignment

`alignment.md`

## Entry State

- branch: `main`
- entry commit: `36eafb5915122a9254c0c8e07c2c87c75042d55b`
- cached `origin/main`: exact match
- worktree: clean
- P3-014: PASS / CLOSED
- candidate version: not assigned

## In Scope

- exact-pinned `@xyflow/react` Frontend dependency
- deterministic bounded subgraph layout and presentation module
- Map/List segmented view, legend, viewport controls, and node selection
- preservation of Article context and same-section return navigation
- keyboard, focus, reduced-motion, responsive, loading, empty, and error states
- focused Frontend and isolated Product E2E coverage
- read-only real local Graph and Article browser validation
- evidence report, implementation/closure commits, push, and exact-SHA CI

## Protected Boundaries

- no Backend or published interface changes
- no frozen M1, Article source-record, or derived Graph/RAG/Reference changes
- no source-site access or private Zotero reads/writes
- no real or paid Provider calls
- no candidate, tag, Release, or attestation
- no committed runtime stores, databases, screenshots, traces, profiles,
  credentials, secrets, corpus files, or generated assets

## Deliverables

- visual Graph module and deterministic layout helper
- bounded Graph route integration and accessible fallback
- focused tests and expanded Product E2E
- `docs/P3_015_VISUAL_KNOWLEDGE_EXPLORER_REPORT.md`
- governance updates and two-commit exact-SHA CI closure

## Acceptance

- Map/List, selection, zoom, pan, and fit-view work within existing bounds
- Article context and exact return path remain intact during free exploration
- typed nodes, directed relationships, selection, and legend are unambiguous
- desktop/mobile geometry and keyboard controls pass real-browser checks
- three isolated Product E2E runs and all repository quality gates pass
- protected implementation and data boundaries remain unchanged
- final branch is clean and synchronized

## Stop Rule

Stop without widening scope if completion requires a protected interface,
external data side effect, private-data action, release action, unresolved
dependency finding, or critical regression.
