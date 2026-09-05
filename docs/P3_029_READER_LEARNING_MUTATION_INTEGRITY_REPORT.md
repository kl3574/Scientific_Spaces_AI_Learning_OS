# P3-029 Reader Learning Mutation Integrity Report

## 1. Current Status

- task: P3-029 Reader Learning Mutation Integrity
- local implementation: PASS
- independent final review: PASS, 2 reviewers, 0 Critical / 0 Important
- exact-SHA implementation main CI: PASS
- closure: PASS / CLOSED by this separate docs-only closure commit; final
  reporting waits for its exact-SHA main CI readback
- formal version: `v1.1.0`
- v1.2 candidate: not assigned

## 2. Baseline Defect

The Reader allowed Bookmark and Notes requests to overlap and applied their
results after `await` without binding them to the originating Article
generation. A deterministic local probe held two rapid note-create responses:
the Backend persisted two records while a stale captured Frontend array
rendered one. Navigation could also leave an earlier Article callback able to
change the next Article's feedback or controls.

## 3. Mutation Contract

- Every Bookmark or Notes operation owns an immutable Article ID, committed
  Article generation, operation ID, mutation kind, and optional note ID.
- The committed route identity is updated in a layout effect. An interrupted
  React render cannot overwrite the identity of the Article still displayed.
- Only one Bookmark operation and one Notes operation may be in flight from
  the Reader. Repeated activation while pending is a no-op.
- Post-await UI effects require exact token ownership and the same committed
  Article generation. Token cleanup is independent from visible-state
  ownership so an interrupted render cannot strand an operation ref.
- Note create and update merge by `note_id` through functional state updates;
  delete filters the current state rather than a captured array.
- An unconfirmed create retains its draft. Unconfirmed update or delete keeps
  the prior rendered note. No uncertain operation is replayed automatically.
- Initial Bookmark and Notes reads must finish successfully before their
  mutation controls are enabled, preventing a late read from overwriting a
  confirmed local write.

## 4. Reader Feedback

Bookmark and Notes each expose stable local status and alert regions. Pending,
success, and unconfirmed outcomes remain beside the owning controls. The
sections expose truthful `aria-busy` state, native controls are disabled while
their operation group is pending, and both note textareas have explicit
accessible names.

## 5. Browser Evidence

The isolated fake-runtime Product E2E proves:

- initial Bookmark and Notes controls remain disabled until their reads settle;
- two rapid note-create activations issue one POST and persist/render one note;
- rapid Bookmark add and remove activations each issue one request;
- create, update, and delete response loss occurs after Backend persistence,
  while the Reader keeps the draft or prior rendered state and reports the
  result as unconfirmed;
- every temporary persistence mutation is read back exactly and restored or
  removed before the next scenario;
- a delayed Article A note success cannot affect Article B draft, feedback, or
  focus;
- a delayed Article A Bookmark success cannot alter Article B Bookmark state,
  feedback, or focus; the destination is normalized to the opposite state so a
  leak is observable;
- completion/session behavior and Graph-Reader/Tutor round trips remain green.

The initial-readiness probe uses a dedicated browser context. This prevents its
fetch gate from leaking into later navigation scenarios. Two existing Concept
return keyboard assertions explicitly focus their links before Enter to keep
the full historical E2E oracle deterministic; no product route-focus behavior
was changed.

## 6. Test Evidence

- focused Frontend tests: PASS, 130 total
- Article/Reader tests: 53 PASS, including 5 new mutation tests
- Global Search tests: 5 PASS
- Structured Reference tests: 3 PASS
- Saved Library tests: 5 PASS
- Focused Session tests: 13 PASS
- Tutor tests: 22 PASS
- Graph tests: 29 PASS
- Frontend production build: PASS, Next.js 15.5.21, 11 routes
- Backend regression: PASS, 600 passed / 4 skipped
- Product E2E: PASS, 3/3 final runs, 155 checks per run
- Product E2E restart persistence: PASS
- Product E2E non-loopback requests: 0
- Product E2E unexpected console errors: 0
- Product E2E page errors: 0
- implementation commit:
  `7b4ac74cd0d4b2e7ce708511387a78eb5f61b7b7`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33935734608`
- CI Frontend build, Backend pytest, Product E2E, dependency audit, secret
  audit, workflow/suppression policy, and SBOM validation: PASS
- normal-main Docker compose smoke and release evidence: skipped as designed
- uploaded CI artifacts: 0

## 7. Review Findings And Repairs

The first review pass identified unstable conditional live regions, incomplete
stale/duplicate browser coverage, render-time route-ref mutation, initial-read
overwrite risk, and failure probes that rejected before persistence. A second
pass required explicit unknown-result accounting for update and delete and an
observable opposite-state Bookmark destination.

All Critical and Important findings were repaired. Two fresh final reviewers
then returned PASS with zero Critical or Important findings. Their bounded
minor cleanup notes were also resolved: the dead response-loss helper and
accidental session-storage branch were removed, and restored update content is
read back exactly.

## 8. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action pin rate: 100 percent
- explicit permission rate: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS
- Backend, API, persistence, dependency, lockfile, workflow, frozen M1,
  source/Article records, derived assets, and release metadata changed: 0
- non-loopback source, external search, private Zotero, and real/paid Provider
  access: 0

The local dependency audit was deferred because it requires registry access,
which this task prohibits. The exact-SHA implementation main CI ran and passed
that existing gate.

## 9. Known Risks

- Frontend pending guards prevent duplicate activation in one mounted Reader;
  they do not claim Backend idempotency or exactly-once behavior across tabs,
  process restarts, or arbitrary clients.
- A response lost after persistence is intentionally reported as unconfirmed.
  Reloading the Article is the reconciliation path; the client does not risk an
  automatic duplicate replay.
- Bookmark or Notes read failure disables the corresponding mutation surface
  until the Article is reloaded.
- Shell modal-origin route-focus continuity is a separate verified usability
  gap and remains deferred to P3-030.
- GitHub Actions reports that its Node.js 20 action runtime is deprecated and
  currently forced to Node.js 24. This did not fail a P3-029 gate; it is future
  CI-maintenance work and does not change the immutable workflow in this task.

## 10. Decision

P3-029 local implementation, full machine gates, repository safety checks, both
independent final reviews, and exact-SHA implementation main CI are PASS. This
docs-only commit closes P3-029; its exact-SHA main CI remains the final reporting
gate. P3-030 Shell Modal-Origin Route Focus Continuity is the next bounded
candidate. No v1.2 candidate is assigned.
