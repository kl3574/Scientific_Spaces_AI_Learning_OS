# M5 Verification Report

# Current Status

| Item | Result | Evidence |
|---|---|---|
| M5 Implementation | PASS | Commit `f46ab8b72cb431b498d1e1f1c5bb641f40cbe466` is present on `main`. |
| M5 Verification | PASS | Provider, API, storage, frontend, regression, freeze, scope, and artifact checks passed. |
| M6 Readiness | A: Ready for M6 | Zotero metadata links are stable enough for a separate M6 Knowledge Graph milestone. |

This is a verification gate only. No M5 implementation code, frozen M1/M2/M3/M4 implementation code, M6 Knowledge Graph, or M7 AI Tutor functionality was changed by this gate.

Required context documents were read where present:

- `docs/00_PROJECT_STATE.md`
- `docs/M5_IMPLEMENTATION_REPORT.md`
- `docs/M4_VERIFICATION_REPORT.md`
- `docs/M3_VERIFICATION_REPORT.md`
- `docs/M2_VERIFICATION_REPORT.md`
- `docs/M1_FINAL_FREEZE_REPORT.md`
- `docs/04_DATA_MODEL.md`
- `docs/10_UI_SPEC.md`

Missing or renamed context recorded as documentation gaps, not verification blockers:

- `milestones/M5_ZOTERO_INTEGRATION.md` is absent.
- Repository contains `milestones/M5_ZOTERO.md`.
- `docs/15_ACCEPTANCE.md` is absent.
- `docs/31_MVP_BOUNDARY.md` is absent.

# Provider Verification

Implementation:

- `backend/app/zotero/provider.py`
- `backend/app/zotero/fake.py`
- `backend/app/zotero/local_api.py`
- `backend/app/zotero/models.py`

Result:

- PASS

Evidence:

- `ZoteroProvider` protocol defines:
  - `status()`
  - `search(query, limit)`
  - `get_item(item_key)`
  - `export_bibtex(item_keys)`
  - `list_collections()`
  - `list_tags()`
- `get_zotero_provider()` defaults to `FakeZoteroProvider`.
- `LocalZoteroProvider` is selected only when `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=local`.
- `LocalZoteroProvider` uses `GET` requests only.
- No Zotero library import, connector save, attachment fetch, or library write command is implemented.
- No personal Zotero profile path, API key, attachment path, or real library data is hardcoded in application code.
- `FakeZoteroProvider` distinguishes Zotero item key `ABCD1234` from BibTeX key `vaswani_attention_2017`.

No-Zotero behavior:

```text
provider: local
available: false
read_only: true
items: []
status code: 200
```

Local API helper status:

```text
base_url: http://127.0.0.1:23119
api_running: false
api_status: 503
connector_running: false
connector_status: 503
```

The helper also reported a local profile path, but the application endpoint does not expose that path.

# Status Verification

Endpoint:

- `GET /zotero/status`

Result:

- PASS

Fake provider runtime result:

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

Unavailable local provider result:

```json
{
  "provider": "local",
  "available": false,
  "read_only": true,
  "base_url": "http://127.0.0.1:9",
  "version": null
}
```

Privacy boundary:

- The status endpoint exposes provider type, availability, read-only mode, optional base URL, version, and error.
- It does not expose Zotero profile paths, attachment paths, API keys, or library data.

# Search and Item Verification

Endpoints:

- `GET /zotero/items?q=keyword`
- `GET /zotero/items/{item_key}`

Result:

- PASS

Search smoke:

```text
GET /zotero/items?q=attention
status: 200
total: 1
```

Returned metadata fields:

- `item_key`
- `bibtex_key`
- `title`
- `creators`
- `year`
- `item_type`
- `publication_title`
- `doi`
- `url`
- `abstract_note`
- `tags`
- `collections`
- `updated_at`

Item detail smoke:

```text
GET /zotero/items/ABCD1234
status: 200
item_key: ABCD1234
bibtex_key: vaswani_attention_2017
title: Attention Is All You Need
```

Missing item behavior:

```json
{
  "item": null
}
```

The missing item response is explicit and does not crash the API. A future M5.x revision may choose to convert this to `404`, but the current behavior is clear enough for the verification gate.

# BibTeX Export Verification

Endpoint:

- `POST /zotero/export/bibtex`

Result:

- PASS

Existing item smoke:

```json
{
  "bibtex": "@article{vaswani_attention_2017,...}",
  "item_count": 1
}
```

Verification:

- Fake provider exports BibTeX.
- `item_count` is correct for the tested existing item request.
- Export returns text in the API response and does not write a `.bib` file into the repository.
- No Zotero library write is performed.
- No large `references.bib` or real Zotero export is tracked.

Missing item behavior:

```json
{
  "bibtex": "",
  "item_count": 1
}
```

This is non-crashing but should be refined in a future M5.x revision because `item_count` currently reflects requested keys rather than exported entries when all requested keys are missing.

# Article-Zotero Link Verification

Endpoints:

- `GET /zotero/links/{article_id}`
- `POST /zotero/links/{article_id}`
- `DELETE /zotero/links/{article_id}/{item_key}`

Result:

- PASS

Create smoke:

```json
{
  "article_id": "attention-001",
  "zotero_item_key": "ABCD1234",
  "relation_type": "background",
  "note": "Background reading"
}
```

List smoke:

```text
GET /zotero/links/attention-001
status: 200
total: 1
linked item title: Attention Is All You Need
```

Duplicate behavior:

- Re-posting the same `article_id` and `item_key` updates the relation and note.
- `created_at` remains stable for the duplicate upsert.

Relation validation:

```text
relation_type=graph
status: 422
allowed values: related, cites, background
```

Delete smoke:

```text
DELETE /zotero/links/attention-001/ABCD1234
status: 204
GET after delete: {"items":[],"total":0}
```

Boundary checks:

- Links are stored in project-local JSON.
- Links are not written to Zotero Desktop.
- M1 Article schema is unchanged.
- M4 Learning model is unchanged.

# Storage Verification

Implementation:

- `backend/app/zotero/store.py`

Result:

- PASS

Storage path:

```text
.local_data/scientific_spaces/zotero_links.json
```

Environment isolation:

```text
SCIENTIFIC_SPACES_ZOTERO_FILE
SCIENTIFIC_SPACES_DATA_DIR
```

`.gitignore` coverage:

- `.local_data/`
- `backend/.local_data/`
- cache directories
- `.env`
- `node_modules`
- `frontend/.next/`

Artifact status:

- No real Zotero data is tracked.
- No real BibTeX library export is tracked.
- No Zotero attachment path is tracked.
- No local runtime Zotero link data is tracked.

Known storage risks:

- The local JSON store is not a multi-user production database.
- Corrupt JSON is not self-healed.
- Concurrent writes are not locked.

# Frontend Verification

Implementation:

- `frontend/src/app/zotero/page.tsx`
- `frontend/src/lib/zotero.ts`
- `frontend/src/components/ZoteroLibraryView.tsx`
- `frontend/src/components/ZoteroLinksPanel.tsx`
- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/components/ReaderShell.tsx`

Result:

- PASS

Build result:

```text
npm run build
✓ Compiled successfully
✓ Generating static pages (6/6)
```

Frontend smoke:

| Route | Result |
|---|---|
| `/` | `200` |
| `/articles` | `200` |
| `/articles/attention-001` | `200` |
| `/zotero` | `200` |

UI behavior verified by code inspection:

- `/zotero` displays provider status.
- `/zotero` supports metadata search.
- `/zotero` displays title, creators, year, item type, publication title, item key, BibTeX key, and abstract when available.
- `/zotero` supports BibTeX text export.
- Article Detail includes a "Related Papers" panel.
- Article Detail can search, link, unlink, select relation type, save a local note, list linked Zotero items, and export linked BibTeX.

Fallback behavior:

- If provider calls fail, frontend components show an error message rather than crashing.
- With the default fake provider, `/zotero` is usable without Zotero Desktop.

Forbidden UI scan:

- No Knowledge Graph UI.
- No citation graph UI.
- No AI literature review UI.
- No AI recommendation UI.
- No Zotero write/import UI.
- No AI Tutor UI.

# Regression Verification

Result:

- PASS

M2 Article API smoke:

```text
GET /articles
status: 200
total: 1
```

M3 RAG API smoke:

```text
POST /rag/query
status: 200
sources: present
```

M4 Learning API smoke:

```text
GET /learning/state      status: 200
GET /learning/bookmarks  status: 200
GET /learning/notes/{id} status: 200
GET /learning/sessions   status: 200
GET /learning/stats      status: 200
```

Regression test evidence is also covered by:

- `backend/tests/test_zotero_api.py::test_m2_m3_m4_regressions_remain_available`

# Freeze Protection

Result:

- PASS

Checked frozen M1 paths:

- `backend/app/crawler/`
- `backend/app/parser/`
- `backend/app/converter/`
- `backend/app/storage/`
- `backend/app/validation/`
- `backend/app/sync.py`
- M1 verification docs/milestone

Checked M2 frozen contracts:

- Article API
- Reader routes
- Search behavior
- Reading history boundary

Checked M3 frozen contracts:

- RAG API
- Citation policy
- No-source refusal
- Chunking / embedding / vector / LLM provider contracts

Checked M4 frozen contracts:

- Learning state
- Bookmarks
- Notes
- Sessions
- Stats
- local learning storage boundary

Git evidence:

```text
git diff --name-only HEAD -- <frozen paths>
no output
```

# Scope Leak Scan

Result:

- PASS

No M6 implementation detected:

- no Knowledge Graph implementation
- no graph database
- no graph node/edge model
- no graph extraction
- no citation graph
- no paper graph
- no article graph visualization

No M7 implementation detected:

- no AI Tutor
- no quiz generation
- no adaptive tutoring
- no explain/derive/research tutor modes
- no mastery prediction
- no autonomous research agent

No Zotero library write detected:

- `LocalZoteroProvider` uses `method="GET"` only.
- No import-bibtex/import-ris/connector-save operation is implemented.
- Link deletion deletes only local project links, not Zotero library items.

# Test Evidence

Backend tests:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
50 passed, 2 skipped in 3.43s
```

Frontend build:

```bash
cd frontend && npm run build
```

Result:

```text
✓ Compiled successfully
✓ Generating static pages (6/6)
```

Runtime smoke:

- backend Zotero status/search/item/export/link CRUD: PASS
- backend M2/M3/M4 regression smoke: PASS
- frontend `/`, `/articles`, `/articles/attention-001`, `/zotero`: PASS

Docker status:

```text
docker: command not found
```

Docker was not available in this environment. This is not a blocker because backend tests, frontend build, and non-Docker runtime smoke passed.

Forbidden artifact checks:

- no `.env`
- no API key
- no real Zotero library export
- no large `references.bib`
- no personal Zotero data
- no Zotero attachment paths
- no PDF
- no full HTML dump
- no images
- no FAISS index/cache
- no embedding cache
- no local runtime data
- no `node_modules`
- no trace/profile/cache artifact

# Known Risks

- Local Zotero Desktop API availability depends on the user's environment.
- Fake provider is intentionally small and is the default for tests.
- Local API provider is read-only by design.
- Real Zotero writes are intentionally not implemented.
- Project-local JSON link store is not multi-user production storage.
- Corrupt JSON and concurrent writes are not currently self-healed.
- Missing BibTeX export requests return empty BibTeX while `item_count` reflects requested keys; a future M5.x revision should consider adding `exported_count` or returning a clearer error for all-missing requests.

# M6 Readiness

M6 Readiness:

A: Ready for M6

Reason:

- M5 metadata integration is stable.
- Zotero item metadata and local Article-Zotero links are available as M6 inputs.
- Frozen M1/M2/M3/M4 contracts remain unchanged.
- No M6 or M7 functionality was implemented early.
