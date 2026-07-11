# Scientific Spaces AI Learning OS v1.1.0

## Status

Draft - not yet released.

Release readiness: pending P2-007 re-audit. The P2-008 compatibility and migration revision passed its implementation checks, but the formal project version remains `v1.0.0` and no `v1.1.0` tag target is authorized until the fresh release-readiness audit passes.

## Highlights

`v1.1.0` is an operational-maturity and full-local-corpus candidate. P2-008 restores the frozen Article and Graph contracts, moves scalable list/query behavior to explicit `/v1.1` endpoints, and adds identity-preserving Learning JSON/SQLite migration. A fresh P2-007 audit is still required before release actions.

## Full Local Corpus

- Canonical seed inventory: 1,326 URLs.
- Valid imported Articles: 1,311.
- Classified non-importable candidates: 15.
- Remaining unclassified candidates: 0.
- Duplicate URLs, missing content, and invalid imported content: 0.
- Article content, metadata, and formula validation rates: 100% for the imported corpus.

"Full local corpus" means all safely importable Articles plus an explicit classification for every rejected candidate. It does not mean that all 1,326 URLs produced valid `Article.content`.

## Reader and Search

- Reader and keyword/title search run against the 1,311-Article local store.
- Article list responses retain `id`, `title`, `url`, `metadata`, and `content_preview`.
- Legacy `GET /articles` returns every match in original store order with exactly `items`, `total`, and `query`.
- The Reader uses `GET /v1.1/articles`; page size defaults to 20 and is capped at 100.
- Article detail keeps the frozen `id`, `title`, `url`, `content`, and `metadata` contract.
- The Reader renders Chinese Markdown and math and preserves basic local reading history.

## Grounded RAG

- Persisted local index: 1,311 Articles and 5,547 Markdown-structure chunks.
- Indexed Article coverage: 100%; empty chunks, duplicate chunk IDs, and missing source provenance: 0.
- Current 12-query deterministic evaluation: expected-Article hit@10 90.91%, no-source refusal 100%, source schema 100%, retrieval errors 0, unsupported fabrications 0.
- Corpus fingerprint: `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d`.

The release baseline uses deterministic fake embeddings. It does not certify real-provider semantic quality.

## Knowledge Graph

- 52,874 nodes: 1,311 Articles, 5,547 Sections, 39,032 Concepts, and 6,984 Formulas.
- 82,230 source-grounded edges.
- Article coverage: 100%; dangling edges, duplicate IDs, missing provenance, and invalid Article references: 0.
- API summary, pagination, filters, and subgraphs are bounded for full-corpus use under `/v1.1/graph/*`.
- Current benchmark: 1,347.9 ms cold summary load and 76.3 ms maximum warm query, within the local 5,000/1,000 ms guards.

The legacy full-document, node-search, build, and path-subgraph Graph contracts remain for M6 compatibility. Full-corpus callers should use bounded `/v1.1/graph/nodes` and `/v1.1/graph/subgraph` endpoints.

## AI Research Tutor

- Full-corpus source selection supports Explain, Derive, QA, Quiz, and Research modes.
- Current deterministic evaluation: 42 cases, 0 hard failures, and 0 evaluation-validity failures.
- Current live local frontend smoke: 17/17 checks, no external network requests, no unexpected console errors, and no local path disclosure.
- Unsupported or insufficiently grounded requests refuse instead of relying on model common knowledge.

Research remains local-corpus-only. The fake-provider evidence validates grounding, bounds, and refusal behavior, not final language or mathematical quality from a real model.

## Local Markdown and PDF Libraries

- Markdown: 1,311 files, generated without source fetching.
- PDF: 1,311 valid A4 files, 7,152 pages, 830,490,049 PDF bytes.
- Current PDF resume check: 1,311 unchanged, 0 regenerated, 0 failed, and 1,311 validation PASS.
- Formula render, empty PDF, corrupt PDF, and external network failure counts: 0.
- Remote image references are represented by local placeholders; one empty image reference is recorded as broken.

PDFs are optional derived output and are not Reader/RAG source data. Source-site print parity is not implemented.

## Backup, Restore and Health Checks

- Configured local health check: PASS with zero issues across source and derived assets.
- Fresh essential backup: 4 Tier 1 files, 14,978,927-byte archive, mode `0600`, PDF excluded.
- Independent backup verification: PASS with zero issues.
- Isolated restore: PASS; 1,311 Articles, 1,311 unique URLs, 0 missing content, and an identical Article-store SHA-256.
- Cleanup is dry-run by default and cannot delete the complete data root or Tier 1 assets.

The verification archive is temporary audit evidence, not a retained user backup. Users should create and retain their own verified backup outside the repository.

## CI, Deployment and Security Hardening

- CI triggers: pull request, `main` push, `v*` tag push, and manual dispatch.
- Every run covers backend pytest and frontend build.
- Tag and manual runs additionally cover Docker compose smoke.
- Latest pre-audit `main` CI for `f00d596a5ab3ef43a9ef57230ab51eee80fe0d81`: success.
- Deployment profiles cover local development and local production-like use.
- Tracked-file and finite-history scans found no real secret pattern or runtime/private/large artifact.
- Fake providers and local JSON persistence remain the safe defaults.

## Verification Evidence

Fresh release-readiness checks on 2026-07-11:

- Backend: 469 passed, 3 skipped.
- Frontend production build: PASS, 8 routes.
- Frontend Article API client tests: 3/3 PASS.
- Frontend Graph tests: 7/7 PASS.
- Fresh versioned Graph client tests: 8/8 PASS.
- Frontend Tutor tests: 13/13 PASS.
- Deterministic RAG/Tutor baseline: 9/9 PASS.
- Full-corpus RAG evaluation: PASS.
- Graph benchmark and 17-check Graph frontend smoke: PASS.
- Full-corpus Tutor evaluation and 17-check live Tutor frontend smoke: PASS.
- PDF manifest/idempotency: PASS.
- Configured health and essential backup/verify/isolated restore: PASS.
- Legacy Article full-corpus smoke: 1,311/1,311 with exact v1.0 response keys; `/v1.1/articles` returned 20 with total 1,311.
- Learning JSON/SQLite identity round trip, repeated execution, reverse export, and injected-failure atomicity: PASS.

These release-CI steps remain required after a fresh readiness gate passes.

## Upgrade Notes

1. Keep `Version` at `v1.0.0` until the `v1.1.0` tag and GitHub Release exist.
2. Preserve `.local_data/` before Git operations; `git clean -fdX` deletes ignored local corpus and derived assets.
3. Configure `SCIENTIFIC_SPACES_ARTICLE_STORE`, `SCIENTIFIC_SPACES_RAG_INDEX_DIR`, and `SCIENTIFIC_SPACES_GRAPH_FILE` for the completed local profile.
4. Existing v1.0 clients can continue using `GET /articles` and legacy Graph routes. New Reader/Graph clients should use the bounded `/v1.1` list/query endpoints.
5. JSON Learning persistence remains the default. Before opting into SQLite, run `scripts/persistence/migrate_learning_json_to_sqlite.py` with explicit source and target paths. Before switching back after SQLite writes, run `scripts/persistence/migrate_learning_sqlite_to_json.py`; a backend configuration change alone does not transfer data.
6. Derived Markdown, PDF, RAG, and Graph assets must be rebuilt or restored when their corpus fingerprint is stale.

## Data Locations

- Article source of truth: `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json`
- Candidate classifications: `.local_data/scientific_spaces/corpus/pilot/completion_classifications.json`
- Learning data: `.local_data/scientific_spaces/learning.json` or the opt-in SQLite file
- Markdown: `.local_data/scientific_spaces/corpus/local_library/`
- PDF: `.local_data/scientific_spaces/corpus/pdf_library/`
- RAG: `.local_data/scientific_spaces/rag/full_corpus/`
- Graph: `.local_data/scientific_spaces/graph/full_corpus/`
- Unified manifest: `.local_data/scientific_spaces/operations/local_data_manifest.json`

All paths above are ignored local runtime data and are not included in the GitHub repository or Release assets.

## Known Limitations

- Local-first, single-user only; no authentication or authorization.
- JSON stores are not production multi-user or concurrent-write storage.
- SQLite is a partial, opt-in Learning migration rather than a complete managed database.
- Real-provider cost, rate, latency, privacy, and answer quality are not certified.
- Tutor Research is not live or exhaustive web research.
- Structured `metadata.references` arrays are present but currently empty across the completed corpus; inline source links remain in Article content.
- Remote images are not archived for complete offline fidelity.
- Year-based legacy partition completion remains conditional.
- Source-site structure and access behavior can change.
- RAG and Graph artifacts become stale after Article corpus changes.
- The 75 MB JSON Graph is a local single-process baseline.
- Complete backup and isolated restore require substantial additional disk space.
- Application-level backup encryption and off-site redundancy are absent.
- Local Docker is unavailable in the audit environment; exact-tag Docker evidence is required from GitHub Actions.

## Privacy and Local Data

Article corpus data, reading history, Learning state, Tutor sessions, Zotero links, PDF output, indexes, Graph data, backups, restores, browser data, and provider credentials are local/private runtime data. They must not be committed. Backups are not uploaded automatically.

## Breaking Changes

No intentional breaking API change remains in the P2-008 candidate. The frozen v1.0 `GET /articles` behavior and legacy Graph query/build/subgraph response contracts are covered by compatibility regressions. Scalable behavior is additive under `/v1.1`.

SQLite is still optional and Learning-only. Migration/export must be invoked explicitly; switching the backend setting does not merge data automatically.

The targeted legacy parser revision adds body selection and page-chrome removal without changing the frozen Article schema.

## Recommended User Actions

1. Create and independently verify an essential backup on a separate local disk.
2. Review available capacity before retaining the approximately 830 MB PDF library or creating a complete backup.
3. Set the full-corpus Reader/RAG/Graph environment variables and run the health checker.
4. Keep fake providers for deterministic validation; opt into real providers only after reviewing cost and privacy boundaries.
5. Do not create or publish `v1.1.0` until the fresh P2-007 release-readiness gate passes.
