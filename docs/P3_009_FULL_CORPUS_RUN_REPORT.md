# P3-009 Full Corpus Run Report

## Current Status

Full browser-print acquisition: **PASS**

Private Zotero full-corpus synchronization: **PASS**

Idempotent rerun: **PASS**

Overall status: **PASS / CLOSED**

Date: 2026-07-28

## Corpus Contract

The P3-009 canonical inventory reconciles as:

- canonical seed URLs: 1,326;
- valid stored Articles: 1,311;
- classified non-importable URLs: 15;
- unclassified seed URLs: 0; and
- Article Store SHA-256:
  `3b91f22db548373a6c91bb11a5188fb3e388ab9e19c4429e8e8fac918609a505`.

The frozen Article Store schema and every existing `Article.content` value
were left unchanged.

A prior low-frequency RSS check observed three newer URLs outside this frozen
1,326-URL inventory. They are recorded as a source-delta/M1.x revision
candidate. P3-009 does not silently add them through a new source contract and
does not claim that the frozen inventory is a continuously refreshed live-feed
snapshot.

## Production Strategy

```text
validated Article Store
  -> WebBridge desktop Chrome at 1 worker / 4 seconds
  -> source-page A4 browser print after MathJax wait
  -> local PDF and distributed body validation
  -> append-only resume checkpoint
  -> sequential Zotero parent/PDF write
  -> batched PDF SHA-256 readback
  -> one-PDF/zero-HTML collection audit
```

The implementation used no real or paid AI provider and did not export or
inspect unrelated private Zotero content.

## Resumable Full Run

The collection began with the three previously approved parent/PDF pairs.
Transient browser failures occurred during the long-running acquisition, and
the run was resumed from its ignored checkpoint. Failed or incomplete PDFs
were never written as successful attachments.

The final completion cycle recorded:

| Metric | Result |
| --- | ---: |
| Total target Articles | 1,311 |
| Already valid at cycle start | 704 |
| Pending at cycle start | 607 |
| Rendered and created | 607 |
| Navigation attempts | 608 |
| Zotero writes | 607 |
| Failed | 0 |
| Deferred | 0 |
| Duplicate parents/attachments | 0 |
| Final parents | 1,311 |
| Final PDF children | 1,311 |
| Final HTML children | 0 |

Across P3-009, 1,308 new browser-printed PDF attachments were added after the
three-item pilot. Every terminal item passed local PDF validation and Zotero
readback before its staging PDF was removed.

## Idempotency

The required second full sync completed with:

- preexisting parent/PDF pairs: 1,311;
- pending Articles: 0;
- browser renders: 0;
- network navigations: 0;
- Zotero writes: 0;
- duplicate count: 0;
- failed/deferred count: 0;
- final parents/PDF children: 1,311 / 1,311; and
- final HTML children: 0.

This proves that the completed sync does not refetch or rewrite already valid
Articles.

A final independent read-only collection audit after all test runs again found
1,311 preexisting valid parent/PDF pairs, zero pending Articles, zero
duplicates, zero failures, zero navigations, and zero writes.

## PDF Quality

For every newly written PDF, the automated gate required:

- file exists and is non-empty;
- `%PDF-` header and trailing `%%EOF`;
- bounded file size;
- at least one readable A4 page;
- Article title and Chinese text;
- at least 60% of distributed authoritative body samples; and
- MathJax evidence whenever the stored Article contains formula syntax.

The validator excludes image Markdown and known citation/share boilerplate
from body sampling and supports genuine short or image-centric Articles
without accepting navigation, comments, or unrelated text as proof.

## Functional Evidence

- Backend: `587 passed, 3 skipped`.
- Frontend Article tests: `3/3 PASS`.
- Frontend Reference tests: `3/3 PASS`.
- Frontend Tutor tests: `13/13 PASS`.
- Frontend Graph tests: `8/8 PASS`.
- Frontend Next.js 15.5.21 build: `PASS`, static generation `8/8`.
- Reader/Search smoke: `PASS`, 1,311 Articles; title and content queries both
  returned the expected Article; detail metadata included `date`, `category`,
  `references`, and `images`.
- Full-corpus RAG smoke: `PASS`, 12 retrieval queries, 100% indexed-Article
  coverage, 0 retrieval errors, source schema rate 100%, and expected Article
  hit@k 90.9%.
- Baseline RAG/Tutor fixture evaluation: `PASS`, 9 cases.
- Full-corpus Tutor evaluation with the fake provider: `PASS`, 42 cases, no
  hard-metric or evaluation-validity failures.
- Full-corpus Graph benchmark: `PASS`, 5 repetitions, 0 errors, bounded
  responses, and 70.713 ms maximum warm latency.

No real Provider or paid request was used.

## Artifact and Privacy Result

- Zotero synchronization evidence and checkpoints remain ignored runtime data.
- Staging PDF count after completion: 0.
- No PDF, HTML dump, image, browser profile, trace, screenshot, database,
  checkpoint, corpus, Zotero key, credential, or secret is included in the
  tracked deliverables.
- Private Zotero evidence in repository documents is aggregate-only.
- The task browser tab remains open; no user browser tab was closed.

## Remaining Risks

- Source availability remains environment-dependent and can fluctuate.
- The WebBridge current-tab contract limits safe concurrency to one.
- External DOM, MathJax, or print behavior can change.
- The frozen Article inventory is not a live-feed refresh mechanism; the three
  observed newer RSS URLs require a separately authorized M1.x source-delta
  task before they can join the canonical Article Store.
- Local Zotero and browser availability remain runtime dependencies.

## Closure

P3-009 is **PASS / CLOSED** for the canonical 1,311-Article corpus.

The formal version remains `v1.1.0`; no v1.2 candidate, tag, Release,
attestation, or push is authorized by this task. The next staged governance
task is P3-008 Candidate Decision, which remains
`ALIGNMENT REQUIRED / NOT GRANTED`.
