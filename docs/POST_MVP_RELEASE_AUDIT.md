# Post-MVP Release Audit

## Current Status

| Item | Result | Evidence |
|---|---|---|
| MVP Complete | Yes | `docs/00_PROJECT_STATE.md` records `v1.0.0`, `MVP Complete`, and `MVP Status: Complete`. |
| Release Readiness | PASS | README, environment documentation, verification reports, artifact/privacy checks, local tests/build, runtime smoke, freeze checks, and CI configuration are acceptable. |

This is a release-readiness audit only. No backend feature code, frontend feature code, M1-M7 frozen contracts, release, or tag was changed by this gate.

## README Audit

Result:

- PASS

Actions:

- Updated `README.md` from bootstrap-only status to MVP-complete release-readiness documentation.

Verified README coverage:

- Project introduction.
- MVP capability overview:
  - Scientific Spaces source pipeline.
  - Reader.
  - Grounded RAG.
  - Learning Management.
  - Zotero Integration.
  - Knowledge Graph.
  - AI Research Tutor.
- Architecture overview.
- Backend setup and runtime commands.
- Frontend setup and runtime commands.
- Test commands.
- Environment variable summary.
- Fake provider defaults and optional real-provider boundaries.
- Docker usage and local Docker limitation.
- Local data and artifact policy.
- Known limitations.
- Post-MVP directions.

## Setup / Run Audit

Result:

- PASS

Verified commands:

Backend tests:

```text
uv run --project backend --extra dev pytest -q
```

Backend runtime:

```text
uv run --project backend uvicorn app.main:app --reload
```

Frontend install/build/dev:

```text
cd frontend
npm install
npm run build
npm run dev
```

Notes:

- Root `pyproject.toml` is absent; backend dependency management is intentionally in `backend/pyproject.toml`.
- Tests do not require a real API key.
- Zotero defaults to a fake read-only provider.
- Docker is documented as optional for local use when unavailable.

## Environment Variable Audit

Result:

- PASS

Actions:

- Added `.env.example` with placeholder-only values.

Verified coverage:

- `SCIENTIFIC_SPACES_DATA_DIR`
- `SCIENTIFIC_SPACES_ARTICLES_FILE`
- `SCIENTIFIC_SPACES_LEARNING_FILE`
- `SCIENTIFIC_SPACES_ZOTERO_FILE`
- `SCIENTIFIC_SPACES_GRAPH_FILE`
- `SCIENTIFIC_SPACES_TUTOR_FILE`
- `SCIENTIFIC_SPACES_SOURCE_STRATEGY`
- `SCIENTIFIC_SPACES_FEED_URL`
- `SCIENTIFIC_SPACES_MAX_PAGES`
- `SCIENTIFIC_SPACES_MAX_ARTICLES`
- `SCIENTIFIC_SPACES_ZOTERO_PROVIDER`
- `SCIENTIFIC_SPACES_ZOTERO_BASE_URL`
- `SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_CHAT_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `NEXT_PUBLIC_API_BASE_URL`

Provider boundary:

- Fake/test providers remain the documented default.
- Real OpenAI-compatible providers require explicit environment configuration.
- No real API key is committed.

## Verification Report Audit

Result:

- PASS

Required reports:

- `docs/M1_FINAL_FREEZE_REPORT.md`: PASS.
- `docs/M2_VERIFICATION_REPORT.md`: PASS.
- `docs/M3_VERIFICATION_REPORT.md`: PASS.
- `docs/M4_VERIFICATION_REPORT.md`: PASS.
- `docs/M5_VERIFICATION_REPORT.md`: PASS.
- `docs/M6_VERIFICATION_REPORT.md`: PASS.
- `docs/M7_VERIFICATION_REPORT.md`: PASS and `A: MVP Complete`.

State consistency:

- `docs/00_PROJECT_STATE.md` records `v1.0.0`, `MVP Complete`, `M7 Verification Passed`, and `MVP Status: Complete`.
- M1-M7 status chain is coherent.

Known documentation gaps:

- `docs/15_ACCEPTANCE.md` is absent.
- `docs/31_MVP_BOUNDARY.md` is absent.
- `milestones/M7_AI_RESEARCH_TUTOR.md` is absent; repository contains `milestones/M7_AI_TUTOR.md`.

These are documented gaps, not release blockers for this audit because M1-M7 implementation and verification reports are present and consistent.

## Artifact / Privacy Audit

Result:

- PASS

Git scans found no tracked:

- `.env`
- API keys
- runtime tutor session data
- private user study data
- runtime learning data
- runtime graph data
- runtime Zotero data
- real Zotero library export
- large BibTeX data
- FAISS index/cache
- embedding cache
- PDFs
- downloaded HTML dumps
- images
- trace/profile/cache artifacts
- `node_modules`
- large article corpus exports
- local runtime data

`.gitignore` covers:

- `.env`
- `.env.*`
- `.local_data/`
- `backend/.local_data/`
- `backend/data/`
- Python caches
- Node/Next.js outputs
- dependency directories

## Freeze Contract Audit

Result:

- PASS

Git diff showed no changes to frozen implementation or contract files during this release audit.

Checked frozen areas:

- M1 crawler, parser, converter, storage, validation, sync.
- M2 Article API, Reader routes, search behavior.
- M3 RAG API, citation policy, no-source refusal.
- M4 learning state, bookmarks, notes, sessions, stats.
- M5 Zotero provider and status/search/item/export/link APIs.
- M6 graph model, graph API, concept provenance, edge evidence.
- M7 tutor API, citation policy, no-source refusal, local-only research boundary.

## Test / Build Audit

Result:

- PASS

Backend:

```text
uv run --project backend --extra dev pytest -q
63 passed, 2 skipped in 3.57s
```

Frontend:

```text
npm run build
Next.js 15.5.20 build completed successfully.
```

Runtime smoke:

- Backend smoke covered `/health`, `/articles`, `/rag/index`, `/rag/query`, `/learning/state`, `/learning/stats`, `/zotero/status`, `/graph/build`, `/graph`, and `/tutor/ask`.
- Frontend smoke covered `/`, `/articles`, `/zotero`, `/graph`, and `/tutor`.

Docker:

- Local environment limitation: `docker` is unavailable with `docker: command not found`.
- Not a release blocker because non-Docker tests/build/runtime smoke passed and CI includes Docker compose smoke.

## CI / GitHub Actions Audit

Result:

- PASS with note

Workflow:

- `.github/workflows/ci.yml`

Triggers:

- `pull_request`
- `workflow_dispatch`

Jobs:

- Backend pytest.
- Frontend build.
- Docker compose smoke.

Latest visible workflow runs:

- Recent `workflow_dispatch` CI runs on `main` completed successfully.

Release note:

- The workflow does not trigger on push. Release maintainers should run the manual workflow before publishing a GitHub release if they require CI evidence on the exact release commit.

## Known Risks

- Docker is not installed in the current local audit environment.
- CI is PR/manual-triggered rather than push-triggered.
- The MVP is local-first and not production multi-user storage.
- Real LLM quality depends on optional provider configuration and source quality.
- Research mode is local-only and not exhaustive web research.
- Zotero local provider is read-only.
- Historical documentation gaps remain: `docs/15_ACCEPTANCE.md`, `docs/31_MVP_BOUNDARY.md`, and the renamed M7 milestone document.

## Recommended Release Action

A: Ready to tag v1.0.0
