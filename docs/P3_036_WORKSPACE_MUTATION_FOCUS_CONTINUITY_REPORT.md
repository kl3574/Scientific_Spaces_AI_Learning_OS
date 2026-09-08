# P3-036 Workspace Mutation Focus Continuity Report

## 1. Status

- Product implementation: **PASS**, historical local evidence below
- Current caller-evidence repair local gates: **PASS**
- Current repair independent final review: **PASS**, two independent reviewers
- Latest exact-SHA repair main CI: **FAILED**, run `34180979475`
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

## 14. Navigation Caller Evidence Repair (2026-09-08)

Baseline: `d80780506fed84d4def4342c904954e9b049f22d`, clean `main`, matching
the cached `origin/main`; no `REWORK.md` or `.audit` exists. Exact-SHA CI
[`34180979475`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34180979475)
passed Backend, Frontend, dependency, workflow/suppression, secret, and SBOM
jobs. Product E2E reached its final audit and rejected two HTTP 200 RSC
`net::ERR_ABORTED` lifecycles. The previous unfinished Tutor activity read did
not recur. This failed run cannot close P3-036.

### Diagnosis And Reproduction

- Shell request A: homepage to `/graph?node_id=concept%3Acrb&q=CRB`,
  start/response/terminal/navigation sequences `2957/2958/2962/2963` in CI.
  A local execution of the unchanged full Shell prefix failed one of two
  runs with the same request identity fields and start sequence, before the
  later modal Back/Forward actions. The failure belongs to the earlier slow
  Graph search activation, not the separately declared same-route CRB visit.
- A minimized execution of the original slow Graph block failed 3/3 times,
  taking 4.16-4.27 seconds each. The rendered destination, focus, and existing
  120-frame delay assertions passed; the unchanged final audit rejected the
  undeclared response-backed cancellation. The request's homepage source is
  an ordinary transition endpoint. No stale-frame exception is needed.
- Reference request B: selected Zotero reference to the CRB Article's second
  reference page, including its exact row fragment. CI sequences were
  `11743/11744/11749/11750` for start/response/navigation/terminal. That caller
  also lacked a declaration/completion pair. Cold and previously loaded Reader
  probes passed 3/3 each locally because the RSC responses fully completed;
  those results do not claim to reproduce B's CI cancellation.
- Temporary three-Article fixture stores, fake providers, and loopback-only
  Chromium were used throughout. External requests and page errors were zero.
  No source, private Zotero, or real/paid Provider was accessed.

### Bounded Repair

The only implementation change is in `scripts/e2e/run_product_e2e.py`:

- Add 15 ordinary Shell declaration/completion pairs covering stale-focus and
  stale-opener navigation, slow Graph, workspace shortcuts and their returns,
  Article Back, and modal query/pathname history.
- Add one exact page-two source-reference return pair, including the fragment.
- Declare before activation using the current page as source; complete only
  after all original semantic/focus assertions and terminal request settlement.
- Require the slow Graph probe's exact observed RSC terminal result and verify
  any cancellation through the existing completed-transition predicate.
- Preserve all original assertions, observers, race injection, product routes,
  data behavior, classifier predicates, timeouts, and error allowances.

An independent bounded caller audit approved this approach. The other missing
pairs are code-proven instrumentation gaps, not claims that each has separately
failed at runtime. The atomic event-time stale-route probe remains unchanged;
it is not treated as an ordinary source override or a proven failure.

### Focused Evidence

The updated slow Graph block passed 3/3 times: two HTTP 200 cancellations each
bound to the exact completed declaration, and one fully finished HTTP 200
control. All three final audits were clean. The embedded HTTP evidence
contract also passed before and after the patch.

An in-memory original-code control rejected an aborted HTTP 200 request, then
correctly accepted a fully finished HTTP 200 request. Its diagnostic driver
incorrectly expected every schedule to abort and stopped on the second case;
this is not evidence of a deterministic all-schedule negative control or a
product regression. No page-two updated-code result was produced by that
interrupted diagnostic invocation.

First repair script blob: `07c9b7911dec77b4de3fabca7c69c4176bd14e59`.
Two independent reviewers passed this snapshot; the second also ran the
embedded HTTP contract and 16 positive / 63 negative offline cases. AST
comparison confirmed only two caller functions changed, with every original
statement retained in order and all ledger/classifier/helper definitions
unchanged. Backend passed 600 tests with 4 skips; Frontend passed 139 tests;
production build passed with 11 generated pages. Workflow, suppression,
secret, temporary SBOM, artifact, and protected-path gates passed. Local
network-dependent dependency auditing remains deferred to exact-SHA CI.

### Full-Run Reader Finding

The first full three-run invocation on that blob did not pass. It reached the
final audit and rejected one different HTTP 200 RSC cancellation on
`reader-fragment-route-owner`: `/session` to
`/articles/crb-formula?from=%2Fsession#reading-tools`. Request, response,
navigation, and terminal sequences were `1733/1734/1738/1739`; navigation
generation advanced from 31 to 32. The earlier Shell and Reference failures
were absent from this final audit. No successful complete-three-run result is
claimed from that invocation.

The original Reader function passed once in isolation with action-level
diagnostic tracing. This does not contradict the full-run failure or prove a
deterministic isolated reproduction. A bounded independent audit identified
seven missing cross-route pairs: Article-outline history return, two guided
reading-tools entries, return to Session, saved-heading entry, and its
Back/Forward round trip.

The current patch adds those seven pairs, for 23 total. The atomic
`focus(); history.back()` action is unchanged. The second guided entry still
opens and closes its modal immediately; settlement occurs only after every
original modal/focus assertion. Hash-only moves and all classifier predicates
remain unchanged. The Reader pair design passed independent review.

Reader repair snapshot: `303715775d02a369907dd8302aee83d5ee0fdfa3`.
The complete updated Reader function passed 3/3 in 54.14-54.88 seconds per
iteration, with 18 route declarations and 1/1/2 bound cancellations. Final
audits, page errors, and external requests were zero in every iteration.

A follow-up bounded audit identified ten further unpaired desktop/mobile
round trips; the adjacent outbound Reader-to-Tutor and Reader-to-Graph links
had the same omission. All 12 now use ordinary existing pairs, retaining full
query/fragment identity and all original UI assertions. These are preventive
instrumentation repairs, not separately reproduced failures. This bounded
review is not a claim that every possible navigation in the script has been
exhaustively classified.

Caller-only script blob: `db3a61543c4acfcc01b2fc5b0783083197383339`.
The patch contains 35 new pairs across three caller functions. No original
source lines were removed; AST comparison confirms every other function and
class, including all classifiers/helpers, is unchanged. The embedded HTTP
evidence contract passes. Replacement full E2E and final snapshot reviews are
in progress. Replacement implementation CI and a separate docs-only closure
CI remain mandatory. No closure or candidate is declared.

### Query-Order Canonicalization Finding

The second full invocation on the 35-caller snapshot failed at the newly
declared Reader-to-Graph completion. The rendered link orders parameters as
`article_id, article_title, return_to, node_id`; Graph canonicalizes them as
`node_id, article_id, article_title, return_to`. All encoded values are
identical. This is current product behavior in `createLearningToolHref` and
`createGraphWorkspaceHref`, not a broken page or permission to globally sort
URL identity. The invocation is not a completed three-run result.

A local Chromium probe using the actual Reader link showed both valid
lifecycles: raw-link RSC HTTP 200 followed by `ERR_ABORTED`, and fully finished
HTTP 200. Declaring the raw URL as a required cancelled route passed the first
case but correctly failed the second, because required cancellations must bind
exactly once. Making that existing cardinality optional would weaken unrelated
evidence and is not the repair.

The subsequent E2E-only repair introduces an explicit `query_order_alias_url`
certificate. It is frozen with source, canonical destination, page, label,
sequence, and generation before activation. Only a different ordering of the
same raw encoded query components is admitted; duplicate decoded keys,
transport parameters, empty separators, changed encoding/values, and changed
non-query URL components are rejected. Completion remains at the exact
canonical URL. Alias aborts additionally need an exact HTTP 200 response,
ordered terminal evidence, and observed canonical navigation without unrelated
intervening routes or declarations. The alias may finish normally without an
abort; duplicate aborts and pending requests fail. Snapshot changes at binding
or final audit fail. Existing default behavior, global URL keys, required
cancelled-route/read counts, cache, prefetch, and static-chunk policies remain
unchanged. This is an opt-in evidence-classification extension and is not
described as an unchanged classifier. No product implementation changed.

The contract regression, real-browser alias probe, replacement full run, and
independent final reviews must pass before any new CI/closure claim.

### Alias Browser And Local Gate Evidence

- Five unthrottled real Reader-to-Graph activations passed with fully finished
  HTTP 200 raw RSC responses and zero error bindings.
- Six further activations with Chromium CPU throttling at 4x and network
  conditions of 30 ms latency / 128,000 bytes per second passed: four finished
  HTTP 200 responses, two HTTP 200 `ERR_ABORTED` responses bound exactly once.
  The latter six used the generation-bound canonical navigation checks and
  combined alias/canonical cancellation ceiling. Every final request audit was
  clean; page errors and external requests were zero.
- Each probe used a fresh browser context and temporary three-Article fake
  runtime; all runtime directories were cleaned on exit. No real source,
  private library, Provider, screenshot, or downloaded content was involved.
- Fresh Backend regression: 600 passed / 4 skipped in 39.05 seconds.
- Fresh Frontend suites: Articles 67, References 21, Tutor 22, Graph 29;
  139 total passed. Fresh Next.js production build passed with 11 pages.
- Workflow and suppression policies, secret scan, temporary SBOM validation,
  artifact scan, and protected-path diff passed. SBOM component counts were
  40 / 239 / 281 with schema validation PASS and forbidden count 0. The first
  SBOM validation invocation used an invalid option; the corrected positional
  invocation passed and both temporary directories were cleaned.
- The artifact-name scan matched only the tracked `.env.example` template,
  not a runtime environment file; secret scan reported zero findings.

These are bounded and supporting results, not a substitute for the required
three complete Product E2E runs or exact-SHA CI.

### Contract Regression

The independent test author added 141 scenarios inside the existing HTTP
evidence contract: 19 positive controls and 122 rejection cases. The complete
contract passed after fixing two newly exposed holes: `urlparse` normalizes
scheme spelling, so the alias check now also preserves the literal non-query
prefix; alias request ownership now requires the recorded frame URL to equal
the owning page URL. These constraints apply only to the opt-in certificate.

The matrix covers absent/finished/aborted alias and canonical requests, exact
response provenance, immutable declarations before and after completion,
missing/deleted snapshots, pending responses, duplicate and combined endpoint
bindings, late requests, canonical navigation generations, unrelated frames,
competing declarations, and exact query encoding. Three valid prefetch controls
retain the existing independent prefetch policy without binding the alias;
three overlong prefetch cases remain failures. Omitted, explicit `None`, and
legacy missing-field declarations retain their original behavior.

The replacement three-run Product E2E invocation uses frozen script blob
`9840c591399ea7cae15a9b9fb1c76c59d8ae5490`; results and final independent
reviews are pending. No Product E2E or CI success is inferred from these pure
contract tests.

The run on `9840c591399ea7cae15a9b9fb1c76c59d8ae5490` was intentionally
interrupted (exit 130) when independent final review found three additional
certificate gaps. It is not passing full-run evidence. The isolated servers
were stopped and temporary runtime data was cleaned. Findings and repairs:

- Deleting an expectation could allow the list-length-based ID to be reused
  and overwrite its private alias snapshot. Declaration now rejects reuse of
  any retained alias registry ID, preserving the missing-declaration failure.
- `urlparse` discards literal tabs/newlines within a URL. Both declared URLs
  now reject literal ASCII controls/whitespace before parsing. Alias request
  URLs also retain literal origin/path spelling and cannot carry a fragment;
  properly encoded values are unaffected.
- Terminal navigation generation was unchecked. Alias evidence now requires
  `declaration <= request <= terminal <= completion` generations and a terminal
  page within the same declared endpoints.

The new literal-tab regression failed before the repair and the entire
contract passed afterward. Eleven further rejection cases cover these findings
and literal request URLs, bringing the matrix to 152 scenarios: 19 positives
and 133 negatives. The replacement full gate and final reviews remain required.

Further independent review found that in-range generations can still disagree
with the collected event order. Alias admission now replays the declaration's
complete ordered navigation window: every recorded event increments one
generation, and request/terminal generations must equal the latest event before
their respective sequences. This follows the existing collector's behavior
without changing it or requiring terminal generation to equal completion.
Three additional rejection cases cover early/late generations and missing
intermediate events; one positive verifies canonical navigation after terminal.
The complete contract passes 156 added scenarios (20 positive / 136 negative).

The last bounded Chromium probe before this event-replay tightening passed
3/3 (two bound HTTP 200 aborts, one finished HTTP 200), with clean final audits
and zero page/external errors. Replacement full E2E is running on script blob
`95feae7950c002127199941e2719832828e87233`; its final result remains pending.

Two independent final reviewers passed this snapshot with no remaining
Critical, Important, or Minor finding. The first independently exercised eight
generation/ordering probes; the second reran the complete 156-scenario contract
and the prior counterexamples. Both confirmed that canonical commit after
terminal remains valid. The second also verified all 35 caller pairs preserve
original code lines, UI assertions, and race timing, and that protected URL,
prefetch/cache, and required-cancellation behavior remains unchanged. These
reviews are code/evidence-model approval, not full E2E or CI completion.

### Final Local Result

Frozen script blob: `95feae7950c002127199941e2719832828e87233`, unchanged
through the final run and subsequent readback.

`uv run --offline --project backend python scripts/e2e/run_product_e2e.py
--repeat 3 --frontend-mode start` completed with exit 0:

- Product E2E: 3/3 complete runs, 227/227 checks in every run.
- Restart persistence: PASS for notes, bookmarks, completed states, and ended
  sessions.
- Chromium: `149.0.7827.55`.
- Unexpected console errors, page errors, and external requests: zero in all
  three runs.
- Route declarations: 486; bound requests: 78; valid route cancellations: 57;
  independently validated prefetch cancellations: 675; successful no-content
  writes: 30. No specialized precursor-snapshot recovery was used.
- Backend 600 passed / 4 skipped; Frontend 139 passed; production build PASS
  with 11 pages; the full HTTP contract including 156 new scenarios PASS.
- Two independent final reviews and local workflow, suppression, secret,
  temporary SBOM, artifact, and protected-path checks PASS.

The temporary output was read back as structured JSON and removed after its
bounded metadata was recorded here. Isolated runtime directories and services
were cleaned; ports 3000/8000 are no longer held by this test. No product,
Backend, Frontend, dependency, lockfile, workflow, or runtime-data change is in
the patch. Network-dependent dependency auditing remains assigned to exact-SHA
CI. The repair is ready for its implementation commit and CI; P3-036 remains
open until implementation and docs-only closure CI succeed.
