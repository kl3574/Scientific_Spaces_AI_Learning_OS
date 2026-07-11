# v1.1 Release Checklist

Candidate: `v1.1.0`

Audit date: 2026-07-11

Current formal version: `v1.0.0`

Gate status: **PASS - Ready to tag v1.1.0 after the audit commit main CI succeeds**

The prior Article/Graph compatibility and Learning migration blockers are resolved by P2-008. The fresh P2-007 audit returns recommendation A. This task still does not create a tag or Release.

## Repository

- [x] Re-audit `main` matched `origin/main` at `bf6a4515ceb4e7ed6d9bd150a4aaba444b131c73`.
- [x] No unrelated working-tree changes were present; the confirmed task alignment is tracked with P2-008.
- [x] `v1.0.0` remains an annotated tag whose peeled target is `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6` locally and remotely.
- [x] `v1.0.0` and its GitHub Release were not moved or rewritten.
- [x] `v1.0.0..HEAD` commit and file scope was reviewed.
- [ ] Push the audit commit and confirm `main` is synchronized.
- [ ] Record the final `v1.1.0` target commit after the audit commit is on `origin/main` and main CI passes.

## Tests

- [x] Backend full suite: 469 passed, 3 skipped.
- [x] Article legacy/versioned regression: 18 passed, including 37-record no-truncation and duplicate-record compatibility coverage.
- [x] Graph legacy/versioned regression: 11 passed.
- [x] Learning JSON/SQLite migration and persistence regression: 16 passed.
- [x] Frontend production build: PASS, 8 routes.
- [x] Frontend Article API client tests: 3/3 PASS.
- [x] Fresh Frontend Graph tests after endpoint versioning: 8/8 PASS.
- [x] Frontend Tutor tests: 13/13 PASS.
- [x] Original deterministic RAG/Tutor evaluation: 9/9 PASS.
- [x] Full-corpus RAG evaluation: PASS, 12 queries, expected hit@10 90.91%, 0 errors/fabrications.
- [x] Graph benchmark: PASS; bounds and latency guards satisfied.
- [x] Graph production UI smoke: PASS, 17/17 checks.
- [x] Full-corpus Tutor evaluation: PASS, 42 cases, 0 hard/validity failures.
- [x] Tutor live production UI smoke: PASS, 17/17 checks.
- [x] PDF manifest/idempotency: PASS, 1,311 unchanged, 0 failed, 1,311 validation PASS.
- [x] Configured operations health: PASS with zero issues.
- [x] Essential backup, independent verification, isolated restore, and restored Article audit: PASS.
- [x] Production-like backend API, Reader detail, and frontend route smoke: PASS.
- [x] Full-corpus legacy Article smoke: 1,311/1,311 returned with exact v1.0 top-level keys.
- [x] Full-corpus `/v1.1/articles` smoke: 20 returned, total 1,311.
- [x] Managed full-corpus `POST /graph/build`: 200 with 52,874 nodes/82,230 edges; Graph SHA-256 unchanged.
- [x] Reader Chromium smoke uses `/v1.1/articles`: PASS; final controlled run blocked four remote image references and received zero external responses.

## CI

- [x] Workflow supports `pull_request`.
- [x] Workflow supports pushes to `main`.
- [x] Workflow supports `v*` tag pushes.
- [x] Workflow supports `workflow_dispatch`.
- [x] Backend pytest and frontend build run on every supported event.
- [x] Docker compose smoke runs on tag pushes and manual dispatch.
- [x] P2-008 `main` run `29157847470` succeeded for commit `bf6a4515ceb4e7ed6d9bd150a4aaba444b131c73`.
- [x] CI requires no real-provider secret.
- [ ] Audit-commit `main` CI succeeds.
- [ ] `v1.1.0` tag CI succeeds, including Docker compose smoke.

## Artifacts

- [x] No tracked `.local_data` tree or Article corpus.
- [x] No tracked Markdown library or PDF output.
- [x] No tracked FAISS/vector index, chunks, or embedding cache.
- [x] No tracked Graph runtime.
- [x] No tracked backup archive or restore data.
- [x] No tracked DB/SQLite runtime file.
- [x] No tracked `.env` or real API key.
- [x] No tracked browser profile, trace, log, or cache.
- [x] No tracked `node_modules`, `.next`, or build output.
- [x] The only tracked HTML files are three bounded M1 parser fixtures.
- [x] Runtime and backup/restore ignore rules were checked with `git check-ignore`.
- [x] Finite secret-pattern scan over `v1.0.0..HEAD` returned no match.

## Documentation

- [x] README documents setup, full-corpus use, local-data operations, risks, and verification entry points.
- [x] `docs/RELEASE_NOTES_v1.1.0_DRAFT.md` exists and remains marked Draft.
- [x] `CHANGELOG.md` records `1.1.0` as Unreleased.
- [x] Security/privacy baseline and verification are present.
- [x] Deployment profile and verification are present.
- [x] Persistence migration/rollback and local data management are documented.
- [x] `docs/API_COMPATIBILITY_MIGRATION_REVISION.md` records P2-008 evidence and recommendation A to rerun P2-007.
- [x] `docs/ADR/0005-m1-post-freeze-corpus-compatibility-revisions.md` records M1 post-freeze governance and compatibility.
- [x] Backup/restore/health/cleanup behavior is documented.
- [x] Known limitations do not claim multi-user production, full image parity, exhaustive research, or real-model certification.
- [x] Historical P0 numbering drift and missing historical boundary documents are recorded as documentation hygiene risks.

## Release action

- [x] Resolve/version the M2 Article list compatibility blocker and add a >20-Article regression.
- [x] Audit M6 default query/build compatibility and verify the Learning migration/rollback contract.
- [x] Re-run P2-007 and obtain `A: Ready to tag v1.1.0`.
- [ ] Push the audit commit to `origin/main`.
- [ ] Wait for main CI and record the successful run URL.
- [ ] Confirm the working tree is clean and `main` equals `origin/main`.
- [ ] Create annotated tag `v1.1.0` at the audited commit.
- [ ] Push only the new tag; do not move `v1.0.0`.
- [ ] Wait for tag CI: backend pytest, frontend build, and Docker compose smoke must pass.
- [ ] Create and publish the GitHub Release using the finalized release notes.
- [ ] Add a post-release CI evidence document with tag, target SHA, run URL, jobs, and conclusion.
