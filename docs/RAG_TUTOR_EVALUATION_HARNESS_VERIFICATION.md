# RAG and Tutor Evaluation Harness Verification

## Current Status

- P0-005 Implementation: PASS
- Verification: PASS
- Recommendation: A: Evaluation harness verified

This is an audit gate only. No product feature behavior, M1-M7 frozen implementation code, tag, or release metadata was changed.

Required context documents were read where present:

- `README.md`
- `docs/00_PROJECT_STATE.md`
- `docs/POST_MVP_ROADMAP.md`
- `docs/RAG_TUTOR_EVALUATION_HARNESS.md`
- `docs/SECURITY_PRIVACY_BASELINE.md`
- `docs/SECURITY_PRIVACY_BASELINE_VERIFICATION.md`
- `docs/M7_VERIFICATION_REPORT.md`
- `docs/M7_IMPLEMENTATION_REPORT.md`
- `docs/M6_VERIFICATION_REPORT.md`
- `docs/M5_VERIFICATION_REPORT.md`
- `docs/M4_VERIFICATION_REPORT.md`
- `docs/M3_VERIFICATION_REPORT.md`
- `docs/05_AI_AGENT_SPEC.md`
- `docs/04_DATA_MODEL.md`

Absent context documents:

- `docs/25_RETRIEVAL_SPEC.md`
- `docs/31_MVP_BOUNDARY.md`

Their absence is a documentation hygiene gap already consistent with post-MVP roadmap notes, not a blocker for this verification.

## Dataset Verification

Result: PASS

Evidence:

- Fixture path: `backend/tests/fixtures/evaluation/`
- `articles.json`: 3 small deterministic Article fixtures.
- Article fixture IDs:
  - `attention-basics`
  - `crb-formula`
  - `local-research-map`
- Article fixture shape includes `id`, `title`, `url`, `content`, and `metadata`.
- Metadata includes `date`, `category`, `references`, and `images`.
- `expected_cases.json`: 9 deterministic evaluation cases.
- Case task types present:
  - `rag_query`
  - `no_source`
  - `tutor_explain`
  - `tutor_derive`
  - `tutor_qa`
  - `tutor_quiz`
  - `tutor_research`
- All cases include auditable fields including `case_id`, `task_type`, `question`, `expected_source_article_ids`, `expected_refusal`, and `min_sources`.
- `zotero_links.json` contains fake article-to-Zotero metadata links only.
- `graph_expected.json` contains structural fake graph expectations only.
- No API keys, private paths, runtime output, DB files, or real Zotero library exports were found in the dataset.

## Metrics Verification

Result: PASS

Implemented metrics were verified in `backend/app/evaluation/models.py` and `backend/app/evaluation/metrics.py`:

- `retrieval_hit_at_k`
- `expected_article_hit`
- `expected_chunk_hit`
- `retrieved_source_count`
- `citation_required_pass_rate`
- `non_empty_sources_rate`
- `source_schema_valid_rate`
- `no_fake_source_rate`
- `no_source_refusal_rate`
- `unsupported_query_refusal_rate`
- `explain_grounded_rate`
- `derive_refusal_when_insufficient_rate`
- `qa_sources_required_rate`
- `quiz_question_sources_rate`
- `research_local_only_rate`
- `no_source_answer_fabrication_count`
- `answer_without_sources_count`
- `quiz_without_sources_count`

The metrics are deterministic structural checks. They do not use LLM-as-judge, external evaluator APIs, web calls, or subjective semantic scoring.

## Runner Verification

Result: PASS

Evidence from `backend/app/evaluation/runner.py`:

- Uses `TemporaryDirectory(prefix="scientific-spaces-eval-")` for runtime stores.
- Sets isolated Article, Zotero, Graph, Learning, and Tutor store paths.
- Sets `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=fake`.
- Sets `SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER=fake`.
- Uses existing `RagService` and `TutorService` without modifying their behavior.
- Does not require `OPENAI_API_KEY`.
- Does not import or call Playwright, browser providers, crawlers, web search, requests, httpx, or external evaluator clients.
- Writes only temporary runtime files during evaluation; default CLI execution writes no repository output.
- Optional `--output` is restricted to `eval_outputs/` or `evaluation_outputs/`, both ignored by `.gitignore`.

## RAG Evaluation Verification

Result: PASS

Evidence:

- `rag_attention_sources` returned non-empty sources.
- RAG sources include article ID/title/URL/section/chunk metadata.
- Expected article hit and retrieval hit@k are included in metrics.
- `rag_no_source_refusal` covers unsupported/no-source refusal.
- No-source answer fabrication count is `0`.
- CLI baseline:
  - Retrieval hit@k: `100%`
  - Citation required pass rate: `100%`
  - No-source refusal rate: `100%`
  - Source schema valid rate: `100%`
  - No fake source rate: `100%`

M3 RAG citation/no-source behavior was not modified by P0-005. `git show --name-only 5334ae642758ab1c1306592e7f11796a999e90db` confirms no `backend/app/rag/` files were changed.

## Tutor Evaluation Verification

Result: PASS

Coverage:

- `tutor_explain_attention`: grounded explain mode with sources and follow-up questions.
- `tutor_derive_crb_formula`: derive mode with explicit formula source.
- `tutor_derive_insufficient_formula`: derive mode refuses when formula evidence is insufficient.
- `tutor_qa_attention_sources`: QA mode with sources.
- `tutor_qa_no_source_refusal`: QA no-source refusal.
- `tutor_quiz_crb_sources`: quiz mode with per-question sources.
- `tutor_research_local_only`: research mode includes sources and local-only limitation text.

CLI baseline:

- Quiz source coverage: `100%`
- Research local-only checks: PASS
- Unsupported answer fabrications: `0`
- Answers without sources: `0`
- Quiz without sources: `0`
- Overall: PASS

M7 Tutor grounding/citation behavior was not modified by P0-005. `git show --name-only 5334ae642758ab1c1306592e7f11796a999e90db` confirms no `backend/app/tutor/` files were changed.

## CLI Verification

Result: PASS

Command:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Output:

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

The output contains case count, retrieval hit rate, citation pass rate, no-source refusal rate, source schema validity, quiz source coverage, research local-only checks, and final PASS/FAIL status.

## Documentation Verification

Result: PASS

`docs/RAG_TUTOR_EVALUATION_HARNESS.md` contains the required sections:

- Current Status
- Purpose
- Evaluation Scope
- Dataset
- Metrics
- How to Run
- Baseline Results
- Limitations
- Next Steps

The document explicitly states that the harness is a structural/groundedness baseline, does not represent full subjective answer quality, does not use LLM-as-judge, does not do web-scale evaluation, and uses a small fixture dataset.

README contains an evaluation harness section with the run command, fake-provider default, no-key requirement, and output artifact boundary.

## Artifact / Privacy Verification

Result: PASS

Commands:

```bash
git status --short
git ls-files | grep -E '(eval_outputs|evaluation_outputs|\.eval\.json|\.eval\.jsonl|\.env$|\.sqlite$|\.sqlite3$|\.db$|\.pdf$|node_modules|\.local_data|FAISS|faiss|embedding.*cache|knowledge_graph\.json|learning\.json|tutor.*\.json)' || true
```

Results:

- Working tree was clean before report creation.
- No tracked eval runtime output.
- No tracked DB/cache/runtime/private data.
- No tracked PDF, FAISS index, embedding cache, `.env`, `node_modules`, `.local_data`, runtime graph, learning, tutor, or Zotero store artifact.
- The committed evaluation fixture `zotero_links.json` is fake test metadata and not a real Zotero export.

## Freeze Protection

Result: PASS

P0-005 implementation commit changed only:

- `.gitignore`
- `README.md`
- `backend/app/evaluation/`
- `backend/tests/fixtures/evaluation/`
- `backend/tests/test_evaluation_metrics.py`
- `backend/tests/test_evaluation_runner.py`
- `docs/00_PROJECT_STATE.md`
- `docs/RAG_TUTOR_EVALUATION_HARNESS.md`
- `scripts/eval/run_rag_tutor_eval.py`

Frozen contracts were not modified:

- M1 crawler/parser/converter/sync
- M2 Article API
- M3 RAG citation/no-source behavior
- M4 Learning API
- M5 Zotero read-only boundary
- M6 Graph provenance/evidence behavior
- M7 Tutor grounding/citation policy

## Regression Test Evidence

Backend pytest:

```text
87 passed, 2 skipped in 3.78s
```

Frontend build:

```text
Next.js 15.5.20
Compiled successfully
Generated static pages (8/8)
```

Eval CLI:

```text
Overall: PASS
```

Runtime smoke with temporary stores:

```json
{
  "GET /health": 200,
  "GET /articles": {"status": 200, "count": 3},
  "POST /rag/index": {"status": 200, "article_count": 3, "chunk_count": 6},
  "POST /rag/query": {"status": 200, "sources": 3},
  "GET /learning/stats": 200,
  "GET /zotero/status": {"status": 200, "read_only": true},
  "GET /graph": {"status": 200, "nodes": 64},
  "POST /tutor/ask": {"status": 200, "sources": 8, "refusal": null}
}
```

CI:

- Run: `28940008254`
- URL: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28940008254`
- Event: `push`
- Head SHA: `5334ae642758ab1c1306592e7f11796a999e90db`
- Conclusion: `success`

CI coverage:

- Backend pytest: PASS
- Frontend build: PASS
- Docker compose smoke: skipped on `push` by workflow condition; Docker smoke remains covered by manual release/tag evidence.

## Findings

### Blockers

None.

### Medium Risks

None.

### Low Risks

- The fixture dataset is intentionally small and can overfit structural checks.
- Unsupported-query refusal is primarily tested through no-source cases, not broad semantic out-of-domain detection over a populated corpus.
- Push CI skips Docker compose smoke by design; Docker smoke is covered for workflow_dispatch/tag release evidence.

### Accepted Limitations

- Fake provider baseline does not represent real LLM quality.
- Structural metrics do not evaluate language fluency, proof completeness, or subjective answer quality.
- No LLM-as-judge is used.
- No web-scale evaluation is performed.
- Real-provider evaluation remains a future env-gated task.

## Final Recommendation

A: Evaluation harness verified
