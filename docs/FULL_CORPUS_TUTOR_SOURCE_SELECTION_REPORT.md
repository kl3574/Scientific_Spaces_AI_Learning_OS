# Full Corpus Tutor Source Selection Report

## Current Status

- P2-004 Tutor Source Selection over Full Corpus: PASS
- Selected architecture: deterministic bounded source selector (Scheme A)
- Graph expansion: explicit nonblank `node_id` only
- Baseline provider: deterministic fake/local
- Recommendation: A: Ready for P2-005 Optional PDF Export Workflow

This gate implements and evaluates Tutor source selection against the completed
local corpus. It does not fetch Scientific Spaces, access the web, modify
`Article.content`, generate PDFs, or claim real-provider language quality.

## Input Resources

| Resource | Result |
| --- | --- |
| Article store | `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json` |
| Article count | 1,311 |
| RAG index | `.local_data/scientific_spaces/rag/full_corpus/` |
| RAG chunk count | 5,547 |
| Graph directory | `.local_data/scientific_spaces/graph/full_corpus/` |
| Graph nodes | 52,874 |
| Graph edges | 82,230 |
| Corpus fingerprint | `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d` |
| Graph fingerprint | `abfcbc2b6dfc266e7fe190bee6d7196eb7fa00c07c6bbd68a2e2eaa9573ac9dc` |
| RAG provider/model | `fake` / `deterministic-hash-v1` |
| RAG dimension | 128 |

The evaluator validates the persisted RAG artifacts against the Article store,
recomputes the corpus fingerprint, loads `graph.json`, recomputes the Graph
fingerprint, and compares both fingerprints with their manifests before any
case runs. All 44 expected Article IDs in the 42-case suite exist in the local
Article store.

## Selection Policy

The Tutor uses one Article retrieval operation per ask and then performs
deterministic Article-level selection.

| Limit | Value |
| --- | ---: |
| Retrieval candidates | 20 chunks |
| Chunks per Article | 2 |
| Final source Articles | 6 |
| Final Article chunks | 10 |
| Graph depth | 2 |
| Graph nodes | 20 |
| Graph edges | 30 |
| Generation context | 24,000 characters |
| Stored Graph provenance per node | 2 records |
| Per-record supplemental payload | 8,192 serialized characters |
| Aggregate Graph supplement | 31,500 serialized characters |
| Aggregate Zotero supplement | 16,000 serialized characters |
| Combined supplemental response | 48,000 serialized characters |

The pipeline normalizes the query, retrieves bounded candidates, removes
duplicate chunk IDs, groups by Article, ranks Articles deterministically,
applies mode-specific diversity/evidence rules, assembles a bounded context,
and validates citation identity before generation.

Graph behavior is deliberately explicit:

- no `node_id` means zero Graph lookup and zero Graph context;
- a nonblank `node_id` uses the bounded M6 subgraph interface;
- Graph and Zotero evidence are supplemental and never satisfy Article
  grounding, Research diversity, or Derive formula requirements;
- Graph/Zotero strings, collections, nesting, URLs, and payload size are
  bounded and local paths are removed;
- aggregate supplemental overflow is dropped deterministically and exposed as
  `supplement_omitted_count` instead of returning an unbounded response;
- the combined clamp removes trailing Zotero items first, then Graph edges and
  trailing nodes, and reports the post-clamp Graph counts actually returned;
- Graph latency, safe error code, counts, and truncation are additive response
  metadata.

## Mode-Specific Policies

### Explain

- Maximum 5 Articles and 10 chunks.
- Definition/explanation passages receive a deterministic evidence bonus.
- When the bounded candidate set contains a query-relevant formula passage,
  the final multi-chunk selection preserves one such passage.
- One relevant Article is sufficient; no relevant Article causes refusal.

### Derive

- Maximum 4 Articles and 8 chunks.
- At least one selected Article chunk must contain balanced formula or explicit
  theorem/derivation evidence.
- Zero Article evidence maps to the existing `no_sources` contract.
- Article evidence without formulas maps to
  `insufficient_formula_sources`; Graph Formula nodes cannot satisfy the gate.

### QA

- Maximum 4 Articles and 6 chunks.
- Requires answerable Article evidence and valid citation schema.
- Query-relevant formula evidence is preserved when available without adding
  candidates or exceeding the Article/chunk budget.
- Explicit web/account/private-data and unsupported real-time/high-stakes
  requests refuse deterministically.

### Quiz

- Maximum 6 Articles and 10 chunks.
- Quiz generation reuses the same evidence/refusal gates.
- Every question maps to a unique auditable Article evidence unit and carries
  at least one valid Article source.
- The requested count, normalized uniqueness, topic relevance, and Article
  source mapping are hard evaluation gates.

### Research

- Maximum 6 Articles and 10 chunks; at least 2 distinct Articles are required.
- Diversity ranking penalizes repeated title/section terms.
- Every successful answer states the local-corpus-only boundary and evidence
  gap; a single-Article scope refuses instead of pretending to be a synthesis.

## Full-Corpus Evaluation Dataset

The committed fixture contains metadata only: questions, expected Article IDs,
mode, evidence type, source bounds, expected refusal, and optional explicit
identifiers. It contains no Article body, answer, snippet, URL, local path, or
candidate list.

| Mode | Cases |
| --- | ---: |
| Explain | 8 |
| Derive | 8 (5 supported, 3 required refusals) |
| QA | 8 |
| Quiz | 8 |
| Research | 6 |
| Unsupported | 4 |
| Total | 42 |

`P2-004-EX-05` explicitly supplies `node_id=concept:attention`; all other
cases leave `node_id` absent. This proves that the Graph path is reachable and
that Graph does not expand implicitly.

## Source Selection Results

| Metric | Result |
| --- | ---: |
| evaluation case count | 42 |
| selected source chunks mean / median / p95 / max | 2.4286 / 2 / 6 / 7 |
| selected chunks mean / median / p95 / max | 2.5238 / 2 / 6 / 7 |
| duplicate source rate | 0.0 |
| source budget violations | 0 |
| Graph budget violations | 0 |
| source schema valid rate | 1.0 |
| source title present rate | 1.0 |
| source URL present rate | 1.0 |
| source section present rate | 1.0 |
| supported case non-empty source rate | 1.0 |
| expected evidence type pass rate | 1.0 |
| supported Derive formula evidence rate | 1.0 |
| expected Article hit rate | 0.9143 |
| expected Article recall | 0.6038 |
| selected Article diversity mean | 0.5170 |
| irrelevant Article rate | 0.5077 |
| high-degree concepts checked | 1 |
| high-degree overexpansion count | 0 |

Expected-Article misses are diagnostic, not rewritten to manufacture a perfect
retrieval score. The six misses are the six broad Research cases
`P2-004-RS-01` through `P2-004-RS-06`; each still passed all grounding,
multi-Article, citation, budget, and local-only requirements. This reflects the
deterministic fake embedding baseline and broad expected-source sets, not a
claim about real semantic reranking quality.

The high-degree guard used `concept:attention`, whose complete M6 provenance
count is 255. The Tutor response retained `source_count=255`,
`truncated=true`, and only two sanitized provenance records. The independent
Graph/Tutor smoke returned 20 nodes and 19 edges and did not inject the full
52,874-node graph.

## Grounding and Refusal

| Metric | Result |
| --- | ---: |
| citation required pass rate | 1.0 |
| no-source refusal rate | 1.0 |
| Derive insufficient-evidence refusal rate | 1.0 |
| refusal match rate | 1.0 |
| unsupported answer fabrication count | 0 |
| answer without sources count | 0 |
| Quiz question source coverage | 1.0 (16/16 questions) |
| Quiz requested count pass rate | 1.0 |
| Quiz normalized unique question rate | 1.0 |
| Quiz topic relevance rate | 1.0 |
| Quiz Article source mapping rate | 1.0 |
| empty Quiz suites | 0 |
| Research local-only pass rate | 1.0 |
| Research evidence-gap statement rate | 1.0 |
| Research multi-Article evidence rate | 1.0 |
| execution errors | 0 |

The outward M7 aliases remain stable: `no_sources` for unsupported/no relevant
Article context and `insufficient_formula_sources` when selected Article
evidence lacks formula support. The additive `evidence_summary` retains the
more precise internal decision.

## Context Size

The measured context is selected Article generation context; Graph and
supplemental payloads have independent count and serialization bounds.

| Mode | Mean chars | P95 chars | Max chars | Mean estimated tokens | Truncation rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Explain | 2,280.9 | 4,618 | 4,618 | 570.6 | 0.125 |
| Derive | 1,580.0 | 3,149 | 3,149 | 395.3 | 0.0 |
| QA | 1,931.9 | 2,936 | 2,936 | 483.4 | 0.0 |
| Quiz | 2,587.6 | 3,323 | 3,323 | 647.3 | 0.0 |
| Research | 9,364.2 | 13,475 | 13,475 | 2,341.5 | 0.0 |
| Unsupported | 3,250.0 | 6,946 | 6,946 | 812.8 | 0.0 |

All Article contexts remained below the 24,000-character ceiling. The one
Explain truncation flag is the explicit high-degree Graph case: bounded Graph
provenance was intentionally truncated. Citation identity is stored separately
from excerpts, so no orphan snippet or truncated source identity was produced.

## Performance Baseline

Environment:

- Linux `7.0.0-27-generic`, x86_64
- Python `3.11.15`
- Intel Core Ultra X7 358H, 16 logical CPUs
- 30 GiB system memory

Times are local fake-provider baselines in milliseconds and are not a
cross-device SLA.

| Stage | Min | Mean | Median | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Retrieval | 0.513 | 44.954 | 8.376 | 20.081 | 1,560.673 |
| Graph | 0.003 | 46.736 | 0.003 | 0.008 | 1,962.734 |
| Selector | 1.057 | 5.241 | 4.174 | 10.375 | 12.876 |
| Tutor residual/fake generation | 0.055 | 0.248 | 0.224 | 0.519 | 0.633 |

The retrieval maximum is the cold persisted-index load. The Graph maximum is
the single explicit `concept:attention` cold 75 MB Graph load; no-node Graph
paths are near-zero. The separate P2-003 Graph benchmark remained PASS with a
1,956.2 ms cold summary load and 90.4 ms maximum warm query in this run.

## Tutor API and Frontend UX

`POST /tutor/ask` preserves all M7 keys and adds safe `selection_summary` and
`evidence_summary` objects. `POST /tutor/quiz` accepts an optional topic while
preserving its existing response shape. A configured corrupt or missing full
corpus index returns HTTP 503; it does not silently start a second retrieval
route.

The `/tutor` UI now provides:

- all five modes with stale state cleared on mode changes;
- bounded, deduplicated Article/Graph/Zotero source rendering;
- bidirectional source expand/collapse and backend/UI omitted-count messaging;
- safe local Article and HTTP(S) original links;
- section/chunk metadata, refusal states, and Derive insufficiency text;
- one visible Quiz prompt mapped to the request topic and per-question sources;
- local-corpus-only Research scope and evidence-gap text;
- additive source/context/Graph timing summaries;
- embedded POSIX, Windows, UNC, traversal, and executable-scheme filtering.

The fixture Chromium smoke passed 20/20 UI checks, including simulated 500
error/retry and empty/refusal states. The live Chromium smoke passed 17/17
checks through the real local backend, persisted full-corpus RAG index, and
explicit bounded Graph access. Both reported zero external network requests,
zero unexpected console errors, and no desktop/mobile horizontal overflow.

## Artifact and Privacy

- No source fetch, web request, crawler, PDF, HTML dump, or Article mutation
  occurred.
- Fake providers remained the default; no API key was required or recorded.
- The 42-case fixture contains metadata only.
- Runtime evaluation summaries and smoke output stayed under ignored
  `.local_data/`.
- API/frontend checks found no local path exposure.
- No corpus, RAG index, Graph runtime, response log, candidate list, PDF,
  image, trace, profile, cache, `.env`, or `node_modules` is committed.

## Regression Evidence

| Check | Result |
| --- | --- |
| Backend pytest | PASS, 341 passed / 2 skipped |
| Frontend Tutor tests | PASS, 13/13 |
| Frontend Graph tests | PASS, 7/7 |
| Next.js production build | PASS, 8 routes generated |
| Original RAG/Tutor evaluation | PASS, 9 cases / all required rates 1.0 |
| Full-corpus RAG evaluation | PASS, hit@10 0.9091 / no-source 1.0 / errors 0 |
| P2-003 Graph benchmark | PASS, response bounds and latency guard satisfied |
| Bounded Tutor Graph smoke | PASS, 20 nodes / 19 edges / full graph not injected |
| Full-corpus Tutor evaluation | PASS, 42 cases / 0 hard or validity failures |
| Frontend fixture smoke | PASS, 20/20 |
| Frontend live full-corpus smoke | PASS, 17/17 |

Normal CI remains fixture-only and does not depend on the ignored 1,311-Article
corpus, FAISS index, or Graph runtime.

## Limitations

- Fake embeddings and fake generation prove deterministic structure,
  grounding, and budgets; they do not establish final language or mathematical
  quality for a real model.
- Six broad Research expected-source sets were not hit exactly; IDs and metrics
  are retained for future semantic retrieval work.
- Research is local-corpus-only and does not cover external or latest
  literature.
- Real-provider execution remains explicit opt-in, disabled in CI, and subject
  to cost, rate, latency, token, and data-egress constraints.
- The 75 MB JSON Graph has a visible cold-load cost and remains a local
  single-process baseline.
- Corpus year metadata limitations remain unchanged.
- PDF export was not executed or marked complete.

## Recommendation

A: Ready for P2-005 Optional PDF Export Workflow

P2-004 is complete for deterministic full-corpus source selection. Real-provider
quality evaluation remains a separate opt-in task and is not implied by this
PASS result.
