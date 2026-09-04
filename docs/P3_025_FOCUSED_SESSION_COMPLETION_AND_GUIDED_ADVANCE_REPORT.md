# P3-025 Focused Session Completion and Guided Advance Report

Status: **PASS / CLOSED**

## 1. Scope And Boundaries

P3-025 connects the existing browser-local Focused Session queue to the
existing server-backed Learning State without changing either contract. The
Reader now exposes two explicit actions: first confirm the current Article as
completed, then deliberately open the next unfinished Article. Dashboard and
Session derive the same completion summary.

Backend code, frozen M1 modules, source and Article records, derived assets,
dependencies, lockfiles, workflows, and published APIs remain unchanged. No
source request, external search, private Zotero action, real Provider call,
candidate, tag, Release, or attestation occurred.

## 2. Canonical Completion Model

- Only `LearningState.status === "completed"` completes an Article.
- Reader scroll progress and timer state never imply completion.
- Completed Articles remain in the queue and retain its existing order and
  schema.
- A nonempty queue is terminal only when every queued Article is confirmed
  complete.
- Omission from a successful state list means unread; a failed list means
  unknown and cannot prove terminal state.
- Guided advance scans after the current Article, wraps once, skips confirmed
  completed items, and never returns the current Article.

The pure model covers unread, reading, completed, omission, unknown, empty,
stale-active, wrapped-successor, and terminal cases.

## 3. Reader Workflow

The completion panel is available only for the active queue item opened from
`/session`. Manual Previous and Next links remain review-only and never change
the active queue pointer.

`Mark Article complete` reloads canonical state, avoids a duplicate completed
PUT, and reconciles an uncertain write through readback. A known Reader timer
is ended separately. Timer uncertainty preserves the confirmed Article result,
performs no blind replay, and exposes bounded recovery or warned continuation.

`Open next unfinished Article` reloads canonical completion state, rereads the
latest local queue, reconfirms the current Article, saves the successor as
active, and only then navigates. Failed local persistence prevents navigation.
Leaving the Reader invalidates in-flight operations, so stale requests cannot
rewrite the queue pointer or override newer navigation.

## 4. Dashboard And Session Consistency

Dashboard and Session request the complete Learning State list and show
completed count, remaining count, next unfinished Article, and terminal state
from the same model. Confirmed completed Articles are excluded from generic
Dashboard Continue choices. A failed state-list request keeps manual links
available, reports completion as unavailable, and exposes Retry without making
a false empty or terminal claim.

## 5. Accessibility And Responsive Evidence

- the persistent completion region is programmatically focusable;
- the router-replaced Reader focuses its Article heading;
- real forward Tab order reaches the first completion action from that heading;
- one polite, atomic live region reports bounded status changes;
- definitive failures use an alert and return focus to the completion region;
- timer and completion mutations lock conflicting controls;
- terminal, retry, stale-active, and local-write failures have deterministic
  focus evidence; and
- 1440 x 900, 390 x 844, 320 x 844, and 720 x 450 layouts pass intersection,
  keyboard, action-fit, and horizontal-overflow checks.

## 6. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 39.10s
```

### Frontend

- Article, Reader, Dashboard, workflow, and navigation: 35 passed
- Focused Session and completion model: 13 passed
- structured References: 3 passed
- Tutor: 20 passed
- Graph and Concept Study Set: 27 passed
- global search: 5 passed
- Saved Learning Library: 5 passed
- focused total: 108 passed
- Next.js 15.5.21 production build: PASS, 11 routes
- Article detail: 14.8 kB route / 249 kB first load
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py \
  --repeat 3 --frontend-mode start
```

- formal complete runs: 3
- formal successful runs: 3
- checks per run: 92
- completion, duplicate-write, timer-reconciliation, stale-state,
  persistence-failure, cancelled-advance, terminal, and responsive cases: PASS
- restart persistence: PASS
- Chromium: 149.0.7827.55
- non-loopback requests: 0
- unexpected console errors: 0
- page errors: 0

## 7. Security, Artifact, And Protected Paths

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action full-SHA pin rate: 100 percent
- explicit workflow and job permission rate: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- dependency audit: PASS, 40 PyPI / 239 npm packages / 0 findings
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM schema, dependency coverage, and forbidden-value checks: PASS
- temporary evidence cleanup: PASS
- Backend, frozen M1, source, Article, derived-asset, dependency, lockfile,
  workflow, and published API changes: 0
- tracked runtime/private artifact additions: 0

The unrelated agent-authored `AGENTS.md` remains absent. The existing tracked
`.env.example` is a credential-free template, not a runtime secret.

## 8. Independent Review And Repairs

Two independent final reviews returned PASS. Findings repaired before final
validation included duplicate-safe timer actions, review-only manual
navigation, canonical state readback, stale queue rereads, request-generation
guards, unmount cancellation, truthful Dashboard partial states, one live
announcement path, and real keyboard focus order.

## 9. Known Risks

- Learning State and timer writes are separate existing Backend operations, so
  temporary partial success remains possible; the UI exposes reconciliation
  rather than claiming an atomic transaction.
- The queue remains browser-local and is not a cross-device or multi-user
  workflow.
- Dashboard and Session cannot derive canonical completion while the full
  Learning State list is unavailable; they deliberately report unknown and
  retain manual access.
- Browser storage eviction can remove the local queue, as in the pre-existing
  Focused Session contract.

## 10. Exact-SHA Main CI

Implementation commit:
`16d7d50759358c217dc5b0546256c967c6be703b`.

Exact-SHA main CI:
`https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33893619547`.

The run completed successfully for the exact implementation SHA. Backend
pytest, Frontend build, three-run Product E2E, workflow and suppression policy,
dependency audit, secret audit, and SBOM validation all passed. Docker compose
smoke and release evidence skipped as designed for an ordinary `main` push.
Uploaded artifacts: 0.

## 11. Current Decision

P3-025 is PASS / CLOSED. Its implementation passed all local gates, two
independent reviews, and exact-SHA main CI. This docs-only closure commit must
pass its own exact-SHA main CI before final reporting. No v1.2 candidate is
assigned.
