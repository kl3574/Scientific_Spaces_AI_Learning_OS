# P3-006-CI-001 Dependency Audit Repair - Confirmed Execution Alignment

Canonical task:
`docs/tasks/P3-006_CI_001_DEPENDENCY_AUDIT_REPAIR.md`

## 1. Background

- The confirmed starting point is `main` at
  `f2496cafa4a54440b19e4491294277b70a1f07cf`, synchronized with
  `origin/main` and clean.
- GitHub Actions run `30320834573` failed only its Dependency audit job
  (`90156179263`). Backend, Frontend, workflow policy, secret audit, and SBOM
  validation passed; normal main-push Docker and release jobs were skipped;
  workflow artifacts were zero.
- The complete failure log reports 11 blocked npm findings affecting
  `next@15.5.20`, `postcss@8.5.10`, and `sharp@0.34.5`.
- P3-006 remains `CONDITIONAL / CLOSED`; 64 deterministic review cases remain
  pending with zero real reviewers.
- The user explicitly confirmed and authorized this exact repair alignment.
  Attachment UUIDs are transport locators, not task identity.

Authorization:

- Exact dependency-audit repair: GRANTED.
- Minimum officially fixed dependency update: GRANTED.
- Scanner/parser repair: GRANTED only if the audit tool is the root cause.
- Read-only public advisory access: GRANTED for GitHub Actions, PyPI, npm, OSV,
  GitHub Advisory Database, and official upstream metadata.
- Suppression, full-corpus work, source/product network, Provider, private
  Zotero, P3-006.1/P3-007 staging, candidate, tag, Release, and attestation:
  NOT GRANTED.

## 2. Requirements

1. Preserve the exact Git baseline, clean worktree, and governance state.
2. Persist the canonical repair task, `CURRENT_TASK.md`, and this alignment
   before changing dependencies, lockfiles, scanner code, or policy.
3. Capture the complete original failed-job log outside the repository.
4. Select exactly one root-cause class from transient scanner failure, real
   dependency vulnerability, audit-tool defect, or suppression/risk acceptance.
5. For a real vulnerability, confirm each advisory from at least two
   authoritative sources, including affected range, minimum official fixed
   version, runtime/dev scope, and direct/transitive status.
6. Apply only minimum patch/minor fixed versions and necessary lockfile
   closure. No broad update, major upgrade, suppression, or policy weakening.
7. Reproduce the dependency audit before repair and run it twice after repair;
   both post-repair runs must pass consistently with zero blocked findings.
8. Run security tests, workflow/suppression checks, secret audit, temporary
   SBOM build/validation, full Backend tests, frontend clean install/build,
   changed-path checks, and artifact audits.
9. Prove Article Store SHA, corpus fingerprint, and Reference Store build
   fingerprint remain unchanged without rebuilding the corpus.
10. Commit the repair, push a dedicated validation branch, and require all
    workflow-dispatch jobs including Docker and release dry-run to pass with
    zero artifacts before pushing main.
11. Require the repair commit main CI to pass.
12. Record the closure in governance/report files, create a docs-only closure
    commit, push it, and require its main CI to pass.
13. Keep P3-006 `CONDITIONAL / CLOSED`; do not create P3-006.1.

## 3. Purpose

Restore a trustworthy dependency-security gate for the exact P3-006 main
commit using the smallest officially supported dependency repair, while
preserving all frozen corpus, reference, product, privacy, release, and human
review boundaries.

## 4. Planned Execution

1. Read governance/security files, check REWORK/audit, fetch, and prove the
   exact clean baseline.
2. Download the complete failed job log to `/tmp` and classify the root cause.
3. Persist canonical task authority and this alignment.
4. Run one pre-repair dependency audit under `/tmp`.
5. Verify every advisory and minimum fixed version from authoritative sources.
6. Apply the minimum targeted dependency and lockfile updates.
7. Run two post-repair audits and compare deterministic evidence.
8. Run all required local security, Backend, Frontend, SBOM, identity,
   artifact, and Git checks.
9. Create `fix: resolve dependency audit blocker`.
10. Push `validation/p3-006-ci-dependency-<SHORT_SHA>`, trigger manual CI, and
    require every job and zero-artifact gate to pass.
11. Push main, require exact repair-SHA main CI to pass, then write closure
    evidence.
12. Create and push `docs: close dependency audit repair`, require its main CI
    to pass, audit the final synchronized state, and stop.

Stop immediately if the root cause is ambiguous; a suppression, major update,
policy weakening, scanner removal, product change, out-of-allowlist path,
corpus build, source/private access, or unknown worktree cleanup is required;
or any required local/CI/artifact/secret gate fails.

## 5. Selection Rationale

The failed log contains concrete findings from both npm audit and OSV, so the
evidence supports a real-dependency-vulnerability path. Targeted fixed-version
updates retain fail-closed policy and scanner diversity while minimizing
compatibility and lockfile churn. Validation branch CI prevents an unverified
repair from reaching main.

## 6. Alternatives

| Option | Advantages | Disadvantages | Decision |
| --- | --- | --- | --- |
| Minimum official patch/minor dependency updates | Removes real findings without policy changes | Requires lockfile and full validation | Selected if fixed versions exist |
| One failed-job rerun | No code change | Invalid for concrete vulnerability findings | Rejected |
| Audit-tool parser repair | Appropriate for malformed valid scanner output | Does not address actual vulnerable packages | Rejected unless evidence changes |
| Suppression/risk acceptance | Avoids dependency change | Hides a real blocked finding; unauthorized | Prohibited |
| Broad or major dependency upgrade | May clear all findings | Excessive compatibility and lockfile scope | Prohibited |

## 7. Deliverables

- `docs/tasks/P3-006_CI_001_DEPENDENCY_AUDIT_REPAIR.md`
- Updated `docs/tasks/CURRENT_TASK.md` and `alignment.md`
- Minimum required `frontend/package.json` and `frontend/package-lock.json`
  repair, unless authoritative evidence instead proves a scanner defect
- Local before/after dependency evidence under `/tmp` only
- Security, Backend, Frontend, SBOM, corpus/store identity, artifact, secret,
  and Git evidence
- Repair commit and passing validation-branch/main CI evidence
- Updated P3-006 report, project state, v1.2 roadmap, canonical repair task,
  current-task pointer, and alignment
- Docs-only closure commit and passing final main CI evidence

## 8. Acceptance Criteria

PASS requires:

- Exact failure identity and unique root-cause classification are proven.
- Every advisory has two-source affected/fixed-version evidence.
- Only minimum compatible dependency and necessary lockfile changes occur.
- Two post-repair dependency audits pass with zero blocked/suppressed findings
  and stable inventories/evaluations.
- Security tests, workflow policy, suppression validation, secret audit, SBOM,
  full Backend tests, frontend clean install/build, immutable identity checks,
  changed-path audit, and artifact audit pass.
- Validation-branch CI passes Backend, Frontend, workflow policy, dependency
  audit, secret audit, SBOM, Docker, and release evidence with zero artifacts
  and no publish authorization.
- Repair main CI and docs-only closure main CI both pass with zero artifacts.
- P3-006 remains `CONDITIONAL / CLOSED`; P3-006-CI-001 becomes
  `PASS / CLOSED`; P3-006.1 remains not staged.
- No suppression, policy weakening, source/private access, full-corpus work,
  product change, candidate, tag, Release, or attestation occurs.

BLOCKED takes precedence if any required evidence is missing, no compatible
fixed version exists, a major update/suppression/policy change is required,
corpus/reference identity changes, a secret/artifact/worktree anomaly appears,
or any required local or CI gate fails.
