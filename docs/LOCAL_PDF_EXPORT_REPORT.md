# Local PDF Export Report

## Current Status

- P2-005 Optional Local PDF Export Workflow: PASS
- execution mode: offline local export
- source access during export: disabled
- full-corpus coverage: 1,311 / 1,311
- idempotent rerun: PASS

## Design Decision

Mode A, offline local export, is the default and completed implementation. It reads the frozen local Article store, renders Markdown through the locally installed React Markdown and KaTeX stack, prints with headless Chromium, and validates with Poppler. It never fetches the source site or remote images.

Mode B, source print-parity, remains an unimplemented optional revision candidate. The CLI validates its safety envelope: explicit source-access approval, one worker, at most 10 Articles, at least eight seconds delay, and a separate output directory. The P2-005 batch intentionally refuses to execute this online path. It was not run and is not required for this PASS.

PDF is derived output. It does not replace `Article.content`, the local Markdown library, RAG chunks, Graph data, or Tutor sources.

## Input Corpus

- Article store: `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json`
- Article count: 1,311
- unique URL count: 1,311
- missing content count: 0
- duplicate ID/URL count: 0
- corpus fingerprint: `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d`

Each input record was validated for `id`, `title`, `url`, `content`, and `metadata`. The fingerprint is computed from the complete corpus before Article selection.

## Renderer

- template version: `local-pdf-v5`
- renderer version: `chromium-149.0.7827.55`
- page format: A4
- formula strategy: local `remark-math` plus KaTeX SSR with local inlined font data
- legacy formula compatibility: bounded normalization of legacy MathJax syntax without modifying Article storage
- formula trust policy: only legacy `\htmlStyle` is trusted; TeX link/image commands and `file:` URIs are removed from the rendering copy
- image strategy: local images require an explicit allowlist; remote images become embedded SVG placeholders, and displayed URLs omit credentials, query strings, and fragments
- validation: `pdfinfo` and `pdftotext`
- network policy: Chromium aborts HTTP(S)/WS(S) requests; successful records require zero blocked requests
- body fidelity: one of three body-derived text probes must be present in extracted PDF text
- resume integrity: source hash, template/renderer versions, file size, PDF header, and PDF SHA-256 must match
- concurrency safety: one output-root process lock plus a single main-thread atomic manifest writer

The renderer uses a persistent Node process and persistent Chromium page per worker. Node responses have a bounded timeout and the child is restarted after a timeout. The main thread alone writes atomic JSON/CSV manifest checkpoints. Successful full runs remove PDF files no longer referenced by the manifest.

## Pilot Audit

The deterministic 20-Article pilot used:

`a96fb8c5192fc3ba`, `f703785db4192f04`, `54222327243755e4`, `03dfe77de35ec4ec`, `c10628495483e2c5`, `314d4d677cdf8b6c`, `e4539b3ee91ddf70`, `1cdcdc963fbaf6bc`, `8658cbea7ea7fa3d`, `4368e79f44edce53`, `9f65c292c4538f9e`, `9adcdd2e80f9f4a6`, `42ca3db9ef053ea5`, `09260cccb8f0a9fe`, `b6e4b373221c12f1`, `c433711bdf659ac6`, `e794b2ba77dad9f2`, `b9cf3aa4d9aebf4d`, `480d4ef5cc5be09e`, `acaac952bd9e2de1`.

Coverage included formula-dense, long, short, image, code, table, legacy, recent, and all 11 corpus categories.

- structural result: PASS, 20 / 20
- formula Articles: 12
- formula failures: 0
- remote image placeholders: 126
- external network requests: 0
- final recovery run: 17 unchanged, 3 regenerated, 0 failed in 1.77 seconds
- visual audit: PASS

The first `v4` pilot identified three false negatives because all three body probes were required even when Poppler changed text across formula or page boundaries. Validation was corrected to require at least one body-derived probe, then resume regenerated only those three Articles. After the KaTeX trust boundary produced the final `v5` template, all 20 first pages were inspected again as a local contact sheet. Additional formula, code, table, and long-Article pages were inspected. Titles, Chinese text, formulas, tables, code blocks, links, placeholders, margins, page breaks, and page numbers were legible. Visual images were deleted after inspection and were not committed.

## Full Export

Final `local-pdf-v5` full export:

- input / selected: 1,311 / 1,311
- exported or regenerated: 1,311
- failed: 0
- validation pass / fail: 1,311 / 0
- total PDF size: 830,490,049 bytes
- PDF size min / mean / median / p95 / max: 334,563 / 633,478.30 / 625,803 / 865,111 / 1,186,006 bytes
- total pages: 7,152
- page min / mean / median / p95 / max: 2 / 5.455 / 5 / 11 / 22
- formula Articles: 809
- image references: 4,729
- remote image placeholders: 4,728
- local images embedded: 0
- broken image references: 1 empty source reference, safely replaced by a placeholder
- worker count: 4
- external network requests: 0
- elapsed time: 126.03 seconds
- throughput: 10.40 files/second

The single broken image reference is an empty source in Article `576d8da7b5d91453`; it is explicitly recorded and rendered as an offline placeholder. It is not a missing PDF, network request, or validation failure.

## Resume and Idempotency

Resume requires a valid PDF header, minimum size, PASS export and validation status, unchanged source-content hash, unchanged template/renderer versions, identical file size, and an identical PDF SHA-256 digest. The most recent non-empty generation summary is retained separately from the current-run summary, so an idempotent rerun does not erase generation evidence.

Final unchanged rerun:

- exported: 0
- regenerated: 0
- unchanged: 1,311
- failed: 0
- validation pass: 1,311
- stale: 0
- elapsed time: 0.77 seconds

Template changes from formula/image compatibility work incremented the template version and correctly forced stale PDF regeneration before the final run.

## PDF Validation

- PDF header valid: 1,311 / 1,311
- page count at least one: 1,311 / 1,311
- title or Article ID in extracted text: 1,311 / 1,311
- extracted body text above threshold: 1,311 / 1,311
- body-derived text probe present: 1,311 / 1,311
- formula render failures: 0
- delimiter balance failures: 0
- empty PDFs: 0
- corrupt PDFs: 0
- browser/error-page markers: 0
- local runtime path disclosures: 0
- external network requests: 0

PDF text extraction is validation evidence only and is never used as Article input.

## Optional Product Integration

No Reader PDF status/download endpoint or frontend link was added. This optional integration was not required for P2-005 and would expand the filesystem-serving security surface. Operators use the configured local PDF directory documented in `README.md`.

## Artifact and Privacy

- PDF root: ignored `.local_data/scientific_spaces/corpus/pdf_library/`
- runtime manifest and reports: ignored
- rendered HTML and browser cache: ignored
- source Articles and Markdown: unchanged
- remote images: not downloaded
- source site access: none
- local paths in PDF/manifest records: none; manifest output paths are relative
- manifest schema: version 2, 1,311 unique IDs, 1,311 unique paths, 1,311 non-empty SHA-256 digests
- PDFs or runtime output tracked by Git: none

## Regression Evidence

- backend: `415 passed, 3 skipped`
- frontend: Next.js 15.5.20 production build PASS, static generation 8 / 8
- deterministic RAG/Tutor baseline: 9 cases, PASS
- full-corpus RAG evaluation: PASS; expected hit@10 90.9%; retrieval errors 0; unsupported fabrications 0
- bounded Graph/Tutor context smoke: PASS; 20 nodes, 19 edges, full graph not injected
- full-corpus Tutor evaluation: 42 cases, 0 hard failures, 0 validity failures, PASS

Normal CI does not execute the 1,311-Article browser batch. Browser-dependent integration remains explicit and local.

## Limitations

- PDF is derived output and can be rebuilt from the Article store.
- Remote images are placeholders; image completeness is not claimed.
- One source record contains an empty image reference and is explicitly counted.
- Rendering can vary after Chromium, KaTeX, or font-stack upgrades; version changes invalidate resume.
- Legacy MathJax syntax is normalized only in the rendering copy.
- Source print parity was not evaluated or claimed.
- Source-probe configuration is guarded, but the online provider is intentionally not implemented in P2-005.
- No PDF or runtime manifest is committed to Git.

## Recommendation

A: Ready for post-corpus product hardening
