# P3-009 Full Corpus Acquisition and Zotero PDF Sync

## Status

PASS / CLOSED

## Objective

Measure a bounded safe source-page browser-print envelope, then use the fastest
stable tier to complete resumable browser-printed PDF synchronization into the
private Zotero root collection `苏剑林博客`.

## Authoritative Alignment

`alignment.md`

## Entry State

- Formal version: `v1.1.0`
- v1.2 candidate: Not assigned
- P3-007: `CONDITIONAL / RISK ACCEPTED / CLOSED`
- Canonical source inventory evidence: 1,326 URLs
- Valid local Article Store evidence: 1,311 Articles
- Classified non-importable evidence: 15 URLs
- Existing Zotero browser-printed PDF pilot: 3 Articles

All counts must be revalidated from current runtime state before they are used
as completion evidence.

## Authorizations

- Bounded public Scientific Spaces source access: CONSUMED / CLOSED
- Private Zotero Desktop read/write in `苏剑林博客`: CONSUMED / CLOSED
- Browser-printed PDF generation: CONSUMED / CLOSED
- Local repository changes and local commit: CONSUMED BY THE P3-009 CLOSURE COMMIT
- Real/paid Provider calls: NOT GRANTED
- Push, candidate, tag, Release, or attestation: NOT GRANTED

## Source-Access Envelope

- Known canonical Article URLs only
- No archive-ID scanning or search-page scraping
- Probe maximum: 25 URLs
- Browser worker maximum: 4
- Global navigation-start interval minimum: 4 seconds
- Baseline: 1 worker / 8 seconds
- Immediate stop and backoff on HTTP 403/429, content-quality failure, retry
  clustering, or material resource degradation
- Full run uses only the fastest previously stable tier

This task-specific bounded probe does not change the frozen M1 crawler or its
general full-corpus policy.

## Data and Attachment Contract

- Existing `Article.content` is immutable.
- Source-page print is A4 and waits for MathJax.
- Each Zotero parent is provenance-matched by Article ID and source URL.
- Each target parent ends with exactly one PDF child and no live HTML child.
- Browser/PDF work may be concurrent; Zotero writes remain sequential.
- Every result is checkpointed and resumable.

## Allowed Repository Changes

- `alignment.md`
- this canonical task and `docs/tasks/CURRENT_TASK.md`
- P3-009 reports and governance status files
- non-frozen bulk orchestration under `scripts/`
- focused tests under `backend/tests/`
- minimal non-frozen Zotero/export support needed by the orchestration

## Prohibited Changes and Actions

- `backend/app/crawler/` or any frozen M1 source contract
- Article Store schema or stored `Article.content`
- legacy or `/v1.1` API contracts
- real/paid Provider calls
- unrelated private Zotero reads, writes, merges, deletes, or exports
- unbounded/high-frequency access, access-control bypass, or distributed crawl
- tracked PDF, corpus, database, checkpoint, trace, profile, cache, or secret
- push, candidate assignment, tag, GitHub Release, or attestation

## Required Evidence

1. Runtime and dependency preflight.
2. Throughput probe report with every tested tier.
3. Selected stable tier and stop/backoff evidence.
4. Full source inventory reconciliation.
5. Per-Article PDF and Zotero checkpoint.
6. Final PDF/HTML attachment cardinality.
7. Idempotent zero-fetch/zero-write rerun.
8. Full functional and repository audits.

## Git Plan

If acceptance passes, create one local commit:

```text
ops: complete P3-009 full corpus Zotero PDF sync
```

Do not push it.

## Completion Evidence

- The connected desktop Chrome WebBridge passed nine distinct known Articles
  at `1 worker / 8 seconds`, `1 / 6`, and `1 / 4`, with HTTP 200, zero retries,
  and valid A4/body/Chinese/MathJax evidence.
- The bridge can safely bind exactly one current tab, so the measured provider
  concurrency upper bound is one. The selected interval lower bound is four
  seconds.
- The canonical inventory remains 1,326 URLs: 1,311 valid Articles, 15
  classified non-importable URLs, and zero unclassified URLs.
- The private Zotero root collection now contains 1,311 provenance-matched
  parents, 1,311 valid PDF children, zero HTML children, zero duplicates, and
  no unresolved failure.
- The idempotent rerun made zero source navigations and zero Zotero writes.
- Backend, Frontend, Reader/Search, RAG, Tutor, Graph, secret, artifact, and
  changed-path gates passed.

Aggregate evidence is recorded in
`docs/P3_009_THROUGHPUT_PROBE_REPORT.md` and
`docs/P3_009_FULL_CORPUS_RUN_REPORT.md`. Runtime checkpoints and private
Zotero evidence remain ignored.

## Follow-up Boundary

Three newer RSS URLs observed outside the frozen 1,326-URL inventory remain a
separate M1.x source-delta candidate. P3-009 did not change the frozen source
contract or claim continuous live-feed coverage.

No v1.2 candidate, push, tag, Release, or attestation was authorized.
