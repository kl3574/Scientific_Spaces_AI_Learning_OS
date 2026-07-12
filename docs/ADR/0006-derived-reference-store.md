# ADR 0006: Derived Reference Store

Status: Accepted

Date: 2026-07-12

## Context

The validated v1.1 corpus contains 1,311 Articles with frozen `id`, `title`, `url`, `content`, and `metadata` contracts. Structured `metadata.references` arrays are empty, while links and citation text remain in Article Markdown. M1 is frozen, the Article store is authoritative, and ordinary v1.2 work cannot modify the parser, converter, validation, storage schema, content, or metadata.

Reference extraction must therefore be reproducible, provenance-complete, offline, and independently disposable. Human-reviewed Zotero decisions are not disposable and must survive derived rebuilds and cleanup.

## Decision Drivers

- Preserve Article/M1 and released API compatibility.
- Stream and audit a full local corpus without loading or rewriting one large object.
- Keep the P3-003 pilot simple and external-service-free.
- Support deterministic rows, complete provenance, corruption detection, atomic install, rollback, stale detection, and no-op reuse.
- Keep user-reviewed decisions protected from derived-data cleanup.

## Options Considered

### 1. Backfill `metadata.references`

Pros:

- Reference data travels with each Article.

Cons:

- Mutates the frozen source of truth and M1 contract.
- Requires Article-store migration, backup, rollback, and broad compatibility audit.
- Mixes inferred/derived data with acquired source data.

Rejected for v1.2. Any future backfill requires separate M1.x governance.

### 2. One JSON Document

Pros:

- Matches the simplest existing local stores.
- Easy to inspect for a small pilot.

Cons:

- Requires full-document parse/write.
- Increases partial-write and large-corpus memory costs.
- Makes deterministic row auditing and streaming less direct.

Rejected for the derived full-corpus payload, though bounded indexes/manifests remain JSON.

### 3. SQLite

Pros:

- Transactions, indexes, constraints, and bounded queries.

Cons:

- Introduces a database and migration surface before pilot evidence.
- Duplicates existing JSONL-derived artifact patterns without a demonstrated need.
- Risks conflating rebuildable extraction with authoritative user decisions.

Deferred. Reconsider after measured JSONL query/build evidence, concurrent-write requirements, or scale growth.

### 4. JSONL Payload plus JSON Indexes

Pros:

- Streamable, deterministic, inspectable, simple Python implementation.
- Supports per-row validation, complete hashes/counts, staged directory replacement, and rebuilds.
- Aligns with current ignored local derived-artifact policy.

Cons:

- Indexes must be validated against payload rows.
- No multi-writer transactions or ad hoc relational queries.
- Bounded API service needs an in-memory/on-disk index adapter.

Selected.

## Decision

Use an independent Tier 2 Reference Store under:

```text
.local_data/scientific_spaces/references/full_corpus/
```

Payload records and evidence use deterministic JSONL. Manifest, Article index, and identifier index use bounded JSON. Zotero candidates use JSONL and may be absent when matching is not configured.

The store is keyed by schema versions, Article corpus fingerprint, extraction/normalization/matcher versions, secret-free configuration fingerprint, content checksums, and deterministic build fingerprint.

Builds occur in a private sibling staging directory. A validated existing store is moved to one rollback location only during install. The staged directory is installed by rename and revalidated; failure restores the previous valid directory. Partial/unvalidated output is never current.

An unchanged, valid source/configuration returns a no-op. API/startup never triggers an implicit rebuild and never silently serves stale/corrupt data.

Store user-reviewed confirmations, rejections, corrections, and annotations separately at:

```text
.local_data/scientific_spaces/references/reviewed/decisions.json
```

That repository is Tier 1, atomically written, backed up, cleanup-protected, and never deleted by a derived rebuild.

## Invariants

- Article Store is read-only; its before/after fingerprint is unchanged.
- Every candidate has a terminal classification; silent drops are zero.
- Every deterministic merge retains complete evidence and correct `source_count`.
- Records, evidence, indexes, and candidates have no orphan IDs.
- No file contains full Article content, local absolute paths, credential userinfo, secret, or private full-library export.
- Only manifest status `complete` with passing integrity may be installed/served.

## Consequences

Positive:

- Reference work can evolve independently and be deleted/rebuilt safely.
- Frozen Article/API contracts remain stable.
- Corpus/rule changes produce explicit stale state.
- Human decisions remain durable across rebuilds.

Costs:

- The system owns JSONL/index integrity and recovery code.
- A large store may require a future indexed storage adapter.
- Reapplying human decisions after canonical identity changes needs explicit reconciliation.

## Migration and Rollback

- Compatible rule changes build a new staged store; no in-place row mutation.
- Schema changes use an offline staged converter plus full validation or rebuild from Articles.
- Rollback reinstalls the last validated directory or deletes and rebuilds Tier 2 output.
- Tier 1 decision migration requires backup, forward/reverse conversion, count/fingerprint reconciliation, and stale-decision reporting.
- SQLite migration is deferred until measured evidence justifies it; any migration preserves the same repository interface and keeps JSONL rollback export.

## Acceptance

- P3-003 fixtures and 50-100 Article pilot meet the exact normalization, provenance, no-network, no-mutation, no-silent-drop, idempotency, and rollback gates.
- P3-006 full-corpus work is separately authorized and audits every Article/candidate.
- Operations inventory classifies the derived store Tier 2 and reviewed decisions Tier 1 before product integration.
