# P3-007 v1.2 Integration and Release Readiness Alignment

Canonical task:
`docs/tasks/P3-007_V1_2_INTEGRATION_RELEASE_READINESS.md`

Status: **CONDITIONAL / RISK ACCEPTED / LOCAL IMPLEMENTATION COMPLETE**

IMPLEMENTATION AUTHORIZATION: **CONSUMED / CLOSED**

PUSH AUTHORIZATION: **NOT GRANTED**

CANDIDATE / TAG / RELEASE AUTHORIZATION: **NOT GRANTED**

## 1. Background

- Formal version remains `v1.1.0`; no v1.2 candidate is assigned.
- Baseline commit
  `d6f6f3eefdf5d54bae93727647cab51a4236a3fb` passed main CI run
  `30337284957`.
- P3-003, P3-004, and P3-005 are PASS / CLOSED.
- P3-006 machine-verifiable extraction, store, and matching gates passed, but
  its formal 64-case real-human review was not completed.
- The user reviewed and approved the three Zotero pilot cases on 2026-07-28
  and explicitly accepted the risk of skipping the remaining 61 cases.
- The three reviewed cases are evidence of a bounded usability decision, not
  evidence that 64/64 cases or precision >=0.95 were achieved.
- P3-006.3 proved that Scientific Spaces full-text Zotero attachments must be
  browser-printed PDFs. HTML snapshots are not an accepted final attachment
  representation.

## 2. Requirements

1. Record the explicit review-scope waiver and risk acceptance without
   fabricating a reviewer count or statistical precision.
2. Keep P3-006 transparent as `CONDITIONAL / RISK ACCEPTED`.
3. Freeze browser-printed PDF as the Scientific Spaces Zotero full-text
   attachment representation; final live HTML snapshot children are
   prohibited.
4. Permit P3-007 to proceed through the documented release-board exception.
5. Finish additive `/v1.2` reference APIs and Reader/Zotero UI states.
6. Integrate the Reference Store as Tier 2 and review decisions as Tier 1 in
   inventory, backup, restore, health, and cleanup safety.
7. Preserve legacy, `/v1.1`, M1, and M3-M7 contracts and safe defaults.
8. Run Backend, Frontend, Docker, compatibility, security, SBOM/provenance,
   documentation, artifact, secret, and Git gates.
9. Produce an evidence-based P3-007 report and local status-appropriate
   commit. Do not push.

## 3. Purpose

Complete v1.2 product integration and release-readiness evidence without
weakening frozen contracts or misrepresenting the incomplete human-review
sample. The highest successful result for this task is
`CONDITIONAL / RISK ACCEPTED`; candidate assignment remains a separate user
decision.

## 4. Planned Execution

1. Verify governance, Git state, REWORK/audit, current contracts, and existing
   uncommitted P3-007 evidence.
2. Persist this alignment, the canonical task, ADR 0009, and the explicit
   acceptance/execution exception.
3. Implement a validated, bounded, read-only Reference Store adapter and
   additive `/v1.2` endpoints.
4. Add Structured References to Article Detail and read-only candidate states
   to the Zotero view.
5. Add Reference Store Tier 2 and review-decision Tier 1 operations coverage.
6. Add focused Backend and Frontend regression tests.
7. Run all mandatory release-readiness gates without real Provider, private
   Zotero, source-site, paid, or full-corpus operations.
8. Update the report, project state, roadmap, and current task.
9. Create one local status-appropriate commit without push.

## 5. Selection Rationale

An explicit risk-acceptance exception lets the approved integration proceed
while preserving the distinction between three reviewed cases and the
uncompleted 64-case statistical gate. It is more honest than declaring the
original gate passed and more useful than keeping all integration blocked
after the product owner accepted the bounded risk.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Accept the bounded review risk and continue P3-007 | Selected |
| Complete all 64 human-review cases before P3-007 | Valid but explicitly waived |
| Treat three cases as 64/64 and precision >=0.95 | Rejected as false evidence |
| Keep P3-007 blocked despite explicit risk acceptance | Rejected |

## 7. Deliverables

- `alignment.md`
- `docs/tasks/P3-007_V1_2_INTEGRATION_RELEASE_READINESS.md`
- `docs/ADR/0009-p3-007-review-risk-and-zotero-pdf-policy.md`
- revised `docs/V1_2_ACCEPTANCE.md`
- revised `docs/V1_2_EXECUTION_PLAN.md`
- additive v1.2 Backend API/service code and tests
- additive Frontend reference UI/client code and tests
- required operations integration and tests
- `docs/P3_007_V1_2_RELEASE_READINESS_REPORT.md`
- updated `docs/tasks/CURRENT_TASK.md`
- updated `docs/00_PROJECT_STATE.md`
- updated `docs/V1_2_ROADMAP.md`
- one local status-appropriate commit
- no push

## 8. Acceptance Criteria

- Governance records exactly 3 reviewed/approved cases and 61 waived cases.
- No document claims 64/64 completion or measured precision >=0.95.
- Scientific Spaces Zotero full-text policy requires browser-printed PDF and
  rejects HTML as the final live attachment format.
- All five planned `/v1.2` endpoints are implemented, bounded, read-only, and
  fail closed for missing, stale, or corrupt stores.
- UI covers loading, empty, error, stale, ambiguity, pagination, and safe-link
  states without writing Zotero or review decisions.
- Reference Store is Tier 2; review decisions are Tier 1, backup-protected,
  restore-verified, health-checked, and cleanup-protected.
- Full Backend tests and focused compatibility tests pass.
- Frontend reference tests and production build pass.
- Docker smoke and security/SBOM/provenance dry-run gates pass when the local
  environment supports them.
- No M1, Article Store, Reference Store payload, legacy API, `/v1.1`, provider
  default, or M3-M7 contract changes.
- No real Provider, paid request, source access, private Zotero read/write, or
  full-corpus operation occurs.
- Artifact and secret audits are clean.
- Final successful status is `CONDITIONAL / RISK ACCEPTED`; no candidate,
  push, tag, Release, or attestation publication occurs.

## Risk Decision

- Owner: repository product owner.
- Accepted limitation: 61 of the formal 64 review cases remain unreviewed.
- Evidence retained: three user-approved Zotero pilot cases; machine gates
  remain unchanged.
- Remediation option: complete P3-006.1 if stronger statistical evidence is
  later required.
- Decision gate: any future candidate task must carry this accepted risk
  explicitly; it must not silently convert it into measured precision.

## Execution Result

- Additive `/v1.2` Reference API, Reader/Zotero UI, and Tier 1/Tier 2
  operations integration are complete.
- Backend: 573 passed, 3 skipped.
- Frontend focused suites and production build: PASS.
- Browser runtime, security, dependency, secret, SBOM, fake-provider, and
  no-publish release-evidence gates: PASS.
- Local Docker: not run because `docker` is unavailable.
- No push occurred, so current-change GitHub Actions remain for a separately
  aligned synchronization task.
- Final status: `CONDITIONAL / RISK ACCEPTED`; no candidate was assigned.
