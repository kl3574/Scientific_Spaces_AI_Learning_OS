# M7 Implementation Report

## Current Status

| Item | Result | Evidence |
|---|---|---|
| M0 Engineering Foundation | PASS | Previous project state records M0 completion. |
| M1 Source Pipeline | PASS | `docs/M1_FINAL_FREEZE_REPORT.md` records M1 final freeze. |
| M2 Scientific Reader | PASS | `docs/M2_VERIFICATION_REPORT.md` records M2 verification. |
| M3 Grounded RAG Assistant | PASS | `docs/M3_VERIFICATION_REPORT.md` records M3 verification. |
| M4 Learning Management | PASS | `docs/M4_VERIFICATION_REPORT.md` records M4 verification. |
| M5 Zotero Integration | PASS | `docs/M5_VERIFICATION_REPORT.md` records M5 verification. |
| M6 Knowledge Graph | PASS | `docs/M6_VERIFICATION_REPORT.md` records M6 verification. |
| M7 AI Research Tutor | PASS | Tutor model, service, API, frontend, tests, and smoke checks are implemented. |

This task implements only M7 AI Research Tutor behavior. It does not modify frozen M1-M6 backend implementation modules and does not implement crawler, reader, RAG indexing changes, learning-system expansion, Zotero writes, or knowledge-graph schema revisions.

Required context documents were read where present:

- `docs/00_PROJECT_STATE.md`
- `milestones/M7_AI_TUTOR.md`
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

Missing or renamed context documents were recorded as documentation gaps, not M7 blockers:

- `milestones/M7_AI_RESEARCH_TUTOR.md` is absent.
- Repository contains `milestones/M7_AI_TUTOR.md`.
- `docs/15_ACCEPTANCE.md` is absent.
- `docs/31_MVP_BOUNDARY.md` is absent.

## Implemented Features

M7 adds a tutor layer over existing M2-M6 capabilities:

- Tutor request, response, source, quiz, turn, and session models.
- Tutor orchestration service.
- Grounding and refusal policy.
- Explain, derive, qa, quiz, and research modes.
- Tutor session summary storage in local project data.
- Frontend tutor page and navigation entry.

The default model provider is deterministic and local-testable. A real OpenAI-compatible provider remains optional through environment configuration and no API key is committed.

## Tutor Data Model

Implementation:

- `backend/app/tutor/models.py`

Primary model types:

- `TutorRequest`
- `TutorResponse`
- `TutorSource`
- `QuizQuestion`
- `TutorTurn`
- `TutorSession`

Supported modes:

- `explain`
- `derive`
- `qa`
- `quiz`
- `research`

Source types:

- `article_chunk`
- `graph_node`
- `graph_edge`
- `zotero_item`
- `learning_state`
- `article_metadata`

## Tutor Orchestration Strategy

Implementation:

- `backend/app/tutor/service.py`

The orchestration flow is:

1. Retrieve grounded article chunks through the existing M3 chunking, embedding, and FAISS vector search components.
2. Optionally collect M6 graph node and edge context.
3. Optionally collect M5 Zotero metadata links in read-only mode.
4. Collect M4 learning state as personalization-only context.
5. Call the configured LLM provider.
6. Enforce citation policy before returning a response.

The service reuses existing M2-M6 read interfaces and does not change their storage schemas or contracts.

## Grounding and Citation Policy

Implementation:

- `backend/app/tutor/policy.py`

Policy:

- All substantive tutor answers require at least one `article_chunk` source.
- Graph nodes, graph edges, Zotero items, and learning state can supplement context but cannot be the only factual citation.
- If no source exists, the tutor returns: `无法基于当前资料回答。`
- Derive mode refuses with `当前资料不足以完整推导。` when retrieved context lacks formula evidence.
- Quiz questions include sources.
- Research mode is local-only, does not claim exhaustive literature review, and returns `无法基于当前资料形成可靠研究建议。` when no local sources exist.

## Explain Mode

Implementation:

- `TutorService.answer()` with `mode="explain"`

Behavior:

- Retrieves relevant article chunks.
- Adds graph neighbors when a node is provided.
- Returns a concise explanation, key points, sources, and follow-up questions.
- Refuses if article sources are unavailable.
- Does not extend concepts beyond retrieved local evidence.

## Derive Mode

Implementation:

- `TutorService.answer()` with `mode="derive"`

Behavior:

- Uses only retrieved article chunks and graph formula nodes as derivation evidence.
- Checks formula context before producing a derivation-style answer.
- Refuses with `当前资料不足以完整推导。` when formula evidence is missing.
- Includes sources and follow-up questions for checking formula support.

## QA Mode

Implementation:

- `TutorService.answer()` with `mode="qa"`

Behavior:

- Wraps existing M3 retrieval with tutor-oriented answer formatting.
- Includes direct answer text, why-it-matters guidance, sources, and suggested next questions.
- Uses the same no-source refusal boundary as M3 grounded answering.

## Quiz Mode

Implementation:

- `TutorService.quiz()`
- `POST /tutor/quiz`

Behavior:

- Generates lightweight concept-check questions from retrieved article chunks.
- Each question includes `question`, `options`, `correct_answer`, `explanation`, and `sources`.
- Returns no questions when no article source is available.
- Does not implement mastery prediction, spaced repetition, or adaptive tutoring algorithms.

## Research Guidance Mode

Implementation:

- `TutorService.answer()` with `mode="research"`

Behavior:

- Uses local Article/RAG chunks as factual grounding.
- Adds linked Zotero metadata in read-only mode when available.
- Uses graph context to surface related local concepts.
- States local source gaps and does not claim exhaustive literature review.
- Does not perform web search, paper download, Zotero writes, or external source ingestion.
- Refuses with `无法基于当前资料形成可靠研究建议。` when local sources are unavailable.

## API Contract

Implementation:

- `backend/app/api/tutor.py`
- Registered in `backend/app/main.py`

Endpoints:

- `POST /tutor/ask`
- `POST /tutor/quiz`
- `GET /tutor/sessions`
- `POST /tutor/sessions`
- `GET /tutor/sessions/{session_id}`

`POST /tutor/ask` returns:

- `answer`
- `mode`
- `sources`
- `graph_context`
- `zotero_context`
- `follow_up_questions`
- `refusal_reason`

`POST /tutor/quiz` returns:

- `questions`
- `total`

Session endpoints store only local session summaries and do not write long-term private user data into the repository.

## Frontend Integration

Implementation:

- `frontend/src/app/tutor/page.tsx`
- `frontend/src/components/TutorView.tsx`
- `frontend/src/lib/tutor.ts`
- `frontend/src/components/ReaderShell.tsx`

Frontend behavior:

- Adds `/tutor`.
- Supports mode selection for explain, derive, qa, quiz, and research.
- Accepts optional article and graph node IDs.
- Displays tutor answer, follow-up questions, sources, graph context counts, Zotero context count, quiz questions, and local tutor session summary count.
- Does not add AI chat to Reader pages or modify M2 Reader behavior.

## Test Evidence

Backend tests:

```text
uv run --project backend --extra dev pytest -q
63 passed, 2 skipped in 3.53s
```

Frontend build:

```text
npm run build
Next.js 15.5.20 build completed successfully.
Routes generated: /, /articles, /articles/[id], /graph, /tutor, /zotero.
```

Runtime smoke:

Backend:

- `GET /health`: 200
- `GET /articles`: 200, total 2
- `POST /rag/index`: 200, chunk count 6
- `POST /rag/query`: 200, sources returned
- `GET /learning/stats`: 200
- `GET /zotero/status`: 200, read-only true
- `POST /graph/build`: 200
- `GET /graph`: 200
- `POST /tutor/ask` explain: 200, grounded sources returned
- `POST /tutor/ask` derive: 200, grounded sources returned
- `POST /tutor/ask` qa: 200, grounded sources returned
- `POST /tutor/ask` research: 200, grounded sources returned
- `POST /tutor/ask` research no-source: 200, `无法基于当前资料形成可靠研究建议。`
- `POST /tutor/quiz`: 200, sourced questions returned
- `GET /tutor/sessions`: 200

Frontend:

- `/`: 200
- `/articles`: 200
- `/zotero`: 200
- `/graph`: 200
- `/tutor`: 200

## Regression Coverage

Implementation tests:

- `backend/tests/test_tutor.py`

Coverage includes:

- Tutor model validation.
- Citation policy source requirement.
- Explain, derive, qa, and research grounded responses.
- Derive insufficient-source refusal.
- No-source refusal.
- Quiz source requirement.
- Tutor session endpoints.
- M2 Article API regression.
- M3 RAG API regression.
- M4 Learning API regression.
- M5 Zotero API regression.
- M6 Graph API regression.

## Scope Boundary

M7 is limited to the tutor layer:

- Grounded tutor ask.
- Explain, derive, qa, quiz, and research modes.
- Tutor API.
- Tutor frontend route.
- M1-M6 regression protection.

M7 does not implement:

- Autonomous web research.
- Browser/search crawling.
- External source ingestion.
- Automatic paper download.
- Automatic Zotero writes.
- Hidden mastery prediction.
- Adaptive tutoring beyond simple local state context.
- Production multi-user analytics.
- M1-M6 frozen contract changes.

## Freeze Protection

Frozen M1-M6 backend module diff check:

```text
No changes under:
backend/app/crawler
backend/app/parser
backend/app/converter
backend/app/storage
backend/app/validation
backend/app/export
backend/app/rag
backend/app/learning
backend/app/zotero
backend/app/graph
```

Only M7-specific backend additions and route registration were made:

- `backend/app/tutor/`
- `backend/app/api/tutor.py`
- `backend/app/main.py`

Frontend changes were limited to adding the tutor route and navigation entry.

## Artifact Check

No new PDF, downloaded HTML, article export, image, trace, profile, cache, `.env`, API key, `node_modules`, FAISS index, embedding cache, graph store, Zotero data, or runtime tutor session data is tracked for this task.

Existing tracked HTML fixtures remain pre-existing parser fixtures and were not introduced by M7.

Ignored local dependencies remain:

- `backend/.venv/`
- `frontend/node_modules/`

## Known Risks

- Fake LLM provider is deterministic and suitable for local tests, but production answer quality depends on an optional real provider configuration.
- Tutor answer quality is bounded by existing Article, RAG, graph, Zotero, and learning data quality.
- Research mode is local-only and cannot replace a full literature review.
- Learning state is personalization-only and must not become a factual citation source.
- Missing `docs/15_ACCEPTANCE.md`, `docs/31_MVP_BOUNDARY.md`, and the renamed M7 milestone document remain documentation hygiene gaps.

## Final Verification Readiness

Result:

- M7 Implementation: PASS

Recommendation:

- Next gate should be M7 Verification Gate.
