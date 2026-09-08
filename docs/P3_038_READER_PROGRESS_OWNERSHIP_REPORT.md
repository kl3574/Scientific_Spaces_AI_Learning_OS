# P3-038 Reader Progress Ownership Report

Status: OPEN / IMPLEMENTATION CI PENDING
Baseline: a294c8fd36beee1b79673f05150310156d0d7f7f.
P3-037 closure CI 34225518378 is terminal PASS. This task is independent.

## Reproduced Defect

The production Reader maps tool-only window scrolling to reading progress.
All six fresh cases (Outline/Reading tools at 390x844, 320x844, 720x450)
write 0 -> 100 and set the References section. An actual Dashboard round trip
exposes /articles/crb-formula#references. Its expected-preservation assertion
fails (minimal diagnostic exit 1), establishing a user-visible RED.
That observed Backend /learning/state snapshot is unchanged; this is a local
Reader-progress/resume defect, not evidence of a Backend mastery defect.

## Causal Evidence

Pass-through instrumentation records activation, focus, window scroll, progress
render and native localStorage writes without changing DOM, styles or timers.
At 390x844: Outline ends with Article bottom -100.84px; Reading tools ends at
72.16px, still partly visible. Both display 100 and write it after approximately
300ms. A real body wheel of 500px yields 27% and a nonfinal section. The same
three cases observed for 6000ms retain those sequences with no late correction.
Three caller frames identify the same compiled writer, not the asynchronous
initiating event by themselves; the ordered event trace supplies correlation.

Baseline code's updateReadingPosition uses every armed window scroll and scans
headings by top <= readingLine without reading/tool ownership. It updates UI
and pending state together. Restore, resize and cleanup persistence must also
be considered. articleRoot.scrollHeight includes header and structured
references; changing that denominator is not the repair.

Cold tool URLs seeded with valid 43% / the derivation heading produce 100%
(Outline) or 88% (Reading tools), both with final References and a new timestamp.
An initial diagnostic wrongly expected tool focus on hard load and timed out
before its progress assertion. Existing P3-034 E2E explicitly preserves BODY
focus during hydration; the corrected read-only inspection confirms checkpoint
corruption, not a focus defect or a passing regression.

A context-only short Article response measures root 479px, Markdown 100px,
tools 2298px. At both 390x844 and 390x1280, Reading tools changes 0 -> 100;
root bottom ends at 72.33px. No canonical Article fixture was changed.
All successful diagnostics report zero external requests and unexpected
console/page errors. They used only an owned temporary synthetic preview;
no source, Provider, private Zotero or canonical corpus access occurred.

## Review And Fix Plan

Two independent read-only reviews endorse a separate bounded repair. Preserve
meaningful tuple and recency, legitimate pending flush, genuine forward/back
body reading, short content, native hashes, cold focus, history and origins.
The reviewed rendered matrix is in the canonical task. The candidate now
pauses tool-owned measurements, admits real document gestures using stable
layout samples, separates nested aside scrolling, rebases after preference
commits/reflow, and preserves explicit clamped headings. It keeps the original
progress denominator and ordinary body-reading path. Final review remains open.

## Current Validation Evidence

- The persisted new regression fails on the original compiled Reader
  (BUILD_ID 4Pj0OIWEfw5baX8YQBx4D): immediate tool activation displays 100%
  and References while the prior 0% snapshot has not yet reached its debounce.
  This is semantic RED, not a setup or request-admission failure.
- The unchanged original minimal diagnostic now passes: Outline retains 0%,
  no section, and actual Dashboard href /articles/crb-formula. Its observed
  Backend learning-state snapshot remains unchanged.
- Frontend pure suites: Articles 72, Tutor 24, References 23, Graph 29 PASS.
  The five new Article helper tests cover geometry, directional nested
  ownership, short Articles, reversal and malformed measurements.
- Backend: 671 passed, 4 skipped, 4 pre-existing invalid-escape warnings in
  36.81s. Re-run after final test/code corrections is still required.
- Production builds pass, 11 routes, Next.js 15.5.21. The latest completed
  rendered matrix used BUILD_ID bkGLyp0e2sBeFhc8iXkZQ.
- Fourteen rendered journeys PASS with zero external requests, unexpected
  console errors or page errors. This includes original six tool cases, cold
  saved positions, short Articles, reflow/resize, history/refresh, Dashboard
  resume and genuine wheel/keyboard/emulated-touch/end/retreat behavior.
  A subsequent additional clamped-heading/cold-restore case and final source
  correction are not covered by that 14-case result yet.
- Initial GREEN diagnostics exposed two new-test oracle errors: a successful
  Dashboard intentionally omits its remote-error banner; and a cold mobile
  tool hash can leave the pointer over Article references rather than tools.
  Corrected checks use actual Dashboard readiness and public tool activation
  plus elementFromPoint ownership. No product change was made for those
  incorrect assumptions. The end-scroll action now reaches the actual outer
  Article border; the percentage and visibility assertions are unchanged.
- Independent product review identified three genuine risks. The nested
  ticket leak is reproduced: aside scroll 300, window unchanged, then an
  unrelated programmatic window scroll 120 incorrectly changes 43% to 6%.
  Its negative regression now passes. The first wheel after Compact reflow
  also fails on the prior bundle, retaining 43% instead of the new geometry;
  post-layout rebasing passes its added single-action regression.
- Chromium nested boundary probe: one interior-start wheel of 5000 moves the
  aside to its 1610px boundary without moving the document. The next wheel of
  300 chains to the document. This supports the bounded directional adapter,
  not a claim about every physical browser/trackpad implementation.
- Native scrollbar probe with only Chromium's hide-scrollbars launch default
  disabled: a 15px document gutter emits trusted HTML pointerdown, document
  scroll and scrollend. No DOM/style change was used. Post-repair native
  scrollbar and boundary readback remain pending.
- Safety so far: 17 security unit tests, workflow 19/19 pins and explicit
  permissions, zero suppressions and zero reported/credible secrets PASS.
  Backend, M1, API, dependency/lock and workflow paths remain unchanged.

Full three-run Product E2E, final safety/visual gates, two final independent
reviews, implementation CI and closure CI are pending. No P3-038 commit or
push has been made. Earlier preview runtimes were stopped and removed before
rebuilds; the current owned preview is temporary synthetic data only.

## Validation And Risks

Unfinished P3-038 gates are not borrowed from P3-037. Existing Graph visibility
risk remains OPEN, root cause UNKNOWN.
Wheel, touch, keyboard, scrollbar, reflow and restore ownership need explicit
positive as well as negative tests. No runtime artifact is a deliverable.

## Post-review Input Boundaries

The subsequent 15-journey matrix, including clamped-heading restoration, passes
on its then-current bundle with zero unexpected errors or external requests.
This does not cover the later input-boundary corrections below or constitute
the complete three-repeat acceptance gate.

Independent test review found three coverage gaps: interior section expectations
were not independent of the saved result; keyboard/touch positives started after
wheel reading had already resumed; and pending-body exit did not enter tools.
The additive runner now derives heading identity/title from rendered Markdown,
compares active outline, displayed/stored progress and actual Dashboard resume,
and adds separate first-input and pending-body-to-tool scenarios. Clamped heading
checks now also require progress, section title and exact URL coherence. The
formal matrix still contains all 15 journeys, with seven additional subcases.
No canonical fixture, network/error audit or exactly-25-ended restart gate changes.

Two further real-input diagnostics reproduce failures on the preceding bundle:
an upward wheel at document/aside top and horizontal-only touch create no vertical
movement, but a later unrelated window displacement changes saved 43% to 6%.
Native thumb drag with an intervening Shift key moves the document to 231px but
leaves saved 43%. Directional document bounds, zero-delta touch handling and
non-scroll-key isolation correct these cases. A subsequent compiled check passes
both exact-tuple negatives, real thumb drag (18%, correct mathematical section)
and no-motion thumb release followed by unrelated displacement.

Native track-click is a distinct reproduced timing edge: document 0 -> 875px
after pointerup can leave progress at 43%. The correction gives that native
default action a bounded rendering opportunity before expiring its no-motion
ticket; newer inputs/intents and teardown cancel the pending release callback.
Final-bundle repeated track-click and the strengthened full matrix are running,
not claimed PASS here. All probes use temporary fake data, real Chromium input
or explicitly labelled CDP touch emulation, and no source/Provider/private access.

Additional completed checks: frontend 72 + 24 + 23 + 29 tests; production build
11 routes; security unit tests 17; dependency audit 40 PyPI / 239 npm with zero
findings; pinned workflow and zero-suppression checks; secret audit zero credible,
reported or suppressed findings; official-schema temporary SBOM validation with
40/239/281 components and forbidden=0. The temporary SBOM is removed.
Four rendered screenshots were inspected at 1440x1000, 390x844, 320x844 and
720x450: Chinese text and two math renderings present, no horizontal overflow or
incoherent overlap. Screenshots and their owned runtime were removed. The first
visual harness hit EOF only at its cleanup prompt; the corrected terminal-input
harness completed normally. This was not an application rendering failure.

Final current-source tests/reviews, three-repeat E2E and both exact-SHA CI gates
remain required. No P3-038 commit, push, tag or Release has been performed.

Latest boundary run on BUILD_ID tlerOFOYZEu4K8R2qCpot: four native/no-op cases
and six separate delayed track clicks pass. Each track activation starts its
observed movement after the pre-release snapshot and reaches 875px / 87%,
matching the unchanged geometry. The stronger Reader matrix then identifies
a test setup error: its first touch begins at 55%, moves to 61%, and correctly
selects References at top 154.64px, past the 168.8px reading line. The independent
geometry, title, active outline and store agree; the retained interior-section
assertion rejects the final section. The new action now starts at 20% instead
of 55%; no assertion or product behavior is relaxed. Focused re-validation is
pending. Backend re-run: 671 passed, 4 skipped, 4 existing warnings in 38.54s.

Independent product review additionally requests a below-Article upward native
track animation check. Downward track results alone do not establish that return
path: a release callback must not discard actual movement before it enters the
Article. This concrete input-boundary follow-up remains open.

## Final Native Return Correction

The deeper return diagnostic reproduces the review finding: after real tool
scrolling, Article bottom is -228.05px and the reading line is 168.8px. A native
upward track click moves the window 2783 -> 2045px but retains the old 43%.
The release callback was discarding an already moving, same-layout gesture
before that movement reached the Article. It now expires only motionless or
layout-invalid samples; actual native movement remains eligible until Article
entry, document scrollend or an existing input/intent invalidation. A shared
motion predicate and its sixth helper regression preserve the distinction
between actual movement and Article admission without changing either geometry.

On BUILD_ID 10QX_vUvgNj2aOy-J7ij5, all four no-op/thumb checks, six downward
track contexts and three deep upward return contexts pass. The deep returns
reach the actual Article end (100% under the unchanged denominator) and retain
References, rather than keeping the stale 43%. Network/error probes report zero
external requests and unexpected errors. These native checks use Chromium's
real 15px document scrollbar, without DOM or CSS mutation. They are Linux
Chromium evidence, not a physical-touch or cross-browser certification.

Final current-source unit/build results: Articles 73, Tutor 24, References 23,
Graph 29 (149 total); Backend 671 passed, 4 skipped, 4 existing warnings in
38.52s; production build PASS, 11 routes. The corrected first-input body subset
passes both desktop and mobile with zero unexpected errors/external requests.
The final strengthened all-15 matrix passes with zero external requests,
unexpected console errors or page errors. Its owned runtime and servers were
removed. The complete three-repeat product regression has now started on the
same build and hash-bound product/test sources; its result and both
implementation/closure CI gates remain open.

Independent product and test/scope final reviews report no remaining Critical
or Important finding. Product source blobs are ec55edcc508ad9f4d368932cb0ac5eb1135232b4
(component), 03f9edc57e82b4774d8c0b013535fa67f95313ab (helpers), and
57d3ad80d8dd6a11951bba0cb0464e29fa17924c (pure tests). Rendered runner blob is
ad65a3e96c13ab14874e314886869160c987932b. AST comparison against the baseline
finds only the new ownership function and its additive invocation; original
E2E functions/classes, audit policies and restart assertions are unchanged.

## Full Regression: Outgoing Reader Checkpoint Failure

The complete three-repeat command fails during the first iteration after
752.49s, at the new 390x844 body journey's Dashboard return. The valid saved
checkpoint is 45% / the numerical-check heading at 14:31:04.349Z; Dashboard
reads 0% / that same heading with a new timestamp at 14:31:05.701Z. This is
an actual persistence failure, not waived as an unrelated browser risk.
All bound product/test blobs and BUILD_ID are unchanged. No completed-repeat
or restart result is available from this invocation; do not infer acceptance
from the earlier focused passes. The command terminated, its servers stopped
normally and its temporary runtime was removed.

Submission is stopped pending an outgoing-navigation lifecycle diagnosis.
Candidate causes are route-scroll reset while the outgoing Reader still owns
tracking, automatic scrolling of the activated home link, or a stale Reader
focus/restore callback. A bounded real-click, pass-through scroll/storage trace
will distinguish them; no root cause or repair is claimed yet. Existing
independent review clearance preceded this new runtime evidence.

Full local gate: BLOCKED. Implementation and closure commits/CI remain pending.

The bounded CPU-throttled real-click trace reproduces this failure independently:
home activation retains the valid 45% at windowY 777; the route then becomes `/`
and the captured Article root is disconnected with top/height zero; the old
writer subsequently stores 0% with the previous numerical-check section. No
DOM, CSS or browser scheduling function was changed by the trace. The new
persisted sixteenth route-exit journey also fails on the preceding bundle at
the same exact-tuple assertion, without trace instrumentation.

The component correction checks live Article identity, root connectivity and
ref identity before progress measurement and delayed restoration. It does not
gate persistence on the destination URL or clear a legitimate dirty snapshot.
Thus destination scroll/DOM replacement cannot become an outgoing Article
reading sample, while the accepted pre-navigation checkpoint can still flush.
Focused GREEN, independent correction reviews and replacement full regression
remain pending. No assertion is relaxed and the failed full run stays failed.

## Incoming Article Layout Correction

The outgoing live-root guard preserves the original 45% checkpoint, but the
same real Dashboard Continue journey exposes another failure: displayed and
stored progress remain 100% after returning to the numerical-check heading,
while the independently measured final Article geometry requires 43%.
A read-only runtime trace observes the root expand from 1430px to 2382px as
Structured References arrive. That instrumented run eventually corrects to
43%, so it is not evidence that the uninstrumented failure was repaired.

The sixteenth persisted regression now delays one actual incoming local GET
reference response by 800ms, retaining its payload and headers. It requires
the root to grow and retains the original final progress, storage, heading,
focus, exact-URL, backend-isolation and error/network assertions. This new
regression deterministically fails on the outgoing-guard-only bundle at
100% versus 43%; it is not a synthetic progress setter or altered denominator.

The existing ResizeObserver only rebased geometry and invalidated stale input;
it never requested a follow-up progress calculation. The correction refreshes
through the existing RAF and debounce only after a body measurement has been
admitted, restoration/tracking are armed, the root still owns the live Article,
and tools do not own progress. Admission is not inferred from saved data or
the protected Graph/header restoration branches. Tool bookkeeping and all
existing dirty-snapshot flushes remain intact. No scrolling, focus transfer,
direct storage write or second progress formula is introduced by the observer.

On component blob 576311f93c68e9c05f9e034ca8504d69b4dca4d1 and BUILD_ID
u_P66P2-yviCntdgjOLU2, the delayed-response route-exit regression passes,
with zero external requests or unexpected console/page errors. Current unit
tests pass: Articles 73, Tutor 24, References 23, Graph 29; Backend 671 passed,
4 skipped, 4 existing invalid-escape warnings in 38.54s. Production build
passes all 11 routes. Security unit tests 17, workflow pin/permission policy,
zero-suppression policy and zero credible/reported/suppressed secret findings
also pass.

Independent test review identifies two important diagnostic-access risks:
unanchored route matching and implicit redirects inside route.fetch. The
candidate now anchors the complete local URL, checks exact origin/path/method,
rejects unexpected query/body/fragment and duplicate reads before fetching,
uses max_redirects=0, and requires the response URL to equal the requested URL.
Its focused re-validation and final review are still required; the prior GREEN
does not certify this later runner hardening. No external access occurred in
the completed owned-runtime checks.

The current all-sixteen matrix is running on the pre-hardening loaded runner;
the final runner must receive its own focused check and complete three-repeat
acceptance. Product/test correction reviews and implementation/closure CI
remain open. Full local gate remains BLOCKED until the replacement full
regression succeeds. No P3-038 commit, push, tag or Release has been performed.

## Viewport Persistence And Protected Admission

The preceding sixteen-journey matrix passes on component 576311f, including
the incoming layout correction. The hardened exact-local response handler also
passes its own route-exit check. Its nine pre-fetch rejection cases, two
response rejection cases, exact-local success and fully anchored matching
pass an in-memory test of the actual handler AST, with no network activity.
Independent test review clears both diagnostic-access findings.

The product review requests a pure viewport-change check. That additional
mobile regression fails: at unchanged windowY 777 and Article height 2382,
shrinking viewport height 844 -> 744 changes the displayed and independent
progress from 45% to 42%, but storage remains 45%. A viewport-only change
need not resize the Article element, and the ordinary resize scheduler did
not request persistence. Already-admitted body resize now uses the same
pending flag, RAF and debounce as accepted reading, while tool ownership
continues to reject progress writes.

On component 2950312 and BUILD_ID 2UmmNWRZeVCkbmqmRtwdW, the full sixteen
journeys, including desktop/mobile shrink and restore, pass. Four no-op/thumb
checks, six native downward track contexts and three deep upward returns also
pass on this build. All report zero external requests and unexpected errors.

Further independent review exposes a protected-entry admission hazard. The
new seventeenth regression seeds saved 43%, opens a real Graph-return Reader
route, and changes viewport height 1000 -> 900 -> 1000 without body input.
It fails on that build: the first resize silently admits a body measurement;
the second writes 0% and a new timestamp. This is an observed regression, not
waived as an artificial-event or browser risk.

The scheduler now checks live-root ownership and, before body admission,
handles resize only by rebasing document/tools measurements. It does not
schedule a reading sample, clear a dirty checkpoint, or cancel an existing
legitimate pending body frame. Already-admitted body resize and real body
scroll retain their ordinary update path. The protected regression includes
a subsequent real wheel positive to reject a permanent progress lock.

Latest protected-entry correction GREEN and final all-seventeen regression
remain pending. The added tests do not remove any prior journey or change the
baseline audit/restart gate. Backend re-run before the seventeenth addition:
671 passed, 4 skipped, 4 existing warnings in 38.61s. Current pure Frontend
suites remain 149 PASS. Dependency audit passes 40 PyPI / 239 npm with zero
findings; temporary SBOM has 40/239/281 components, official schema/coverage
PASS and forbidden=0, and is removed. All unfinished gates remain open.

The protected-entry correction now passes its exact seventeenth regression,
including subsequent genuine body movement, with zero unexpected errors or
external requests. Independent product and test/scope correction reviews
both report no remaining Critical/Important finding. The protected cold Graph
entry intentionally displays Article start / 0% while retaining its saved
43% tuple; the regression preserves both, rather than conflating displayed
entry state with stored resume progress.

Final candidate bindings are component
a94660a3b76bf78436a287ef5846ef8bed083cfd, helper
03f9edc57e82b4774d8c0b013535fa67f95313ab, pure tests
57d3ad80d8dd6a11951bba0cb0464e29fa17924c, rendered runner
421d05e451d5db565d66a9a193caee7a9a7304d0 and BUILD_ID
dhuN0yOT3QvFk_CZjk1q7. On these sources, Backend is 671 passed / 4 skipped
with 4 existing warnings in 37.77s; Frontend 73/24/23/29 and the 11-route
production build pass. The secret audit again reports zero findings.

The exact canonical three-repeat Product E2E has started on these bound
sources, with the final seventeen-journey ownership matrix included in every
iteration. No result, restart outcome or CI success is claimed before it
terminates. Product/test sources and build remain unchanged during that run.
The earlier full-suite failure remains historical failed evidence; task
closure and implementation/closure commits are still pending.

## Invalidated Concurrent Visual Run

The replacement full invocation is deliberately interrupted and cannot be used
as acceptance evidence. A concurrent visual sidecar incorrectly intercepted
127.0.0.1:8000 writes, while the compiled Reader uses localhost:8000. Its
session-write isolation therefore did not cover the actual browser API origin;
shared temporary runtime mutation cannot be excluded. The absence of browser
errors is not proof of isolation. No private or canonical repository data was
involved, but this invalidates the claimed clean test environment.

The owned full runner and both servers terminate, and its temporary directory
is removed. KeyboardInterrupt and the wrapper's consequent JSONDecodeError are
operator-stop results, not application failures or a passing partial run.
All four sidecar screenshots had already been removed. No partial repeat or
restart result is accepted from this invocation.

Visual inspection is being repeated in a separate, freshly prepared temporary
runtime, before a new full invocation. The full acceptance run must execute
alone: no concurrent browser/API probes, regardless of claimed route isolation.
Product/test source and build bindings remain unchanged. Submission stays
stopped until a clean complete three-repeat result and all remaining gates.

The corrected visual check completes in its own fresh synthetic runtime on
the final bound build. Screenshots at 1440x1000, 390x844, 320x844 and 720x450
are inspected: Chinese title/body and two formula renderings are present,
document widths equal viewport widths, and no incoherent overlap is observed.
External requests and unexpected console/page errors are zero. The screenshots,
temporary data and both visual servers are removed; ports 8000/3000 are free
before the exclusive replacement acceptance run. This supersedes the earlier
sidecar's isolation claim, not the history of that invalidated invocation.

## Final Local Acceptance

Date: 2026-09-09, Asia/Shanghai. The exclusive replacement command
`uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
terminates with exit 0 and PASS in 2465.82s on the final bindings above.
Chromium version: 149.0.7827.55. No other browser/API probe runs against this
temporary runtime. Source and build binding equality is verified at completion.

- Complete runs: 3/3 PASS; 298/298 checks each.
- Reader ownership: all 17 journeys PASS in each run, including the new
  outgoing/incoming layout and protected-entry cases plus body resize.
- Restart persistence: bookmark, completed states, ended sessions and note
  PASS under the unchanged restart gate, including exactly 25 ended sessions.
- External requests, unexpected console errors, page errors and Next static
  chunk cancellations: 0. Existing strictly scoped route/prefetch cancellation
  handling is unchanged; those expected categories are not misreported as zero.
- Backend: 671 passed, 4 skipped, 4 existing warnings; Frontend: 149 PASS;
  production build: 11 routes PASS.
- Separate final-build native input recheck: four no-op/thumb cases, six
  downward track contexts and three deep upward return contexts PASS, with
  zero external requests and unexpected errors. Completed after the exclusive
  acceptance runtime was removed, in a new temporary runtime also removed.
- Independent visual inspection: four viewports PASS in its separate runtime;
  all screenshots, data and owned servers removed.
- Workflow policy, 17 security unit tests, zero-suppression policy, dependency
  audit (40 PyPI / 239 npm, zero findings), official-schema temporary SBOM and
  secret audit PASS. No forbidden runtime/private artifact is a deliverable.
- Independent product and test/scope reviews: no unresolved Critical/Important
  finding on the final source bindings. Documentation scope review also passes.

Local gate: PASS. Task: OPEN / IMPLEMENTATION CI PENDING. The earlier genuine
full-suite failure and the explicitly invalidated sidecar-contaminated attempt
remain unsuccessful evidence. No acceptance criterion is waived. The unrelated
historical Graph visibility incident remains OPEN / UNRESOLVED, root cause
UNKNOWN; passing this run does not establish its root cause or repair.

Next: submit `fix: preserve meaningful reader progress` and verify that exact
commit's main CI. Only then prepare `docs: close P3-038 reader progress ownership`
and verify its separate exact-SHA CI before PASS / CLOSED. Formal v1.1.0,
candidate none; no source/Provider/private Zotero access, tag or Release action.
