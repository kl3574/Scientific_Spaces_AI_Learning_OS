# P3-010 Incremental Derived Asset Refresh

## Status

LOCAL PASS / IMPLEMENTATION CI PENDING

## Objective

Refresh the persisted RAG, Knowledge Graph, and structured Reference Store
snapshots from the exact current 1,314-Article Store through one deterministic,
offline, recoverable bundle operation.

## Authoritative Alignment

`alignment.md`

## Entry State

- branch: `main`
- entry commit:
  `30b46208a171ce2416e636a1270b9668290b8c37`
- Article count: 1,314
- expected Article Store SHA-256:
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`
- existing RAG, Graph, and Reference snapshots: 1,311-Article corpus
- Reference API state: `reference_store_stale`
- M1.4: PASS / CLOSED

## Authorized Actions

- local Article Store read: GRANTED
- ignored local derived-data staging, backup, install, and rollback: GRANTED
- local code/docs/tests, commit, push, and CI inspection: GRANTED
- source network or browser acquisition: NOT GRANTED
- private Zotero read/write: NOT GRANTED
- real/paid Provider: NOT GRANTED
- candidate, tag, Release, or attestation: NOT GRANTED

## Required Flow

```text
exact 1,314-Article Store
  -> preflight identity and integrity
  -> recoverable 1,311-snapshot backup
  -> isolated deterministic RAG build
  -> isolated deterministic Graph build
  -> isolated deterministic Reference build
  -> bundle integrity and compatibility gates
  -> atomic bundle install
  -> post-install API and feature verification
  -> deterministic idempotent rerun
```

## Boundaries

- Do not modify existing Articles or the Article Store.
- Do not modify frozen M1 crawler/parser/converter/storage modules.
- Do not change legacy, `/v1.1`, or `/v1.2` contracts.
- Do not fetch source pages, update Zotero, call real Providers, or enable
  paid/default network behavior.
- Do not commit local stores, indexes, backups, databases, credentials,
  secrets, or generated runtime artifacts.
- Do not assign a candidate or create/move a tag or Release.

## Deliverables

- additive refresh orchestrator and CLI
- deterministic unit/integration/rollback/idempotency tests
- exact local refresh and feature evidence
- P3-010 implementation report and governance updates
- implementation and closure commits with successful exact main CI runs

## Acceptance

- exact source identity and immutable source evidence
- backup, staging, all-or-nothing installation, and rollback evidence
- all three derived assets match the 1,314 corpus fingerprint
- new Articles 11814, 11818, and 11823 are represented
- stale Reference API state is resolved
- full regression, secret, artifact, and frozen-path gates pass
- final branch is clean and synchronized

## Stop Rule

Stop without widening scope if source identity, frozen contracts, offline
operation, complete-bundle consistency, rollback, secret/artifact policy, or
prohibited release/provider/private-data boundaries cannot be preserved.
