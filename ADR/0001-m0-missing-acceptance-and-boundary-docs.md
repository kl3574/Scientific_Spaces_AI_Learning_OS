# ADR 0001: M0 Execution With Missing Acceptance and Boundary Documents

## Status

Accepted for M0 execution.

## Context

The M0 execution prompt requires reading:

- `docs/15_ACCEPTANCE.md`
- `docs/31_MVP_BOUNDARY.md`

Both files are missing in the current repository state.

The engineering constraint for this task forbids directly modifying existing design documents and milestone documents. Specification gaps should be recorded as ADRs instead of changing the normative documents in place.

## Decision

For M0 only, the execution boundary is derived from:

- `milestones/M0_FOUNDATION.md`
- the confirmed task alignment in `alignment.md`
- the user's explicit M0 boundary constraints

Missing acceptance and MVP boundary documents are recorded as a specification gap in this ADR.

## Consequences

- M0 implementation remains limited to engineering skeleton work.
- No M1 crawler, parser, storage, M2 reader/search, or M3 RAG/embedding/vector/LLM behavior is implemented.
- Future work should add the missing acceptance and MVP boundary documents through an explicit documentation task.
