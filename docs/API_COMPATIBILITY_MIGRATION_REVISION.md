# P2-008 API Compatibility and Migration Revision

Audit date: 2026-07-11

## Current Status

- P2-008 implementation and verification: **PASS**
- Formal version: `v1.0.0`
- Candidate version: `v1.1.0`
- P2-007 re-audit: **PASS** (completed after this revision was merged and its main CI succeeded)
- Release readiness: **PASS - Ready to tag v1.1.0 after the audit commit main CI**
- Tag/Release action: not performed by this revision

This revision restores the frozen v1.0 Article and Graph contracts, moves full-corpus extensions to explicit `/v1.1` endpoints, and adds an executable identity-preserving Learning JSON/SQLite migration path.

## Original Release Blocker

The prior candidate replaced `GET /articles` with a paginated response. An unchanged v1.0 client therefore received 20 of 1,311 Articles, a different default order, and seven new top-level fields. The release audit also identified Graph query/build drift and an incomplete Learning migration/rollback procedure.

## v1.0 Contract Baseline

The peeled `v1.0.0` tag was inspected directly.

- `GET /articles` accepts optional `q`, returns all matches in store order, and has exactly `items`, `total`, and `query`.
- `GET /articles/{id}` returns `id`, `title`, `url`, `content`, and `metadata`.
- `GET /graph/nodes` accepts `q`, `node_type`, and `limit`; `total` is the number of returned items.
- `GET /graph/subgraph/{node_id:path}` accepts `depth` and `limit` and returns `nodes`, `edges`, `built_at`, and `source_counts`.
- `POST /graph/build` returns HTTP 200 with `node_count`, `edge_count`, `built_at`, and `source_counts`.

## M2 Article API Contract Matrix

| Behavior | v1.0 baseline | v1.1 candidate after P2-008 | Result |
|---|---|---|---|
| Legacy list path | `GET /articles` | unchanged | PASS |
| Legacy parameters | optional `q` | optional `q` only | PASS |
| Legacy response keys | `items`, `total`, `query` | exact match | PASS |
| Legacy ordering | Article store order | Article store order | PASS |
| Legacy result size | all matches | all matches | PASS |
| Legacy search | title/content substring | unchanged | PASS |
| Empty legacy result | exact empty three-key response | exact match | PASS |
| Detail path/schema | `GET /articles/{id}` | unchanged | PASS |
| Scalable list | not present | `GET /v1.1/articles` | Additive |

## Legacy Article Endpoint Result

Regression fixtures cover 37 Articles and verify that an unparameterized legacy request returns all 37 in input order. Search, long-query, duplicate-URL, and empty-data cases preserve the v1.0 behavior: legacy records and old detail IDs are not hidden by the versioned endpoint's URL deduplication. Article detail and OpenAPI parameter regressions also pass.

Focused result:

```text
backend/tests/test_article_api.py: 18 passed
```

## Paginated Article Endpoint Result

`GET /v1.1/articles` retains the candidate's bounded full-corpus behavior:

- `page=1`
- `page_size=20`, maximum `100`
- `q`, `category`, and deterministic `sort`
- pagination state fields including `total_pages`, `has_next`, and `has_previous`
- invalid page bounds return `422`

The endpoint is additive and does not alter Article detail.

## Frontend Migration

The Reader Article list and Dashboard now call `/v1.1/articles`. Article detail remains on `/articles/{id}`. The Knowledge Graph UI calls `/v1.1/graph/nodes` and `/v1.1/graph/subgraph`; node detail remains on the legacy detail route.

Frontend contract tests:

```text
Article client: 3/3 PASS
Graph client/presentation: 8/8 PASS
Tutor client/presentation: 13/13 PASS
Next.js production build: PASS, 8 generated routes
```

## Full-Corpus API Smoke

The existing ignored local Article store was read without source access or rebuild:

```text
GET /articles              -> 200, total=1311, items=1311, exact legacy keys
GET /v1.1/articles         -> 200, total=1311, items=20
GET /articles/{first_id}   -> 200, non-empty content
```

The legacy response exposes all Articles by design for compatibility. New clients must use the bounded endpoint.

## M6 Graph Compatibility

Legacy routes preserve v1.0 parameter and response surfaces. Scalable behavior is versioned:

| Legacy route | Versioned extension |
|---|---|
| `GET /graph/nodes?q=&node_type=&limit=` | `GET /v1.1/graph/nodes` with pagination, filters, and sort |
| `GET /graph/subgraph/{node_id:path}` | `GET /v1.1/graph/subgraph` with explicit node/edge limits |
| `GET /graph/nodes/{node_id:path}/neighbors` | `GET /v1.1/graph/nodes/{node_id:path}/neighbors` with explicit bounds |

Legacy search retains Graph store order, clamps legacy limits as v1.0 did, and returns exactly `items`, `total`, `query`, and `node_type`. Legacy path subgraphs omit the new `limits` object. Under a managed full-corpus Graph, `POST /graph/build` returns the existing snapshot with the legacy HTTP 200/four-field response and does not overwrite the managed file.

Evidence:

```text
backend/tests/test_graph.py: 11 passed
Managed full-corpus POST /graph/build: 200, 52,874 nodes, 82,230 edges, graph SHA-256 unchanged
Full-corpus Graph benchmark: PASS
Cold summary: 1346.08 ms (limit 5000 ms)
Maximum warm query: 75.09 ms (limit 1000 ms)
Response bounds and status/error guards: PASS
Graph Chromium smoke: 17/17 PASS
```

## M1 Freeze Governance

`docs/ADR/0005-m1-post-freeze-corpus-compatibility-revisions.md` records the post-freeze parser/canonicalization/corpus-control changes as an explicit M1.x compatibility revision.

- `#PostContent` and page-chrome filtering are verified content-fidelity fixes.
- Candidate replacement and legacy skip prevent invalid rows from entering Article storage.
- Converter and validation code have no post-v1.0 delta in the audited range.
- The frozen Article schema and metadata keys are unchanged.
- No verified content fix is rolled back.

M1 compatibility result: **PASS**.

## SQLite Migration

The executable JSON-to-SQLite command is:

```bash
uv run --project backend python scripts/persistence/migrate_learning_json_to_sqlite.py \
  --json-path /path/to/learning.json \
  --sqlite-path /path/to/scientific_spaces.db
```

It preserves all primary keys, timestamps, status, `read_count`, bookmark fields, note content, and session fields. It builds a complete staged database and atomically replaces the target. The source JSON is never modified. Repeated execution produces the same record counts and source values.

## SQLite Rollback and Restore

Export SQLite data before switching back to JSON:

```bash
uv run --project backend python scripts/persistence/migrate_learning_sqlite_to_json.py \
  --sqlite-path /path/to/scientific_spaces.db \
  --json-path /path/to/learning.json
```

The export also stages and atomically replaces its target. Tests inject replace failures in both directions and verify that source and pre-existing target bytes remain unchanged and staging files are removed. A backend environment-variable switch alone does not transfer data. General executable backup/restore remains available through the existing operations commands.

Migration evidence:

```text
Migration/config/SQLite stores: 16 passed
JSON -> SQLite -> JSON identity round trip: PASS
Repeated migration/export: PASS
Strict numeric and record-ID preservation: PASS
Forward/reverse failure atomicity: PASS
CLI explicit-path smoke: PASS
```

## OpenAPI and Documentation

OpenAPI now exposes separate legacy and scalable contracts:

```text
GET /articles: q
GET /v1.1/articles: q, page, page_size, category, sort
GET /graph/nodes: q, node_type, limit
GET /v1.1/graph/nodes: q, node_type, article_id, concept, sort, page, page_size
GET /graph/subgraph/{node_id}: node_id, depth, limit
GET /v1.1/graph/subgraph: node_id, depth, node_limit, edge_limit, node_type
```

README, CHANGELOG, the persistence plan, release-note draft, and release checklist document the endpoint split and explicit migration/rollback process.

## Regression Evidence

Fresh results on 2026-07-11:

- Backend full suite: **469 passed, 3 skipped**.
- Frontend production build: **PASS**.
- Baseline RAG/Tutor evaluation: **9/9 PASS**.
- Full-corpus RAG evaluation: **PASS**, 12 queries, expected hit@10 90.91%, no-source refusal 100%, errors/fabrications 0.
- Full-corpus Graph benchmark: **PASS**.
- Full-corpus Tutor evaluation: **PASS**, 42 cases, hard/validity failures 0.
- Production-like API/frontend smoke: **PASS**.
- Reader Chromium smoke: **PASS**; the final controlled run blocked four remote image references before network access, external responses 0, unexpected console errors 0.
- Graph Chromium smoke: **17/17 PASS**, external requests 0.
- Tutor Chromium smoke: **17/17 PASS**, external requests 0.

No Scientific Spaces crawl, Article-page refetch, PDF generation, corpus rebuild, RAG rebuild, or Graph rebuild was performed. An initial Reader diagnostic exposed four stored remote image URLs before route interception was enabled; the final evidence run blocked all four and received no external response. This is recorded as an execution deviation and a Reader privacy risk, not hidden as a clean local-only first attempt.

## Artifact and Secret Check

- No tracked `.local_data`, database, Article corpus, PDF, HTML dump, image, vector index, Graph runtime, backup, browser profile, trace, cache, `.env`, API key, `node_modules`, or `.next` output was added.
- Evaluation outputs were written only to ignored or `/tmp` paths and deleted after evidence capture.
- Migration fixtures used temporary directories.
- Runtime Learning/Zotero/Tutor writes used `/tmp` and were deleted.

## Remaining Risks

- Legacy `GET /articles` is intentionally unbounded and expensive at 1,311 Articles; it exists only for unchanged v1.0 clients.
- The Reader's stored Markdown can contain remote image references. The release smoke blocks them; normal online Reader use can request them unless a later privacy revision changes rendering policy.
- The managed Graph remains a large local JSON snapshot with browser/runtime and cold-load costs.
- JSON and SQLite can diverge if an operator switches backends without running the explicit migration/export command.
- Migration replaces the target with the selected source snapshot; operators must keep a verified backup and choose source/target paths carefully.

## Recommendation

**A: Ready to rerun P2-007**

P2-008 resolves the compatibility and migration blockers. Its recommendation at completion was to rerun P2-007; that clean-main re-audit subsequently passed and is recorded in `docs/V1_1_RELEASE_READINESS_AUDIT.md`.
