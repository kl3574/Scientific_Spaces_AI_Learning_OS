# Scientific Spaces AI Learning OS

Scientific Spaces AI Learning OS is a local-first learning system for Scientific Spaces articles. The MVP combines a source pipeline, reader, grounded RAG assistant, learning state, Zotero metadata links, a knowledge graph, and a citation-grounded AI research tutor.

## Current Status

- Version: `v1.0.0`
- Phase: `MVP Complete`
- Status: `Scientific Spaces AI Learning OS MVP complete`
- Candidate: `v1.1.0` (`Release Readiness: BLOCKED`; not released)
- Latest gate: `P2-007 v1.1 Release Readiness Audit: BLOCKED`

Release-readiness evidence is recorded in `docs/POST_MVP_RELEASE_AUDIT.md`.

Post-MVP corpus processing planning is recorded in `docs/FULL_CORPUS_PROCESSING_PLAN.md`.

Bounded full-corpus pilot evidence is recorded in `docs/FULL_CORPUS_PILOT_REPORT.md`.

Medium-batch 100-article planning is recorded in `docs/MEDIUM_BATCH_100_ARTICLES_PLAN.md`.

Full corpus execution planning is recorded in `docs/FULL_CORPUS_EXECUTION_PLAN.md`.

Cumulative 200-article batch evidence is recorded in `docs/CUMULATIVE_200_ARTICLES_REPORT.md`.

Seed year metadata enrichment evidence is recorded in `docs/SEED_YEAR_METADATA_ENRICHMENT_REPORT.md`.

Year metadata source decision is recorded in `docs/P1_010_YEAR_METADATA_SOURCE_DECISION.md`.

Cumulative 1000-article batch evidence is recorded in `docs/CUMULATIVE_1000_ARTICLES_REPORT.md`.

Full corpus final batch planning is recorded in `docs/FULL_CORPUS_FINAL_BATCH_PLAN.md`.

Full corpus completion evidence is recorded in `docs/FULL_CORPUS_COMPLETION_REPORT.md`.

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
- `GET /articles` (v1.0-compatible unbounded list; optional `q` only)
- `GET /v1.1/articles` (bounded pagination, filters, and sorting)
- `POST /rag/query`
- `GET /learning/stats`
- `GET /zotero/status`
- `GET /graph`
- `GET /graph/nodes` (v1.0-compatible bounded search)
- `GET /v1.1/graph/nodes` (full-corpus pagination and filters)
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
- `SCIENTIFIC_SPACES_ARTICLE_STORE`: preferred full-corpus Reader override for an existing Article JSON store.
- `SCIENTIFIC_SPACES_ARTICLES_FILE`: override Article storage file.
- `SCIENTIFIC_SPACES_LEARNING_FILE`: override learning-state storage file.
- `SCIENTIFIC_SPACES_ZOTERO_FILE`: override Zotero link storage file.
- `SCIENTIFIC_SPACES_GRAPH_FILE`: override graph storage file.
- `SCIENTIFIC_SPACES_TUTOR_FILE`: override tutor session storage file.
- `SCIENTIFIC_SPACES_ZOTERO_PROVIDER`: `fake` by default; set `local` to use the local Zotero API.
- `SCIENTIFIC_SPACES_ZOTERO_BASE_URL`: local Zotero API URL, default `http://127.0.0.1:23119`.
- `SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER`: `fake` by default; set `openai` for OpenAI-compatible chat.
- `SCIENTIFIC_SPACES_RAG_INDEX_DIR`: optional persisted RAG index used by full-corpus Tutor retrieval.
- `SCIENTIFIC_SPACES_TUTOR_MAX_SOURCE_ARTICLES`: maximum selected Articles per Tutor response, default `6`.
- `SCIENTIFIC_SPACES_TUTOR_MAX_CHUNKS`: maximum selected Article chunks, default `10`.
- `SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_NODES`: maximum explicit Graph nodes, hard-capped at `20`.
- `SCIENTIFIC_SPACES_TUTOR_MAX_GRAPH_EDGES`: maximum explicit Graph edges, hard-capped at `30`.
- `SCIENTIFIC_SPACES_TUTOR_MAX_CONTEXT_CHARS`: selected generation-context ceiling, default `24000`.
- `OPENAI_API_KEY`: optional, only needed for OpenAI-compatible providers.
- `OPENAI_BASE_URL`: optional OpenAI-compatible base URL.
- `OPENAI_CHAT_MODEL`: optional chat model override.
- `OPENAI_EMBEDDING_MODEL`: optional embedding model override.
- `NEXT_PUBLIC_API_BASE_URL`: frontend API base URL, default `http://localhost:8000`.

Do not commit real `.env` files, API keys, Zotero library exports, or local runtime data.

Run the Reader against the completed local corpus without copying or modifying it:

```bash
SCIENTIFIC_SPACES_ARTICLE_STORE=.local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The Article API reads that local store through two explicit contracts. Legacy `GET /articles` preserves the v1.0 response (`items`, `total`, `query`), original store order, and all matches. The Reader uses `GET /v1.1/articles`, where `page_size` defaults to `20` and is capped at `100`; this endpoint also supports `q`, `category`, and deterministic sorting. Both list endpoints return summaries only, and full Markdown content remains on `GET /articles/{id}`. The legacy `SCIENTIFIC_SPACES_ARTICLES_FILE` override remains supported and takes precedence when both variables are set.

## Deployment Profiles

Deployment profile details are recorded in `docs/PRODUCTION_DEPLOYMENT_PROFILE.md`.

Local development:

```bash
uv run --project backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Local production-like run:

```bash
uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend
npm run build
npm run start -- --hostname 127.0.0.1 --port 3000
```

Smoke checklist:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:3000/
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Seed year metadata enrichment defaults to no live fetch and writes ignored runtime output:

```bash
uv run --project backend python scripts/corpus/run_seed_year_enrichment.py \
  --seed-file /path/to/article_list.json \
  --archive-url https://spaces.ac.cn/content.html \
  --output-dir .local_data/scientific_spaces/corpus/inventory \
  --no-live-fetch
```

Docker compose remains available for local or CI smoke where Docker is installed:

```bash
docker compose up --build
```

Production cloud deployment is not implemented in this MVP. Before real production use, add auth/authz, HTTPS, secret management, managed storage, CORS allowlists, backup/restore, monitoring, and rate limiting.

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

## Evaluation Harness

The deterministic RAG/Tutor evaluation harness lives under `backend/app/evaluation/` with fixed fixtures in `backend/tests/fixtures/evaluation/`.

Run the structural baseline:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

The default harness uses fake providers only. It does not require a real API key, web access, Zotero Desktop, or runtime article downloads. Optional JSON output must be written under ignored `eval_outputs/` or `evaluation_outputs/` paths.

Run the metadata-only 42-case Tutor evaluation against existing local resources:

```bash
uv run --project backend python scripts/eval/run_full_corpus_tutor_eval.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --rag-index-dir .local_data/scientific_spaces/rag/full_corpus \
  --graph-dir .local_data/scientific_spaces/graph/full_corpus \
  --provider fake
```

The command reads existing local Article, RAG, and Graph resources without fetching source content. Runtime output is aggregate-only and belongs under ignored `.local_data/scientific_spaces/evaluation/tutor_full_corpus/`.

## Full Corpus Pilot

Run the bounded full-corpus pilot:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py --limit 10 --delay-seconds 3
```

The default smoke command is intentionally small. Staged cumulative import phases are audited separately; the current bounded pilot cap is 1000, runs with concurrency `1`, writes runtime output under ignored `.local_data/`, and must not be used as an unbounded full crawl.

Run the audited cumulative 400-article batch:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 400 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

The seed file is operator-local runtime input and must not be committed. Do not reduce the 400-batch delay below 8 seconds or increase concurrency.

Run the audited cumulative 700-article batch:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 700 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Do not reduce the 700-batch delay below 8 seconds or increase concurrency.

Run the audited cumulative 1000-article batch:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 1000 \
  --delay-seconds 8 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Refresh the ignored local Markdown library after a successful cumulative batch:

```bash
uv run --project backend python scripts/corpus/materialize_local_library.py \
  --article-store-path .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/corpus/local_library
```

Do not reduce the 1000-batch delay below 8 seconds or increase concurrency. The next 1000 -> 1326 expansion requires a separate final-batch planning gate before execution.

Run the audited all-importable final completion batch:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json \
  --delay-seconds 8 \
  --complete-all-seed
```

The final completion mode processes the approved canonical seed set and imports all safely importable Articles. Non-importable legacy or parser-quality candidates are classified under ignored runtime output. Do not reduce the delay below 8 seconds, increase concurrency, commit the seed file, or commit runtime corpus data.

Run the full seed inventory dry-run without fetching article bodies:

```bash
uv run --project backend python scripts/corpus/run_seed_inventory.py \
  --seed-file /path/to/article_list.json \
  --output-dir .local_data/scientific_spaces/corpus/inventory
```

The inventory dry-run reads seed metadata only and writes ignored runtime summary output.

## Full Corpus RAG Index

Build the deterministic local index from the completed 1311-Article store:

```bash
uv run --project backend python scripts/rag/build_full_corpus_index.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/rag/full_corpus \
  --provider fake \
  --rebuild
```

The command validates the strict 1311-Article input contract, computes a deterministic corpus fingerprint, audits Markdown-structure chunks, and atomically writes the FAISS index plus source metadata under ignored `.local_data/`. Repeating the command with an unchanged, integrity-checked corpus is a no-op.

Run the explicit full-corpus retrieval suite:

```bash
uv run --project backend python scripts/eval/run_full_corpus_rag_eval.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --index-dir .local_data/scientific_spaces/rag/full_corpus
```

Both commands use the deterministic fake embedding provider by default, require no API key, and perform no source fetch or web access. The build command's optional real-provider path requires `--provider openai --allow-real-provider`, a local `OPENAI_API_KEY`, and a non-CI environment; it is not part of the P2-001 PASS baseline.

## Offline Local PDF Export

The optional PDF workflow derives A4 PDFs from the existing local Article store. It does not fetch Scientific Spaces pages or remote images, and it never replaces `Article.content` as the Reader/RAG source.

Requirements:

- frontend dependencies installed under `frontend/node_modules`
- Playwright Chromium installed locally
- Poppler tools `pdfinfo` and `pdftotext`

Run the deterministic 20-Article representative pilot:

```bash
uv run --project backend python scripts/export/export_local_corpus_pdfs.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/corpus/pdf_library \
  --mode offline \
  --limit 20 \
  --workers 2 \
  --rebuild
```

Export or resume the full local corpus:

```bash
uv run --project backend python scripts/export/export_local_corpus_pdfs.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/corpus/pdf_library \
  --mode offline \
  --workers 4 \
  --resume
```

Offline workers are bounded to `1..4` and default to `2`. Each worker owns a persistent Node renderer and Chromium page; manifest checkpoints are written atomically by the main thread. Resume verifies source/template/renderer identity and the PDF SHA-256 digest. Remote images become local placeholders; displayed HTTP(S) URLs omit credentials, query strings, and fragments, while local or forbidden schemes are redacted. PDFs, manifests, reports, rendered HTML, and browser cache remain under ignored `.local_data/`.

Source print-parity is not part of the batch PASS path. The CLI validates the `source-probe` safety envelope: explicit opt-in, one worker, a maximum of 10 Articles, at least 8 seconds delay, and a separate output directory. P2-005 does not implement the online provider, so the batch command intentionally refuses to execute that optional path.

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

## Local Data Operations

The post-corpus runtime is local-only. Its source-of-truth assets are:

| Tier | Assets | Policy |
|---|---|---|
| Tier 1 | Article store, completion classifications, corpus progress, Learning/bookmarks/notes/sessions, Zotero links, Tutor sessions, other user-created data | Back up first; never remove through routine cleanup |
| Tier 2 | Markdown, PDF, RAG chunks/FAISS, Knowledge Graph, manifests, benchmark/evaluation output | Rebuildable from Tier 1; include only when the backup profile requires it |
| Tier 3 | Browser cache/profile, rendered HTML, traces, transient logs and staging directories | Safe cleanup candidates after review |

Primary local paths:

- Article source of truth: `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json`
- Completion classifications: `.local_data/scientific_spaces/corpus/pilot/completion_classifications.json`
- Learning/user data: `.local_data/scientific_spaces/learning.json` or `scientific_spaces.db`
- Markdown: `.local_data/scientific_spaces/corpus/local_library/`
- PDF: `.local_data/scientific_spaces/corpus/pdf_library/`
- RAG: `.local_data/scientific_spaces/rag/full_corpus/`
- Graph: `.local_data/scientific_spaces/graph/full_corpus/`
- Unified ignored manifest: `.local_data/scientific_spaces/operations/local_data_manifest.json`

### Learning JSON and SQLite migration

JSON remains the default Learning backend. Before changing backends, create and verify an essential backup. Migrate an existing JSON store to an explicit SQLite target with:

```bash
uv run --project backend python scripts/persistence/migrate_learning_json_to_sqlite.py \
  --json-path .local_data/scientific_spaces/learning.json \
  --sqlite-path .local_data/scientific_spaces/scientific_spaces.db
```

The command stages a complete database and atomically replaces the target only after all states, bookmarks, notes, and sessions are valid. Repeating it produces the same record identities and counts. It does not modify the source JSON.

To export SQLite writes back to JSON before switching the backend to `json`:

```bash
uv run --project backend python scripts/persistence/migrate_learning_sqlite_to_json.py \
  --sqlite-path .local_data/scientific_spaces/scientific_spaces.db \
  --json-path .local_data/scientific_spaces/learning.json
```

This export is also staged and atomically replaces its target. A configuration switch alone is not a data rollback: export first when SQLite contains newer writes, verify the JSON result, then set `SCIENTIFIC_SPACES_LEARNING_BACKEND=json`. The general `scripts/ops/backup_local_data.py` and `scripts/ops/restore_local_backup.py` commands remain the executable backup/restore path for both Learning formats.

Audit the inventory and write the deterministic manifest. Read-only hashing uses four workers by default:

```bash
uv run --project backend python scripts/ops/audit_local_data.py \
  --data-root .local_data/scientific_spaces \
  --workers 4
```

Create and verify the default essential backup outside the source root:

```bash
uv run --project backend python scripts/ops/backup_local_data.py \
  --data-root .local_data/scientific_spaces \
  --output-dir /path/on/another/disk/scientific-spaces-backups \
  --profile essential \
  --verify \
  --workers 4
```

An essential backup excludes Markdown, PDF, RAG, and Graph. A complete backup requires an explicit PDF choice because the current PDF library is approximately 830 MB:

```bash
uv run --project backend python scripts/ops/backup_local_data.py \
  --data-root .local_data/scientific_spaces \
  --output-dir /path/on/another/disk/scientific-spaces-backups \
  --profile complete \
  --exclude-pdf \
  --verify
```

Use `--include-pdf` instead only when the destination has enough capacity. Backups are private local archives, are created with user-only permissions where supported, never upload automatically, and exclude `.env`, keys, profiles, traces, caches, and logs by default. No application-specific encryption is provided; encrypted/off-site backup remains a separate operational decision.

Verify an existing archive and restore only into an isolated empty directory:

```bash
uv run --project backend python scripts/ops/verify_local_backup.py \
  --backup /path/to/scientific-spaces-essential-*.zip \
  --workers 4

uv run --project backend python scripts/ops/restore_local_backup.py \
  --backup /path/to/scientific-spaces-essential-*.zip \
  --target-dir /tmp/scientific-spaces-restore-check \
  --protected-data-root .local_data/scientific_spaces \
  --verify \
  --workers 4
```

Check source/derived fingerprints, integrity, runtime configuration, and disk capacity:

```bash
uv run --project backend python scripts/ops/check_local_system.py \
  --data-root .local_data/scientific_spaces \
  --workers 4
```

Cleanup is a dry-run unless `--execute` is supplied. `all-derived` additionally requires `--confirm-derived-delete`; no command can delete the full data root or Tier 1 assets:

```bash
uv run --project backend python scripts/ops/cleanup_local_data.py \
  --data-root .local_data/scientific_spaces \
  --category temp \
  --category logs \
  --category browser-cache
```

Derived artifact rebuild commands are explicit and never run from the health checker:

```bash
uv run --project backend python scripts/corpus/materialize_local_library.py
uv run --project backend python scripts/export/export_local_corpus_pdfs.py
uv run --project backend python scripts/rag/build_full_corpus_index.py
uv run --project backend python scripts/graph/build_full_corpus_graph.py
```

Keep at least twice the current local-data size free for a complete backup and isolated restore. PDF rebuilds also require free space comparable to the PDF library.

> **Destructive Git warning:** `git clean -fdX` deletes ignored data. In this repository that includes the Article corpus, Markdown library, PDF library, RAG index, Knowledge Graph, unified manifest, and all other `.local_data` state. Create and verify an essential backup before running it.

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
- `docs/POST_CORPUS_HARDENING_RECOVERY_REPORT.md`
- `docs/V1_1_RELEASE_READINESS_AUDIT.md`
- `docs/API_COMPATIBILITY_MIGRATION_REVISION.md`
- `docs/RELEASE_NOTES_v1.1.0_DRAFT.md`
- `docs/V1_1_RELEASE_CHECKLIST.md`
- `CHANGELOG.md`

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
