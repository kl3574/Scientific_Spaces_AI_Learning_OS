# P3-031 Reader Note Deletion Safety

## Status

PASS / CLOSED

## Task Identity

Prevent an accidental single activation from permanently deleting a saved
Reader note, while preserving P3-029 mutation ownership and truthful handling
of uncertain network results.

## Authoritative Baseline

- Starting commit and cached `origin/main`:
  `4b39dd470dbb8d798ecd71159835f799a2afe164`
- Starting ahead / behind: `0 / 0`
- Previous task: P3-030 PASS / CLOSED
- P3-030 closure exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33949242912`
- Entry worktree, index, and untracked set: clean
- `REWORK.md`, `.audit`, and repository-root `AGENTS.md`: absent
- Formal version: `v1.1.0`; candidate version: not assigned
- Two independent sub-agent scope reviews: PASS after all Important contract
  findings were incorporated
- The product owner directed bounded platform and GUI work to proceed
  automatically after sub-agent review without recurring plan confirmation.

## Evidence

- `ArticleDetailView` currently calls the DELETE client directly from the first
  `Delete` activation.
- The DELETE endpoint permanently removes the note; there is no undo contract.
- An isolated local GUI probe observed one DELETE request on first activation,
  immediate removal, and focus falling to `body` after success.
- P3-029 intentionally treats rejected or lost mutation responses as
  unconfirmed. A client error is not proof that the Backend retained the note.

## Goals

1. Require an explicit inline confirmation before any note DELETE request.
2. Bind the pre-request intent to exact Article, generation, and note identity.
3. Preserve one-operation ownership and prevent duplicate DELETE requests.
4. Keep keyboard focus deterministic across open, cancel, pending, success,
   failure, Article transitions, history navigation, and reload.
5. Communicate permanent deletion and uncertain results truthfully.
6. Keep the interaction usable without horizontal overflow at all required
   desktop, mobile, narrow, and zoom-equivalent viewports.

## Non-Goals

- Undo, trash, soft-delete, note versioning, or Backend recovery
- Bookmark, learning-state, session, Tutor, Graph, Search, or related-paper work
- Backend, API, persistence, Article, source, corpus, or frozen M1 changes
- Dependency, lockfile, workflow, candidate, tag, Release, or attestation changes
- Source access, private Zotero, external search, or real/paid Providers

## Interaction And Ownership Contract

1. The first `Delete` activation creates an immutable
   `{articleId, generation, noteId}` intent and sends zero DELETE requests.
2. The inline confirmation states that deletion is permanent and cannot be
   undone. It is not a modal and does not use `window.confirm`.
3. Opening confirmation focuses `Cancel`, the least-destructive action. `Tab`
   moves to `Delete permanently`; `Shift+Tab` returns to `Cancel`; `Escape`
   cancels only while awaiting confirmation.
4. Awaiting confirmation and delete-in-flight are distinct phases. All note
   create, edit, update, and competing delete launchers are disabled in both
   phases. Repeated Confirm is disabled or a no-op.
5. Cancel sends zero DELETE requests, keeps the note, and restores the exact
   initiating `Delete` button when it still belongs to the active Article
   generation.
6. Confirm sends exactly one DELETE request through the existing client and
   P3-029 operation guard. While pending, confirmation stays mounted and both
   confirmation actions are disabled.
7. Confirmed success removes the rendered note, announces `Note deleted.`, and
   moves focus to the visible Notes status region.
8. A rejected or lost response is unconfirmed: preserve only the rendered
   note, never replay automatically, announce the uncertainty, instruct the
   learner to reload before retrying, and restore the exact Delete control.
9. Article changes, query/history transitions, reload, or a newer generation
   clear any unconfirmed intent without a DELETE. Deferred focus work is
   generation-owned and cannot affect another Article.

## Allowed Changes

- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/lib/readerLearningMutations.ts`
- `frontend/tests/readerLearningMutations.test.ts`
- `scripts/e2e/run_product_e2e.py`
- `docs/tasks/P3-031_READER_NOTE_DELETION_SAFETY.md`
- `alignment.md`
- `docs/tasks/CURRENT_TASK.md`
- `docs/00_PROJECT_STATE.md`
- `README.md`
- `roadmap.md`
- `docs/V1_2_ROADMAP.md`
- `docs/P3_031_READER_NOTE_DELETION_SAFETY_REPORT.md`

## Prohibited Actions

- Backend, API, persistence, storage schema, frozen M1, source/Article records,
  corpus, Graph data, or derived-asset changes
- Dependency, lockfile, framework, workflow, or release metadata changes
- Bookmark, learning-state, session, Tutor, Graph, Search, or related-paper
  implementation changes
- Source access, external search, private Zotero, real/paid Provider, or other
  non-loopback network access
- Candidate, tag, Release, attestation, force push, or history rewrite
- Runtime/private artifacts, credentials, generated corpus, PDFs, HTML dumps,
  screenshots, traces, profiles, caches, or local databases in Git

## Deliverables

- Article/generation/note-owned deletion intent helper
- Inline two-phase permanent-delete confirmation and deterministic focus policy
- Pure intent ownership tests and Product E2E regression coverage
- `docs/P3_031_READER_NOTE_DELETION_SAFETY_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. First mouse, `Enter`, or `Space` activation opens confirmation, sends zero
   DELETE requests, and focuses `Cancel` without transient `body` focus.
2. The confirmation visibly explains permanence and exposes deterministic
   Cancel / Delete permanently keyboard order.
3. Cancel and `Escape` send zero DELETE requests, preserve the rendered and
   persisted note, and restore the exact initiating control.
4. One accepted Confirm creates exactly one DELETE request; repeated activation
   cannot create another request.
5. The pending confirmation remains mounted, all conflicting Notes mutation
   launchers are disabled, and focus remains connected and visible.
6. Success removes the exact note, announces success, and focuses a stable,
   visible Notes status region.
7. Request rejection and post-persistence response loss preserve the current
   rendering, are described as unconfirmed, never auto-replay, and restore a
   generation-owned reload-before-retry control.
8. Article change, Back/Forward, reload, and stale completion clear the old
   intent/focus operation and send no unintended DELETE.
9. The confirmation and focus contract pass at `1440x900`, `390x844`,
   `320x844`, and `720x450` with no horizontal page overflow.
10. Focused Frontend tests, production build, full Backend regression, three
    Product E2E runs, two independent final reviews, and repository safety
    gates pass with zero external requests or unexpected console/page errors.
11. Implementation and closure commits each pass exact-SHA main CI; final
    `main` is clean and synchronized.

### CONDITIONAL

No conditional closure. Any unverified destructive-action, ownership, or focus
contract keeps the task open.

### BLOCKED

- A DELETE can occur before explicit confirmation or more than once per intent.
- Focus can fall to `body`, disconnect, or cross into another Article generation.
- Unconfirmed network results are represented as confirmed persistence state.
- Correctness requires a prohibited Backend, API, persistence, dependency,
  workflow, external/private, Provider, or release change.
- A required test, review, safety, artifact, or exact-SHA CI gate cannot be
  repaired within allowed paths.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Persist the exact bounded task and alignment after independent review.
2. Add failing intent-ownership and browser behavior regression coverage.
3. Implement the two-phase intent, control lock, truthful feedback, and
   generation-owned focus behavior.
4. Run focused and full local gates, then obtain two independent final reviews
   and repair every in-scope Critical or Important finding.
5. Commit and non-force push the implementation, verify exact-SHA CI, create a
   docs-only closure commit, push it, and verify closure exact-SHA CI.

## Verification Commands

- `npm --prefix frontend run test:articles`
- `npm --prefix frontend run test:references`
- `npm --prefix frontend run test:tutor`
- `npm --prefix frontend run test:graph`
- `npm --prefix frontend run build`
- `uv run --project backend --extra dev pytest -q`
- `uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
- repository workflow, suppression, dependency, secret, temporary SBOM,
  artifact, and protected-path gates
- exact-SHA GitHub Actions readback for implementation and closure commits

## Local Verification Evidence

- Focused Frontend: PASS, 113/113
- Frontend production build: PASS, 11 routes
- Backend: PASS, 600 passed / 4 skipped
- Product E2E: PASS, 3/3 complete runs with 177 checks each
- Chromium: 149.0.7827.55
- Restart persistence: PASS
- external requests and unexpected console/page errors: 0
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- workflow, suppression, secret, temporary SBOM, artifact, and protected-path
  gates: PASS
- evidence: `docs/P3_031_READER_NOTE_DELETION_SAFETY_REPORT.md`

The implementation commit passed exact-SHA main CI on unchanged-SHA attempt 2.
This docs-only closure commit requires its own exact-SHA main CI before final
reporting.

## Closure Evidence

- implementation commit:
  `f944d2df79505bcca0f22276b1138d84fe1f161b`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33956965124`
- run attempt: 2
- Frontend build, Backend pytest, three-run Product E2E, dependency audit,
  workflow/suppression policy, secret audit, and SBOM validation: PASS
- normal-main Docker compose smoke and release evidence: skipped as designed
- uploaded artifacts: 0
- attempt 1 failed only at the pre-existing P3-028 Graph-origin Reader saved-
  progress assertion; the unchanged SHA passed attempt 2 and all P3-031
  deletion-safety assertions
- docs-only closure commit: this commit; exact-SHA main CI is required before
  final reporting
- next bounded candidate: none staged

## Git Plan

- Implementation commit: `fix: require confirmation before deleting Reader notes`
- Push: non-force `main` push after local gates pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-031 Reader note deletion safety`
- Push: non-force `main` push after implementation CI evidence is recorded
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Stop Conditions

Stop rather than widen scope if an unknown worktree change appears or correct
behavior needs any prohibited Backend, API, persistence, dependency, workflow,
external/private, Provider, or release change.
