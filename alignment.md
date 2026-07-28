# P3-006 Conditional Closure After Dependency Audit Repair

Canonical current task:
`docs/tasks/P3-006_STRUCTURED_REFERENCE_FULL_CORPUS.md`

Repair evidence:
`docs/tasks/P3-006_CI_001_DEPENDENCY_AUDIT_REPAIR.md`

## 1. Background

- P3-006 remains `CONDITIONAL / CLOSED`.
- Its exact 1,311-Article offline build and all machine gates passed.
- Sixty-four deterministic human-review cases remain pending with zero real
  reviewers; no review result is fabricated.
- Completion commit `f2496cafa4a54440b19e4491294277b70a1f07cf`
  reached main, where CI run `30320834573` exposed 11 newly published runtime
  npm vulnerability findings.
- The separately authorized P3-006-CI-001 task repaired only those findings.
- Repair commit `9b0080cbe5c6483de2534ed63f9eeb5c5e5b1dbd`
  passed validation run `30322598783` and main CI run `30322723458`.
- No suppression, policy weakening, corpus rebuild, Reference Store mutation,
  product change, Provider/source access, private Zotero access, candidate,
  tag, Release, or attestation occurred.

## 2. Requirements

1. Preserve P3-006 as `CONDITIONAL / CLOSED`.
2. Preserve the exact Article and Reference Store identities and all frozen
   reference semantics.
3. Record P3-006-CI-001 as `PASS / CLOSED`.
4. Keep dependency suppression count at zero and the dependency policy and
   scanner set unchanged.
5. Restore `CURRENT_TASK.md` to the P3-006 canonical task.
6. Keep P3-006.1 uncreated and its implementation and real-review
   authorization not granted.
7. Require separate complete alignment and confirmation before P3-006.1.
8. Keep P3-007, candidate, tag, Release, and attestation unstaged.

## 3. Purpose

Close the finite dependency-audit incident without changing the scientific
corpus or reference product, and return governance to the truthful P3-006
conditional state so a separate human-review task can be considered.

## 4. Completed Execution

1. Audited original run `30320834573` and job `90156179263`.
2. Classified the root cause as `B. REAL_DEPENDENCY_VULNERABILITY`.
3. Verified all 11 advisories with GitHub Advisory Database and OSV.
4. Updated only `next`, `postcss`, and the required Sharp transitive closure.
5. Proved two byte-identical dependency-audit PASS results with zero findings
   and zero suppressions.
6. Passed security tests, workflow policy, suppression validation, secret
   audit, SBOM, Backend, frontend clean install/build, Sharp runtime, and Next
   image-optimizer compatibility.
7. Revalidated Article Store SHA, corpus fingerprint, and Reference Store
   build fingerprint unchanged.
8. Passed validation-branch CI including Docker and no-publish release
   evidence with zero workflow artifacts.
9. Passed repair main CI with zero workflow artifacts.
10. Prepared this docs-only closure for its required main CI.

## 5. Selection Rationale

The minimum official patch/minor versions remove actual vulnerabilities while
retaining fail-closed security policy and scanner diversity. A dedicated
validation branch proved the dependency tree and complete workflow before the
repair reached main.

## 6. Alternatives

| Option | Result |
| --- | --- |
| Rerun the failed job | Rejected because findings were real, not transient |
| Add suppressions | Prohibited and unnecessary |
| Weaken policy or remove scanners | Prohibited |
| Broad or major dependency upgrade | Rejected as unnecessary |
| Minimum fixed versions plus full validation | Selected and passed |

## 7. Deliverables

- P3-006-CI-001 canonical repair record
- Minimum dependency and lockfile repair
- Local security, compatibility, immutable-store, and artifact evidence
- Validation run `30322598783`
- Repair main CI run `30322723458`
- Updated P3-006 report, project state, roadmap, current-task pointer, and this
  closure alignment
- Docs-only closure commit and required final main CI

## 8. Acceptance Criteria

Closure is complete only when:

- the docs-only closure commit main CI passes with zero artifacts;
- P3-006 remains `CONDITIONAL / CLOSED`;
- P3-006-CI-001 is `PASS / CLOSED`;
- P3-006.1 is not staged and no real review is executed;
- Article/Reference Store identities remain unchanged;
- suppression count remains zero and policy/scanners remain unchanged;
- worktree and index are clean and main is synchronized;
- no candidate, tag, Release, attestation, source/Provider/private-Zotero
  access, or runtime/private artifact is created.

The next required action is:

`Prepare and confirm the separate P3-006.1 Human Review Completion task.`
