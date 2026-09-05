# P3-029 Reader Learning Mutation Integrity Alignment

Canonical task:
`docs/tasks/P3-029_READER_LEARNING_MUTATION_INTEGRITY.md`

Status: **PASS / CLOSED**

BOUNDED READER FRONTEND, PURE TESTS, PRODUCT E2E, GOVERNANCE DOCUMENTATION,
ISOLATED LOCAL FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE PUSH TO `main`,
AND EXACT-SHA CI READBACK: **CONSUMED / CLOSED**

BACKEND, FROZEN M1, SOURCE OR ARTICLE RECORDS, DERIVED ASSETS, GRAPH/TUTOR DATA,
PERSISTENCE OR PUBLISHED API CONTRACTS, DEPENDENCIES, LOCKFILES, WORKFLOWS,
CANDIDATE, TAG, RELEASE, AND ATTESTATION CHANGES: **NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Prevent duplicate and stale Reader bookmark/note effects, keep persistence and
rendered state consistent, and provide local accessible mutation feedback.

## Binding Scope

- Bind mutations to Article ID, Reader generation, operation ID, and kind.
- Permit one in-flight bookmark operation and one in-flight Notes operation.
- Merge note results by `note_id` with functional state transitions.
- Preserve drafts and rendered records when results fail or are unconfirmed.
- Keep feedback beside the owning Bookmark or Notes controls.
- Preserve all Backend, API, persistence, Graph, Tutor, Session, and release
  contracts.
- Defer Shell route-focus continuity to P3-030.

## Allowed Changes

- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/lib/readerLearningMutations.ts`
- `frontend/tests/readerLearningMutations.test.ts`
- `frontend/scripts/test-articles.sh`
- `scripts/e2e/run_product_e2e.py`
- P3-029 task/status/roadmap/README/alignment/report documentation

## Acceptance

- Rapid repeated activation emits one mutation and one persisted/rendered note.
- Article A callbacks cannot alter Article B state, feedback, draft, or focus.
- Note responses merge by identity; failures retain current UI and draft data.
- Bookmark and Notes controls expose truthful local pending/success/error state.
- Focused/full tests, build, three Product E2E runs, safety gates, and two final
  reviews pass.
- Implementation and docs-only closure commits each pass exact-SHA main CI.

## Authorization Basis

The product owner explicitly directed the agent to stop repeated plan
confirmations, use independent sub-agent review, and automatically execute
approved in-scope work. Independent audits identified both mutation integrity
and route-focus issues; a deterministic local fake-runtime reproduction proved
the mutation defect writes two records while rendering one, so data integrity
is prioritized as P3-029. This authorization does not extend beyond the exact
scope above.

## Stop Conditions

Stop rather than widen scope if correct behavior requires Backend, API,
persistence, dependency, workflow, external/private, Provider, or release
changes, or if an unknown worktree change, forbidden artifact, unrepairable
gate, or exact-SHA CI failure appears.

No v1.2 candidate is assigned.

## Closure Evidence

- implementation commit:
  `7b4ac74cd0d4b2e7ce708511387a78eb5f61b7b7`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33935734608`
- Frontend build, Backend pytest, Product E2E, dependency audit, secret audit,
  workflow/suppression policy, and SBOM validation: PASS
- normal-main Docker compose smoke and release evidence: skipped as designed
- uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI is required before
  final reporting
- next bounded candidate: P3-030 Shell Modal-Origin Route Focus Continuity
