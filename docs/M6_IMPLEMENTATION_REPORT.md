# M6 Implementation Report

## 1. Current Status

| Item | Status | Evidence |
|---|---|---|
| M0 Engineering Foundation | PASS | Existing backend/frontend foundation remains in place. |
| M1 Final Freeze | PASS | `docs/00_PROJECT_STATE.md` retains `M1 Freeze Passed`. |
| M2 Verification | PASS | `docs/00_PROJECT_STATE.md` retains `M2 Verification Passed`. |
| M3 Verification | PASS | `docs/00_PROJECT_STATE.md` retains `M3 Verification Passed`. |
| M4 Verification | PASS | `docs/00_PROJECT_STATE.md` retains `M4 Verification Passed`. |
| M5 Verification | PASS | `docs/00_PROJECT_STATE.md` retains `M5 Verification Passed`. |
| M6 Knowledge Graph | PASS | Graph model, builder, store, query service, API, frontend page, tests, and report are implemented. |

This milestone implements deterministic Knowledge Graph functionality only. It does not implement M7 AI Tutor, quiz generation, adaptive tutoring, autonomous research agents, AI-generated literature review, or LLM-based graph extraction.

Required context note:

- `docs/15_ACCEPTANCE.md` and `docs/31_MVP_BOUNDARY.md` are absent and remain recorded as documentation gaps.
- `milestones/M6_KNOWLEDGE_GRAPH.md` is present but broader than this implementation prompt; this M6 implementation follows the stricter prompt boundary and remains deterministic/rule-based.

## 2. Implemented Features

- Knowledge Graph data model.
- Deterministic node and edge IDs.
- Rule-based concept extraction.
- Formula extraction from LaTeX block forms.
- Section extraction using existing M3 Markdown chunking.
- Article node enrichment from M4 learning state and bookmark metadata.
- Zotero link integration using M5 project-local links and read-only provider metadata.
- Project-local graph storage with `SCIENTIFIC_SPACES_GRAPH_FILE` override.
- Graph query service for build/get/search/node/neighbors/subgraph.
- Backend Graph API.
- Frontend `/graph` page.
- Lightweight node-list, neighbor, and evidence view.
- Regression coverage for M2 Article API, M3 RAG API, M4 Learning API, and M5 Zotero API.

## 3. Graph Data Model

Implementation:

- `backend/app/graph/models.py`

Node shape:

```text
GraphNode
├── node_id
├── node_type: article | section | concept | formula | zotero_item
├── label
├── source_id
├── source_url
└── metadata
```

Edge shape:

```text
GraphEdge
├── edge_id
├── source_node_id
├── target_node_id
├── edge_type
├── weight
├── evidence
└── metadata
```

Graph document shape:

```text
GraphDocument
├── nodes
├── edges
├── built_at
└── source_counts
```

Determinism:

- `make_node_id(node_type, source)` is deterministic.
- `make_edge_id(source_node_id, target_node_id, edge_type, evidence_key)` is deterministic.
- Nodes and edges are sorted before storage/API output.

Boundary:

- The graph model is independent from the frozen M1 Article schema.
- The graph model does not modify M3 chunk schema.
- The graph model does not modify M5 Zotero item/link schema.

## 4. Graph Builder Strategy

Implementation:

- `backend/app/graph/builder.py`

Inputs:

- M2 Article Reader over M1 stored articles.
- M3 `chunk_article()` for Markdown section chunks.
- M4 `LearningStore` for article learning status and bookmark metadata.
- M5 `ZoteroLinkStore` for Article-Zotero links.
- M5 read-only Zotero provider metadata.

Construction rules:

- One `article` node per Article.
- Article node metadata includes read-only M4 learning state and bookmark status.
- One `section` node per Markdown chunk.
- `article -> section` edges use `has_section`.
- Rule-extracted concept nodes are linked from article metadata and sections with `mentions`.
- Formula nodes are linked from sections with `has_formula`.
- Zotero item nodes are linked from article nodes using the M5 link relation: `related`, `cites`, or `background`.
- Articles in the same category get limited `same_category` edges using adjacent pairs only, capped to avoid a dense graph.

Traceability:

- Every edge has `evidence`.
- Evidence records article IDs, article titles, URLs, section titles, chunk indices, formulas, link data, or category source metadata.

## 5. Concept Extraction Strategy

Implementation:

- `backend/app/graph/extractors.py`

Strategy:

- Uses deterministic regex token extraction.
- Extracts English technical tokens such as `attention`, `transformer`, `query`, and `key`.
- Extracts Chinese phrase tokens when present in titles, headings, categories, and section text.
- Applies a small stopword filter for common English words.
- Does not call an LLM.
- Does not call an external API.

Known limitation:

- Chinese concept segmentation is phrase-based and can be coarse. This is acceptable for M6 foundation and should be refined in a future M6.x extraction revision if higher precision is required.

## 6. Formula / Section Preservation

Section preservation:

- M6 uses the existing M3 Markdown chunker.
- Heading boundaries are preserved.
- Formula and fenced-code boundary behavior remains owned by M3 and is not modified.

Formula extraction:

- Supports:
  - `$$ ... $$`
  - `\[ ... \]`
  - `\begin{equation} ... \end{equation}`
- Stores the full formula text in formula node metadata.
- Does not split formula content.

Example runtime smoke produced:

```text
formula node label: QK^T
edge type: has_formula
```

## 7. Zotero Link Integration

Implementation:

- `backend/app/graph/builder.py`
- Reuses `backend/app/zotero/store.py`
- Reuses read-only `get_zotero_provider()`

Behavior:

- Article-Zotero links become `zotero_item` nodes.
- M5 relation types map directly to graph edge types:
  - `related`
  - `cites`
  - `background`
- Zotero item metadata is included when the configured provider can resolve the item.
- Missing Zotero item metadata still creates a traceable node by item key.

Boundary:

- No Zotero library write is performed.
- M5 Zotero store and provider contracts are not modified.
- No citation graph or paper graph analysis is implemented beyond explicit local links.

## 8. Graph Storage Strategy

Implementation:

- `backend/app/graph/store.py`

Default path:

```text
.local_data/scientific_spaces/knowledge_graph.json
```

Environment override:

```text
SCIENTIFIC_SPACES_GRAPH_FILE
```

Capabilities:

- `load()`
- `save(graph)`
- `clear()`
- missing file returns an empty `GraphDocument`

Boundary:

- Graph storage is separate from Article, Learning, and Zotero stores.
- `.gitignore` already covers `.local_data/` and `backend/.local_data/`.
- Runtime graph JSON is not committed.

Known risk:

- Corrupt JSON is not self-healed.
- Concurrent writes are not locked.

## 9. API Contract

Implementation:

- `backend/app/api/graph.py`

Endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/graph/build` | Build and persist the current graph. |
| `GET` | `/graph` | Return the current graph document. |
| `GET` | `/graph/nodes?q=keyword` | Search nodes by label/id/source/metadata. |
| `GET` | `/graph/nodes/{node_id}` | Return one node or `404`. |
| `GET` | `/graph/nodes/{node_id}/neighbors` | Return adjacent nodes and connecting edges. |
| `GET` | `/graph/subgraph/{node_id}` | Return a bounded subgraph around a node. |

Limits:

- search limit is capped.
- neighbor/subgraph depth is capped to `3`.
- neighbor/subgraph size is capped.
- empty graph returns an empty document.
- missing node returns `404`.

## 10. Frontend Integration

Implementation:

- `frontend/src/lib/graph.ts`
- `frontend/src/components/GraphView.tsx`
- `frontend/src/app/graph/page.tsx`
- `frontend/src/components/ReaderShell.tsx`

Route:

```text
/graph
```

UI features:

- graph summary:
  - node count
  - edge count
  - source article count
  - last built time
- node type counts
- build graph button
- node search
- node type filter
- node list
- selected node metadata panel
- neighbor list
- edge evidence view
- article node link to `/articles/{id}`
- zotero item node link to `/zotero`

No AI Tutor UI, quiz UI, research mode, generated explanation, or AI concept reasoning was added.

## 11. Test Evidence

Backend test command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
56 passed, 2 skipped in 3.42s
```

New backend coverage:

- deterministic graph IDs
- empty graph builder
- article/section/concept/formula/zotero graph builder behavior
- graph edge evidence presence
- graph store load/save/clear/missing file
- graph query search/neighbors/subgraph
- graph API build/get/search/node/neighbors/subgraph/missing node
- M2 Article API regression
- M3 RAG API regression
- M4 Learning API regression
- M5 Zotero API regression

Frontend build command:

```bash
cd frontend && npm run build
```

Result:

```text
✓ Compiled successfully
✓ Generating static pages (7/7)
```

Runtime smoke:

Backend:

| Check | Result |
|---|---|
| `GET /health` | PASS |
| `POST /graph/build` | PASS |
| `GET /graph` | PASS |
| `GET /graph/nodes?q=attention&node_type=concept` | PASS |
| `GET /graph/nodes/concept:attention/neighbors` | PASS |
| `GET /articles` | PASS |
| `POST /rag/query` | PASS |
| `GET /learning/stats` | PASS |
| `GET /zotero/status` | PASS |

Frontend:

| Route | Result |
|---|---|
| `/` | `200` |
| `/articles` | `200` |
| `/articles/attention-001` | `200` |
| `/zotero` | `200` |
| `/graph` | `200` |

Docker:

```text
docker: command not found
```

Docker is unavailable in this environment. This is recorded as an environment limitation, not a blocker, because backend tests, frontend build, and non-Docker smoke passed.

## 12. Scope Boundary

Frozen M1-M5 backend implementation paths were not modified:

- M1 crawler/parser/converter/storage/validation/sync
- M2 Article API and article reader service
- M3 RAG and LLM provider modules
- M4 learning API/store/modules
- M5 Zotero API/provider/store/modules

M6 changed:

- FastAPI router registration in `backend/app/main.py`.
- New graph backend modules.
- New graph frontend route/client/component.
- Reader shell navigation to expose `/graph`.

No M7 scope leak was detected:

- no AI Tutor
- no quiz generation
- no adaptive tutoring
- no mastery prediction
- no autonomous research agent
- no AI-generated literature review
- no LLM-based graph extraction

Artifact checks:

- no runtime `knowledge_graph.json`
- no graph cache
- no large graph export
- no real article corpus export
- no real Zotero library data
- no large BibTeX
- no FAISS index/cache
- no embedding cache
- no `.env`
- no API keys
- no PDF
- no HTML dump
- no images
- no trace/profile/cache artifact
- no `node_modules`

The artifact scan matched tracked source file `backend/app/crawler/cache.py` by filename only; this is source code, not a runtime cache artifact.

## 13. Known Risks

- Rule-based concept extraction is deterministic but coarse, especially for Chinese segmentation.
- Graph storage is local JSON and not multi-user production storage.
- Corrupt graph JSON is not self-healed.
- Concurrent graph writes are not locked.
- Same-category edges are intentionally limited and do not represent a full semantic relationship model.
- M6 does not infer `Theory` or `Experiment` entities beyond the implemented article/section/concept/formula/zotero foundation.
- M6 does not use LLM extraction by default.

## 14. M7 Readiness

M7 Readiness:

A: Ready for M7

Reason:

- Graph data model, builder, storage, query API, and frontend view are implemented.
- Article, section, concept, formula, and Zotero item nodes are available.
- Edges include evidence/source metadata.
- M1-M5 frozen contracts remain intact.
- M7 AI Tutor can consume this graph through the M6 graph API without modifying frozen M1-M6 implementation directly.
