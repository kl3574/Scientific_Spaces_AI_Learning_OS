# P3-006.1 Human Review Completion

## Status

ALIGNMENT REQUIRED

IMPLEMENTATION AUTHORIZATION: NOT GRANTED

HUMAN REVIEW PACKET ACCESS AUTHORIZATION: NOT GRANTED

HUMAN REVIEW WORKSHEET CREATION AUTHORIZATION: NOT GRANTED

COMPLETED REVIEW DECISION ACCESS AUTHORIZATION: NOT GRANTED

REAL HUMAN REVIEW EXECUTION AUTHORIZATION: NOT GRANTED

PRIVATE ZOTERO AUTHORIZATION: NOT GRANTED

NETWORK AUTHORIZATION: NOT GRANTED

## Task Identity

P3-006.1 Human Review Completion

## Version State

- Formal version: `v1.1.0`
- Candidate version: Not assigned

## Previous Task

P3-006 Structured Reference Full-Corpus Build and Zotero Matching:
`CONDITIONAL / CLOSED`

## Related Repair

P3-006-CI-001 Dependency Audit Repair: `PASS / CLOSED`

## Authoritative Baseline

- P3-006 completion commit:
  `f2496cafa4a54440b19e4491294277b70a1f07cf`
- P3-006-CI-001 repair commit:
  `9b0080cbe5c6483de2534ed63f9eeb5c5e5b1dbd`
- P3-006-CI-001 closure commit:
  `df521b9e9d5a39c82f843c4708c4b337f4f48f3e`
- P3-006-CI-001 closure CI:
  [`30322970832`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30322970832),
  PASS with zero artifacts
- Applicable ADR: `docs/ADR/0006-derived-reference-store.md`
- Applicable evaluation contract: `docs/V1_2_EVALUATION_PLAN.md`
- Applicable acceptance contract: `docs/V1_2_ACCEPTANCE.md`

## Background

P3-006 completed every machine-verifiable full-corpus gate while preserving
the frozen Article source and derived Reference Store boundaries.

Exact corpus and store identity:

| Evidence | Value |
| --- | --- |
| Article count | 1311 |
| Candidate accounting | 24514 / 24514 |
| Reference records | 12859 |
| Article Store SHA-256 | `3b91f22db548373a6c91bb11a5188fb3e388ab9e19c4429e8e8fac918609a505` |
| Corpus fingerprint | `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d` |
| Reference Store build fingerprint | `70ab191621aa8819f3c195c116aec5b5ae05f44c0b90fb0d11e6cb4365d5d846` |

The following machine gates passed:

- complete Article and candidate accounting;
- silent drops: `0`;
- provenance completeness: `1.0`;
- deterministic ID rate: `1.0`;
- duplicate consistency: `1.0`;
- Article mutations: `0`;
- network requests: `0`;
- atomic install and rollback/recovery;
- checkpoint/resume;
- stale and corruption detection;
- unchanged-input no-op reuse;
- clean rebuild determinism;
- resource budgets;
- Backend and Frontend regression gates;
- artifact and secret audits.

A deterministic 64-case human-review packet exists, but no real human review
result has been completed. Automated expectations and model judgments cannot
be counted as human correctness evidence. P3-006 therefore remains
`CONDITIONAL / CLOSED`.

## Goals

1. Verify the identity and completeness of the existing 64-case review
   packet.
2. Bind the packet to the exact corpus and Reference Store build fingerprint.
3. Generate or validate an independent human-review worksheet.
4. Separate immutable evidence fields from human-entered judgment fields.
5. Require at least one real natural-person reviewer.
6. Avoid collecting names, email addresses, or unnecessary personal data.
7. Permit pseudonymous reviewer IDs.
8. Reject Codex, ChatGPT, any LLM, script, fixture expectation, or automated
   rule as a real reviewer.
9. Validate every reviewed row completely and fail closed on invalid rows.
10. Compute strong-identifier precision from valid completed review rows.
11. Detect any false exact Zotero match.
12. Preserve and classify uncertainty, follow-up needs, and reviewer
    disagreement.
13. Commit only aggregate metrics and irreversible fingerprints.
14. Upgrade P3-006 from `CONDITIONAL / CLOSED` to `PASS / CLOSED` only when
    every PASS gate is met.
15. Keep P3-006 conditional or mark the review task BLOCKED when evidence does
    not meet the gate; never fabricate PASS.

## Non-Goals

- No full-corpus extraction or processing rerun.
- No Reference Store generation, replacement, mutation, or migration.
- No Article Store or `Article.content` modification.
- No change to reference extraction, normalization, IDs, deduplication, or
  provenance.
- No change to review-case selection.
- No private Zotero read, export, or write.
- No source-site, Provider, paid-service, or other network access.
- No validation of scientific conclusions themselves.
- No claim that syntactic extraction correctness proves scientific
  correctness.
- No product code, test, API, dependency, lockfile, workflow, or frozen
  contract change.
- No P3-007 staging.
- No candidate, tag, Release, or attestation.

## Current Authorized Action

Only persist this canonical task, update approved governance pointers, create
and push one docs-only staging commit, validate its exact-SHA main CI, and
present the complete future execution alignment for confirmation.

The current staging task must not read or create the review packet,
worksheet, or completed decisions and must not calculate human-review
metrics.

## Future Runtime Boundary

A separately confirmed Stage A may use only:

```text
.local_data/scientific_spaces/references/full-corpus/reviews/p3-006-1/
```

Planned files:

```text
review_manifest.json
review_cases.jsonl
human_review.csv
HUMAN_REVIEW_INSTRUCTIONS.md
review_validation.json
```

The future execution alignment must reconfirm exact paths before access. The
current staging task creates and reads none of these files.

Every runtime review file must:

- remain Git ignored;
- never be committed or uploaded to CI;
- contain no complete Article body;
- contain no private Zotero metadata;
- contain no local absolute path, credential, or secret.

## Real Human Reviewer Definition

A real human reviewer is a natural person who personally inspects the bounded
review evidence and enters their own judgments.

The following are not real human reviewers and cannot provide human
correctness evidence:

- Codex;
- ChatGPT;
- any other LLM;
- automated classification or validation;
- fixture expected values;
- script-generated verdicts;
- copied expected results;
- bulk defaults without personal review.

Pseudonymous IDs such as `reviewer-01` and `reviewer-02` are allowed. Do not
record real names, email addresses, organization accounts, private Zotero
identities, or other unnecessary personal information.

## Immutable Review-Case Fields

The reviewer must not edit:

```text
case_id
stratum
reference_id
evidence_id
article_id
section
reference_type
classification
normalized_identity
duplicate_group
zotero_candidate_decision
strong_identifier
bounded_evidence_excerpt
raw_reference_hash
corpus_fingerprint
reference_store_build_fingerprint
```

Any identity-field change makes the packet stale and must fail closed.

## Human-Entered Fields

The worksheet plans these human-entered fields:

```text
reviewer_id
reviewed_at
extraction_correct
normalized_identity_correct
provenance_sufficient
duplicate_decision_correct
zotero_decision_correct
false_exact_match
review_status
comment
```

Allowed values:

```text
extraction_correct:
yes | no | uncertain

normalized_identity_correct:
yes | no | uncertain

provenance_sufficient:
yes | no | uncertain

duplicate_decision_correct:
yes | no | uncertain

zotero_decision_correct:
yes | no | uncertain

false_exact_match:
yes | no

review_status:
reviewed | needs_followup
```

An empty value is never interpreted as `yes`.

## Two-Stage Future Execution

### Stage A: Worksheet Preparation

Only after separate confirmation, Stage A may:

- read and validate the existing 64-case packet;
- verify corpus and Reference Store fingerprints;
- generate the independent worksheet and bounded instructions;
- report only safe relative paths and validation evidence;
- stop and wait for real human input.

Stage A must not:

- enter or infer a verdict;
- calculate or claim a human-correctness PASS;
- update governance status;
- create a Git commit.

### Stage B: Decision Validation and Closure

Only after a real person has completed the worksheet and the user separately
authorizes Stage B, it may:

- read completed decisions;
- validate reviewer IDs and required fields;
- reject stale, unknown, duplicate, incomplete, or malformed rows;
- compute aggregate metrics;
- preserve uncertain, follow-up, and disagreement evidence;
- update only approved repository reports and governance files;
- create one status-appropriate docs-only local closure commit if gates permit.

Stage B does not authorize push by default.

## Packet Identity Gate

```text
packet_case_count = 64
unique_case_id_count = 64
unknown_case_id_count = 0
stale_case_count = 0
duplicate_case_id_count = 0
corpus_fingerprint_match = true
reference_store_build_fingerprint_match = true
```

## Review Completeness Gate

PASS requires:

```text
reviewed_unique_case_count = 64
real_human_reviewer_count >= 1
duplicate_review_row_count = 0
missing_required_verdict_count = 0
```

Completion of only 60-63 cases cannot produce PASS. A future confirmed
alignment may classify it as CONDITIONAL only when the missing cases do not
show selective bias and every safety/integrity gate remains valid.

## Strong-Identifier Precision

```text
strong_identifier_reviewed =
all reviewed cases where strong_identifier = true
```

```text
strong_identifier_correct =
strong-identifier cases where:

extraction_correct = yes
AND normalized_identity_correct = yes
AND provenance_sufficient = yes
AND duplicate_decision_correct = yes
AND zotero_decision_correct = yes
AND false_exact_match = no
```

Gate:

```text
strong_identifier_reviewed > 0

strong_identifier_precision =
strong_identifier_correct / strong_identifier_reviewed

strong_identifier_precision >= 0.95
```

`uncertain` and `needs_followup` never enter the correct numerator.

## Zotero Safety Gate

```text
false_exact_Zotero_match_count = 0
ambiguous_auto_confirmation_count = 0
automatic_Zotero_write_count = 0
private_Zotero_read_count = 0
```

## Uncertainty and Disagreement

- `uncertain` and `needs_followup` remain explicit and are never coerced to a
  correct verdict.
- Every unresolved critical case blocks PASS.
- A 60-63 case completion or bounded non-critical uncertainty may be
  CONDITIONAL only under a separately confirmed Stage B alignment.
- Multiple-reviewer disagreement is retained per case and reported
  separately; it is never overwritten by majority vote without an approved
  adjudication rule.
- Reports must list affected case IDs without exposing reviewer identity or
  full source content.

## Aggregate-Only Repository Reporting

Repository reports may contain only:

- counts and rates;
- safe case IDs and strata;
- irreversible corpus, store, packet, worksheet, and decision fingerprints;
- aggregate disagreement, uncertainty, and follow-up counts;
- bounded failure classifications;
- status and verification evidence.

Runtime rows, comments, reviewer-level decisions, complete excerpts, personal
information, private Zotero data, local paths, and secrets must remain outside
Git.

## PASS

All of the following are mandatory:

- exact packet identity;
- 64/64 unique reviewed cases;
- at least one real human reviewer;
- strong-identifier precision at least `0.95`;
- false exact Zotero matches: `0`;
- unknown, stale, and duplicate rows: `0`;
- missing required verdicts: `0`;
- critical follow-up cases: `0`;
- private Zotero access and automatic writes: `0`;
- tracked runtime review files: `0`;
- every P3-006 machine gate and source/store identity remains PASS.

## CONDITIONAL

Only a finite, explicit, non-security-critical limitation may be conditional,
including:

- a small number of uncertain cases;
- a small number of `needs_followup` cases;
- reviewer disagreement;
- 60-63 completed cases without evidence of selective bias;
- a quality limitation that does not affect machine gates, store integrity,
  or Article immutability.

The exact case IDs, impact, owner, and next action must be recorded. A
CONDITIONAL result cannot be represented as PASS.

## BLOCKED

BLOCKED takes precedence over CONDITIONAL for:

- fabricated reviewer identity or model verdict presented as human judgment;
- stale packet, unknown case, duplicate case, or changed identity field;
- false exact Zotero match or incorrect strong identity;
- missing provenance or critical unresolved follow-up;
- review data, private data, path, or secret leakage;
- private Zotero access or any Zotero write;
- tracked runtime review artifact;
- changed Article/corpus/Reference Store identity or failed machine gate;
- any required action outside a separately confirmed allowlist.

## Future Verification Plan

Before Stage A, the execution alignment must provide exact commands that:

1. confirm the clean synchronized Git baseline and applicable governance;
2. read only the approved existing packet and exact Reference Store identity;
3. validate packet count, unique IDs, immutable fields, hashes, and
   fingerprints;
4. create only ignored worksheet files under the approved runtime root;
5. run packet/worksheet validators without network or private Zotero access;
6. prove runtime files remain untracked and contain no forbidden data;
7. stop before any human decision is entered or read.

Before Stage B, a new authorization must provide exact commands that:

1. validate completed rows and pseudonymous reviewer IDs;
2. calculate completeness, strong-identifier precision, Zotero safety,
   uncertainty, follow-up, and disagreement metrics;
3. revalidate P3-006 store identity and machine gates without rebuilding;
4. run secret, artifact, changed-path, and Git audits;
5. create only aggregate repository evidence and a status-appropriate local
   docs commit.

No current CLI, packet path, or worksheet schema is assumed executable until
the future alignment verifies it against the live repository.

## Future Git Plan

Stage A:

```text
No Git commit expected.
Runtime worksheet remains ignored.
```

Stage B PASS:

```text
docs: close P3-006 after human review
```

Stage B CONDITIONAL:

```text
docs: record conditional P3-006 human review
```

Stage B BLOCKED:

```text
docs: record P3-006 human-review blockers
```

The default Stage B plan is local commit only. Push requires separate
authorization. Candidate, tag, Release, and attestation remain prohibited.

## Prohibited Current Actions

- Read, modify, regenerate, or replace the review packet.
- Create a review worksheet or instructions.
- Read or validate completed human decisions.
- Generate, copy, or fabricate human verdicts.
- Calculate human-review metrics.
- Run full-corpus processing or mutate the Reference Store.
- Access private Zotero, source sites, Providers, paid services, or other
  network resources.
- Modify product code, tests, APIs, workflows, dependencies, or lockfiles.
- Stage P3-007 or assign a candidate.
- Create or move a tag, Release, or attestation.
- Force push, rebase, amend, or rewrite history.

## Stop Conditions

- The Git or governance baseline differs from the confirmed staging task.
- REWORK or FAIL audit exists.
- A required action falls outside the confirmed allowlist.
- Packet, worksheet, completed-decision, private Zotero, Provider, source-site,
  or paid-service access would be required before separate authorization.
- Runtime/private data, personal information, secret, or local path would
  enter Git or CI.
- A P3-006 machine identity or gate changes.
- Staging commit or exact-SHA main CI fails.
- Candidate, tag, Release, attestation, P3-007 staging, or history rewrite
  would be required.

## Current Staging Completion Criteria

- This canonical task is committed in a docs-only staging commit.
- `CURRENT_TASK.md` points to this file with status `ALIGNMENT REQUIRED`.
- P3-006 remains `CONDITIONAL / CLOSED`.
- P3-006-CI-001 remains `PASS / CLOSED`.
- Every P3-006.1 implementation and review-data permission remains
  `NOT GRANTED`.
- P3-007 remains not staged and no candidate is assigned.
- Exact staging-SHA main CI passes required jobs with zero artifacts.
- Main is synchronized and the worktree, index, and untracked set are clean.
- The complete two-stage execution alignment is presented for confirmation
  and no review execution begins.

## Next Required Decision

Confirm or revise the complete P3-006.1 execution alignment before any review
packet, worksheet, completed decision, metric, implementation, or closure
action.
