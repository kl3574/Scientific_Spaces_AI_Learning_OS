# Persistence Upgrade Plan

## Current Store Inventory

Current MVP store inventory:

| Milestone | Store | Current backend | Default path | Environment override |
|---|---|---|---|---|
| M1 | Article storage | JSON file | `.local_data/scientific_spaces/articles.json` | `SCIENTIFIC_SPACES_ARTICLES_FILE` |
| M4 | Learning state, bookmarks, notes, sessions | JSON file by default; SQLite opt-in | `.local_data/scientific_spaces/learning.json` or `.local_data/scientific_spaces/scientific_spaces.db` | `SCIENTIFIC_SPACES_LEARNING_FILE`, `SCIENTIFIC_SPACES_LEARNING_BACKEND`, `SCIENTIFIC_SPACES_DB_FILE` |
| M5 | Zotero article links | JSON file | `.local_data/scientific_spaces/zotero_links.json` | `SCIENTIFIC_SPACES_ZOTERO_FILE` |
| M6 | Knowledge Graph document | JSON file | `.local_data/scientific_spaces/knowledge_graph.json` | `SCIENTIFIC_SPACES_GRAPH_FILE` |
| M7 | Tutor sessions | JSON file | `.local_data/scientific_spaces/tutor_sessions.json` | `SCIENTIFIC_SPACES_TUTOR_FILE` |
| M3 | FAISS vector index | In-memory, rebuildable | None | None |

Shared runtime data root:

```text
SCIENTIFIC_SPACES_DATA_DIR=.local_data/scientific_spaces
```

All local runtime data remains ignored and must not be committed.

## Decision Summary

Decision record:

- `docs/ADR/0004-persistence-upgrade-strategy.md`

Decision:

- Adopt SQLite as the local structured persistence baseline for post-MVP user/project data.
- Keep JSON as the default compatibility backend.
- Add SQLite as an opt-in first migration slice for M4 Learning persistence.
- Keep FAISS/vector indexes rebuildable and ephemeral.
- Keep Article, Zotero links, Graph, and Tutor session storage unchanged until later migration phases.

## First Migration Slice

First migration slice:

- M4 Learning store.

Why Learning store was selected:

- It is structured and stable.
- It stores high-value local user data.
- Its API contract is already covered by tests.
- It does not alter M1 Article ingestion.
- It does not change M3 RAG citation/no-source behavior.
- It does not change M5 Zotero read-only provider boundaries.
- It does not change M6 graph provenance/evidence behavior.
- It does not change M7 tutor citation/no-source policy.

Backend selection:

```text
SCIENTIFIC_SPACES_LEARNING_BACKEND=json
SCIENTIFIC_SPACES_LEARNING_BACKEND=sqlite
```

Default:

```text
json
```

SQLite is explicitly opt-in for v1.1.

## SQLite Schema

SQLite file:

```text
SCIENTIFIC_SPACES_DB_FILE=.local_data/scientific_spaces/scientific_spaces.db
```

Tables:

```text
learning_state
bookmarks
notes
sessions
```

`learning_state`:

- `article_id TEXT PRIMARY KEY`
- `status TEXT NOT NULL`
- `last_read_at TEXT`
- `completed_at TEXT`
- `read_count INTEGER NOT NULL DEFAULT 0`
- `updated_at TEXT`

`bookmarks`:

- `article_id TEXT PRIMARY KEY`
- `title TEXT NOT NULL`
- `url TEXT NOT NULL`
- `created_at TEXT NOT NULL`

`notes`:

- `note_id TEXT PRIMARY KEY`
- `article_id TEXT NOT NULL`
- `content TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

Indexes:

- `idx_notes_article_id_created_at`

`sessions`:

- `session_id TEXT PRIMARY KEY`
- `article_id TEXT NOT NULL`
- `started_at TEXT NOT NULL`
- `ended_at TEXT`
- `duration_seconds INTEGER`
- `source TEXT NOT NULL`

Indexes:

- `idx_sessions_started_at`

Schema initialization is deterministic and idempotent through:

- `backend/app/persistence/sqlite.py`

## Configuration

New environment variables:

```text
SCIENTIFIC_SPACES_DB_FILE=.local_data/scientific_spaces/scientific_spaces.db
SCIENTIFIC_SPACES_LEARNING_BACKEND=json
```

Existing JSON environment variables retained:

```text
SCIENTIFIC_SPACES_DATA_DIR=.local_data/scientific_spaces
SCIENTIFIC_SPACES_LEARNING_FILE=.local_data/scientific_spaces/learning.json
```

Backend behavior:

- `SCIENTIFIC_SPACES_LEARNING_BACKEND=json` uses the legacy JSON `LearningStore`.
- `SCIENTIFIC_SPACES_LEARNING_BACKEND=sqlite` uses `LearningSQLiteStore`.
- Invalid backend values fail clearly at backend runtime.

## Migration Procedure

No automatic migration runs at startup. Create and verify an essential backup, then migrate the existing JSON data with explicit paths:

```bash
uv run --project backend python scripts/persistence/migrate_learning_json_to_sqlite.py \
  --json-path .local_data/scientific_spaces/learning.json \
  --sqlite-path .local_data/scientific_spaces/scientific_spaces.db
```

The migration preserves state, bookmark, note, and session primary keys, timestamps, `read_count`, status, and content. It builds a staged SQLite database and atomically replaces the target only after validation and insertion complete. The source JSON is never modified. Repeating the command replaces the target with the same source snapshot and does not grow record counts.

After verifying the command result, opt in:

```text
SCIENTIFIC_SPACES_DB_FILE=.local_data/scientific_spaces/scientific_spaces.db
SCIENTIFIC_SPACES_LEARNING_BACKEND=sqlite
```

Verify through the unchanged Learning API:

```text
GET /learning/stats
GET /learning/state
GET /learning/bookmarks
GET /learning/sessions
```

## Rollback Procedure

If SQLite contains newer writes, export them before switching back:

```bash
uv run --project backend python scripts/persistence/migrate_learning_sqlite_to_json.py \
  --sqlite-path .local_data/scientific_spaces/scientific_spaces.db \
  --json-path .local_data/scientific_spaces/learning.json
```

The export stages and atomically replaces the JSON target. Verify the resulting JSON and then configure the JSON backend:

```text
SCIENTIFIC_SPACES_LEARNING_BACKEND=json
```

If using an explicit JSON file:

```text
SCIENTIFIC_SPACES_LEARNING_FILE=.local_data/scientific_spaces/learning.json
```

Rollback does not require deleting the SQLite file. A backend setting change alone does not transfer writes between backends. SQLite and JSON files are runtime artifacts and are ignored by git. General backup and isolated restore remain available through `scripts/ops/backup_local_data.py` and `scripts/ops/restore_local_backup.py`.

## Test Evidence

Targeted migration/SQLite/config tests:

```text
uv run --project backend --extra dev pytest -q backend/tests/test_learning_migration.py backend/tests/test_persistence_sqlite.py backend/tests/test_learning_sqlite_store.py
16 passed
```

These tests cover an exact JSON -> SQLite -> JSON round trip, repeat execution, explicit-path CLIs, strict numeric/identity preservation, and injected atomic-replace failures in both directions.

Learning API regression tests:

```text
uv run --project backend --extra dev pytest -q backend/tests/test_learning_api.py
8 passed in 0.29s
```

Full backend test suite:

```text
uv run --project backend --extra dev pytest -q
469 passed, 3 skipped
```

Frontend build:

```text
npm run build
Next.js 15.5.20 build completed successfully.
Generated routes: /, /articles, /articles/[id], /graph, /tutor, /zotero.
```

Runtime smoke with temporary SQLite database:

```json
{
  "health": 200,
  "learning_stats_initial": 200,
  "learning_state_put": 200,
  "learning_state_get": "completed",
  "learning_note_post": 200,
  "learning_notes_total": 1,
  "articles": 1,
  "rag_index": 200,
  "rag_sources": 1,
  "zotero_status": 200,
  "graph_build": 200,
  "graph_nodes": 12,
  "tutor_sources": 1,
  "db_exists_during_smoke": true
}
```

Smoke used a temporary directory and did not write runtime data to the repository.

## Remaining Stores

M1 Article storage:

- Keep JSON for now.
- Revisit after controlled full-corpus processing and content-quality reporting.

M5 Zotero links:

- Recommended next SQLite migration candidate.
- Preserve read-only Zotero provider boundary.

M6 Knowledge Graph:

- Keep JSON for now.
- Reassess after graph scaling and provenance UX work.
- Future options include SQLite tables or a graph database, depending on scale.

M7 Tutor sessions:

- Migrate after Learning and Zotero links.
- Keep tutor sessions separate from M4 learning sessions.

M3 FAISS/vector index:

- Keep ephemeral and rebuildable.
- Do not commit FAISS indexes or embedding caches.

## Risks

- JSON and SQLite learning backends can diverge if an operator changes the backend without running the explicit migration/export command.
- SQLite files require explicit backup discipline.
- SQLite is not a production multi-user database.
- Concurrent writes are improved by SQLite transactions but still require deployment-level policy.
- Future Postgres migration requires a repository adapter and schema migration plan.
- Automatic startup migration remains intentionally disabled; operators retain an explicit backup and verification gate.
