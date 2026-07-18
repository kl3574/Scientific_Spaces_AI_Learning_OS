# P3-005 CI Security and Release Provenance

## Status

PASS / CLOSED

IMPLEMENTATION AUTHORIZATION: CONSUMED / CLOSED

## Task Identity

P3-005 CI Security and Release Provenance

## Version State

- Formal version: `v1.1.0`
- Candidate version: Not assigned

## Previous Task

P3-004 Real Provider Evaluation Design: PASS / CLOSED

## Starting Baseline

`ed5bef2bd8ed3dd8ba9f42e02e7faa3dc0fb81d6`

P3-004 main CI run `29627617727` passed Backend and Frontend; Docker compose smoke was correctly skipped for the normal main push.

## Background

The existing CI validates Backend tests, Frontend builds, and Docker smoke under tag or manual conditions. The v1.2 architecture identified remaining supply-chain gaps: mutable third-party Action references, incomplete permission declarations, no unified dependency or secret scanning gate, no validated Backend/Frontend SBOM, and no exact-tag/manual release provenance design.

P3-005 implemented bounded repository and release-evidence hardening under the confirmed execution alignments. The original implementation was local-only; P3-005.1 subsequently authorized one exact validation-branch push, one manual workflow dispatch, and one local docs-only closure commit. A later synchronization alignment authorized the exact three-commit sequence to be pushed to `main` and verified there. Candidate assignment, tag, Release, formal attestation publication, real-provider calls, and private-data access remained prohibited.

## Goals

- Inventory every workflow, trigger, permission, third-party Action, artifact path, secret boundary, and release behavior.
- Pin every third-party GitHub Action to an immutable 40-character commit SHA with a human-readable version comment.
- Declare workflow and job permissions explicitly and apply least privilege.
- Add Python dependency scanning, npm dependency scanning, and multi-ecosystem OSV or equivalent coverage, including transitive dependencies.
- Define severity thresholds, suppression records, expiry/review rules, false-positive triage, and scanner-unavailable behavior.
- Add bounded secret scanning that never logs secret values and blocks on credible findings.
- Generate and validate deterministic CycloneDX 1.6 JSON SBOMs for Backend and Frontend components.
- Design exact-tag/manual release provenance and attestation that binds commit, tag, workflow, SBOM, and eligible release artifacts.
- Exclude corpus, PDF, Graph, RAG, databases, backups, private data, and other runtime artifacts from SBOM/provenance publication.
- Document branch-protection recommendations without modifying repository rules through an API.
- Provide an operator verification SOP.
- Preserve existing Backend, Frontend, and Docker CI behavior.

## Non-Goals

- No product runtime behavior, API, UI, storage, or data-contract change.
- No new product runtime dependency.
- No real or paid Provider call, credential access, or provider-default change.
- No private Zotero library, user data, corpus, PDF, Graph, RAG, database, backup, or runtime-store access or publication.
- No automatic tag, GitHub Release, candidate assignment, or release credential creation.
- No branch-protection API write.
- No P3-006 full-corpus reference execution.
- No weakening of existing Backend, Frontend, Docker, fake-provider, legacy API, or `/v1.1` compatibility gates.

## Future Allowed Areas

The following areas are planning candidates only. Their exact allowlist must be confirmed in the future P3-005 execution alignment:

- `.github/workflows/`
- `.github/dependabot.yml`
- `.github/`
- `scripts/security/`
- `scripts/release/`
- `docs/`
- `docs/tasks/`
- `README.md`
- `alignment.md`

## Required Design Areas

### Workflow Inventory

Record each workflow file, triggers, current and required permissions, third-party Actions, artifact behavior, secret exposure risk, and release behavior.

### Immutable Action Pinning

Use immutable 40-character commit SHAs for all third-party Actions. Retain readable version comments and define an update/review policy. Mutable tags, branches, and `main` references are not acceptable.

### Permission Model

Default to:

```yaml
permissions:
  contents: read
```

Grant additional permissions only to the specific job that requires them. Ordinary CI must not receive write permissions for contents, packages, releases, attestations, or OIDC identity tokens.

### Dependency Scanning

Cover Python, npm, transitive dependencies, and OSV or an equivalent multi-ecosystem source. Define severity policy, suppression schema, justification, expiry/review, and deterministic behavior when a scanner is unavailable.

### Secret Scanning

Use a bounded repository scan. Logs may contain only a fingerprint, path, and rule identifier, never a secret value. Every credible finding is a blocker until resolved or explicitly classified through the approved false-positive process.

### SBOM

Generate separate Backend and Frontend CycloneDX 1.6 JSON SBOMs with component versions, hashes where available, and dependency relationships. Validate schemas reproducibly and exclude forbidden runtime/private artifacts.

### Provenance and Attestation

Limit release provenance generation/publication to exact-tag or explicit manual workflows. Bind commit, tag, workflow identity, validated SBOMs, and eligible artifacts. Ordinary main pushes must not publish release provenance. P3-005 does not create a tag or Release.

### Branch Protection Guidance

Document recommended required checks and review controls. Do not call GitHub APIs to change branch-protection settings.

### Compatibility

Preserve the Backend pytest job, Frontend build job, normal main-push Docker skip, tag/manual Docker behavior, product runtime dependencies, fake-provider defaults, and legacy plus `/v1.1` APIs.

## Acceptance Criteria

### PASS

- `third_party_action_full_sha_pin_rate = 1.0`
- `workflow_permissions_explicit_rate = 1.0`
- `credible_secret_findings = 0`
- `approved_dependency_gate = PASS`
- CycloneDX 1.6 schema validation: PASS
- SBOM forbidden-runtime-artifact count: `0`
- Provenance exact-tag/manual boundary: PASS
- Existing Backend CI: PASS
- Existing Frontend CI: PASS
- Normal main-push Docker compose smoke: SKIPPED
- Product runtime changes: `0`
- Candidate, tag, or Release created: `0`

### CONDITIONAL

Core pinning, permissions, scanning, and compatibility gates pass, but a documented non-critical scanner availability, ecosystem metadata, or attestation-platform limitation remains. The limitation must have an owner, bounded impact, expiry/review date, and no credible secret or high-severity dependency finding.

### BLOCKED

- Any third-party Action remains mutable or workflow permissions remain implicit/excessive.
- A credible secret or an unapproved dependency finding meets the blocking threshold.
- SBOM validation fails or includes a forbidden runtime/private artifact.
- Ordinary main CI can publish release provenance or receives release/write identity permissions.
- Existing Backend, Frontend, Docker-policy, product-runtime, provider-default, legacy, or `/v1.1` behavior regresses.
- Work requires private data, a real Provider, product implementation, candidate assignment, tag, Release, or branch-protection API write.

## Artifact and Secret Policy

Do not commit or publish `.env` files, credentials, API keys, auth headers, private Zotero/user data, Article/corpus exports, PDFs, HTML/images, databases, backups, archives, Graph/RAG data, FAISS or embedding caches, traces, profiles, scanner caches, generated runtime stores, or local absolute paths. Generated security evidence must be bounded, deterministic where applicable, and contain no secret value.

## Git Plan

- Implementation authorization: CONSUMED / CLOSED
- Validation-branch push: GRANTED AND PERFORMED for `validation/p3-005-provenance-666e93f`
- Push to `main`: GRANTED AND PERFORMED for the exact audited three-commit sequence
- Tag: prohibited
- Release: prohibited

Future status-appropriate commit messages to confirm in the execution alignment:

- PASS: `feat: add CI security and release provenance`
- CONDITIONAL: `docs: record conditional CI security hardening`
- BLOCKED: `docs: record CI security blockers`

The default future implementation plan is a local commit only. Push requires separate authorization.

## Stop Conditions

- The execution alignment is missing, incomplete, or unconfirmed.
- Required changes exceed the future confirmed allowlist.
- A workflow requires unjustified write, release, package, attestation, or OIDC permissions.
- A credible secret, forbidden artifact, unknown worktree change, REWORK/FAIL audit, test/build regression, or unresolved critical architecture ambiguity appears.
- Work requires a real Provider, private Zotero/user data, product-runtime change, candidate, tag, Release, or external repository-setting write.

## Next Required Decision

Confirm or revise the P3-006 execution alignment. P3-006 implementation, full-corpus processing, network access, and private Zotero access remain unauthorized.

## Closure Evidence

- Initial implementation/blocker commit: `80e8823e2ba8403f347df762de3107298f6bc4b1`
- Initial remote validation: [`29634670103`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29634670103); seven prerequisite jobs passed and the skipped manual release-evidence job exposed the P3-005.1 workflow defect.
- P3-005.1 fix commit: `666e93f043788e03133c3532e69b9fd2dcfa01ea`
- Local closure commit: `ff19c520ac9650a36c5073665864aa4086160565`
- Final validation branch: `validation/p3-005-provenance-666e93f`
- Final remote validation: [`29635940873`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29635940873); all eight jobs passed on the exact fix commit.
- Main CI: [`29637475061`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29637475061); Backend, Frontend, workflow policy, dependency, secret, and SBOM jobs passed at the exact closure commit, while Docker and release evidence were skipped by normal main-push policy.
- Release dry-run: `would_authorize_publish=false`; `publish_authorized=false`.
- Uploaded workflow artifacts: `0`.
- Candidate, tag, Release, attestation publication, real-provider call, and private-data access: `0`.
- `main` push: PERFORMED under explicit authorization without amend, squash, rebase, merge, or force.
