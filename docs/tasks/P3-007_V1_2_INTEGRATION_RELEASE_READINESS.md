# P3-007 v1.2 Integration and Release Readiness

## Status

CONDITIONAL / RISK ACCEPTED / LOCAL IMPLEMENTATION COMPLETE

IMPLEMENTATION AUTHORIZATION: CONSUMED / CLOSED

PUSH AUTHORIZATION: NOT GRANTED

CANDIDATE AUTHORIZATION: NOT GRANTED

TAG / RELEASE AUTHORIZATION: NOT GRANTED

## Task Identity

P3-007 v1.2 Integration and Release Readiness

## Authoritative Baseline

- Formal version: `v1.1.0`
- Candidate version: Not assigned
- Baseline commit:
  `d6f6f3eefdf5d54bae93727647cab51a4236a3fb`
- Baseline main CI:
  [`30337284957`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30337284957),
  PASS
- Approved scope: Scope Decision A
- Acceptance contract: `docs/V1_2_ACCEPTANCE.md`
- Execution contract: `docs/V1_2_EXECUTION_PLAN.md`
- Risk decision:
  `docs/ADR/0009-p3-007-review-risk-and-zotero-pdf-policy.md`

## Entry Gate Decision

P3-003, P3-004, and P3-005 are PASS / CLOSED. P3-006 completed every
machine-verifiable extraction, integrity, idempotency, recovery, and matching
gate but remained conditional because its formal 64-case human review was not
completed.

On 2026-07-28, the product owner:

- confirmed that the three Zotero pilot cases were reviewed and approved;
- accepted the risk of skipping the remaining 61 cases;
- required browser-printed PDF, not HTML, as the Zotero full-text attachment
  format; and
- authorized P3-007 to proceed under a documented exception.

This decision does not claim 64/64 review completion or measured precision
>=0.95. P3-006 remains `CONDITIONAL / RISK ACCEPTED`, and P3-007 can finish no
higher than `CONDITIONAL / RISK ACCEPTED`.

## Goals

1. Finish additive `/v1.2` reference APIs and UI states.
2. Preserve every legacy and `/v1.1` API and M3-M7 contract.
3. Integrate Reference Store Tier 2 and review-decision Tier 1 operations.
4. Revalidate fake/dry-run provider safety without a real request.
5. Run Backend, Frontend, Docker, scanner, SBOM, provenance, documentation,
   artifact, and secret gates.
6. Audit migration, rollback, corruption recovery, and idempotency for every
   new persisted format.
7. Produce a release-readiness recommendation without assigning a candidate.

## In Scope

- Persist the confirmed risk-acceptance alignment and ADR 0009.
- Implement a bounded read-only Reference Store reader.
- Implement the five planned additive `/v1.2` reference endpoints.
- Add Article Detail Structured References states.
- Add Zotero candidate matched/ambiguous/unmatched states without writes.
- Classify Reference Store as Tier 2 and review decisions as Tier 1 in local
  operations.
- Add focused tests, execute full gates, and publish local report/state
  evidence.

## Out of Scope

- Completing or fabricating the remaining 61 human-review decisions.
- Claiming the original precision threshold was measured.
- Reading or writing a private Zotero library in this task.
- Creating HTML full-text Zotero attachments.
- M1, Article Store payload/schema, Reference Store payload/schema, legacy API,
  `/v1.1`, Graph storage, or provider-default changes.
- Real Provider, paid request, source-site access, full-corpus build/rebuild.
- Candidate assignment, push, tag, Release, or attestation publication.

## Allowed Changes

- additive reference-owned Backend API/service modules;
- focused Backend tests and compact fixtures;
- additive Reader/Zotero Frontend reference views, clients, and tests;
- operations inventory/backup/restore/cleanup/health code and tests required
  by Tier 1/Tier 2 contracts;
- P3-007 governance, report, and configuration documentation.

Frozen M1 modules, Article source storage, legacy APIs, `/v1.1` APIs, Graph
storage, provider defaults, and existing persistence defaults remain excluded.

## Deliverables

- `alignment.md`
- this canonical task
- ADR 0009
- revised acceptance and execution contracts
- additive Backend API/service and tests
- additive Frontend reference UI/client and tests
- operations integration and tests
- `docs/P3_007_V1_2_RELEASE_READINESS_REPORT.md`
- updated `docs/tasks/CURRENT_TASK.md`
- updated `docs/00_PROJECT_STATE.md`
- updated `docs/V1_2_ROADMAP.md`
- one local status-appropriate commit
- no push

## Acceptance

### CONDITIONAL / RISK ACCEPTED

- The review waiver remains explicit: 3 reviewed, 61 waived, no fabricated
  precision.
- All P3-007 implementation, compatibility, data, security, Docker,
  SBOM/provenance, artifact, and secret gates pass.
- The candidate recommendation records the accepted review limitation.
- Candidate assignment remains separately authorized.

### BLOCKED

- A frozen contract changes.
- A required test/security/data gate fails.
- Reference API/UI serves missing, stale, corrupt, unbounded, unsafe, or
  private data as valid.
- Zotero full text regresses to HTML as the accepted final format.
- Release evidence is mismatched.
- A runtime/private artifact or secret is exposed.

## Git Plan

Successful local commit:

```text
feat: complete P3-007 integration with accepted review risk
```

Blocked local commit:

```text
docs: record P3-007 integration blocker
```

Push is not authorized.

## Stop Conditions

- A frozen contract must change.
- Unknown worktree drift or conflict appears.
- A mandatory test/build/security/data gate fails and cannot be fixed within
  this task.
- Network, real Provider, paid, private Zotero, source-site, or full-corpus
  access becomes necessary.
- Candidate, push, tag, Release, attestation, artifact, or secret boundaries
  would be crossed.

## Post-Task Rule

Any future change to the accepted review scope or Zotero PDF-only policy
requires a new confirmed revision task or candidate decision. It may not be
silently rewritten as stronger evidence.

## Execution Evidence

- Additive `/v1.2` Reference API and Reader/Zotero UI: complete.
- Tier 1/Tier 2 operations integration: complete.
- Backend: 573 passed, 3 skipped.
- Frontend focused suites and production build: PASS.
- Browser runtime and all available local security/release gates: PASS.
- Local Docker: unavailable; current-change GitHub Actions require a separately
  authorized push.
- Final status: `CONDITIONAL / RISK ACCEPTED`.
- Candidate, push, tag, Release, and attestation publication: not performed.
