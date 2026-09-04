# P3-025 Focused Session Completion and Guided Advance

## Status

LOCAL GATES PASS / EXACT-SHA CI PENDING

## Objective

Add explicit, completion-aware progression to the existing Focused Session
without changing the queue schema or Backend contracts. A learner marks the
current Article complete and then deliberately opens the next unfinished
Article. Dashboard and Session present the same canonical completion summary.

## Canonical Semantics

- only server-backed `LearningState.status=completed` completes an Article
- Reader scroll progress and Reader timer state never imply completion
- the queue retains all Articles and its current schema/order
- a session is terminal only when it is nonempty and every queued Article is
  confirmed completed
- successful list omission means unread; failed list means unknown
- guided advance scans after current, wraps once, skips completed Articles,
  and never returns current
- Reader completion and advance are two explicit actions
- completion, timer end, and local pointer save are reconciled independently;
  partial success must be reported truthfully and remain recoverable
- manual Previous/Next remain review-only

## Required Product Behavior

1. The completion workflow appears only for a valid active Reader entered from
   `/session`.
2. `Mark Article complete` rereads canonical state and avoids a duplicate PUT.
   An uncertain PUT is reconciled by GET before any replay.
3. A known open timer is ended once after completion. Uncertainty is reconciled
   through the sessions list; no blind end replay is allowed.
4. `Open next unfinished Article` reloads queue and states, reconfirms current
   completion, derives the successor, saves it as active, then navigates.
5. Failed local save prevents navigation. No successor exposes an explicit
   return to `/session`, never an automatic redirect.
6. Session and Dashboard show completed, remaining, next unfinished, terminal,
   unavailable, and Retry states without removing completed queue entries.
7. Dashboard Continue excludes confirmed completed Articles and Dashboard does
   not mutate the active queue pointer.
8. The action region is persistent and focusable; live status is polite and
   atomic; mutation failures use alerts; the next Reader heading receives
   focus and is in the viewport.

## Allowed Changes

- `frontend/src/lib/studySession.ts`
- `frontend/src/lib/dashboard.ts`
- `frontend/src/lib/learning.ts`
- `frontend/src/components/StudySessionView.tsx`
- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/components/DashboardView.tsx`
- focused Frontend tests and test runners
- `scripts/e2e/run_product_e2e.py`
- P3-025 alignment, status, roadmap, README, and evidence documents

## Prohibited Scope

- Backend, API, schema, persistence, learning-store, frozen M1, source,
  Article, or derived-asset changes
- queue schema migration or automatic removal of completed items
- Library redesign, AI ordering, new domain entities, dependencies, lockfiles,
  workflows, source network, private Zotero, real/paid Providers, candidate,
  tag, Release, attestation, force push, or history rewriting
- runtime/private artifacts, corpora, databases, PDFs, HTML, images, browser
  traces/profiles/caches, credentials, or secrets in Git

## Acceptance

- pure completion model covers omission/unknown, stale active, wrap, empty, and
  terminal behavior
- duplicate-safe completion and timer reconciliation have automated evidence
- Session, Dashboard, Reader, and existing Library behavior remain consistent
- 1440 x 900, 390 x 844, 320 x 844, and 720 x 450 layouts have focus,
  intersection, and overflow evidence
- focused and full tests, production build, three Product E2E runs, security,
  artifact, and protected-path gates pass
- two independent implementation reviews pass
- implementation and docs-only closure commits pass exact-SHA main CI

## Authorization

Frontend/test/documentation work, isolated local fake-runtime verification,
local commits, non-force push to `main`, and exact-SHA CI readback are granted.
All prohibited scope above remains not granted. No v1.2 candidate is assigned.

## Local Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 108 passed
- production build: PASS, 11 routes
- Product E2E: 3/3 runs, 92 checks each, zero external requests and zero
  unexpected console/page errors
- security, artifact, and protected-path gates: PASS
- independent final implementation reviews: 2 PASS
- report: `docs/P3_025_FOCUSED_SESSION_COMPLETION_AND_GUIDED_ADVANCE_REPORT.md`
- implementation commit and exact-SHA main CI: pending
