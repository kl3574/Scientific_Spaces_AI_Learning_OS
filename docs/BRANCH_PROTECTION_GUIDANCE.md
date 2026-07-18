# Branch Protection Guidance

## Status

This document is guidance only. P3-005 does not call GitHub APIs or modify repository rules.

## Recommended `main` Rules

- Require a pull request before merge.
- Require at least one approving review and dismiss stale approvals after new commits.
- Require conversation resolution.
- Require branches to be up to date before merge.
- Block force pushes and branch deletion.
- Restrict bypass to named repository administrators for documented emergencies.
- Require signed commits if the repository's contributor workflow can support them consistently.

## Recommended Required Checks

- `Backend pytest`
- `Frontend build`
- `Workflow policy`
- `Dependency audit`
- `Secret audit`
- `SBOM validation`

`Docker compose smoke` is intentionally skipped on ordinary PR/main events and runs for manual or `v*` tag workflows. Do not make it a normal-branch required check unless the trigger policy is changed and validated. It remains a release precondition.

`Release evidence dry-run` is exact-tag gated and should not be a normal `main` required check.

## Workflow Governance

- Require review from workflow/security owners for `.github/workflows/`, `.github/security/`, `scripts/security/`, and `scripts/release/`.
- Keep GitHub Actions permissions read-only by default.
- Do not grant ordinary CI `id-token: write`, `contents: write`, `packages: write`, or attestation/release permissions.
- Keep third-party Actions pinned to immutable SHAs and review pin changes using `docs/ACTION_PIN_UPDATE_SOP.md`.
- Do not allow Dependabot pull requests to auto-merge or trigger release behavior.

## Verification After Manual Configuration

After an authorized administrator applies repository rules, open a non-functional test pull request and confirm every normal required check reports, direct pushes are rejected according to policy, and tag/manual release jobs remain outside ordinary branch publication authority.
