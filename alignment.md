# P3-038 Reader Progress Ownership Alignment

Canonical: `docs/tasks/P3-038_READER_PROGRESS_OWNERSHIP.md`.
Status: OPEN / REPAIR CI PENDING.

Implementation f24e67beae880fccefdd398175b9bdf0862b3046 is the pushed baseline;
its worktree was clean when the CI failure was diagnosed.
Exact-SHA main CI 34252242993 fails the desktop Dashboard heading-resume
assertion in Product E2E; the other six required jobs pass. No closure commit
is authorized by this failed gate. The exact rendered failure is reproduced
and corrected within P3-038 after independent review; replacement exclusive
full validation passes 3 x 298 with restart persistence. Retain the assertion;
repair commit/exact-SHA CI is now the next gate. No blind CI rerun or borrowed
local acceptance, and no closure until repair and separate closure CI pass.
The entry baseline and implementation plan below remain historical context.
Baseline a294c8fd36beee1b79673f05150310156d0d7f7f is clean and synchronized;
its P3-037 closure CI 34225518378 passes all seven required jobs and 3 x 281
E2E checks. P3-037 is PASS / CLOSED. Formal v1.1.0; candidate none.

The owner authorizes independent review then automatic GUI improvement.
Repair tool-only scrolling corrupting Reader progress and Dashboard resume,
with the exact contract, allowlist and gates in the canonical task. Preserve
ordinary body tracking, existing geometry, localStorage schema, native hashes,
cold no-focus-transfer, history and Graph/session origins. Add real rendered
regressions before product edits; no backend or source-data changes.

Allowed product/test paths: ArticleDetailView.tsx, articleWorkspace.ts,
articleWorkspace.test.ts and additive run_product_e2e.py. Documentation is
limited to this alignment, current-task/state/roadmap/README pointers, the new
task/report and P3-037 closure evidence. No Provider, private/source access,
API/schema/M1 change, dependency/workflow change, runtime artifact, tag/Release
or repeated generic plan confirmation. Preserve user changes.

Run the full canonical verification and two independent final reviews, then
commit `fix: preserve meaningful reader progress`, non-force push main and
verify exact-SHA CI. A separate `docs: close P3-038 reader progress ownership`
commit and its own CI precede PASS / CLOSED. Stop affected gates on unknown
drift, required failures, forbidden artifacts/secrets or necessary scope
expansion. The historical Graph incident remains OPEN / UNKNOWN.

Prior local gates at that implementation passed: Backend 671/4 skipped, Frontend 149, production build,
exclusive Product E2E 3 x 298 with 17 ownership journeys each, restart
persistence, 13 native-input checks, four rendered viewports, safety and two
independent reviews. The failed and invalidated full invocations stay recorded.
Product/test bindings are in the report. These local results do not override
the failed implementation CI. Reproduce and diagnose before any replacement
implementation validation; separate docs-only closure and its own CI remain
required. The task is not PASS / CLOSED.

The independently reviewed CI correction preserves explicit heading identity
after deferred focus and adds the evidenced initial-clamp regression. Focused
GREEN, original-CI CPU4 replay 3/3, unit/build, native/visual and safety gates
pass on component 7119895 / runner b966b963. Replacement exclusive full E2E
passes 3/3, 298 checks and all 17 Reader journeys each, restart persistence,
zero unexpected errors/external requests and unchanged source/build bindings.
Its temporary runtime is removed. Local/review/safety gates now permit
`fix: preserve resumed reader section`, non-force push and exact-SHA CI, then
the unchanged separate docs-only closure gate. No new user confirmation.

## Historical P3-037 Alignment

Canonical: `docs/tasks/P3-037_TUTOR_CITATION_CONTINUITY.md`.
Status: **OPEN / CLOSURE CI PENDING**. Implementation `37ba58c` passes exact-SHA
main CI `34221048974`, all seven required jobs, Product E2E 3 x 281, restart
persistence and zero uploaded artifacts. Local and independent review gates
also pass. P3-036 and its bounded revisions are PASS / CLOSED. Historical
Graph incident remains OPEN, root cause UNKNOWN.

The owner authorizes independent review followed by automatic GUI improvement.
The implementation authorization is consumed. Current work is docs-only:
update this alignment, README, project state, current-task pointer, both
roadmaps and the P3-037 canonical task/report. No product, tests, URL admission,
API, Backend, data, provider, persistence, dependency or workflow changes.

After independent review and final safety checks, commit
`docs: close P3-037 tutor citation continuity`, non-force push main and verify
that closure commit's own exact-SHA CI before PASS / CLOSED. No recurring
user confirmation, candidate, tag or Release.
No source/private/paid access or committed runtime artifacts. Preserve user
work and stop the affected action on unknown drift or a failed required gate.

## Historical P3-036 Documentation Closure Alignment

Canonical parent: `docs/tasks/P3-036_WORKSPACE_MUTATION_FOCUS_CONTINUITY.md`.
Security revision: `docs/tasks/P3-005.2_SBOM_SCHEMA_TRANSPORT_RESILIENCE.md`.
Status: **OPEN / CLOSURE CI PENDING**.

Implementation `73329956a6a69cf738e42f571df8b924aacf3deb` passed exact-SHA
main CI `34208984649`, all seven required jobs. Product E2E: 3 x 243,
restart PASS, zero unexpected errors/external requests and uploaded artifacts.
The separate P3-005.2 security implementation is PASS; it changes no product,
workflow, pins or dependency. The failed 55ba624 closure remains failed.

Current action is docs-only: update this alignment, README, project state,
current-task pointer, both roadmaps, the P3-036 canonical task/report and
P3-005.2 canonical task/report. Independent review and final safety checks
precede `docs: close P3-036 mutation focus continuity`, non-force main push
and this closure commit's own exact-SHA CI. Only terminal success and clean
synchronized refs permit final closure; no acceptance change or blind rerun.
No product/test/security/workflow/dependency/data/Provider/tag/Release changes.
Historical Graph incident remains OPEN / UNRESOLVED, root cause UNKNOWN.
The 22-case Tutor native-link prototype and independent design review support
a later two-component task, not current product implementation or staging.
No repeated plan confirmation is required under the owner's standing direction.

## Historical P3-005.2 Implementation Alignment

Canonical task: `docs/tasks/P3-005.2_SBOM_SCHEMA_TRANSPORT_RESILIENCE.md`.
Implementation status: **PASS at 7332995 / CI 34208984649**. This reviewed
revision temporarily superseded the parent pointer, not P3-036 acceptance or
product scope. The implementation authorization below is now consumed; only
the docs-only closure action above is active.

Current baseline `55ba624` is clean and synchronized. Its exact-SHA CI
`34205485973` fails SBOM schema download with HTTPError; generation succeeds,
HTTP status/remote cause unknown. P3-036 remains OPEN / CI BLOCKED. The user
authorizes independent review then automatic execution, without another plan
confirmation. The independent scope/security review approved the bounded task.

Allowed: `scripts/security/validate_sbom.py`, its new ordinary-CI regression
`backend/tests/test_sbom_schema_transport.py`, and the exact status/evidence
documents listed by the canonical revision. Implement API -> pinned official
raw -> eligible raw retry within three attempts, unchanged digest/schema/
validator/TLS and every security gate. Digest mismatch is terminal. Run offline
regressions, full Backend/security suites, temporary full schema validation,
safety audits and final independent review; commit
`fix: add pinned SBOM schema transport fallback`, non-force push and verify all
required exact-SHA main CI jobs. Then resume the separate P3-036 closure gate.

No product, workflow, policy-pin, dependency, lockfile, API, M1, source/corpus,
provider, private Zotero, paid request, candidate, tag or Release changes.
Unknown worktree drift, forbidden artifacts/secrets or required failures stop
the affected gate. No blind CI rerun, artifact publication or validation waiver.
Tutor remains unstaged. The full revision contract is in the canonical task.

## Historical P3-036 Alignment

The following records the parent scope and gates; it does not authorize
security changes outside the separate revision above.

Canonical task:
`docs/tasks/P3-036_WORKSPACE_MUTATION_FOCUS_CONTINUITY.md`

Status: **OPEN / CLOSURE CI PENDING**

BOUNDED FRONTEND FOCUS OWNERSHIP, PRODUCT E2E, GOVERNANCE DOCUMENTATION,
ISOLATED LOCAL FAKE-RUNTIME VALIDATION, TWO INDEPENDENT SUB-AGENT REVIEWS, LOCAL
COMMITS, NON-FORCE PUSH TO `main`, AND EXACT-SHA CI READBACK: **AUTHORIZED FOR
THE REMAINING BOUNDED REPAIR AND CLOSURE**

BACKEND, API, PROVIDER, PERSISTENCE, STORAGE SCHEMA, FROZEN M1, SOURCE OR ARTICLE
RECORDS, CORPUS, GRAPH OR REFERENCE DATA, MATCHING, DERIVED ASSETS, DEPENDENCIES,
LOCKFILES, WORKFLOWS, VERSION/CANDIDATE, TAG, RELEASE, ATTESTATION, SOURCE NETWORK,
EXTERNAL SEARCH, PRIVATE ZOTERO, REAL/PAID PROVIDERS, DESTRUCTIVE GIT ACTIONS, AND
HISTORY REWRITING: **NOT GRANTED**

### Historical Objective

Make every reproduced in-page learning mutation retain an explicit, visible,
semantically related focus owner when its initiating control disables,
unmounts, or switches rendering mode, without changing data or route behavior.

### Historical Binding Contract

- No required operation settles on `BODY`, a disconnected element, or an
  unrelated Shell fallback.
- Stable targets are local to the operation: capture/status regions, matching
  note editors/actions, search inputs, result headings, changed/surviving queue
  items, or empty-state recovery actions.
- Async results may not steal focus after a newer user interaction, route,
  modal, or request supersedes the initiating operation.
- Existing request counts, storage writes, URLs, history, feedback, and
  business outcomes remain unchanged.
- Existing correct focus contracts remain correct.

### Historical Allowed Changes

- the nine bounded Frontend components named by the canonical task
- focused pure Frontend tests only if a reusable state helper is necessary
- candidate-filter lifecycle changes explicitly bounded by
  `docs/tasks/P3-036.1_REFERENCE_CANDIDATE_FOCUS_LIFECYCLE.md`
- `scripts/e2e/run_product_e2e.py`
- the canonical task, evidence report, `alignment.md`,
  `docs/tasks/CURRENT_TASK.md`, `docs/00_PROJECT_STATE.md`, `roadmap.md`,
  `docs/V1_2_ROADMAP.md`, and `README.md`

### Historical Acceptance

- Every exact focus target in the canonical task is verified through public
  rendered interactions and visible focus.
- Async ownership and all current success/error/storage/race outcomes remain
  correct.
- Required desktop and mobile viewports have no page-level overflow or clipped
  focused targets.
- Focused Frontend suites, production build, full Backend regression, three
  Product E2E runs, repository safety gates, and two independent final reviews
  pass.
- Implementation and docs-only closure commits each pass exact-SHA main CI and
  final `main` is clean and synchronized.

### Historical Authorization Basis

The product owner explicitly directed continued platform and GUI improvement,
independent sub-agent review, and automatic execution without recurring plan
confirmation. Two independent reviews and controlled Chromium produced current,
reproducible Important evidence at the rendered GUI seam. This standing
direction authorizes only the exact bounded scope above.

### Historical Stop Conditions

Stop rather than widen scope if correct behavior requires Backend, API, data,
provider, persistence, dependency, workflow, external/private, or release
changes, or if an unknown worktree change, forbidden artifact, unrepairable
gate, or exact-SHA CI failure appears.

No v1.2 candidate is assigned.

### Historical Git Plan

- Implementation commit: `fix: preserve workspace mutation focus`
- Current bounded E2E repair commit:
  `test: complete Shell and reference route evidence`
- Follow-up P3-036.1 product lifecycle repair commit:
  `fix: preserve reference candidate filter focus`
- Failure-only Graph evidence commit: `test: capture graph map failure evidence`;
  not a product repair or closure claim
- Non-force push to `main`, followed by exact-SHA implementation CI readback
- Docs-only closure commit: `docs: close P3-036 mutation focus continuity`
- Non-force push to `main`, followed by exact-SHA closure CI readback
- Tag and Release operations are not authorized

### Historical P3-036 Gate

Diagnostic commit `e2ec5e8f2b7682303bd1ca9f3e5ded94f3d8966b` passed
exact-SHA CI `34201705175`, all seven required jobs. Both the fresh local and
remote complete Product E2E runs pass 3/3 with 243 checks each, restart
persistence and zero unexpected console/page errors or external requests.
Backend 629/4 skipped, focused Frontend 141 and production build pass.
Uploaded artifacts: 0. Report sections 19-20 record the reviewed disposition.

Prepare a docs-only closure candidate under the existing PASS requirements;
do not declare closure until that exact documentation commit's CI succeeds.
This is not conditional closure or a Graph repair: the historical rendering
incident remains OPEN, root cause UNKNOWN, with its original assertion and
failure-only diagnostic retained. A required closure failure returns to
diagnosis. Tutor remains unstaged until closure CI succeeds. The following
paragraphs preserve the diagnosis that preceded this decision.

Closure commit `d28fec6e428b6b8e0381d4afb96e988245e25ec8` is pushed, but its
exact-SHA CI `34196981094` failed Product E2E at line 4305. After selecting an
Article in the Graph map, details/counts update but the selected Article node
does not become visible. Other required jobs pass. Fifteen fresh minimal
CPU1/4/8 browser cases do not reproduce it. Replay the original prelude and
inspect map layout/lifecycle; do not rerun CI blindly, relax assertions, infer
a root cause, or start the Tutor follow-on. Section 17 of the report is current.

The original prefix through line 4309 and two 12-case measurement-order probes
also pass locally without reproducing the CI failure. The bounded next action
is a reviewed evidence-only snapshot on failure of the original Graph
assertion in the already-allowed E2E runner. Preserve its timeout, exception,
admission rules and normal path. Capture counts/geometry/visibility only;
no DOM body, labels, inputs, headers, URL/query, screenshot or trace. Validate
diagnostic success/failure handling before publishing an exact-SHA evidence
run. This does not waive any full implementation or closure gate.

The sole additional test path is
`backend/tests/test_e2e_graph_failure_diagnostics.py`, so the existing pytest
collection runs the diagnostic regression without configuration changes.
This explicit, reviewed test-only exception does not authorize Backend
application, persistence, API or data changes. Other allowlist boundaries stand.

Historical implementation gate:

Implementation repair `472350ede8bc20651928ebbc5d88abb206ee6b47` is pushed.
Exact-SHA CI `34194053415` completed SUCCESS: Backend, Frontend, dependency,
workflow, secret, SBOM and Product E2E PASS. Its ordinary browser suite passes
3/3 runs with 243 checks each, restart persistence and zero unexpected errors
or external requests. Uploaded artifacts: 0. Normal-main Docker/release jobs
are skipped by policy. Only the separate docs-only closure commit and its
exact-SHA CI remain before both tasks can be declared PASS / CLOSED. The
reviewed Tutor citation follow-on is not started before that gate passes.

Previous exact-SHA repair CI `34188149037` at `d1e26828` fails the existing
Reference Matched focus assertion before the final network audit. Other
required jobs pass. P3-036.1 now handles the independently reviewed candidate
focus lifecycle defect; this is an explicit product-scope amendment, not an
evidence relaxation. P3-036 remains open. The following describes prior gates.

P3-036.1 focused validation and two independent reviews pass. The prior
full local invocation failed earlier at Reader resume with a chunk-load
error; 12 isolated Reader probes pass, which is not a root-cause resolution.
The original 53-check prefix and 20 subsequent Dashboard-to-Reader transitions
now pass with raw CDP attached to the replacement page. All 20 Article chunk
loads finish HTTP 200, without page errors. This is bounded non-reproduction,
not a demonstrated root-cause fix. The complete replacement gate now passes
3/3 runs, 243 checks each, including strict network/error audits and restart
persistence. Additional in-memory diagnostics did not change existing tests,
timeouts or admission rules. Backend 600/4 skipped, Frontend 141, build and
safety gates pass; a further independent diff review has no Critical or
Important finding. The bounded implementation commit and non-force push can
proceed. Exact-SHA implementation and separate closure CI remain required.

The prior closure and repair failures remain historical evidence. Latest run
`34180979475` at `d80780506fed84d4def4342c904954e9b049f22d` passed Backend,
Frontend and security jobs but failed Product E2E's final request audit. The
previous Tutor pending read is absent; the remaining failures are two HTTP 200
RSC cancellations at undeclared Shell/Reference navigation callers.

The original slow Graph caller now reproduces the exact audit failure in a
four-second loop. The repair adds ordinary declaration/settlement/completion
pairs to 15 existing Shell navigations, one page-two reference return, and
seven cross-route Reader fragment interactions, and 12 additional reviewed
desktop/mobile learning-workspace round trips, plus exact terminal-request
validation for the slow Graph probe. Product scope and original UI assertions
remain unchanged. Focused
slow-route verification passes 3/3. The first complete regression invocation
exposed the additional Reader caller omission; its focused repair passes 3/3.
The 35-caller full invocation then exposed the Reader-to-Graph query-order
canonicalization: the rendered link and canonical destination have identical
encoded parameters in a different order. A bounded opt-in alias certificate
is now being added to the E2E ledger, frozen before activation, with exact
canonical completion and response-backed cancellation evidence. This is an
explicit evidence-model extension, not an unchanged classifier. Global URL
identity, required-cancellation cardinality, and existing default behavior
remain unchanged. Final local gates pass: Backend 600/4 skipped, Frontend 139,
production build, 156 new HTTP-contract scenarios, and three complete Product
E2E runs with 227 checks each and zero unexpected console/page/external errors.
Two independent final reviews pass on script blob
`95feae7950c002127199941e2719832828e87233`. Replacement exact-SHA CI and
docs-only closure CI are still required. P3-036 remains open. Current evidence
is section 14 of the task report.
