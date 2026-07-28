# P3-006-CI-001 Dependency Audit Repair

## Status

PASS / CLOSED

## Task Identity

P3-006-CI-001 Dependency Audit Failure Triage and Repair

## Authoritative Baseline

- Repository: `kl3574/Scientific_Spaces_AI_Learning_OS`
- Branch: `main`
- Required starting commit: `f2496cafa4a54440b19e4491294277b70a1f07cf`
- Original failed workflow run: `30320834573`
- Original failed job: `90156179263` (`Dependency audit`)
- Previous task: P3-006 Structured Reference Full-Corpus Build, `CONDITIONAL / CLOSED`
- Formal version: `v1.1.0`
- Candidate version: not assigned

## Authorization

- Implementation authorization: CONSUMED / CLOSED FOR THE EXACT DEPENDENCY-AUDIT FAILURE
- Dependency update authorization: CONSUMED / CLOSED FOR THE MINIMUM OFFICIALLY FIXED VERSIONS
- Scanner/parser repair authorization: NOT USED
- Suppression authorization: NOT GRANTED
- Full-corpus authorization: NOT GRANTED
- Private Zotero authorization: NOT GRANTED
- Product/source network authorization: NOT GRANTED
- Read-only advisory network authorization: GRANTED only for GitHub Actions, PyPI, npm, OSV, GitHub Advisory Database, and official upstream package metadata

## Background

The exact P3-006 completion commit was pushed to `main`, but its mandatory
dependency-audit job failed. Backend tests, Frontend build, workflow policy,
secret audit, and SBOM validation passed; Docker and release evidence were
skipped by the normal main-push policy; workflow artifacts were zero.

The failure log reports actual blocked npm vulnerability findings. This repair
task must diagnose every finding, confirm affected and fixed versions from at
least two authoritative sources, make the smallest safe repair, and restore a
successful dependency gate without weakening policy or changing product
behavior.

P3-006 remains `CONDITIONAL / CLOSED`. Its 64 deterministic human-review cases
remain pending with zero real reviewers; that limitation is outside this task.

## Goals

- Preserve the exact Git and governance baseline.
- Capture and classify the complete failed-job evidence.
- Confirm each advisory, affected range, minimum official fixed version,
  dependency scope, and direct/transitive status.
- Apply only the minimum compatible dependency and lockfile updates required
  to remove all blocked findings.
- Reproduce the dependency failure before repair and prove two deterministic
  successful audits after repair.
- Pass security tests, full Backend tests, Frontend install/build, SBOM,
  secret, artifact, and immutable-corpus checks.
- Pass a full workflow-dispatch validation run on a dedicated validation
  branch before pushing the repair to `main`.
- Pass the repair commit main CI, then record and push a docs-only closure
  commit whose main CI also passes.
- Restore `CURRENT_TASK.md` to P3-006 `CONDITIONAL / CLOSED` after closure.

## Non-Goals

- No full-corpus extraction, rebuild, resume, or Reference Store mutation.
- No Article Store mutation.
- No reference normalization, identity, deduplication, provenance, or API
  change.
- No product feature or product API change.
- No suppression, risk acceptance, policy weakening, or scanner removal.
- No source-site, Provider, paid-service, or private Zotero access.
- No P3-006.1 or P3-007 staging.
- No candidate, tag, Release, or attestation.

## Root-Cause Classes

Exactly one primary class must be selected:

- `A. TRANSIENT_SCANNER_FAILURE`
- `B. REAL_DEPENDENCY_VULNERABILITY`
- `C. AUDIT_TOOL_OR_PARSER_DEFECT`
- `D. SUPPRESSION_OR_RISK_ACCEPTANCE_REQUIRED`

The original log contains concrete npm findings and therefore initially
classifies as `B. REAL_DEPENDENCY_VULNERABILITY`. This classification may only
change if complete authoritative evidence contradicts the log.

## Allowed Changes

Only the smallest root-cause-related subset of:

- `.github/security/dependency-policy.json`
- `.github/security/suppressions.json`
- `.github/security/tool-versions.json`
- `.github/workflows/ci.yml`
- `scripts/security/run_dependency_audit.py`
- `scripts/security/validate_suppressions.py`
- `scripts/security/lockfiles.py`
- `scripts/security/tests/`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `frontend/package.json`
- `frontend/package-lock.json`
- this task specification
- `docs/tasks/CURRENT_TASK.md`
- `docs/P3_006_STRUCTURED_REFERENCE_FULL_CORPUS_REPORT.md`
- `docs/00_PROJECT_STATE.md`
- `docs/V1_2_ROADMAP.md`
- `alignment.md`

No path outside this list may be modified without stopping for authorization.

## Dependency Repair Rules

- Use at least two consistent authoritative sources per advisory.
- Select the minimum officially fixed patch or minor version.
- Update only the target package and its necessary transitive closure.
- Do not use broad `npm update` or broad `uv lock --upgrade`.
- Do not perform a major upgrade.
- Do not add a suppression.
- Do not downgrade `UNKNOWN`, lower policy thresholds, or remove a scanner.
- Preserve fail-closed behavior for unavailable and malformed scanner output.
- Stop for user decision if no fixed version exists, only a major update
  exists, or compatibility risk is unresolved.

## Root-Cause and Advisory Evidence

Primary classification: `B. REAL_DEPENDENCY_VULNERABILITY`.

The original CI log and a local pre-repair reproduction both reported 11
blocked runtime npm findings. `pip-audit`, npm audit, and OSV all completed
normally, so this is neither a transient scanner failure nor a parser defect.

GitHub Advisory Database and OSV independently agree on these ranges:

| Package | Directness | Advisory | Severity | Affected installed version | Minimum fixed version |
| --- | --- | --- | --- | --- | --- |
| `next` | direct | `GHSA-4633-3j49-mh5q` | MEDIUM / MODERATE | `15.5.20` | `15.5.21` |
| `next` | direct | `GHSA-4c39-4ccg-62r3` | MEDIUM / MODERATE | `15.5.20` | `15.5.21` |
| `next` | direct | `GHSA-68g3-v927-f742` | MEDIUM / MODERATE | `15.5.20` | `15.5.21` |
| `next` | direct | `GHSA-89xv-2m56-2m9x` | HIGH / HIGH | `15.5.20` | `15.5.21` |
| `next` | direct | `GHSA-955p-x3mx-jcvp` | MEDIUM / MODERATE | `15.5.20` | `15.5.21` |
| `next` | direct | `GHSA-m99w-x7hq-7vfj` | HIGH / HIGH | `15.5.20` | `15.5.21` |
| `next` | direct | `GHSA-p9j2-gv94-2wf4` | HIGH / HIGH | `15.5.20` | `15.5.21` |
| `next` | direct | `GHSA-q8wf-6r8g-63ch` | MEDIUM / MODERATE | `15.5.20` | `15.5.21` |
| `postcss` | direct | `GHSA-6g55-p6wh-862q` | HIGH / HIGH | `8.5.10` | `8.5.12` |
| `postcss` | direct | `GHSA-r28c-9q8g-f849` | HIGH / HIGH | `8.5.10` | `8.5.18` |
| `sharp` | optional transitive through Next | `GHSA-f88m-g3jw-g9cj` | HIGH / HIGH | `0.34.5` | `0.35.0` |

The required aggregate minimums are therefore:

- `next`: `15.5.21`
- `postcss`: `8.5.18`, because it is the first version fixing both findings
- `sharp`: `0.35.0`

Authoritative sources:

- `https://github.com/advisories/<GHSA-ID>`
- `https://osv.dev/vulnerability/<GHSA-ID>`
- npm registry metadata for the exact fixed package versions
- Sharp `v0.35.0` upstream changelog

Next 15.5.21 declares optional `sharp ^0.34.3`, which cannot resolve the
security-fixed `0.35.0`. The repair therefore adds a targeted npm override for
only this optional transitive dependency. Compatibility is demonstrated by:

- clean `npm ci` with no invalid dependency-tree exit;
- `next@15.5.21`, `postcss@8.5.18`, and overridden `sharp@0.35.0`;
- a successful Sharp 0.35.0 in-memory PNG transformation;
- successful execution of Next 15.5.21's real `optimizeImage` path through
  Sharp 0.35.0, producing a non-empty PNG with a valid signature;
- successful Next production build.

No suppression or policy/scanner change is used.

## Pre-Commit Validation Evidence

- Original failed run/job: `30320834573` / `90156179263`
- Complete log: captured outside the repository under `/tmp`
- Pre-repair local audit: BLOCKED, 11 findings, 11 blocked, 0 suppressed
- Final post-repair audit 1: PASS, 0 findings, 0 blocked, 0 suppressed
- Final post-repair audit 2: PASS, 0 findings, 0 blocked, 0 suppressed
- Final audit outputs: byte-identical
- Package inventory: PyPI 40, npm 219
- Security unit tests: 17 passed
- Workflow policy: PASS
- Suppression validation: PASS, 0 dependency and 0 secret suppressions
- Secret audit: PASS, 0 credible/reported/suppressed
- SBOM build and validation: PASS, 219 frontend components
- Frontend clean install: PASS, 0 npm vulnerabilities
- Frontend build: PASS
- Sharp runtime and Next image optimizer compatibility: PASS
- Backend: 540 passed, 3 skipped
- Article Store SHA:
  `3b91f22db548373a6c91bb11a5188fb3e388ab9e19c4429e8e8fac918609a505`
- Corpus fingerprint:
  `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d`
- Reference Store build fingerprint:
  `70ab191621aa8819f3c195c116aec5b5ae05f44c0b90fb0d11e6cb4365d5d846`
- Reference Store audit: PASS; source mutations and rebuilds: 0
- Artifact audit: PASS, 0 new tracked runtime/private artifacts

## Verification

Required evidence:

1. Exact Git baseline and complete original failed-job log.
2. One pre-repair dependency audit written only under `/tmp`.
3. Two post-repair dependency audits written only under `/tmp`, each with:
   - `status = PASS`
   - `blocked_count = 0`
   - suppression validation PASS
   - pip-audit PASS
   - npm audit PASS
   - OSV multi-ecosystem PASS
4. Stable package inventory and finding evaluation across both post-repair
   audits, excluding nondeterministic timestamps.
5. Security unit tests, workflow policy, suppression validation, secret audit,
   temporary SBOM build, and SBOM validation PASS.
6. Full Backend tests PASS.
7. `npm --prefix frontend ci` and Frontend build PASS.
8. Article Store SHA, corpus fingerprint, and Reference Store build
   fingerprint unchanged.
9. `git diff --check`, artifact audit, secret audit, and changed-path audit
   PASS.
10. Validation branch workflow-dispatch run PASS for Backend, Frontend,
    workflow policy, dependency audit, secret audit, SBOM, Docker, and release
    evidence, with zero artifacts and no publish authorization.
11. Repair commit main CI PASS with Docker and release evidence skipped by
    policy and zero artifacts.
12. Docs-only closure commit main CI PASS with zero artifacts.

## Git Plan

- Repair commit: `fix: resolve dependency audit blocker`
- Validation branch:
  `validation/p3-006-ci-dependency-<SHORT_SHA>`
- Validation branch push: ordinary non-force push
- Main repair push: allowed only after validation CI PASS
- Closure commit: `docs: close dependency audit repair`
- Closure main push: allowed only after repair main CI PASS
- Amend, rebase, force push, tag, Release, and attestation: prohibited

## PASS Criteria

- Root cause is uniquely classified and supported by complete logs.
- All advisories have authoritative affected/fixed-version evidence.
- The smallest compatible repair removes all blocked findings.
- Suppression count remains zero and policy/scanner coverage is unchanged.
- All local verification, validation-branch CI, repair main CI, and closure
  main CI pass with zero workflow artifacts.
- No product, reference, corpus, Article, Provider, Zotero, candidate, tag,
  Release, or attestation boundary is crossed.
- Task status becomes `PASS / CLOSED`.

## BLOCKED Criteria

- Root cause cannot be uniquely classified.
- A suppression, major upgrade, policy weakening, scanner removal, product
  change, or out-of-allowlist path is required.
- No official fixed version exists or compatibility is unresolved.
- Corpus/reference identities change.
- A secret, private/runtime artifact, or unknown worktree drift appears.
- Any required local, validation, or main CI gate fails.

## Closure State

- Original failed run: `30320834573`
- Original failed job: `90156179263`
- Root-cause class: `B. REAL_DEPENDENCY_VULNERABILITY`
- Repair commit: `9b0080cbe5c6483de2534ed63f9eeb5c5e5b1dbd`
- Validation branch:
  `validation/p3-006-ci-dependency-9b0080c`
- Validation run:
  [`30322598783`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30322598783)
- Validation result: PASS for Backend, Frontend, workflow policy, dependency
  audit, secret audit, SBOM, Docker compose smoke, and no-publish release
  evidence
- Validation artifacts: 0
- Validation release evidence:
  `publish_authorized=false`, `would_authorize_publish=false`
- Successful repair main CI:
  [`30322723458`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30322723458)
- Repair main CI result: PASS; Docker and release evidence skipped by the
  normal main-push policy
- Repair main CI artifacts: 0
- Suppression added: 0
- Dependency policy weakened: no
- Scanner removed: no
- Full-corpus rebuild or Reference Store mutation: no
- Article/source/Provider/private Zotero access: no

This task is `PASS / CLOSED`. `CURRENT_TASK.md` returns to P3-006
`CONDITIONAL / CLOSED`; P3-006.1 remains not staged. The next action is to
prepare and confirm a separate P3-006.1 Human Review Completion task.
