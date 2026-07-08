# M4 Implementation Report

## 1. Current Status

| Item | Status | Evidence |
|---|---|---|
| M0 Engineering Foundation | PASS | Existing backend/frontend foundation remains in place. |
| M1 Final Freeze | PASS | `docs/00_PROJECT_STATE.md` retains `M1 Freeze Passed`. |
| M2 Verification | PASS | `docs/00_PROJECT_STATE.md` retains `M2 Verification Passed`. |
| M3 Verification | PASS | `docs/00_PROJECT_STATE.md` retains `M3 Verification Passed`. |
| M4 Learning Management | PASS | Learning state, bookmarks, notes, sessions, stats, and frontend integration are implemented. |

This milestone implements basic learning management only. It does not implement Zotero, Knowledge Graph, AI Tutor, autonomous research agents, quiz generation, mastery prediction, spaced repetition, recommendation, or full learning analytics.

Required context note:

- The prompt requested `milestones/M4_LEARNING_MANAGEMENT.md`, but the repository contains `milestones/M4_LEARNING_SYSTEM.md`.
- `docs/15_ACCEPTANCE.md` and `docs/31_MVP_BOUNDARY.md` are absent and remain recorded as documentation gaps.

## 2. Implemented Features

- Basic reading state:
  - `unread`
  - `reading`
  - `completed`
- Bookmark/favorite support.
- User-written learning notes with CRUD.
- Basic learning session history with create/end/list.
- Dashboard learning statistics.
- Frontend integration for Dashboard, Article List, and Article Detail.
- M2 Article API regression coverage.
- M3 RAG API regression coverage.

## 3. Learning Data Model

Learning data is separate from the frozen M1 Article schema.

### Learning State

```text
LearningState
├── article_id
├── status: unread | reading | completed
├── last_read_at
├── completed_at
├── read_count
└── updated_at
```

### Bookmark

```text
Bookmark
├── article_id
├── title
├── url
└── created_at
```

### Learning Note

```text
LearningNote
├── note_id
├── article_id
├── content
├── created_at
└── updated_at
```

### Learning Session

```text
LearningSession
├── session_id
├── article_id
├── started_at
├── ended_at
├── duration_seconds
└── source: reader | rag
```

## 4. API Contract

New M4 endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/learning/state` | List stored learning states. |
| `GET` | `/learning/state/{article_id}` | Return state or default unread state. |
| `PUT` | `/learning/state/{article_id}` | Update reading status. |
| `GET` | `/learning/bookmarks` | List bookmarks. |
| `POST` | `/learning/bookmarks/{article_id}` | Add bookmark. |
| `DELETE` | `/learning/bookmarks/{article_id}` | Remove bookmark. |
| `GET` | `/learning/notes/{article_id}` | List notes for an article. |
| `POST` | `/learning/notes/{article_id}` | Create user-written note. |
| `PUT` | `/learning/notes/{note_id}` | Update note content. |
| `DELETE` | `/learning/notes/{note_id}` | Delete note. |
| `POST` | `/learning/sessions` | Create basic learning session. |
| `PUT` | `/learning/sessions/{session_id}/end` | End session and compute duration. |
| `GET` | `/learning/sessions` | List sessions. |
| `GET` | `/learning/stats` | Return dashboard learning stats. |

Existing contracts preserved:

- `GET /articles`
- `GET /articles?q=keyword`
- `GET /articles/{id}`
- `POST /rag/index`
- `POST /rag/query`
- M3 citation and no-source behavior

## 5. Frontend Integration

Updated frontend files:

- `frontend/src/lib/learning.ts`
- `frontend/src/components/DashboardView.tsx`
- `frontend/src/components/ArticleListView.tsx`
- `frontend/src/components/ArticleDetailView.tsx`

Dashboard now displays:

- total articles
- reading count
- completed count
- unread count
- bookmark count
- note count
- recent learning activity
- recent sessions

Article List now displays:

- reading status badge
- bookmark badge

Article Detail now supports:

- status buttons: `unread`, `reading`, `completed`
- bookmark toggle
- user-written notes: create, edit, delete
- lightweight session record with end action

No AI Tutor, Quiz, Knowledge Graph, Zotero, recommendation, or mastery UI was added.

## 6. Storage Strategy

Storage is a lightweight local JSON file, matching the existing project style used for M1 Article storage.

Implementation:

- `backend/app/learning/store.py`
- default path: `.local_data/scientific_spaces/learning.json`
- test override: `SCIENTIFIC_SPACES_LEARNING_FILE`
- shared data-dir override: `SCIENTIFIC_SPACES_DATA_DIR`

Storage shape:

```json
{
  "states": {},
  "bookmarks": {},
  "notes": {},
  "sessions": {}
}
```

The repository does not commit real user learning data.

## 7. Test Evidence

### Backend Tests

Command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
44 passed, 2 skipped in 0.68s
```

New backend test coverage:

- learning state default/read/update
- invalid learning status rejection
- bookmark add/list/delete
- notes CRUD
- session create/end/list
- stats endpoint
- M2 Article API regression
- M3 RAG API regression

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

Temporary fixtures were created under `/tmp/scientific-spaces-m4-smoke` and removed after testing.

Backend smoke:

- `GET /health`: PASS
- `GET /articles`: PASS
- `GET /learning/state/{article_id}`: PASS
- `PUT /learning/state/{article_id}`: PASS
- `POST /learning/bookmarks/{article_id}`: PASS
- `POST /learning/notes/{article_id}`: PASS
- `POST /learning/sessions`: PASS
- `PUT /learning/sessions/{session_id}/end`: PASS
- `GET /learning/stats`: PASS
- `POST /rag/index`: PASS
- `POST /rag/query`: PASS with non-empty sources

Frontend smoke:

- `GET /`: returned dashboard shell including project title and learning counters.
- `GET /articles`: returned article list shell.
- `GET /articles/attention-001`: returned article detail loading shell.

Docker:

```text
/bin/bash: line 1: docker: command not found
```

Docker smoke was not run because Docker is unavailable in the current environment. This is recorded as an environment limitation, not an M4 blocker, because backend tests, frontend build, and non-Docker runtime smoke passed.

## 8. Scope Boundary

Implemented:

- basic reading state
- bookmarks/favorites
- user-written notes
- learning session history
- dashboard counters

Not implemented:

- M5 Zotero integration
- M6 Knowledge Graph
- M7 AI Tutor
- autonomous research agent
- quiz generation
- mastery prediction model
- spaced repetition algorithm
- recommendation engine
- full learning analytics engine
- AI-generated notes
- Zotero annotations
- complete AI conversation history

Freeze protection result:

- M1 frozen paths: unchanged.
- M3 RAG/LLM/chunking/vector paths: unchanged.
- M2 Article API and M3 RAG regression tests pass.
- `backend/app/main.py` changed only to register the M4 router and allow `PUT`/`DELETE` CORS methods.
- M2 frontend components were extended for M4 learning controls without changing routes or removing Reader behavior.

## 9. Known Risks

1. JSON file persistence
   - The M4 store is intentionally lightweight.
   - Concurrent writes are not optimized and can be revisited if multi-user deployment becomes a requirement.

2. Article existence validation
   - Bookmarks use Article title/URL when the Article is available.
   - Missing Article data is handled without crashing, but strict foreign-key validation is deferred.

3. Frontend session creation
   - Article Detail creates a lightweight reader session when the article loads.
   - Development-mode React remount behavior may create duplicate local sessions; production smoke uses the built Next app.

4. Missing docs
   - `docs/15_ACCEPTANCE.md`, `docs/31_MVP_BOUNDARY.md`, and requested `milestones/M4_LEARNING_MANAGEMENT.md` are absent.
   - M4 scope was implemented from the explicit execution prompt plus existing `milestones/M4_LEARNING_SYSTEM.md`.

5. Docker unavailable locally
   - Docker verification remains environment-limited.

## 10. M5 Readiness

M5 readiness result:

- A: Ready for M5 planning

Reason:

- M4 learning state is separated from Article storage and RAG APIs.
- Reader, RAG, and learning APIs have regression coverage.
- No Zotero, Knowledge Graph, or AI Tutor behavior was implemented early.
