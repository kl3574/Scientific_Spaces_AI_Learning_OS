# P3-006 Structured Reference Full-Corpus Build - Confirmed Execution Alignment

## 1. Background

- Formal version: `v1.1.0`; candidate version: not assigned.
- Confirmed starting commit: `0496991746196c1d628a06f4fab36c34085a0144`.
- Canonical task: `docs/tasks/P3-006_STRUCTURED_REFERENCE_FULL_CORPUS.md`.
- Previous task: P3-005 CI Security and Release Provenance, `PASS / CLOSED`.
- P3-003 proved deterministic extraction, normalization, deduplication, provenance, fake/unavailable Zotero matching, and derived-store integrity on a bounded 75-Article pilot.
- The user explicitly confirmed this complete execution alignment. Attachment UUIDs are transport locators and do not define task identity.

Authorization state:

- P3-006 implementation: GRANTED.
- Article-store read: GRANTED only for the exact approved corpus path and identity.
- Full-corpus processing: GRANTED only after exact identity preflight passes.
- Fake/curated/unavailable Zotero validation: GRANTED.
- Testing, ignored local runtime output, and one local status-appropriate commit: GRANTED.
- Network, private Zotero, push, candidate, tag, Release, and attestation publication: NOT GRANTED.

## 2. Requirements

1. Preserve governance, a clean starting baseline, and the exact confirmed allowlist.
2. Persist this alignment and mark P3-006 `IN PROGRESS` before Article-store access.
3. Read only `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json` and require a regular nonsymlink file with 1,311 valid Articles, store SHA-256 `3b91f22db548373a6c91bb11a5188fb3e388ab9e19c4429e8e8fac918609a505`, and corpus fingerprint v1 `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d`.
4. Require unique IDs and URLs, no missing content, stable preflight identity, and at least 2 GiB free disk before processing.
5. Implement a deterministic offline full-corpus orchestrator that reuses P3-003 extraction, normalization, deduplication, matching, models, and schema semantics unchanged.
6. Process each Article exactly once; terminally classify every Article and candidate; retain complete provenance and deterministic duplicate behavior.
7. Atomically checkpoint every 50 Articles; validate corpus/config/rule/code identity on resume; reject stale or corrupt checkpoints.
8. Build to a private sibling staging directory, validate all payload/index/manifest relationships, atomically install `current`, and preserve or restore one valid rollback on failure.
9. Fail closed on schema, corpus, config, rule, hash, count, index, foreign-key, ownership, manifest, checkpoint, path, and corruption mismatches.
10. Prove controlled interruption after Article 125, resume equivalence, no-op rerun, and a separate clean-build byte/deterministic comparison.
11. Validate only fake/curated/unavailable Zotero modes; never access or write a private Zotero library; never auto-confirm ambiguous matches.
12. Generate at least 60 deterministic review cases. Do not fabricate a reviewer; record pending or single-review limitations accurately.
13. Enforce elapsed <=30 minutes, peak RSS <=1.5 GiB, installed store <=512 MiB, combined staging/rollback/checkpoint <=1.5 GiB, and reports/logs <=10 MiB.
14. Run focused reference tests, complete Backend regressions, Frontend build, frozen Article/Graph/Zotero tests, and artifact/secret/changed-path/immutability audits offline.
15. Create `docs/P3_006_STRUCTURED_REFERENCE_FULL_CORPUS_REPORT.md`, update governance, and create one local status-appropriate commit. Do not push.

## 3. Purpose

Build a complete, deterministic, provenance-complete, offline Tier 2 Reference Store from the exact frozen 1,311-Article corpus while proving checkpoint/resume, integrity, atomic installation, rollback, idempotency, clean-build determinism, source immutability, zero network, bounded resources, and conservative Zotero matching.

## 4. Planned Execution

1. Verify local Git, REWORK/audit, and governance without fetching.
2. Persist this alignment and `IN PROGRESS` authorization state.
3. Preflight the exact Article store, identity, content validity, path safety, and free capacity without mutation.
4. Inspect and extend only the approved reference boundary; preserve P3-003 extraction/normalization/deduplication/ID/schema semantics.
5. Add focused tests for identity, path safety, accounting, checkpoint/resume, interruption, corruption, atomic install/rollback, determinism, matching, resources, and artifact boundaries.
6. Run focused tests with `UV_OFFLINE=1`.
7. Execute the approved interruption command, verify checkpoint/current/source invariants, then resume the complete build.
8. Audit the installed store and complete accounting, then run unchanged no-op and isolated clean deterministic rebuild checks.
9. Generate deterministic review cases and record actual review status without fabrication.
10. Run full Backend, Frontend, frozen compatibility, secret, artifact, source-immutability, path, and Git verification.
11. Classify PASS, CONDITIONAL, or BLOCKED; write bounded aggregate evidence; create one local commit; stop without push.

Stop immediately on corpus mismatch/change, insufficient disk, unknown worktree drift, REWORK/FAIL audit, required semantic change to P3-003 normalization/IDs/dedup/schema, Article/M1/API modification, network or private Zotero need, test/build failure, resource overrun, secret/private artifact, or out-of-allowlist path.

## 5. Selection Rationale

Add a dedicated full-corpus orchestration boundary around the already validated P3-003 semantics. Per-Article checkpoint payloads allow interruption recovery without retaining Article bodies, while global deterministic ordering and deduplication after extraction preserve cross-Article identity. Reuse the existing atomic Reference Store installer and audit contracts with only bounded full-corpus enhancements.

## 6. Alternatives

| Option | Advantages | Disadvantages | Decision |
| --- | --- | --- | --- |
| New full-corpus orchestrator reusing frozen P3-003 semantics | Isolates scaling/recovery logic; preserves validated rules | Adds checkpoint format and orchestration tests | Selected |
| Expand the pilot sample limit to 1,311 | Less code | Conflates pilot selection with complete accounting and lacks robust resume | Rejected |
| Rewrite extraction/dedup for streaming | Potential lower memory | Changes validated semantics and IDs | Prohibited |
| SQLite derived store | Transactions and queries | New dependency/migration surface; ADR 0006 defers it | Rejected |
| Private Zotero matching | Real local coverage | Crosses explicit private-data boundary | Not authorized |

## 7. Deliverables

- Full-corpus orchestration under `backend/app/references/`.
- `scripts/references/build_full_corpus_references.py` and bounded audit support.
- Focused tests and synthetic/metadata-only fixtures under the approved reference test paths.
- Ignored runtime store at `.local_data/scientific_spaces/references/full-corpus/` with `current`, `checkpoints`, rollback/staging lifecycle, and reports.
- Controlled interruption/resume, installed-store audit, no-op, clean determinism, fake/unavailable matching, and resource evidence.
- At least 60 deterministic review cases with truthful reviewer status.
- `docs/P3_006_STRUCTURED_REFERENCE_FULL_CORPUS_REPORT.md`.
- Updated canonical/current task, project state, v1.2 roadmap, alignment, and bounded README entry.
- One local status-appropriate commit; no push.

## 8. Acceptance Criteria

PASS requires:

- Article/store identity exactly matches the confirmed 1,311-Article SHA/fingerprint baseline before and after execution.
- Input Article accounting, candidate classification reconciliation, provenance completeness, deterministic ID rate, and duplicate consistency rate are `1.0`; silent drops and unknown/duplicate processing are `0`.
- Checkpoint/resume, controlled interruption, atomic install, rollback/recovery, stale/corrupt detection, no-op reuse, and clean-build determinism pass.
- Fake/curated/unavailable matching passes with zero writes, private reads, false exact matches, title-only exact matches, or ambiguous auto-confirmations.
- At least 60 review cases exist; strong-identifier precision is at least `0.95` when an actual review is complete. Reviewer status is never fabricated.
- Network and unexpected network attempts are `0`; Article mutation is `0`; all resource budgets pass.
- Focused/full Backend, Frontend, frozen compatibility, artifact, secret, local-path, and Git gates pass.

CONDITIONAL is permitted only when all machine integrity, source, accounting, provenance, determinism, recovery, no-network, resource, test/build, and artifact gates pass but a finite optional matching or actual human-review limitation remains documented with exact scope and next action.

BLOCKED takes precedence for any corpus mismatch, Article mutation, incomplete accounting, silent drop, nondeterminism, provenance loss, network request, integrity/recovery failure, false exact match, private/secret artifact, resource overrun, regression, out-of-scope requirement, or unauthorized action.

## Allowed Changes

- `backend/app/references/`
- `backend/tests/references/`
- `backend/tests/fixtures/references/`
- `scripts/references/`
- `docs/P3_006_STRUCTURED_REFERENCE_FULL_CORPUS_REPORT.md`
- `docs/tasks/P3-006_STRUCTURED_REFERENCE_FULL_CORPUS.md`
- `docs/tasks/CURRENT_TASK.md`
- `docs/00_PROJECT_STATE.md`
- `docs/V1_2_ROADMAP.md`
- `alignment.md`
- `README.md`, only for the full-corpus command/report entry
- `.gitignore`, only if the existing `.local_data/` rule is insufficient

## Runtime, Network, and Git Boundary

- Authorized runtime root: `.local_data/scientific_spaces/references/full-corpus/`; all output remains ignored and rejects symlinks, traversal, absolute manifest paths, Article bodies, and private data.
- Existing DOI/arXiv/URL normalization, `reference-id/v1`, evidence IDs, exact duplicate rules, provenance fields, and P3-003 schema versions are frozen.
- `UV_OFFLINE=1` is mandatory for Python execution. `npm run build` may use existing local dependencies only; no install command is authorized.
- Source-site, browser, curl/wget, remote metadata, real Provider, and private Zotero access are prohibited.
- Commit messages: PASS `feat: build full-corpus reference store`; CONDITIONAL `docs: record conditional full-corpus reference build`; BLOCKED `docs: record full-corpus reference build blockers`.
- One local commit is authorized. Push, CI, candidate, tag, Release, attestation, rebase, amend, and force operations are prohibited.

## Current Execution State

- Alignment: CONFIRMED AND PERSISTED.
- Implementation authorization: CONSUMED / CLOSED.
- Exact Article-store read/full-corpus authorization: CONSUMED / CLOSED after successful identity preflight and 1,311-Article processing.
- Network authorization: NOT GRANTED.
- Private Zotero authorization: NOT GRANTED.
- Machine gates: PASS.
- Human review: PENDING with 64 deterministic cases and no fabricated reviewer.
- Final status: CONDITIONAL / CLOSED pending only a separately aligned real human-review evidence task.
- Push, candidate, tag, Release, and attestation: NOT PERFORMED / NOT AUTHORIZED.
