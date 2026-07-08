# M6 Verification Alignment

## Scope

This run executes the M6 Verification Gate only.

Allowed changes:

- `alignment.md`
- `docs/M6_VERIFICATION_REPORT.md`
- `docs/00_PROJECT_STATE.md` only if M6 Verification passes
- `.gitignore` only if graph runtime artifacts are not ignored

Forbidden changes:

- M6 implementation code
- M1-M5 frozen implementation code
- M7 AI Tutor functionality
- Verification standard changes
- Runtime graph data, cache, PDF, HTML, image, profile, trace, local data, or secrets

## Evidence Commands

- `uv run --project backend --extra dev pytest -q`
- `npm run build`
- Runtime smoke with temporary article, Zotero, learning, vector, and graph files under `/tmp`
- Freeze protection scan for M6 commit against M1-M5 frozen paths
- M7 scope leak scan across `backend/app` and `frontend/src`
- Forbidden artifact scan

## Decision

M6 Verification is blocked by a concept-node source metadata gap:

- Runtime `/graph/nodes/concept:attention` returned metadata `{"normalized": "attention"}`.
- Concept source traceability exists on `mentions` edge evidence.
- The verification prompt requires source information in concept node metadata, so this is recorded as a blocker rather than fixed in this verification task.
