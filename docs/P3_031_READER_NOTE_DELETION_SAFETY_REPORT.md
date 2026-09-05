# P3-031 Reader Note Deletion Safety Report

## 1. Status

- Local implementation: **PASS**
- Independent final review: **PASS**, 2/2 reviewers, 0 Critical / 0 Important
- Exact-SHA implementation main CI: **REQUIRED**
- Task closure: **ACTIVE** until implementation and docs-only closure CI pass
- Candidate version: not assigned

The local implementation satisfies every P3-031 behavioral, accessibility,
scope, and repository gate. The implementation commit must still pass exact-SHA
main CI before the task can be closed.

## 2. Implemented Contract

- The first mouse, `Enter`, or `Space` activation creates an immutable
  Article/generation/note deletion intent and sends no DELETE request.
- An inline confirmation states that deletion is permanent and cannot be
  undone. Initial focus moves through a stable bridge to `Cancel` before the
  initiating control is disabled.
- Awaiting confirmation and in-flight deletion are distinct states. All Notes
  mutation launchers are locked in both states.
- Cancel and `Escape` keep the rendered and persisted note, send no DELETE,
  and restore the exact initiating control.
- Keyboard confirmation sends one DELETE. A synchronous operation ref prevents
  repeated activation from sending another request.
- Pending confirmation remains mounted and owns visible focus. Success removes
  only the exact note and focuses the visible Notes status.
- Rejected and post-persistence lost responses remain unconfirmed, preserve the
  current rendering, do not replay, explain possible persistence divergence,
  and restore the exact Delete control.
- Same-Article query/history changes invalidate an in-flight operation before
  its stale completion can render or focus. Notes writes remain locked behind a
  truthful reload-before-retry reconciliation warning.
- Article changes, Back/Forward, and reload clear stale intent and focus work
  without a cross-Article side effect.

## 3. Focus And Responsive Evidence

The Product E2E trace records focus target identity together with whether the
confirmation was still mounted. It proves the bridge focus occurs before React
disables or removes the focused subtree, rather than checking only the eventual
active element. Open, Escape, success, rejection, response loss, awaiting-query
invalidation, and in-flight-query invalidation all produce non-empty ordered
focus evidence with no `body` target.

At `1440x900`, `390x844`, `320x844`, and `720x450`, the suite verifies:

- visible Cancel focus on open;
- confirmation and action containment without horizontal page overflow;
- connected, visible confirmation focus while DELETE is pending;
- disabled competing Notes mutation launchers;
- visible terminal status focus after success; and
- exact note persistence on cancel and exact note removal on success.

## 4. Request And Ownership Evidence

- Opening, Cancel, Escape, navigation before confirmation: 0 DELETE requests.
- Accepted keyboard confirmation: exactly 1 DELETE request.
- Repeated activation while pending: no second request.
- Rejected request: exactly 1 attempt and no automatic replay.
- Post-persistence response loss: exactly 1 attempt and no automatic replay.
- Query invalidation after request dispatch: stale completion is inert; the
  current rendering is retained and writes remain locked until reload.
- Ownership dimensions: Article ID, Article generation, note ID, mutation kind,
  and operation sequence.

## 5. Local Test Evidence

| Gate | Result |
| --- | --- |
| Articles/Reader tests | PASS, 59/59 |
| References tests | PASS, 3/3 |
| Tutor tests | PASS, 22/22 |
| Graph tests | PASS, 29/29 |
| Focused Frontend total | PASS, 113/113 |
| Frontend production build | PASS, 11 routes |
| Backend regression | PASS, 600 passed / 4 skipped |
| Product E2E | PASS, 3/3 complete runs, 177 checks each |
| Chromium | 149.0.7827.55 |
| Restart persistence | PASS |
| External browser requests | 0 |
| Unexpected console errors | 0 |
| Page errors | 0 |

The final three-run E2E used isolated temporary runtime stores and left no
result JSON, screenshot, trace, profile, or mutable product data in the
repository.

## 6. Review Evidence

Initial review found incomplete query-history ownership, insufficient keyboard
and launcher-lock assertions, and an eventual-focus-only oracle. Repairs added
the reconciliation lock, exact request counters, pending and terminal viewport
coverage, and ordered focus identity traces bound to confirmation mount state.
Both independent reviewers then re-reviewed the final stable diff and returned
PASS with zero Critical or Important findings.

## 7. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action pin and explicit permission rates: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS
- changed paths: P3-031 allowlist only
- Backend, frozen M1, API, persistence, dependencies, lockfiles, workflows,
  source/Article/Graph data, derived assets, and release metadata changed: 0
- non-loopback network, source, private Zotero, external search, and real/paid
  Provider access: 0

The local dependency audit is deferred because it requires registry access,
which P3-031 prohibits locally. Exact-SHA implementation main CI must run it.

## 8. Discriminating Failures Repaired

- The first new query-history test failed because a same-Article native History
  change was not observed. Reader now observes canonical search parameters.
- A viewport run initially left synthetic sessions open. The viewport setup now
  intercepts session creation and leaves restart persistence unchanged.
- Review showed a focus trace could pass after its observer had been destroyed
  by reload. The oracle now requires non-empty evidence and is installed on the
  exact scenario under test.
- A stricter focus oracle initially recorded the pre-activation `body` state.
  The test now focuses the initiating Delete control before tracing, then
  verifies only interaction-owned transitions.

No acceptance criterion was weakened to resolve these failures.

## 9. Known Limits

- P3-031 does not add undo, trash, soft-delete, versioning, or Backend recovery.
- Exactly-once persistence is not claimed. The Frontend guarantees one request
  per accepted intent; an unconfirmed network result still requires reload.
- Query navigation after request dispatch can leave the rendered note different
  from persistence until reload; the reconciliation lock and warning make this
  state explicit and prevent another mutation.
- Browser behavior is verified against Chromium and the current React/Next.js
  runtime used by the repository.

## 10. Boundary Result

P3-031 changed only the allowlisted Reader component, pure mutation helper and
test, Product E2E, and task governance documents. It did not change Backend,
published contracts, frozen source processing, product data, dependencies,
workflows, external/private integrations, candidate metadata, tags, Releases,
or attestations.

## 11. Next Gate

Create the implementation commit, push it non-force to `main`, and require all
normal-main exact-SHA CI jobs to pass. Only then create the docs-only closure
commit and verify its own exact-SHA CI. No subsequent task or v1.2 candidate is
staged by this local PASS.
