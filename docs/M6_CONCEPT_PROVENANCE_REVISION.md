# M6 Concept Provenance Revision

## 1. Current Blocker

M6 Verification was blocked because concept nodes did not carry provenance/source information in their own metadata.

Previous runtime evidence:

```text
node_id=concept:attention
metadata={"normalized":"attention"}
```

Although the `mentions` edges had evidence, the M6 Verification Gate required concept node metadata itself to include source information.

## 2. Root Cause

The root cause was in `backend/app/graph/builder.py`:

- `_concept_node()` created metadata with only `normalized`.
- `_add_node()` used `setdefault()`, so the first concept node instance stayed unchanged.
- Later mentions of the same concept could add new edges, but could not enrich concept node metadata.

This made concept provenance edge-based only, not node-based.

## 3. Fix Strategy

The graph builder now aggregates deterministic concept provenance during graph construction and creates concept nodes after all article, metadata, and section mentions have been processed.

The fix preserves:

- Existing concept `node_id` values.
- Existing `mentions` edge evidence.
- Existing graph API response shape.
- M1-M5 frozen contracts.
- Rule-based extraction only, with no LLM or external API dependency.

The graph search service was also adjusted to exclude verbose provenance `sources` from the searchable metadata text. This prevents `q=attention` from matching every concept sourced from an Attention-titled article while still returning full provenance metadata in API responses.

## 4. Concept Metadata Provenance Schema

Concept node metadata now uses:

```json
{
  "normalized": "attention",
  "source_count": 4,
  "sources": [
    {
      "article_id": "attention-001",
      "article_title": "Attention机制的一个直观解释",
      "article_url": "https://spaces.ac.cn/archives/6508",
      "source_type": "article_title",
      "source_context": "Attention机制的一个直观解释",
      "evidence": "attention"
    }
  ],
  "truncated": false
}
```

Section-based source records additionally include:

- `section_title`
- `section_node_id`
- `chunk_index`

Supported `source_type` values in this revision:

- `article_title`
- `metadata_category`
- `section_heading`
- `section_content`

`source_count` records the complete deduplicated provenance count. `sources` is capped at 10 deterministic entries. `truncated` is true when additional sources exist beyond the cap.

## 5. Determinism Behavior

Determinism rules:

- Concept node IDs remain based on normalized concept text.
- Concept edge IDs remain based on existing source node, target node, edge type, and evidence.
- Provenance records are deduplicated by article, source type, section node, source context, and evidence.
- Provenance records are sorted by article, source type, section node, context, and evidence.
- Repeated graph builds produce the same concept metadata provenance ordering for the same input data.

## 6. Tests Added / Updated

Updated:

- `backend/tests/test_graph.py`

Added coverage:

- Concept node metadata includes `source_count`, `sources`, and `truncated`.
- Concept node metadata is not limited to `normalized`.
- Multiple article/section mentions of the same concept merge into one concept node provenance list.
- Provenance ordering is deterministic across repeated builds.
- `source_count` remains stable.
- Source records include article and section/source-context information.
- `mentions` edge evidence remains present.
- Graph search excludes verbose provenance sources from search matching while preserving API metadata.

Regression coverage still includes:

- Empty graph.
- Article/section/concept/formula/Zotero nodes.
- Formula and section behavior.
- Zotero link integration.
- Graph store behavior.
- Graph service and API.
- M2/M3/M4/M5 API regressions.

## 7. Runtime Smoke Result

Runtime smoke used temporary files under `/tmp` for article, learning, Zotero, vector, and graph storage.

Backend smoke:

```text
Backend health: {"status":"ok"}
POST /graph/build -> node_count=22, edge_count=26
GET /graph/nodes/concept:attention -> metadata keys normalized/source_count/sources/truncated
source_count=4
sources=4
truncated=False
source_types=['article_title', 'section_content', 'section_heading']
GET /graph/nodes/concept:attention/neighbors -> edge_evidence_all=True
GET /graph/nodes?q=attention&node_type=concept -> labels ['attention', 'self-attention']
```

Regression smoke:

```text
GET /articles?q=attention -> total=2
POST /rag/query -> sources=3
GET /learning/stats -> total_articles=2
GET /zotero/status -> provider=fake, read_only=True
```

Frontend smoke:

```text
/ -> 200
/articles -> 200
/articles/attention-001 -> 200
/zotero -> 200
/graph -> 200
```

## 8. Freeze Protection Result

M1-M5 frozen implementation paths were not modified by this revision.

Modified implementation paths are limited to M6 graph code:

- `backend/app/graph/builder.py`
- `backend/app/graph/service.py`

Modified test path:

- `backend/tests/test_graph.py`

No M7 AI Tutor, quiz, derive, explain, research, adaptive tutoring, autonomous research, AI-generated graph reasoning, or LLM-based extraction was implemented.

## 9. Remaining Risks

- Concept extraction remains rule-based and conservative.
- Chinese concept segmentation remains phrase-based and may need a future M6.x precision revision.
- `sources` is capped at 10 entries; `source_count` must be used to detect additional provenance.
- Local JSON graph storage still has known corrupt JSON and concurrency risks from the M6 verification report.

## 10. M6 Verification Readiness Recommendation

Recommendation: Ready to re-run M6 Verification Gate.

The specific blocker from `docs/M6_VERIFICATION_REPORT.md` is resolved by current implementation and test evidence. The project state is intentionally not updated to `M6 Verification Passed` in this revision; that must be done only by the next M6 Verification Gate if it passes.
