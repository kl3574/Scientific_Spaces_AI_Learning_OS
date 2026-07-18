# CI Security Triage SOP

## Scope

This SOP covers the P3-005 workflow policy, dependency, secret, and suppression gates. It does not authorize a real Provider, private-data access, a release, or repository-setting changes.

## Local Commands

Run from the repository root:

```bash
python scripts/security/check_workflow_policy.py
python scripts/security/validate_suppressions.py
python scripts/security/run_dependency_audit.py
python scripts/security/run_secret_audit.py
```

Dependency auditing reads the committed Python and npm lockfiles and queries trusted public advisory services. Secret auditing scans the current repository files and bounded Git history without printing matched values.

## Workflow Policy Failure

1. Identify the workflow, line, Action, or permission named by the finding.
2. Replace mutable third-party Action references with a verified 40-character commit SHA and readable version comment.
3. Keep workflow and job permissions explicit. Ordinary CI must remain `contents: read` and must not receive OIDC, release, package, or attestation write permissions.
4. Re-run the policy checker and focused tests.

Do not weaken the checker to accept mutable references or implicit permissions.

## Dependency Finding

The policy in `.github/security/dependency-policy.json` blocks `MEDIUM`, `HIGH`, `CRITICAL`, and `UNKNOWN` findings for runtime and development dependencies. `LOW` findings remain visible.

1. Confirm package, locked version, dependency scope, advisory ID, severity, and scanner sources.
2. Prefer a lockfile update that removes the vulnerable version, handled as a separate dependency-change task.
3. If a finding is demonstrably inapplicable, add an exact suppression only after review.
4. Re-run all scanners because an advisory may be known to only one source.

Scanner unavailability, malformed output, and unresolved severity are fail-closed conditions.

## Suppression Requirements

Every suppression must include the exact ecosystem/rule identity, package or path identity, owner, reason, HTTPS tracking URL, creation date, review date, and expiry date. It must be unexpired and match a current finding. Unmatched, expired, broad, or fabricated suppressions fail validation.

Credible secret findings cannot be suppressed. Synthetic test fixtures may be classified, but their matched values must still never appear in logs.

## Secret Finding

1. Treat every `credible` classification as a blocker.
2. Use only the reported rule ID, path, line, and irreversible fingerprint for triage.
3. Never paste, print, or store the matched value.
4. Revoke or rotate the credential through its owner if it may be real.
5. Remove it from the current tree and assess Git history using an explicitly authorized incident procedure.
6. Re-run the bounded current-tree and history scan.

Do not rewrite Git history, force push, or rotate credentials as part of routine P3-005 execution.

## Closure Evidence

Record the exact command, date, status, finding counts, suppression counts, and relevant tracking issue. A gate closes only when its command exits successfully and no blocking finding remains.
