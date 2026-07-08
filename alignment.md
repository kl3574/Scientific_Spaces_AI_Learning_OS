# M7 AI Research Tutor Implementation Alignment

## Scope

This run implements Milestone 7 - AI Research Tutor.

Allowed changes:

- M7 tutor model, policy, service, local session summary store, and API.
- Frontend tutor page and navigation entry.
- M7 backend regression tests.
- `docs/M7_IMPLEMENTATION_REPORT.md`
- `docs/00_PROJECT_STATE.md`

Forbidden changes:

- M1 crawler, parser, converter, storage, validation, sync, browser access, or verification standards.
- M2 Reader contract changes.
- M3 RAG contract changes.
- M4 Learning Management expansion beyond personalization-only read context.
- M5 Zotero writes or real-library mutation.
- M6 Knowledge Graph schema changes.
- Web research, crawler expansion, PDF/HTML/image exports, runtime stores, `.env`, API keys, FAISS/index/cache artifacts, or private user data.

## Implementation Alignment

M7 tutor orchestration is layered on existing read interfaces:

1. M3 article chunk retrieval and vector search provide primary factual sources.
2. M6 graph context supplements article evidence.
3. M5 Zotero metadata supplements local research context in read-only mode.
4. M4 learning state is exposed only as personalization context and is not a citation source.
5. M7 citation policy refuses substantive answers without article sources.

## Verification Evidence

- Backend tests: `uv run --project backend --extra dev pytest -q`
- Frontend build: `npm run build`
- Runtime smoke using temporary data under `/tmp`
- M2-M6 regression endpoint smoke checks
- Freeze protection scan for frozen M1-M6 backend modules
- Artifact scan for secrets, media, runtime stores, caches, and local data

## Decision

M7 implementation is ready for a separate M7 Verification Gate.

## State Update

`docs/00_PROJECT_STATE.md` is updated to record:

- `Version: v0.8.0`
- `Phase: M7 Completed`
- `Status: AI Research Tutor implemented`
