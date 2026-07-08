# M2 Verification Report

## Current Status

| Item | Result | Evidence |
|---|---|---|
| M2 Implementation | PASS | M2 commit `99dab130d8789c55d55f1b3287fd3db3b6a37eb1` is present on `main`. |
| M2 Verification | PASS | API contract, frontend build, runtime smoke, search boundary, reading history boundary, and scope scans passed. |
| M3 Readiness | A: Ready for M3 | M2 reader is stable enough for a separate M3 RAG task. |

This is a verification gate only. No M2 implementation code, frozen M1 pipeline code, or M3/M4-M7 functionality was changed by this gate.

## API Verification

Verified endpoints:

- `GET /articles`
- `GET /articles?q=keyword`
- `GET /articles/{id}`

### Contract

`GET /articles` returns:

- `items`
- `total`
- `query`

Each item includes:

- `id`
- `title`
- `url`
- `metadata`
- `content_preview`

Each list item intentionally excludes full `content`.

`GET /articles/{id}` returns:

- `id`
- `title`
- `url`
- `content`
- `metadata`

### Empty Dataset Behavior

Verified with a missing local Article file:

```json
{
  "items": [],
  "total": 0,
  "query": null
}
```

The API does not crash when local M1 article storage is absent.

### Fixture Data Behavior

Verified with a temporary fixture Article file outside the repository:

```json
{
  "list_status": 200,
  "list_total": 2,
  "list_fields": ["content_preview", "id", "metadata", "title", "url"],
  "list_has_content_field": false,
  "title_search_ids": ["attention-001"],
  "keyword_search_ids": ["matrix-002"],
  "detail_status": 200,
  "detail_fields": ["content", "id", "metadata", "title", "url"],
  "detail_contains_markdown": true,
  "missing_status": 404,
  "missing_detail": "Article not found"
}
```

### Article Schema

M2 reads the frozen M1 `Article` shape and does not change it:

- `id`
- `title`
- `url`
- `content`
- `metadata`

## Frontend Verification

Verified routes:

- `/`
- `/articles`
- `/articles/[id]`

Frontend implementation:

- Dashboard: `frontend/src/components/DashboardView.tsx`
- Article List: `frontend/src/components/ArticleListView.tsx`
- Article Detail: `frontend/src/components/ArticleDetailView.tsx`

Build result:

```text
npm run build
✓ Compiled successfully
✓ Generating static pages (5/5)
```

Built routes:

- `/`
- `/articles`
- `/articles/[id]`

Runtime smoke result:

| Check | Result |
|---|---|
| `GET http://localhost:8000/health` | `{"status":"ok"}` |
| `GET http://localhost:8000/articles` | `{"items":[],"total":0,"query":null}` |
| `GET http://localhost:3000/` contains project title | PASS |
| `GET http://localhost:3000/articles` renders list route | PASS |
| `GET http://localhost:3000/articles/fixture-id` renders detail route shell | PASS |

Runtime note:

- An initial `/` smoke check returned `500` because the running Next dev server had a stale React Client Manifest after `.next` was removed during verification cleanup.
- Restarting the dev server resolved it.
- This was classified as a local dev-server state issue, not an M2 implementation blocker, because production build passed and a fresh dev server served the route.

Frontend scope check:

- Chinese titles/content are represented in fixtures and API responses.
- Article Detail uses Markdown rendering through `react-markdown`.
- No AI Chat or RAG UI is present.

## Search Verification

Search behavior is implemented in `backend/app/services/article_reader.py`.

Verified behavior:

- Title search: `q=Attention` returns `attention-001`.
- Keyword search: `q=泰勒` returns `matrix-002`.

Boundary check:

- Search is substring matching over `title` and `content`.
- No embedding code was found.
- No FAISS code was found.
- No LLM provider or AI Chat code was found.
- No vector search code was found.

## Reading History Verification

Implementation:

- `frontend/src/lib/readingHistory.ts`
- Storage mechanism: browser `localStorage`
- Storage key: `scientific-spaces-reading-history-v1`

Recorded fields:

- `id`
- `title`
- `url`
- `last_read_at`

Behavior:

- `ArticleDetailView` calls `recordReading()` after an article loads.
- Dashboard and Article Detail display recent reading items.
- History is capped at 8 items.

Scope boundary:

- No mastery state.
- No progress score.
- No bookmark system.
- No quiz state.
- No conversation history.
- No AI tutor state.

## M1 Freeze Protection

Frozen M1 paths checked from M1 freeze commit `c4b90f15e210bc89089b90d57a34a06577651b9c` to current `HEAD`:

- `backend/app/crawler/`
- `backend/app/parser/`
- `backend/app/converter/`
- `backend/app/storage/`
- `backend/app/sync.py`
- `backend/app/validation/`
- `docs/M1_VERIFICATION_REPORT.md`
- `milestones/M1_SOURCE_PIPELINE.md`

Result:

- PASS

No frozen M1 implementation module or M1 verification standard changed during M2.

M1.x revision candidates:

- None found during this verification.

## Scope Leak Scan

Scanned:

- `backend/`
- `frontend/`

Blocked scope checked:

- M3: RAG, embedding, FAISS, LLM Provider, AI Chat, vector search
- M4: Learning Management, mastery, progress score, bookmark, quiz, conversation history
- M5: Zotero
- M6: Knowledge Graph
- M7: AI Tutor

Result:

- PASS

Only M2 reading-history terms were found in the frontend localStorage helper and reader components. No M3/M4-M7 implementation code was found.

## Test Evidence

### Backend Pytest

Command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
28 passed, 2 skipped in 0.25s
```

### Frontend Build

Command:

```bash
cd frontend && npm run build
```

Result:

```text
✓ Compiled successfully
✓ Generating static pages (5/5)
```

### Runtime Smoke

Command summary:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/articles
curl -fsS http://localhost:3000/
curl -fsS http://localhost:3000/articles
curl -fsS http://localhost:3000/articles/fixture-id
```

Result:

- PASS after restarting the local Next dev server.

### Docker

Command:

```bash
docker --version
```

Result:

```text
/bin/bash: line 1: docker: command not found
```

Docker verification was not completed because Docker is not installed in the current environment. This is recorded as an environment limitation, not an M2 blocker, because backend tests, frontend build, and non-Docker runtime smoke passed.

### Artifact Check

No repository PDF, image, trace, zip, `.env`, `node_modules`, cache, or large article-data artifact was staged by this verification gate.

Existing HTML files are small committed parser fixtures under `backend/tests/fixtures/`.

## Known Risks

1. Docker unavailable locally
   - Docker smoke could not run in this environment.

2. Runtime data dependency
   - Full reader content requires M1 Article storage data to exist locally.
   - Empty dataset behavior is verified and returns an empty list.

3. Local dev server cache state
   - Removing `.next` while `next dev` is running can produce a stale manifest error.
   - Restarting the dev server resolves it.

4. Missing acceptance/boundary docs
   - `docs/15_ACCEPTANCE.md` and `docs/31_MVP_BOUNDARY.md` remain absent.
   - Verification used `milestones/M2_READER_SYSTEM.md`, M1 freeze report, data model, UI spec, and explicit task constraints.

## M3 Readiness

A: Ready for M3

Reason:

- Article API contract is stable for M2.
- Frontend reader routes build and serve.
- Search remains basic title/content keyword search.
- Reading history remains local and limited to recent reads with `last_read_at`.
- Frozen M1 pipeline was not modified.
- No M3/M4-M7 scope leak was found.
