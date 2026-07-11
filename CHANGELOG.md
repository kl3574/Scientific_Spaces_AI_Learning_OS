# Changelog

## [Unreleased]

- `v1.1.0` release readiness is blocked by a frozen Article-list compatibility regression. No tag or Release may be created until a targeted compatibility/migration revision and gate re-run pass.

## [1.1.0] - Unreleased

### Added

- Controlled full-corpus processing for 1,326 canonical Scientific Spaces seeds, producing 1,311 validated Articles and classifications for 15 non-importable candidates.
- A 1,311-file local Markdown library and an optional 1,311-file offline PDF library.
- Persisted full-corpus FAISS retrieval with 5,547 source-grounded chunks.
- A bounded full-corpus Knowledge Graph with 52,874 nodes and 82,230 edges.
- Full-corpus Tutor source selection, deterministic grounding evaluations, and local-only frontend smoke coverage.
- Local data inventory, health, cleanup, essential backup, independent verification, and isolated restore tooling.
- Local production-like deployment, security/privacy, and evaluation-harness documentation.

### Changed

- CI now runs on pull requests, `main` pushes, `v*` tag pushes, and manual dispatch; Docker smoke remains limited to tags and manual runs.
- `GET /articles` now uses bounded pagination and supports category and sort parameters while retaining the original list item fields.
- Full-corpus Reader, RAG, Graph, and Tutor paths can be selected through explicit local environment variables.
- Learning JSON remains the default; SQLite is an opt-in persistence slice with documented rollback.

### Fixed

- Legacy Article body extraction, page-chrome filtering, URL canonicalization, and invalid-candidate classification for controlled corpus processing.
- Tutor retrieval support gates, refusal behavior, research-source diversity, bounded graph context, and source payload limits.
- Graph concept provenance and large-corpus API bounds.
- PDF resume validation and local-data backup/restore safety checks.

### Security

- Added explicit local-data, secret, provider, CORS, artifact, backup, and restore boundaries.
- Added ignore rules for runtime corpus data, databases, PDFs, indexes, graphs, backups, restores, browser artifacts, and build output.
- Fake providers remain the default; real provider credentials are opt-in and must remain outside Git.

### Known limitations

- The product remains local-first and single-user, without authentication or authorization.
- JSON stores are not safe for production multi-user concurrency; SQLite covers only an opt-in Learning migration slice.
- Fake-provider evaluations establish deterministic contracts and grounding, not real-model language or mathematical quality.
- PDFs replace remote images with placeholders and do not claim source print parity.
- Backup archives are local, unencrypted by the application, and are not automatically retained off-site.
- Year-based legacy partition completion remains conditional.

## [1.0.0] - 2026-07-08

- Released the verified M0-M7 MVP: source pipeline, Scientific Reader, grounded RAG, Learning Management, read-only Zotero integration, Knowledge Graph, and AI Research Tutor.
- Recorded exact-tag CI evidence covering backend pytest, frontend build, and Docker compose smoke.
