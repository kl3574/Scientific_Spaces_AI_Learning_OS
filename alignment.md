# P3-006.3 Zotero Printed PDF Attachment Correction Alignment

Canonical task:
`docs/tasks/P3-006_3_ZOTERO_FULL_TEXT_SNAPSHOT_SYNC.md`

Status: **PASS / CLOSED**

PDF IMPORT AUTHORIZATION: **CONSUMED / CLOSED**

HTML ATTACHMENT DELETION AUTHORIZATION:
**CONSUMED / CLOSED AFTER ALL THREE PDF ATTACHMENTS PASSED READBACK**

PUSH AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-006.2 remains `PASS / CLOSED`.
- The private root collection `苏剑林博客` exists uniquely.
- The previous P3-006.3 run created three approved Web Page parents and three
  imported HTML snapshot children.
- The user corrected the required attachment format: each Article must use a
  browser-printed PDF rather than an HTML snapshot.
- The P3-006.3 implementation and report are uncommitted and must be revised.
- M1, P3-006, and P3-006.1 status and acceptance remain unchanged.

## 2. Requirements

1. Process exactly these three approved Articles:
   - `68441d48f88c5de6`, `https://spaces.ac.cn/archives/8512`
   - `573354a74b26d9a3`, `https://spaces.ac.cn/archives/138`
   - `d3b2db76b2e5a2dd`, `https://spaces.ac.cn/archives/1850`
2. Reuse the existing metadata-complete Zotero Web Page parents.
3. Generate one A4 PDF per Article using Playwright Chromium page printing.
4. Wait for the article body and MathJax v2/v3 before printing.
5. Generate PDFs only in a temporary directory.
6. Validate every PDF before any HTML deletion:
   - file exists;
   - file size is greater than zero;
   - header is a valid PDF signature;
   - the PDF is readable;
   - rendered article and formula evidence are present.
7. Attach exactly one `application/pdf` child to each approved parent.
8. Read back and validate all three Zotero PDF attachments.
9. Only after all three PDF attachments pass, delete the three corresponding
   HTML snapshot children.
10. Verify the final state is exactly one parent and one PDF child per approved
    Article, with zero HTML children.
11. Repeated synchronization must perform zero browser fetches and create no
    duplicate parent or PDF attachment.
12. Delete all temporary PDF files after verification.

## 3. Purpose

Make the three approved Scientific Spaces Articles available in Zotero as
browser-printed, formula-rendered PDF documents rather than HTML snapshots or
link-only records.

## 4. Planned Execution

1. Persist this revised alignment and mark P3-006.3 as rework in progress.
2. Recheck `REWORK.md`, `.audit`, roadmap, Git drift, and current Zotero state.
3. Inspect the existing frozen PDF exporter and local Zotero Desktop Connector
   contract for safely attaching a PDF to an existing parent.
4. Revise only the downstream Zotero adapter, CLI, tests, and P3-006.3 docs.
5. Add regression tests for PDF attachment creation, readback, idempotency,
   partial failure, and deletion ordering.
6. Generate all three PDFs in one temporary directory and validate them before
   Zotero mutation.
7. Attach and read back all three PDFs while preserving the existing parents
   and HTML safety copies.
8. After 3/3 PDF readback passes, delete only the three attributable HTML
   children and verify the final child cardinality.
9. Repeat synchronization and require a no-op result for all three.
10. Run focused and full Backend tests, source/store integrity checks, changed-
    path, secret, artifact, and Git audits.
11. Update aggregate evidence and create one local commit without push.

## 5. Selection Rationale

Reusing the existing parents preserves metadata and provenance. Generating
PDFs through the established Playwright print path preserves rendered MathJax.
The PDF-first, delete-HTML-last sequence prevents loss of the only local
full-text copy if PDF generation or attachment import fails.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Attach validated PDF, then delete HTML | Selected: matches the corrected format and protects full text during migration |
| Keep both HTML and PDF | Rejected: does not satisfy the requested final format |
| Delete HTML before PDF import | Rejected: creates an avoidable data-loss window |
| Delete and recreate parent items | Rejected: unnecessary destructive metadata churn |

## 7. Deliverables

- Revised `alignment.md`
- Revised `docs/tasks/P3-006_3_ZOTERO_FULL_TEXT_SNAPSHOT_SYNC.md`
- Updated `backend/app/zotero/sync.py`
- Updated `backend/tests/test_zotero_sync.py`
- Updated `scripts/zotero/sync_scientific_spaces.py`
- Revised `docs/P3_006_3_ZOTERO_FULL_TEXT_SNAPSHOT_REPORT.md`
- Updated current-task, project-state, and v1.2-roadmap pointers
- Three private Zotero Web Page parents, each with exactly one PDF child and no
  HTML child
- One local commit:
  `fix: replace Zotero HTML snapshots with PDF attachments`
- No push

## 8. Acceptance Criteria

- Exactly three approved parents remain; no parent is deleted or duplicated.
- Each approved parent has exactly one `application/pdf` child.
- Each approved parent has zero `text/html` children after migration.
- All three PDFs are nonempty, valid, readable, formula-rendered, and available
  from Zotero local storage.
- HTML deletion occurs only after all three PDFs pass Zotero readback.
- A repeated run creates zero parents and zero attachments and performs zero
  browser fetches.
- All temporary PDFs are removed at the end of the run.
- No unrelated Zotero item or collection is read broadly, changed, deleted, or
  exported.
- Browser access remains limited to the exact three approved Article URLs.
- M1, Article Store, Reference Store, and the formal 64-case packet remain
  unchanged.
- Focused and full Backend tests, secret audit, tracked-artifact audit,
  changed-path check, and `git diff --check` pass.
- No PDF, HTML, full text, image, profile, trace, cache, Zotero key, private
  metadata, or secret is tracked.
- Push, P3-007, candidate, tag, Release, and attestation are not performed.

## Stop Conditions

- No supported Zotero Desktop path can attach a generated PDF to an existing
  parent without recreating it.
- Any PDF fails generation, format, formula, or Zotero readback validation.
- All three PDFs cannot be verified before HTML deletion.
- Any unrelated private Zotero item would need to be changed.
- Source/store drift, unknown worktree drift, REWORK/FAIL audit, test failure,
  secret/artifact finding, or scope expansion occurs.

## Completion Evidence

- Existing approved parents reused: 3/3
- Browser-printed A4 PDFs imported and read back: 3/3
- PDF sizes: 971,286; 550,679; and 713,184 bytes
- PDF pages: 11; 2; and 3
- Title, Chinese, distributed Article content, and MathJax checks: 3/3
- HTML replacement ordering: first deletion occurred only after 3/3 PDF
  readback
- Final live child state: PDF 3, HTML 0
- Repeated run: zero browser fetches, zero duplicate writes, zero additional
  trash operations
- Focused tests: 21 passed
- Full Backend suite: 561 passed, 3 skipped
- Article Store, Reference Store, and formal review packet: unchanged
- Temporary PDFs, debugger listener, preference backups, and diagnostic
  profiles: removed or restored
- Local commit only; push remains unauthorized
