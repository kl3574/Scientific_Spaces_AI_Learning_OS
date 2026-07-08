# Security and Privacy Baseline

## Current Status

- Baseline: PASS
- Scope: P0-004 post-MVP security and privacy baseline for the repository, backend, frontend, CI, local runtime stores, provider boundaries, and documentation.
- Date: 2026-07-08
- Audit base commit: `d76c6dc6f9ec22c0c3eb9e9653efb65f83484d1e`

This baseline is an audit and minimal documentation/configuration hardening task. It does not implement product features, authentication, authorization, multi-user storage, or any M1-M7 behavior changes.

## Threat Model Summary

Primary assets:

- Article corpus and Article metadata
- User learning state, bookmarks, notes, and sessions
- Browser local reading history
- Tutor sessions and user questions
- Zotero metadata and article-to-Zotero links
- Local JSON stores and opt-in SQLite database files
- Optional OpenAI-compatible API keys
- RAG chunks, vector index state, graph evidence, and tutor context

Primary boundaries:

- The application is local-first and single-user by default.
- Fake providers are the default for tests and local development.
- Real OpenAI-compatible providers are optional and enabled through environment variables.
- Local Zotero access is optional, local API based, and read-only.
- MVP has no authentication or authorization.
- Research mode is local-only and does not perform autonomous web research.
- Graph and Zotero context are supplemental and cannot replace article citations for tutor answers.

## Secrets and Env Audit

Result: PASS

Evidence:

- `git ls-files` scan found no tracked `.env`, SQLite/DB files, PDFs, `node_modules`, `.local_data`, FAISS/cache, embedding cache, runtime graph, learning, tutor, or Zotero link files.
- `git grep -n "sk-"` returned no matches outside ignored lockfiles.
- `git grep` for `OPENAI_API_KEY`, `api_key`, `password`, `token`, `gho_`, and `github_pat` found only expected placeholder/configuration/code references:
  - `.env.example` placeholder `OPENAI_API_KEY=`
  - README environment documentation
  - backend provider code reading `OPENAI_API_KEY` from the environment
  - non-secret tokenization/math-placeholder code
- `gitleaks` is not installed in the current environment. This is recorded as a tooling limitation, not a blocker, because grep/manual audit found no committed secrets.
- `.env.example` contains local defaults and an empty `OPENAI_API_KEY` placeholder, not a real key.

Path audit:

- No personal runtime path is hardcoded in application code.
- Historical documentation contains local diagnostic/tool paths in:
  - `docs/M1_PDF_EXPORT_EVALUATION.md`
  - `docs/M5_IMPLEMENTATION_REPORT.md`
- These are not secrets or active runtime configuration paths. They remain low-risk historical audit context.

## Local Data and Privacy Audit

Result: PASS

Runtime/local data paths:

- `.local_data/scientific_spaces/articles.json`
- `.local_data/scientific_spaces/learning.json`
- `.local_data/scientific_spaces/scientific_spaces.db`
- `.local_data/scientific_spaces/zotero_links.json`
- `.local_data/scientific_spaces/knowledge_graph.json`
- `.local_data/scientific_spaces/tutor_sessions.json`
- browser `localStorage` key `scientific-spaces-reading-history-v1`

Verified controls:

- `.gitignore` covers `.env`, `.env.*`, `.local_data/`, `*.db`, `*.sqlite`, `*.sqlite3`, `node_modules/`, `frontend/.next/`, Python caches, and local backend data directories.
- This baseline adds explicit ignore patterns for logs, traces, profiles, and `*.cache`.
- Runtime JSON, SQLite DB files, Zotero exports, tutor sessions, learning notes, graph output, FAISS/vector indexes, embedding caches, PDFs, downloaded HTML, images, traces, profiles, and local browser artifacts are not tracked.
- README documents local data and artifact policy.
- `SECURITY.md` documents local data policy and browser localStorage privacy caveat.

Known privacy caveat:

- Reading history is stored in browser localStorage. It is local to the user's browser profile, but it is still user activity data.

## Backend API Security Audit

Result: PASS with accepted limitations

Checked:

- `backend/app/main.py`
- `backend/app/api/`
- JSON/SQLite store modules
- RAG, tutor, Zotero, graph, and learning endpoints

Findings:

- No shell execution path was found in backend application code.
- No API endpoint directly concatenates user input into shell commands.
- SQLite learning persistence uses parameterized queries.
- API storage paths are selected through environment variables and local defaults. They are documented local deployment controls, not user-supplied HTTP parameters.
- CORS allows only `http://localhost:3000` and `http://127.0.0.1:3000`; `allow_credentials=False`.
- RAG `top_k` is bounded with Pydantic `ge=1`, `le=20`.
- Tutor `top_k` is bounded with Pydantic `ge=1`, `le=20`.
- Tutor quiz `num_questions` is bounded with Pydantic `ge=1`, `le=10`.
- Zotero search clamps `limit` to `1..100`.
- Graph search and traversal are capped in service code:
  - search nodes limit capped to `1..100`
  - traversal depth capped to `1..3`
  - traversal limit capped to `1..200`

Accepted limitations:

- MVP has no authentication or authorization.
- Graph `depth` and `limit` are capped in service code but not declared as Pydantic bounds in the API signature. This is a low-risk future API hygiene improvement.
- Production CORS/host configuration is not implemented yet.
- JSON stores do not include locking or corruption recovery.

## RAG / Tutor / LLM Safety Audit

Result: PASS

Verified:

- Fake embedding provider is the default.
- Fake LLM provider is the default for tutor behavior.
- OpenAI-compatible chat and embedding providers are optional and read `OPENAI_API_KEY` from the environment.
- API keys are used only in outbound `Authorization` headers and are not returned by API responses.
- Empty RAG dataset returns `无法基于当前资料回答。` with no sources.
- Empty tutor request returns no-source refusal with no sources.
- Sourced RAG and sourced tutor responses return article sources.
- Tutor citation policy requires article chunk sources for substantive answers.
- Learning state is marked as personalization context and is not accepted as factual citation source.
- Graph node/edge sources and Zotero metadata can supplement, but not replace, article-source grounding.
- Tutor research mode is local-only and does not perform web search, paper download, crawler use, or Zotero writes.

Runtime smoke evidence:

```json
{
  "empty_rag_answer": "无法基于当前资料回答。",
  "empty_rag_sources": 0,
  "empty_tutor_refusal": "no_sources",
  "empty_tutor_sources": 0,
  "sourced_rag_sources": 2,
  "sourced_tutor_refusal": null,
  "sourced_tutor_sources": 2
}
```

## Zotero Privacy and Write Boundary Audit

Result: PASS

Verified:

- `SCIENTIFIC_SPACES_ZOTERO_PROVIDER` defaults to `fake`.
- `LocalZoteroProvider` is selected only when explicitly configured with `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=local`.
- Local provider uses GET requests.
- No `import-bibtex`, `import-ris`, connector save, attachment fetch, or Zotero write operation is implemented.
- Zotero status does not expose personal profile paths or attachment paths.
- Fake provider distinguishes Zotero `item_key` from `bibtex_key`.
- No-Zotero/local unavailable behavior is non-crashing and returns graceful status/search results.

Runtime smoke evidence:

```json
{
  "provider": "fake",
  "available": true,
  "read_only": true,
  "base_url": null,
  "version": "fixture",
  "error": null
}
```

## Persistence Security Audit

Result: PASS with accepted limitations

Verified:

- JSON stores default to `.local_data/scientific_spaces`.
- SQLite learning persistence is opt-in through `SCIENTIFIC_SPACES_LEARNING_BACKEND=sqlite`.
- SQLite database path is configured with `SCIENTIFIC_SPACES_DB_FILE`.
- SQLite schema initialization is deterministic and idempotent.
- SQLite tests use temporary paths.
- SQLite and JSON runtime files are ignored and not tracked.
- No external database is required to run tests.

Accepted limitations:

- `SCIENTIFIC_SPACES_DB_FILE` can point to any local filesystem path the process can write. This is an environment-level deployment control, not an HTTP input, and must follow the documented local data policy.
- JSON stores can be corrupted by interrupted writes and are not safe for production multi-user concurrency.
- SQLite improves local structure but is not a production multi-user database.

## Frontend Privacy Audit

Result: PASS

Verified:

- Frontend code contains no API keys or secret values.
- `NEXT_PUBLIC_API_BASE_URL` defaults to documented local backend URL `http://localhost:8000`.
- Frontend errors display application-level messages and HTTP status codes, not backend stack traces.
- React default escaping is used for user-controlled text.
- Markdown content is rendered with `react-markdown`; no `dangerouslySetInnerHTML` usage was found.
- Reading history is stored in browser localStorage and capped at 8 items.
- Notes, learning state, tutor sessions, graph, and Zotero links are stored through backend local stores, not committed frontend artifacts.

Accepted limitation:

- Browser localStorage reading history is local user activity data and should be treated as private by the user's browser/profile environment.

## Dependency / Supply Chain Audit

Result: PASS with backend audit tooling limitation

Backend:

```text
uv run --project backend --extra dev pytest -q
72 passed, 2 skipped in 3.51s
```

Backend dependency audit:

```text
uv run --project backend --extra dev pip-audit
error: Failed to spawn: `pip-audit`
Caused by: No such file or directory (os error 2)
```

`pip-audit` is not currently installed in the backend dev dependencies or local environment. This is a tooling limitation and should be addressed in a future dependency-audit hardening task.

Frontend:

```text
npm audit --audit-level=high
found 0 vulnerabilities
```

Frontend build:

```text
npm run build
Next.js 15.5.20 build completed successfully.
Generated routes: /, /articles, /articles/[id], /graph, /tutor, /zotero.
```

No high or critical frontend audit issue is actionable now.

## CI / Security Hygiene Audit

Result: PASS

Verified workflow:

- `.github/workflows/ci.yml`

Triggers:

- `pull_request`
- `push` to `main`
- `push` to `v*` tags
- `workflow_dispatch`

Jobs:

- Backend pytest
- Frontend build
- Docker compose smoke for `workflow_dispatch` and `v*` tag refs

Security hygiene:

- CI does not define or print secrets.
- CI does not require real API keys.
- CI uses fake/test provider defaults.
- CI does not upload runtime artifacts.
- Docker smoke is limited to manual/tag contexts and was covered by v1.0.0 release evidence.

Recent CI evidence:

- Manual `v1.0.0` release evidence run: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28931334219`
- Post-push docs run: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28931497404`

## Artifact Check

Result: PASS

Commands:

```text
git ls-files | grep -E '(^\.env$|\.sqlite$|\.sqlite3$|\.db$|\.pdf$|node_modules|\.local_data|knowledge_graph\.json|learning\.json|tutor.*\.json|zotero_links\.json|\.faiss$|embedding.*cache)' || true
```

Result:

- no output

Additional working-tree scan:

- no untracked non-ignored files
- no tracked `.env`, DB, PDF, trace/profile, FAISS/cache, embedding cache, node_modules, or local runtime data artifacts
- Python `__pycache__` files exist locally but are ignored and untracked

## Tests and Evidence

Evidence collected:

- `uv run --project backend --extra dev pytest -q`: `72 passed, 2 skipped in 3.51s`
- `npm run build`: PASS
- `npm audit --audit-level=high`: `found 0 vulnerabilities`
- `uv run --project backend --extra dev pip-audit`: unavailable, `pip-audit` executable missing
- `gitleaks`: unavailable
- grep/manual secrets audit: PASS
- runtime smoke with temporary local data: PASS

Runtime smoke summary:

```json
{
  "health": 200,
  "articles_total": 1,
  "graph_build_status": 200,
  "graph_nodes": 14,
  "learning_state_status": 200,
  "empty_rag_sources": 0,
  "sourced_rag_sources": 2,
  "empty_tutor_refusal": "no_sources",
  "sourced_tutor_sources": 2,
  "zotero_status": {
    "provider": "fake",
    "available": true,
    "read_only": true
  }
}
```

## Findings

Blockers:

- None.

Medium risks:

- MVP has no authentication or authorization and must not be deployed as public multi-user software.
- Local JSON and SQLite stores are not production multi-user persistence.
- Backend Python dependency audit tooling is not installed; dependency audit must be rerun after adding `pip-audit` or equivalent.

Low risks:

- Graph traversal parameters are capped in service code but not declared as API-level Pydantic bounds.
- Historical reports include local diagnostic/tool paths; these are not active runtime paths or secrets.
- Production CORS/host configuration is not yet implemented.
- Browser localStorage reading history contains local activity metadata.

Accepted limitations:

- Fake providers are safe defaults for tests, not production security controls.
- Real provider keys must be managed outside the repository.
- Zotero local API availability and metadata privacy depend on the user's local Zotero environment.
- Research mode is local-only and not a complete literature review.
- `docs/15_ACCEPTANCE.md` and `docs/31_MVP_BOUNDARY.md` remain absent documentation hygiene gaps.

## Actions Taken

- Created `SECURITY.md`.
- Created `docs/SECURITY_PRIVACY_BASELINE.md`.
- Added explicit `.gitignore` patterns for logs, traces, profiles, and `*.cache`.
- Added stronger `.env.example` comments for local-only placeholders and real-key handling.
- Added README security/privacy baseline summary.
- Updated `docs/00_PROJECT_STATE.md` with `P0-004 Security and Privacy Baseline: PASS`.

## Remaining Risks

- No authentication or authorization in the MVP.
- Local JSON/SQLite stores are not production multi-user storage.
- Real provider keys must be managed externally.
- localStorage reading history is a browser-local privacy caveat.
- Zotero local API availability and privacy depend on user environment.
- Dependency audit requires periodic rerun and backend audit tooling should be added.
- Production CORS/host/security headers remain future deployment-hardening work.

## Recommendation

A: Security/privacy baseline complete
