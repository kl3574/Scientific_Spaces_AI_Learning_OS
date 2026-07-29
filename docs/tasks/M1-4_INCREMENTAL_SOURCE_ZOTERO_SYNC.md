# M1.4 Incremental Source and Zotero PDF Sync

## Status

LOCAL PASS / AWAITING MAIN CI

## Objective

Synchronize the completed P3-009 commit to GitHub, then add and validate a
bounded incremental command that imports newly published Scientific Spaces
RSS Articles into the existing Article Store and private Zotero browser-print
PDF collection.

## Authoritative Alignment

`alignment.md`

## Entry State

- Formal version: `v1.1.0`
- v1.2 candidate: Not assigned
- P3-009: `PASS / CLOSED` locally
- P3-009 local commit:
  `048a0f9d1e9b0162e1d020a7c6a98ed4e961e27a`
- Frozen corpus: 1,311 valid Articles
- Known source delta at prior observation: at least three RSS URLs
- Zotero policy: one browser-printed PDF child and zero HTML children

## Authorized Actions

- Bounded official RSS and missing-Article source access: CONSUMED / CLOSED
- Private Zotero read/write in `苏剑林博客`: CONSUMED / CLOSED
- Local file modification, tests, commit, push, and CI inspection: GRANTED THROUGH MAIN CI CLOSURE
- Real/paid AI Provider calls: NOT GRANTED
- Candidate, tag, GitHub Release, or attestation: NOT GRANTED

## Required Flow

```text
official RSS
  -> canonical URL delta
  -> authorized desktop browser HTML acquisition
  -> existing parser/converter
  -> additive Article Store write
  -> browser-printed A4 PDF
  -> sequential Zotero parent/PDF sync
  -> readback and one-PDF/zero-HTML audit
  -> idempotent rerun
```

## Boundaries

- Do not modify existing stored Articles or their content.
- Do not scan archive IDs, archive pages, or search pages.
- Do not modify frozen M1 crawler/parser/converter/storage implementation.
- Do not change Article schema, legacy API, or `/v1.1` contracts.
- Do not retain or commit HTML, PDFs, browser state, checkpoints, Zotero data,
  corpus data, database files, credentials, or secrets.
- Do not call a real/paid AI Provider.

## Deliverables

- additive incremental orchestration and CLI
- deterministic unit/integration tests and isolated live tests
- live delta/import/idempotency evidence
- M1.4 implementation report and governance updates
- implementation commit:
  `feat: add incremental blog Zotero PDF sync`
- successful main CI after push

## Acceptance

- P3-009 push and CI pass.
- RSS delta is bounded and deterministic.
- New Articles pass content, metadata, formula, and provenance gates.
- Zotero final state is one valid PDF and zero HTML per imported parent.
- Immediate rerun performs zero fetches and zero writes.
- Full local test/build, feature, secret, artifact, and changed-path gates pass.
- Final branch is clean and synchronized.

## Stop Rule

Stop without widening scope if any frozen contract, existing Article content,
source policy, private-data boundary, secret/artifact rule, or prohibited
release action would need to change.
