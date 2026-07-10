# Full Corpus Tutor Source Selection Report

## Design Status

- P2-004 architecture: approved
- Selected approach: independent deterministic source selector
- Graph expansion: only when the request explicitly supplies `node_id`
- Implementation evidence: not yet collected

This document is the approved design baseline for P2-004. The implementation
phase will replace this design status with the required PASS, CONDITIONAL, or
BLOCKED result and measured full-corpus evidence. The design does not change
the M3 citation/no-source contract or the M6 provenance/evidence contract.

## Scope and Input Contract

The selector operates only over the completed local resources:

- Article store: `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json`
- RAG index: `.local_data/scientific_spaces/rag/full_corpus/`
- Knowledge Graph: `.local_data/scientific_spaces/graph/full_corpus/`

The full-corpus runtime requires matching Article, RAG, and Graph corpus
fingerprints. Normal CI uses deterministic temporary fixtures and does not
require any of these local resources.

No selector code may fetch Scientific Spaces, browse the web, parse PDFs or
HTML dumps, rebuild Article content, or use `article_list.json` as body input.

## Architecture

The implementation adds an isolated selector under `backend/app/tutor/` and
keeps `TutorService` as the orchestration boundary:

```text
TutorRequest
  -> query normalization and scope guard
  -> persisted FAISS candidate retrieval
  -> optional explicit bounded Graph expansion
  -> chunk deduplication and Article grouping
  -> mode-aware relevance and diversity ranking
  -> evidence sufficiency check
  -> bounded context assembly
  -> Tutor generation or refusal
  -> citation and response-schema validation
```

The selector exposes focused domain types:

- `SourceSelectionPolicy`: validated hard limits and mode defaults.
- `SourceCandidate`: one retrieved Article chunk and its deterministic scores.
- `SelectedSource`: a selected chunk with stable Article identity and evidence.
- `EvidenceSufficiencyResult`: mode-specific support and refusal decision.
- `SourceSelectionResult`: final Article evidence, bounded Graph context,
  generation context, safe summaries, truncation counts, and timing metrics.

The selector depends on retrieval and Graph protocols so fixture tests can use
small in-memory providers. It does not require an API key or real provider.

## Retrieval and Cache Design

For an unscoped request, the Tutor loads the existing persisted full-corpus
FAISS index lazily and caches the loaded index by resolved path and file
signature. It retrieves at most 20 candidate chunks.

For an explicit `article_id`, retrieval remains strictly Article-scoped. The
service chunks only that Article and builds a small temporary in-memory index,
preserving existing M7 behavior without searching unrelated Articles.

If no full-corpus index path is configured, the service keeps the existing
small-store compatibility path used by normal CI and M7 fixtures. The legacy
M3 RAG API and its global service are not redirected or modified.

`TutorRequest.top_k` remains accepted for backward compatibility. It controls
the requested final Article-chunk count and is clamped by the selector policy;
the candidate retrieval stage remains independently capped at 20.

## Selection Policy

Safe defaults:

| Limit | Default |
| --- | ---: |
| RAG candidate chunks | 20 |
| Chunks per Article | 2 |
| Final source Articles | 6 |
| Final Article chunks | 10 |
| Evidence snippets per Article | 2 |
| Graph depth | 2 |
| Graph nodes | 20 |
| Graph edges | 30 |
| Context characters | 24,000 |

The final limits are configurable through safe integer environment variables,
but code-level ceilings prevent unbounded values. Configuration errors fail
closed with a clear local configuration error rather than silently removing
all limits.

Candidate ranking is deterministic. FAISS L2 distance is converted to a
bounded relevance value and combined with query-token overlap, reciprocal
retrieval rank, and mode-specific evidence bonuses. Article score uses the
best chunk plus a bounded aggregate contribution from its second chunk.
Stable tie-breaking uses Article ID and chunk ID.

Selection proceeds at Article level. Duplicate chunk IDs are removed before
grouping, each Article contributes at most two chunks, and every selected
Article appears once in the Article-level source summary. Research mode applies
a deterministic similarity penalty to already selected titles and sections so
one high-frequency topic cannot fill the entire source budget.

Graph evidence is supplemental. It never creates or replaces Article evidence
and never raises an Article's rank solely because a Concept has high degree.

## Explicit Graph Policy

Graph expansion runs only when `TutorRequest.node_id` is non-empty. The selector
uses the existing bounded subgraph interface with depth at most 2, 20 nodes,
and 30 edges by default. A high-degree Concept such as `concept:attention`
therefore cannot return all 255 provenance sources.

Tutor Graph context is sanitized before response or prompt assembly:

- Node and edge identity, type, label, and bounded evidence are retained.
- Concept `source_count` and `truncated` are retained.
- At most two bounded provenance records are retained per Graph node.
- Full provenance arrays, Article bodies, local absolute paths, and store paths
  are removed.

A missing optional Graph node or unavailable Graph store degrades to
Article-only selection and is recorded in the selection summary. It does not
override an otherwise valid Article-grounded response.

## Mode-Specific Policy

### Explain

- Target 2 to 5 distinct Articles, with one Article allowed when it is the only
  relevant local source.
- Prefer definition and explanatory passages.
- Formula evidence is optional.
- Refuse when no relevant Article evidence exists.

### Derive

- Select at most 4 Articles and 8 chunks.
- Require at least one selected Article chunk containing balanced formula
  delimiters or explicit theorem/derivation evidence.
- Graph Formula nodes can supplement but cannot satisfy this requirement alone.
- Refuse with `insufficient_formula_evidence` when Article evidence is
  insufficient. The model may not fill missing steps from memory.

### QA

- Select 1 to 4 distinct Articles and at most 6 chunks.
- Prefer the strongest direct query overlap.
- Return only a grounded answer with valid Article sources, otherwise refuse.

### Quiz

- Select up to 6 Articles and 10 chunks.
- Every generated question and answer maps to at least one selected Article
  source.
- Stable source/chunk keys prevent duplicate questions.
- The number of questions cannot exceed the number of distinct auditable
  evidence units available under the request limit.

### Research

- Target 4 to 6 distinct Articles and require at least 2 for a synthesis.
- Apply diversity selection across Article titles and sections.
- Always state that results are local-corpus-only.
- Always state evidence gaps and never claim current external literature
  coverage.
- Refuse with `insufficient_local_corpus_evidence` when a multi-source synthesis
  cannot be grounded.

## Evidence Sufficiency and Refusal

The selector records:

- source and Article counts
- formula, definition, and answerable evidence flags
- source-schema validity
- unsupported or out-of-scope status
- refusal reason

Canonical refusal reasons are:

- `no_relevant_source`
- `insufficient_formula_evidence`
- `insufficient_local_corpus_evidence`
- `unsupported_query`
- `invalid_source_schema`

Unsupported detection combines the full-corpus local-token support gate with a
small deterministic guard for explicit real-time, web-search, weather, market,
or current-news requests. A populated FAISS index must not turn every query
into a supported answer merely because nearest neighbors always exist.

The existing Chinese no-source response remains unchanged. Research and derive
retain their existing mode-specific refusal messages.

## Context Assembly

Only selected evidence enters the generation context. The assembler consumes
chunks in final rank order, keeps citation identity separate from snippet text,
and enforces the 24,000-character default ceiling.

If a chunk exceeds the remaining budget, the assembler uses a bounded excerpt
ending at a paragraph or line boundary and keeps it attached to the same
Article/section identity. If no meaningful excerpt fits, the chunk and its
source are removed together. The system never creates an orphan snippet or
truncates Article ID, title, URL, section, or chunk identity.

The result records context characters, estimated tokens, context truncation,
and source truncation for each mode. Token estimates are explicitly diagnostic
and do not claim provider-specific tokenizer accuracy.

## API Compatibility

`POST /tutor/ask` keeps all existing request and response fields. It adds only
safe optional response summaries:

- `selection_summary`: candidate count, selected Article/chunk count, bounded
  Graph counts, truncation flags, and context size.
- `evidence_summary`: sufficiency flags and refusal reason.

The response does not expose internal prompts, full candidate lists, full
Graph documents, local paths, API keys, or unselected evidence.

`POST /tutor/quiz` keeps its existing shape and may accept an optional topic
question so full-corpus quiz selection does not require a hard-coded Article.

## Frontend Design

The `/tutor` page keeps the five existing modes and removes hard-coded fixture
Article/Graph defaults. Mode selection uses a compact segmented control.

The result surface provides:

- bounded, deduplicated Article sources with visible section metadata
- local Article and safe original-source links
- explicit refusal and derive-insufficiency states
- per-question Quiz sources
- a local-corpus-only Research label and evidence-gap notice
- safe selection/context counts without internal prompt data
- independent loading, error, empty, and retry behavior

Long titles, sections, and source lists wrap without horizontal overflow. URLs
with local-file or absolute-path schemes are not rendered as external links.

## Evaluation Design

The committed evaluation dataset contains metadata only, never Article bodies.
It has 42 cases:

| Mode | Cases |
| --- | ---: |
| Explain | 8 |
| Derive | 8, including 3 required refusals |
| QA | 8 |
| Quiz | 8 |
| Research | 6 |
| Unsupported | 4 |

Each case records case ID, mode, question, expected Article IDs, source-count
bounds, expected evidence type, and expected refusal. Full-corpus execution uses
the fake provider by default and writes only aggregate metrics plus limited
failed-case IDs under ignored `.local_data/` output.

The runner measures selection counts, duplicate rates, budget compliance,
source schema, expected-Article hits, diversity, high-degree expansion,
grounding/refusal behavior, context size by mode, and retrieval/Graph/selector/
Tutor latency distributions. Expected-Article misses are reported rather than
rewritten to produce an artificial 100 percent score.

## Failure Handling and Privacy

- Missing or fingerprint-mismatched full-corpus resources fail the explicit
  full-corpus CLI with a clear error.
- API compatibility mode falls back only when no full-corpus index is
  configured, not when a configured index is corrupt.
- Invalid source identity causes refusal, never silent citation removal after
  generation.
- Optional Graph/Zotero failures cannot become Article citations.
- Fake providers remain default and no API key is required.
- Real-provider execution remains opt-in, disabled in CI, and outside PASS.
- No web, source fetch, PDF generation, corpus mutation, or runtime artifact
  commit is permitted.

## Test Strategy

Unit and fixture integration tests cover every required selection invariant:
Article grouping, duplicate removal, per-Article and total budgets,
deterministic ranking, high-degree Graph truncation, each mode, evidence
sufficiency, unsupported refusal, schema rejection, context ceiling, local-path
filtering, no-network behavior, fake-provider default, and ordinary-CI
independence from the full corpus.

Regression execution preserves:

- the complete backend pytest suite
- frontend production build and Tutor-specific tests
- the unchanged 9-case RAG/Tutor baseline
- the unchanged full-corpus RAG evaluation
- the P2-003 Graph benchmark and browser smoke
- bounded Tutor Graph context

Production-like browser smoke covers all five modes, derive success/refusal,
Quiz source display, Research scope and gaps, safe links, bounded rendering,
loading/error/refusal states, and zero external requests.

## Implementation Boundary

Implementation may change only the paths permitted by the P2-004 task. It will
not modify Article content, crawler/source access, M3 grounding semantics, M6
provenance semantics, default provider opt-in behavior, release tags, or CI's
fixture-only full-corpus independence.
