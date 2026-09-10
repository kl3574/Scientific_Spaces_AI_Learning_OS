# Scientific Spaces AI Learning OS

Scientific Spaces AI Learning OS is a local-first learning system for Scientific Spaces articles, combining a source pipeline, Reader, grounded RAG/Tutor, learning state, Zotero metadata links and a provenance-bearing knowledge graph.

## Current Status

Formal release: **v1.1.0**; v1.2 has no assigned release candidate.
P3-044 mode policy and offline regression are locally complete. The owner approved
all 12 items in the v3 affine reference packet; this approves reference content,
while real-model answer quality remains **NOT_RUN**.

- [Project state and verification boundaries](docs/00_PROJECT_STATE.md)
- [Current canonical task](docs/tasks/CURRENT_TASK.md)
- [v1.2 priorities and deferred work](docs/V1_2_ROADMAP.md)
- [v1.1.0 release evidence](docs/RELEASE_CI_EVIDENCE_v1.1.0.md) and [release notes](docs/RELEASE_NOTES_v1.1.0.md)

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

Requirements: Python `3.11` and `uv`. From the repository root:

```bash
uv run --project backend --extra dev pytest -q
uv run --project backend uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API listens at `http://localhost:8000`. Useful routes include:

- `GET /health`
- `GET /articles`: legacy unbounded list with optional `q`; original store order.
- `GET /v1.1/articles`: pagination, `q`, `category` and deterministic sorting; `page_size` defaults to 20 and is capped at 100.
- `GET /articles/{id}`: full Markdown; list endpoints return summaries.
- `POST /rag/query`, `GET /learning/stats`, `GET /zotero/status`
- `GET /graph`, `GET /graph/nodes` and bounded `GET /v1.1/graph/nodes`
- `POST /tutor/ask`, `POST /tutor/quiz`

Legacy, `/v1.1` and additive `/v1.2` contracts are described in
[API compatibility](docs/API_COMPATIBILITY_MIGRATION_REVISION.md).

## Frontend Setup

Requirements: Node.js `22` and npm. From the repository root:

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

The frontend listens at `http://localhost:3000`. Main routes are `/`,
`/library`, `/session`, `/articles`, `/articles/[id]`, `/references`,
`/zotero`, `/graph` and `/tutor`.

For a local production build:

```bash
npm --prefix frontend run build
npm --prefix frontend run start -- --hostname 127.0.0.1 --port 3000
```

See [deployment profiles](docs/PRODUCTION_DEPLOYMENT_PROFILE.md) for runtime
configuration and smoke checks. Public multi-user deployment is not implemented.

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
- `SCIENTIFIC_SPACES_REFERENCE_STORE`: validated Reference Store directory. Defaults to `.local_data/scientific_spaces/references/full-corpus/current`.
- `SCIENTIFIC_SPACES_REFERENCE_CONFIGURATION_FINGERPRINT`: optional secret-free expected build configuration fingerprint.
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
- `SCIENTIFIC_SPACES_TUTOR_MAX_CONTEXT_CHARS`: complete generation-input character ceiling, including task, question, evidence and JSON escaping; default `24000`.
- `OPENAI_API_KEY`: optional, only needed for OpenAI-compatible providers.
- `OPENAI_BASE_URL`: optional OpenAI-compatible base URL.
- `OPENAI_CHAT_MODEL`: optional chat model override.
- `OPENAI_EMBEDDING_MODEL`: optional embedding model override.
- `NEXT_PUBLIC_API_BASE_URL`: frontend API base URL, default `http://localhost:8000`.

Do not commit real `.env` files, API keys, Zotero library exports, or local runtime data.

Run the Reader against the completed local corpus without copying or modifying it:

```bash
SCIENTIFIC_SPACES_ARTICLE_STORE=.local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
SCIENTIFIC_SPACES_REFERENCE_STORE=.local_data/scientific_spaces/references/full-corpus/current \
  uv run --project backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The Article API reads that local store through two explicit contracts. Legacy `GET /articles` preserves the v1.0 response (`items`, `total`, `query`), original store order, and all matches. The Reader uses `GET /v1.1/articles`, where `page_size` defaults to `20` and is capped at `100`; this endpoint also supports `q`, `category`, and deterministic sorting. Both list endpoints return summaries only, and full Markdown content remains on `GET /articles/{id}`. The legacy `SCIENTIFIC_SPACES_ARTICLES_FILE` override remains supported and takes precedence when both variables are set.

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

## Structured Reference API

P3-007 serves the validated derived store through additive, bounded, read-only
endpoints:

- `GET /v1.2/references`
- `GET /v1.2/references/{reference_id}`
- `GET /v1.2/articles/{article_id}/references`
- `GET /v1.2/references/{reference_id}/zotero-candidates`
- `GET /v1.2/reference-summary`

The API never rebuilds on request. Missing, stale, or corrupt stores return a
bounded HTTP 503 state. Existing `/articles` and `/v1.1` contracts are
unchanged.

## Evaluation Harness

All ordinary examples below use synthetic data and fake/spy providers. They
measure contracts and retrieval/request observations, not real-model quality:

```bash
UV_OFFLINE=true uv run --project backend python scripts/eval/run_rag_tutor_eval.py
UV_OFFLINE=true uv run --project backend python scripts/eval/run_tutor_generation_eval.py
UV_OFFLINE=true uv run --project backend python scripts/eval/validate_tutor_review.py
UV_OFFLINE=true uv run --project backend python scripts/eval/observe_tutor_review.py \
  --output-dir eval_outputs/tutor_generation/review-observation-new-run
```

Use a new ignored observation directory for each run. The
[v3 review packet](backend/tests/fixtures/evaluation/tutor_generation/review_candidate_v3/review_package.md)
contains the two original synthetic Articles and 12 reference cases. Its
[human decision](docs/reviews/P3_044_AFFINE_V3_HUMAN_DECISION.json) is separate
from the frozen preparation manifest. These materials are development/regression
data, not an unseen holdout. Static validation and model review cannot grant
human approval. See the [review preparation report](docs/P3_044_AFFINE_REVIEW_PREPARATION_REPORT.md)
for exact scope, hashes and limitations.

For an existing local Article/RAG/Graph installation, the metadata-only
[full-corpus Tutor evaluator](scripts/eval/run_full_corpus_tutor_eval.py) reads
configured resources without fetching source content. Raw captures and outputs
belong under ignored `.local_data/`, `eval_outputs/` or `evaluation_outputs/`.

## Provider Evaluation Safety Harness

P3-004 provides an offline fake/dry-run harness for validating provider consent, budgets, bounded request envelopes, terminal errors, redaction, retention, and artifact safety:

```bash
uv run --project backend python scripts/eval/run_real_provider_eval.py \
  --provider fake \
  --case-set backend/tests/fixtures/evaluation/provider_cases.json \
  --dry-run \
  --output-dir .local_data/scientific_spaces/evaluation/real_provider/dry-run
```

Generated output remains under ignored `.local_data/`. Audit it with `scripts/eval/audit_real_provider_eval.py`; cleanup is dry-run by default through `scripts/eval/cleanup_real_provider_eval.py`. The harness does not authorize a real request, read credentials, or change fake product defaults. Evidence is recorded in `docs/P3_004_REAL_PROVIDER_EVALUATION_DESIGN_REPORT.md`.

## Structured Reference Pilot

Run the bounded, deterministic 75-Article pilot against the existing ignored local Article store:

```bash
uv run --project backend python scripts/references/run_reference_pilot.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --sample-size 75 \
  --output-dir .local_data/scientific_spaces/references/pilot \
  --no-network
```

The command is offline, accepts only 50-100 Articles, leaves the Article store unchanged, and writes its derived store under ignored `.local_data/`. It does not authorize a full-corpus build or private Zotero access.

## Structured Reference Full Corpus

The [full-corpus reference report](docs/P3_006_STRUCTURED_REFERENCE_FULL_CORPUS_REPORT.md)
records the exact historical input, hash-bound build command, checkpoint/resume,
atomic installation, provenance and idempotency checks. Runtime stores are local
and ignored. The historical reference review approved three pilot cases and
waived 61; it did not establish 64/64 completion or precision. This is separate
from the approved 12-case P3-044 affine packet.

## Full Corpus Pilot

Source acquisition is an explicit operation. A bounded initial command is:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py --limit 10 --delay-seconds 3
```

Larger batches require their approved input and source-pressure limits. The
[pilot CLI](scripts/corpus/run_full_corpus_pilot.py) and
[final corpus report](docs/P3_009_FULL_CORPUS_RUN_REPORT.md) retain the distinct
historical acquisition profiles; their past authorizations are not permission
to start another crawl. Operator seed files and all acquired content stay local.

## Incremental Blog PDF Sync

[The incremental sync command](scripts/zotero/update_latest_blog_pdfs.py) previews
official RSS metadata by default; `--write` explicitly applies an authorized
Article/PDF/Zotero delta. It validates content before atomic append and preserves
existing Articles. The [M1.4 report](docs/M1_4_INCREMENTAL_SOURCE_ZOTERO_SYNC_REPORT.md)
defines one PDF/zero HTML child readback and idempotency requirements.
It does not implicitly rebuild RAG, Graph or References.

## Incremental Derived Asset Refresh

[The offline refresh command](scripts/ops/refresh_derived_assets.py) is read-only
by default. `--execute` stages and validates RAG/Graph/Reference assets against
an exact Article-store fingerprint, creates a recoverable backup, and installs
the bundle transactionally. It uses fake providers, preserves Article content
and returns `no_op` for an unchanged installed bundle.
See the [refresh report](docs/P3_010_INCREMENTAL_DERIVED_ASSET_REFRESH_REPORT.md)
for exact input/hash arguments and rollback checks.

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

CI security and release provenance:

- Implementation report: `docs/P3_005_CI_SECURITY_PROVENANCE_REPORT.md`
- Security triage: `docs/CI_SECURITY_TRIAGE_SOP.md`
- Action pin updates: `docs/ACTION_PIN_UPDATE_SOP.md`
- SBOM verification: `docs/SBOM_VERIFICATION_SOP.md`
- Release provenance verification: `docs/RELEASE_PROVENANCE_VERIFICATION_SOP.md`
- Branch protection guidance: `docs/BRANCH_PROTECTION_GUIDANCE.md`

Run the local policy and scan gates from the repository root:

```bash
python scripts/security/check_workflow_policy.py
python scripts/security/validate_suppressions.py
python scripts/security/run_dependency_audit.py
python scripts/security/run_secret_audit.py
```

Dependency scanning uses trusted public advisory services. SBOM and release-evidence output is generated only in temporary storage and is not committed. These scans do not enable real Providers or authorize private-data access.

## Docker

```bash
docker compose up --build
```

The [compose profile](docker-compose.yml) exposes Backend
`http://localhost:8000/health` and Frontend `http://localhost:3000`.
Docker is optional locally; report an unavailable smoke check as NOT_RUN.

## Testing

From the repository root:

```bash
uv run --project backend --extra dev pytest -q
npm --prefix frontend run test:articles
npm --prefix frontend run test:references
npm --prefix frontend run test:tutor
npm --prefix frontend run test:graph
npm --prefix frontend run build
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

There is no generic `npm test` script. Product E2E uses task-owned loopback
FastAPI/Next.js services, temporary fixtures, fake providers, a production build
and locally installed Chromium. It blocks external requests and cleans up its
runtime. Do not reuse or stop a user's existing service to run the suite.

Browser/live/PDF tests are skipped by default; use `RUN_LIVE_TESTS=1` only for
explicit live-source diagnostics. Offline maintenance should set
`UV_OFFLINE=true` and `RUN_LIVE_TESTS=0` and report unavailable dependencies.

## CI

[GitHub Actions](.github/workflows/ci.yml) runs Backend, Frontend, Product E2E,
workflow policy, dependency audit, secret audit and SBOM validation on its
configured triggers. Docker and release-evidence jobs have separate tag/manual
conditions. A skipped job is not a passing check.

Release publishing remains manual; CI does not move tags or create Releases.
Exact-ref verification and evidence handling are documented in the
[release provenance SOP](docs/RELEASE_PROVENANCE_VERIFICATION_SOP.md).

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

An essential backup excludes Markdown, PDF, RAG, and Graph. A complete backup requires an explicit PDF choice because PDF libraries can be large:

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
uv run --project backend python scripts/corpus/materialize_local_library.py \
  --article-store-path .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/corpus/local_library

uv run --project backend python scripts/export/export_local_corpus_pdfs.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/corpus/pdf_library \
  --mode offline \
  --workers 2 \
  --resume

uv run --project backend python scripts/rag/build_full_corpus_index.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/rag/full_corpus \
  --provider fake

uv run --project backend python scripts/graph/build_full_corpus_graph.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/graph/full_corpus
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

## Documentation and Limitations

- [Project state](docs/00_PROJECT_STATE.md), [current task](docs/tasks/CURRENT_TASK.md) and [roadmap](docs/V1_2_ROADMAP.md)
- [M1 freeze](docs/M1_FINAL_FREEZE_REPORT.md), [v1.1 audit](docs/V1_1_RELEASE_READINESS_AUDIT.md) and [changelog](CHANGELOG.md)
- [Tutor implementation evidence](docs/P3_044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION_REPORT.md)

The product remains single-user and local-first. Real-model correctness and
teaching quality have not been established. Research mode does not perform
autonomous web research or claim a complete literature review. The existing
Reader and Graph incidents remain open as recorded in project state; unrelated
passing runs do not establish their repair. Future work is listed only in the
roadmap.
