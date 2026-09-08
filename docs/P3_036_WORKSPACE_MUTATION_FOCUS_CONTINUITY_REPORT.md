# P3-036 Workspace Mutation Focus Continuity Report

## 1. Status

- Product implementation: **PASS**, latest repair `472350e`
- Current repair local gates: **PASS**, including 3 x 243 Product E2E checks
- Current repair independent final review: **PASS**, two final and one supplementary review
- Latest cumulative exact-SHA main CI: **PASS**, `7332995`, run `34208984649`
- P3-005.2 SBOM transport revision: **IMPLEMENTATION PASS**
- Task closure: **OPEN / CLOSURE CI PENDING**
- Docs-only closure commit `d28fec6` CI: **FAIL**, run `34196981094`
- Docs-only closure commit `55ba624` CI: **FAIL**, run `34205485973`
- Historical Graph rendering incident: **OPEN / UNRESOLVED**, root cause unknown
- Candidate version: not assigned

Sections 2-15 preserve the chronological implementation, failure and repair
evidence. Sections 16-18 record implementation CI, the later closure failure
and failure-only diagnostic. Sections 19-21 record the diagnostic PASS and
subsequent SBOM closure failure. Section 22 is current: the separate security
repair and complete implementation CI pass; the replacement docs-only closure
still needs its own CI. Earlier failures remain failures. No later product
task has started.

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

## 15. Reference Candidate Focus Lifecycle Repair

Date: 2026-09-08. Baseline `d1e26828fe42f2f1c605973b034295c5b6ee80af`.
Exact-SHA run:
`https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34188149037`.
Backend, Frontend build, dependency, workflow/suppression, secret and SBOM jobs
passed. Product E2E failed the existing Matched-focus assertion in structured
reference review, before the final network audit. Its failure must not be
reported as a passing network audit or a closed P3-036. Docker/release jobs
were skipped under normal-main policy. No CI artifacts were uploaded.

### RED And Scope

An isolated three-Article fake runtime reproduced the defect without the prior
identity/retry sequence. Repeated All/Matched navigation passed 12/12 at CPU1;
CPU4 failed at switch 10 (All), CPU8 at switch 5 (Matched). The current filter's
focus callback ran while disabled, did nothing, consumed the intent, and was
followed by Shell main focus. On CPU8 the failing callback ran at 5416.3 ms,
the button re-enabled at 5419 ms, and Shell main received focus at 5580 ms.
The event sequence distinguishes the cause from stale All stealing focus or a
test timeout. All three contexts had zero external or unexpected errors.

Independent review confirmed the original allowlist did not include this
component. `docs/tasks/P3-036.1_REFERENCE_CANDIDATE_FOCUS_LIFECYCLE.md` now
explicitly bounds the product repair under the owner's automatic-execution
instruction. It does not expand API, data, matching, Shell or frozen M1 scope.

### Repair And Regression

- Candidate focus waits for navigation settlement and checks an enabled,
  connected target before consuming intent in the animation callback.
- Exact intent identity prevents stale same-filter cleanup from consuming a
  newer operation. Local reference/URL ownership and later interaction,
  history/hash, meaningful focus and unmount cancellation prevent stale work.
- Animation cleanup cancels only the frame, not the current operation.
- Existing result/detail effects, request flow, URL/history and HTTP audit
  policy remain unchanged.
- The two added pure tests initially failed compilation against the old helper
  signature, then passed with exact-token support. The original browser RED is
  the behavioral pre-fix evidence, not that compilation failure.
- Independent review found a blanket Shell-main exception in the first patch.
  A separate real-browser negative reproduced `main_still_focused=false`,
  actual focus `candidate-filter-all`, after explicit main focus during retry.
  That exception was removed; this negative remains in regression coverage.

The first new browser invocation completed route switches and six retry cases
but failed on a newly authored, nonexistent navigation test locator. That test
locator was corrected to the existing Primary navigation role; no product or
acceptance behavior was changed. Replacement focused validation passed all
32 route switches, seven retry scenarios and all 21 existing Reference checks,
with zero external, console-audit or page errors. This was before the final
main-focus exception removal and additional cancellation coverage; it is not
final full-suite evidence.

Backend: 600 passed / 4 skipped (38.88 seconds). Focused Frontend: 141 passed
(Articles 67, References 23, Tutor 22, Graph 29). Production build: PASS,
Next.js 15.5.21, 11 routes. Workflow/suppression and secret checks: PASS.
Temporary SBOM generation/validation: PASS, 40 Backend / 239 Frontend / 281
combined, forbidden fields zero; all temporary outputs removed. The initial
SBOM validation invocation incorrectly passed an individual file instead of
its output directory and failed; the corrected directory invocation passed.

Final expanded browser regression, three-run Product E2E, final independent
reviews, and implementation/closure exact-SHA CI remain required. No closure
or later GUI task is claimed here.

The additional scroll diagnostic found native layout adjustment, not a stale
programmatic scroll: both wheel/hash cases changed `scrollY` from 313 to 365
while document height grew from 1213 to 1305 (viewport 900). Forwarding
`scrollIntoView` observations were empty and focus remained unchanged. The
new regression therefore checks zero completion-time programmatic focus or
scroll calls after those interactions, instead of assuming fixed `scrollY`
across loading/result layout changes. Existing assertions and HTTP admission
remain unchanged; AST comparison confirms only the main iteration gains a new
helper call and the new lifecycle helper is added.

The expanded browser gate passed all 16 checks (32 switches and 12 retry
scenarios), including main/filter/wheel/hash behavior. Independent review then
identified two limitations in the new RAF test: held callbacks lost their
original cancellation IDs on release, and immediate retry focus could satisfy
the final assertion without deferred execution. The three-run invocation on
script blob `f8657096ae420558abc20362f589e214dc132cc7` was deliberately
interrupted with exit 130 for this test repair. It is not passing full-suite
evidence. Servers were stopped and no output/artifact remained.

The RAF gate now keeps original-to-released cancellation mapping and uses the
actual delivered frame timestamp. A forwarding observer installed after the
synchronous retry focus requires exactly one deferred, enabled All-filter
focus call. This tests cancellation plus newer same-filter retry; preservation
of a still-current intent across effect cleanup is additionally supported by
the consume-in-callback code and the navigation lifecycle regression.

Desktop 1440x900 and mobile 390x844 screenshots were inspected in a separate
read-only fixture context: the Matched focus ring is visible, content fits,
and no horizontal overflow or browser/network error was observed. Both owned
temporary screenshots were deleted immediately after inspection.

The final focused invocation on script blob
`589b7d9c58ba75d7af871a5abeaf5dba0615f980` passed all 16 checks (32 route
switches, 12 retry scenarios), with zero external requests and empty final
console/page audits. Both independent final reviewers approved that exact
snapshot with no blocking product or test finding; one independently passed
eight RAF cancellation/timestamp cases. The replacement three-run gate uses
this unchanged snapshot; its result and exact-SHA CI are still pending.

### Replacement Full Gate Result

The replacement full invocation on `589b7d9c58ba75d7af871a5abeaf5dba0615f980`
completed with exit 1, before the new candidate helper executes. At Reader
resume (`_run_single_iteration`, line 3740), the expected Article heading was
absent and the existing error boundary displayed a failed load for webpack
chunk 406:
`/_next/static/chunks/app/articles/%5Bid%5D/page-30d87e88b4a1b9a5.js`.
406 is the bundle identifier, not an observed HTTP response status. The
failure report has no request-ledger evidence, so its precise transport and
document attribution remain unknown.

The exact file exists (108250 bytes), with mtime 05:13:43 UTC and BUILD_ID
mtime 05:13:45 UTC, before the full run. No build ran during that invocation;
focused test runners use their own temporary output directories. The bounded
Frontend server log shows normal startup, not a missing-file exception.

Twelve fresh isolated Dashboard-to-Reader probes (CPU1/4 alternating) all
rendered the Reader. Every observed request for the exact Article chunk
finished HTTP 200 with no request failure; external requests and page errors
were zero. This excludes a persistently missing asset in those probes, but
does not establish the cause or dismiss the full-run failure.

Independent read-only diagnosis identified the un-settled hard-navigation
boundary after Dashboard DOM assertions as a hypothesis. The request ledger
uses distinct request GUIDs rather than URL merging. Page-error labels use
the current URL at delivery, so original-document attribution needs loader
evidence. The next bounded replay executes the original iteration prefix
through the failed assertion and observes chunk CDP loader/frame/document
metadata. It is diagnostic-only, not a completed Product E2E run.

P3-036 and P3-036.1 remain open. No implementation commit, push, closure,
tag or Release has been performed for this patch.

The diagnostic prefix replay completed with exit 0 and 53 existing checks
through the previously failed Reader heading assertion. The final URL was
`/articles/crb-formula#%E6%95%B0%E5%80%BC%E6%A3%80%E6%9F%A5`.
The final Reader chunk request was recorded as HTTP 200, finished, no failure;
page errors were empty. This single replay did not reproduce the failure and
did not run the full suite or final HTTP audit. Its extra raw CDP observer was
attached only to the original `primary` page: the original scenario replaces
that page with `graph-reload` before the failing boundary. The next diagnostic
must also attach to that replacement page; no final-loader provenance is
claimed from the primary-only CDP output. The existing request ledger does
include the replacement-page request.

The failed full-run JSON was reduced to the diagnostic metadata above and
removed. All owned test services, runtime directories and screenshots were
cleaned. The next action is targeted Reader chunk-lifecycle diagnosis, not a
blind CI rerun, an assertion relaxation, or publication of this partial gate.

### Replacement-page Loader Diagnostic

The next isolated diagnostic completed with exit 0. Raw CDP was attached to
`graph-reload`, the replacement page that reaches the failed boundary. The
unaltered 53-check prefix passed, followed by 20 Dashboard-to-Reader hard
navigations. Ten used CPU1; ten used CPU4 plus 60 ms network latency and
128000 bytes/second throughput. CPU and network settings changed together, so
this is boundary/stress evidence, not independent attribution to either one.

Every observed Article chunk returned HTTP 200 and finished; MIME type was
`application/javascript`. The diagnostic recorded each document URL, loader
and frame identity. All 20 transitions rendered the expected Reader heading
and page errors remained empty. No root cause was reproduced. This run did
not execute the full suite or its final HTTP audit. Temporary fixture data and
servers were removed by the runner; no diagnostic output file was persisted.

The next invocation executes all original Product E2E checks three times on
the unchanged script blob `589b7d9c58ba75d7af871a5abeaf5dba0615f980`.
An in-memory wrapper adds Reader-chunk CDP metadata and a bounded whitelist of
existing request-ledger fields if the original iteration raises. It snapshots
before server teardown and re-raises the original exception. No assertions,
timeouts, response bodies, request behavior or admission rules are changed.
No source diagnostic helper, downloaded content, headers or private data are
persisted. The result is pending; both tasks remain open.

### Replacement Complete Gate Result

The invocation above completed with exit 0 on 2026-09-08. All three original
iterations passed 243 checks each, including the new candidate lifecycle
helper and the unchanged final HTTP/error audit. Chromium: 149.0.7827.55.
The runner's existing restart check also passed bookmarks, completed states,
ended sessions and notes. This is a complete instrumented local run, not just
a prefix replay; ordinary uninstrumented exact-SHA CI is still required.

| Metric | Result |
| --- | --- |
| Complete Product E2E iterations | 3/3 PASS |
| Checks in each iteration | 243/243 PASS |
| Candidate route switches / retry cases per iteration | 32 / 12 PASS |
| Unexpected console / page errors | 0 / 0 in each iteration |
| External requests | 0 |
| Restart persistence | PASS |
| Mobile page widths | 390/390 for all six reported workspaces |
| Article static chunk cancellations | 0 |
| Controlled route cancellations | 56, admitted by unchanged strict evidence rules |
| Ordinary route declarations | 591 |
| Controlled route-read cancellations | 12 |
| Successful no-content responses | 30 |

The original Reader chunk error did not recur. No Reader or runtime loader
fix was made and no root-cause resolution is claimed. The remaining risk is
intermittent chunk loading under a long browser workflow; any recurrence must
retain document/request evidence and fail the existing gate rather than be
silently retried or suppressed.

Fresh corroborating checks in the same worktree:

- Backend: 600 passed, 4 skipped in 39.81 seconds, offline.
- Frontend: Articles 67, References 23, Tutor 22, Graph 29; 141 total PASS.
- Fresh production build after test services stopped: PASS, Next.js 15.5.21,
  11 generated routes; no build ran during the browser suite.
- Workflow/suppression and secret audit: PASS, zero findings.
- Fresh temporary SBOM structural/lock coverage: PASS, 40/239/281 components,
  zero forbidden fields. This offline invocation did not rerun online schema
  validation; the new exact-SHA CI must validate the schema and dependencies.
- No Backend, workflow, dependency or lockfile diff. Artifact-name matches are
  only existing fixture files and `crawler/cache.py`; none is modified.
- The owned browser/runtime/server processes exited and their temporary
  directory was removed. No HTML, screenshots, PDF, profile, trace, raw ledger
  or JSON result artifact is added to Git.

The further independent final diff review checked the exact component/helper/
test/runner blobs `433d4c1`, `fde872a5`, `6944266`, `589b7d9c` and found no
Critical or Important issue. Its nonblocking request to distinguish the prior
failed run from the active replacement run has been incorporated into the
task pointers. The two prior final reviews remain recorded above.

The bounded `fix: preserve reference candidate filter focus` implementation
commit and non-force push are ready. P3-036 and P3-036.1 stay open until the
implementation exact-SHA main CI and separate docs-only closure CI pass. No
candidate version, tag, Release or later product task is declared complete.

### Implementation Publication And Pending CI

- Commit: `472350ede8bc20651928ebbc5d88abb206ee6b47`.
- Message: `fix: preserve reference candidate filter focus`.
- Non-force push to `main`: PASS; local HEAD and cached `origin/main` agree.
- Exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34194053415`.
- Latest readback: IN PROGRESS. Backend, Frontend, dependency, workflow,
  secret and SBOM jobs PASS. Product E2E has finished setup/build/Chromium
  installation and is executing its three-run step. Normal-main Docker is
  skipped by policy. A successful terminal E2E/overall result is not inferred.
- Both tasks remain open. A separate docs-only closure commit and its own
  exact-SHA CI are still required; no tag, Release or candidate operation.

### Follow-on GUI Diagnostic, Not An Implementation

An independent read-only GUI review identified that local Tutor source links
leave the current tab, while answer/quiz state resides in the Tutor component.
The next bounded diagnostic used the existing three-Article temporary runtime
and fake providers on the pushed commit. No source or private Zotero access,
real provider, source edits or persisted diagnostic artifacts were involved.

Four real Chromium cases (1440/390 pixels, Explain/submitted Quiz) performed:
select CRB, generate an answer or score, click `Open local article`, inspect
the correct Reader, then browser Back. All four returned to `/tutor` without
the prior answer/quiz score or selected Article. The source link had no target
attribute. No additional Tutor POST, external request or page error occurred
during source inspection and return. Temporary runtime and servers were
removed. This is a reproduced continuity defect, not a failed P3-036 focus
assertion and not a claim that inline Markdown citations were already tested.

Recommended separate follow-on: preserve Tutor work while inspecting local
citations, including source-list and inline Markdown links, with an explicit
separate-tab affordance. Preserve safe URLs/fragments and same-document
anchors; intentional Return-to-Article/Concept navigation remains unchanged.
Verify retained answers, quiz selections/score and zero extra Tutor generation
or activity writes through desktop/mobile rendered interactions. No Backend,
persistence, provider or matching change is needed by this proposal. Stage it
after P3-036 closure; no P3-037 implementation has occurred in this commit.

The follow-up single-variable browser prototype changed only the rendered
source link's `target`/`rel` attributes in the temporary page, not source files.
The same four viewport/mode cases all preserved the originating Tutor URL,
answer or submitted Quiz score/selections, and selected Article while the
correct Reader opened separately. Each child had `window.opener === null`;
closing it returned to the existing Tutor page. Additional Tutor POSTs,
external requests, unexpected context pages and page errors were zero. All
temporary servers/data were removed. This supports the proposed navigation
mechanism; it is not a shipped fix or full citation regression evidence.

An independent design review supports a separate bounded P3-037 once both
P3-036 CI gates pass. Important contract details for its implementation:

- Classify accepted hash-only anchors versus accepted document links, not
  case-sensitive HTTP prefixes. The current sanitizer preserves accepted
  mixed-case HTTP(S) spelling; those must still open a separate tab.
- Preserve `getSafeTutorMarkdownHref` admission and sanitized hrefs exactly;
  do not add arbitrary relative routes or normalize URLs. Rejected links
  remain noninteractive. An admitted URL does not prove the Article exists.
- Keep native anchors/Next Link, explicit new-tab wording, and
  `noopener noreferrer`; no `window.open`, named-tab reuse, or same-tab fallback.
- Test source-list and inline answer links, submitted-Quiz source links,
  disclosure expansion, pointer/keyboard activation, query/fragment fidelity,
  mixed-case absolute loopback URLs, existing hash anchors, and unchanged
  Article/Concept Return actions. Quiz explanations are plain text, not an
  inline-Markdown seam. Cover narrow and short-landscape layout as well.
- Settle generation and activity before request/state baselines, observe both
  pages before activation, register only the exact expected popup, settle it
  before closing, and retain strict network/error auditing.
- The scope preserves a live originating tab, not state across refresh, tab
  closure or browser eviction. No state/persistence/provider change is implied.

The active implementation CI remains IN PROGRESS. One `gh run watch`
observation ended with a TLS handshake timeout; a subsequent read of the same
run confirmed Product E2E still executing. The workflow was not restarted.
Its completed jobs report a GitHub Actions runtime-deprecation annotation;
those jobs pass, and workflow-pin maintenance is outside this GUI patch.

## 16. Final Implementation CI And Closure Handoff

Implementation `472350ede8bc20651928ebbc5d88abb206ee6b47` passed exact-SHA
main CI run
[`34194053415`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34194053415).
The run is completed with conclusion `success`. Backend pytest, Frontend
build, Product E2E, dependency audit, workflow policy, secret audit and SBOM
validation all PASS. Docker compose smoke and release-evidence dry-run are
skipped under normal-main policy; no Docker or release claim is inferred.

The completed Product E2E job's JSON was parsed from its log in memory:

- Chromium: 149.0.7827.55.
- Ordinary, uninstrumented complete runs: 3/3 PASS, 243 checks each, all true.
- Unexpected console/page errors and external requests: 0 in each run.
- Article static-chunk cancellations: 0.
- Restart persistence: bookmarks, completed states, ended sessions and notes PASS.
- Final artifact API readback: `total_count=0`.

This corroborates the complete local run without the temporary diagnostic
wrapper. The earlier unexplained Reader chunk failure remains historical risk,
not a claimed loader fix. Actions runtime-deprecation annotations remain a
separate maintenance risk; they did not fail the required jobs.

No additional product change is needed for P3-036/P3-036.1 on this evidence.
The remaining action is `docs: close P3-036 mutation focus continuity`,
non-force push and verification of that exact documentation commit's main CI.
Status is deliberately CLOSURE CI PENDING until its terminal success is read
back. The user-authorized autonomous workflow requires no repeated plan
confirmation. Only then stage the independently reviewed Tutor citation task;
its live-tab scope, prototype evidence and limitations are recorded above.

## 17. Closure CI Graph Map Failure

Docs-only commit `d28fec6e428b6b8e0381d4afb96e988245e25ec8` was independently
reviewed, committed and non-force pushed. Local HEAD, cached origin/main and
remote main agreed; worktree was clean. Its diff from `472350e` contains only
nine Markdown files. Product, Backend, runner, dependency and workflow blobs
are unchanged. Secret/workflow/suppression and artifact checks pass.

Exact-SHA run
[`34196981094`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34196981094)
completed with failure. Product E2E job `101966789398` fails the original
selected-Article visibility assertion at `run_product_e2e.py:4305`, after
keyboard selection of an Article node in the Attention concept map. The URL
and details change; the accessibility snapshot reports 7 nodes / 6
relationships and the selected Article details ready, but the map exposes
only images, minimap and controls, not node buttons. Backend, Frontend,
dependency, workflow, secret and SBOM jobs pass. Normal-main Docker/release
jobs are skipped. This is a terminal workflow failure, not an observer timeout.

The failure precedes the final request audit. No complete three-run PASS,
restart-persistence PASS or clean final HTTP audit is inferred from this run.
The prior successful implementation CI remains evidence for its exact run,
not proof that this intermittent Graph failure is harmless or resolved.

An isolated local replay preserves the relevant public interactions: load the
Attention concept, open Knowledge context, focus a graph edge, open/close
global Search with the keyboard, and select an Article with Enter. Fifteen
fresh Chromium contexts, five each at CPU1/4/8, all render the selected Article
within the unchanged 30-second assertion. External requests, console and page
errors are zero. These minimal cases do not reproduce the CI failure and do
not replace the complete gate. Temporary fixture runtime and servers are
removed; no screenshot, HTML or raw diagnostic artifact is persisted.

Next diagnosis replays the original E2E prelude through the exact failing
assertion and captures bounded node/container geometry and visibility on
failure. An independent read-only review examines the React Flow/map lifecycle.
No root cause, product repair, assertion change or workflow rerun is claimed.
P3-036 remains open; P3-036.1 implementation passed but its parent closure is
blocked. The reviewed Tutor citation task remains unstaged.

### Original Prelude And Measurement-order Probes

The next local diagnostic parsed the runner with Python AST and retained every
original statement through `_complete_expected_route_transition(page,
graph_article_selection)` at line 4309. That prefix PASS includes the failing
30-second selected-Article assertion and route settlement. Node wrappers have
positive dimensions and visible styles. It does not execute later assertions,
the final audit or restart persistence, and is not a full-suite PASS.

Independent source review identifies that fresh callback identities rebuild
controlled React Flow node objects without measured dimensions. Installed
`@xyflow/system` discards previous measurements for those new objects; an
ordinary re-observation can recover them. This is not yet the proven cause of
the CI failure. Each remounted React Flow has an isolated internal provider,
so an old instance clearing the new store is not supported without additional
store-identity evidence. ARIA absence alone cannot distinguish hidden nodes
from missing nodes.

Two further diagnostic matrices each pass 12/12: CPU1/4/8, with the pending
Article detail response released before, after, in a microtask, or in the next
animation frame relative to the first new map-node ResizeObserver callback.
The first matrix gates fetch completion, the second gates already parsed JSON.
Response payloads are unchanged. Every case receives another seven-node
measurement delivery and displays the selected Article. These negative
replays do not establish root-cause resolution. All external requests and
unexpected console/page errors are zero; temporary runtime and servers are
removed.

The next bounded action is evidence-only failure capture at the original
Graph assertion: geometry/visibility/count metadata, no HTML, labels, body,
input, headers, query, screenshot or trace. Capture must never replace the
original exception or turn a failure into PASS. Independent review and
targeted positive/negative diagnostic tests precede publication. A resulting
exact-SHA run gathers missing CI evidence; no blind rerun, speculative Graph
implementation change or closure claim is authorized by these results.

## 18. Failure-only Graph Diagnostic

The reviewed change wraps only the existing selected-Article visibility
assertion. Its locator, 30-second timeout, following route settlement and all
success-path statements remain unchanged. After an `AssertionError`, one
synchronous DOM evaluation adds a bounded diagnostic note and rethrows the
same exception. Capture, serialization, helper and annotation failures cannot
replace that original assertion. This is evidence infrastructure, not a Graph
product fix; P3-036 remains REOPENED / GRAPH MAP DIAGNOSIS.

The note contains finite numeric geometry, fixed visibility/display/type
enums, rendered `aria-pressed` selection booleans, handle counts, model counts
and at most 25 node samples. It omits labels, Article content, node IDs,
HTML, input values, headers, URLs/query strings, screenshots and traces.
Unknown error classes are reduced to `Exception`; capture exception messages
are not serialized. The original assertion traceback is unchanged and is
not claimed to be content-free. Post-failure layout reads cannot reconstruct
the preceding render interleaving; synchronous evaluation has no separate
hard wall-clock deadline.

The sole additional test file is
`backend/tests/test_e2e_graph_failure_diagnostics.py`, explicitly added to the
canonical allowlist. It uses the production assertion's AST, not a separately
written imitation. Existing pytest collection covers it without configuration
or workflow changes. Backend application, Frontend, frozen M1, APIs, data,
dependencies and lockfiles are unchanged by this diagnostic patch.

### Local Validation

- Runner blob: `2e05ec856b7c1863e633427ba0d969cab4bf1d7d`.
- Diagnostic test blob: `ca4add37633c0db2d4dc3461afe99f87c9b801ab`.
- Diagnostic contracts: 29 PASS, including original exception identity,
  existing notes, success-path silence, non-Assertion errors, failed capture,
  non-finite JSON, persistent serializer failure, unknown/long exception
  classes, failing helper and failing annotation.
- Fresh final Backend command:
  `uv run --offline --project backend --extra dev pytest -q`:
  **629 passed, 4 skipped, 4 warnings in 36.51s**. The warnings concern two
  pre-existing invalid escape sequences in the runner, surfaced by its new
  AST/runpy tests; no unrelated escape cleanup is included.
- Fresh Frontend suites: Articles 67, References 23, Tutor 22, Graph 29,
  **141 PASS** total.
- Fresh `npm run build`: PASS, Next.js 15.5.21, 11 generated routes.
- Removing only the new helper and unwrapping only the failure-note try block
  yields an AST identical to the HEAD runner, ignoring source positions.
- `_verify_http_error_evidence_contract()`: PASS, unchanged admission rules.
- Workflow policy: PASS, 19 pinned actions, full permission coverage.
- Suppression validation: PASS, zero dependency/secret suppressions.
- Secret audit: PASS, zero credible/reported/suppressed findings.
- Protected implementation paths: unchanged. Runtime artifact path scan finds
  only the unchanged, tracked `.env.example` template; no runtime/private
  artifact is added. Final staged checks remain required before publication.

Prior browser validation of the same DOM projection used isolated temporary
fake runtime and Chromium 149.0.7827.55. Healthy three-node geometry and rendered
selection were correct; a hidden wrapper remained distinguishable from zero
geometry; 31 synthetic nodes produced exactly 25 samples and a truncation flag.
Injected sensitive sentinel values did not enter the note. External requests,
console and page errors were zero, and temporary servers/data were removed.
Static schema tests do not substitute for this browser evidence.

An additional negative replay used real Graph search typing without submitting,
at CPU1/4/8 with three batches of 155 keystrokes each. All nine batches retained
the selected Article. No ResizeObserver/fetch interception was used in that
probe. Like the original prefix and measurement-order probes, this does not
reproduce or resolve the CI failure.

Independent final code review approves the exact runner and test blobs with
no remaining Critical/Important finding. Review did not independently rerun
the reported browser results. Publication requires final staged secret/artifact
and diff checks, then a non-force push and
exact-SHA CI readback. No new complete local three-run Product E2E, root-cause
repair, closure PASS or next-task implementation is claimed by this section.

## 19. Complete Diagnostic Commit Evidence

Commit `e2ec5e8f2b7682303bd1ca9f3e5ded94f3d8966b`
(`test: capture graph map failure evidence`) was committed and non-force
pushed after independent code/documentation review and staged safety checks.
It changes nine Markdown files, the one failure-note wrapper/helper and its
29 offline regression contracts. No Frontend or Backend application code,
dependency, workflow, provider, storage or frozen M1 implementation changes.

The exact committed runner then completed a fresh local invocation equivalent
to `uv run --offline --project backend python scripts/e2e/run_product_e2e.py
--repeat 3`, with production Next.js startup. Only final JSON presentation was
summarized in memory; the runner, assertions and audits were unmodified:

- Chromium 149.0.7827.55; 3/3 complete runs, 243 checks each, all true.
- External requests, unexpected console errors and page errors: 0 per run.
- Article static-chunk cancellations: 0. Declared route/prefetch cancellations
  remain subject to the unchanged strict ledger, not treated as raw errors.
- Restart persistence: bookmark, completed states, ended sessions and note PASS.
- Temporary runtime and owned servers removed; no result file persisted.

Exact-SHA main CI
[`34201705175`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34201705175)
completed with `success`. Readback confirmed the exact commit above. Backend,
Frontend, Product E2E, workflow policy, dependency audit, secret audit and SBOM
validation all PASS. Normal-main Docker compose and release-evidence jobs are
skipped as designed; this is not new Docker/release evidence.

Product E2E job `101981756711` JSON was parsed from completed logs in memory:
3/3 ordinary runs, 243 checks each, restart persistence PASS, zero external
requests or unexpected console/page errors. The artifact API reports
`total_count=0`. Live remote main and local HEAD agreed; worktree was clean.
Two observer invocations encountered TLS/EOF read failures; reading the same
run confirmed it remained active. No workflow restart was used to obtain PASS.

### Zero-layout Recovery A/B

A separate bounded experiment compared normal Article-map mounting with
short-lived zero layout, at CPU1/4/8. Both arms used the same observer/style
metadata instrumentation and original public map-selection interaction. Only
the treatment added a temporary browser-memory CSS rule hiding the newly
selected Article canvas. It confirmed seven wrappers and zero renderer
offsets, retained zero layout for two animation frames, then removed the rule
before the original 30-second visibility assertion. No response, payload,
viewport or product-source change was made.

All six cases PASS. Each treatment records nine zero-size observer entries
followed by nine positive entries for the current map generation; all seven
wrappers become visible with one selected Article. No event-cap truncation,
external requests or unexpected console/page errors occurred. Temporary
runtime, styles and servers were removed. This is bounded recovery evidence
under instrumentation, not an exact historical prelude replay or proof of the
old CI interleaving. Zero-layout initialization alone is insufficient to
reproduce the incident in these exercised sequences.

## 20. Reviewed Closure Candidate And Open Incident

Two independent read-only reviewers separately examined the unchanged
canonical acceptance and the diagnostic implementation/test boundaries.
Both support preparing a focused docs-only closure candidate; neither calls
the Graph incident repaired. Their code/spec checks were independent; latest
runtime outcomes were supplied evidence, not independently rerun by reviewers.
The parent runner performed and read back those executions as recorded above.

Canonical PASS items 8-9 still require all complete local, review and safety
gates, plus the closure commit's own exact-SHA CI and a clean synchronized
branch. The historical failure followed the explicit context-visible-focus
check; it failed selected-node visibility, not that focus-owner check. No
known required focus-owner defect is deferred by this disposition. All
original visibility/focus assertions and HTTP/error admission remain binding.
This decision does not alter acceptance or introduce conditional closure.

Prepare `docs: close P3-036 mutation focus continuity` and verify its own CI.
Status remains **OPEN / CLOSURE CI PENDING**, not PASS / CLOSED, until terminal
success is read back. Any required failure stops closure and returns to
evidence-directed diagnosis. A new failure is not addressed by selecting a
passing unchanged-SHA rerun. No later implementation is staged before that gate.

Open incident record:

- Incident: intermittent selected-Article Graph map visibility failure.
- Status: OPEN / UNRESOLVED; root cause UNKNOWN; no Graph product repair.
- Evidence: failed `d28fec6` run `34196981094`, job `101966789398`; updated
  Article details and seven-node counts, absent node buttons in ARIA, missing
  contemporaneous geometry. That run remains FAILED.
- Impact: a Graph map may fail to expose its selected node. Frequency and
  causal trigger are not established; it is not classified as harmless.
- Owner: the active platform/GUI maintenance workstream, beyond focused
  mutation-focus closure. No release or universal reliability claim is made.
- Recurrence response: retain the original failing assertion and bounded note;
  stop the affected required gate, classify hidden/missing/off-canvas geometry,
  and review a bounded repair only when causal evidence supports it. If the
  snapshot is insufficient, capture generation-bound measurement history in a
  separately reviewed probe. No speculative product fix or assertion relaxation.
- Follow-up: inspect this checkpoint in subsequent ordinary CI. Negative local
  and current CI runs establish non-reproduction only; closure of P3-036 does
  not close this incident.

### Next GUI Candidate Revalidated

Before staging any implementation, four fresh fake-runtime browser cases at
the current commit checked desktop 1440 and mobile 390, each with Explain and
submitted Quiz. Article selection was made through the visible picker. In
all four cases, clicking `Open local article` uses the same tab; Back loses
the selected Article and answer or Quiz score. Initial generation/activity
POST count was two per case, extra Tutor POSTs on the round trip zero;
external requests and unexpected console/page errors were zero. Temporary
runtime and servers were removed. This corroborates the bounded Tutor
citation-continuity candidate in section 15, not a shipped fix.

## 21. Closure CI Blocked By Schema Transport

Docs-only commit `55ba624951df30c5fe803dcaebb3213185010f1c` was non-force
pushed; exact-SHA run
[`34205485973`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34205485973)
completed FAILURE. SBOM job `101993861976` generated 40 Backend / 239 Frontend /
281 combined components successfully, then failed before schema validation:
`CycloneDX schema unavailable: HTTPError`, exit 2. The status code and external
cause were not logged; neither quota nor HTTP 403 is established.

The other six required jobs PASS: Backend, Frontend, Product E2E, dependency,
secret and workflow policy. Product E2E job `101993862003` completed JSON was
parsed from logs in memory: Chromium 149.0.7827.55, 3/3 ordinary runs, 243/243
checks each, bookmark/completed-state/ended-session/note restart PASS, zero
external requests, unexpected console/page errors or static-chunk cancellations.
Docker/release jobs were skipped by normal-main policy. Uploaded artifact count
is zero by the run artifact API. The run remains failed,
not a successful or conditional closure; no blind rerun was requested.

P3-036 is **OPEN / CI BLOCKED**. Independently reviewed P3-005.2 addresses
only the schema transport and its ordinary-CI regressions, using the existing
official alternate and unchanged hash, validator and security gates. Its
canonical task/report separately bind this security scope. P3-036 product
acceptance and all E2E assertions remain unchanged. Only successful repair
CI and a subsequent docs-only closure CI permit parent closure. The Graph
incident remains OPEN / UNRESOLVED; Tutor implementation is not staged.

## 22. Security Repair PASS And Replacement Closure Candidate

Separate P3-005.2 commit `73329956a6a69cf738e42f571df8b924aacf3deb`
(`fix: add pinned SBOM schema transport fallback`) was non-force pushed after
production-path RED/GREEN tests, independent security review and staged safety
checks. It changes the schema downloader, 42 offline regressions and status/
evidence documents only. Product, E2E runner, workflow, schema/validator pins,
dependencies, source/corpus and frozen API/M1 paths are unchanged.

Exact-SHA main CI
[`34208984649`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34208984649)
is terminal SUCCESS, all seven required jobs PASS. Normal-main Docker and
release evidence jobs are skipped as designed. Uploaded artifacts: 0.

- Local Backend: 671 passed, 4 skipped, 4 existing warnings, 38.75s.
- CI Backend: 667 passed, 8 skipped, 4 warnings, 84.04s. Four extra skips
  are existing Node-renderer tests needing Frontend dependencies absent in
  the Backend job; these pass locally. All 42 new tests execute in CI.
- Fresh local production build: PASS, 11 generated routes; CI Frontend PASS.
- Existing security tests 17 PASS, workflow/suppression/secret gates PASS;
  actual full temporary SBOM/schema CLI PASS, generated data removed.
- CI Product E2E `102005190265`: 3/3 complete runs, 243/243 checks each,
  Chromium 149.0.7827.55, all restart-persistence checks PASS, zero external
  requests, unexpected console/page errors or static-chunk cancellations.
- Final CI JSON was parsed in memory, not saved. Observer TLS timeouts were
  recovered by reading the same run/job; no workflow rerun was used.
- Local/cached/live remote main agree at the implementation commit; worktree
  was clean before this docs-only candidate.

The current SBOM CI takes the healthy API route. A separate local controlled
primary-outage probe verifies actual official raw HTTP 200 and unchanged
digest/full validator PASS. This establishes fallback viability, not the
unlogged original HTTP cause. The earlier failed run stays FAILED. Full
security details and cleanup-boundary regressions are in the P3-005.2 report.

Prepare the independently reviewed **docs-only** closure candidate, keeping
P3-036 **OPEN / CLOSURE CI PENDING** until its own exact-SHA main CI succeeds.
No canonical acceptance, required job, assertion, error admission, product or
test file is changed by this closure. The historical Graph incident stays
OPEN / UNRESOLVED under section 20, root cause UNKNOWN. Any required closure
failure returns to diagnosis. No candidate, tag or Release is assigned.

Two independent read-only final documentation reviews approve exactly the
10 Markdown changes, with zero Critical/Important findings on evidence/
consistency and scope/acceptance respectively. Runtime and CI figures were
provided by the parent runner's executions, not rerun by those reviewers.
This approves publication of the candidate, not its still-unexecuted closure CI.

### Tutor Candidate: Expanded Temporary Prototype

While implementation CI ran, a temporary fake-runtime Chromium prototype
replaced only the selected citation DOM anchor with a native link using
`target="_blank"`, `rel="noopener noreferrer"` and a visible ` (new tab)` cue.
It changed no product file, provider or persistent production data. The current
same-tab defect from section 20 remains unshipped; this is design evidence,
not validation of a new compiled component.

22/22 cases PASS:

- Core 12: 1440x1000 and 390x844, Explain source list / Explain inline /
  submitted Quiz source list, each pointer and Tab/Enter.
- Six further cases: Derive, Q&A and Research inline sources at both widths.
- Four layout cases: Explain and Quiz source list by keyboard at 320x844 and
  720x450.

All use the public Article picker and populated Graph key `concept:crb`, five
sources with disclosure expanded, and generation/activity POSTs settled first.
After inspecting the correct Reader and closing the one new page, parent
prompt, mode, selected Article, actual Graph input value, answer/Quiz choices/
score, disclosure, URL/history, scroll and initiating-link focus match their
pre-click snapshots. Raw href remains unchanged, resolved destination including
inline repeated query parameters and fragment is exact, `window.opener` is
null, and the source fits the viewport without page overflow. Extra Tutor
POSTs, unexpected pages, console/page errors and external requests: 0.
Observers were attached before popup activation and both pages settled before
teardown. All temporary stores, browser contexts and owned servers were removed.

An earlier 12-case probe did not read the actual Graph input because it assumed
an aria-label attribute. The expanded probe uses the public named textbox.
Its first attempt then exposed an exact `get_by_label` lookup limitation after
textarea value changes. A separate ARIA readback confirms the real textbox name
is still exactly `Question`; there is no established product accessibility bug.
Role-based lookup corrected the probe. No product-label change is proposed.

Independent design review supports a later two-component task: keep existing
safe-href/Article-ID admission and exact encoding, open accepted document
citations separately with an explicit cue, preserve hash-only and intentional
Return actions. Final product tests must exercise compiled rendered links,
not DOM replacements, compare state while the child exists as well as after
closing, and cover mixed-case loopback URLs, rejected URLs and Concept-origin
context. External source links are inspected, never activated in offline tests.
New-case Reader session writes must be isolated without changing the existing
exactly-25-ended-sessions restart gate. No refresh/eviction/tab-closure recovery
or physical-mobile popup guarantee is claimed. Stage this task only after the
parent closure CI passes; no repeated user confirmation is required.

## 23. Final Closure CI PASS

Docs-only closure `f87ba6bb0191d08fa84b0b5ef2cdf4d1a79a26db` was pushed
without rewriting history. Exact-SHA main CI
[`34212438350`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34212438350)
completed SUCCESS on 2026-09-08. All seven required jobs PASS: Backend,
Frontend, Product E2E, dependency, secret, workflow policy and SBOM. Docker
and release evidence are skipped by normal-main policy; no workflow rerun.

Product E2E job `102016332027` finished in 26m46s. Complete JSON was parsed
from its logs in memory: Chromium 149.0.7827.55, 3/3 runs, 243/243 checks
each, all checks true. Restart bookmark, completed-state, exactly-25-ended-
session and note persistence PASS. External requests, page errors and static
chunk cancellations: 0. Each strict final network/console audit passes.
The artifact API reports total_count=0. No downloaded log was persisted.

Local HEAD, cached origin/main and live remote main agree at f87ba6b; worktree
and index are clean. Published targets remain v1.0.0 ->
8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6 and v1.1.0 ->
3efbe2a792a9853f1bac456f0287c3b5b62713ce. Closure changes exactly ten Markdown
files, with no product/test/workflow/policy/dependency or forbidden artifact.

P3-036, P3-036.1 and P3-005.2 are **PASS / CLOSED** under their unchanged
acceptance. The historical Graph incident remains OPEN / UNRESOLVED, root
cause UNKNOWN, with its assertion and failure-only evidence unchanged.
Earlier failed runs remain failed; closure makes no universal reliability claim.
Stage the independently reviewed P3-037 Tutor citation-continuity task.
