# P3-023 Concept Study Set and Learning Launch Alignment

Canonical task:
`docs/tasks/P3-023_CONCEPT_STUDY_SET_AND_LEARNING_LAUNCH.md`

Status: **PASS / CLOSED**

ORDINARY FRONTEND / TEST / DOCUMENTATION WORK, LOCAL ARTICLE AND GRAPH READS,
BROWSER-LOCAL FOCUSED SESSION WRITES, FAKE-PROVIDER LOCAL RUNTIME, TEMPORARY
ISOLATED MUTABLE STATE, LOCAL COMMITS, NON-FORCE PUSH TO `main`, AND EXACT-SHA
CI READBACK: **GRANTED FOR P3-023**

BACKEND / FROZEN M1 / SOURCE RECORD / ARTICLE RECORD / DERIVED ASSET /
DEPENDENCY / LOCKFILE / WORKFLOW / PUBLISHED API CONTRACT MODIFICATION:
**NOT GRANTED**

SOURCE NETWORK / EXTERNAL SEARCH / PRIVATE ZOTERO / REAL OR PAID PROVIDER /
CANDIDATE / TAG / RELEASE / ATTESTATION / DESTRUCTIVE GIT ACTION:
**NOT GRANTED**

## 1. Background

- P3-015 provides a bounded visual Graph and concept provenance.
- P3-017 provides Tutor Explain and Quiz modes with Article selection and an
  optional Graph node key.
- P3-021 provides a browser-local, Article-only Focused Session capped at 20
  unique readable Articles.
- P3-022 is PASS / CLOSED, but selecting a Concept still leaves provenance,
  Tutor, Reader, and Session as disconnected surfaces.
- The Graph does not encode prerequisite order or complete Paper and
  Experiment entities. This task must not imply those unsupported semantics.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `e5fd14d1292cb6142dca26d0bfdc6eb517d109bb`; entry worktree and index are
  clean with ahead / behind `0 / 0`.
- REWORK and `.audit` are absent. No v1.2 candidate is assigned.
- Two independent sub-agent reviews initially identified scope and contract
  gaps. After the task was narrowed as recorded here, both returned PASS.

## 2. Objective

Turn a selected Graph Concept into a bounded, evidence-transparent Concept
Study Set and explicit launch points for reading, Tutor Explain, Tutor Quiz,
and the existing Focused Session without adding a new route, data model,
persistence contract, or Backend capability.

## 3. Product Semantics

1. A Concept Study Set contains only valid readable Articles present in the
   provenance records returned by the existing Graph detail response.
2. Preserve returned source order and deduplicate by Article ID.
3. Report returned records, unique eligible Articles, omitted source records,
   and truncation. Never claim completeness.
4. The display order is deterministic source order, not a pedagogical or
   prerequisite recommendation.
5. Existing related Section, Formula, Article, and Zotero nodes remain in the
   current explorer. Do not relabel them as Paper or Experiment entities.
6. Tutor Explain may receive the Concept node as supplemental Graph context
   plus the first eligible source Article. Tutor Quiz receives the Concept
   topic and first eligible source Article; it is not described as Graph
   grounded. Neither launch auto-submits a Tutor request.

## 4. In Scope

- pure Concept Study Set extraction and presentation model
- safe typed Concept Tutor launch builder/parser, separate from Article-origin
  learning context
- canonical `/graph?node_id=...` return paths
- Graph -> Article -> Graph and Graph -> Tutor -> Graph continuity
- per-Article and one bounded bulk add action using the existing Focused
  Session store
- deterministic bulk outcome counts and one persistence write
- malformed, empty, truncated, full, duplicate, recovered, unavailable, and
  write-failure states
- keyboard, focus, semantic, live-announcement, long-CJK, 200-percent zoom,
  desktop, and 390 px behavior
- focused Frontend tests, isolated Product E2E, local real-data browser probe,
  evidence report, commits, push, and exact-SHA CI closure
- concise repository governance update implementing the user's reviewed-task
  automatic-execution rule

## 5. Out of Scope

- prerequisite inference or pedagogical ordering
- completeness claims about related Articles, papers, formulas, or experiments
- a persistent concept plan, new queue, route, Tutor mode, or persistence model
- Backend, schema, API, Graph builder, derived asset, Article, source, or M1
  changes
- dependency, lockfile, or workflow changes
- source-site access, external search, private Zotero access, or real/paid
  Provider calls
- candidate, tag, Release, attestation, destructive Git, or history rewriting

## 6. Planned Execution

1. Persist this alignment, canonical task, and active status.
2. Add a failing pure-model test for ordered provenance deduplication,
   disclosure counts, safe primary Article selection, and malformed sources.
3. Implement the minimal Concept Study Set model.
4. Add failing tests for typed Explain/Quiz launch URLs and tamper-resistant
   Graph return paths, then implement the URL contract.
5. Add failing tests for one-write bulk Session append, preserved active/order,
   idempotence, and capacity outcomes, then implement the operation.
6. Integrate the Concept Study Set into the existing Graph detail flow and
   prefill Tutor without auto-submission.
7. Add browser assertions for round trips, request envelopes, Session states,
   focus, announcements, mobile, and zoom behavior.
8. Validate representative real local Concepts and Articles with fake
   providers, temporary mutable state, and all non-loopback requests blocked.
9. Run full regression, build, Product E2E, security, artifact, and protected
   path gates.
10. Commit and push implementation, verify exact-SHA CI, then create and push
    a docs-only closure commit and verify its exact-SHA CI.

## 7. Deliverables

- updated `AGENTS.md` reviewed-task execution rule
- updated `alignment.md`
- `docs/tasks/P3-023_CONCEPT_STUDY_SET_AND_LEARNING_LAUNCH.md`
- updated `docs/tasks/CURRENT_TASK.md`
- Concept Study Set and launch implementation under `frontend/src/`
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_023_CONCEPT_STUDY_SET_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- Only a selected Concept exposes the Study Set; other node types retain their
  existing detail and context behavior.
- Eligible Articles are safe, readable, source-ordered, and unique by ID.
- Returned, eligible, omitted, duplicate/invalid, and truncated states are
  represented without a completeness or recommendation claim.
- Explain and Quiz launches carry bounded Concept title, validated node ID,
  optional primary Article, explicit mode, and canonical Graph return path.
- Tutor fields are prefilled but no request occurs before explicit submission.
- Explain uses the Concept node only as supplemental context; Quiz does not
  claim Graph grounding.
- Provenance Article links round-trip to the exact Concept. Section labels are
  not converted into unverified Reader anchors.
- Per-Article and bulk Session adds preserve existing queue order and active
  item, append in source order, enforce the 20-item limit, are idempotent, and
  save once per bulk action.
- Added, already-present, invalid, and capacity-omitted outcomes are announced;
  persistence failure does not navigate or claim success.
- Empty, malformed, truncated, unavailable-storage, full-capacity, Graph
  failure, and Tutor failure states remain controlled and do not expose raw IDs.
- Keyboard access, visible focus, semantic headings/lists, live status/error
  feedback, long CJK titles, 1440 x 900, 390 x 844, and 200-percent zoom pass
  without overlap or horizontal overflow.
- Three consecutive isolated production Product E2E runs pass with fake
  providers, temporary state, zero external requests, and zero unexpected
  console/page errors.
- Backend full tests, focused Frontend tests, production build, workflow,
  suppression, dependency, secret, SBOM, artifact, and protected-path gates
  pass.
- Backend, frozen M1, source records, Article records, derived assets,
  dependencies, lockfiles, workflows, and published APIs remain unchanged.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Confirmed Test Seams

1. Pure Concept Study Set, typed launch URL, and bounded Session mutation
   interfaces.
2. Browser-visible Graph Concept -> Reader/Tutor/Focused Session workflow.

## Stop Conditions

- An unknown worktree change or conflict appears.
- Existing contracts cannot support the accepted workflow without a Backend,
  schema, dependency, Graph-data, or published-interface change.
- Required evidence needs source access, private Zotero, external search, or a
  real/paid Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic repair.
- A candidate, tag, Release, attestation, force push, or history rewrite becomes
  necessary.

## Completion Evidence

- implementation commit:
  `fceadc512c266de2670d5c426dc201b9e580924b`
- implementation exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33834027640`
- Backend: 600 passed / 4 skipped
- focused Frontend: 92 passed; production build: PASS
- Product E2E: 3/3 runs, 63 checks each, zero external requests and zero
  unexpected console/page errors
- final independent implementation reviews: 2 PASS
- security, SBOM, artifact, and protected-path gates: PASS
- evidence report: `docs/P3_023_CONCEPT_STUDY_SET_REPORT.md`
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
- candidate, tag, Release, attestation, source, private Zotero, and real
  Provider actions: not performed
