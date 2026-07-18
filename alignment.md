# P3-005 Main Synchronization and P3-006 Canonical Staging - Confirmed Alignment

## 1. Background

- Formal version: `v1.1.0`; candidate version: not assigned.
- P3-005 implementation/blocker commit: `80e8823e2ba8403f347df762de3107298f6bc4b1`.
- P3-005 manual-validation fix commit: `666e93f043788e03133c3532e69b9fd2dcfa01ea`.
- P3-005 local closure commit: `ff19c520ac9650a36c5073665864aa4086160565`.
- Exact-commit validation run [`29635940873`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29635940873) passed all eight jobs with no uploaded artifact or publication authorization.
- The user explicitly authorized auditing and pushing the exact sequence, verifying main CI, persisting closure evidence, staging P3-006 without implementation authority, pushing the docs-only staging commit, and verifying its main CI.
- Attachment UUIDs are transport locators and do not redefine the semantic task.

## 2. Requirements

1. Revalidate governance, REWORK/audit state, live remote refs, the exact three-commit parent chain, commit messages, changed paths, secret/artifact boundaries, validation branches, run `29635940873`, tags, and Releases.
2. Push the exact P3-005 three-commit sequence to `main` without amend, squash, rebase, merge, force, tag, or Release operations.
3. Require the exact closure commit main CI to pass Backend, Frontend, workflow policy, dependency, secret, and SBOM jobs; Docker and release evidence must be skipped by normal main-push policy.
4. Record P3-005 main CI evidence and retain `PASS / CLOSED`.
5. Create `docs/tasks/P3-006_STRUCTURED_REFERENCE_FULL_CORPUS.md` with `ALIGNMENT REQUIRED` and implementation, full-corpus, private Zotero, and network authorization all `NOT GRANTED`.
6. Switch `docs/tasks/CURRENT_TASK.md` to P3-006 and synchronize project state, v1.2 roadmap, README task pointer, and this alignment.
7. Create and push one docs-only staging commit with message `docs: record P3-005 main CI and stage P3-006`.
8. Require the staging commit main CI to pass with the same normal-main job policy and no uploaded artifacts or release-state changes.
9. After staging CI passes, output a complete P3-006 execution alignment and stop for confirmation.
10. Do not implement P3-006 or access any Article store, corpus, network service, real Provider, or private Zotero library.

## 3. Purpose

Close P3-005 with independently verifiable main-branch evidence, then persist P3-006 as the sole current canonical task while preserving a strict no-implementation and no-data-access boundary until its complete execution alignment is separately confirmed.

## 4. Planned Execution

1. Read governing and canonical files; stop on REWORK/FAIL audit.
2. Fetch remote refs and verify the exact clean baseline and `v1.1.0` target.
3. Audit the P3-005 parent chain, subjects, cumulative paths, diff, secrets, artifacts, validation branches/run, tags, and Releases.
4. Push the exact sequence to `main`, verify synchronization, and wait for exact-commit main CI.
5. On CI PASS, update only the eight approved documentation paths and stage P3-006 as unauthorized.
6. Run diff, changed-path, secret, artifact, local-path, and Git audits.
7. Create the exact docs-only staging commit and push it normally to `main`.
8. Wait for staging main CI; verify artifacts, refs, tags, Releases, and clean synchronization.
9. Output the complete P3-006 execution alignment and request confirmation without writing or executing it.

Stop on remote drift, unknown worktree change, REWORK/FAIL audit, commit-chain mismatch, test/CI failure, forbidden artifact/secret, unexpected workflow artifact, tag/Release drift, out-of-allowlist change, or any need for P3-006 processing, network, Provider, private Zotero, candidate, tag, Release, or attestation.

## 5. Selection Rationale

Preserving and pushing the exact already validated commit chain gives GitHub a direct audit trail from implementation through the workflow-boundary fix and local closure. A separate docs-only staging commit cleanly changes governance from closed P3-005 to unapproved P3-006 without mixing product work or retroactively rewriting validated commits.

## 6. Alternatives

| Option | Advantages | Disadvantages | Decision |
| --- | --- | --- | --- |
| Push exact chain, verify, then create a docs-only staging commit | Preserves provenance and separates implementation from next-task governance | Requires two CI waits | Selected |
| Squash or amend before push | Shorter history | Destroys exact validated lineage | Prohibited |
| Stage P3-006 before first main CI | Fewer remote steps | Mixes unverified closure with next-task state | Rejected |
| Begin P3-006 immediately | Faster apparent progress | Lacks alignment and data authorization | Prohibited |

## 7. Deliverables

- Exact P3-005 three-commit sequence synchronized to `main`.
- P3-005 main CI evidence in `docs/P3_005_CI_SECURITY_PROVENANCE_REPORT.md` and its canonical task.
- `docs/tasks/P3-006_STRUCTURED_REFERENCE_FULL_CORPUS.md` with all execution/data authorizations not granted.
- Updated `docs/tasks/CURRENT_TASK.md`, `docs/00_PROJECT_STATE.md`, `docs/V1_2_ROADMAP.md`, `README.md`, and this alignment.
- One docs-only staging commit with the exact approved subject.
- Successful main CI for both the P3-005 closure commit and P3-006 staging commit.
- A complete P3-006 execution alignment shown to the user but not executed or persisted as confirmed.

## 8. Acceptance Criteria

- Initial chain is exactly `ed5bef2 -> 80e8823 -> 666e93f -> ff19c52`, with the approved subjects and no forbidden path or artifact.
- Validation branch `validation/p3-005-provenance-666e93f` and run `29635940873` bind to the exact fix commit and all eight jobs pass.
- `main` receives the exact chain without history rewrite and run [`29637475061`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29637475061) passes the six normal-main jobs; Docker and release evidence are skipped.
- P3-005 remains `PASS / CLOSED` and records implementation, fix, closure, validation, and main CI evidence.
- P3-006 is the current canonical task with `ALIGNMENT REQUIRED`; implementation, full-corpus, private Zotero, and network authorization are all `NOT GRANTED`.
- The staging commit changes only the eight approved documentation paths and has subject `docs: record P3-005 main CI and stage P3-006`.
- Staging main CI passes the six normal-main jobs; Docker and release evidence are skipped; workflow artifacts remain `0`.
- Formal version remains `v1.1.0`; candidate remains unassigned; existing tags, Releases, validation branches, and published attestations do not change.
- Full-corpus processing, Article-store access, network access, Provider calls, private Zotero access, and P3-006 implementation all remain `0`.
- Final `main == origin/main == <staging commit>` with clean worktree, index, and untracked state.

## Allowed Changes

- `docs/P3_005_CI_SECURITY_PROVENANCE_REPORT.md`
- `docs/tasks/P3-005_CI_SECURITY_AND_RELEASE_PROVENANCE.md`
- `docs/tasks/P3-006_STRUCTURED_REFERENCE_FULL_CORPUS.md`
- `docs/tasks/CURRENT_TASK.md`
- `docs/00_PROJECT_STATE.md`
- `docs/V1_2_ROADMAP.md`
- `alignment.md`
- `README.md`, limited to the current task/gate pointer

## Git and External Boundary

- Normal push of the exact P3-005 sequence to `main`: authorized and completed.
- One docs-only staging commit and normal push to `main`: authorized.
- Read-only GitHub Actions, branch, tag, Release, and artifact verification: authorized.
- Force push, force-with-lease, amend, squash, rebase, merge, branch deletion, tag, Release, candidate, attestation publication, and repository-setting writes: prohibited.
- P3-006 implementation, full-corpus execution, Article-store access, network requests, real Provider calls, and private Zotero access: not granted.

## Current Execution Result

- Governance, REWORK/audit, live baseline, commit chain, changed paths, secret/artifact policy, validation branches, run `29635940873`, tags, and Releases: PASS.
- Exact P3-005 sequence push to `main`: PASS.
- P3-005 closure main CI run [`29637475061`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29637475061): PASS with six required jobs successful and two policy skips.
- P3-006 canonical task: staged with `ALIGNMENT REQUIRED` and all execution/data authorizations `NOT GRANTED`.
- Remaining authorized work: create and push the docs-only staging commit, verify its main CI and final invariants, then present the unexecuted P3-006 execution alignment for confirmation.
