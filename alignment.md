# Task Alignment - M1 Final Freeze Re-run After M1.3

## 1. Background

Project: `kl3574/Scientific_Spaces_AI_Learning_OS`

Current milestone evidence:

- M0 Engineering Foundation: PASS
- M1 Source Pipeline: PASS
- M1 Verification: PASS
- M1 PDF Export: PASS
- M1.3 Browser Article Acquisition Quality Revision: PASS

Latest M1.3 fix commit:

- `da60d2b81d002e2b7f863f4ed54f2db590f17cbb`

This task re-runs the M1 Final Freeze & Handoff Gate. It is an acceptance freeze task only. It must not implement M2 Reader, Search, RAG, Learning System, or M3-M7 behavior.

## 2. Scope

Allowed changes:

- `alignment.md`
- `docs/M1_FINAL_FREEZE_REPORT.md`
- `docs/00_PROJECT_STATE.md` only if freeze passes
- `backend/tests/test_browser_access.py` only if a retain/delete decision is required

Forbidden changes:

- M1 implementation code
- M1 Verification standard
- Backend crawler/parser/converter/storage/validation/export code
- M2-M7 features
- Committed PDF, HTML, image, trace, profile, cache, or temporary artifacts

## 3. Gate Focus

The re-run must verify:

1. Browser acquisition quality gate is active.
2. Article content fidelity passes for live synced articles.
3. Formula validation passes.
4. `https://spaces.ac.cn/archives/11787` blocker is resolved.
5. Browser transient failures, if present, are classified as risks unless they prevent content-quality verification.
6. M2 readiness can be classified as `A: Ready for M2`, `B: Need additional M1 work`, or `C: Human decision required`.

## 4. Execution Plan

1. Read project state, M1 milestone, prior freeze report, M1.1/M1.3 revision reports, M1 verification, source access strategy, PDF export report, data model, knowledge pipeline, ADRs, and relevant implementation/test paths.
2. Check git status.
3. Run ordinary tests:
   - `uv run --project backend --extra dev pytest -q`
4. Run a bounded live sync:
   - `SCIENTIFIC_SPACES_DATA_DIR=/tmp/scientific-spaces-m1-final-freeze-rerun uv run --project backend python -m app.sync --max-articles 5`
5. Inspect live sync output and stored JSON for:
   - discovered/imported/failed/validated counts
   - article count
   - duplicate count
   - validation issues
   - `content_completeness_rate`
   - `formulas_valid`
   - formula delimiter balance
   - `11787` content length and metadata
   - references/images preservation
6. Sample 3-5 live articles for:
   - correct title
   - content starts from article body
   - reasonable content length
   - metadata presence
   - sidebar/comment/share script/navigation exclusion
7. Confirm PDF export evidence from `docs/M1_PDF_EXPORT_EVALUATION.md`.
8. Check `backend/tests/test_browser_access.py` handling and record the decision.
9. Check artifacts and diff before commit.
10. If all pass, update project state with `M1 Freeze Passed`, `M2 Readiness: Ready for M2`, and the post-freeze change rule.

## 5. Pass Criteria

Freeze can pass only if:

- pytest passes.
- live sync imports real articles.
- `duplicate_count=0`.
- `11787` blocker is resolved.
- content fidelity passes.
- `formulas_valid=true`.
- delimiter balance passes.
- validation issues are empty or only non-blocking risks.
- PDF export evidence remains PASS.
- no forbidden artifacts are staged or committed.
- no M2-M7 implementation exists.

## 6. Block Criteria

Freeze remains blocked if any of these are found:

- content extraction error
- formula corruption
- metadata loss
- unresolved `11787` blocker
- RSS discovery failure
- browser access cannot fetch valid pages for verification
- storage failure
- real validation data-quality issue
- forbidden artifact staged for commit
- M2-M7 implementation ahead of schedule

## 7. Expected Deliverables

- Updated `alignment.md`
- Updated `docs/M1_FINAL_FREEZE_REPORT.md`
- Updated `docs/00_PROJECT_STATE.md` if freeze passes
- Commit:
  - pass: `docs: pass M1 final freeze handoff`
  - blocked: `docs: rerun M1 final freeze gate`
