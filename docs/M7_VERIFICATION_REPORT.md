# M7 Verification Report

## Current Status

| Item | Result | Evidence |
|---|---|---|
| M7 Implementation | PASS | Commit `97bb7e108b7ea28809c0c8c42272c3851d4fce28` is present on `main`. |
| M7 Verification | PASS | Model, orchestration, citation policy, modes, API, frontend, regressions, freeze, and artifact checks passed. |
| MVP Status | Complete | M0-M7 implementation and verification gates are complete. |

This is a verification gate only. No M7 implementation code, M1-M6 frozen implementation code, or verification standards were changed by this gate.

Required context documents were read where present:

- `docs/00_PROJECT_STATE.md`
- `milestones/M7_AI_TUTOR.md`
- `docs/M7_IMPLEMENTATION_REPORT.md`
- `docs/M6_VERIFICATION_REPORT.md`
- `docs/M5_VERIFICATION_REPORT.md`
- `docs/M4_VERIFICATION_REPORT.md`
- `docs/M3_VERIFICATION_REPORT.md`
- `docs/M2_VERIFICATION_REPORT.md`
- `docs/M1_FINAL_FREEZE_REPORT.md`
- `docs/04_DATA_MODEL.md`
- `docs/05_AI_AGENT_SPEC.md`
- `docs/08_KNOWLEDGE_PIPELINE.md`
- `docs/10_UI_SPEC.md`

Missing or renamed context documents remain documentation gaps, not M7 blockers:

- `milestones/M7_AI_RESEARCH_TUTOR.md` is absent.
- Repository contains `milestones/M7_AI_TUTOR.md`.
- `docs/15_ACCEPTANCE.md` is absent.
- `docs/31_MVP_BOUNDARY.md` is absent.

## Tutor Model Verification

Implementation:

- `backend/app/tutor/models.py`

Result:

- PASS

Verified `TutorRequest` fields:

- `question`
- `mode`
- `article_id`
- `node_id`
- `top_k`
- `include_graph_context`
- `include_zotero_context`

Verified `TutorResponse` fields:

- `answer`
- `mode`
- `sources`
- `graph_context`
- `zotero_context`
- `follow_up_questions`
- `refusal_reason`

Verified `TutorSource` fields:

- `source_type`
- `source_id`
- `title`
- `url`
- `section_title`
- `chunk_index`
- `evidence`
- `metadata`

Verified `QuizQuestion` fields:

- `question`
- `options`
- `correct_answer`
- `explanation`
- `sources`

Verified `TutorSession` fields:

- `session_id`
- `mode`
- `article_id`
- `node_id`
- `created_at`
- `updated_at`
- `turns`

Model boundaries:

- Tutor session model is independent from M4 `LearningSession`.
- M3 RAG response contract is unchanged.
- M6 graph schema is unchanged.
- Sources are structured dictionaries from `TutorSource.to_dict()`.
- Model and citation-policy behavior is covered by `backend/tests/test_tutor.py`.

## Orchestration Verification

Implementation:

- `backend/app/tutor/service.py`

Result:

- PASS

Verified behavior:

- M3 article chunks are the primary factual source.
- The service builds `article_chunk` sources from retrieved chunks.
- M6 graph nodes and edges are added as context/evidence, but cannot replace article citations.
- M5 Zotero metadata is read through the provider and link store, and remains supplemental metadata.
- M4 learning state is returned inside `graph_context.learning_state` as personalization-only context.
- Runtime smoke confirmed `learning_state` was not present in `TutorResponse.sources`.
- Default providers are `FakeEmbeddingProvider` and `FakeLLMProvider`.
- Real LLM use is optional through `SCIENTIFIC_SPACES_TUTOR_LLM_PROVIDER=openai`.
- Tests do not require a real API key.
- No article/RAG source returns refusal instead of an answer.
- M7 code does not call Playwright, requests/httpx, crawlers, web search, paper download, or Zotero write APIs.

## Citation Policy Verification

Implementation:

- `backend/app/tutor/policy.py`

Result:

- PASS

Verified behavior:

- `explain`, `derive`, `qa`, and `research` substantive answers require sources.
- The citation guard requires at least one `article_chunk` source for substantive answers.
- Graph node/edge sources and Zotero item sources can supplement but cannot be the only citation.
- Learning state is never accepted as a factual citation source.
- Answer without sources returns `无法基于当前资料回答。`.
- Research no-source path returns `无法基于当前资料形成可靠研究建议。`.
- Quiz questions include sources; no-source quiz returns zero questions and does not fabricate items.
- No fake citation construction was found in M7 code.

## Mode Verification

### Explain

Result:

- PASS

Runtime evidence:

- `POST /tutor/ask mode=explain`: 200
- `sources`: 9
- Includes `article_chunk` sources.
- Includes graph context and follow-up questions.
- No-source explain returns `无法基于当前资料回答。`.

### Derive

Result:

- PASS

Runtime and test evidence:

- `POST /tutor/ask mode=derive`: 200
- Includes `article_chunk` formula/source context.
- Answer includes `分步推导` and states that unsupported derivation steps are not filled in.
- `backend/tests/test_tutor.py::test_tutor_derive_refuses_when_formula_source_is_missing` covers insufficient formula-source refusal.

### QA

Result:

- PASS

Runtime evidence:

- `POST /tutor/ask mode=qa`: 200
- Includes `article_chunk` sources.
- Answer includes direct answer text and `为什么重要`.
- Follow-up questions are returned.
- M3 RAG query still returns sources.
- Isolated empty-data RAG check returns `无法基于当前资料回答。` with no sources.

### Quiz

Result:

- PASS

Runtime evidence:

- `POST /tutor/quiz`: 200
- Generated 2 questions.
- Each question included a source.
- `correct_answer` and `explanation` are tied to the source.
- `POST /tutor/quiz` with missing article returns `questions=[]` and `total=0`.

Boundary verification:

- No mastery prediction.
- No spaced repetition.
- No adaptive tutoring algorithm.
- M4 learning model was not changed.

### Research

Result:

- PASS

Runtime evidence:

- `POST /tutor/ask mode=research`: 200
- Includes `article_chunk` sources.
- Answer includes next reading guidance and source-gap text.
- Graph neighbors are available through `graph_context`.
- Zotero metadata is available through `zotero_context` when links exist.
- No-source research returns `无法基于当前资料形成可靠研究建议。`.

Boundary verification:

- No web search.
- No paper download.
- No Zotero library writes.
- No source credibility scoring.
- The answer states it is not a complete literature review.

## API Verification

Implementation:

- `backend/app/api/tutor.py`

Result:

- PASS

Verified endpoints:

- `POST /tutor/ask`
- `POST /tutor/quiz`
- `GET /tutor/sessions`
- `POST /tutor/sessions`
- `GET /tutor/sessions/{session_id}`

Runtime evidence:

- `POST /tutor/ask` explain/derive/qa/research returned stable response shape.
- `POST /tutor/quiz` returned `questions` and `total`.
- `GET /tutor/sessions` returned `items` and `total`.
- `POST /tutor/sessions` created a local summary session.
- `GET /tutor/sessions/{session_id}` returned the created session.
- `GET /tutor/sessions/missing-session` returned 404 with `Tutor session not found`.
- Existing M2-M6 APIs remained available.

## Session Storage Verification

Implementation:

- `backend/app/tutor/store.py`

Result:

- PASS

Verified behavior:

- Default path is `.local_data/scientific_spaces/tutor_sessions.json`.
- `SCIENTIFIC_SPACES_TUTOR_FILE` isolates test/runtime storage.
- Empty store returns an empty session list and does not crash.
- Session store is independent from M4 `LearningSession`.
- `.gitignore` covers `.local_data/`, `backend/.local_data/`, `.env`, cache, and dependency directories.
- No runtime session data is tracked.

Known risk:

- Store uses simple JSON file persistence and does not implement production multi-user locking or damaged JSON recovery.

## Frontend Verification

Implementation:

- `frontend/src/app/tutor/page.tsx`
- `frontend/src/components/TutorView.tsx`
- `frontend/src/lib/tutor.ts`

Result:

- PASS

Verified behavior:

- `/tutor` builds successfully.
- `/tutor` runtime smoke returns 200.
- Mode selector contains `explain`, `derive`, `qa`, `quiz`, and `research`.
- Question input exists.
- Article ID and Graph Node inputs exist.
- Answer/refusal can be displayed.
- Sources/citations are displayed through `SourceList`.
- Graph and Zotero context are displayed as counts.
- Follow-up questions are displayed.
- Quiz mode displays question, answer, explanation, and sources.
- Existing `/`, `/articles`, `/zotero`, and `/graph` routes return 200.

## Regression Verification

Result:

- PASS

M2 Article API:

- `GET /articles`: 200, total 2 in smoke data.
- `GET /articles?q=Attention`: 200, total 1.
- `GET /articles/attention-001`: 200 with `id`, `title`, `url`, `content`, and `metadata`.

M3 RAG API:

- `POST /rag/index`: 200, chunk count 6.
- `POST /rag/query`: 200, sources returned.
- Empty article dataset check returned `无法基于当前资料回答。` with no sources.

M4 Learning API:

- `GET /learning/state`: 200.
- `GET /learning/stats`: 200, reading count 1 after smoke update.

M5 Zotero API:

- `GET /zotero/status`: 200, read-only true.
- `GET /zotero/items?q=attention`: 200.

M6 Graph API:

- `GET /graph`: 200, nodes and edges returned.
- `GET /graph/nodes?q=attention`: 200.
- `GET /graph/nodes/concept:attention`: 200, metadata included provenance keys `normalized`, `source_count`, `sources`, and `truncated`.

## Freeze Protection

Result:

- PASS

Verification evidence:

- Git diff against `HEAD` showed no changes in M1-M6 frozen backend paths or API/UI contract files.
- Frozen paths checked included crawler, parser, converter, storage, validation, export, RAG, learning, Zotero, graph, and sync modules.
- M7 verification did not modify implementation code.

Frozen contract status:

- M1 frozen paths: unchanged.
- M2 Article API, Reader UI, search behavior, and reading history boundary: unchanged.
- M3 RAG API, citation policy, no-source behavior, chunking, embedding, vector, and LLM provider contracts: unchanged.
- M4 learning state, bookmarks, notes, sessions, stats, and local storage boundary: unchanged.
- M5 Zotero read-only provider, status/search/item/export APIs, and link storage: unchanged.
- M6 graph API, graph model, deterministic builder, concept provenance metadata, and edge evidence policy: unchanged.

## Artifact and Privacy Check

Result:

- PASS

Git scans found no tracked:

- real tutor session data
- private user study data
- runtime tutor store
- runtime graph store
- real article corpus export
- real Zotero library data
- FAISS index/cache
- embedding cache
- `.env`
- API keys
- PDF
- downloaded full HTML
- images
- trace/profile artifacts
- cache
- `node_modules`
- local runtime data

Only ignored local dependency directories were present:

- `backend/.venv/`
- `frontend/node_modules/`

## Test Evidence

Backend:

```text
uv run --project backend --extra dev pytest -q
63 passed, 2 skipped in 3.55s
```

Frontend:

```text
npm run build
Next.js 15.5.20 build completed successfully.
Routes generated: /, /articles, /articles/[id], /graph, /tutor, /zotero.
```

Runtime smoke:

- Backend smoke: 25 checks passed.
- Frontend smoke: `/`, `/articles`, `/zotero`, `/graph`, and `/tutor` returned 200.

Docker:

- `docker` is unavailable in the current environment: `docker: command not found`.
- This is recorded as an environment limitation, not a blocker, because backend tests, frontend build, backend runtime smoke, and frontend route smoke passed.

## Known Risks

- Fake provider is the default; real LLM usage requires environment configuration.
- Local tutor session store is not production multi-user storage.
- Tutor quality depends on available RAG, graph, Zotero, and article source quality.
- Research mode is local-only and not an exhaustive web or literature review.
- Missing `docs/15_ACCEPTANCE.md`, `docs/31_MVP_BOUNDARY.md`, and renamed M7 milestone document remain documentation hygiene gaps.

## Final Recommendation

A: MVP Complete
