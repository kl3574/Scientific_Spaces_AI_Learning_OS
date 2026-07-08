# Task Alignment - M4 Verification Gate

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
- M4 Learning Management: IMPLEMENTED

M4 implementation commit:

- `0077f60fe6065b9143b865837e4d0664341a790f`

This task verifies M4 only. It must not implement M5 Zotero Integration, M6 Knowledge Graph, or M7 AI Tutor.

## 2. Scope

Allowed changes:

- `alignment.md`
- `docs/M4_VERIFICATION_REPORT.md`
- `docs/00_PROJECT_STATE.md` only if verification passes
- `.gitignore` only if local runtime data paths are not ignored

Forbidden changes:

- M4 implementation code
- M1/M2/M3 frozen implementation code
- M4 verification standard
- M5-M7 features
- local runtime data, API keys, FAISS indexes, embedding caches, PDFs, HTML dumps, images, traces, profiles, caches, `node_modules`, or large article data

## 3. Gate Focus

The verification gate must confirm:

1. Learning state model and API work for default, reading, completed, timestamps, and read counts.
2. Bookmark/favorite add, list, delete, and duplicate behavior are stable.
3. Manual notes support create, list, update, and delete without AI generation.
4. Learning sessions support create, end, duration, and list without conversation history or tutor state.
5. Dashboard stats match Article and learning store data and handle empty data.
6. Storage uses local JSON, supports `SCIENTIFIC_SPACES_LEARNING_FILE`, and does not commit user data.
7. Frontend Dashboard, Article List, and Article Detail expose basic M4 controls without M5-M7 UI.
8. M2 Article API and M3 RAG API regressions pass.
9. M1/M2/M3 frozen contracts are not broken.
10. No M5-M7 scope leak or forbidden artifact exists.

## 4. Execution Evidence

Verification used:

- Code inspection of `backend/app/api/learning.py`, `backend/app/learning/`, `backend/tests/test_learning_api.py`, `frontend/src/lib/learning.ts`, and frontend M4 components.
- Backend tests:
  - `uv run --project backend --extra dev pytest -q`
- Frontend build:
  - `npm run build`
- Runtime smoke with temporary `/tmp/scientific-spaces-m4-verification-*` fixtures.
- Freeze path checks using git diffs from M3 verification commit to current `HEAD`.
- Scope leak and artifact scans.

## 5. Pass Criteria

M4 verification can pass only if:

- Backend tests pass.
- Frontend build passes.
- Learning state works.
- Bookmark/favorite works.
- Notes CRUD works.
- Session history works.
- Dashboard stats work.
- Storage isolation works.
- M2 Article API regression passes.
- M3 RAG regression passes.
- M1/M2/M3 frozen contracts are not broken.
- No M5-M7 scope leak is detected.
- No forbidden artifacts are committed.

## 6. Block Criteria

M4 verification is blocked if any of these are found:

- Learning API tests fail.
- Frontend build fails.
- Real user learning data is committed.
- Notes, session, or stats behavior is incorrect.
- M2 Reader regression fails.
- M3 RAG regression fails.
- Frozen M1/M2/M3 contract is modified without a revision task.
- M5-M7 functionality is implemented early.
- Forbidden artifact is committed.

## 7. Expected Deliverables

- Updated `alignment.md`
- Created `docs/M4_VERIFICATION_REPORT.md`
- Updated `docs/00_PROJECT_STATE.md` if verification passes
- Commit:
  - pass: `docs: pass M4 verification gate`
  - blocked: `docs: record M4 verification blockers`
