# ADR 0004: Persistence Upgrade Strategy

## Context

Scientific Spaces AI Learning OS v1.0.0 is a local-first MVP. The current persistence baseline is intentionally lightweight:

- M1 Article storage uses project-local JSON.
- M4 Learning state, bookmarks, notes, and sessions use project-local JSON.
- M5 Zotero article links use project-local JSON.
- M6 Knowledge Graph output uses project-local JSON.
- M7 Tutor sessions use project-local JSON.
- M3 FAISS vector search is in-memory and rebuildable from Article content.
- Fake providers are the default for tests and local development.
- Runtime data lives under `.local_data/scientific_spaces` unless overridden by environment variables.
- `.gitignore` excludes local runtime data, cache directories, dependency directories, generated browser artifacts, and local `.env` files.

This baseline is acceptable for the MVP, but the post-MVP roadmap requires a structured persistence direction before broader corpus processing, richer evaluation, or production deployment hardening.

## Problem

JSON stores create post-MVP operational risks:

- Concurrent writes can overwrite data.
- Corrupted JSON is not self-healed.
- Querying is weak and requires full-file reads.
- Schema migration is implicit and hard to audit.
- Multi-user deployment is not viable.
- Backup and restore expectations are ambiguous.
- Analytics, reporting, and larger data sets are difficult to support.

The persistence upgrade must not break existing M1-M7 API contracts, must not require external services for tests, and must not submit runtime databases or real user data to git.

## Options Considered

### 1. Keep JSON Stores

Pros:

- Lowest immediate risk.
- No new persistence code.
- Existing tests already pass.

Cons:

- Preserves concurrency and corruption risks.
- Does not create a migration path.
- Does not improve queryability or schema evolution.

### 2. SQLite Local Persistence

Pros:

- Uses the Python standard library through `sqlite3`.
- Works without external services.
- Supports structured schema, indexes, transactions, and portable local files.
- Fits the local-first MVP shape.
- Can be isolated in tests with temporary database files.

Cons:

- Still not a full multi-user production database.
- File backup and concurrency rules must be documented.
- Future Postgres migration still needs an adapter boundary.

### 3. Postgres First

Pros:

- Stronger production deployment target.
- Better multi-user and concurrent-write posture.
- Better operational tooling.

Cons:

- Requires an external service for local development and CI.
- Expands deployment surface before the product has a persistence abstraction.
- Increases post-MVP complexity too early.

### 4. Repository Abstraction With Phased Migration

Pros:

- Allows JSON, SQLite, and future Postgres backends behind stable interfaces.
- Reduces API contract churn.
- Supports one store at a time.

Cons:

- Adds adapter maintenance cost.
- Dual backends can diverge without shared regression tests.

### 5. Hybrid SQLite plus Rebuildable Ephemeral Indexes

Pros:

- Stores structured user/project data in SQLite.
- Keeps FAISS/vector indexes rebuildable from Article content.
- Avoids committing generated vector/cache artifacts.

Cons:

- Requires clear documentation about what is durable and what is rebuildable.
- Future large-corpus runs may require a stronger article and index persistence decision.

## Decision

Adopt a SQLite-backed repository layer for structured local project/user data, starting as an opt-in backend.

The first migration slice is M4 Learning persistence:

- Learning state.
- Bookmarks.
- Notes.
- Reading sessions.

The default backend remains JSON for compatibility:

```text
SCIENTIFIC_SPACES_LEARNING_BACKEND=json
```

SQLite is enabled explicitly:

```text
SCIENTIFIC_SPACES_LEARNING_BACKEND=sqlite
SCIENTIFIC_SPACES_DB_FILE=.local_data/scientific_spaces/scientific_spaces.db
```

M3 FAISS remains rebuildable and ephemeral.

M6 graph storage remains JSON until graph scale requires a database or graph database decision.

M5 Zotero links are the next structured-data migration candidate.

Article storage remains stable until full-corpus processing creates a clear need for database-backed article storage.

## Consequences

Positive consequences:

- Establishes a concrete structured persistence direction.
- Keeps tests local and external-service-free.
- Keeps existing API contracts stable.
- Allows gradual migration store by store.
- Creates a safe rollback path through the JSON backend.

Costs and risks:

- Two learning backends must remain behaviorally aligned.
- SQLite files need backup guidance.
- SQLite improves local durability but is not a production multi-user storage solution.
- Future Postgres support still needs a repository adapter and migration plan.
- Query/schema changes must be covered by tests.

## Migration Plan

### Phase 1: Learning Store SQLite Migration

- Add shared persistence config.
- Add SQLite schema initialization.
- Add `LearningSQLiteStore`.
- Keep JSON `LearningStore`.
- Select backend with `SCIENTIFIC_SPACES_LEARNING_BACKEND=json|sqlite`.
- Keep JSON as default for compatibility.

### Phase 2: Zotero Links SQLite Migration

- Migrate project-local Zotero article links.
- Keep Zotero provider read-only.
- Preserve article-to-Zotero API contracts.

### Phase 3: Tutor Sessions SQLite Migration

- Migrate tutor session summaries and turns.
- Preserve M7 citation/no-source behavior.
- Keep tutor sessions separate from M4 learning sessions.

### Phase 4: Graph Persistence Decision

- Reassess JSON, SQLite, or a graph database after large-graph scaling work.
- Keep graph provenance and edge evidence contracts intact.

### Phase 5: Article Corpus Storage Decision

- Reassess Article JSON storage after controlled full-corpus processing.
- Do not change M1 source pipeline behavior without an explicit M1.x revision task.

## Rollback Plan

SQLite learning persistence is opt-in. Rollback is configuration-only:

```text
SCIENTIFIC_SPACES_LEARNING_BACKEND=json
```

Existing JSON store variables remain supported:

```text
SCIENTIFIC_SPACES_LEARNING_FILE=.local_data/scientific_spaces/learning.json
SCIENTIFIC_SPACES_DATA_DIR=.local_data/scientific_spaces
```

No automatic migration runs at startup. Runtime SQLite files are not committed. If SQLite data must be backed up, copy the configured `SCIENTIFIC_SPACES_DB_FILE` outside the repository or into an ignored local backup path.

## Acceptance Criteria

- ADR exists and records the persistence decision.
- Current stores are inventoried.
- SQLite config supports `SCIENTIFIC_SPACES_DB_FILE`.
- Learning backend config supports `SCIENTIFIC_SPACES_LEARNING_BACKEND=json|sqlite`.
- SQLite schema initialization is deterministic and idempotent.
- Learning SQLite store supports state, bookmarks, notes, sessions, and note counts.
- JSON learning backend remains the default.
- Existing Learning API contract remains unchanged.
- Backend tests pass.
- Frontend build passes.
- No runtime database, `.env`, cache, generated index, or real user data is committed.
