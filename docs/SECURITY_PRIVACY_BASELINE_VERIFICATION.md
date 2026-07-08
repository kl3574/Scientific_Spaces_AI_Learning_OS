# Security and Privacy Baseline Verification

## Current Status

- P0-004 Baseline: PASS
- Verification: PASS
- Recommendation: A: Security/privacy baseline verified
- Verification date: 2026-07-08
- Verified baseline commit: `39413df448749bbe6ff85eba69cbe3a81d56683e`

This verification gate audited the P0-004 security/privacy baseline. It did not implement new features, auth/authz, dependency upgrades, release changes, or M1-M7 contract changes.

## Security Policy Verification

Result: PASS

`SECURITY.md` contains the required sections:

- Supported versions
- Reporting vulnerabilities
- Security model
- Secrets policy
- Local data policy
- AI grounding policy
- Zotero privacy boundary
- Known limitations
- Responsible use note

The policy clearly states that the MVP is local-first and single-user, has no authentication or authorization, uses fake providers by default, keeps real provider keys outside git, and treats local runtime data as private artifacts.

## Baseline Report Verification

Result: PASS

`docs/SECURITY_PRIVACY_BASELINE.md` contains the required sections:

- Current Status
- Threat Model Summary
- Secrets and Env Audit
- Local Data and Privacy Audit
- Backend API Security Audit
- RAG / Tutor / LLM Safety Audit
- Zotero Privacy and Write Boundary Audit
- Persistence Security Audit
- Frontend Privacy Audit
- Dependency / Supply Chain Audit
- CI / Security Hygiene Audit
- Artifact Check
- Tests and Evidence
- Findings
- Actions Taken
- Remaining Risks
- Recommendation

Baseline recommendation:

```text
A: Security/privacy baseline complete
```

## Secrets and Env Verification

Result: PASS

Commands and evidence:

```text
git status --short
```

No local modifications were present before verification edits.

```text
git ls-files | grep -E '(^\.env$|\.env\.local|\.env\.production)' || true
```

Result: no tracked `.env`, `.env.local`, or `.env.production` files.

```text
git grep -n "sk-" -- . ':!frontend/package-lock.json' ':!backend/uv.lock' || true
```

Result: no real key match. The only match after P0-004 is the baseline report line documenting the scan command itself.

Keyword scans for `OPENAI_API_KEY`, `api_key`, `password`, and `token` found only expected placeholder, documentation, and code references:

- `.env.example` leaves `OPENAI_API_KEY=` blank.
- README documents optional provider environment variables.
- backend provider code reads `OPENAI_API_KEY` from environment.
- backend provider code uses the key only in outbound `Authorization` headers.
- math placeholder and embedding tokenization variables are not secrets.
- `SECURITY.md` uses `tokens` only in security policy text.

Path scan:

```text
git grep -n "/Users/\|/home/" -- . ':!backend/tests/fixtures/*' ':!frontend/package-lock.json' ':!backend/uv.lock' || true
```

Only historical diagnostic/tool paths were found in docs:

- `docs/M1_PDF_EXPORT_EVALUATION.md`
- `docs/M5_IMPLEMENTATION_REPORT.md`

These are not active runtime paths or secrets.

Tooling:

- `gitleaks`: unavailable in the current environment.
- This limitation is documented in `docs/SECURITY_PRIVACY_BASELINE.md` and is not a blocker because grep/manual audit found no committed secrets.

## Artifact and Privacy Verification

Result: PASS

Artifact scan:

```text
git ls-files | grep -E '(\.sqlite$|\.sqlite3$|\.db$|\.pdf$|node_modules|\.local_data|knowledge_graph\.json|learning\.json|tutor.*\.json|zotero.*\.json|\.trace|\.prof|\.cache)' || true
```

Result: no tracked runtime/private artifacts.

Untracked scan:

```text
git ls-files -o --exclude-standard
```

Result: no untracked non-ignored files.

`.gitignore` covers:

- `.env`
- `.env.*`
- `!.env.example`
- `.local_data/`
- `*.db`
- `*.sqlite`
- `*.sqlite3`
- `*.log`
- `*.trace`
- `*.prof`
- `*.cache`
- `node_modules/`
- Python caches
- Next.js/build artifacts

No runtime JSON, SQLite DB, learning notes/state data, tutor sessions, Zotero exports, graph runtime data, FAISS/cache, embedding cache, PDF, HTML dump, images, logs, traces, profiles, or `node_modules` artifacts are committed.

## Backend Security Boundary Verification

Result: PASS with accepted limitations

Checked:

- `backend/app/main.py`
- `backend/app/api/`
- `backend/app/rag/`
- `backend/app/tutor/`
- `backend/app/zotero/`
- `backend/app/graph/`
- `backend/app/persistence/`

Verification:

- No `subprocess`, `os.system`, `Popen`, or `shell=True` usage was found in backend application code.
- External fetch paths are limited to known subsystems:
  - M1 crawler/browser/PDF export paths
  - optional OpenAI-compatible LLM/embedding providers
  - optional local Zotero API provider
- No uncontrolled external URL fetch was found in RAG/Tutor product paths.
- No API key is returned in responses.
- CORS remains local frontend only with `allow_credentials=False`.
- RAG `top_k` is bounded by Pydantic `ge=1`, `le=20`.
- Tutor `top_k` is bounded by Pydantic `ge=1`, `le=20`.
- Tutor quiz `num_questions` is bounded by Pydantic `ge=1`, `le=10`.
- Zotero search clamps `limit` to `1..100`.
- Graph service caps search/traversal:
  - node search limit `1..100`
  - graph traversal depth `1..3`
  - traversal limit `1..200`
- MVP no-auth/no-authz status is explicitly recorded as an accepted limitation, not production readiness.

Accepted limitation:

- Graph `depth` and `limit` caps are enforced in service code but not declared as Pydantic API bounds.

## RAG / Tutor / LLM Safety Verification

Result: PASS

Verification:

- `FakeEmbeddingProvider` remains the default embedding provider.
- `FakeLLMProvider` remains the default RAG/tutor test provider.
- OpenAI-compatible providers are env-gated through `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and model variables.
- Tests do not require a real API key.
- Empty RAG returns `无法基于当前资料回答。` with no sources.
- Empty tutor answer returns `refusal_reason="no_sources"` with no sources.
- Sourced RAG and tutor responses return article sources.
- Tutor citation policy requires at least one `article_chunk` source for substantive answers.
- Learning state remains personalization context and is not accepted as a factual citation source.
- Graph node/edge evidence and Zotero metadata are supplemental and are not disguised as article chunk sources.
- Tutor research mode does not call Playwright, crawlers, web search, requests/httpx, paper downloads, or Zotero write APIs.

Runtime smoke evidence:

```json
{
  "rag_empty_answer": "无法基于当前资料回答。",
  "rag_empty_sources": 0,
  "rag_sourced_sources": 2,
  "tutor_empty_refusal": "no_sources",
  "tutor_empty_sources": 0,
  "tutor_sourced_sources": 2
}
```

## Zotero Boundary Verification

Result: PASS

Verification:

- Local Zotero provider is env-gated by `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=local`.
- Default provider remains fake.
- `LocalZoteroProvider` uses GET requests.
- No `import-bibtex`, `import-ris`, connector save, attachment fetch, or Zotero library write operation is implemented.
- Business API link endpoints write only local project link metadata through `ZoteroLinkStore`; they do not write to Zotero.
- Zotero status does not expose attachment paths or personal profile paths.
- No-Zotero behavior remains graceful.

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

## Persistence Security Verification

Result: PASS

Verification:

- `SCIENTIFIC_SPACES_DB_FILE` is documented in README, `.env.example`, `docs/PERSISTENCE_UPGRADE_PLAN.md`, and `docs/ADR/0004-persistence-upgrade-strategy.md`.
- SQLite database runtime files are ignored by `.gitignore`.
- SQLite schema initialization is deterministic and idempotent.
- SQLite store uses parameterized SQL.
- JSON remains the default compatibility backend through `SCIENTIFIC_SPACES_LEARNING_BACKEND=json`.
- SQLite remains opt-in through `SCIENTIFIC_SPACES_LEARNING_BACKEND=sqlite`.
- Backend regression tests cover SQLite config/store behavior.
- No DB file is committed.
- Local JSON/SQLite stores are documented as not production multi-user storage.

P0-002 behavior was not modified by P0-004. The P0-004 commit touched only:

- `.env.example`
- `.gitignore`
- `README.md`
- `SECURITY.md`
- `docs/00_PROJECT_STATE.md`
- `docs/SECURITY_PRIVACY_BASELINE.md`

## Frontend Privacy Verification

Result: PASS

Verification:

- Frontend contains no API keys or secrets.
- `NEXT_PUBLIC_API_BASE_URL` defaults to documented local backend URL.
- Browser reading history uses localStorage key `scientific-spaces-reading-history-v1`.
- README and `SECURITY.md` document localStorage reading history as private local activity data.
- No `dangerouslySetInnerHTML` usage was found.
- Frontend errors are application-level messages/statuses, not backend stack traces.

## Dependency / Supply Chain Verification

Result: PASS with accepted backend tooling limitation

Frontend dependency audit:

```text
npm audit --audit-level=high
found 0 vulnerabilities
```

Backend dependency audit:

```text
uv run --project backend --extra dev pip-audit
error: Failed to spawn: `pip-audit`
Caused by: No such file or directory (os error 2)
```

`pip-audit` is unavailable in the current environment and not installed as a backend dev dependency. This is documented as a tooling limitation and does not block verification because backend tests pass, no known critical issue surfaced in the current audit, and the baseline records the need for periodic backend dependency audit.

No dependency upgrades or new feature dependencies were introduced.

## CI / Security Hygiene Verification

Result: PASS

Checked workflow:

- `.github/workflows/ci.yml`

Verification:

- CI does not define repository secrets or provider keys.
- CI runs backend pytest and frontend build with fake/test defaults.
- CI does not upload runtime artifacts.
- CI triggers remain:
  - `pull_request`
  - `push` to `main`
  - `push` to `v*` tags
  - `workflow_dispatch`
- Docker compose smoke remains limited to manual `workflow_dispatch` and `v*` tag refs.
- CI hardening documentation matches workflow behavior.

Latest P0-004 baseline CI evidence:

- Run: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28931844273`
- Conclusion: PASS

## Regression Test Evidence

Backend:

```text
uv run --project backend --extra dev pytest -q
72 passed, 2 skipped in 3.52s
```

Frontend:

```text
npm run build
Next.js 15.5.20 build completed successfully.
Generated routes: /, /articles, /articles/[id], /graph, /tutor, /zotero.
```

Dependency audit:

```text
npm audit --audit-level=high
found 0 vulnerabilities
```

Backend dependency audit tooling:

```text
uv run --project backend --extra dev pip-audit
error: Failed to spawn: `pip-audit`
Caused by: No such file or directory (os error 2)
```

Secret scan tooling:

```text
command -v gitleaks
```

Result: unavailable.

Runtime smoke with temporary local data:

```json
{
  "health": 200,
  "articles": 1,
  "learning_stats": 200,
  "graph_before_build": 200,
  "graph_build": 200,
  "graph_nodes": 14,
  "rag_empty_answer": "无法基于当前资料回答。",
  "rag_empty_sources": 0,
  "rag_sourced_sources": 2,
  "tutor_empty_refusal": "no_sources",
  "tutor_empty_sources": 0,
  "tutor_sourced_sources": 2,
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

- No authentication or authorization; public/multi-user deployment remains blocked.
- Local JSON and SQLite stores are not production multi-user persistence.
- Backend `pip-audit`/equivalent dependency audit tooling is unavailable.

Low risks:

- Graph traversal caps are service-level rather than API-schema-level.
- Historical diagnostic docs include local paths that are not active runtime paths or secrets.
- Production CORS/host/security-header hardening remains future deployment work.
- Browser localStorage reading history contains local activity metadata.

Accepted limitations:

- `gitleaks` unavailable locally; grep/manual audit completed.
- `pip-audit` unavailable locally; npm high-level audit completed and backend tests passed.
- Fake providers are safe testing defaults, not production security controls.
- Real provider keys must be managed externally.
- Zotero privacy depends on the user's local Zotero environment when the local provider is enabled.

## Frozen Contract Verification

Result: PASS

P0-004 did not modify backend feature code, frontend feature code, M1-M7 frozen contracts, or P0-002 persistence behavior.

Evidence:

```text
git show --name-only --oneline --no-renames 39413df448749bbe6ff85eba69cbe3a81d56683e
39413df docs: add security and privacy baseline
.env.example
.gitignore
README.md
SECURITY.md
docs/00_PROJECT_STATE.md
docs/SECURITY_PRIVACY_BASELINE.md
```

## Final Recommendation

A: Security/privacy baseline verified
