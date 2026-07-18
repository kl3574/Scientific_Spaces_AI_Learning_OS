# P3-006 Structured Reference Full-Corpus Build and Zotero Matching

## Status

ALIGNMENT REQUIRED

IMPLEMENTATION AUTHORIZATION: NOT GRANTED

FULL-CORPUS AUTHORIZATION: NOT GRANTED

PRIVATE ZOTERO AUTHORIZATION: NOT GRANTED

NETWORK AUTHORIZATION: NOT GRANTED

## Task Identity

P3-006 Structured Reference Full-Corpus Build and Zotero Matching

## Authoritative Baseline

- Formal version: `v1.1.0`
- Candidate version: Not assigned
- Previous task: P3-005 CI Security and Release Provenance, PASS / CLOSED
- P3-005 local closure commit: `ff19c520ac9650a36c5073665864aa4086160565`
- P3-005 main CI: [`29637475061`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29637475061), PASS
- Pilot baseline: P3-003 Structured Reference Extraction Pilot, PASS / CLOSED
- Applicable ADR: `docs/ADR/0006-derived-reference-store.md`
- Applicable governance: root `AGENTS.md`, `docs/tasks/CURRENT_TASK.md`, this canonical task, and a separately confirmed execution alignment

The expected local corpus contains 1,311 Articles. Its exact store path, manifest, Article count, content fingerprint, and read-only identity must be revalidated and recorded in the future execution alignment before any Article-store access or processing occurs.

## Background

P3-003 proved deterministic structured-reference extraction, normalization, deduplication, provenance, and derived-store behavior on fixtures and a bounded 75-Article pilot. It did not authorize complete-corpus processing or access to a private Zotero library.

P3-006 is the planned scale-up from that bounded pilot to the complete existing local Article corpus. It must preserve the frozen Article source data, build only derived reference data, provide complete input/output accounting, and support deterministic recovery. Zotero matching is a separate read-only boundary and remains optional even after full-corpus processing is approved.

This document stages the task only. It grants no implementation, Article-store access, full-corpus execution, network request, or Zotero access.

## Goals

- Revalidate the exact 1,311-Article input identity and process every eligible Article exactly once.
- Reuse the P3-003 extractor, normalizer, deduplicator, and derived-store contracts without changing Article or M1 data.
- Produce complete extraction, classification, normalization, duplicate, and provenance accounting.
- Preserve deterministic reference IDs and duplicate-group behavior across clean reruns and resume flows.
- Install a complete derived Reference Store atomically after validation.
- Detect stale, partial, corrupt, or mismatched input/output state before installation or use.
- Prove interruption recovery, rollback, idempotent rerun, and checkpoint/resume behavior.
- Bound runtime, memory, disk, logging, and temporary artifact use.
- Define optional read-only Zotero matching modes with conservative ambiguity handling and human review.

## Non-Goals

- No modification of `Article.content`, Article metadata, or `metadata.references`.
- No M1 crawler, browser access, parser, converter, storage, validation, or sync change.
- No source-site access or remote corpus refresh.
- No RAG, Graph, embedding, FAISS, Tutor, Learning, or search redesign.
- No Zotero write, import, mutation, merge, attachment download, or automatic ambiguous match confirmation.
- No authentication, multi-user architecture, Graph storage migration, or remote image archive.
- No candidate assignment, tag, Release, release asset, or attestation publication.

## Planned In Scope

- Read-only loading of the separately approved complete local Article store.
- Exact corpus manifest and fingerprint verification.
- Full-corpus use of the already validated P3-003 extraction pipeline.
- Derived Reference Store staging, validation, atomic installation, manifesting, and rollback.
- Checkpoint/resume and interrupted-run recovery with deterministic accounting.
- Stale/corruption detection and idempotent rerun evidence.
- Bounded human-review sampling for extraction and matching quality.
- Optional, separately authorized read-only Zotero matching against local metadata.

## Out of Scope

- Any operation listed under Non-Goals.
- Any path, command, dataset, provider, network endpoint, or private library not explicitly approved by a future execution alignment.
- Automatic promotion of candidate matches to authoritative links without deterministic identity evidence or human confirmation.

## Allowed Changes

No P3-006 implementation path is currently authorized.

A future execution alignment must define an exact allowlist before modification. Candidate areas may include P3-003-owned reference modules, focused tests and fixtures, offline reference scripts, ignored derived-store output, and named P3-006 reports/governance documents. Candidate areas are planning context, not current authorization.

## Prohibited Actions

- Read or process the Article store before a confirmed execution alignment grants that access.
- Run a full-corpus, partial-corpus, pilot, migration, matching, checkpoint, or recovery command.
- Access the source website or any other network service.
- Read, export, match, or modify a private Zotero library.
- Modify Article source content, metadata, M1 modules, legacy APIs, or `/v1.1` APIs.
- Create runtime output, derived stores, checkpoints, reports, or test caches for P3-006.
- Commit, push, tag, release, or publish P3-006 evidence before explicit authorization.
- Read credentials, secrets, private user data, Provider data, or paid services.

## Planned Inputs

- The exact existing local Article store, only after read authorization and fingerprint capture.
- P3-003 extractor, normalizer, deduplicator, store, fixtures, and pilot evidence.
- P3-002 architecture, data model, threat model, evaluation, acceptance, and execution documents.
- ADR 0006 and the future confirmed P3-006 execution alignment.
- Optional private Zotero metadata only under a separate explicit authorization.

## Planned Data Contracts

### Article Source Contract

The Article store is read-only. Every input record must retain its original ID, URL, title, content, and metadata. P3-006 cannot rewrite, enrich, reorder, normalize, or repair source Article data.

### Derived Reference Store

The output is a separately versioned derived store. It must contain deterministic reference identities, normalized identifiers, source Article and section provenance, extraction/classification status, duplicate relationships, schema/version metadata, and an input-manifest binding.

### Run Manifest

The run manifest must bind configuration, code commit, input fingerprint, Article accounting, output fingerprint, checkpoint state, tool versions, timestamps, completion status, validation results, and install/rollback state without embedding Article content or private Zotero data.

### Zotero Match Evidence

Any future match record must remain derived and read-only. It must identify match mode, normalized identity evidence, confidence/reason, ambiguity state, source reference IDs, and human-review state without copying private notes, attachments, or full text.

## Planned Deliverables

- Exact corpus identity and preflight report.
- Complete derived Reference Store and bounded manifest under an ignored approved output root.
- Full-corpus accounting, provenance, determinism, duplicate, idempotency, recovery, and resource evidence.
- Focused regression and corruption/recovery tests.
- Optional read-only Zotero match report only if separately authorized.
- P3-006 implementation report and status-appropriate local commit.

## Acceptance Criteria

### PASS

- Exact input identity and expected count are proven before processing.
- Input accounting equals processed plus explicitly classified terminal outcomes with no unexplained Article.
- Article source mutation count is `0`.
- Network request count is `0` for the full-corpus build.
- Reference IDs, normalized identities, duplicate groups, manifests, and clean reruns are deterministic.
- Every installed reference has complete Article and section provenance.
- Staging validation, atomic install, stale/corruption detection, rollback, interruption recovery, and idempotent rerun pass.
- Runtime, memory, disk, checkpoint, and log budgets remain within the confirmed limits.
- Ambiguous Zotero matches are never automatically confirmed.
- Artifact, secret, private-data, compatibility, tests, and build gates pass.

### CONDITIONAL

The complete offline derived-store build and all safety gates pass, but optional read-only Zotero matching remains unexecuted or produces a bounded documented non-critical limitation. The limitation must not affect Article immutability, complete accounting, deterministic IDs, provenance, recovery, or store integrity.

### BLOCKED

- Exact corpus identity or complete input accounting cannot be proven.
- Any Article, M1, legacy API, or `/v1.1` contract changes.
- Provenance is incomplete, IDs or duplicate groups are nondeterministic, or reruns diverge.
- Atomic install, corruption detection, rollback, interruption recovery, or idempotency fails.
- A network request occurs during the no-network build.
- Private Zotero data is accessed without explicit authorization, or any Zotero mutation occurs.
- A secret, private/runtime artifact, source content export, or local absolute path becomes tracked or exposed.
- Required work exceeds the confirmed execution allowlist or resource budgets.

## Verification Commands

No P3-006 command is currently authorized. The future execution alignment must provide exact commands for:

- corpus identity and fingerprint verification;
- focused extractor/store/recovery tests;
- no-network full-corpus build with checkpoint/resume;
- complete accounting and provenance validation;
- deterministic clean rerun and idempotent resume comparison;
- stale/corruption, atomic-install, rollback, and interrupted-run recovery;
- optional read-only Zotero matching, only if separately authorized;
- full Backend regression, Frontend build, artifact/secret audit, and Git checks.

## Artifact and Secret Policy

All runtime outputs must remain under a separately approved ignored local root. Never commit or publish Article/corpus exports, reference stores, checkpoints, manifests containing local paths or content, Zotero metadata/full text/notes/attachments, databases, PDFs, HTML/images, Graph/RAG/FAISS data, provider output, secrets, credentials, `.env` files, caches, traces, profiles, archives, or backups.

Reports and commits may contain only bounded aggregate metrics, irreversible fingerprints, safe schema/config identifiers, status evidence, and redacted failure classifications.

## Git Plan

- Implementation commit: NOT AUTHORIZED
- Push: NOT AUTHORIZED
- CI: NOT AUTHORIZED
- Candidate: prohibited
- Tag: prohibited
- Release: prohibited

The future confirmed execution alignment must use a local-commit-only plan unless the user separately authorizes push and CI.

## Stop Conditions

- The P3-006 execution alignment is absent, incomplete, or unconfirmed.
- Exact corpus identity, Article count, fingerprint, or read-only path cannot be established.
- Worktree drift, REWORK/FAIL audit, test/build failure, or artifact/secret finding appears.
- A required path or command falls outside the confirmed allowlist.
- Work requires network, source-site access, Provider credentials, private Zotero access, or paid requests without explicit authorization.
- Article/M1/frozen contract modification, Zotero mutation, candidate, tag, Release, or attestation is required.
- Resource budgets, recovery semantics, or a critical architecture decision remain unresolved.

## Completion Evidence

- Canonical task staged: YES
- Execution alignment: NOT YET CONFIRMED
- Implementation: NOT STARTED / NOT AUTHORIZED
- Full-corpus processing: NOT PERFORMED
- Private Zotero access: NOT PERFORMED

## Next Required Decision

Confirm or revise the complete P3-006 execution alignment before any implementation, Article-store access, full-corpus processing, testing, file modification, Git commit, network access, or Zotero operation.
