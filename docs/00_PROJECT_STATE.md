# Project State

This is the single current status summary. Detailed requirements and run receipts
belong to the linked canonical tasks and reports.

| Area | Current state | Evidence |
| --- | --- | --- |
| Formal release | v1.1.0; no v1.2 release candidate assigned | [Release evidence](RELEASE_CI_EVIDENCE_v1.1.0.md) |
| P3-044 Tutor modes | LOCAL COMPLETE / OFFLINE VERIFIED | [Canonical task](tasks/P3-044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION.md), [implementation report](P3_044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION_REPORT.md) |
| Affine v3 reference content | Owner approved all 12/12 cases and both Articles in this conversation | [Human decision](reviews/P3_044_AFFINE_V3_HUMAN_DECISION.json), [review packet](../backend/tests/fixtures/evaluation/tutor_generation/review_candidate_v3/review_package.md) |
| Real-model answer quality | NOT_RUN; reference approval does not approve model answers | [Review preparation report](P3_044_AFFINE_REVIEW_PREPARATION_REPORT.md) |
| Reader P3-042 | OPEN / CI BLOCKED; historical cause UNKNOWN | [Canonical task](tasks/P3-042_ARTICLE_LIST_ROUTE_STATE_CONTINUITY.md), [report](P3_042_ARTICLE_LIST_ROUTE_STATE_CONTINUITY_REPORT.md) |
| Graph P3-039 | OPEN / DEFERRED; historical cause UNKNOWN | [Canonical task](tasks/P3-039_GRAPH_NODE_RENDERING_RELIABILITY.md), [report](P3_039_GRAPH_NODE_RENDERING_RELIABILITY_REPORT.md) |

The approved reference candidate is `p3-044-affine-review/v3`, bound to digest
`52656b4933d23dd1aa20c575a77c5ab318116720e60e995661264e51fd69295e`.
Its frozen manifest retains preparation-time PENDING. The separate human decision
records the subsequent approval; changing the reviewed content invalidates that
binding. The Articles and cases are development/regression materials, not an unseen holdout.

P3-043 has separate local Reader implementation and focused evidence. Final
acceptance is incomplete: the old report's running E2E has no current runner or
terminal receipt. This synchronization records that progress without integrating
the Reader code or claiming the process remains active.

## Verification Scope

| Evidence | Recorded result | Scope |
| --- | --- | --- |
| Previous affine review preparation focused suite | 202 passed | Historical local run; [preparation report](P3_044_AFFINE_REVIEW_PREPARATION_REPORT.md) |
| Synchronization validation, 2026-09-10 | 202 passed (109 generation/review + 93 compatibility tests); v3 digest unchanged; secret audit 0 findings | Local pre-publication checks, not remote CI |
| Previous P3-044 full backend run | 1244 passed, 4 skipped | Historical implementation verification |
| Previous P3-044 Product E2E | Original 3 × 298 checks plus restart and additive profiles passed | Historical task-owned loopback run; [implementation report](P3_044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION_REPORT.md) |
| GitHub synchronization | Reviewed P3-044 implementation, approved reference decision and concise progress/planning documents | Remote checks belong to the publishing commit in [GitHub Actions](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/workflows/ci.yml) |

No earlier test result proves this synchronization's CI passed. A skipped or
unrun gate remains distinct from PASS. Passing Tutor or new CI checks do not
close the independent Reader/Graph incidents.

## Product and Data Boundaries

M1 acquisition is frozen; Reader, RAG, Learning, Zotero metadata links, Graph and
Tutor capabilities are documented in the [README](../README.md). Article schema,
legacy/`/v1.1`/`/v1.2` contracts, source-selection rules, fake defaults and
backup/restore boundaries remain protected.

GitHub synchronization covers reviewed code, self-authored synthetic fixtures,
necessary documentation and redundant-document cleanup. Private Zotero, paid or
real model calls, source scraping, private runtime data, tags and Releases are
outside the current action. The original workspace's uncommitted Reader work
and local services remain preserved; no claim is made that both workspaces are clean.

Historical reference-review risk acceptance remains separate: P3-006 approved
three pilot cases and waived 61, with no precision claim.
[ADR 0009](ADR/0009-p3-007-review-risk-and-zotero-pdf-policy.md) and the
[P3-006 report](P3_006_STRUCTURED_REFERENCE_FULL_CORPUS_REPORT.md) retain that decision.

Redundancy cleanup removed repeated entry-document history and the superseded
v1.1.0 release draft. Three obsolete validation branches had zero commits outside
main and were deleted; one old npm cache matched no active branch's lockfile and
was removed. Formal releases, unique task evidence and active dependency PRs remain.

## Next Work

The next proposed task is controlled-response, claim-level offline regression
using the approved v3 reference content. It is recorded for planning, not implemented.
Further priorities and deferred architecture requirements are in the
[v1.2 roadmap](V1_2_ROADMAP.md). Task receipts remain in [canonical tasks](tasks/)
and their linked reports; this entry does not duplicate their history.
