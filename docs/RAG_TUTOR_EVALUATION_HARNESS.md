# RAG and Tutor Evaluation Harness

## Current Status

- P0-005 status: PASS
- Scope: post-MVP quality evaluation infrastructure
- Default providers: deterministic fake embedding, fake LLM, fake Zotero
- Runtime behavior: no real LLM call, no web search, no article download, no Zotero write

Required context was read before implementation. `docs/25_RETRIEVAL_SPEC.md` and `docs/31_MVP_BOUNDARY.md` are absent in the current repository and remain documentation hygiene gaps rather than blockers for this harness.

## Purpose

This harness provides a repeatable structural and groundedness baseline for RAG and tutor behavior. It checks retrieval, citation shape, no-source refusal, tutor mode grounding, quiz source coverage, and local-only research boundaries.

It is not a full subjective answer quality evaluator. It does not use LLM-as-judge and does not grade language fluency, mathematical elegance, or broad semantic completeness.

## Evaluation Scope

- RAG retrieval against expected article sources.
- Citation presence and source schema shape.
- No-source refusal without fabricated citations.
- Tutor `explain`, `derive`, `qa`, `quiz`, and `research` modes.
- Quiz question source coverage.
- Derive-mode refusal when formula evidence is insufficient.
- Research-mode local-only language and source-gap boundary.
- Graph and Zotero context as supplemental local context only.

## Dataset

Fixture directory:

```text
backend/tests/fixtures/evaluation/
```

Files:

- `articles.json`: three small deterministic article fixtures.
- `expected_cases.json`: nine evaluation cases covering RAG, no-source, and five tutor modes.
- `zotero_links.json`: fake article-to-Zotero metadata links only.
- `graph_expected.json`: structural graph expectation metadata only.

The fixture articles use the MVP Article shape:

- `id`
- `title`
- `url`
- `content`
- `metadata`

The harness copies fixtures into a temporary runtime directory for each case and sets isolated store environment variables. It does not write runtime data into the repository.

## Metrics

Retrieval metrics:

- `retrieval_hit_at_k`
- `expected_article_hit`
- `expected_chunk_hit`
- `retrieved_source_count`

Grounding metrics:

- `citation_required_pass_rate`
- `non_empty_sources_rate`
- `source_schema_valid_rate`
- `no_fake_source_rate`

Refusal metrics:

- `no_source_refusal_rate`
- `unsupported_query_refusal_rate`

Tutor mode metrics:

- `explain_grounded_rate`
- `derive_refusal_when_insufficient_rate`
- `qa_sources_required_rate`
- `quiz_question_sources_rate`
- `research_local_only_rate`

Regression counters:

- `no_source_answer_fabrication_count`
- `answer_without_sources_count`
- `quiz_without_sources_count`

All metrics are deterministic structural checks. They do not require a semantic judge.

## How to Run

Run backend tests:

```bash
uv run --project backend --extra dev pytest -q
```

Run the evaluation baseline:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Run frontend build:

```bash
cd frontend
npm run build
```

Optional JSON output is allowed only under ignored runtime output paths:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py --output eval_outputs/rag_tutor.eval.json
```

## Baseline Results

Command:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Result:

```text
RAG/Tutor Evaluation Baseline
Cases: 9
Retrieval hit@k: 100%
Citation required pass rate: 100%
No-source refusal rate: 100%
Source schema valid rate: 100%
No fake source rate: 100%
Quiz source coverage: 100%
Research local-only checks: PASS
Unsupported answer fabrications: 0
Answers without sources: 0
Quiz without sources: 0
Overall: PASS
```

## Limitations

- Fake provider baseline does not represent real LLM answer quality.
- Structural metrics do not evaluate language fluency or nuanced semantic correctness.
- No LLM-as-judge is used.
- No web-scale evaluation is performed.
- The fixture dataset is intentionally small and curated.
- Unsupported-query refusal is evaluated through no-source structural cases, not broad semantic out-of-domain detection over a populated corpus.

## Next Steps

- Expand a curated human evaluation set.
- Add real-provider evaluation behind explicit environment gates.
- Expand retrieval gold sets and chunk-level expectations.
- Add regression thresholds to CI once the baseline stabilizes.
- Define an answer quality rubric for human review.
