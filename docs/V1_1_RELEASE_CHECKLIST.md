# v1.1 Release Checklist

Candidate: `v1.1.0`

Audit date: 2026-07-11

Current formal version: `v1.0.0`

Gate status: **BLOCKED**

Blocking item: unparameterized `GET /articles` does not preserve the frozen v1.0 list behavior. Release actions remain disabled until a targeted compatibility/migration revision and this gate's re-run pass.

## Repository

- [x] Pre-audit `main` matched `origin/main` at `f00d596a5ab3ef43a9ef57230ab51eee80fe0d81`.
- [x] No unrelated working-tree changes were present; `alignment.md` was task-owned and must be restored before commit.
- [x] `v1.0.0` remains an annotated tag whose peeled target is `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6` locally and remotely.
- [x] `v1.0.0` and its GitHub Release were not moved or rewritten.
- [x] `v1.0.0..HEAD` commit and file scope was reviewed.
- [ ] Push the audit commit and confirm `main` is synchronized.
- [ ] Record the final `v1.1.0` target commit after the audit commit is on `origin/main` and main CI passes.

## Tests

- [x] Backend full suite: 453 passed, 3 skipped.
- [x] Frontend production build: PASS, 8 routes.
- [x] Frontend Graph tests: 7/7 PASS.
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

## CI

- [x] Workflow supports `pull_request`.
- [x] Workflow supports pushes to `main`.
- [x] Workflow supports `v*` tag pushes.
- [x] Workflow supports `workflow_dispatch`.
- [x] Backend pytest and frontend build run on every supported event.
- [x] Docker compose smoke runs on tag pushes and manual dispatch.
- [x] Latest pre-audit `main` run `29154850374` succeeded for commit `f00d596a5ab3ef43a9ef57230ab51eee80fe0d81`.
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
- [x] Backup/restore/health/cleanup behavior is documented.
- [x] Known limitations do not claim multi-user production, full image parity, exhaustive research, or real-model certification.
- [x] Historical P0 numbering drift and missing historical boundary documents are recorded as documentation hygiene risks.

## Release action

- [ ] Resolve or version the M2 Article list compatibility blocker and add a >20-Article regression.
- [ ] Audit M6 default query/build compatibility and verify the Learning migration/rollback contract.
- [ ] Re-run P2-007 and obtain `A: Ready to release v1.1.0`.
- [ ] Push the audit commit to `origin/main`.
- [ ] Wait for main CI and record the successful run URL.
- [ ] Confirm the working tree is clean and `main` equals `origin/main`.
- [ ] Create annotated tag `v1.1.0` at the audited commit.
- [ ] Push only the new tag; do not move `v1.0.0`.
- [ ] Wait for tag CI: backend pytest, frontend build, and Docker compose smoke must pass.
- [ ] Create and publish the GitHub Release using the finalized release notes.
- [ ] Add a post-release CI evidence document with tag, target SHA, run URL, jobs, and conclusion.
