# P3-039 Graph Node Rendering Reliability

Status: OPEN / DEFERRED; historical root cause UNKNOWN.

Current execution priority is the separately reproduced P3-040 expanded-
provenance return defect. Diagnostic publication at d25113d is verified. The
late-detail frame-oracle draft is preserved but not executed or published;
its admission did not make it a prerequisite to other GUI repairs. No historical
map assertion is weakened and no Graph rendering repair or closure is claimed.

## Baseline And Authority

Baseline: 598c0daae5eebddef75eaf29206a55b7c093d1b9, clean synchronized main.
P3-038 is PASS / CLOSED after exact-SHA CI 34267030994: all seven required
jobs, 3 x 298 checks, all 17 Reader journeys each, restart PASS and zero
unexpected errors, external requests or uploaded artifacts. Formal v1.1.0;
candidate none. The owner authorizes independent review then automatic GUI
improvement, without recurring generic confirmation or AGENTS regeneration.

## Objective And Evidence

Resolve the historical Graph selected-Article rendering failure while keeping
native keyboard/pointer navigation, selection, map/list controls, focus, URLs,
details, model counts and accessibility correct. Source:
docs/P3_036_WORKSPACE_MUTATION_FOCUS_CONTINUITY_REPORT.md, sections 17-20.
CI 34196981094 updated URL/details and showed seven nodes/six relationships,
but the selected Article button was not visible within the original 30 seconds.
Subsequent passing runs and bounded negative probes do not resolve that incident.

Current root cause: UNKNOWN. Fresh controlled node objects can reset measured
dimensions, but the proposed later reset/commit ordering is not established.
The first task is a tight, honest feedback loop, not a speculative product fix.

## Current Diagnostic Evidence

One independently reviewed unchanged-product calibration passes: complete 31/31
committed events, 17 target samples, two real generations and the selected
Article's false -> true initialization. Original UI assertion and strict audit
PASS; external/unexpected errors 0, source/build bindings unchanged and temporary
runtime removed. Offline contracts 52 PASS, Backend 723/4 skipped, Frontend build
PASS. Two probe orchestration review findings were reproduced and corrected
before browser execution. Report contains exact bindings and limitations.

This is observation calibration only, not symptom reproduction or product repair.
Diagnostic publication passed final review and exact-SHA main CI at d25113d,
run 34276540291, all seven required jobs; Docker/release jobs policy-skipped.
No callback pilot or product change is active before its own evidence gate.

## Deferred Diagnostic Scope

- scripts/e2e/probe_graph_render_lifecycle.py
- scripts/e2e/graph_render_probe.js
- backend/tests/test_graph_render_probe.py
- scripts/e2e/graph_frame_oracle.js: independently reviewed diagnostic-only extension
- backend/tests/test_graph_frame_oracle.py: offline oracle contracts
- this task and docs/P3_039_GRAPH_NODE_RENDERING_RELIABILITY_REPORT.md
- alignment.md, docs/tasks/CURRENT_TASK.md, docs/00_PROJECT_STATE.md,
  roadmap.md, docs/V1_2_ROADMAP.md and README.md
- P3-038 canonical task/report: final closure receipt only

Use an owned temporary synthetic runtime and the unchanged production build.
No diagnostic hook is installed in the application or ordinary startup.
No product-code authority is active during diagnosis.

## Deferred Post-Calibration Diagnostic Amendment

Diagnostic d25113d2f730e99c1e730f5649874f0cd5fc17e5 passes exact-SHA main CI
34276540291: all seven required jobs, 3 x 298 E2E checks, restart persistence
and zero unexpected errors, external requests or uploaded artifacts. The
historical Graph failure is not reproduced or repaired. The proposed pending-
effect treatment has no qualified normal-owner trigger and is not executed.

Independent review admits one different evidence-only case: late Article detail
completion after the selected map is already visible. This does not weaken or
replace the historical 30-second assertion or authorize a product repair.

- Optional `--late-detail` only; default calibration and snapshot v1 remain
  unchanged. Do not change graph_render_probe.js or the original E2E runner.
- Hold exactly one selected-Article detail GET. Forward the synthetic Backend's
  real HTTP 200 unchanged, once, without redirects; leave subgraph and every
  other response unchanged. Missing/duplicate interception invalidates the case.
- Preserve Enter / URL / context focus / original 30-second selected-button
  assertion. Only afterwards, within five seconds, require committed initialized
  state and a visible pre-release compositor baseline. No forced repaint.
- Arm observation before response release; release before the existing global
  request-settlement helper. Require actual detail-application evidence and
  unchanged selection, subgraph, viewport and provider/wrapper/fiber lifetime.
- Capture one fixed one-second post-release window, PNG and everyNthFrame=1.
  At most 64 compressed frames, 1 MiB each and 16 MiB aggregate, including the
  baseline. Acknowledge promptly; decode sequentially only after capture stops.
  No silent eviction, adaptive deadline or repeat matrix.
- Image buffers are transient in-memory diagnostic inputs only. No image file,
  screenshot output, trace, video or protocol/debug-log serialization. Validate
  PNG dimensions before decoding, require identity viewport/DPR mapping and
  cap decoded pixels at two million. Use bounded-time native Chromium decoding,
  ROI-sized detached canvases and ImageBitmap.close; dropping references is not
  a guarantee of immediate garbage collection. Export only bounded primitives.
- Use valid swap timestamps and conservative clock alignment with release and
  actual detail application. Missing/ambiguous timing prevents attribution.
- Fix pixel masks/thresholds before execution. Require unchanged same-frame
  control/background evidence and loss of both outline and interior silhouette,
  with canvas background visible. Text-only/border-only differences, overlays,
  shifted/cropped mappings and generally blank/corrupt capture do not qualify.
- A visible baseline, post-detail absence and restoration support only a
  captured composited-blink candidate under instrumentation. Without restoration,
  report captured disappearance only. This is not physical-screen presentation,
  complete frame coverage or absence-of-blink evidence. Missing baseline,
  bracketing, detail application, invariants or coverage means INCONCLUSIVE.
- Offline pixel-array contracts prove the oracle only, not a product defect.
  Independent concrete code review and all offline contracts must pass before
  this single browser execution. Any positive needs a separately reviewed
  P3-039.x layout-stability revision; no automatic repair or historical closure.

Authoring is limited to the two extra diagnostic files above, the existing
Python probe and its tests, and the already-allowlisted governance/evidence
documents. Application, dependency, workflow and data boundaries are unchanged.

## Diagnostic Contract

1. Calibrate a minimal pre-load DevTools hook on real GraphView/ReactFlow.
   Record the actual injected renderer identity; Next uses its bundled renderer,
   not necessarily the top-level react-dom package. Do not replace an existing
   hook, provider, native ResizeObserver, scheduler, compiled module or store.
2. Read only root.current committed fibers, not speculative render state.
   Identify the target wrapper structurally and verify its nodeRef, neighboring
   hook signature and circular-effect membership. Recognize alternate swaps
   without calling them remounts. Use observer-owned WeakMaps, never annotate
   fibers. Copy only allowlisted primitive snapshots, not live effect objects.
3. Bound work as well as output: at most 512 events, four renderers, 4096 fibers
   per commit, depth 128, 128 hooks per candidate and 64 circular effects.
   Detect cycles. Latch capture_error, overflow and coverage_incomplete outside
   the buffer; exhaustion or exceptions stop capture and invalidate attribution.
4. Establish renderer/initial concept-map selector before Article activation,
   within five seconds once the initial map is ready. Preserve the original
   Enter -> URL -> visible context focus -> 30-second selected-Article assertion.
   Do not wait for new-generation initialization, dimensions, selector readiness
   or details before that assertion. Observe the new generation asynchronously.
5. Keep observation validity, actual UI assertion and network/error audit
   verdicts separate. Capture failure cannot erase a UI failure. Calibration
   success is not symptom RED/GREEN or proof of the historical root cause.
6. Export only finite numbers, booleans, fixed enums and explicitly admitted
   renderer/version metadata. No raw fibers, props, IDs, labels, content, input,
   URLs, headers, exception text/tracebacks, browser diagnostics or server logs.
   Runtime files stay in a temporary directory and are removed on every exit.
7. Mandatory offline probe contracts cover valid/ambiguous selectors, alternate
   versus remount identity, incomplete coverage, exceptions, traversal/event
   exhaustion and sensitive sentinels in normal and failure output.
8. Only after successful calibration consider at most three matched pairs for
   the reviewed later-callback pilot. A harness may own an unchanged
   GraphVisualization prop; it must not rewrite GraphView fibers or dispatchers.
   Keep native observer delivery and provider lifetime. Prove actual adoption,
   reset, positive measurement/handles and committed dependency history. The
   required gap is no committed true between measurement and reset, not merely
   a delayed effect body. Same five-second prerequisites and original symptom
   deadline; overflow, missed ordering or an invalid control is INCONCLUSIVE.
9. Synthetic RED requires transfer to unchanged real GraphView and its original
   keyboard/URL/details assertion without instrumentation. No forced flushSync,
   hidden CSS, suppressed observer or corrupted state can qualify the failure.
   Stop an inconclusive probe rather than repeat old timing/CPU matrices.

## Evidence-Qualified Repair Scope

After a reproducible actual failure, causal evidence and an independent concrete
fix review, the bounded candidate paths are GraphVisualization.tsx, GraphView.tsx,
src/lib/graphVisualization.ts, tests/graph.test.ts and tests/graphWorkspace.test.ts
under frontend, plus additive rendered regressions in scripts/e2e/run_product_e2e.py.
These paths are not active edit authority yet. Preserve every existing assertion,
timeout placement, fixture, URL and strict network/error/cancellation policy.
Any further scope change needs a concrete independent review, not another
generic user confirmation.

## Exclusions

No Backend application, M1, legacy or versioned API, schema, storage migration,
source/corpus/Graph/reference data, acquisition, PDF, private Zotero, real/paid
Provider, dependency, lockfile, workflow, candidate, tag, Release, attestation,
destructive Git or history rewriting. No external browser requests. No runtime
artifact, secret, HTML, screenshot, trace, profile, cache or database in Git.
Do not declare Graph repaired from a negative replay or Reader CI success.

## Verification And Delivery

- Offline probe contracts and independent diagnostic-code review must PASS
  before the first browser execution. A failed prerequisite stops that execution.
- Calibration: unchanged production GraphView, strict existing loopback/browser
  error audit and complete temporary runtime cleanup. Record source/build hashes.
- uv run --offline --project backend --extra dev pytest -q backend/tests/test_graph_render_probe.py
- Before publishing diagnostics: full ordinary Backend pytest, Frontend build,
  probe contracts/browser calibration, independent diff review, documentation
  consistency, secret/artifact/protected-path audits and exact-SHA main CI.
- Actual repair additionally requires test:articles, test:tutor, test:references,
  test:graph, production build, full Backend, exclusive Product E2E --repeat 3
  --frontend-mode start, four-view visual inspection with images removed, safety,
  two independent final reviews, and implementation plus separate closure CI.
- Diagnostic commit: test: probe graph node rendering lifecycle
- Repair commit: fix: stabilize graph node rendering
- Closure commit: docs: close P3-039 graph rendering reliability
- Non-force main push and exact-SHA CI readback follow the appropriate gates.

PASS / CLOSED requires original rendered failure reproduced and corrected,
regression and complete acceptance passing, clean synchronized main and all
required CI. INCONCLUSIVE or a bounded negative is diagnostic evidence only;
the incident stays OPEN / UNKNOWN. Unknown worktree drift, unsafe output,
required failure or necessary forbidden scope stops the affected action.
