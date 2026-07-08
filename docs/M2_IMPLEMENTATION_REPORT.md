# M2 Implementation Report

## 1. Current Status

| Item | Status | Evidence |
|---|---|---|
| M0 Engineering Foundation | PASS | Existing backend, frontend, Docker, and CI foundation. |
| M1 Source Pipeline | PASS | M1 freeze report records stable Article output. |
| M1 Final Freeze | PASS | `docs/00_PROJECT_STATE.md` records `M1 Freeze Passed`. |
| M2 Scientific Reader | PASS | Article API, reader UI, search, and basic reading history implemented. |

This milestone implements only M2 Reader behavior. It does not implement RAG, embeddings, FAISS, LLM provider, AI chat, learning state, bookmarks, Zotero, knowledge graph, or AI tutor behavior.

## 2. Implemented Features

- Backend Article API reads the frozen M1 Article storage output.
- Frontend Dashboard shows project title, article count, recent articles, and recent reading history.
- Frontend Article List supports title and keyword search.
- Frontend Article Detail renders Markdown article content and metadata.
- Basic reading history is stored in browser `localStorage`.

## 3. API Contract

### `GET /articles`

Query parameters:

- `q`: optional string used for title/content keyword search.

Response:

```json
{
  "items": [
    {
      "id": "string",
      "title": "string",
      "url": "string",
      "metadata": {},
      "content_preview": "string"
    }
  ],
  "total": 1,
  "query": "string or null"
}
```

Empty dataset behavior:

- Returns `{"items": [], "total": 0, "query": null}` if no local M1 article file exists.

### `GET /articles/{id}`

Response:

```json
{
  "id": "string",
  "title": "string",
  "url": "string",
  "content": "markdown string",
  "metadata": {}
}
```

Missing article behavior:

- Returns `404` with `{"detail": "Article not found"}`.

Article storage path:

- Uses `SCIENTIFIC_SPACES_ARTICLES_FILE` when set.
- Otherwise reads `${SCIENTIFIC_SPACES_DATA_DIR:-.local_data/scientific_spaces}/articles.json`.

## 4. Frontend Pages

| Route | Purpose |
|---|---|
| `/` | Dashboard with article count, recent articles, and reading history. |
| `/articles` | Searchable Article List. |
| `/articles/[id]` | Article Detail with Markdown rendering and metadata. |

Runtime API base:

- `NEXT_PUBLIC_API_BASE_URL`
- Default: `http://localhost:8000`

## 5. Search Behavior

Search is implemented in the backend Article API.

- Title search: case-insensitive substring match against `title`.
- Keyword search: case-insensitive substring match against `content`.
- No embeddings, FAISS, LLM calls, vector search, or RAG behavior are used.

## 6. Reading History Behavior

Reading history is M2-basic only.

- Storage: frontend `localStorage`.
- Key: `scientific-spaces-reading-history-v1`.
- Fields: `id`, `title`, `url`, `last_read_at`.
- Maximum retained items: `8`.

Explicitly not implemented:

- mastery
- progress score
- quiz state
- bookmark system
- conversation history
- AI tutor state

## 7. Test Evidence

### Backend

Command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
28 passed, 2 skipped in 0.23s
```

Added backend coverage:

- `GET /articles`
- `GET /articles/{id}`
- title search
- content keyword search
- missing article `404`
- empty dataset behavior

### Frontend

Command:

```bash
cd frontend && npm run build
```

Result:

```text
✓ Compiled successfully
✓ Generating static pages (5/5)
```

Routes built:

- `/`
- `/articles`
- `/articles/[id]`

### Docker

Command:

```bash
docker compose build
```

Result:

```text
/bin/bash: line 1: docker: command not found
```

Docker verification was not completed because Docker is not installed in the current execution environment.

## 8. Known Risks

1. Runtime data dependency
   - The reader displays articles only when M1 Article storage data exists locally.
   - Empty storage returns an empty list instead of crashing.

2. Client-side API base
   - Browser requests default to `http://localhost:8000`.
   - Deployments should set `NEXT_PUBLIC_API_BASE_URL`.

3. Markdown rendering scope
   - Markdown rendering is sufficient for reader use but does not include RAG citation rendering or AI answer formatting.

4. Missing project boundary docs
   - `docs/15_ACCEPTANCE.md` and `docs/31_MVP_BOUNDARY.md` are still absent in this repository.
   - M2 scope was derived from `milestones/M2_READER_SYSTEM.md`, M1 freeze, UI spec, and the user's explicit constraints.

5. M1 freeze governance
   - M2 did not modify M1 RSS discovery, browser access, parser, converter, storage schema, sync flow, or verification standards.

## 9. M3 Readiness

M3 readiness result:

- M2 Reader is ready as a user-facing article browsing and reading layer.
- M3 should start only as a separate milestone task.
- M3 must add RAG, embedding, FAISS, LLM provider, and citations without back-editing frozen M1 code or overloading M2 reading history into M4 learning state.
