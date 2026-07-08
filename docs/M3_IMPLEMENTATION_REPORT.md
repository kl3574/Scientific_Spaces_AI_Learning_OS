# M3 Implementation Report

## 1. Current Status

| Item | Status | Evidence |
|---|---|---|
| M0 Engineering Foundation | PASS | Existing backend/frontend/Docker/CI foundation. |
| M1 Final Freeze | PASS | `docs/00_PROJECT_STATE.md` records `M1 Freeze Passed`. |
| M2 Verification | PASS | `docs/00_PROJECT_STATE.md` records `M2 Verification Passed`. |
| M3 Grounded RAG Assistant | PASS | Markdown chunking, fake embedding, FAISS search, LLM abstraction, and citation-grounded RAG API implemented. |

This milestone implements backend M3 RAG capability only. It does not implement M4 Learning Management, M5 Zotero, M6 Knowledge Graph, M7 AI Tutor, autonomous research agents, quizzes, bookmarks, mastery, or conversation history.

## 2. Implemented Features

- Markdown-aware document chunking.
- Fake deterministic embedding provider for tests and default local use.
- Optional OpenAI-compatible embedding provider behind environment configuration.
- In-memory FAISS vector search.
- Fake LLM provider for default local/test use.
- Optional OpenAI-compatible chat provider behind environment configuration.
- Citation-grounded RAG answer service.
- Backend API:
  - `POST /rag/index`
  - `POST /rag/query`

## 3. Chunking Strategy

Module:

- `backend/app/rag/chunking.py`

Chunking is Markdown-aware:

- Splits primarily on Markdown headings.
- Preserves section titles.
- Keeps paragraphs, equation blocks, and fenced code blocks inside their section chunk.
- Does not use fixed character slicing as the primary strategy.

Each chunk carries source metadata:

- `article_id`
- `article_title`
- `article_url`
- `section_title`
- `chunk_index`
- `content`

Formula/code preservation:

- `$$ ... $$` blocks are not split.
- Fenced code blocks are not split.

## 4. Embedding Provider Design

Module:

- `backend/app/rag/embeddings.py`

Providers:

- `EmbeddingProvider` protocol.
- `FakeEmbeddingProvider` for deterministic local/test embeddings.
- `OpenAICompatibleEmbeddingProvider` for optional real embeddings behind env config.

Default behavior:

- Tests and local RAG API use `FakeEmbeddingProvider`.
- No API key is required for tests or default local use.
- API keys are read from environment only and are not committed.

## 5. Vector Search Design

Module:

- `backend/app/rag/vector_store.py`

Implementation:

- Uses FAISS `IndexFlatL2`.
- Stores chunk embeddings in an in-memory FAISS index.
- Maintains chunk metadata side-by-side with FAISS row order.
- Supports `top_k` retrieval.
- Returns an empty result list for empty indexes.

Artifact policy:

- FAISS indexes are built locally in memory.
- No FAISS index files or embedding caches are committed.

## 6. LLM Provider Design

Modules:

- `backend/app/llm/provider.py`
- `backend/app/llm/fake.py`

Providers:

- `LLMProvider` protocol with `chat()`.
- `FakeLLMProvider` for deterministic tests/local use.
- `OpenAICompatibleLLMProvider` for optional real chat completion behind env config.

Design decision:

- Embedding is separated into `EmbeddingProvider`.
- Chat is separated into `LLMProvider`.
- No provider API key is required unless an OpenAI-compatible provider is explicitly instantiated and called.

## 7. Citation Policy

Citation policy:

- Any substantive RAG answer must include `sources`.
- Each source includes:
  - `article_id`
  - `article_title`
  - `article_url`
  - `section_title`
  - `chunk_index`

No-source behavior:

- If no chunks are available or retrieval returns no source, the answer is:
  - `无法基于当前资料回答。`
- The service does not fabricate an answer.
- `sources` is empty only for this explicit no-source refusal path.

## 8. API Contract

### `POST /rag/index`

Builds or refreshes the local in-memory RAG index from the existing M1 Article storage.

Response:

```json
{
  "article_count": 1,
  "chunk_count": 2
}
```

### `POST /rag/query`

Request:

```json
{
  "question": "什么是Attention？",
  "top_k": 5
}
```

Response:

```json
{
  "answer": "...",
  "sources": [
    {
      "article_id": "...",
      "article_title": "...",
      "article_url": "...",
      "section_title": "...",
      "chunk_index": 0
    }
  ]
}
```

Behavior:

- Builds the index lazily if `/rag/query` is called before `/rag/index`.
- Uses fake providers by default.
- Does not modify M2 `GET /articles` or `GET /articles/{id}` contracts.

## 9. Frontend Integration

Frontend integration was intentionally not added in M3.

Reason:

- The task allows backend-only M3 scope if frontend integration is deferred.
- This keeps M3 focused on grounded retrieval, citation behavior, and backend API contracts.

Deferred candidate:

- M3.1 lightweight Article Detail Ask box using `POST /rag/query`.

## 10. Test Evidence

### Targeted M3 Tests

Command:

```bash
uv run --project backend --extra dev pytest backend/tests/test_rag_chunking.py backend/tests/test_rag_vector_search.py backend/tests/test_llm_provider.py backend/tests/test_rag_api.py -q
```

Result:

```text
9 passed
```

Coverage:

- Markdown chunking.
- Equation/code block preservation.
- Deterministic fake embeddings.
- FAISS vector search.
- Empty vector-store behavior.
- Fake LLM provider.
- RAG API index/query.
- Citation-required answer.
- No-source refusal.

### Full Backend Tests

Command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
37 passed, 2 skipped in 0.29s
```

### Frontend Build

Command:

```bash
cd frontend && npm run build
```

Result:

```text
✓ Compiled successfully
✓ Generating static pages (5/5)
```

### Runtime Smoke

Temporary fixture article data was created under `/tmp/scientific-spaces-m3-smoke`.

Command summary:

```bash
curl -fsS http://localhost:8000/health
curl -fsS -X POST http://localhost:8000/rag/index
curl -fsS -X POST http://localhost:8000/rag/query \
  -H 'Content-Type: application/json' \
  --data '{"question":"什么是Attention？","top_k":3}'
```

Observed:

```json
{"article_count":1,"chunk_count":2}
```

Query returned:

- grounded answer mentioning `Attention`
- non-empty `sources`
- source article title, URL, section title, and chunk index

No-source smoke:

```json
{
  "answer": "无法基于当前资料回答。",
  "sources": []
}
```

## 11. Known Risks

1. In-memory index lifecycle
   - The FAISS index is process-local and must be rebuilt after backend restart.

2. Fake provider quality
   - Default fake embeddings and fake LLM are deterministic and testable, but not semantically equivalent to production models.

3. Optional provider integration
   - OpenAI-compatible providers are present but not live-tested because no API key is required or committed.

4. Frontend RAG entry point
   - No frontend Ask box is included in M3. A lightweight UI can be added as an M3.1 task.

5. Missing retrieval/boundary docs
   - `docs/25_RETRIEVAL_SPEC.md`, `docs/15_ACCEPTANCE.md`, and `docs/31_MVP_BOUNDARY.md` are absent.
   - M3 scope was derived from `milestones/M3_RAG_SYSTEM.md`, M2 verification, M1 freeze, AI agent spec, knowledge pipeline, and the user's explicit M3 constraints.

6. M1/M2 freeze governance
   - M3 did not change frozen M1 modules or M2 Article API/Reader UI contracts.
   - `backend/app/main.py` was changed only to register the new M3 router and allow `POST` CORS methods.

## 12. M4 Readiness

M4 readiness result:

- M3 backend RAG capability is ready for a later learning-management layer.
- M4 should start as a separate milestone.
- M4 must not back-edit frozen M1/M2 contracts or overload M3 citation answers into mastery/progress state without an explicit M4 design.
