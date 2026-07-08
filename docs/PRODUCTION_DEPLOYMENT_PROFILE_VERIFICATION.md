# Production Deployment Profile Verification

## Current Status

- P0-003 Implementation: PASS
- Verification: PASS
- Recommendation: A: Deployment profile verified

This is an audit gate only. No backend feature code, frontend product behavior, deployment architecture, M1-M7 contract, `v1.0.0` tag, or GitHub Release was changed.

## Deployment Document Verification

Result: PASS

`docs/PRODUCTION_DEPLOYMENT_PROFILE.md` contains the required sections:

- Current Status
- Scope
- Runtime Profiles
- Backend Runtime
- Frontend Runtime
- Provider Configuration
- Persistence and Local Data
- Security and Privacy Notes
- Docker / Compose Profile
- Smoke Test Checklist
- CI Coverage
- Known Risks
- Recommendation

The recommendation is `A: Deployment profile complete`.

The document explicitly states that this task is not a real production launch, does not deploy cloud infrastructure, does not add authentication, does not move the `v1.0.0` tag, and does not create a release.

## Runtime Profiles Verification

Result: PASS

`local-dev` includes:

- Backend `uvicorn app.main:app --reload`.
- Frontend `npm run dev`.
- Fake provider defaults.
- JSON stores by default.
- SQLite learning backend as opt-in.
- Local runtime data policy.

`local-production-like` includes:

- Backend non-reload `uvicorn` command.
- Frontend `npm run build` and `npm run start`.
- Explicit environment variables.
- Persistent local data directory.
- Optional SQLite learning backend.
- No real secrets committed.
- Smoke checklist.

`future-production` includes required future production boundaries:

- Auth/authz.
- HTTPS.
- Secret manager.
- Managed database.
- Object storage / artifact retention policy.
- Backup/restore.
- Monitoring/logging.
- CORS allowlist.
- Rate limiting.
- Data retention and privacy controls.

The document makes clear that `future-production` is a design boundary only and that no cloud deployment is implemented in this task.

## README Verification

Result: PASS

README contains:

- Local development backend and frontend commands.
- Local production-like backend and frontend commands.
- Backend test command.
- Frontend build command.
- Evaluation CLI command.
- Smoke checklist.
- Docker/Compose status.
- Environment variable summary.
- Known deployment limitations.

Commands align with current project configuration:

- Backend uses `uv run --project backend uvicorn app.main:app`.
- Frontend uses `npm run dev`, `npm run build`, and `npm run start`.
- Frontend API base URL is `NEXT_PUBLIC_API_BASE_URL`, matching `frontend/src/lib/*`.
- Docker compose command is `docker compose up --build`, matching `docker-compose.yml`.

## Env Example Verification

Result: PASS

`.env.example` contains safe placeholders and local defaults:

- `APP_ENV=local`
- `BACKEND_HOST=127.0.0.1`
- `BACKEND_PORT=8000`
- `FRONTEND_HOST=127.0.0.1`
- `FRONTEND_PORT=3000`
- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- `SCIENTIFIC_SPACES_LEARNING_BACKEND=json`
- `SCIENTIFIC_SPACES_DB_FILE=.local_data/scientific_spaces/scientific_spaces.db`
- `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=fake`
- `SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER=fake`
- `OPENAI_API_KEY=` with comments requiring real keys to stay in untracked local env or deployment environment.

No real API key, private path, real Zotero library path, or real secret was found.

## Backend Runtime Verification

Result: PASS

Backend tests:

```text
uv run --project backend --extra dev pytest -q
87 passed, 2 skipped in 3.74s
```

Production-like backend runtime smoke used non-reload `uvicorn app.main:app --host 127.0.0.1 --port 8000` with temporary stores and fake providers.

Smoke result:

```json
{
  "GET /health": {"status": 200, "payload": {"status": "ok"}},
  "GET /articles": {"status": 200, "count": 3},
  "POST /rag/index": {"status": 200, "article_count": 3, "chunk_count": 6},
  "POST /rag/query": {"status": 200, "sources": 3},
  "GET /learning/stats": {"status": 200},
  "GET /zotero/status": {"status": 200, "read_only": true},
  "GET /graph": {"status": 200, "nodes": 64},
  "POST /tutor/ask": {"status": 200, "sources": 8, "refusal": null}
}
```

The smoke run did not require a real API key, real Zotero, or web access.

## Frontend Runtime Verification

Result: PASS

Frontend build:

```text
npm run build
Next.js 15.5.20
Compiled successfully
Generated static pages (8/8)
```

Production-like frontend runtime used:

```bash
npm run start -- --hostname 127.0.0.1 --port 3000
```

Route smoke:

```json
{
  "/": {"status": 200, "length": 9665},
  "/articles": {"status": 200, "length": 8491},
  "/zotero": {"status": 200, "length": 9084},
  "/graph": {"status": 200, "length": 10936},
  "/tutor": {"status": 200, "length": 9601}
}
```

No `.next` or build artifact was staged or committed.

## Eval CLI Verification

Result: PASS

Command:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Output:

```text
RAG/Tutor Evaluation Baseline
Cases: 9
Retrieval hit@k: 100%
Citation required pass rate: 100%
No-source refusal rate: 100%
Source schema valid rate: 100%
No fake source rate: 100%
Quiz source coverage: 100%
Research local-only checks: PASS
Unsupported answer fabrications: 0
Answers without sources: 0
Quiz without sources: 0
Overall: PASS
```

The eval run did not require a real API key, did not access the web, and did not write runtime eval output.

## Docker / Compose Verification

Result: PASS with local environment limitation

Files exist:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.github/workflows/ci.yml`

Compose status:

- Defines `backend` and `frontend`.
- Backend exposes `8000`.
- Frontend exposes `3000`.
- Backend has a `/health` healthcheck.
- Frontend depends on backend health.
- Compose file does not include real secrets.
- Compose file does not mount or commit runtime DB files.

Local Docker check:

```text
docker --version
/bin/bash: line 1: docker: command not found
```

This is not a blocker because the deployment profile accurately records the local Docker limitation, backend/frontend/eval/runtime smoke passed outside Docker, and CI covers Docker compose smoke for manual `workflow_dispatch` and `v*` tag pushes.

CI Docker policy:

- Docker compose smoke is not run on normal PR/main push.
- Docker compose smoke runs on manual `workflow_dispatch` and `v*` tag push.
- This matches `docs/CI_RELEASE_AUTOMATION_HARDENING.md`.

## Provider / Persistence Boundary Verification

Result: PASS

Provider boundary:

- RAG defaults to `FakeEmbeddingProvider` and `FakeLLMProvider`.
- Tutor defaults to `SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER=fake`.
- Zotero defaults to `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=fake`.
- Real OpenAI-compatible provider paths are env-gated through `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_CHAT_MODEL`, and `OPENAI_EMBEDDING_MODEL`.
- No API key is committed.

Persistence boundary:

- JSON remains default compatibility backend.
- SQLite is opt-in for Learning through `SCIENTIFIC_SPACES_LEARNING_BACKEND=sqlite`.
- `SCIENTIFIC_SPACES_DB_FILE` is documented.
- `.local_data/`, DB files, runtime stores, cache, and eval outputs are ignored.
- Local stores are explicitly documented as not production multi-user persistence.

P0-002 behavior is not modified by this verification gate.

## Security and Privacy Caveat Verification

Result: PASS

Deployment/security caveats are explicit:

- MVP is local-first and single-user.
- No authentication.
- No authorization.
- No multi-user isolation.
- Production requires HTTPS, auth/authz, secret manager, managed storage, backup/restore, monitoring/logging, CORS allowlist, and rate limiting.
- Backend CORS currently allows only `http://localhost:3000` and `http://127.0.0.1:3000` with `allow_credentials=False`.
- Real provider secrets must be managed externally.
- Backup/restore caveats are documented for JSON and SQLite runtime files.
- Browser reading history localStorage privacy caveat is documented in README and the security/privacy baseline.

The documentation does not describe the current MVP as production-secure or multi-user ready.

## CI Coverage Verification

Result: PASS

`.github/workflows/ci.yml` includes:

- `pull_request`
- `push` to `main`
- `push` to `v*` tags
- `workflow_dispatch`

Jobs:

- Backend pytest: `uv run --project backend --extra dev pytest -q`
- Frontend build: `npm ci` then `npm run build`
- Docker compose smoke: manual workflow dispatch or `v*` tag push only

CI does not require real provider secrets and runs with fake/test defaults.

Latest P0-003 implementation CI:

- Run: `28941547811`
- URL: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28941547811`
- Event: `push`
- Head SHA: `5bd24e649266c5d4b1a82fe73c341b5b7832cf48`
- Conclusion: `success`

## Artifact / Privacy Verification

Result: PASS

Commands:

```bash
git status --short
git ls-files | grep -E '(^\.env$|\.sqlite$|\.sqlite3$|\.db$|\.pdf$|node_modules|\.local_data|eval_outputs|knowledge_graph\.json|learning\.json|tutor.*\.json|\.trace|\.prof|\.cache|\.next)' || true
```

Result:

- No tracked `.env`.
- No tracked API keys.
- No tracked DB files.
- No tracked runtime JSON stores.
- No tracked local data.
- No tracked eval outputs.
- No tracked graph outputs.
- No tracked FAISS/cache/embedding cache.
- No tracked PDFs, HTML dumps, traces, profiles, logs, `node_modules`, or `.next`.

## Freeze Protection

Result: PASS

P0-003 implementation commit `5bd24e649266c5d4b1a82fe73c341b5b7832cf48` changed only:

- `.env.example`
- `README.md`
- `docs/00_PROJECT_STATE.md`
- `docs/PRODUCTION_DEPLOYMENT_PROFILE.md`

Frozen contracts were not modified:

- M1 crawler/parser/converter/sync
- M2 Article API contract
- M3 RAG citation/no-source behavior
- M4 Learning API contract
- M5 Zotero read-only boundary
- M6 Graph provenance/evidence behavior
- M7 Tutor grounding/citation policy

Related post-MVP baselines remain intact:

- P0-002: JSON remains default and SQLite remains opt-in.
- P0-004: security/privacy baseline remains PASS.
- P0-005: eval CLI remains PASS.

## Test and Smoke Evidence

Backend pytest:

```text
87 passed, 2 skipped in 3.74s
```

Frontend build:

```text
Next.js 15.5.20 compiled successfully.
Generated static pages (8/8).
```

Eval CLI:

```text
Overall: PASS
```

Backend smoke:

```text
GET /health: 200
GET /articles: 200, count=3
POST /rag/query: 200, sources=3
GET /learning/stats: 200
GET /zotero/status: 200, read_only=true
GET /graph: 200, nodes=64
POST /tutor/ask: 200, sources=8, refusal=null
```

Frontend route smoke:

```text
/: 200
/articles: 200
/zotero: 200
/graph: 200
/tutor: 200
```

Docker status:

```text
docker: command not found
```

CI:

```text
Run 28941547811: success
```

## Findings

### Blockers

None.

### Medium Risks

None.

### Low Risks

- Local Docker is unavailable in this environment.
- Docker compose smoke is skipped on normal PR/main push by design.
- Runtime profile host and port variables in `.env.example` are documentation/shell-command inputs, not automatically consumed by app code.
- CORS remains local-only and must be configurable before real production.

### Accepted Limitations

- No auth/authz.
- Local JSON/SQLite stores are not production multi-user persistence.
- Real provider secret management remains external.
- No cloud deployment automation exists yet.
- Future production requires managed storage, backup/restore, monitoring/logging, rate limiting, and CORS allowlisting.

## Final Recommendation

A: Deployment profile verified
