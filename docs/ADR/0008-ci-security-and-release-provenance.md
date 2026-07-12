# ADR 0008: CI Security and Release Provenance

Status: Accepted

Date: 2026-07-12

## Context

Current CI runs Backend pytest and Frontend build on pull requests/main/tag/manual events; Docker smoke runs on tag and manual events. Third-party Actions use mutable major tags. The repository has prior secret/artifact audits but no integrated dependency/secret scanning policy, immutable pin enforcement, SBOM, or exact-subject release attestation.

The project publishes source/tag/Release evidence, not a container or package. Local corpus, PDF, RAG, Graph, database, backup, provider, Zotero, and user data must never become CI/release artifacts.

## Decision Drivers

- Prevent mutable workflow dependencies and excessive token permissions.
- Preserve current backend/frontend/Docker gates.
- Cover both Python and npm locked dependency graphs with more than one signal.
- Make suppression explicit, narrow, owned, and expiring.
- Produce verifiable release dependency/provenance evidence without shipping runtime data.

## Options Considered

### 1. Keep Current CI plus Manual Audits

Rejected. Manual scans do not prevent mutable Actions or provide consistent release evidence.

### 2. Container/Image Signing Pipeline

Rejected for v1.2. The project does not publish a container/package, so package write permissions and image signing add unnecessary surface.

### 3. SPDX and CycloneDX Together

Deferred. Dual-format generation increases tooling and reconciliation cost without a current consumer requirement.

### 4. Immutable CI plus CycloneDX and GitHub Attestation

Selected.

## Decision

### Action Integrity

- Pin every third-party Action to a reviewed 40-character commit SHA.
- Keep an inline comment naming the upstream semantic release.
- Reject mutable branch/tag references through a policy check.
- Use weekly Dependabot `github-actions` update PRs or equivalent reviewed proposals. No unattended bulk merge.
- Every pin update runs the complete applicable CI matrix.

Current pins to resolve in P3-005 are:

- `actions/checkout@v4`
- `actions/setup-python@v5`
- `actions/setup-node@v4`

Any new scanner/SBOM/attestation Action follows the same policy.

### Least Privilege

- Workflow default: `contents: read`.
- Backend, frontend, Docker, dependency, secret, and SBOM build jobs receive no write permission.
- `security-events: write` exists only for a SARIF upload step/job when supported and is not exposed to untrusted fork code.
- `id-token: write` and `attestations: write` exist only in an isolated trusted exact-tag release evidence job.
- `packages: write` is absent unless a future ADR approves package publication.

### Dependency and Secret Scanning

- Audit the locked `backend/uv.lock` graph with a pinned Python vulnerability tool.
- Audit `frontend/package-lock.json` with npm and an independent OSV-compatible lockfile scanner.
- Scan tracked files and a documented bounded Git-history range for secrets; use GitHub secret scanning when repository settings support it.
- Never print the matched secret; logs use rule/fingerprint/path and redacted location only.
- Critical/High unsuppressed runtime findings and credible secrets block. Medium findings require fix or narrow unexpired suppression before release. Low findings remain visible.
- Suppressions require finding ID, exact package/path/version scope, rationale, owner, review URL, and expiry. Expired, broad, unmatched, or ownerless entries fail.

### SBOM

- Generate one CycloneDX 1.6 JSON release SBOM covering Python and npm locked dependencies.
- Record project commit, commit-derived timestamp, generator versions, component hashes/versions, and dependency relationships.
- Normalize and sort deterministic fields; cap the artifact at 5 MiB.
- Validate schema and scan for secrets, absolute paths, corpus/runtime names, and private data.

CycloneDX is selected because both ecosystems have mature generators and the format supports components, dependency relationships, hashes, and tool metadata in one bounded JSON artifact. SPDX may be added later if a consumer requires it.

### Provenance and Attestation

- On an explicitly authorized exact release tag, verify annotated tag object and peeled commit before generating evidence.
- Build subjects are the CycloneDX SBOM and a small release-evidence JSON record only.
- Use GitHub artifact attestations to bind each subject digest to the exact workflow/ref/commit.
- Verify with `gh attestation verify` and independent Git tag/commit/digest checks.
- No local corpus, PDF, database, RAG/Graph, backup, private Zotero/provider output, or secret is uploaded.

### Branch Protection Guidance

Recommend, but do not automatically change:

- require Backend pytest and Frontend build;
- require conversation resolution;
- prohibit force push and deletion on `main`;
- protect `v*` release tags against movement/deletion;
- require at least one review for workflow/security changes when collaborator capacity permits;
- allow admin bypass only for documented incident recovery with follow-up audit;
- linear history is recommended for auditability but not mandatory if the project intentionally uses merge commits.

## Cache and Pull-Request Policy

- Untrusted fork pull requests receive no secrets or elevated write permissions.
- Cache keys bind runner/tool/lockfile identity. Privileged release evidence must not trust unvalidated outputs restored from an untrusted PR cache.
- Scanner databases/caches may be used for availability, but stale-data tolerance is explicit and scanner failure cannot silently become PASS.

## Consequences

Positive:

- Workflow dependencies and release subjects become auditable and immutable by digest.
- Security findings and exceptions have consistent ownership and expiry.
- Users can verify the SBOM and exact-tag build identity.

Costs and residual risks:

- SHA pins require maintenance and review.
- Scanners create false positives and only know disclosed vulnerabilities.
- GitHub attestation availability and trust depend on the GitHub platform.
- An SBOM proves declared dependency resolution, not absence of malicious code.

## Failure and Rollback

- A failed scanner, policy, SBOM, or attestation job blocks release evidence; it is not skipped silently.
- Workflow changes are reverted through normal reviewed Git history; published tags are never moved to hide a failure.
- If attestation is unavailable, release status remains blocked/conditional under `docs/V1_2_ACCEPTANCE.md`; no replacement unsigned claim is made.
- Previous valid release evidence remains immutable and is not overwritten.

## Acceptance

- Full immutable pin map and permission matrix pass static checks.
- Backend/Frontend remain green; manual/tag Docker smoke remains green.
- Dependency, secret, and suppression policies execute and fail closed.
- CycloneDX validates, covers both lockfiles, stays <=5 MiB, and passes forbidden-artifact/secret scan.
- Test/exact-release provenance binds the correct ref, commit, and subject digests.
- No repository settings are changed without separate external-write authorization.
