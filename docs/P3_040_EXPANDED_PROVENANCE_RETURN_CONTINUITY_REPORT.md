# P3-040 Expanded Provenance Return Continuity Report

Status: LOCAL VERIFICATION PASS / PUBLICATION CI PENDING

## Root Cause And RED Evidence

`GraphNodeDetail` initializes `NodeContent` with collapsed provenance and renders
only the first three returned sources. `GraphView` consumes the exact Article
return marker but searches only currently rendered links. An existing fourth
source therefore takes the same fallback as a genuinely missing source.

One unchanged-production Chromium run on 2026-09-09 used the existing three
synthetic Articles and a temporary concept with four distinct section-source
entries. Only its temporary Graph metadata was enriched before server startup;
the same fixture remained in place for both sides of navigation.

Native keyboard journey: Show 1 more returned sources, provenance-3, Article,
end the temporary reading session, Back to concept. After detail/request
settlement the diagnostic recorded:

| Check | Result |
| --- | --- |
| Exact concept and query URL | true |
| Fourth-source DOM count | 0 |
| Fourth source visible / focused | false / false |
| Sources collapsed again | true |
| Selected detail region focused | true |
| External / unexpected console / page / context pages | 0 / 0 / 0 / 0 |
| Fixture unchanged | true |
| Product/build bindings unchanged | true |
| Temporary runtime removed | true |

This is a rendered navigation failure, not a Graph map-rendering reproduction.
The first and genuinely missing provenance origins have existing E2E coverage;
the expanded fourth-source path was missing. The dedicated regression now covers
the expanded source and the additional arrival-ownership counterexample.

## Verification Status

- Entry Graph unit suite: 29 passed.
- Independent concrete design review: approved before product edits, with
  post-disclosure focus, supersession and competing-focus cancellation required.
- Product correction implemented; Graph unit suite: 33 passed, including four
  new contracts for exact/visible/malformed/missing/filtered/unsafe origins.
- Frontend tests: Articles 73, Tutor 24, References 23, Graph 33; all 153 PASS.
- Production build: PASS, Next.js 15.5.21, 11 static pages generated.
- Dedicated runner offline contracts: final 47 PASS. They cover temporary-only seed
  ownership, fixed markers, native keyboard/route-ledger ordering, cleanup and
  non-passing failures. These mocks do not substitute for browser execution.
- Ordinary Backend suite after the arrival correction: 770 passed, 4 skipped,
  6 existing invalid-escape warnings in 40.29s. Exit 0 after process teardown.
  The earlier 750-test result preceded the additional arrival contracts.
- Secret audit: PASS, credible/reported/suppressed 0. Protected Backend, map
  renderer/model, original E2E, dependency and workflow diff: empty.
- Dedicated browser regression: initial six of six fresh contexts PASS across desktop
  1440x1000 and mobile 390x844. Fourth-source return, explicit collapse,
  first-source return, cold reload and missing/wrong-Article fallback pass.
  Audit counts are all zero; fixture/source/build bindings are stable and the
  temporary runtime is removed. Independent runner review preceded execution.
- Final seven-case browser regression after the arrival correction: 7/7 PASS,
  all audit counts zero, unchanged fixture/source/build bindings, runtime removed.
- Two independent focused product-amendment reviews: no Critical/Important
  finding; the previously open arrival-focus finding is closed.
- Full unchanged Product E2E `--repeat 3 --frontend-mode start`: PASS on
  2026-09-09, Chromium 149.0.7827.55, exit 0, 2470.68 seconds. All three runs
  pass 298/298 checks; each has zero external requests, unexpected console
  errors and page errors. Restart persistence passes bookmark, completed-state,
  ended-session and note checks. Source/build/fixture bindings remain equal,
  the owned temporary runtime is removed and stderr is empty.
- Existing strict request auditing remains intact: 735 route-transition
  expectations, 68 bound requests, 49 classified transition cancellations,
  12 declared route-read cancellations and 1197 framework-prefetch cancellations.
  These are classified request outcomes, not ignored unexpected errors.
- Independent final publication-scope review: no material discrepancy; exactly
  16 candidate paths. The known untracked frame-oracle draft is excluded.
- Workflow/suppression policy, secret audit and protected-path checks: PASS.
- Implementation publication candidate: this commit. Its exact-SHA main CI must
  still pass before closure; local evidence is not remote CI evidence. Do not
  create a receipt-only commit to record this commit's own SHA.

## Related Work

P3-039 diagnostic d25113d passes exact-SHA CI 34276540291, seven required jobs.
Its historical node-rendering cause remains UNKNOWN. The optional frame-oracle
draft is preserved, deferred and excluded from this task's publication. Reader
inline-image filtering is a separate reviewed candidate, not part of this change.

## Arrival-Ownership Review And Correction

One independent product reviewer found no Critical/Important issue; another
identified a concrete source-derived counterexample that the six cases do not
cover. With details delayed, a mobile user can activate Results and then Selected.
Once the user's ordinary focus request has finished, the late return marker can
still expand provenance and replace that newer detail-region focus. This was
recorded as an Important finding in the initial correction, not waived as a risk.

An initial inline attempt to reproduce it was INCONCLUSIVE: `route.fetch` had not
finished when the test required its captured response. Context teardown then
reported a callback TargetClosedError. No private values or files were exported;
the temporary runtime was removed and product/build bindings remained unchanged.
The next bounded regression must wait for the captured real response before user
actions, latch callback failures and clean up its owned route before context close.
The six-case PASS does not establish completion of this additional ownership gate.

The revised held-response helper explicitly waits for a unique, completed real
200 response before Results/Selected actions. It releases that response unchanged
only after the detail region is focused, verifies detail application and request
settlement, and cleans up only its route/response. Prerequisite assertion failures
are BLOCKED, not product RED; two added contracts first failed the old classifier
and passed after the narrow correction.

One qualified seven-case execution then passed the original six cases but failed
the new mobile `arrival_superseded` final focus gate. All prerequisite, audit,
binding and cleanup conditions passed. This is evidence of lost newer region
focus; the output did not directly record the replacement focus target.

The approved correction latches explicit user cancellation for the Graph arrival,
retires a canceled return marker without expansion or fallback, and rechecks the
latch before deferred focus. Automatic route focus is distinguished from user
actions. The latch remains effective after a user's ordinary focus request has
already finished, and through retry. A rebuilt seven-case execution passes every
case with clean audit and cleanup. Both independent reviewers approve the bounded
product amendment. This does not close P3-039 or substitute for full Product E2E.
