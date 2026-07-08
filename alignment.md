# Task Alignment - M5 Verification Gate

## 1. Background

Project: `kl3574/Scientific_Spaces_AI_Learning_OS`

Current milestone evidence:

- M0 Engineering Foundation: PASS
- M1 Source Pipeline: PASS
- M1 Final Freeze: PASS
- M2 Scientific Reader: PASS
- M2 Verification: PASS
- M3 Grounded RAG Assistant: PASS
- M3 Verification: PASS
- M4 Learning Management: PASS
- M4 Verification: PASS
- M5 Zotero Integration: IMPLEMENTED

M5 implementation commit:

- `f46ab8b72cb431b498d1e1f1c5bb641f40cbe466`

This task verifies M5 only. It must not implement M6 Knowledge Graph, M7 AI Tutor, Zotero library writes, citation graphs, paper graphs, or autonomous research agents.

## 2. Scope

Allowed changes:

- `alignment.md`
- `docs/M5_VERIFICATION_REPORT.md`
- `docs/00_PROJECT_STATE.md` only if verification passes
- `.gitignore` only if local runtime data paths are not ignored

Forbidden changes:

- M5 implementation code
- M1/M2/M3/M4 frozen implementation code
- M5 verification standard
- M6/M7 features
- Zotero library writes
- real Zotero data, BibTeX large exports, local runtime data, API keys, FAISS indexes, embedding caches, PDFs, HTML dumps, images, traces, profiles, caches, or `node_modules`

## 3. Gate Focus

The verification gate must confirm:

1. Zotero provider abstraction exists and is read-only by default.
2. `FakeZoteroProvider` works and tests do not require Zotero Desktop.
3. No-Zotero or unavailable local API behavior is graceful and does not crash.
4. Optional local API provider is env-enabled only and does not write to Zotero.
5. Zotero status/search/item/BibTeX export APIs work.
6. Zotero item key and BibTeX key are clearly distinguished.
7. Article-Zotero link create/list/delete and duplicate behavior work.
8. Link storage is project-local, env-isolated, ignored by git, and separate from Article/Learning models.
9. Frontend `/zotero` and Article Detail related papers panel build and smoke.
10. M2/M3/M4 API regressions pass.
11. M1/M2/M3/M4 frozen contracts are not broken.
12. No M6/M7 scope leak or forbidden artifact exists.

## 4. Execution Evidence

Verification will use:

- Required document reads where present.
- Zotero helper `status --json` probe only.
- Code inspection of `backend/app/zotero/`, `backend/app/api/zotero.py`, M5 tests, and M5 frontend files.
- Backend tests:
  - `uv run --project backend --extra dev pytest -q`
- Frontend build:
  - `npm run build`
- Runtime smoke with temporary fixtures and default fake provider.
- Local unavailable-provider smoke with `SCIENTIFIC_SPACES_ZOTERO_PROVIDER=local`.
- Freeze path checks with git diffs.
- Scope leak and artifact scans.

## 5. Pass Criteria

M5 verification can pass only if:

- Backend tests pass.
- Frontend build passes.
- Fake provider works.
- No-Zotero environment is handled gracefully.
- `/zotero/status`, search, item, export, and link CRUD work.
- Storage isolation works.
- Frontend `/zotero` and Article Detail Zotero panel work.
- M2 Article API regression passes.
- M3 RAG regression passes.
- M4 Learning regression passes.
- M1/M2/M3/M4 frozen contracts are not modified.
- No M6/M7 scope leak is detected.
- No forbidden artifacts are committed.

## 6. Block Criteria

M5 verification is blocked if any of these are found:

- Tests require real Zotero installation.
- No-Zotero environment crashes.
- Fake provider is missing.
- Search/item/export API fails.
- Link CRUD fails.
- Real Zotero data or attachment paths are committed.
- Zotero library write occurs without explicit user request.
- M2/M3/M4 regressions fail.
- Frozen M1/M2/M3/M4 contract is modified without a revision task.
- M6 Knowledge Graph or M7 AI Tutor is implemented early.
- Forbidden artifact is committed.

## 7. Expected Deliverables

- Updated `alignment.md`
- Created `docs/M5_VERIFICATION_REPORT.md`
- Updated `docs/00_PROJECT_STATE.md` if verification passes
- Commit:
  - pass: `docs: pass M5 verification gate`
  - blocked: `docs: record M5 verification blockers`
