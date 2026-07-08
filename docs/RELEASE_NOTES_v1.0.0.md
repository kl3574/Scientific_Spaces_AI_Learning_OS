# Scientific Spaces AI Learning OS v1.0.0 MVP

## Status

- MVP Complete
- Release readiness: PASS

## Included Milestones

- M0 Engineering Foundation
- M1 Scientific Spaces Source Pipeline
- M2 Scientific Reader
- M3 Grounded RAG Assistant
- M4 Learning Management
- M5 Zotero Integration
- M6 Knowledge Graph
- M7 AI Research Tutor

## Highlights

1. Scientific Spaces article source pipeline with RSS discovery, browser article access, parsing, Markdown conversion, storage, validation, and independent PDF export capability.
2. Markdown reader and search for local Scientific Spaces articles.
3. Citation-grounded RAG with Markdown-structure chunking, deterministic fake providers for tests, FAISS vector search, and source citations.
4. Learning state, bookmarks, notes, sessions, and dashboard statistics.
5. Zotero metadata/search/export/linking through fake default and optional local read-only provider.
6. Knowledge graph with article, section, concept, formula, and Zotero item nodes plus provenance metadata and edge evidence.
7. AI Research Tutor with grounded modes:
   - explain
   - derive
   - qa
   - quiz
   - research

## Verification Evidence

- Backend tests: 63 passed, 2 skipped
- Frontend build: passed
- Runtime smoke: backend and frontend passed
- Post-MVP Release Readiness: PASS

## Safety / Grounding Guarantees

- No uncited substantive answer.
- No-source refusal behavior for RAG and Tutor paths.
- Fake providers are default for tests.
- Real providers are optional via environment variables.
- No API keys committed.
- No private/runtime artifacts committed.

## Known Limitations

- Docker unavailable in local verification environment.
- CI currently PR/manual triggered, not push triggered.
- Local JSON stores are not production multi-user databases.
- Zotero local API availability depends on user environment.
- Research mode is local-only and not exhaustive web research.

## Post-MVP Directions

- Deployment hardening.
- Persistence/database upgrade.
- Richer graph visualization.
- Improved real provider configuration.
- Better CI/release automation.
