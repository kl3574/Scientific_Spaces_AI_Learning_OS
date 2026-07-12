# P3-002 v1.2 Product Requirements and Architecture

## 1. Background

Scientific Spaces AI Learning OS `v1.1.0` is released. P3-001 post-release validation passed at commit `fdba4d8759f36704fcc928fff504526d0c5e1781` with no Critical or Important findings and no need for `v1.1.1`. P3-002 approves product requirements and architecture only; it does not implement v1.2 or assign a candidate version.

## 2. Authoritative Inputs

- Attachment: `/home/lkx/.codex/attachments/334ce5f2-2121-4014-98c7-98ff6100bb9f/pasted-text-1.txt`
- Attachment SHA-256: `05df8ddbe6e71e19e303e2521951d03b7d49a1bbf7be3c8972ed6a30062fdf8f`
- Attachment size: 1,371 lines / 24,975 bytes
- Applicable governance: repository-root `AGENTS.md`
- Existing project evidence: P3-001 report, v1.2 roadmap, release evidence, compatibility/security/deployment/persistence/corpus reports, current source and tests
- Starting branch: `main`
- Starting HEAD and `origin/main`: `fdba4d8759f36704fcc928fff504526d0c5e1781`
- Starting ahead/behind: `0/0`
- `v1.1.0` peeled target: `3efbe2a792a9853f1bac456f0287c3b5b62713ce`
- P3-001 CI run: `29179023882`, Backend and Frontend PASS, Docker skipped by main-push policy
- `REWORK.md`: absent
- `.audit`: absent

## 3. Requirements

1. Decide whether Structured References, opt-in Real Provider Evaluation, and CI Security/Release Provenance enter v1.2 using Scope Decision A/B/C/D.
2. Define product problems, users, journeys, goals, non-goals, security/privacy requirements, compatibility, success metrics, release scope, and deferred scope.
3. Define an independent derived reference pipeline that never modifies `Article.content`, `metadata.references`, or frozen M1 modules.
4. Define DOI, arXiv, URL, citation-text normalization; deterministic and ambiguous deduplication; complete provenance; and no silent candidate drops.
5. Define a versioned, fingerprinted, atomic, idempotent, stale-detecting, corruption-detecting Reference Store with rebuild/rollback lifecycle.
6. Separate deterministic derived reference data from Tier 1 user-reviewed Zotero decisions.
7. Keep Zotero read-only; never auto-write or auto-confirm ambiguous/title-only matches.
8. Approve additive, bounded `/v1.2` reference API contracts and minimal Article/Zotero UI states without implementing them.
9. Define real-provider adapter metadata, explicit operator consent, bounded request/cost budgets, privacy/redaction/retention, case taxonomy, metrics, and ignored outputs. No real call is permitted.
10. Define immutable GitHub Action pinning, least-privilege permissions, dependency/secret scanning, SBOM, provenance/attestation, branch-protection guidance, and artifact boundaries.
11. Create a scoped threat model for references, Zotero, real providers, and CI/supply chain.
12. Freeze v1.0 legacy, `/v1.1`, M3-M7, JSON-default, SQLite-opt-in, and backup/restore contracts; all v1.2 behavior is additive.
13. Define P3-003 through P3-007 milestones, dependencies, evaluation budgets, and executable PASS/CONDITIONAL/BLOCKED gates.
14. Run Backend tests, Frontend build, documentation consistency checks, and artifact/secret audit before a local status-dependent commit.

## 4. Scope

### In Scope

- Product and architecture documentation
- Reference/Zotero contracts and persistence lifecycle
- Real-provider evaluation design and dry-run boundaries
- CI security and release provenance design
- Threat model, compatibility matrix, evaluation plan, acceptance gates, and implementation sequencing
- Scope Decision A/B/C/D

### Out of Scope

- Product implementation or new endpoints/UI
- Reference extraction or full-corpus reference build
- Real-provider or paid calls
- Private Zotero reads/exports or writes
- M1/frozen API changes
- Graph storage migration, remote image archive, multi-user/auth
- Candidate version, tag, Release, push

## 5. Allowed Changes

- `alignment.md`
- `docs/V1_2_PRD.md`
- `docs/V1_2_ARCHITECTURE.md`
- `docs/V1_2_DATA_MODEL.md`
- `docs/V1_2_THREAT_MODEL.md`
- `docs/V1_2_EVALUATION_PLAN.md`
- `docs/V1_2_ACCEPTANCE.md`
- `docs/V1_2_EXECUTION_PLAN.md`
- `docs/ADR/0006-derived-reference-store.md`
- `docs/ADR/0007-real-provider-evaluation-boundary.md`
- `docs/ADR/0008-ci-security-and-release-provenance.md`
- `docs/V1_2_ROADMAP.md`
- `docs/00_PROJECT_STATE.md`
- `README.md`, planning links only

No other file may be created, deleted, renamed, or modified.

## 6. Prohibited Actions

- Modify Article content, M1 parser/converter/validation, legacy APIs, or `/v1.1` APIs
- Implement reference extraction, API, UI, storage, provider, scanner, SBOM, or provenance functionality
- Run full-corpus reference processing
- Call a real provider, make a paid request, or read/export a private Zotero library
- Auto-write Zotero or assign ambiguous matches
- Make SQLite the default
- Modify/create/move tags or GitHub Releases
- Push the local commit
- Add runtime/private artifacts, credentials, database, corpus, PDF, Graph, FAISS, backup, raw provider output, profile, trace, or cache
- Expand to Graph migration, image archiving, multi-user, authentication, or public production deployment

## 7. Deliverables

1. Seven v1.2 specification documents: PRD, architecture, data model, threat model, evaluation plan, acceptance, and execution plan.
2. ADR 0006, 0007, and 0008.
3. Updated v1.2 roadmap, project state, README planning links, and alignment.
4. Explicit Scope Decision A/B/C/D and PASS/CONDITIONAL/BLOCKED status.
5. Test/build, consistency, artifact/secret, Git, and CI evidence.
6. One local commit matching the final status; no push.

## 8. Acceptance Criteria

P3-002 PASS requires all 15 attachment criteria: each theme is approved or rejected; non-goals are explicit; ReferenceRecord and store lifecycle are complete; provenance/duplicate rules are complete; Zotero never auto-writes; provider consent/data/cost boundaries are complete; CI security policy and threat model are complete; compatibility and migration/rollback are explicit; milestones/dependencies and per-milestone gates are executable; no critical ambiguity remains; no feature implementation or candidate declaration occurs.

## 9. Execution Plan

1. Write this approved alignment.
2. Fetch tags and verify clean synchronized main, P3-001 CI, and immutable v1.1.0 target.
3. Read every required project document and inspect each specified source/test boundary.
4. Build an evidence inventory and compare Scope Options A-D.
5. Select the scope and lock product, data, security, compatibility, and lifecycle decisions.
6. Write the seven specifications and three ADRs.
7. Update roadmap, project state, and README planning links.
8. Self-review for placeholders, contradictions, nonexistent modules, naming drift, and incomplete gates.
9. Run Backend tests, Frontend build, consistency checks, and artifact/secret audit.
10. Commit locally with the status-appropriate message and verify the final branch/worktree state.

## 10. Verification Plan

- `git fetch origin --tags`
- Required Git status/revision/log/tag and GitHub Actions checks
- `uv run --project backend --extra dev pytest -q`
- `npm run build` in `frontend/`
- Search and inspect every documented path, CLI, endpoint, schema, milestone dependency, version, and tag target
- Confirm planned modules are described as future work, not existing implementation
- `git status --short`, `git diff --stat`, staged diff review, tracked artifact scan, bounded secret-pattern scan
- Verify no push, tag, Release, provider, Zotero, corpus, migration, or implementation action occurred

## 11. Git Plan

- PASS: `docs: approve v1.2 requirements and architecture`
- CONDITIONAL: `docs: record conditional v1.2 architecture`
- BLOCKED: `docs: record v1.2 architecture blockers`
- Push: not authorized
- Tag/Release: prohibited
- Candidate version: not assigned

## 12. Risk Controls

- Preserve any user changes and stop on unexpected worktree drift.
- Use current files and remote read evidence, not prior summaries.
- Keep M1 and frozen contracts untouched.
- Separate rebuildable derived data from Tier 1 reviewed decisions.
- Keep fake-provider defaults and prevent secret/private content capture.
- Keep all generated runtime data ignored and out of Git.
- Keep published tags and Release immutable.
- Do not perform any unapproved external write.

## 13. Stop Conditions

- Unknown worktree change or conflict
- Missing required source/document evidence
- Test or build failure
- Artifact or secret scan hit requiring investigation
- Need to modify a frozen contract or product code
- Need for real-provider, paid, private Zotero, corpus, tag, Release, or push action
- Scope cannot converge on A/B/C/D
- Unresolved critical architecture ambiguity

## 14. Confirmation

User confirmed this P3-002 Task Alignment and authorized local documentation changes, verification, and one local commit. Push, tag, Release, candidate declaration, product implementation, real-provider calls, private Zotero access, and full-corpus reference processing remain unauthorized.
