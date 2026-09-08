# P3-036 Workspace Mutation Focus Continuity Report

## 1. Status

- Local implementation: **PASS**
- Independent final review: **PASS**, 2/2 reviewers, 0 Critical / 0 Important /
  0 Minor
- Latest exact-SHA repair main CI: **FAILED**, run `34178687022`
- Task closure: **REOPENED / CI EVIDENCE REPAIR**
- Replacement implementation and docs-only closure CI: **PENDING**
- Candidate version: not assigned

Sections 2-10 preserve the earlier implementation evidence. Subsequent closure
run `34024098616` and repair run `34065911116` failed Product E2E; they supersede
the earlier closure claim. The bounded script repair and fresh browser/CI
evidence below must pass before the task closes.

## 2. Entry Evidence

Two independent reviewers audited exact entry HEAD
`7997cceca268bae1e43806efb5460674a699dc92` with Chromium
`149.0.7827.55`, an isolated three-Article fixture, fake providers, temporary
runtime storage, and loopback-only networking. A separate controlled probe
reproduced the core failures and observed zero blocked external requests.

The probe found `document.activeElement === document.body` after Article List
selection clearing; Reader bookmark, learning-state, note, and session
mutations; Saved Learning capture; Concept capture; and Focused Session queue
mutations. The independent reviews additionally reproduced Graph search and
paging, Saved Learning filter clearing, Tutor Article/context mutations, Tutor
activity retry, and boundary queue movement. These were rendered
focus-ownership defects rather than data or API failures.

## 3. Root Cause

Affected controls became disabled, unmounted, or switched rendering mode as
their state committed. Although visible feedback often updated correctly, no
stable element inherited focus and the browser fell back to `BODY`. Several
async paths also lacked operation-specific ownership, so a delayed result could
either lose focus or override a newer user action.

## 4. Implemented Repair

- Article List selection clearing returns focus to its persistent capture
  region; search clearing returns to the search input; retry completion owns the
  stable list status only while its operation remains current.
- Reader bookmark, learning-state, note create/update/edit/cancel/delete,
  completion, timer, session ending, and guided-advance outcomes use exact
  Article, note, generation, and interaction ownership before moving focus.
- Saved Learning filtering and Session capture restore focus to the filter or
  exact initiating Article result without stealing a later focus move.
- Focused Session clear confirmation, cancellation, current-item changes,
  boundary moves, removal, and empty-queue recovery use stable local targets.
- Graph search, clearing, paging, Reader round trips, and Knowledge Context
  loading preserve destination and request ownership, including initial-frame
  and terminal async transitions.
- Concept capture and Tutor Article/activity mutations use persistent result
  regions or exact search results with request and interaction-version guards.
- All programmatic targets expose a visible focus indicator.

No request count, payload, route, history, storage write, data record, API, or
business outcome changed. No Backend, dependency, lockfile, workflow, source,
private Zotero, or release surface changed.

## 5. Race And Regression Evidence

Permanent browser assertions cover delayed note deletion, completion, timer,
guided advance success/error, Graph article return, Graph Knowledge Context
initial/terminal frames, Tutor search/retry, overlapping Tutor searches whose
older response settles last, and retry successors across Article List, Saved
Learning, and Focused Session.

The suite also preserves the already-correct note-delete confirmation,
completion reconciliation, queue-confirmation entry, non-boundary movement,
Graph keyboard selection, and Reader hash-focus contracts. During development,
new RED assertions exposed stale focus assumptions and an initial-frame Graph
race; each was repaired and rerun to GREEN before the formal evidence below.

## 6. Local Test Evidence

| Gate | Result |
| --- | --- |
| Articles/Reader tests | PASS, 67/67 |
| References tests | PASS, 21/21 |
| Tutor tests | PASS, 22/22 |
| Graph tests | PASS, 29/29 |
| Focused Frontend total | PASS, 139/139 |
| Frontend production build | PASS, 11 routes |
| Backend regression | PASS, 600 passed / 4 skipped |
| Product E2E | PASS, 3/3 complete runs; 225/225 checks per run |
| Chromium | 149.0.7827.55 |
| Restart persistence | PASS |
| External browser requests | 0 |
| Unexpected console errors | 0 |
| Page errors | 0 |

The formal Product E2E ran at `1440x900`, `390x844`, `320x844`, and
`720x450`. Every constrained document width matched its viewport, focused
targets remained available, and no page-level horizontal overflow was found.

## 7. Independent Review Evidence

Two independent final reviewers inspected the complete allowlisted diff after
the final race repairs. A follow-up reviewer found two fail-closed URL ownership
edge cases during the CI-test repair; both were fixed and both reviewers then
reported 0 Critical, 0 Important, and 0 Minor findings. No reviewer edited
repository files.

## 8. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- changed and untracked paths: P3-036 allowlist only
- tracked forbidden runtime/private artifacts introduced: 0
- source access, external search, private Zotero, and real/paid Provider calls: 0

The local dependency audit was not invoked because it requires registry network
access, which P3-036 does not authorize. The existing exact-SHA CI dependency
job remains the required evidence for that gate. Temporary browser and SBOM
evidence stayed outside the repository and is removed before commit.

## 9. Initial Exact-SHA CI And Bounded Repair

Implementation commit `d864cc1755b050a1dfeb247beaaa8a9d20a2eab3`
triggered exact-SHA main CI run
[`34019342064`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34019342064).
Backend, Frontend, dependency, workflow/suppression, secret, and SBOM jobs
passed; normal-main Docker and release evidence skipped as designed; uploaded
artifacts were zero.

The Product E2E job exposed two independent test-evidence races:

- attempt 1 completed the product flow but treated a repeated intentional
  Article 404 as unexpected because the harness used a global count allowance;
- unchanged-SHA attempt 2 reached the existing ordinary Shell test before a
  Dashboard layout had reached its observable terminal state, so its immediate
  scroll snapshot differed after same-route brand activation.

The bounded repair keeps every product assertion strict. Intentional 404s are
now consumed only when the shared and page-scoped console sequences match and
every console location and response URL has the exact HTTP loopback host, port,
path, and empty credentials/params/query/fragment. The global 404 allowance is
removed. The Shell test waits for Dashboard `aria-busy=false` and animation
frames before establishing scroll, while preserving exact history, URL, focus,
and scroll assertions.

Repair evidence:

- endpoint predicate: 2 valid forms accepted; 9 malformed or unrelated forms
  rejected; unowned shared errors rejected
- intentional 404 browser probe: 10/10 PASS
- ordinary Shell route-focus stress: 20/20 PASS
- final Product E2E: 3/3 runs, 225/225 checks each, restart persistence PASS,
  and zero external requests, console errors, or page errors
- final independent reviews: 2/2 PASS, 0 Critical / 0 Important / 0 Minor

## 10. Exact-SHA Repair CI

- cumulative repair commit:
  `39369ea430e942ce12c176fb9a9ca24111e59ef3`
- exact-SHA main CI:
  [`34023028516`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34023028516)
- event / branch / head SHA: `push` / `main` /
  `39369ea430e942ce12c176fb9a9ca24111e59ef3`
- Backend pytest: PASS
- Frontend build: PASS
- Product E2E: PASS
- dependency, workflow/suppression, secret, and SBOM jobs: PASS
- normal-main Docker and release evidence: skipped as designed
- uploaded artifacts: 0
- non-blocking platform notice: GitHub reported the existing future Node.js 20
  Action runtime deprecation; workflow changes are outside P3-036 scope

## 11. Final Disposition

P3-036 result: **REOPENED / CI EVIDENCE REPAIR**. No v1.2 candidate, tag, or
Release is assigned. Local GUI runs and final focused regression pass with the
version qualification below; the replacement repair and docs-only closure
require exact-SHA main CI.

## 12. Route Evidence Repair (2026-09-08)

The later CI failure concerns a destination RSC response that returned HTTP
200, was cancelled by the browser, and was followed immediately by the exact
destination navigation while Playwright still recorded the earlier page URL.
The UI assertions must pass independently; a cancelled response is not reported
as a successfully downloaded response or proof of cache consumption.

The repair adds an explicitly bound recovery path with ordered request,
response, cancellation, and navigation evidence. It requires one exact
next-generation destination event within 250 ms, no competing route declaration,
and exact current-request ownership. Previously completed same-destination
responses are captured at declaration and classified as a precursor snapshot,
without claiming which response supplied the rendered page.

An initial overly broad historical-sibling check caused false failures on
ordinary navigation. A focused Shell reproduction completed all visible
navigation/focus assertions but reported three audit failures. The recovered
request ledger showed independently valid prefetch cancellations being counted
again as competing destination requests. The final correction preserves their
separate validation and applies historical equality only to explicit stale-page
recovery. The matching ordinary-route waiter uses the same boundary, retaining
strict selection among current requests. The focused Shell reproduction then
passed with zero audit failures, external requests, and page errors.

Regression evidence includes real declaration/binding/completion/audit methods
with two completed precursors, two ordinary visits through the actual waiter,
invalid response and ordering cases, and valid/failed historical prefetches.
Missing responses, HTTP 301/500, competing current requests, delayed or duplicate
special navigation, and cross-expectation reuse are rejected. Responsive
reference-filter checks also verify the selected filter and fixture-appropriate
candidate or empty state in addition to focus and URL.

Current local evidence:

- Backend: 600 passed, 4 skipped.
- Frontend: Articles 67, References 21, Tutor 22, Graph 29; total 139 passed.
- Production build: PASS, 11 routes.
- Embedded evidence regressions and focused Shell browser probe: PASS.
- Local three-run Product E2E: PASS, 3/3 complete runs, 226/226 checks each; restart persistence
  PASS, zero external requests and unexpected console/page errors. See the
  version qualification below.
- Route telemetry across three runs: 381 declared transitions, 66 bound
  requests, 50 ordinary route cancellations, 640 independently validated
  prefetch cancellations, and zero special precursor-snapshot recoveries.
- Independent final reviews: 2/2 PASS on script blob
  `af0f5b9f1a07912ea6d4ec5551c2283b66891d0c`; no remaining Important findings.
- Workflow, suppression, secret audit: PASS; no findings.
- Temporary SBOM: PASS, 40 Backend / 239 Frontend / 281 combined components.
- Replacement repair and closure CI: pending.

One earlier three-run invocation was intentionally interrupted after the waiter
fix was identified; it is not counted as completed verification.

The completed local three-run invocation began at script blob
`370664ffdb1e7691096ef24957281e61f7b7eac5`. During that run, the existing
pre-start navigation certificate was extracted into one shared helper used by
the caller, waiter, and final audit. The final helper and three-visit waiter
regressions passed independently and in both reviews. Exact-version three-run
GUI evidence remains required in the replacement commit's CI; the local run
does not claim to test this later helper extraction.

## 13. Tutor Activity Closure Repair (2026-09-08)

Exact-SHA main CI for `6844a4073134902337e58d07bb9d947fcc1d4814`,
[`34178687022`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34178687022),
completed with Backend, Frontend, dependency, workflow/suppression, secret,
and SBOM jobs passing. Product E2E completed its UI assertions but failed its
final ledger audit on one unfinished `GET /tutor/sessions` from the
`graph-reload` page. Normal-main Docker and release jobs skipped as designed;
uploaded artifacts: 0. This run is not passing closure evidence.

The final Tutor retry waits for the answer's focus, then closes the page. The
product intentionally starts its independent activity POST followed by GET
after publishing the answer; answer focus does not prove that read has ended.
The existing wait for the preceding intentional `/tutor/ask` error only drains
that declared failed request, not the later activity read.

A loopback-only Chromium reproduction held the actual activity GET after the
successful retry. Answer focus passed with one activity request still pending;
the old close left `unsettled_product_request` in the unchanged final audit.
External requests and page errors were zero. The probe used temporary fake
runtime storage and retained no runtime artifacts.

The bounded repair changes only Product E2E: deliberately hold the retry's
activity GET while asserting answer focus, release it to the real local
Backend, wait for the existing page-request settlement gate, require HTTP 200
and `requestfinished` for that exact request, then verify unchanged answer
focus before closing. No product handler, network-error classification,
timeout, or cancellation allowance is changed.

Focused execution of the exact updated retry test block passed 3/3 times,
with `start < response < terminal < close intent`, no audit issues, no page
errors, and no external requests. Existing embedded HTTP-evidence contracts
also pass. Two independent reviewers found no blocking issue in the bounded
38-line test change.

Independent offline negative checks passed: a never-ending GET and HTTP 200
headers without a completed body both timed out at the configured 200 ms
probe deadline; finished HTTP 500, an ordinary abort, and HTTP 200 followed by
abort remained audit failures. A completed HTTP 200 control passed. The drain
did not modify ledger evidence. Removing the wait from an in-memory delayed
terminal simulation failed the exact-request assertion; that mutation may pass
under an already-completed schedule, so the browser probe alone is not claimed
to deterministically reject every no-wait variant.

Final local gates for script blob
`7a7bf03e4471b1d7e98b04f99a0d50f68087608c`:

- Product E2E: 3/3 complete runs, 227/227 checks each, including the controlled
  Tutor retry activity read; restart persistence PASS.
- External requests, unexpected console errors, and page errors: 0 in all
  three runs.
- Route telemetry: 381 declarations, 68 bound requests, 48 ordinary route
  cancellations, 703 independently validated prefetch cancellations, zero
  special precursor-snapshot recoveries, and 30 successful no-content writes.
- Backend: 600 passed, 4 skipped.
- Frontend: Articles 67, References 21, Tutor 22, Graph 29; total 139 passed.
- Production build: PASS, 11 generated pages.
- Workflow policy, suppression policy, secret audit, temporary SBOM validation,
  forbidden-artifact scan, and protected-path diff: PASS.
- Backend, Frontend, dependency, lockfile, and workflow changes: none.

The final local three-run invocation used the same script blob throughout;
only governance text changed while it ran. Replacement exact-SHA main CI and
the subsequent docs-only closure CI remain required. P3-036 is not yet closed.
