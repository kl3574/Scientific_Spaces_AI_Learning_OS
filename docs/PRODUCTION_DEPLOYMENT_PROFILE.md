# Production Deployment Profile

## Current Status

- P0-003 status: PASS
- Recommendation: A: Deployment profile complete

This document defines the current post-MVP deployment profile. It is not a real production launch, does not deploy cloud infrastructure, does not add authentication, does not move the `v1.0.0` tag, and does not create a release.

## Scope

This task documents and verifies development, local production-like, and future production runtime profiles for the existing MVP. It does not change M1-M7 product behavior or API contracts.

In scope:

- Backend and frontend startup commands.
- Environment variables and local runtime data policy.
- JSON and SQLite persistence boundaries.
- Fake and optional real provider boundaries.
- CORS, host, no-auth, and MVP caveats.
- Docker compose status and smoke commands.
- Test, build, evaluation, and smoke checklists.

Out of scope:

- Cloud deployment.
- Auth/authz implementation.
- Multi-user authorization model.
- Managed database migration.
- Secret-manager integration.
- Release creation or tag movement.

## Runtime Profiles

### local-dev

Purpose:

- Local development.
- Fast feedback.
- Fake providers by default.
- JSON stores by default.
- Optional SQLite learning backend.
- Backend reload.
- Frontend development server.

Commands:

```bash
uv run --project backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Default URLs:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:3000`
- Frontend API target: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`

### local-production-like

Purpose:

- Local simulation of production startup.
- Backend non-reload process.
- Frontend build and `next start`.
- Explicit environment variables.
- Persistent ignored local data directory.
- Optional SQLite learning backend.
- No real secrets committed.

Commands:

```bash
cp .env.example .env
uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend
npm run build
npm run start -- --hostname 127.0.0.1 --port 3000
```

Recommended local-production-like environment:

```text
APP_ENV=local
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_HOST=127.0.0.1
FRONTEND_PORT=3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
SCIENTIFIC_SPACES_DATA_DIR=.local_data/scientific_spaces
SCIENTIFIC_SPACES_LEARNING_BACKEND=json
SCIENTIFIC_SPACES_ZOTERO_PROVIDER=fake
SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER=fake
```

SQLite opt-in for Learning data:

```text
SCIENTIFIC_SPACES_LEARNING_BACKEND=sqlite
SCIENTIFIC_SPACES_DB_FILE=.local_data/scientific_spaces/scientific_spaces.db
```

### future-production

Purpose:

- Future cloud or managed deployment design boundary.
- Not implemented by this task.

Required before real production use:

- Authentication and authorization.
- HTTPS termination.
- Secret manager for provider keys.
- Managed database or explicitly supported durable storage.
- Object storage and artifact retention policy.
- Backup and restore procedure.
- Monitoring, logging, and alerting.
- CORS allowlist configuration.
- Rate limiting and abuse controls.
- Data retention and privacy controls.
- Operational runbooks for provider failures and source pipeline failures.

## Backend Runtime

Development command:

```bash
uv run --project backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Production-like local command:

```bash
uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Docker command:

```bash
docker compose up --build
```

Current backend Dockerfile command:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Persistence behavior:

- Article storage: JSON.
- Learning storage: JSON default, SQLite opt-in.
- Zotero links: JSON.
- Knowledge graph: JSON.
- Tutor sessions: JSON.
- FAISS/vector index: in-memory and rebuildable.

## Frontend Runtime

Development command:

```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Build command:

```bash
cd frontend
npm run build
```

Production-like local command:

```bash
cd frontend
npm run start -- --hostname 127.0.0.1 --port 3000
```

Frontend API base URL:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

If the backend is exposed on a different host or port, set `NEXT_PUBLIC_API_BASE_URL` before building or starting the frontend runtime that will use it.

## Provider Configuration

Default local/test behavior:

- RAG embeddings use deterministic fake embeddings by default.
- Tutor LLM uses `SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER=fake` by default.
- Zotero uses `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=fake` by default.

Optional real-provider behavior:

- Tutor chat can use the OpenAI-compatible provider with `SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER=openai`.
- OpenAI-compatible chat and embedding provider classes read:
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `OPENAI_CHAT_MODEL`
  - `OPENAI_EMBEDDING_MODEL`
- Local Zotero metadata access is selected with `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=local`.
- Local Zotero base URL defaults to `http://127.0.0.1:23119`.

Boundary:

- Tests and CI must run without real provider keys.
- Real keys must live only in untracked `.env` files or the deployment environment.
- No API key is committed.
- Real provider quality is outside this deployment-profile task.

## Persistence and Local Data

Shared local runtime root:

```text
SCIENTIFIC_SPACES_DATA_DIR=.local_data/scientific_spaces
```

Store inventory:

| Store | Default backend | Default path or lifecycle | Environment override |
|---|---|---|---|
| Articles | JSON | `.local_data/scientific_spaces/articles.json` | `SCIENTIFIC_SPACES_ARTICLES_FILE` |
| Learning | JSON default, SQLite opt-in | `.local_data/scientific_spaces/learning.json` or SQLite DB | `SCIENTIFIC_SPACES_LEARNING_FILE`, `SCIENTIFIC_SPACES_LEARNING_BACKEND`, `SCIENTIFIC_SPACES_DB_FILE` |
| Zotero links | JSON | `.local_data/scientific_spaces/zotero_links.json` | `SCIENTIFIC_SPACES_ZOTERO_FILE` |
| Graph | JSON | `.local_data/scientific_spaces/knowledge_graph.json` | `SCIENTIFIC_SPACES_GRAPH_FILE` |
| Tutor sessions | JSON | `.local_data/scientific_spaces/tutor_sessions.json` | `SCIENTIFIC_SPACES_TUTOR_FILE` |
| FAISS/vector index | In-memory | Rebuildable | None |

Backup and restore caveats:

- JSON and SQLite files are local runtime artifacts.
- Backup must copy the configured runtime files outside the repository or into ignored local paths.
- No automatic JSON-to-SQLite migration runs at startup.
- SQLite currently covers Learning data only.
- Multi-user durability requires a future managed persistence design.

Ignored artifacts:

- `.env`
- `.local_data/`
- `*.db`, `*.sqlite`, `*.sqlite3`
- runtime JSON stores
- FAISS/cache/embedding outputs
- eval outputs
- PDF/HTML/image/browser trace artifacts
- `node_modules/` and build caches

## Security and Privacy Notes

Current MVP boundary:

- Local-first.
- Single-user.
- No authentication.
- No authorization.
- No multi-user isolation.
- No production secret manager.

CORS:

- Backend currently allows:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- This is suitable for local development.
- Real production requires an explicit CORS allowlist and HTTPS origin policy.

Secrets:

- Real provider keys must come from environment variables.
- `.env` files are ignored.
- `.env.example` contains placeholders only.
- Do not log or commit real API keys.

Production blockers:

- Add auth/authz before multi-user use.
- Add HTTPS and deployment secret management.
- Add backup/restore and retention policies.
- Add monitoring, logging, and rate limiting.

## Docker / Compose Profile

Current status:

- `backend/Dockerfile` exists.
- `frontend/Dockerfile` exists.
- `docker-compose.yml` defines `backend` and `frontend` services.
- Backend exposes `8000`.
- Frontend exposes `3000`.
- Compose includes a backend health check for `/health`.
- Frontend waits for backend health before start.

Command:

```bash
docker compose up --build
```

Smoke:

```bash
curl http://localhost:8000/health
curl http://localhost:3000/
```

Local limitation:

- The current Codex environment does not have `docker` installed, so local Docker build/smoke could not be executed here.

CI coverage:

- GitHub Actions Docker compose smoke runs for manual `workflow_dispatch` and `v*` tag pushes.
- PR and normal `main` push CI intentionally run backend pytest and frontend build without Docker smoke to keep feedback fast and avoid Docker-only runner failures.

## Smoke Test Checklist

Backend smoke:

- `GET /health`
- `GET /articles`
- `POST /rag/query`
- `GET /learning/stats`
- `GET /zotero/status`
- `GET /graph`
- `POST /tutor/ask`

Frontend smoke:

- `/`
- `/articles`
- `/zotero`
- `/graph`
- `/tutor`

Evaluation smoke:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Regression tests:

```bash
uv run --project backend --extra dev pytest -q
cd frontend
npm run build
```

## CI Coverage

Workflow:

- `.github/workflows/ci.yml`

Triggers:

- Pull requests.
- Pushes to `main`.
- Pushes to `v*` tags.
- Manual `workflow_dispatch`.

Jobs:

- Backend pytest.
- Frontend build.
- Docker compose smoke for manual workflow dispatch and `v*` tag pushes.

Latest referenced CI evidence before this task:

- P0-005 Verification CI run: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28941131869`
- Conclusion: PASS

## Validation Evidence

Backend tests:

```text
uv run --project backend --extra dev pytest -q
87 passed, 2 skipped
```

Frontend build:

```text
npm run build
Next.js 15.5.20 compiled successfully and generated static pages.
```

Evaluation harness:

```text
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
Overall: PASS
```

Production-like runtime smoke with temporary stores:

```json
{
  "GET /health": 200,
  "GET /articles": {"status": 200, "count": 3},
  "POST /rag/index": {"status": 200, "article_count": 3, "chunk_count": 6},
  "POST /rag/query": {"status": 200, "sources": 3},
  "GET /learning/stats": {"status": 200, "keys": ["bookmark_count", "completed_count", "note_count", "reading_count", "recent_articles", "recent_sessions", "total_articles", "unread_count"]},
  "GET /zotero/status": {"status": 200, "read_only": true},
  "GET /graph": {"status": 200, "nodes": 64},
  "POST /tutor/ask": {"status": 200, "sources": 8, "refusal": null}
}
```

Frontend route smoke with `next start`:

```json
{
  "/": {"status": 200, "length": 9665},
  "/articles": {"status": 200, "length": 8491},
  "/zotero": {"status": 200, "length": 9084},
  "/graph": {"status": 200, "length": 10936},
  "/tutor": {"status": 200, "length": 9601}
}
```

Docker:

```text
docker --version
/bin/bash: line 1: docker: command not found
```

Docker local smoke was not run in this environment. This is recorded as a local environment limitation, not a blocker, because the deployment profile documents Docker status and CI has Docker smoke coverage for manual/tag runs.

## Known Risks

- No auth/authz.
- Local stores are not production multi-user persistence.
- Fake providers are the default.
- Real provider secret management remains external.
- Docker behavior can vary by local environment.
- No cloud deployment automation exists yet.
- CORS is local-only and must be tightened for production origins.
- SQLite is only an opt-in Learning persistence slice, not a full production storage layer.
- Provider availability and source pipeline failures need future operational diagnostics.

## Recommendation

A: Deployment profile complete
