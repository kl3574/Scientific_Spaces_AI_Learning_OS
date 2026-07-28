# P3-006.3 Zotero Printed PDF Attachment Sync

## Status

PASS / CLOSED

IMPLEMENTATION AUTHORIZATION: CONSUMED / CLOSED

PRIVATE ZOTERO AUTHORIZATION:
CONSUMED / CLOSED AFTER THREE PDF ATTACHMENTS PASSED READBACK AND THE THREE
REPLACED HTML CHILDREN WERE MOVED TO ZOTERO TRASH

NETWORK AUTHORIZATION:
CONSUMED / CLOSED AFTER BOUNDED PLAYWRIGHT ACCESS TO THE THREE APPROVED ARTICLE
URLS

PUSH AUTHORIZATION: NOT GRANTED

## Task Identity

P3-006.3 Zotero Printed PDF Attachment Sync

## Approved Articles

| Article ID | URL |
| --- | --- |
| `68441d48f88c5de6` | `https://spaces.ac.cn/archives/8512` |
| `573354a74b26d9a3` | `https://spaces.ac.cn/archives/138` |
| `d3b2db76b2e5a2dd` | `https://spaces.ac.cn/archives/1850` |

No other Article or URL was authorized.

## Goals

1. Reuse the three metadata-complete Web Page parents already present in the
   private root collection `苏剑林博客`.
2. Generate one browser-printed A4 PDF for each approved Article.
3. Validate file format, readable text, Article content, Chinese text, and
   MathJax evidence before import.
4. Attach exactly one PDF to each approved parent.
5. Remove the replaced HTML children only after all three PDFs pass Zotero
   readback.
6. Prove duplicate-free, zero-fetch idempotency.

## Non-Goals

- No M1 crawler, browser provider, parser, converter, storage, validation, PDF
  exporter, or sync modification.
- No new parent creation for the three existing Articles.
- No bulk Zotero import or unrelated private-library inventory.
- No HTML snapshot generation or retention in the final live child set.
- No permanent trash purge, parent deletion, merge, or replacement.
- No source-site access outside the exact three approved URLs.
- No Provider, paid service, or private Zotero export.
- No P3-006/P3-006.1 status change.
- No push, P3-007, candidate, tag, Release, or attestation.

## Allowed Tracked Changes

```text
alignment.md
backend/app/zotero/sync.py
backend/tests/test_zotero_sync.py
scripts/zotero/sync_scientific_spaces.py
docs/tasks/P3-006_3_ZOTERO_FULL_TEXT_SNAPSHOT_SYNC.md
docs/tasks/CURRENT_TASK.md
docs/00_PROJECT_STATE.md
docs/V1_2_ROADMAP.md
docs/P3_006_3_ZOTERO_FULL_TEXT_SNAPSHOT_REPORT.md
```

## PDF and Zotero Contract

The downstream adapter preserves metadata-only synchronization and adds an
explicit printed-PDF mode:

1. resolve the unique target collection and exact Article parent;
2. validate parent URL and `Scientific Spaces Article ID` provenance;
3. generate the PDF under a temporary directory through Playwright Chromium;
4. require A4, a valid PDF envelope, readable pages, title, Chinese text,
   bounded authoritative content samples, and MathJax evidence;
5. attach the PDF to the exact existing parent through a short-lived localhost
   Zotero Desktop bridge;
6. read back exactly one `application/pdf` child and validate its local bytes;
7. complete the same checks for all three parents before the first HTML
   deletion;
8. move only the attributable `text/html` child to Zotero Trash;
9. verify exactly one live PDF and zero live HTML children per parent.

The adapter fails closed on duplicate parents, duplicate PDF or HTML children,
parent provenance mismatch, invalid or missing PDF bytes, partial batch
readback, or a non-local debugger endpoint.

## Browser Boundary

- Playwright Chromium only
- Maximum three approved URLs
- Sequential, bounded access
- Bounded retry, timeout, and a 10-second print-settle window
- MathJax v2/v3 wait
- No pagination, discovery, archive traversal, or additional crawl
- PDFs exist only in a temporary directory before Zotero import
- Browser profiles, traces, screenshots, HTML dumps, and cache are not tracked

## Runtime Data Boundary

PDF attachment files remain private Zotero runtime data. The tracked report
contains only public Article identities, aggregate validation metrics, and
irreversible source/store fingerprints. It contains no Zotero item key,
attachment path, PDF bytes, HTML, or Article body.

## Verification

- Focused PDF synchronization and deletion-order regression tests
- Full Backend tests
- Exact Article identity and frozen source/store fingerprints
- Runtime parent/PDF/file readback
- Three-PDF-before-first-HTML-delete gate
- Repeated three-Article zero-fetch no-op verification
- Zotero normal-mode API and Connector readiness after debugger shutdown
- `git diff --check`
- changed-path allowlist
- tracked runtime/private-artifact audit
- secret audit
- final clean index/worktree after the local commit

## Git Plan

Exactly one local commit:

```text
fix: replace Zotero HTML snapshots with PDF attachments
```

Push is not authorized.

## Completion Evidence

- Existing approved parents reused: 3/3
- Browser-printed A4 PDFs attached and read back: 3/3
- PDF pages: 11, 2, and 3
- Readable extracted text: 12,326, 1,107, and 5,489 characters
- Title, Chinese, and MathJax evidence: 3/3
- Live child state after replacement: PDF 3, HTML 0
- Replaced HTML children moved to Zotero Trash: 3, after 3/3 PDF readback
- Repeated synchronization: zero browser fetches and zero duplicate writes
- Focused tests: 21 passed
- Full Backend tests: 561 passed, 3 skipped
- Source/store fingerprints: unchanged
- Temporary debugger endpoint and configuration: removed/restored
- Push: not performed

## Completion States

PASS requires all three PDFs, content/file readback, deletion ordering,
idempotent rerun, tests, audits, report, local commit, and no forbidden
artifact.

CONDITIONAL is not allowed for a missing or invalid PDF.

BLOCKED applies to partial PDF import, HTML deletion before 3/3 PDF readback,
ambiguous private-library state, source/store drift, data leakage, or failed
tests/audits.
