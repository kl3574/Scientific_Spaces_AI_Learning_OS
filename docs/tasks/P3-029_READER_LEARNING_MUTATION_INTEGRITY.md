# P3-029 Reader Learning Mutation Integrity

## Status

PASS / CLOSED

## Task Identity

Prevent duplicate, stale, or misattributed Reader bookmark and note mutations
without changing the existing learning API or persistence contract.

## Authoritative Baseline

- Starting commit and cached `origin/main`:
  `aab0bc6f4c7a1f17eb1f9ce90e724dfe8d4b4010`
- Starting ahead / behind: `0 / 0`
- Previous task: P3-028 PASS / CLOSED
- Entry worktree, index, and untracked set: clean
- `REWORK.md` and `.audit`: absent
- Formal version: `v1.1.0`; candidate version: not assigned
- The product owner authorized autonomous continuation after independent
  sub-agent review within the existing platform-improvement goal.

## Evidence

- Reader Article loading and completion operations have generation ownership,
  but bookmark and note handlers update state directly after `await`.
- A deterministic local fake-runtime browser probe submitted one note twice
  while both responses were held. The Backend persisted two records while the
  Reader rendered one, proving a data/UI integrity defect.
- Navigating between Articles can invalidate a pending mutation, but existing
  handlers do not bind their completion, error, draft clearing, or focus to the
  originating Article generation.
- Existing Product E2E covers one serial bookmark and note success only; it
  does not cover duplicate submission, stale completion, or local mutation
  failure feedback.

## Goals

1. Allow at most one in-flight bookmark operation and one in-flight Notes
   operation from a Reader surface.
2. Bind every mutation result to its exact Article generation and operation.
3. Merge note responses by `note_id` using functional state updates.
4. Preserve unconfirmed drafts and existing rendered data when an operation
   fails or its result is unknown.
5. Present pending, success, and failure feedback beside the owning Bookmark
   or Notes control with accessible status semantics.
6. Add deterministic pure and browser regression evidence for duplicate and
   stale operations.

## Non-Goals

- Backend, API, learning-store, Article, or persistence-format changes
- Idempotency keys or an exactly-once claim unsupported by the Backend
- A Notes workspace, search, tags, export, or Tutor-result persistence
- Learning completion, Focused Session, Graph, Tutor, AppShell, or route-focus
  changes
- Dependency, lockfile, workflow, candidate, tag, or Release changes
- Source access, private Zotero, real/paid Providers, or non-loopback network

## Mutation Contract

1. A mutation token contains `articleId`, `generation`, `operationId`, and its
   mutation kind.
2. A result may affect Reader state only while its token is still the current
   owner and the Reader still displays that Article generation.
3. Repeated activation while the same control group is pending is a no-op.
4. A create result is inserted or replaced by `note_id`; update and delete use
   functional state transitions and cannot revive stale snapshots.
5. Create failure retains the submitted draft unless the learner has already
   changed it. No failed or unknown create is replayed automatically.
6. Article transition clears Article-scoped edit state and pending UI while
   stale callbacks become inert.
7. Bookmark and Notes feedback is local, atomic, and truthful; errors do not
   appear only in the unrelated Learning State section.

## Allowed Changes

- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/lib/readerLearningMutations.ts`
- `frontend/tests/readerLearningMutations.test.ts`
- `frontend/scripts/test-articles.sh`
- `scripts/e2e/run_product_e2e.py`
- P3-029 canonical, alignment, current-state, roadmap, README, and report files

## Prohibited Actions

- Backend, published API, storage schema, frozen M1, source or Article record,
  derived-asset, Graph, Tutor persistence, or Provider changes
- Dependency, lockfile, framework, workflow, or release metadata changes
- Source access, external search, private Zotero, real/paid Provider, or other
  non-loopback network access
- Candidate, tag, Release, attestation, force push, or history rewrite
- Runtime/private artifacts, credentials, generated corpus, PDFs, HTML dumps,
  screenshots, traces, profiles, caches, or local databases in Git

## Deliverables

- Reader mutation ownership and note merge helpers
- Pending guards and Article-scoped bookmark/note feedback
- Pure regression tests and deterministic Product E2E race/failure coverage
- `docs/P3_029_READER_LEARNING_MUTATION_INTEGRITY_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. Two rapid create activations emit exactly one note POST and persist/render
   exactly one record.
2. Bookmark activation is disabled while pending and cannot issue a duplicate
   add or remove request.
3. Delayed success or failure from Article A cannot alter Article B state,
   feedback, draft, edit controls, or focus.
4. Mutation ownership is checked by Article ID, generation, operation ID, and
   kind before any post-await UI effect.
5. Note create/update results are merged by `note_id`; delete uses current
   state rather than a captured array.
6. Create failure keeps the draft and reports an unconfirmed result locally;
   update/delete failure keeps the prior rendered note.
7. Bookmark and Notes pending/success/error feedback is exposed through
   stable local live regions; controls have explicit accessible names.
8. Existing completion/session behavior and P3-028 Graph-Reader round trips
   remain unchanged.
9. Focused Frontend tests, production build, full Backend regression, three
   Product E2E runs, two independent final reviews, and repository safety gates
   pass with zero external requests or unexpected console/page errors.
10. Implementation and closure commits each pass exact-SHA main CI; final
    `main` is clean and synchronized.

### CONDITIONAL

No conditional closure. Unverified ownership or persistence accounting keeps
the task open.

### BLOCKED

- Duplicate or stale mutation effects remain reproducible.
- Correctness requires a prohibited Backend, API, persistence, dependency,
  workflow, external/private, Provider, or release change.
- A required test, review, security, artifact, or exact-SHA CI gate cannot be
  repaired within the allowed paths.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Persist this bounded task and alignment.
2. Add failing pure tests for operation ownership and note merge behavior.
3. Implement owned mutation helpers and integrate them into Reader controls.
4. Add deterministic browser coverage for duplicate submission, stale result,
   local failure, draft retention, and persistence/UI accounting.
5. Run focused and full local gates; obtain two independent final reviews and
   repair every in-scope Critical or Important finding.
6. Commit and push implementation, verify exact-SHA CI, then create and push a
   docs-only closure commit and verify its exact-SHA CI.

## Verification Commands

- `npm --prefix frontend run test:articles`
- `npm --prefix frontend run build`
- `uv run --project backend --extra dev pytest -q`
- `uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
- repository workflow, suppression, dependency, secret, SBOM, artifact, and
  protected-path gates
- exact-SHA GitHub Actions readback for implementation and closure commits

## Git Plan

- Implementation commit: `fix: preserve Reader learning mutations`
- Push: non-force `main` push after local gates pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-029 Reader mutation integrity`
- Push: non-force `main` push after implementation CI evidence is recorded
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Deferred Candidate

P3-030 should address Shell modal-origin route-focus continuity. Global Search,
mobile Drawer, and Back navigation currently leave focus on `body`; that work
must not be mixed into this data-integrity repair.

## Closure Evidence

- implementation commit:
  `7b4ac74cd0d4b2e7ce708511387a78eb5f61b7b7`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33935734608`
- required implementation jobs: PASS
- normal-main Docker compose smoke and release evidence: skipped as designed
- uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA closure CI is required before
  final reporting
- implementation authorization: CONSUMED / CLOSED

## Stop Conditions

Stop rather than widen scope if an unknown worktree change appears or correct
behavior needs any prohibited Backend, API, persistence, dependency, workflow,
external/private, Provider, or release change.
