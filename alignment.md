# P3-010 Incremental Derived Asset Refresh Alignment

Canonical task:
`docs/tasks/P3-010_INCREMENTAL_DERIVED_ASSET_REFRESH.md`

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

LOCAL DERIVED DATA READ / WRITE AUTHORIZATION: **GRANTED**

LOCAL FILE MODIFICATION / TEST / COMMIT / PUSH / CI AUTHORIZATION:
**GRANTED**

SOURCE NETWORK / PRIVATE ZOTERO / REAL PROVIDER AUTHORIZATION:
**NOT GRANTED**

CANDIDATE / TAG / RELEASE AUTHORIZATION: **NOT GRANTED**

## 1. Background

- M1.4 is PASS / CLOSED at 1,314 Articles.
- Reader/Search and the private Zotero PDF collection already use the current
  Article Store.
- RAG, Knowledge Graph, and structured Reference Store remain immutable
  1,311-Article snapshots.
- The Reference API correctly reports `reference_store_stale` rather than
  serving mismatched provenance.
- M1 is frozen. P3-010 must not modify source discovery, browser acquisition,
  parsing, conversion, Article storage, PDF export, or Zotero synchronization.
- The expected entry Article Store SHA-256 is
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`;
  it must be revalidated before use.

## 2. Requirements

1. Use the exact current 1,314-Article Store as the sole source input.
2. Refresh the persisted RAG index, Knowledge Graph, and structured Reference
   Store with matching corpus fingerprints.
3. Preserve recoverable copies of the existing 1,311-Article snapshots.
4. Build in staging and install only after every integrity and compatibility
   gate passes.
5. Use deterministic offline providers and perform zero external requests.
6. Prove Articles `/archives/11814`, `/archives/11818`, and `/archives/11823`
   are represented by the refreshed derived assets.
7. Preserve Reader/Search, Tutor, legacy API, `/v1.1`, and `/v1.2` contracts.
8. Add dry-run, failure rollback, atomic install, determinism, and idempotency
   tests.
9. Run full Backend, Frontend, feature, secret, artifact, and changed-path
   validation.
10. Create implementation and closure commits, push both, and verify exact
    main CI runs.
11. Do not access the source site, write Zotero, call a real/paid Provider, or
    assign a candidate/tag/Release.

## 3. Purpose

Bring all persisted derived capabilities into fingerprint-consistent alignment
with the 1,314-Article source of truth so the three newly imported Articles can
participate in retrieval, graph, structured-reference, and Tutor workflows.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Revalidate Git state, Article count/SHA/fingerprint, and current derived
   manifests.
3. Audit existing RAG, Graph, Reference, operations, backup, and rollback
   interfaces without modifying frozen contracts.
4. Implement an additive read-only-by-default orchestration module and CLI.
5. Add deterministic fixture tests for preflight, staging, rollback, atomic
   installation, idempotency, and failure handling.
6. Run a dry-run against the local 1,314-Article source.
7. Create recoverable snapshot backups and build all three derived stores in
   isolated staging directories.
8. Validate counts, fingerprints, integrity, compatibility, and explicit
   representation of the three new Articles.
9. Atomically install the validated bundle; roll back the complete bundle on
   any installation or post-install failure.
10. Rerun to prove deterministic no-op/idempotent behavior.
11. Run API, Reader/Search, RAG, Tutor, Graph, Reference, full test/build,
    secret, artifact, and frozen-path gates.
12. Update governance and evidence, commit, push, verify main CI, close the
    task with a docs-only commit, and verify the second CI.

## 5. Selection Rationale

Reference deduplication, graph relationships, and vector indexing contain
global corpus relationships. A deterministic full rebuild in staging is safer
than appending three records into independently persisted structures. Atomic
bundle installation prevents mixed 1,311/1,314 runtime state and provides a
clear rollback boundary.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Offline full rebuild in staging, then atomic bundle install | Selected: strongest consistency and rollback evidence |
| Direct incremental append into each store | Rejected: global deduplication, graph, and index consistency risk |
| Leave existing snapshots stale | Rejected: new Articles remain unavailable to derived capabilities |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-010_INCREMENTAL_DERIVED_ASSET_REFRESH.md`
- updated `docs/tasks/CURRENT_TASK.md`
- additive derived-refresh orchestration module and CLI
- focused tests for refresh, rollback, determinism, and idempotency
- `docs/P3_010_INCREMENTAL_DERIVED_ASSET_REFRESH_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation commit and exact main CI evidence
- docs-only closure commit and exact main CI evidence

## 8. Acceptance Criteria

- Input is exactly 1,314 Articles and its SHA-256/fingerprint is recorded.
- The original 1,311-Article RAG, Graph, and Reference snapshots have
  recoverable ignored backups and are not edited in place.
- Refreshed RAG, Graph, and Reference manifests match the current Article
  corpus fingerprint.
- Articles 11814, 11818, and 11823 are present in relevant derived indexes;
  RAG can retrieve their content and Graph/Reference APIs can account for them
  without stale-state errors.
- Reference API no longer returns `reference_store_stale`.
- Reader/Search, Tutor, legacy API, `/v1.1`, and `/v1.2` compatibility checks
  pass.
- A repeated refresh is deterministic and performs no unnecessary install.
- Injected build/install/post-install failures leave or restore the complete
  prior bundle.
- Full Backend tests and Frontend focused tests/build pass.
- Secret and artifact audits report no credible secret or tracked
  runtime/private artifact.
- Frozen M1 modules, Article records, published API contracts, source site,
  Zotero, real Providers, candidate, tag, and Release remain untouched.
- Implementation and closure commits are pushed; both required main CI runs
  pass; final `main` is clean and synchronized.

## Stop Conditions

- The Article Store count or SHA differs from the approved entry state.
- The worktree develops unknown changes or conflicts.
- A frozen contract or existing Article content would need modification.
- A source network request, private Zotero access, or real/paid Provider is
  required.
- Any staging, integrity, compatibility, rollback, test, artifact, or secret
  gate fails without an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.
