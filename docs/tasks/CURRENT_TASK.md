# Current Task

## Task

M1.4 Incremental Source and Zotero PDF Sync

## Canonical Specification

`docs/tasks/M1-4_INCREMENTAL_SOURCE_ZOTERO_SYNC.md`

## Status

PASS / CLOSED

## Authorization

- Official RSS and bounded missing-Article source access: CONSUMED / CLOSED
- Private Zotero Desktop read/write in `苏剑林博客`: CONSUMED / CLOSED
- Local changes, tests, commit, push, and CI inspection: CONSUMED / CLOSED
- Real/paid Provider calls: NOT GRANTED
- Candidate / tag / Release / attestation: NOT GRANTED

## Required Exit

- P3-009 commit pushed and main CI passed;
- incremental update command implemented and tested;
- current RSS delta imported through Article/PDF/Zotero quality gates;
- idempotent rerun produces zero fetches and zero writes;
- runtime/private artifacts remain untracked;
- implementation commit pushed and main CI passed; and
- branch/worktree synchronized and clean.

## Next Task

`P3-010 Incremental Derived Asset Refresh` is
`ALIGNMENT REQUIRED / NOT GRANTED`.
