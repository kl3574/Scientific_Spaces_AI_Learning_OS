# Full Corpus RAG Index Report

## Current Status

- P2-001 Full Local Corpus RAG Index Rebuild: PASS
- Required baseline provider: deterministic fake/local
- Article source access: none
- Recommendation: A: Ready for P2-002 Local Corpus Reader/Search UX Audit

This gate rebuilds and audits a local RAG index from the completed Article store. It does not fetch Scientific Spaces, crawl source pages, generate PDFs, modify `Article.content`, or claim real-provider semantic quality.

## Input Corpus

| Metric | Result |
| --- | --- |
| Article store | `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json` |
| article count | 1311 |
| unique URL count | 1311 |
| duplicate URL count | 0 |
| missing content count | 0 |
| required fields | `id`, `title`, `url`, `content`, `metadata` |
| corpus fingerprint | `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d` |

The CLI defaults to a strict expected count of 1311. A partial Article store cannot produce the full-corpus PASS result. The loader reads only the Article store above; it does not use `article_list.json`, PDF, HTML dumps, the local Markdown export, search engines, or live pages.

The fingerprint is a deterministic SHA-256 digest over URL-sorted article IDs, canonical stored URLs, content hashes, and metadata. Reordering the same records leaves it unchanged; changing content changes it.

## Chunking Result

The frozen Markdown-structure chunker remains the source of chunk boundaries. Full-corpus indexing adds a stable `chunk_id` and serializes provenance without changing the M3 API contract.

| Metric | Result |
| --- | ---: |
| article count | 1311 |
| total chunk count | 5547 |
| indexed article count | 1311 |
| indexed article coverage rate | 1.0 |
| chunks/article min | 1 |
| chunks/article max | 39 |
| chunks/article mean | 4.2311 |
| chunks/article median | 1.0 |
| chunk characters min | 5 |
| chunk characters max | 23073 |
| chunk characters mean | 1524.6293 |
| empty chunk count | 0 |
| duplicate chunk ID count | 0 |
| missing source title count | 0 |
| missing source URL count | 0 |
| missing section count | 0 |
| articles without chunks | 0 |

Every runtime chunk is traceable through `article_id`, `article_title`, `article_url`, `section`, `chunk_id`, `chunk_index`, and `text`.

## Index Build Result

Command:

```bash
uv run --project backend python scripts/rag/build_full_corpus_index.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/rag/full_corpus \
  --provider fake \
  --rebuild
```

| Metric | Result |
| --- | ---: |
| status | PASS |
| provider | `fake` |
| embedding model | `deterministic-hash-v1` |
| embedding dimension | 128 |
| embedding input | `article_title_section_text_v1` |
| embedding batch size | 128 |
| embedding call estimate | 44 |
| build elapsed seconds | 2.7353 |
| chunks/second | 2027.9189 |
| FAISS index size | 2,840,109 bytes |
| chunk metadata size | 15,582,042 bytes |
| process peak memory | 107,835,392 bytes |

The 128-dimensional fake baseline and title/section/text embedding input were selected after a local diagnostic. The former 64-dimensional text-only baseline produced `expected_article_hit_at_k=0.5455`; the final baseline produces `0.9091`. This is a deterministic structural baseline, not evidence that fake embeddings match a production semantic model.

Manifest schema v2 records article/chunk counts, provider, embedding settings, build timestamp, source path, corpus fingerprint, file sizes, SHA-256 checksums, and chunk audit metrics.

Build safety:

- All index files are completed in a staging directory before replacement.
- An existing index is moved to a recoverable backup only during commit.
- A failed commit restores the previous index.
- A subsequent build recovers a backup left by an interrupted process.
- No-op reuse fully validates manifest schema, checksums, JSON rows, FAISS loadability, dimensions, row counts, provenance, article IDs, and corpus fingerprint.
- Corrupt or incompatible artifacts are rebuilt when `--rebuild` is present and are never accepted as a successful no-op.

## Idempotent Rebuild

The same command was executed after the successful build.

| Metric | Result |
| --- | --- |
| second run action | `no_op` |
| second run elapsed seconds | 0.2307 |
| corpus fingerprint unchanged | true |
| article count unchanged | true |
| chunk count unchanged | true |
| integrity validation before no-op | PASS |

This gate uses Option A: unchanged, valid artifacts are reused. The second run still reads and verifies the persisted index and chunk metadata before returning PASS.

## Retrieval Smoke Dataset

The local suite contains 11 supported queries plus one unsupported query. It spans 2009 through 2026 and covers the required themes.

| Category | Expected article/date | hit@10 |
| --- | --- | --- |
| Attention / Transformer | `archives/4765`, 2018-01-06 | HIT |
| Probability / statistics | `archives/10007`, 2024-03-07 | HIT |
| Optimizer / Muon | `archives/10592`, 2024-12-10 | HIT |
| Diffusion model | `archives/9119`, 2022-06-13 | HIT |
| Matrix analysis | `archives/11787`, 2026-06-25 | HIT |
| Variational / differential equation | `archives/1304`, 2011-04-04 | MISS |
| Early mathematics | `archives/104`, 2009-08-28 | HIT |
| Astronomy / physics | `archives/102`, 2009-08-26 | HIT |
| NLP / BERT | `archives/6736`, 2019-06-18 | HIT |
| GAN / VAE | `archives/5716`, 2018-07-18 | HIT |
| Website / tools | `archives/10320`, 2024-08-15 | HIT |
| Unsupported nonce query | no expected article | REFUSAL |

The single expected miss is retained rather than tuning the dataset to claim 100%. It documents the deterministic fake provider's retrieval limitation over a 5547-chunk search space.

## Retrieval Results

| Metric | Result |
| --- | ---: |
| indexed article coverage rate | 1.0 |
| retrieval query count | 12 |
| supported query source rate | 1.0 |
| loaded-service supported source rate | 1.0 |
| expected article hit@10 | 0.9091 |
| extended source schema valid rate | 1.0 |
| M3 service source schema valid rate | 1.0 |
| source title present rate | 1.0 |
| source URL present rate | 1.0 |
| source section present rate | 1.0 |
| no-source refusal rate | 1.0 |
| unsupported answer fabrication count | 0 |
| duplicate source count | 0 |
| retrieval error count | 0 |

Extended retrieval records contain `article_id`, `title`, `url`, `section`, `chunk_id`, and `score`. The service smoke separately validates the frozen M3 source keys: `article_id`, `article_title`, `article_url`, `section_title`, and integer `chunk_index`.

## Performance Baseline

Environment:

- Linux `7.0.0-27-generic`, x86_64
- Python `3.11.15`
- FAISS `1.14.3`
- NumPy `2.4.6`
- Intel Core Ultra X7 358H, 16 logical CPUs
- 30 GiB system memory

Query latency:

| Metric | Result |
| --- | ---: |
| query count | 12 |
| min | 0.0048 ms |
| mean | 0.2017 ms |
| median | 0.1650 ms |
| p95 | 0.7450 ms |
| max | 0.7450 ms |

These measurements are a baseline for this local machine and deterministic provider. They are not a cross-device or production SLA. Index load time is outside the per-query measurements.

## RAG API / Service Smoke

The full-corpus helper loads the persisted index into the existing `RagService` without changing the HTTP API or M3 response contract.

- Supported query: non-refusal answer with 10 sources.
- Supported source schema: PASS.
- Unsupported query: `无法基于当前资料回答。` with `sources=[]`.
- Unsupported query path: the same loaded 1311-Article index with an exact local-token support gate, not an empty fixture index.
- Citation/no-source contract: unchanged.
- Web access: none.
- API key: not required.

The local-token gate is deliberately conservative and deterministic. It proves the no-source contract for a query with no local lexical support; it does not claim broad semantic out-of-domain detection.

## Artifact Policy

Runtime layout:

```text
.local_data/scientific_spaces/rag/full_corpus/
├── index/
│   ├── faiss.index
│   ├── chunks.jsonl
│   └── manifest.json
├── reports/
│   ├── build_summary.json
│   ├── retrieval_smoke.json
│   └── benchmark.json
└── logs/
```

The entire output is covered by the existing `.local_data/` ignore rule. No Article store, local Markdown library, FAISS index, chunks, manifest, benchmark JSON, logs, embedding cache, PDF, HTML, image, trace, profile, API key, or other runtime artifact is committed.

## Regression Evidence

```text
uv run --project backend --extra dev pytest -q
194 passed, 2 skipped in 39.06s
```

```text
npm run build
PASS (Next.js 15.5.20; static page generation 8/8)
```

```text
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
Cases: 9
Overall: PASS
```

```text
uv run --project backend python scripts/eval/run_full_corpus_rag_eval.py \
  --article-store .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --index-dir .local_data/scientific_spaces/rag/full_corpus
status: PASS
```

Normal CI remains fixture-only and does not depend on the local 1311-Article store. The original M3/M7 deterministic cases still run unchanged.

## Risks

- Fake provider retrieval quality is structurally useful but not a substitute for a real semantic provider.
- The optional real-provider path has cost, rate-limit, token-length, and data-egress implications; it requires explicit `--allow-real-provider`, is disabled in CI, and was not executed in this gate.
- The largest structure-preserving chunk is 23,073 characters and may exceed a real provider's practical input limit.
- Index size and build cost will grow with corpus and embedding dimension.
- A corpus change makes the manifest fingerprint stale and requires rebuild.
- The local atomic directory protocol is designed for a single builder process; concurrent writers are not supported.
- The exact-token no-source gate is conservative and does not provide general semantic OOD classification.
- Larger Tutor source-selection spaces require a separate scaling evaluation.

## Recommendation

A: Ready for P2-002 Local Corpus Reader/Search UX Audit

Real-provider semantic quality, Graph scaling, Tutor scaling, and PDF export are not marked complete by this gate.
