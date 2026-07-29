# Current Task

## Task

P3-010 Incremental Derived Asset Refresh

## Canonical Specification

`docs/tasks/P3-010_INCREMENTAL_DERIVED_ASSET_REFRESH.md`

## Status

LOCAL PASS / IMPLEMENTATION CI PENDING

## Authorization

- Exact local Article Store read: GRANTED
- Ignored local derived-data staging, backup, install, and rollback: GRANTED
- Local changes, tests, commit, push, and CI inspection: GRANTED
- Source network/browser access: NOT GRANTED
- Private Zotero read/write: NOT GRANTED
- Real/paid Provider calls: NOT GRANTED
- Candidate / tag / Release / attestation: NOT GRANTED

## Required Exit

- RAG, Graph, and Reference stores match the 1,314-Article corpus;
- new Articles 11814, 11818, and 11823 are represented;
- stale Reference API state is resolved;
- rollback and idempotency are proven;
- runtime/private artifacts remain untracked;
- implementation and closure commits pass main CI; and
- final branch/worktree are synchronized and clean.
