# M6.1 Concept Provenance Metadata Revision Alignment

## Scope

This run fixes the M6 Verification blocker recorded in `docs/M6_VERIFICATION_REPORT.md`:

- Concept nodes were traceable through `mentions` edge evidence.
- Concept node metadata only contained `normalized`.
- M6 Verification requires source/provenance information on the concept node metadata itself.

## Allowed Changes

- `backend/app/graph/`
- `backend/tests/test_graph.py`
- `docs/M6_CONCEPT_PROVENANCE_REVISION.md`
- `docs/M6_IMPLEMENTATION_REPORT.md`
- `alignment.md`

## Forbidden Changes

- M1 crawler/parser/converter/storage/validation/sync code
- M2 Article API contracts
- M3 RAG contracts and citation/no-source behavior
- M4 Learning API contracts
- M5 Zotero contracts
- `docs/00_PROJECT_STATE.md`
- M7 AI Tutor, quiz, derive, explain, research, adaptive tutoring, or LLM-based extraction
- Runtime graph files, caches, PDFs, HTML exports, images, traces, profiles, local data, secrets, or `node_modules`

## Implementation Decision

Concept provenance is aggregated in the graph builder and stored on each concept node:

- `normalized`
- `source_count`
- `sources`
- `truncated`

Each source record includes:

- `article_id`
- `article_title`
- `article_url`
- `source_type`
- `source_context`
- `evidence`
- `section_title`, `section_node_id`, and `chunk_index` when section-based

The source list is sorted deterministically and capped at 10 entries. `source_count` records the complete deduplicated provenance count.

## Verification

Fresh checks run in this revision:

- Failing provenance test observed first: `KeyError: 'sources'`
- Search broadening regression observed and fixed after adding a failing test
- `uv run --project backend --extra dev pytest -q`
- `npm run build`
- Runtime smoke with temporary article, Zotero, learning, vector, and graph files under `/tmp`

## Status

M6.1 blocker is resolved by implementation evidence, but `docs/00_PROJECT_STATE.md` remains unchanged. M6 Verification Passed must be recorded only by a later M6 Verification Gate re-run.
