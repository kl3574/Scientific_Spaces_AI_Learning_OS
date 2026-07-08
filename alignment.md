# Task Alignment - M3 Verification Gate

## 1. Background

Project: `kl3574/Scientific_Spaces_AI_Learning_OS`

Current milestone evidence:

- M0 Engineering Foundation: PASS
- M1 Source Pipeline: PASS
- M1 Final Freeze: PASS
- M2 Scientific Reader: PASS
- M2 Verification: PASS
- M3 Grounded RAG Assistant: IMPLEMENTED

M3 implementation commit:

- `0e76a4b5021491fffe38955dfc93fa208123bd3c`

This task verifies M3 only. It must not implement M4 Learning Management or any M5-M7 functionality.

## 2. Scope

Allowed changes:

- `alignment.md`
- `docs/M3_VERIFICATION_REPORT.md`
- `docs/00_PROJECT_STATE.md` only if verification passes

Forbidden changes:

- M3 implementation code
- M1/M2 frozen implementation code
- M3 verification standard
- M4-M7 features
- FAISS index files, embedding cache, API keys, `.env`, PDF, HTML dumps, images, traces, profiles, cache, `node_modules`, or large article data

## 3. Gate Focus

The verification gate must confirm:

1. Markdown-aware chunking preserves heading sections, equation blocks, fenced code blocks, and chunk metadata.
2. Embedding provider abstraction is testable with a default fake provider and no API key.
3. FAISS vector search is reproducible, handles empty data, and does not commit index/cache artifacts.
4. LLM provider abstraction is testable with a default fake provider and no API key.
5. Grounded answers return non-empty citations.
6. No-source queries refuse without fabrication.
7. M1/M2 frozen code and contracts are unchanged.
8. M4-M7 scope is not implemented early.

## 4. Execution Plan

1. Read required M3, M2, M1, data model, AI agent, and knowledge pipeline documents.
2. Record missing required docs as verification risk when absent.
3. Inspect M3 RAG, LLM, API, tests, and frontend paths.
4. Check M1/M2 freeze protection through git diffs.
5. Scan for M4-M7 scope leaks and forbidden tracked artifacts.
6. Run backend tests:
   - `uv run --project backend --extra dev pytest -q`
7. Run frontend build:
   - `npm run build`
8. Run runtime smoke for:
   - `POST /rag/index`
   - `POST /rag/query`
   - no-source refusal
   - M2 `/articles` regression
9. Create `docs/M3_VERIFICATION_REPORT.md`.
10. If all pass, update `docs/00_PROJECT_STATE.md` with:
    - `M3 Verification Passed`
    - `M4 Readiness: Ready for M4`

## 5. Pass Criteria

M3 verification can pass only if:

- Backend tests pass.
- Frontend build passes.
- Chunking preserves sections, equations, and code blocks.
- Fake embedding provider works without an API key.
- FAISS search works and no vector artifacts are committed.
- Fake LLM provider works without an API key.
- Grounded answers return non-empty citations.
- No-source behavior refuses without fabrication.
- M1/M2 frozen code is not modified.
- No M4-M7 scope leak is detected.
- No forbidden artifacts are committed.

## 6. Block Criteria

M3 verification is blocked if any of these are found:

- Substantive answer can be returned without citation.
- No-source query fabricates an answer.
- Chunking breaks equation or code blocks.
- Embedding/vector tests require a real API key.
- FAISS index/cache artifacts are committed.
- M1/M2 frozen paths are modified.
- M4-M7 functionality is implemented early.
- Backend tests or frontend build fail.

## 7. Expected Deliverables

- Updated `alignment.md`
- Created `docs/M3_VERIFICATION_REPORT.md`
- Updated `docs/00_PROJECT_STATE.md` if verification passes
- Commit:
  - pass: `docs: pass M3 verification gate`
  - blocked: `docs: record M3 verification blockers`
