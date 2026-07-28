# P3-009 Full Corpus Acquisition and Zotero PDF Sync Alignment

Canonical task:
`docs/tasks/P3-009_FULL_CORPUS_ACQUISITION_ZOTERO_PDF_SYNC.md`

Status: **PASS / CLOSED**

NETWORK / PRIVATE ZOTERO WRITE AUTHORIZATION: **CONSUMED / CLOSED**

LOCAL FILE MODIFICATION / LOCAL COMMIT AUTHORIZATION: **CONSUMED BY THE P3-009 CLOSURE COMMIT**

PUSH / CANDIDATE / TAG / RELEASE AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-007 is `CONDITIONAL / RISK ACCEPTED / CLOSED`.
- The accepted private Zotero representation is one browser-printed PDF child
  per Scientific Spaces parent; HTML is not an accepted final attachment.
- Three approved Articles already passed PDF import and idempotency checks.
- Existing runtime evidence contains 1,326 canonical URLs, 1,311 valid stored
  Articles, 15 classified non-importable candidates, and no unclassified URL.
- Existing offline PDFs cover 1,311 Articles, but they are local Markdown
  renders rather than source-page browser prints.
- P3-008 Candidate Decision is deferred. No v1.2 candidate is assigned.

## 2. Requirements

1. Revalidate the current corpus, source delta, disk capacity, Chromium,
   Zotero Desktop, collection identity, and checkpoint state.
2. Measure a bounded, compliant browser-print operating envelope rather than
   stress-testing the source.
3. Start from one worker and an eight-second global navigation interval.
4. Test at most four browser workers, no interval below four seconds, and no
   more than 25 known Article URLs across the probe.
5. Change one pressure dimension at a time and stop at the first HTTP 403,
   HTTP 429, source-quality failure, retry spike, or material latency/resource
   degradation.
6. Select the previous stable tier and retain adaptive backoff for the full
   run.
7. Fetch only source pages needed for incremental Article ingestion or
   browser-printed PDFs. Do not repeat the completed body crawl without a
   source-delta reason.
8. Generate A4 PDFs after MathJax settles, validate them, and import them into
   the private Zotero root collection `Su Jianlin Blog` (`苏剑林博客`).
9. Keep Zotero writes idempotent and sequential even when browser rendering is
   parallel.
10. Do not retain HTML children as the final representation.
11. Skip per-Article human review, but retain automated content, PDF,
    attachment-cardinality, duplicate, and readback gates.
12. Validate Reader, Search, RAG citations, Graph, Tutor, and Zotero behavior
    against the completed local corpus using fake/offline providers.
13. Do not call a real or paid AI provider.
14. Do not commit runtime corpus data, PDFs, Zotero data, browser artifacts,
    credentials, or secrets.

## 3. Purpose

Complete the real private-data production path as quickly as the measured safe
source-access envelope permits, while preserving source-site policy, PDF
fidelity, Zotero integrity, resumability, and honest failure accounting.

## 4. Planned Execution

1. Persist this alignment and the canonical P3-009 task.
2. Audit current runtime corpus, source delta, browser/PDF dependencies,
   Zotero readiness, and existing three-item state.
3. Add only non-frozen operational orchestration and focused tests needed for
   a resumable throughput probe and bulk PDF/Zotero sync.
4. Run a small browser-print probe with a global start-rate limiter, bounded
   concurrency, quality validation, and immediate stop conditions.
5. Record every tested tier and choose the fastest stable tier.
6. Discover and ingest only new canonical source Articles under the existing
   frozen source pipeline constraints.
7. Resume through all valid stored Articles, printing source-page PDFs,
   validating them, writing Zotero sequentially, and checkpointing every
   terminal result.
8. Re-run the bulk command to prove zero duplicate parents/attachments and
   zero unnecessary browser fetches.
9. Run focused and full Backend tests, Frontend tests/build, full-corpus
   feature smoke, secret audit, and artifact audit.
10. Write throughput and full-run reports, update project governance, and
    create the authorized local commit.

## 5. Selection Rationale

A global navigation limiter controls actual source pressure while multiple
browser workers can overlap rendering and MathJax wait time. This improves
throughput more safely than reducing delay alone. Sequential Zotero writes
retain deterministic parent/attachment cardinality and simple recovery.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Keep one worker and eight seconds permanently | Safe but unnecessarily slow if bounded evidence supports more |
| Run an unbounded stress or capacity test | Prohibited because it could burden the source |
| Bounded adaptive probe plus global rate limiting | Selected |
| Use offline rendered PDFs instead of source-page prints | Rejected by the accepted Zotero policy |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-009_FULL_CORPUS_ACQUISITION_ZOTERO_PDF_SYNC.md`
- updated `docs/tasks/CURRENT_TASK.md`
- `docs/P3_009_THROUGHPUT_PROBE_REPORT.md`
- `docs/P3_009_FULL_CORPUS_RUN_REPORT.md`
- necessary non-frozen operational scripts and focused tests
- ignored private runtime checkpoint, temporary PDFs, and Zotero attachments
- updated `docs/00_PROJECT_STATE.md`, `docs/V1_2_ROADMAP.md`, and `README.md`
- local commit:
  `ops: complete P3-009 full corpus Zotero PDF sync`

## 8. Acceptance Criteria

- Probe evidence records tested workers, global interval, URL count, HTTP
  status, latency, retries, content/PDF quality, and the selected stable tier.
- The probe never exceeds four workers, a four-second global interval, or 25
  known Article URLs and does not scan archive IDs or search pages.
- Source inventory reconciles to 100%; `unclassified=0`.
- Every accessible, safely importable Article has valid stored content.
- Every target Zotero parent has exactly one valid browser-printed PDF child
  and zero live HTML children.
- Every PDF exists during staging, is non-empty, starts with `%PDF-`, has at
  least one readable A4 page, contains title/Chinese/body evidence, and
  preserves MathJax evidence when formulas are expected.
- A repeated sync produces zero duplicate parents, zero duplicate PDF
  attachments, and zero unnecessary source fetches.
- All terminal failures are explicitly classified and resumable; no failure is
  silently dropped.
- Backend, Frontend, full-corpus feature smoke, secret, artifact, and
  changed-path checks pass.
- No frozen M1 module, Article schema/content, legacy API, candidate, tag,
  Release, real Provider, private export, or tracked runtime artifact changes.
- Final status and counts are based on live evidence, not inferred from the
  three-item pilot.

## Stop Conditions

- The work requires a frozen M1 implementation or contract change.
- Robots/site policy forbids the requested access.
- HTTP 403/429, source-quality failures, or retry clusters persist after
  immediate backoff.
- Zotero collection identity or parent provenance is ambiguous.
- Disk, browser, or Zotero runtime becomes unsafe or unstable.
- A secret/private artifact would enter Git.
- A real Provider, paid request, push, candidate, tag, or Release becomes
  necessary.

## Completion Evidence

- The user-connected desktop Chrome session passed all nine bounded probe
  Articles at 8-, 6-, and 4-second intervals with zero retries.
- WebBridge's reliable current-tab identity limits safe concurrency to one;
  `1 worker / 4 seconds` is the selected stable tier.
- The canonical inventory reconciled to 1,311 valid Articles, 15 classified
  non-importable URLs, and zero unclassified URLs.
- Zotero final audit: 1,311 parents, 1,311 PDF children, zero HTML children,
  zero duplicates, and zero unresolved failures.
- Idempotent rerun: zero browser renders, zero network navigations, and zero
  Zotero writes.
- Backend, Frontend, full-corpus feature, secret, artifact, and changed-path
  gates passed.
- Three newer RSS URLs outside the frozen inventory remain an explicit M1.x
  source-delta candidate; no frozen M1 code or Article content changed.

No push, candidate assignment, tag, Release, attestation, real Provider, or
paid request occurred.
