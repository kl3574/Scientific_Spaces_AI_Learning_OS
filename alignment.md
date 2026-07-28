# P3-006.1 Human Review Completion - Canonical Staging Alignment

Canonical task:
`docs/tasks/P3-006_1_HUMAN_REVIEW_COMPLETION.md`

## 1. Background

- P3-006 is `CONDITIONAL / CLOSED`; all machine gates passed.
- The exact corpus contains 1,311 Articles and produced 12,859 reference
  records from 24,514 fully classified candidates.
- The Article Store SHA, corpus fingerprint, and Reference Store build
  fingerprint are frozen in the canonical task.
- Sixty-four deterministic human-review cases exist, but there are zero real
  reviewer results and no human correctness metric.
- P3-006-CI-001 is `PASS / CLOSED`; its closure commit
  `df521b9e9d5a39c82f843c4708c4b337f4f48f3e` passed main CI run
  `30322970832` with zero artifacts.
- The user explicitly confirmed this staging alignment and authorized one
  docs-only commit, ordinary main push, and exact-SHA main CI validation.
- The current task stages governance only. It does not authorize P3-006.1
  implementation or human-review execution.

Authorization state:

- Implementation: NOT GRANTED.
- Review packet access: NOT GRANTED.
- Worksheet creation: NOT GRANTED.
- Completed decision access: NOT GRANTED.
- Real human-review execution: NOT GRANTED.
- Private Zotero: NOT GRANTED.
- Product/source/Provider network: NOT GRANTED.
- P3-007, candidate, tag, Release, and attestation: NOT GRANTED.

## 2. Requirements

1. Prove the clean synchronized baseline at
   `df521b9e9d5a39c82f843c4708c4b337f4f48f3e`.
2. Reverify P3-006-CI-001 closure CI run `30322970832` and zero artifacts.
3. Create the durable P3-006.1 canonical task with status
   `ALIGNMENT REQUIRED`.
4. Define exact corpus/store identities, the 64-case expectation, reviewer
   definition, privacy boundary, immutable fields, human fields, metrics,
   status gates, runtime policy, and future Git plan.
5. Define future execution as Stage A worksheet preparation followed by a
   stop for real human input, then separately authorized Stage B validation
   and closure.
6. Switch `CURRENT_TASK.md` and project/roadmap/README pointers to P3-006.1
   without changing P3-006 from `CONDITIONAL / CLOSED`.
7. Keep every implementation and review-data authorization `NOT GRANTED`.
8. Modify only approved documentation paths.
9. Pass diff, changed-path, artifact, secret, and Git audits.
10. Create `docs: stage P3-006.1 human review completion`, push it normally
    to main, and require exact-SHA main CI success with zero artifacts.
11. After CI, output the complete future execution alignment and stop for
    confirmation.

## 3. Purpose

Create durable, fail-closed governance for completing the finite P3-006 human
review limitation while preventing automated verdict fabrication, review-data
leakage, Reference Store mutation, private Zotero access, or premature P3-007
progression.

## 4. Planned Execution

1. Read governance, P3-006 evidence, v1.2 evaluation/acceptance contracts, and
   ADR 0006.
2. Check REWORK/audit, fetch tags, and prove the exact clean baseline.
3. Reverify the P3-006-CI-001 closure run and artifact count.
4. Create `docs/tasks/P3-006_1_HUMAN_REVIEW_COMPLETION.md`.
5. Update `CURRENT_TASK.md`, project state, v1.2 roadmap, this alignment, and
   the README current-task pointer.
6. Do not modify `docs/tasks/README.md` unless its generic index requires a
   task-specific entry.
7. Run docs-only changed-path, diff, artifact, secret, and Git checks.
8. Create the authorized staging commit without amend/rebase.
9. Refresh remote state, push main normally, and verify synchronization.
10. Locate the exact staging-SHA push CI; require Backend, Frontend, workflow
    policy, dependency audit, secret audit, and SBOM success, policy-correct
    Docker/release skips, overall SUCCESS, and zero artifacts.
11. Audit the final clean state, output the complete P3-006.1 execution
    alignment, and stop before packet or worksheet access.

Stop immediately if the Git/governance baseline changes, a REWORK/FAIL audit
exists, an out-of-allowlist file is required, an audit or CI gate fails, or
work would require review data, Reference Store mutation, private Zotero,
Provider/source access, P3-007, candidate, tag, Release, attestation, or
history rewrite.

## 5. Selection Rationale

A docs-only canonical staging commit gives the future review task a durable
identity and explicit permission boundaries before any sensitive runtime
review data is touched. Separating Stage A from Stage B prevents Codex from
creating a worksheet and then treating automated or incomplete values as
human evidence. Exact-SHA CI ensures the governance transition does not
weaken repository security or build gates.

## 6. Alternatives

| Option | Result |
| --- | --- |
| Execute review immediately | Prohibited; packet, worksheet, and real-review permissions are not granted |
| Keep P3-006 as the current task | Rejected; the finite limitation now has a separately authorized canonical staging task |
| Store review rows in Git | Prohibited by privacy and runtime-artifact policy |
| Use Codex, fixtures, or LLM judgments as reviewers | Prohibited; not human correctness evidence |
| One combined worksheet-and-closure stage | Rejected; it removes the mandatory stop for real human input |
| Canonical docs-only staging plus later two-stage confirmation | Selected |

## 7. Deliverables

- `docs/tasks/P3-006_1_HUMAN_REVIEW_COMPLETION.md`
- Updated `docs/tasks/CURRENT_TASK.md`
- Updated `docs/00_PROJECT_STATE.md`
- Updated `docs/V1_2_ROADMAP.md`
- Updated `alignment.md`
- Updated README current-task/status pointer
- One docs-only staging commit
- Exact staging-SHA main CI evidence with zero artifacts
- A complete future P3-006.1 execution alignment in the final response only

`docs/tasks/README.md` is unchanged because it maintains a generic canonical
task index and has no per-task listing.

## 8. Acceptance Criteria

- Starting and final main are synchronized; worktree, index, and untracked
  files are clean.
- P3-006 remains `CONDITIONAL / CLOSED`.
- P3-006-CI-001 remains `PASS / CLOSED`.
- P3-006.1 is the current canonical task with status `ALIGNMENT REQUIRED`.
- Every P3-006.1 implementation, packet, worksheet, completed-decision,
  real-review, private-Zotero, and network permission remains `NOT GRANTED`.
- The canonical task defines all identities, fields, reviewer/privacy rules,
  Stage A/Stage B boundaries, formulas, status gates, artifact rules, future
  Git plan, and stop conditions required by the confirmed attachment.
- No review packet, worksheet, human decision, comment, metric, Article body,
  private Zotero data, runtime artifact, secret, or local absolute path enters
  Git.
- Changed paths are limited to the approved documentation allowlist.
- Staging commit message is exactly
  `docs: stage P3-006.1 human review completion`.
- Exact staging-SHA main CI succeeds for Backend, Frontend, workflow policy,
  dependency audit, secret audit, and SBOM; Docker and release dry-run are
  skipped by normal main-push policy; artifacts equal zero.
- P3-007 remains not staged; candidate stays unassigned; published tags and
  Releases remain unchanged; attestation publication remains zero.
- Final output presents the complete future execution alignment and requests
  confirmation. No P3-006.1 execution begins automatically.
