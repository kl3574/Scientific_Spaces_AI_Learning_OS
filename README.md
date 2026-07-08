# Scientific Spaces AI Learning OS

Scientific Spaces AI Learning OS is a local-first learning system for Scientific Spaces articles. The MVP combines a source pipeline, reader, grounded RAG assistant, learning state, Zotero metadata links, a knowledge graph, and a citation-grounded AI research tutor.

## Current Status

- Version: `v1.0.0`
- Phase: `MVP Complete`
- Status: `Scientific Spaces AI Learning OS MVP complete`
- Latest gate: `M7 Final Verification: PASS`

Release-readiness evidence is recorded in `docs/POST_MVP_RELEASE_AUDIT.md`.

## MVP Capabilities

- Scientific Spaces source pipeline: RSS discovery, Playwright article access, parser, Markdown converter, storage, validation, and independent PDF export capability.
- Scientific Reader: article list, article detail, title/content search, and basic local reading history.
- Grounded RAG Assistant: Markdown-structure chunking, deterministic fake embeddings by default, FAISS vector search, optional OpenAI-compatible providers, and source citations.
- Learning Management: article learning state, bookmarks, notes, sessions, and dashboard statistics.
- Zotero Integration: read-only fake provider by default, optional local Zotero API provider, metadata search/export, and article-to-Zotero links.
- Knowledge Graph: article, section, concept, formula, and Zotero item graph with provenance metadata and edge evidence.
- AI Research Tutor: `explain`, `derive`, `qa`, `quiz`, and `research` modes with required grounding and refusal for unsupported answers.

## Architecture

```text
Scientific Spaces RSS
  -> browser article acquisition
  -> parser / Markdown converter
  -> Article storage
  -> Reader API and UI
  -> RAG chunking / embeddings / FAISS
  -> Learning / Zotero / Knowledge Graph
  -> Grounded AI Tutor
```

Backend code is under `backend/app/`. Frontend code is under `frontend/src/`. Project specifications, verification reports, and milestone records are under `docs/` and `milestones/`.

## Backend Setup

Requirements:

- Python `3.11`
- `uv`

Install and test:

```bash
uv run --project backend --extra dev pytest -q
```

Run the backend:

```bash
uv run --project backend uvicorn app.main:app --reload
```

Default backend URL:

```text
http://localhost:8000
```

Useful endpoints:

- `GET /health`
- `GET /articles`
- `POST /rag/query`
- `GET /learning/stats`
- `GET /zotero/status`
- `GET /graph`
- `POST /tutor/ask`

## Frontend Setup

Requirements:

- Node.js `22`
- npm

Install dependencies:

```bash
cd frontend
npm install
```

Build:

```bash
npm run build
```

Run the frontend:

```bash
npm run dev
```

Default frontend URL:

```text
http://localhost:3000
```

Main routes:

- `/`
- `/articles`
- `/articles/[id]`
- `/zotero`
- `/graph`
- `/tutor`

## Environment Variables

The project runs locally with fake providers by default and does not require a real API key for tests.

Copy `.env.example` only if you need local overrides:

```bash
cp .env.example .env
```

Important variables:

- `SCIENTIFIC_SPACES_DATA_DIR`: local runtime data directory. Defaults to `.local_data/scientific_spaces`.
- `SCIENTIFIC_SPACES_DB_FILE`: optional SQLite database path. Defaults to `.local_data/scientific_spaces/scientific_spaces.db`.
- `SCIENTIFIC_SPACES_LEARNING_BACKEND`: `json` by default; set `sqlite` to opt into the v1.1 Learning SQLite persistence slice.
- `SCIENTIFIC_SPACES_ARTICLES_FILE`: override Article storage file.
- `SCIENTIFIC_SPACES_LEARNING_FILE`: override learning-state storage file.
- `SCIENTIFIC_SPACES_ZOTERO_FILE`: override Zotero link storage file.
- `SCIENTIFIC_SPACES_GRAPH_FILE`: override graph storage file.
- `SCIENTIFIC_SPACES_TUTOR_FILE`: override tutor session storage file.
- `SCIENTIFIC_SPACES_ZOTERO_PROVIDER`: `fake` by default; set `local` to use the local Zotero API.
- `SCIENTIFIC_SPACES_ZOTERO_BASE_URL`: local Zotero API URL, default `http://127.0.0.1:23119`.
- `SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER`: `fake` by default; set `openai` for OpenAI-compatible chat.
- `OPENAI_API_KEY`: optional, only needed for OpenAI-compatible providers.
- `OPENAI_BASE_URL`: optional OpenAI-compatible base URL.
- `OPENAI_CHAT_MODEL`: optional chat model override.
- `OPENAI_EMBEDDING_MODEL`: optional embedding model override.
- `NEXT_PUBLIC_API_BASE_URL`: frontend API base URL, default `http://localhost:8000`.

Do not commit real `.env` files, API keys, Zotero library exports, or local runtime data.

## Persistence

The v1.0.0 MVP uses local JSON stores by default. Post-MVP persistence hardening introduces an opt-in SQLite slice for M4 Learning data while preserving the existing API contracts and JSON compatibility path.

Default compatibility mode:

```text
SCIENTIFIC_SPACES_LEARNING_BACKEND=json
```

Opt-in SQLite Learning persistence:

```text
SCIENTIFIC_SPACES_LEARNING_BACKEND=sqlite
SCIENTIFIC_SPACES_DB_FILE=.local_data/scientific_spaces/scientific_spaces.db
```

Current persistence boundaries:

- Article storage remains JSON.
- Learning state, bookmarks, notes, and sessions can use JSON or opt-in SQLite.
- Zotero links remain JSON.
- Knowledge Graph output remains JSON.
- Tutor sessions remain JSON.
- FAISS/vector indexes remain rebuildable and ephemeral.

SQLite database files are local runtime artifacts and must not be committed.

## Provider Boundaries

Default local/test behavior:

- RAG embeddings: deterministic fake embedding provider.
- Tutor LLM: deterministic fake LLM provider.
- Zotero: read-only fake provider.

Optional real-provider behavior:

- OpenAI-compatible chat/embedding providers are enabled only through environment variables.
- Local Zotero API is read-only and selected only with `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=local`.
- The system must refuse unsupported substantive tutor answers instead of relying on model common knowledge.

## Security and Privacy

Security policy:

- `SECURITY.md`

Baseline audit:

- `docs/SECURITY_PRIVACY_BASELINE.md`

Current security/privacy boundary:

- The MVP is local-first and single-user.
- Authentication, authorization, and multi-user isolation are not implemented.
- Fake providers are the default for tests and local development.
- Real OpenAI-compatible provider keys are optional and must stay outside git.
- Zotero integration is read-only and local-provider access is opt-in.
- RAG and tutor answers must be grounded in local article sources; no-source cases refuse.
- Research mode is local-only and does not perform autonomous web research or paper downloads.

## Docker

Docker support is defined in `docker-compose.yml` and service Dockerfiles:

```bash
docker compose up --build
```

Expected services:

- Backend: `http://localhost:8000/health`
- Frontend: `http://localhost:3000`

Current local audit environment limitation:

- `docker` is not installed in the current Codex environment, so local Docker smoke may be skipped there.
- GitHub Actions includes a Docker compose smoke job.

## Testing

Backend:

```bash
uv run --project backend --extra dev pytest -q
```

Frontend:

```bash
cd frontend
npm run build
```

Optional live checks:

- Browser/live/PDF tests are marked and skipped by default.
- Use `RUN_LIVE_TESTS=1` only for explicit live-source diagnostics.

## CI

GitHub Actions workflow:

- `.github/workflows/ci.yml`

Triggers:

- Pull requests
- Pushes to `main`
- Pushes to `v*` tags
- Manual `workflow_dispatch`

Jobs:

- Backend pytest: `uv run --project backend --extra dev pytest -q`
- Frontend build: `npm ci` then `npm run build`
- Docker compose smoke: runs for manual workflow dispatch and `v*` tag pushes, so PR/main push test-build feedback is not blocked by Docker-only failures

Release evidence process:

- For release evidence on an exact tag, run the CI workflow manually with `workflow_dispatch` against that tag or inspect the CI run created by a `v*` tag push.
- Record the workflow run URL, ref/tag, conclusion, and covered checks in a release evidence document.
- Release publishing remains manual; CI does not move tags or create GitHub Releases.

## Local Data and Artifact Policy

Ignored local/runtime paths include:

- `.env`
- `.local_data/`
- `backend/.local_data/`
- `backend/data/`
- `node_modules/`
- `frontend/node_modules/`
- Python and Next.js caches

Do not commit:

- API keys
- real tutor session data
- private user study data
- runtime Article/learning/graph/Zotero/tutor stores
- real Zotero library data
- large article corpus exports
- FAISS or embedding caches
- PDFs, downloaded HTML, images, traces, profiles, or generated browser artifacts

Browser reading history is stored in localStorage under the user's browser profile. Treat it as local private activity data.

## Verification Reports

Release-readiness should be checked against:

- `docs/M1_FINAL_FREEZE_REPORT.md`
- `docs/M2_VERIFICATION_REPORT.md`
- `docs/M3_VERIFICATION_REPORT.md`
- `docs/M4_VERIFICATION_REPORT.md`
- `docs/M5_VERIFICATION_REPORT.md`
- `docs/M6_VERIFICATION_REPORT.md`
- `docs/M7_VERIFICATION_REPORT.md`
- `docs/POST_MVP_RELEASE_AUDIT.md`

Project state:

- `docs/00_PROJECT_STATE.md`

## Known Limitations

- The MVP is local-first and not production multi-user storage.
- Real LLM quality depends on optional provider configuration and available source quality.
- Research mode is local-only and does not perform autonomous web research or claim exhaustive literature review.
- Zotero integration is read-only for local libraries.
- Docker is optional locally; if unavailable, use backend/frontend test and runtime smoke commands.
- Some historical planning documents are missing or renamed, including `docs/15_ACCEPTANCE.md`, `docs/31_MVP_BOUNDARY.md`, and `milestones/M7_AI_RESEARCH_TUTOR.md`.

## Post-MVP Directions

- Harden storage for multi-user deployments.
- Add authentication and production deployment configuration.
- Improve source coverage and source-quality monitoring.
- Add release automation and versioned distribution artifacts.
- Expand tutor evaluation with curated source-grounded benchmarks.
