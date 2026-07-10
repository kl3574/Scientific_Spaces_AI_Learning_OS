# Full Corpus Knowledge Graph Scaling Report

## Current Status

- P2-003 Full-Corpus Knowledge Graph Scaling: PASS
- Input source: completed local Article store only
- Article source access: none
- Recommendation: A: Ready for P2-004 Tutor Source Selection over Full Corpus

This task scales and audits the existing M6/M6.1 graph contract. It does not crawl Scientific Spaces, fetch web content, generate PDFs, modify `Article.content`, change the M3 citation/no-source contract, or optimize Tutor source selection.

## Input Corpus

| Metric | Result |
| --- | --- |
| Article store | `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json` |
| Article count | 1311 |
| Unique URL count | 1311 |
| Missing content count | 0 |
| Duplicate count | 0 |
| Required fields | `id`, `title`, `url`, `content`, `metadata` |
| Corpus fingerprint | `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d` |

The full-corpus loader validates the JSON root, required fields, non-empty values, unique IDs, unique URLs, and metadata objects. It sorts Articles by URL and ID before graph construction. `article_list.json`, fixture data, PDF, HTML dumps, the Markdown materialization, the live site, and external APIs are not graph inputs.

## Graph Build Result

Command:

```bash
uv run --project backend python scripts/graph/build_full_corpus_graph.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/graph/full_corpus \
  --expected-article-count 1311 \
  --rebuild
```

| Metric | Result |
| --- | ---: |
| Status | PASS |
| Graph fingerprint | `abfcbc2b6dfc266e7fe190bee6d7196eb7fa00c07c6bbd68a2e2eaa9573ac9dc` |
| Graph fingerprint version | 1 |
| Extraction rule version | `m6.1-deterministic-v2` |
| Integrity audit rule version | `p2-003-integrity-v4` |
| Build elapsed | 5.8526 seconds |
| Graph file size | 75,291,074 bytes |
| Total nodes | 52,874 |
| Total edges | 82,230 |
| Atomic replacement | true |

Node counts:

| Type | Count |
| --- | ---: |
| Article | 1,311 |
| Section | 5,547 |
| Concept | 39,032 |
| Formula | 6,984 |

Edge counts use the frozen M6 names:

| Type | Count |
| --- | ---: |
| `has_section` | 5,547 |
| `mentions` | 69,649 |
| `has_formula` | 6,984 |
| `same_category` | 50 |

No Zotero link store exists for this runtime corpus, so no `zotero_item` node or Article-to-Zotero edge was fabricated. The current M6 builder does not emit `explained_by`, `supported_by`, or `verified_by`; those types were not manufactured to satisfy a count.

The build writes a complete staging directory, moves an existing target to a rollback location, and installs the staged output with atomic filesystem renames. Failure-injection tests prove that a failed replacement restores the previous graph. `GraphStore.save` independently uses a same-directory temporary file, flush, `fsync`, and `os.replace`. Platforms without an atomic directory-exchange primitive can still have a brief name-level visibility gap during a successful directory swap; full-corpus rebuild remains a single-writer maintenance operation.

The graph fingerprint excludes the non-deterministic build timestamp and includes the graph schema, M6.1 contract, extraction rule version, canonical nodes and edges, source counts, and corpus fingerprint. Therefore Article content changes and extraction-rule changes invalidate it even when extracted labels happen to remain unchanged.

## Integrity Audit

| Metric | Result |
| --- | ---: |
| input_article_count | 1,311 |
| graph_article_node_count | 1,311 |
| article_coverage_rate | 1.0 |
| article_metadata_mismatch_count | 0 |
| isolated_node_count | 0 |
| duplicate_node_id_count | 0 |
| duplicate_edge_id_count | 0 |
| dangling_edge_count | 0 |
| self_loop_count | 0 |
| missing_node_type_count | 0 |
| missing_edge_type_count | 0 |
| missing_provenance_count | 0 |
| missing_edge_evidence_count | 0 |
| concepts_without_sources_count | 0 |
| formulas_without_sources_count | 0 |
| sections_without_parent_article_count | 0 |
| articles_without_sections_count | 0 |
| invalid_source_url_count | 0 |
| invalid_article_reference_count | 0 |
| duplicate_concept_source_count | 0 |
| concept_source_count_mismatch_count | 0 |
| local_path_provenance_count | 0 |

Article-node title, URL, date, category, references, and images were compared with the input Article store. The mismatch count is zero, which confirms references and images metadata were preserved without changing the Article schema.

An initial full build correctly failed on four dangling `mentions` edges. Root-cause analysis found that the section-body helper removed every line beginning with `#`, including code lines such as `#include` and Python comments. The helper now removes only the first Markdown section heading. A regression fixture proves code-comment concepts are materialized and connected; the final full audit has zero dangling edges.

The v4 audit independently recomputes complete Concept source counts from the frozen extraction rule. It exposed six stable-ID collisions where punctuation variants such as `kullback`/`kullback-` mapped to one M6 node ID and one provenance set was previously discarded. The builder now deterministically merges those aliases and all source records under the existing node ID. Six nodes carry an `aliases` list; the final `concept_source_count_mismatch_count` is zero.

## Concept Provenance

M6.1 provenance remains attached directly to Concept metadata:

- `normalized`
- full deduplicated `source_count`
- bounded `sources` list, maximum 10
- `truncated`

Every stored source contains Article identity, title, canonical URL, source type, evidence, and section or equivalent source context. The audit rejects missing Article references, duplicate stored source records, full content fields, local paths, and invalid truncation semantics.

Full-corpus example:

| Concept | Full source count | Stored sources | Truncated |
| --- | ---: | ---: | --- |
| `attention` | 255 | 10 | true |

The frontend reports the 245 omitted sources explicitly. Regression coverage also builds a concept with more than 10 sources and proves deterministic ordering, complete `source_count`, deduplication, truncation, and no full Article content or local paths.

## Distribution and Scale

| Distribution | Min | Mean | Median | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nodes per Article | 15 | 56.6209 | 23 | 158 | 403 |
| Edges per Article | 15 | 62.7613 | 22 | 182 | 456 |
| Concepts per Article | 13 | 46.0625 | 17 | 129 | 351 |
| Formulas per Article | 0 | 5.3272 | 1 | 23 | 86 |

Connected components:

| Metric | Result |
| --- | ---: |
| Connected component count | 1 |
| Largest component | 52,874 nodes |

Largest concepts by full source count include `https` (916), `boldsymbol` (728), `begin` (678), `archives` (567), `equation` (537), and `attention` (255). The technical URL/LaTeX tokens are evidence of extraction-quality noise and are recorded as a risk rather than silently filtered in this M6-compatible scaling task.

## Idempotent Build

The same `--rebuild` command was executed after the final build.

| Metric | Result |
| --- | --- |
| second_run_action | `no_op` |
| second_run_elapsed_seconds | 0.1382 |
| corpus_fingerprint_unchanged | true |
| graph_fingerprint_unchanged | true |
| node_count_unchanged | true |
| edge_count_unchanged | true |

This uses preferred Option A. A no-op validates schema versions, corpus fingerprint, graph file size, and graph file SHA-256 before reuse.

## Graph API Scaling

The frozen M6 `GET /graph` response remains a complete `GraphDocument` for backward compatibility. Full-corpus clients and the frontend use the new bounded `GET /graph/summary` endpoint, which returns counts, timestamps, source counts, schema versions, and graph fingerprint without `nodes`, `edges`, source-store paths, or other local filesystem paths. This preserves M6 outward semantics while removing full-graph loading from the P2-003 UI path.

`POST /graph/build` remains available for legacy/small graph stores. When `SCIENTIFIC_SPACES_GRAPH_FILE` points to a managed full-corpus `graph.json` with its P2-003 manifest, the service rejects the request with 409. Managed graphs must be rebuilt through `scripts/graph/build_full_corpus_graph.py`, so the legacy builder cannot bypass corpus fingerprints, manifest generation, or the integrity audit.

`GET /graph/nodes` supports:

- `page`, `page_size`, maximum 100
- `node_type`
- `q`
- `article_id`
- `concept`
- `sort`

It returns `items`, `total`, `page`, `page_size`, `total_pages`/`pages`, `has_next`, and `has_previous`.
The frozen M6 `limit` parameter remains accepted as a bounded `page_size` alias for legacy clients. In legacy mode, `total` remains the returned-item count and the full match count is available as `matched_total`.

Article filtering is indexed from complete edge evidence as well as direct node metadata. It therefore includes a high-degree Concept even when the requested Article is outside that Concept's bounded 10-source provenance response.

`GET /graph/subgraph` and the compatibility path endpoint support explicit bounds:

- depth: 1 to 3
- node limit: 1 to 500
- edge limit: 1 to 1000
- optional node-type filter

Invalid bounds return 422, and missing nodes return 404. Graph JSON and its node map/adjacency index are cached by file path, modification time, and size rather than reparsed on every request. Concurrent cold requests use a single-flight load guard; a four-request regression test records one underlying graph load.

Five-run local benchmark:

| Query | Mean | P95 | Max | Returned nodes/edges |
| --- | ---: | ---: | ---: | --- |
| Summary | 14.26 ms | 15.27 ms | 15.27 ms | 0 / 0 |
| First node page | 11.19 ms | 13.03 ms | 13.03 ms | 100 / 0 |
| Middle node page | 9.78 ms | 10.49 ms | 10.49 ms | 100 / 0 |
| Article filter | 4.10 ms | 4.35 ms | 4.35 ms | 50 / 0 |
| Concept type filter | 11.08 ms | 12.08 ms | 12.08 ms | 50 / 0 |
| Concept search | 66.12 ms | 70.53 ms | 70.53 ms | 50 / 0 |
| `concept=` filter | 18.09 ms | 18.91 ms | 18.91 ms | 1 / 0 |
| Article-specific nodes | 5.12 ms | 5.33 ms | 5.33 ms | 17 / 0 |
| One-hop subgraph | 1.54 ms | 2.15 ms | 2.15 ms | 2 / 1 |
| Two-hop subgraph | 1.75 ms | 2.04 ms | 2.04 ms | 17 / 16 |

Cold summary load, including the initial 75 MB JSON parse and index construction, was 1,269.01 ms. All 65 expected-status benchmark requests completed without errors, stayed within response bounds, and passed configurable local smoke limits of 1,000 ms warm / 5,000 ms cold. Missing-node, invalid-depth, and excessive-page-size cases returned their expected 404/422 responses.

## Frontend Graph UX

The `/graph` page now uses bounded exploration:

- initial requests are summary plus a 20-node page
- no full graph request and no browser-side graph build action
- node-type filtering, search, clear, previous/next pagination
- independent loading, error/retry, and empty states
- selected-node detail fetched separately
- one-hop context fixed at 25 nodes and 50 relationships
- structured Concept provenance with full/omitted counts
- three-source default provenance view with expansion to the bounded 10 returned sources
- local Article navigation and original canonical URL
- long-label wrapping and desktop/mobile overflow checks
- local path filtering before metadata display

The tracked production-like Chromium smoke runner passed summary, filtering, exact `attention` provenance, provenance expansion, pagination, Article navigation, original-link inspection, bounded subgraph, node-list empty/error states, subgraph empty/error/retry states, and 1440 px/390 px overflow checks. External network request count was zero. Two expected console errors came from deliberately aborted node and subgraph requests used to prove retry behavior; unexpected console errors were zero. No screenshot, trace, profile, HTML, image, or Article body artifact was retained.

## RAG/Tutor Boundary Smoke

The full graph was loaded through the existing Tutor graph-context path using `concept:attention`:

| Metric | Result |
| --- | ---: |
| Context nodes | 20 |
| Context edges | 19 |
| Graph sources | 20 |
| Entire graph injected | false |
| Article provenance preserved | true |
| Local path exposed | false |

Tutor source selection was not rewritten. The graph context remains supplemental and bounded; the unchanged evaluation suite confirms Article citation grounding and no-source behavior.

## Artifact and Privacy Policy

Runtime layout:

```text
.local_data/scientific_spaces/graph/full_corpus/
├── graph.json
├── manifest.json
├── reports/
│   ├── build_summary.json
│   ├── integrity_audit.json
│   ├── query_benchmark.json
│   ├── frontend_smoke.json
│   └── tutor_graph_smoke.json
└── logs/
```

The entire runtime tree is covered by `.local_data/` in `.gitignore`. No corpus, graph, manifest, benchmark JSON, local log, Article store, Markdown library, RAG index, PDF, HTML dump, image, trace/profile/cache, API key, or `.env` file is committed. Full-corpus graph API and frontend responses expose no local source path.

## Regression Evidence

```text
uv run --project backend --extra dev pytest -q
213 passed, 2 skipped
```

```text
cd frontend && npm run test:graph
7 passed
```

```text
cd frontend && npm run build
PASS (Next.js 15.5.20; static page generation 8/8; /graph 5.57 kB)
```

```text
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
9 cases; Overall: PASS
```

```text
uv run --project backend python scripts/eval/run_full_corpus_rag_eval.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --index-dir .local_data/scientific_spaces/rag/full_corpus \
  --expected-article-count 1311
PASS; hit@10 90.9%; unsupported fabrications 0; retrieval errors 0
```

```text
uv run --project backend python scripts/graph/benchmark_full_corpus_graph.py ...
PASS; 13 query classes x 5 runs; bounded summary; response bounds respected; local latency guard passed; errors 0
```

```text
uv run --project backend python scripts/graph/smoke_full_corpus_graph_frontend.py ...
PASS; 17/17 UI checks; external network requests 0; unexpected console errors 0
```

```text
uv run --project backend python scripts/graph/smoke_tutor_graph_context.py ...
PASS; 20 context nodes; 19 edges; complete graph not injected; provenance preserved
```

Normal CI remains fixture-only and does not require the local 1311-Article store. The full-corpus build, graph, and reports remain ignored local evidence.

## Risks

- The 75 MB JSON graph has an approximately 1.27-second cold parse on this machine and is not a multi-process shared index.
- Full-directory replacement is rollback-safe for one builder, but concurrent writers are unsupported and readers can observe a brief path gap during a successful swap on platforms without atomic directory exchange.
- The legacy `GET /graph` full-document endpoint remains unbounded solely for M6 compatibility; full-corpus callers must use `/graph/summary`, paginated nodes, and bounded subgraphs.
- High-degree technical tokens connect the graph into one component and reduce Concept semantic precision.
- Concept provenance grows faster than the bounded 10-source response; clients receive omitted counts but cannot request all sources yet.
- A future corpus or extraction-rule change invalidates the graph and requires a rebuild.
- Playwright/frontend maintenance must preserve bounded queries and local-path filtering.
- Article detail pages contain remote image URLs; offline smoke must continue to block non-local network requests.
- No full-corpus Zotero links were present, so Zotero graph scaling remains unmeasured.
- Year metadata limitations from the corpus completion work remain unchanged.

The current 75 MB JSON design is acceptable for this local single-user baseline because warm API queries remain below 71 ms in the measured set. Further corpus growth, concurrent writers, or multi-process deployment should trigger a graph-storage architecture decision rather than unbounded JSON expansion.

## Recommendation

A: Ready for P2-004 Tutor Source Selection over Full Corpus
