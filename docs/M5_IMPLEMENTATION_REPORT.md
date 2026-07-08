# M5 Implementation Report

## 1. Current Status

| Item | Status | Evidence |
|---|---|---|
| M0 Engineering Foundation | PASS | Existing backend/frontend foundation remains in place. |
| M1 Final Freeze | PASS | `docs/00_PROJECT_STATE.md` retains `M1 Freeze Passed`. |
| M2 Verification | PASS | `docs/00_PROJECT_STATE.md` retains `M2 Verification Passed`. |
| M3 Verification | PASS | `docs/00_PROJECT_STATE.md` retains `M3 Verification Passed`. |
| M4 Verification | PASS | `docs/00_PROJECT_STATE.md` retains `M4 Verification Passed`. |
| M5 Zotero Integration | PASS | Zotero provider, metadata API, article links, frontend library page, and Article Detail paper links are implemented. |

This milestone implements Zotero metadata and library integration only. It does not implement Knowledge Graph, citation graph analysis, paper graph, RAG over Zotero papers, AI literature review, AI Tutor, autonomous research agents, or Zotero library writes.

Required context note:

- The prompt requested `milestones/M5_ZOTERO_INTEGRATION.md`, but the repository contains `milestones/M5_ZOTERO.md`.
- `docs/15_ACCEPTANCE.md` and `docs/31_MVP_BOUNDARY.md` are absent and remain recorded as documentation gaps.

## 2. Implemented Features

- Read-only Zotero provider abstraction.
- Fake provider for local development, CI, and environments without Zotero Desktop.
- Optional local Zotero Desktop API provider.
- Zotero status/readiness endpoint.
- Zotero item metadata search endpoint.
- Zotero item metadata detail endpoint.
- BibTeX export endpoint.
- Article-to-Zotero item link CRUD in a project-local store.
- Frontend `/zotero` library search page.
- Article Detail related papers panel.
- Regression coverage for M2 Article API, M3 RAG API, and M4 Learning API boundaries.

## 3. Zotero Provider Design

Provider interface:

```text
ZoteroProvider
├── status()
├── search(query, limit)
├── get_item(item_key)
├── export_bibtex(item_keys)
├── list_collections()
└── list_tags()
```

Provider implementations:

| Provider | Purpose | Read-only | Default |
|---|---|---|---|
| `FakeZoteroProvider` | Deterministic fixture provider for tests and development. | Yes | Yes |
| `LocalZoteroProvider` | Optional Zotero Desktop local API provider. | Yes | No |

Runtime selection:

```text
SCIENTIFIC_SPACES_ZOTERO_PROVIDER=fake | local
SCIENTIFIC_SPACES_ZOTERO_BASE_URL=http://127.0.0.1:23119
```

Default behavior is `fake`, so the application works when Zotero Desktop is not installed or not running. The local API provider is enabled only through environment configuration and does not write to the user's Zotero library.

## 4. Zotero Data Model

M5 does not modify the frozen M1 Article schema.

Article remains:

```text
Article
├── id
├── title
├── url
├── content
└── metadata
```

Zotero item metadata:

```text
ZoteroItem
├── item_key
├── bibtex_key
├── title
├── creators
├── year
├── item_type
├── publication_title
├── doi
├── url
├── abstract_note
├── tags
├── collections
└── updated_at
```

Lightweight article association:

```text
ZoteroArticleLink
├── article_id
├── zotero_item_key
├── relation_type: related | cites | background
├── created_at
└── note
```

`item_key` is the Zotero item identifier. `bibtex_key` is the citation key used in BibTeX output. They are intentionally separate fields and are covered by provider/API tests.

## 5. API Contract

New M5 endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/zotero/status` | Return provider status and read-only mode. |
| `GET` | `/zotero/items?q=keyword` | Search Zotero metadata. |
| `GET` | `/zotero/items/{item_key}` | Return one Zotero item, or `null` when missing. |
| `POST` | `/zotero/export/bibtex` | Export BibTeX for selected item keys. |
| `GET` | `/zotero/links/{article_id}` | List linked Zotero items for an article. |
| `POST` | `/zotero/links/{article_id}` | Create or update a local article-to-Zotero link. |
| `DELETE` | `/zotero/links/{article_id}/{item_key}` | Delete a local article-to-Zotero link. |

Existing contracts preserved:

- `GET /articles`
- `GET /articles?q=keyword`
- `GET /articles/{id}`
- `POST /rag/index`
- `POST /rag/query`
- M4 learning state/bookmark/note/session/stats endpoints

## 6. Frontend Integration

New route:

```text
/zotero
```

New UI:

- Provider status panel.
- Zotero item search.
- Paper metadata list.
- Item key and BibTeX key display.
- DOI/URL/tags display where available.
- BibTeX export text display.
- Navigation link from the shared reader shell.

The page shows clear provider status and remains usable with the default fake provider when Zotero Desktop is unavailable.

## 7. Article-Zotero Linking

Article Detail now includes a "Related Papers" panel.

Supported actions:

- list current Zotero links for the article
- search Zotero items
- link a Zotero item
- select relation type: `related`, `cites`, or `background`
- add an optional local relationship note
- remove a local link
- export BibTeX for linked papers

The links are project-local metadata. They do not write to Zotero Desktop and do not create a citation graph or paper graph.

## 8. Storage Strategy

M5 uses a lightweight project-local JSON store for Article-to-Zotero links.

Default path:

```text
.local_data/scientific_spaces/zotero_links.json
```

Environment overrides:

```text
SCIENTIFIC_SPACES_ZOTERO_FILE
SCIENTIFIC_SPACES_DATA_DIR
```

Storage shape:

```text
{
  article_id: {
    zotero_item_key: ZoteroArticleLink
  }
}
```

The implementation does not cache a real Zotero library and does not commit runtime link data. Tests isolate storage with temporary files.

## 9. Test Evidence

Backend command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
50 passed, 2 skipped in 3.39s
```

New backend coverage:

- Zotero status without local Zotero
- fake provider search
- get item
- BibTeX export
- API response shape
- Article-Zotero link create/list/update/delete
- M2 Article API regression
- M3 RAG API regression
- M4 Learning API regression

Frontend command:

```bash
cd frontend && npm run build
```

Result:

```text
✓ Compiled successfully
✓ Generating static pages (6/6)
```

Generated routes include:

```text
/
/articles
/articles/[id]
/zotero
```

Runtime smoke used temporary article, learning, and Zotero link files outside the repository.

Backend smoke:

| Check | Result |
|---|---|
| `GET /health` | PASS |
| `GET /zotero/status` | PASS |
| `GET /zotero/items?q=attention` | PASS |
| `POST /zotero/export/bibtex` | PASS |
| `POST /zotero/links/attention-001` | PASS |
| `GET /zotero/links/attention-001` | PASS |
| `GET /articles` | PASS |
| `POST /rag/query` | PASS |
| `GET /learning/stats` | PASS |

Frontend production smoke:

| Route | Result |
|---|---|
| `/` | `200` |
| `/zotero` | `200` |
| `/articles/attention-001` | `200` |

## 10. Environment Limitations

Zotero helper probe:

```bash
python3 /home/lkx/.codex/plugins/cache/openai-curated-remote/zotero/0.1.2/skills/zotero/scripts/zotero.py status --json
```

Observed local API status:

```text
base_url: http://127.0.0.1:23119
api_running: false
api_status: 503
connector_running: false
connector_status: 503
local_api_enabled_pref: null
```

Decision:

- Local Zotero Desktop API is currently unavailable in this environment.
- This is not a blocker because the default fake provider supports tests, build, and smoke checks.
- `LocalZoteroProvider` returns unavailable status and empty results instead of crashing.

Docker was not required for this task because non-Docker backend tests, frontend build, and runtime smoke passed.

## 11. Scope Boundary

Frozen M1 modules checked with `git diff --name-only`:

- `backend/app/crawler/`
- `backend/app/parser/`
- `backend/app/converter/`
- `backend/app/storage/`
- `backend/app/validation/`
- `backend/app/sync.py`
- `milestones/M1_SOURCE_PIPELINE.md`
- `docs/M1_FINAL_FREEZE_REPORT.md`

Result:

```text
No changes.
```

M2/M3/M4 frozen contracts checked:

- M2 Article API and article reader code: no changes.
- M3 RAG and LLM provider code: no changes.
- M4 learning API and learning store code: no changes.

Scope leak scan result:

- no M6 Knowledge Graph entities or relations
- no citation graph analysis
- no paper graph
- no graph database
- no graph node/edge extraction
- no RAG over Zotero papers
- no embedding or FAISS changes
- no AI literature review
- no AI Tutor
- no Derive/Quiz/Research tutor modes
- no writes to the user's Zotero library

Artifact checks found no forbidden pending artifacts:

- no `.env`
- no `node_modules`
- no PDF
- no full HTML download
- no images
- no trace/profile/cache artifact
- no committed Zotero link data file
- no real Zotero library export

Fixture Zotero metadata lives in code for deterministic tests only.

## 12. Known Risks

- Local Zotero Desktop API was unavailable in this environment and needs user-side setup before real library access.
- Zotero local API route behavior can differ across Zotero versions.
- Fake provider data is intentionally small and only proves integration contracts.
- Article-to-Zotero links are local JSON data; multi-user synchronization is not implemented.
- M5 does not evaluate citation graph correctness or paper full-text retrieval.

## 13. M6 Readiness

M6 Readiness:

A: Ready for M6

Reason:

- Article-to-paper metadata links now exist as a stable input for future Knowledge Graph work.
- M5 did not alter frozen source, reader, RAG, or learning contracts.
- Future M6 work should introduce graph entities and relations explicitly rather than overloading M5 Zotero links.
