# P3-003 Structured Reference Extraction Pilot Preparation

## 1. Background

Scientific Spaces AI Learning OS has released `v1.1.0`. P3-001 post-release validation and P3-002 v1.2 product requirements and architecture are reported as PASS, with P3-002 Scope Decision A and expected baseline commit `edc6e4a4f619c8b7bc0cd3de480fbd64a463aabf`. Random Codex attachment UUIDs are transport locators, not stable task identities. This task persists task authority in the repository and prepares P3-003 for a separate implementation alignment.

Historical transport evidence only:

- Attachment SHA-256: `cf92fb7f42056bb4e6dbaa2e09efa36ba60872a574358ba929f22252858d1c0a`
- Attachment size: 1,031 lines / 20,396 bytes

Canonical task specification: `docs/tasks/P3-003_STRUCTURED_REFERENCE_PILOT.md`

Architecture baseline: `edc6e4a4f619c8b7bc0cd3de480fbd64a463aabf`

External attachments are transport-only input and are not the long-term source of truth.

Current authorization is limited to task-authority persistence and GitHub synchronization. P3-003 implementation authorization is `NOT GRANTED`. The next action is to obtain confirmation for the P3-003 execution alignment.

## 2. Requirements

1. Verify clean synchronized `main`, exact P3-002 baseline, immutable `v1.1.0` target, P3-002 main CI, and absence of unresolved `REWORK.md` or FAIL audit.
2. Create `docs/tasks/README.md`, `TEMPLATE.md`, `CURRENT_TASK.md`, and `P3-003_STRUCTURED_REFERENCE_PILOT.md` without symlinks.
3. Define repository task-authority precedence, attachment transport policy, task lifecycle, and completion synchronization policy.
4. Persist the approved P3-003 pilot scope, contracts, fixtures, runtime outputs, gates, artifact policy, Git plan, and next action without implementing the pilot.
5. Set P3-003 to `ALIGNMENT REQUIRED`, with implementation authorization `NOT GRANTED` and candidate version `Not assigned`.
6. Update `alignment.md`, `docs/00_PROJECT_STATE.md`, `roadmap.md`, and README governance links.
7. Add a minimal non-weakening Persistent Task Authority section to `AGENTS.md` only if it is compatible with existing governance.
8. Run documentation consistency checks, Backend tests, Frontend build, and artifact/secret audit.
9. Commit as `docs: persist P3-003 task authority`, push to `origin/main`, and verify main CI.
10. Do not implement or run P3-003, process corpus data, call providers, access private Zotero data, change frozen contracts, assign a v1.2 candidate, or create a tag or Release.

## 3. Purpose

Make the GitHub repository the durable, auditable source of truth for the current task so humans, ChatGPT, and Codex can determine task identity, authorization, scope, acceptance, completion, CI evidence, and next action without relying on ephemeral attachment paths.

## 4. Execution Plan

1. Read all required governance, v1.2 specification, project-state, roadmap, and ADR files.
2. Fetch origin/tags and verify Git, tag, REWORK/audit, and P3-002 CI baselines; stop on any mismatch or failed gate.
3. Create the four `docs/tasks/` authority files from approved v1.2 contracts.
4. Update current alignment, project state, roadmap pointer, and README task-governance links.
5. Assess and, if compatible, minimally extend `AGENTS.md` without weakening existing rules.
6. Check document references and status consistency; run Backend tests and Frontend build.
7. Audit the exact diff, tracked artifacts, secrets, and prohibited implementation paths.
8. Commit only the authorized governance/documentation files and push `main` without force, rebase, amend, tag, or Release actions.
9. Locate and wait for the exact main CI run; require Backend and Frontend PASS and Docker smoke SKIPPED by policy.
10. Verify `main == origin/main`, a clean worktree, unchanged `v1.1.0`, and P3-003 still awaiting implementation alignment.

## 5. Rationale

Version-controlled canonical task specifications provide stable identity, review history, and CI evidence. Keeping `CURRENT_TASK.md` as the single entry point and `alignment.md` as repository-state-specific authorization separates durable task meaning from temporary transport and prevents attachment UUID churn from creating false task mismatches.

## 6. Alternatives

The required approach is to persist task authority under `docs/tasks/` and synchronize it through GitHub. Continuing to treat attachments as long-term authority is rejected because their paths and raw hashes are unstable.

For `AGENTS.md`, two compliant branches remain:

- Apply the minimal Persistent Task Authority addition when it does not conflict with existing confirmation, REWORK, audit, artifact, secret, commit, or push rules.
- Leave `AGENTS.md` unchanged and record the recommendation if compatibility cannot be established.

## 7. Deliverables

1. `docs/tasks/README.md`
2. `docs/tasks/TEMPLATE.md`
3. `docs/tasks/CURRENT_TASK.md`
4. `docs/tasks/P3-003_STRUCTURED_REFERENCE_PILOT.md`
5. Updated `alignment.md`, `docs/00_PROJECT_STATE.md`, `roadmap.md`, and `README.md`
6. Optional compatible minimal update to `AGENTS.md`
7. Documentation, test/build, artifact/secret, Git, and CI evidence
8. Commit `docs: persist P3-003 task authority`, pushed to `origin/main`

## 8. Acceptance Criteria

- Starting branch is clean synchronized `main` at `edc6e4a4f619c8b7bc0cd3de480fbd64a463aabf`; `v1.1.0^{}` remains `3efbe2a792a9853f1bac456f0287c3b5b62713ce`; P3-002 CI is successful.
- No unresolved REWORK or FAIL audit exists.
- All four regular `docs/tasks/` files exist and implement the required authority model, template, current-task pointer, and P3-003 specification.
- P3-003 remains `ALIGNMENT REQUIRED`, `IMPLEMENTATION NOT YET AUTHORIZED`, and candidate version `Not assigned`.
- Current canonical authority does not depend on an absolute attachment path.
- Project state, roadmap, README, alignment, and task files agree on version, phase, status, authorization, and next action.
- `git diff --check`, required file/status checks, Backend tests, and Frontend build pass.
- No runtime/private artifact, secret, product code, reference fixture, pilot output, corpus data, tag, or Release is introduced.
- The authorized commit is pushed; exact main CI reports Backend PASS, Frontend PASS, Docker smoke SKIPPED, and overall SUCCESS.
- Final local `main` matches `origin/main`, the worktree is clean, and the next required action is confirmation of the P3-003 execution alignment.

## Confirmation

The user explicitly confirmed this execution alignment with: `确认执行，方案准确无误`.
