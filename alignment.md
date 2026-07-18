# P3-005 CI Security and Release Provenance - Confirmed Execution Alignment

## 1. Background

- Formal version: `v1.1.0`; candidate version: not assigned.
- Confirmed starting baseline: `ed5bef2bd8ed3dd8ba9f42e02e7faa3dc0fb81d6`.
- Canonical task: `docs/tasks/P3-005_CI_SECURITY_AND_RELEASE_PROVENANCE.md`.
- Previous task: P3-004 Real Provider Evaluation Design, `PASS / CLOSED`.
- Existing CI has one workflow with Backend pytest, Frontend build, and tag/manual Docker smoke.
- Existing third-party Actions use mutable major tags and workflow permissions are implicit.
- The user explicitly confirmed this complete execution alignment. Attachment paths remain transport locators and do not define task identity.

## 2. Requirements

1. Inventory all workflows, triggers, filters, permissions, Actions, artifacts, secrets, OIDC, release behavior, and external access.
2. Pin every third-party Action to a verified 40-character immutable SHA with a readable version comment.
3. Apply explicit least-privilege workflow and job permissions.
4. Add Python, npm, and independent multi-ecosystem dependency auditing with fail-closed parsing and structured suppressions.
5. Add bounded secret scanning that never logs matched values and blocks credible findings.
6. Generate deterministic Backend, Frontend, and combined CycloneDX 1.6 SBOMs in temporary storage.
7. Validate SBOM schema, lockfile coverage, relationships, reproducibility, size, and forbidden-content policy.
8. Implement exact-tag/manual-only release-evidence boundaries and local `--dry-run --no-publish` verification.
9. Configure bounded Dependabot updates without auto-merge or release behavior.
10. Preserve existing Backend, Frontend, Docker, product runtime, fake-provider, legacy API, and `/v1.1` behavior.
11. Document triage, Action-pin updates, SBOM verification, release provenance verification, and branch-protection guidance.
12. Run the complete local verification sequence and create one status-appropriate local commit.
13. Do not push, create or move a tag, create a Release, publish an attestation, call a real Provider, or access private Zotero/user data.

## 3. Purpose

Establish an auditable CI security baseline with immutable workflow dependencies, explicit least privilege, bounded scanning, reproducible dependency evidence, and a fail-closed release provenance boundary without changing the product runtime or publishing release evidence.

## 4. Planned Execution

1. Revalidate governance, canonical state, Git baseline, REWORK/audit, and workflow inventory.
2. Persist this alignment and mark P3-005 `IN PROGRESS`.
3. Resolve current Action releases to official immutable SHAs and record verification evidence.
4. Implement workflow pin/permission policy checks and update CI without renaming existing jobs.
5. Implement suppression, dependency, and secret audit tooling plus focused tests.
6. Implement deterministic CycloneDX generation/validation and no-publish release-evidence tooling plus focused tests.
7. Add Dependabot configuration, CI integration, SOPs, guidance, and the implementation report.
8. Run focused tests, policies, live advisory scans, secret audit, two SBOM builds/diff, provenance dry-run, Backend, Frontend, and Docker smoke.
9. Run changed-path, artifact, secret, local-path, generated-output, Git, and compatibility audits.
10. Classify PASS, CONDITIONAL, or BLOCKED; update governance documents and create one local commit. Do not push.

Stop on remote drift, unknown worktree changes, REWORK/FAIL audit, unverifiable Action SHA, credible secret, unresolved blocking vulnerability, scanner output ambiguity, SBOM instability, required out-of-scope path, test/build/Docker regression, or any need for credentials, tag, Release, formal attestation, Provider, private data, or repository-setting write.

## 5. Selection Rationale

Extend the existing `ci.yml` so security and SBOM jobs share the same trigger and exact-tag dependency graph as the preserved Backend, Frontend, and Docker jobs. Keep elevated attestation permissions isolated to a strictly gated future publish job while this task executes only local no-publish evidence validation.

## 6. Alternatives

| Option | Advantages | Disadvantages | Decision |
| --- | --- | --- | --- |
| Extend `ci.yml` with isolated security jobs | Direct gate dependencies; preserves current job names and trigger behavior | Larger workflow file | Selected |
| Separate security/release workflows | Strong file separation | Cross-workflow trust and artifact handoff are harder to prove | Rejected unless the single workflow cannot remain safe |
| Add scanners as product dependencies | Simple invocation | Changes runtime/lock contracts | Prohibited |
| Publish a test attestation | Hosted evidence | Requires external write and release identity | Prohibited in P3-005 |

## 7. Deliverables

- Updated `.github/workflows/ci.yml` and `.github/dependabot.yml`.
- Policy files under `.github/security/`.
- Security tooling and tests under `scripts/security/`.
- Release-evidence tooling and tests under `scripts/release/`.
- `docs/P3_005_CI_SECURITY_PROVENANCE_REPORT.md`.
- `docs/CI_SECURITY_TRIAGE_SOP.md`.
- `docs/ACTION_PIN_UPDATE_SOP.md`.
- `docs/SBOM_VERIFICATION_SOP.md`.
- `docs/RELEASE_PROVENANCE_VERIFICATION_SOP.md`.
- `docs/BRANCH_PROTECTION_GUIDANCE.md`.
- Updated canonical task, current-task pointer, project state, v1.2 roadmap, README, and this alignment.
- One local status-appropriate commit; no push.

## 8. Acceptance Criteria

- `third_party_action_full_sha_pin_rate = 1.0`.
- `workflow_permissions_explicit_rate = 1.0`.
- `credible_secret_findings = 0` and logs contain no matched secret value.
- Python, npm, and independent multi-ecosystem dependency gates pass under the approved severity/suppression policy.
- Suppressions are exact, owned, justified, linked, reviewable, unexpired, and matched; fake suppressions are prohibited.
- Backend, Frontend, and combined SBOMs use CycloneDX 1.6; both lockfiles are covered; repeated builds are byte-identical; combined size is at most 5 MiB.
- SBOM schema, relationships, hashes where reliable, local-path, secret, and forbidden-runtime-content checks pass.
- Exact-tag/manual provenance boundary and local no-publish dry-run pass; ordinary PR/main publish capability equals zero.
- Backend pytest, Frontend `npm ci`/build, and local/manual Docker smoke pass while normal main Docker remains skipped by policy.
- Product runtime and frozen contract changes equal zero.
- Candidate, tag, Release, formal attestation publication, real-provider calls, and private-data access equal zero.
- Generated SBOM, evidence, scanner cache/output, and runtime/private artifacts are not tracked.
- Final commit parent is `ed5bef2bd8ed3dd8ba9f42e02e7faa3dc0fb81d6`; changed paths remain in the confirmed allowlist; worktree is clean; push is not performed.

## Allowed Changes

- `.github/workflows/ci.yml`
- `.github/dependabot.yml`
- `.github/security/`
- `scripts/security/` and `scripts/security/tests/`
- `scripts/release/` and `scripts/release/tests/`
- The named P3-005 report/SOP/guidance documents
- `docs/tasks/P3-005_CI_SECURITY_AND_RELEASE_PROVENANCE.md`
- `docs/tasks/CURRENT_TASK.md`
- `docs/00_PROJECT_STATE.md`
- `docs/V1_2_ROADMAP.md`
- `alignment.md`
- `README.md`, limited to security commands and documentation links

## Network and Git Boundary

- Read-only public network access is allowed only for official Action SHA verification, trusted package/advisory data, scanner databases, and CycloneDX specifications.
- No source, lockfile, SBOM, report, secret, or private data may be uploaded to an unapproved service.
- PASS commit: `feat: add CI security and release provenance`.
- CONDITIONAL commit: `docs: record conditional CI security hardening`.
- BLOCKED commit: `docs: record CI security blockers`.
- One local commit is authorized. Push, force push, rebase, amend, candidate, tag, Release, formal attestation, and branch-protection writes are prohibited.

## Execution Result

- Implementation and all locally available security, dependency, secret, SBOM, provenance, Backend, and Frontend checks passed.
- Docker compose smoke is mandatory but unavailable because the authorized environment has no Docker-compatible runtime.
- Final task status: `BLOCKED` pending Docker smoke evidence.
- The authorized local blocker commit may be created with `docs: record CI security blockers`.
- Push, candidate, tag, Release, formal attestation publication, Provider calls, and private-data access remain prohibited and were not performed.
