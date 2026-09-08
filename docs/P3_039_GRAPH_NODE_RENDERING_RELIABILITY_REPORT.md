# P3-039 Graph Node Rendering Reliability Report

Status: OPEN / DIAGNOSIS
Root cause: UNKNOWN

## Baseline

P3-038 is PASS / CLOSED at 598c0daae5eebddef75eaf29206a55b7c093d1b9 and
exact-SHA CI 34267030994. Seven required jobs, 3 x 298 E2E checks, all 17
Reader journeys each, restart persistence, zero unexpected errors/external
requests and uploaded artifacts. Final branch was clean and synchronized;
published tags unchanged. Its canonical task/report contain the closure receipt.

## Existing Incident

P3-036 report sections 17-20 retain the failed Graph selected-Article visibility
assertion and all later negative probes. URL/details/count readiness does not
prove visible node rendering. Missing, hidden and off-canvas nodes were not
distinguished in that historical snapshot. No new root cause is claimed here.

## Independent Diagnostic Review

The reviewed next step is observation calibration, not a forced-ordering fix.
The key unresolved observation is complete same-generation committed
useNodeObserver dependency history across measurement/reset. Effect-body timing
alone is insufficient. Public props cannot guarantee that internal ordering.

Source inspection identifies an inert DevTools commit hook as a possible seam.
Next's bundled production renderer identifies itself as
19.2.0-canary-0bdb9206-20250818; the actual browser injection must still verify
that identity. The commit hook reads root.current after layout and before
passive effects. Structural nodeRef/neighbor/effect-list checks are required;
minified names and global hook indexes are not evidence.

The historical pre-calibration task review requires bounded traversal with latched failure
flags, unchanged assertion placement, and mandatory whole-output/sentinel
contracts. These requirements are included in the canonical task. No product
code or observer behavior is changed. Browser calibration had not yet run at
that review; its subsequent result is recorded below.

## Offline Probe Verification

The first 45 probe contracts passed. Independent diagnostic-code review then
identified two Important orchestration defects, before any browser execution:

- Browser, Playwright or server teardown failure after a successful UI check
  could still produce CALIBRATED after directory cleanup.
- A failed visibility assertion closed the page without capturing its committed
  history. Successful-path tests did not exercise that failure path.

Seven new real-CLI orchestration checks first failed against the original probe.
Three teardown cases incorrectly returned exit 0; context teardown was incorrectly
INCONCLUSIVE. Visibility-failure and healthy-output cases exposed the missing
failure/capture fields. These are probe defects, not the historical Graph cause.

The correction adds an independent execution-failure latch, first-failure stage,
resource-specific teardown stages, and validated capture before closing a failed
page. Capture failure preserves UI FAIL; teardown failure prevents CALIBRATED.
The original Enter / URL / focus / 30-second visibility assertion order remains
unchanged. No product, installed dependency or original E2E runner is modified.

Command:
`uv run --offline --project backend --extra dev pytest -q backend/tests/test_graph_render_probe.py`

Result: **52 passed in 1.90s**, including four post-success teardown failures,
visibility failure with successful and failed capture, and healthy orchestration.
Sensitive sentinels do not appear in CLI stdout/stderr. Independent re-review
closes both Important findings, with no remaining Critical/Important issue in
the reviewed code, and approves one isolated unchanged-product calibration.
It does not approve a product repair or infer the historical cause.

Current full ordinary Backend regression: **723 passed / 4 skipped / 4 existing
warnings in 39.87s**. Frontend `npm run build`: **PASS**, Next.js 15.5.21,
all 11 static pages generated and dynamic routes compiled. The warnings are the
existing invalid-escape deprecations in the unchanged original E2E runner.
The earlier, pre-correction ordinary
Backend run completed 716 passed / 4 skipped / 4 existing warnings in 39.92s;
that result does not substitute for verification of the corrected probe.

Secret audit: PASS, credible/reported/suppressed 0. Protected application,
existing E2E, dependency and workflow diff: empty.

## Unchanged-Product Browser Calibration

Date: 2026-09-09, Asia/Shanghai.

Command:
`uv run --offline --project backend python scripts/e2e/probe_graph_render_lifecycle.py`

One invocation, after the offline contracts and independent diagnostic-code
review passed. Exit 0, status **CALIBRATED**, UI **PASS**, observation **VALID**,
audit **PASS**. Incident remains **OPEN / UNKNOWN**.

- Actual injected production renderer: react-dom
  `19.2.0-canary-0bdb9206-20250818`, one renderer and one observed root.
- Complete 31/31 committed events; 17 contain the target. No capture error,
  incomplete coverage, overflow, execution failure or failed snapshot export.
- Initial concept-map target: wrapper 2 / fiber 3, commits 12-23.
  Initialized false at 12-14, then true at 15-23, not selected.
- Article-map target: wrapper 4 / fiber 5, commits 27-31. Selected throughout;
  initialized false at 27-29, then true at 30-31. This is a real generation
  change, not an alternate-fiber swap mislabeled as a remount.
- The original Enter / URL / visible context focus / 30-second selected Article
  assertion passed, followed by seven nodes / six relationships and exact route
  settlement. No extra generation-recovery wait precedes that assertion.
- External requests, unexpected console errors, page errors and unexpected
  context pages: **0 each**, using the unchanged strict E2E guards.
- Source/build bindings equal before and after; temporary runtime removed.
  Post-run ports 3000/8000 have no listeners; no calibration directory remains.
  No HTML, image, PDF, screenshot, profile, trace or runtime data is retained.

This proves the bounded committed-state observer works on the unchanged real
GraphView journey. It does **not** show measurement/reset ordering between
commits, reproduce the old invisible-node symptom, justify a callback patch,
or establish any product repair. The next causal experiment needs its own
concrete independent review under the existing bounded-pilot contract.

### Exact Bindings

Reviewed diagnostic Git blobs:

| File | Blob |
| --- | --- |
| Python runner | ba32ac8901c3d28243ef66b3ffa6aa7fcd3d4f5c |
| Browser observer | b371ebfd6282350521f12e120984194d346a9b5a |
| Offline contracts | 4f1fe05ada61d2d816fb364834bae0246ae413ad |

Observed source/build SHA-256:

| Input | SHA-256 |
| --- | --- |
| GraphView.tsx | b92135158067876e75cf19e6e9714ade2c76a262a61e1f7e738ce358ddca0cf5 |
| GraphVisualization.tsx | 33b02a76fb4c42184ed406e49e971ad77fa8f299623a9c63b91f8acca4f6df0d |
| graphVisualization.ts | dcad83e5c0e749d8e57a73cb256acf62d5ced6d708d2b46e5d778db2218a726b |
| Original E2E runner | b24e1c5091dc13c561cd9173126b1ed03528343b6a3778ae8e04b3e2bd9f85d9 |
| Production BUILD_ID | 8145e6c7bfb7ffbe034dfc630e3d30004ee8063595ebb0cd74016e008ecc3679 |

## Delivery Status

Calibration and local diagnostic verification pass. Final independent diagnostic
diff review finds no Critical/Important issue and confirms the exact 13-file
scope. Its minor historical-wording correction is applied. Documentation
consistency, secret/artifact and protected-path audits pass. The diagnostic
commit and its exact-SHA seven-job main CI remain the publication gate; the local
result is not remote CI or Graph closure. Formal v1.1.0; candidate none.

## Result Rules

Observation validity, UI outcome and audit outcome are separate. Missing or
ambiguous observation is INCONCLUSIVE, not evidence of no committed transition.
Actual UI failure remains FAIL even when capture fails. A calibrated healthy
page is not proof that the historical incident is repaired. Any later matched
pilot remains bounded and requires transfer to an uninstrumented real journey.
No diagnostic or implementation publication is authorized before its gates.
