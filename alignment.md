# P3-004 Remote CI Closure and P3-005 Canonical Staging - Confirmed Execution Alignment

## 1. Background

- Current canonical task: `P3-004 Real Provider Evaluation Design`.
- P3-004 implementation commit: `0bf90e518549bea7549409cde72a3befda0c340d`.
- Expected parent: `d294a447c966ae7b34b06bed9fceee672f26bd30`.
- Formal version: `v1.1.0`; candidate version: not assigned.
- P3-004 local implementation evidence is PASS, but remote main CI closure and the transition to P3-005 must be verified and persisted.
- The user explicitly confirmed this closure/staging alignment before repository or external write actions.

## 2. Requirements

1. Verify the P3-004 implementation commit identity, parent, subject, and changed paths.
2. Fetch current remote refs and verify that local `main` and `origin/main` remain synchronized at the expected commit.
3. Locate the main CI run for `0bf90e5` and require Backend and Frontend success; Docker compose smoke must be skipped under the normal main-push policy.
4. Close P3-004 only after the remote CI evidence passes.
5. Create `docs/tasks/P3-005_CI_SECURITY_AND_RELEASE_PROVENANCE.md` as the canonical next task.
6. Set P3-005 to `ALIGNMENT REQUIRED` with implementation authorization `NOT GRANTED`.
7. Update current-task, project-state, v1.2 roadmap, alignment, P3-004 evidence, and only any necessary README current-task pointer.
8. Run changed-path, artifact, secret, and Git-state audits before committing.
9. Create the docs-only commit `docs: close P3-004 and stage P3-005`, push `main`, and verify its main CI.
10. After staging CI succeeds, provide the complete P3-005 execution alignment without implementing P3-005.

## 3. Purpose

Create an auditable transition from the completed P3-004 implementation to a canonical but unimplemented P3-005 task. Remote CI must prove the P3-004 baseline and the docs-only staging commit before P3-005 implementation can be considered for separate authorization.

## 4. Planned Execution

1. Recheck applicable governance, `REWORK.md`, `.audit`, canonical task state, and the clean Git baseline.
2. Persist this confirmed alignment.
3. Fetch `origin`, verify branch synchronization, and verify the published `v1.1.0` tag remains unchanged.
4. Inspect the P3-004 main CI run and stop if required jobs are missing or unsuccessful.
5. Record P3-004 remote CI evidence and mark it fully closed.
6. Create the P3-005 canonical specification with goals, boundaries, acceptance metrics, Git plan, and implementation authorization explicitly not granted.
7. Update task pointers and planning/state documentation without changing product or workflow implementation.
8. Audit changed paths, artifacts, secrets, worktree, and staged content.
9. Create and push the docs-only closure/staging commit.
10. Verify the staging commit main CI and final branch synchronization.
11. Deliver the complete P3-005 execution alignment and request separate confirmation.

Stop on unknown worktree drift, REWORK/FAIL audit, remote divergence, CI failure or missing evidence, artifact/secret findings, tag movement, scope expansion, or any need to implement P3-005.

## 5. Selection Rationale

Separating implementation, remote CI closure, canonical next-task staging, and next-task authorization preserves an auditable lifecycle. It prevents P3-005 workflow/security changes from being mixed into P3-004 or treated as authorized merely because the next task has been named.

## 6. Alternatives

| Option | Advantages | Disadvantages | Decision |
| --- | --- | --- | --- |
| A. Verify CI, close P3-004, stage P3-005, then align separately | Strong evidence chain and explicit authorization boundary | Requires two CI waits | Selected |
| B. Implement P3-005 in the closure commit | Faster apparent progress | Mixes task ownership and bypasses authorization | Prohibited |
| C. Close P3-004 from local evidence only | Avoids remote checks | Cannot prove pushed-commit CI status | Rejected |

## 7. Deliverables

- Verified P3-004 commit and remote main CI evidence.
- Updated `docs/tasks/P3-004_REAL_PROVIDER_EVALUATION_DESIGN.md` closure evidence.
- New `docs/tasks/P3-005_CI_SECURITY_AND_RELEASE_PROVENANCE.md`.
- Updated `docs/tasks/CURRENT_TASK.md` pointing to P3-005.
- Updated `docs/00_PROJECT_STATE.md` and `docs/V1_2_ROADMAP.md`.
- Updated `alignment.md`; README only if a current-task pointer requires it.
- One docs-only commit: `docs: close P3-004 and stage P3-005`.
- Verified staging-commit main CI evidence.
- Complete P3-005 execution alignment, with implementation still not granted.

## 8. Acceptance Criteria

- P3-004 commit is exactly `0bf90e518549bea7549409cde72a3befda0c340d`, with expected parent and subject.
- Live-fetched `origin/main` contains the P3-004 commit and local `main` has no unexplained divergence.
- P3-004 main CI overall conclusion is success; Backend and Frontend pass; Docker compose smoke is skipped for the normal main push.
- P3-004 canonical status is `PASS / CLOSED` with durable remote CI evidence.
- P3-005 canonical task records `ALIGNMENT REQUIRED` and implementation authorization `NOT GRANTED`.
- P3-005 defines immutable Action pins, least-privilege permissions, dependency/OSV and secret scanning, CycloneDX 1.6 SBOMs, exact-tag/manual provenance boundaries, branch-protection guidance, and preservation of existing CI behavior.
- The closure commit modifies only approved documentation/task files, is pushed to `main`, and its Backend and Frontend jobs pass while Docker smoke is skipped.
- No product/runtime/workflow implementation, real provider call, private Zotero access, candidate assignment, tag, or Release occurs.
- No secret, runtime/private artifact, generated corpus, PDF, Graph/RAG data, database, archive, trace, profile, or cache is committed.
- Final `main` is synchronized with `origin/main`, the worktree is clean, and P3-005 implementation remains unauthorized pending separate confirmation.

## P3-005 Staging Boundary

- Formal version: `v1.1.0`.
- Candidate version: not assigned.
- Previous task: P3-004 `PASS / CLOSED`.
- Baseline: `0bf90e518549bea7549409cde72a3befda0c340d`.
- P3-005 implementation authorization: `NOT GRANTED`.
- Tag and Release operations: prohibited.
- Real provider and private Zotero operations: prohibited.

## Closure and Staging Evidence

- P3-004 implementation commit: `0bf90e518549bea7549409cde72a3befda0c340d`.
- P3-004 main CI run: `29627617727`.
- P3-004 main CI URL: https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29627617727
- Backend pytest: PASS.
- Frontend build: PASS.
- Docker compose smoke: SKIPPED by normal main-push policy.
- P3-004 remote closure: PASS / CLOSED.
- Current canonical task: `docs/tasks/P3-005_CI_SECURITY_AND_RELEASE_PROVENANCE.md`.
- P3-005 status: `ALIGNMENT REQUIRED`.
- P3-005 implementation authorization: `NOT GRANTED`.
- Current authorization covers canonical staging and its CI verification only; it does not authorize P3-005 implementation.
- Next action after successful staging CI: output the complete P3-005 execution alignment and wait for separate confirmation.
