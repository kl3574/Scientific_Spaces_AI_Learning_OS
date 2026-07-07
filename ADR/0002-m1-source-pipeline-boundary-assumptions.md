# ADR 0002: M1 Source Pipeline Boundary Assumptions

## Status

Accepted for M1 execution.

## Context

The M1 execution prompt requires reading:

- `docs/15_ACCEPTANCE.md`
- `docs/31_MVP_BOUNDARY.md`

Both files are missing in the current repository state. Existing project constraints forbid modifying PRD, TDD, SOP, and milestone documents during this implementation task.

## Decision

For M1 only, the implementation boundary is derived from:

- `milestones/M1_SOURCE_PIPELINE.md`
- `docs/08_KNOWLEDGE_PIPELINE.md`
- `docs/11_SOURCE_POLICY.md`
- the confirmed task alignment in `alignment.md`
- the user's explicit M1 restrictions

M1 implements only the Scientific Spaces source pipeline:

- crawler
- parser
- Markdown converter
- Article storage
- validation
- sync entry point

M1 does not implement Article API, frontend reader, search UI, RAG, embeddings, FAISS, LLM integrations, learning state, Zotero, knowledge graph, or AI tutor behavior.

## Consequences

- Missing acceptance and MVP boundary documents remain a documentation gap for a future documentation task.
- Runtime cache, downloaded HTML, and imported article data must stay outside committed source files.
- The storage format is intentionally simple and local so future milestones can replace it behind the same Article boundary.
