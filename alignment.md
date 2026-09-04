# P3-025 Focused Session Completion and Guided Advance Alignment

Canonical task:
`docs/tasks/P3-025_FOCUSED_SESSION_COMPLETION_AND_GUIDED_ADVANCE.md`

Status: **PASS / CLOSED**

FRONTEND, FOCUSED TESTS, PRODUCT E2E, GOVERNANCE DOCUMENTATION, ISOLATED
LOCAL FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE PUSH TO `main`, AND
EXACT-SHA CI READBACK: **CONSUMED / CLOSED AFTER THE DOCS-ONLY CLOSURE COMMIT**

BACKEND, FROZEN M1, SOURCE OR ARTICLE RECORDS, DERIVED ASSETS, DEPENDENCIES,
LOCKFILES, WORKFLOWS, PUBLISHED API CONTRACTS, CANDIDATE, TAG, RELEASE, AND
ATTESTATION CHANGES: **NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## 1. Background

- P3-021 created a bounded browser-local Focused Session queue. P3-022 exposed
  it on Dashboard, but neither surface understands canonical completion.
- The Reader has server-backed `LearningState`, a separate scroll position,
  and a separate reading timer. These signals currently remain disconnected.
- Repeating `PUT completed` increments `read_count`; repeating timer end rewrites
  its end time. Completion and timer mutations therefore require read-before-
  write and uncertain-response reconciliation.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `a493f55f47d5db1e443e28a13312c48371feb2d8`; ahead / behind is `0 / 0`.
- Entry worktree, index, and untracked set are clean. `REWORK.md` and `.audit`
  are absent. No v1.2 candidate is assigned.
- Two independent scope reviews passed after resolving queue retention, status
  omission, timer uncertainty, and guarded-advance semantics. The user's
  standing instruction authorizes automatic implementation after review.

## 2. Objective

Turn the existing Focused Session into a completion-aware learning workflow:
the learner explicitly completes the current Article, then explicitly opens
the next unfinished Article, while Dashboard and Session show truthful derived
progress and all partial failures remain recoverable.

## 3. Canonical State Contract

1. Article completion is confirmed only by
   `LearningState.status === "completed"`.
2. Reader scroll progress is position only. Timer end is activity only. Neither
   can complete an Article or a Focused Session.
3. The queue schema, order, items, and manual controls remain unchanged.
   Completed items are retained for review.
4. A nonempty Focused Session is complete only when every queued Article has a
   confirmed completed state. An empty queue is not complete.
5. A successful learning-state list that omits a queued Article means canonical
   `unread`. A failed or unavailable list means unknown; unknown never proves a
   terminal session.
6. Guided advance scans strictly after the current Article, wraps once, skips
   confirmed completed Articles, selects the first unread or reading Article,
   and never selects the current Article.

## 4. Reader Workflow

The two-step workflow appears only when the Reader was entered with canonical
`from=/session` and the current Article is present and active in that queue.

### Step 1 - Mark Article complete

1. Reload and validate browser-local queue and active identity.
2. Read the current canonical Learning State.
3. Skip the PUT when already completed; otherwise PUT completed once.
4. If the PUT result is uncertain, GET the state before offering any replay.
5. Completion never mutates queue order, active pointer, or navigation.
6. After the completion attempt, end a known open Reader timer once. An
   uncertain timer response is reconciled through the sessions list before any
   retry.

### Step 2 - Open next unfinished Article

1. Reload the queue and a successful complete Learning State list.
2. Reconfirm the current Article is completed.
3. Recompute the successor from current queue order and canonical statuses.
4. Persist the successor as active before `router.replace` navigation.
5. A persistence failure must not navigate.
6. With no successor, expose an explicit action back to `/session`; never
   redirect automatically.

Known timer failures expose deterministic recovery:

- confirmed-open timer: Retry end rereads first and performs at most one PUT;
- unknown readback: status-check retry only, with no blind PUT replay;
- absent or unconfirmed timer creation: preserve confirmed Article completion
  and allow an explicit warned continuation without claiming timer success;
- every timer-warning continuation reuses the complete guarded Step 2 path.

Definitive Article 404 continues to use the existing unavailable state. Its
queue item is retained for review or manual removal.

## 5. Surface Consistency

- Session and Dashboard request the full Learning State list and show completed
  count, remaining count, next unfinished Article, and truthful terminal state.
- Status-fetch failure preserves manual navigation, shows Retry, and makes no
  terminal claim.
- Dashboard generic Continue excludes confirmed completed Articles. Dashboard
  routes to Session and never mutates the active queue pointer.
- Existing Library consistency is required when its canonical state request
  succeeds. Cross-tab live refresh during partial failure is out of scope.
- Manual Reader Previous and Next remain adjacency/review links and never
  mutate completion or active queue state.

## 6. Accessibility And Responsive Contract

- The Reader action region stays mounted with `tabIndex=-1` and a polite,
  atomic live region.
- Success, terminal, failure, and retry states receive deterministic focus.
  Definitive mutation failures use `role=alert`.
- A router-replaced session Reader focuses its Article heading and proves
  viewport intersection.
- Required viewports: 1440 x 900, 390 x 844, 320 x 844, and 720 x 450.
- Labels and controls must fit without horizontal overflow.

## 7. Allowed Changes

- `frontend/src/lib/studySession.ts`
- `frontend/src/lib/dashboard.ts`
- `frontend/src/lib/learning.ts`
- `frontend/src/components/StudySessionView.tsx`
- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/components/DashboardView.tsx`
- focused Frontend tests and test runners
- `scripts/e2e/run_product_e2e.py`
- this task's canonical, status, roadmap, README, alignment, and report files

## 8. Out Of Scope

- Backend, API, schema, persistence, learning-store, or M1 changes
- queue schema migration or removal of completed queue entries
- Article/source/derived-asset mutation
- Library redesign, recommendation ranking, AI-guided ordering, or new domain
  entities
- dependencies, lockfiles, workflows, source access, external search, private
  Zotero, real/paid Providers, candidate, tag, Release, or attestation

## 9. Execution Plan

1. Persist this alignment and current-task status.
2. Add failing pure tests for derived completion, omission/unknown behavior,
   wrapped successor selection, and completed-aware Dashboard resume.
3. Implement the minimal pure state model and existing API client seam.
4. Integrate Session, Dashboard, and the Reader's explicit two-step workflow.
5. Extend Product E2E for duplicate-safe writes, stale state, failures, focus,
   terminal state, responsive geometry, and cross-surface consistency.
6. Run focused tests, full Frontend tests, build, Backend regression, three
   isolated Product E2E runs, and repository security/artifact gates.
7. Obtain two independent implementation reviews and repair in-scope findings.
8. Commit and push implementation, verify exact-SHA CI, then commit and push a
   docs-only closure and verify its exact-SHA CI.

## 10. Acceptance Criteria

- Completion and successor pure tests cover unread, reading, completed,
  omission, unknown, empty, stale active, wrap, and terminal cases.
- Repeated completion actions do not duplicate a completed-state PUT.
- Uncertain completion and timer responses reconcile before any mutation retry.
- Session and Dashboard retain the queue and expose truthful completed,
  remaining, next, terminal, unavailable, and Retry states.
- Dashboard Continue never selects a confirmed completed Article.
- Reader Step 2 cannot navigate before successful local active-pointer save.
- Manual Previous/Next remain review-only.
- Keyboard focus and viewport intersection pass at every required viewport.
- Three isolated production Product E2E runs pass with zero non-loopback
  requests, zero unexpected console/page errors, and no horizontal overflow.
- Full Backend tests, Frontend tests, production build, workflow, dependency,
  secret, SBOM, artifact, and protected-path gates pass.
- Two independent implementation reviews pass.
- Implementation and closure commits each pass exact-SHA main CI; final `main`
  is clean and synchronized.

## 11. Stop Conditions

- An unknown worktree change or conflict appears.
- The workflow requires a Backend, API, persistence, schema, dependency,
  lockfile, workflow, frozen M1, source, Article, or derived-asset change.
- Required evidence needs source access, private Zotero, external search, or a
  real/paid Provider call.
- A test, build, browser, secret, artifact, review, or CI gate fails without an
  in-scope deterministic repair.
- A candidate, tag, Release, attestation, force push, or history rewrite becomes
  necessary.

## 12. Local Completion Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 108 passed
- production build: PASS, 11 routes
- Product E2E: 3/3 runs, 92 checks each, zero external requests and zero
  unexpected console/page errors
- workflow, suppression, dependency, secret, temporary SBOM, artifact, and
  protected-path gates: PASS
- independent final implementation reviews: 2 PASS
- evidence report:
  `docs/P3_025_FOCUSED_SESSION_COMPLETION_AND_GUIDED_ADVANCE_REPORT.md`
- implementation commit:
  `16d7d50759358c217dc5b0546256c967c6be703b`
- implementation exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33893619547`
- required implementation CI jobs: PASS; normal-main Docker and release
  evidence skipped as designed; uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
- candidate, tag, Release, attestation, source, private Zotero, and real
  Provider actions: not performed
