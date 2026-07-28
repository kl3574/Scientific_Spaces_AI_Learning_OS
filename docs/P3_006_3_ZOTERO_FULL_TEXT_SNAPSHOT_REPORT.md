# P3-006.3 Zotero Printed PDF Attachment Sync Report

## Status

P3-006.3: **PASS / CLOSED**

The three approved Scientific Spaces Articles are now represented in the
private Zotero root collection `苏剑林博客` by their existing
metadata-complete Web Page parents and one browser-printed PDF child each.
There are no live HTML children under those parents.

## Scope

Only these public Article identities were processed:

| Article ID | URL |
| --- | --- |
| `68441d48f88c5de6` | `https://spaces.ac.cn/archives/8512` |
| `573354a74b26d9a3` | `https://spaces.ac.cn/archives/138` |
| `d3b2db76b2e5a2dd` | `https://spaces.ac.cn/archives/1850` |

No unrelated private Zotero item was changed, merged, deleted, or exported.
The existing parents were reused and not recreated.

## Design

The correction uses a PDF-first, delete-HTML-last transaction boundary:

1. resolve each exact parent by URL and Article ID provenance;
2. print the live page to A4 PDF with Playwright Chromium after the page and
   MathJax settle;
3. validate the temporary PDF with its envelope, `pdfinfo`, `pdftotext`, title,
   Chinese text, and distributed authoritative Article samples;
4. attach the PDF to the exact parent through a short-lived localhost Zotero
   Desktop bridge;
5. read back and validate exactly one PDF from each of all three parents;
6. only after 3/3 readback succeeds, move the three attributable HTML children
   to Zotero Trash;
7. verify the final live child cardinality and repeat the command as a no-op.

Temporary PDFs were created under an automatically removed temporary
directory. No PDF was copied into the repository.

## Live PDF Result

| Article ID | PDF bytes | Pages | A4 | Extracted text chars | Content samples | Title | Chinese | MathJax |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- | --- |
| `68441d48f88c5de6` | 971,286 | 11 | PASS | 12,326 | 2/3 | PASS | PASS | PASS |
| `573354a74b26d9a3` | 550,679 | 2 | PASS | 1,107 | 3/3 | PASS | PASS | PASS |
| `d3b2db76b2e5a2dd` | 713,184 | 3 | PASS | 5,489 | 2/3 | PASS | PASS | PASS |

The content gate requires at least 60% of three distributed normalized
samples and requires both the first and last samples. This tolerates
`pdftotext` formula ordering while still proving coverage across the Article.

Aggregate result:

- approved parents reused: 3/3
- browser-printed PDFs imported and read back: 3/3
- valid PDF envelope and nonzero local file: 3/3
- readable A4 pages: 3/3
- title, Chinese, and MathJax evidence: 3/3
- temporary PDF artifacts after each run: 0

## Slow-Page Correction

The first two migration attempts for `/archives/138` produced a sub-minimum
PDF and stopped before Zotero import. A bounded diagnostic confirmed HTTP 200,
one article body, approximately 1,100 printable text characters, and a valid
approximately 551 KB direct browser print. The cause was the downstream
migration script's three-second print-settle window, not missing source
content. The script now uses a bounded 10-second settle window; the retry
produced a valid 550,679-byte, two-page PDF.

No HTML child was deleted during either failed attempt.

## Replacement Ordering

The replacement sequence was observed as follows:

1. initial state: PDF 0, live HTML 3;
2. PDFs imported individually without HTML deletion;
3. joint preflight: PDF 3/3 valid, live HTML 3/3 present;
4. one guarded replacement operation: HTML children moved to Trash 3;
5. final state: PDF 3, live HTML 0.

The HTML children were moved to Zotero Trash, not permanently erased. This
meets the requested live-child deletion while keeping a recoverable failure
boundary.

## Idempotency

The same three-Article replacement command was repeated after final readback:

- result: 3/3 `existing`
- browser fetches: 0
- new parents: 0
- new PDFs: 0
- additional HTML trash operations: 0
- temporary PDF artifacts: 0

A final dry readback after normal Zotero restart confirmed one PDF and zero
live HTML children for every approved parent.

## Zotero Runtime Recovery

- Zotero Desktop version: 9.0.6
- temporary debugger listener: bound only to `127.0.0.1`
- debugger configuration: restored from the pre-migration backup
- debugger listener after migration: closed
- normal local API: HTTP 200
- normal Connector: HTTP 200
- temporary debugger backups and diagnostic profiles: removed

## Test Evidence

- Focused Zotero tests: 21 passed
- Full Backend suite: 561 passed, 3 skipped
- PDF readback and replacement ordering: PASS
- Zero-fetch idempotent rerun: PASS
- Zotero normal-mode recovery: PASS
- Secret audit: PASS, zero credible findings
- Changed-path allowlist: PASS
- Tracked runtime/private-artifact audit: PASS
- `git diff --check`: PASS

## Source Integrity

| Evidence | Result |
| --- | --- |
| Article Store SHA-256 | `3b91f22db548373a6c91bb11a5188fb3e388ab9e19c4429e8e8fac918609a505` |
| Reference Store build fingerprint | `70ab191621aa8819f3c195c116aec5b5ae05f44c0b90fb0d11e6cb4365d5d846` |
| Formal review-case SHA-256 | `9618349de7ba2f8f3f3f2f2595d7f4a43ab8b5d799abd5bd31201970e6ba7b73` |
| M1/source module changes | 0 |
| Article/Reference Store mutations | 0 |
| P3-006.1 packet mutations | 0 |

## Limitations

- The migration is intentionally bounded to the three authorized Articles.
- Zotero Desktop requires a short-lived localhost bridge when an attachment is
  added to an existing parent; the bridge is disabled after the operation.
- The pre-existing Article 6508 controlled item remains metadata-only because
  it is outside this task's approved three-Article scope.
- This task does not replace or complete the paused P3-006.1 natural-person
  review gate.

## Boundary Result

- M1 and frozen source contracts remain unchanged.
- P3-006 remains `CONDITIONAL / CLOSED`.
- P3-006.1 remains `HUMAN_REVIEW_INCOMPLETE / PAUSED`.
- No bulk import, Provider call, candidate assignment, tag, Release,
  attestation, or push occurred.
- Implementation, private Zotero, and bounded network authorizations are
  consumed and closed.
