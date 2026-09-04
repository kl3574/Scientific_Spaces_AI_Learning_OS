# P3-028 Graph-Reader Round-Trip Reliability Report

## 1. Current Status

- task: P3-028 Graph-Reader Round-Trip Reliability
- local implementation: PASS
- independent final review: PASS, 2 reviewers, 0 Critical / 0 Important
- exact-SHA main CI: pending implementation commit
- closure: not yet claimed
- formal version: `v1.1.0`
- v1.2 candidate: not assigned

## 2. Baseline Defects

The baseline sent selected Graph Article links directly to `/articles/{id}`.
The selected `node_id` and applied query were lost, Reader showed a generic
Articles return action, and neither destination owned useful keyboard focus.
The Product E2E oracle could also see the same Article title in the source
Graph view before proving that navigation reached Reader.

One historical exact-SHA CI run had remained on `Loading article` after a 200
response. A corrected local stress probe did not reproduce that event, so this
task does not claim a framework or hydration root-cause fix.

## 3. Return Contract

- Article return state accepts only local `/graph`, a supported generated node
  type and identifier alphabet, and a normalized query of at most 120
  characters.
- External origins, fragments, malformed percent/UTF-8 input, whitespace or
  unsupported node identifiers, unknown parameters, and recursive workflow
  parameters fail closed or are removed.
- Selected Article nodes, provenance sources, and Concept Study Set Article
  actions all use the existing Article detail href contract.
- The exact canonical `/graph?node_id=...&q=...` path survives client
  navigation and Reader hard reload.

## 4. Focus And Recovery

- Same-tab Graph actions record a bounded Article ID and exact originating
  control. Modifier-key, middle-button, and `_blank` navigation do not mutate
  return-focus state.
- A one-shot return event is paired with bounded tab-session origin context so
  repeated browser Back/Forward cycles can re-arm the same deterministic
  target without adding URL parameters.
- Reader focuses its Article heading after Graph-origin navigation and browser
  Forward. Graph restores the originating control when present and otherwise
  falls back to the selected-node region.
- Saved Reader progress does not move or overwrite a Graph-origin heading
  before the learner scrolls.
- A denied `sessionStorage` getter, read, or write degrades to selected-region
  focus instead of throwing or leaving focus on the document body.
- Missing origin controls and Graph detail failures also focus the selected
  Graph region, where recovery remains available.
- Article loading has a ten-second deadline, AbortSignal propagation,
  generation invalidation, a truthful busy state, a focused `Retry article`
  action, and a safe return link.
- A late stale Article success cannot render, write reading history, or start
  learning work. If an already-persisted Reader session response becomes
  stale during navigation, the client reconciles that session to ended.

## 5. Browser Oracle

The Product E2E now proves destination URL before querying a heading scoped to
`article#article-start`. It covers selected-node, provenance, and Concept Study
Set entry; explicit return; hard reload; repeated browser Back/Forward; visible
focus; a request that ignores abort and succeeds late; and delayed session
creation followed by navigation and persisted end-state readback. It also
covers saved-progress preservation, storage write denial, a missing exact
origin control, and Graph detail-error recovery.

The four required viewports are:

- 1440 x 900 desktop
- 390 x 844 mobile
- 320 x 844 narrow mobile
- 720 x 450 zoom-equivalent

Interactive Graph/Reader controls must be fully contained in the viewport,
and both the Reader and returned Graph workspace must remain free of horizontal
overflow. The timeout/retry surface is additionally exercised at 320 x 844.

## 6. Test Evidence

- focused Frontend tests: PASS, 125 total
- Article tests: 48 PASS
- Graph tests: 29 PASS
- Global Search tests: 5 PASS
- Structured Reference tests: 3 PASS
- Saved Library tests: 5 PASS
- Focused Session tests: 13 PASS
- Tutor tests: 22 PASS
- Frontend production build: PASS, Next.js 15.5.21, 11 routes
- Backend regression: PASS, 600 passed / 4 skipped
- Product E2E: PASS, 3/3 runs, 154 checks per run
- Product E2E restart persistence: PASS
- Product E2E non-loopback requests: 0
- Product E2E unexpected console errors: 0
- Product E2E page errors: 0

Corrected Graph-to-Reader stress:

- transitions: 100/100 PASS
- CPU throttle: 4
- browser cache: disabled
- elapsed time: 36.608 seconds
- Article responses: 301, all HTTP 200
- external requests, console errors, page errors, and failures: 0

## 7. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action pin rate: 100 percent
- explicit permission rate: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS
- protected Backend, API, data, dependency, lockfile, workflow, M1, and release
  paths changed: 0
- tracked runtime/private artifacts: 0
- untracked files before the report: only the canonical P3-028 task
- `git diff --check`: PASS

The dependency audit requires registry access and is deferred to exact-SHA CI,
consistent with the task's non-loopback network prohibition.

## 8. Review Findings And Repairs

The first independent review pass rejected the implementation for five
Important classes of issue: an uncovered Concept Study Set Article path,
permissive malformed node IDs, a non-red-capable stale-generation browser
test, unsafe direct access to the `sessionStorage` getter, and an incomplete
task allowlist. The accessibility review additionally identified repeat
Back/Forward focus, stale session reconciliation, full viewport containment,
and real keyboard focus on retry.

Subsequent review passes identified storage write-only denial, strict fallback
when an exact origin disappears, reading-history storage isolation, stale
history/context side effects, saved-position focus races and unintended
progress writes, and return focus during Graph detail failure. All findings
were repaired with red-capable unit or browser coverage.

Two fresh independent final reviewers audited the completed snapshot. Both
returned PASS with zero Critical or Important findings. Their only repeated
minor note was the stale E2E count in this report, corrected above from 150 to
154.

## 9. Known Risks

- The ten-second Reader deadline is a bounded recovery policy, not proof of the
  historical post-200 loading event's root cause.
- One pre-final three-run invocation reproduced the historical
  `data-hydrated=false` shell stall. It did not recur in the final isolated
  3/3 run or the corrected 100-transition stress. No AppShell or framework
  causal fix is claimed by this task.
- Browser and Next.js runtime behavior can change across upgrades; no framework
  or dependency upgrade is included here.
- Stale session closure is a compensating request. A simultaneous Backend or
  transport outage can still prevent that best-effort reconciliation and must
  remain observable in later operational work.
- Exact focus origin is session-local. If session storage is unavailable,
  navigation remains usable and Graph falls back to its selected region.

## 10. Decision

Local implementation, machine gates, and both independent final reviews are
PASS. P3-028 is LOCAL PASS / IMPLEMENTATION READY, not yet CLOSED. The
implementation commit must pass exact-SHA main CI before a docs-only closure
commit can be created; that closure commit then requires its own exact-SHA CI
readback.
