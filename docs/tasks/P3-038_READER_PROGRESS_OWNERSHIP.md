# P3-038 Reader Progress Ownership

Status: PASS / CLOSED

## Baseline And Authority

Baseline: a294c8fd36beee1b79673f05150310156d0d7f7f, clean synchronized main.
P3-037 is PASS / CLOSED after exact-SHA CI 34225518378, all seven required
jobs and 3 x 281 E2E checks. Formal version v1.1.0; candidate none.
The owner authorizes independent sub-agent review followed by automatic
platform/GUI improvement, without recurring plan confirmation.

## Current Gate

Docs-only closure 598c0daae5eebddef75eaf29206a55b7c093d1b9 passes exact-SHA
main CI 34267030994, all seven required jobs. Remote Product E2E passes 3/3,
298 checks and all 17 Reader journeys each, restart persistence, and zero
unexpected errors/external requests. Uploaded artifacts: 0. Final local HEAD,
cached origin/main and live remote main agree; worktree/index were clean.
P3-038 is PASS / CLOSED under unchanged acceptance. This receipt accompanies
the next genuine GUI task, not a self-hash receipt-only commit. Historical
Graph visibility incident remains OPEN / UNRESOLVED, root cause UNKNOWN.

## Historical Closure Candidate

Repair 1ab812b7292c21cb8775a8e63b93785cf106cc03 passes exact-SHA main CI
34261697861: all seven required jobs, 3 x 298 Product E2E checks, all 17
Reader journeys each, restart persistence and zero unexpected errors, external
requests or uploaded artifacts. Remote Backend is 667 passed / 8 skipped;
Frontend build passes. Normal-main Docker/release jobs are skipped. Current
local corrected-build, safety and two independent review gates also pass.

Implementation authority is consumed. The active gate is a separate docs-only
closure commit, its independent final diff/consistency/safety review, non-force
push and its own exact-SHA CI. Only terminal success and clean synchronized
main permit final PASS / CLOSED. Until then this is a closure candidate, not
a completed task. No self-hash receipt-commit loop or next implementation.

## Historical Repair Gate

Implementation f24e67beae880fccefdd398175b9bdf0862b3046 is pushed. Exact-SHA
main CI 34252242993 fails Product E2E at desktop Dashboard heading resume;
all six other required jobs pass. The requested URL/focus is the saved
heading, but rendered/stored/active-outline section falls back to its preceding
heading. A fresh real-browser trace reproduces initial document-end clamping
while references load and loss of section identity during deferred focus.
The bounded internal section-ID correction passes its persisted regression,
original CPU4 replay and exclusive full replacement validation: 3 x 298,
all 17 Reader journeys each, restart PASS and zero unexpected errors/external
requests. Unit/build, native/visual, safety and two independent review gates
also pass. Repair exact-SHA CI and separate closure CI remain required. No
blind rerun, assertion waiver or closure.

Prior local gates PASS at f24e67b: Backend 671 passed / 4 skipped,
Frontend 149, production build, exclusive Product E2E 3 x 298 with all 17
ownership journeys each, restart persistence, 13 native-input checks, four
viewports, safety and two independent reviews. Implementation and separate
docs-only closure exact-SHA CI remain required. Earlier failed/invalidated
invocations remain in the report; they are not acceptance evidence.

## Objective

Opening or operating Reader tools must not count as reading the Article or
overwrite the learner's meaningful progress and Dashboard resume destination.
Normal body reading must continue to advance and retreat accurately.

## Evidence And Contract

1. Existing compiled Reader reproduces 0 -> 100 / References for both Outline
   and Reading tools at 390x844, 320x844 and 720x450. The actual Dashboard then
   links to /articles/crb-formula#references despite no body reading.
2. A six-second pass-through trace links tool activation, native/corrective
   scrolling, rendered progress and the 300ms localStorage writer. Body-wheel
   control produces a legitimate 27% interior checkpoint. No late repair occurs.
3. Cold tool hashes with saved 43% also overwrite progress and section. Keep
   cold BODY focus/no hydration focus theft; fresh clicks retain tool focus.
4. Preserve displayed progress, active section and stored article_id, progress,
   section_id, section_title and updated_at during tool-only movement/reflow.
   A previously dirty legitimate body checkpoint may still flush normally.
5. Protect click, cold restore, history, resize, font/width changes, delayed
   scroll and pagehide/visibility/unmount persistence. Ownership cannot rely
   solely on focus or a tool hash, which can remain after genuine reading.
6. Real wheel/touch/keyboard/scrollbar body movement, explicit body headings
   and Back to article reacquire reading. Actual end still reaches 100%; moving
   back updates to an earlier section, not a monotonic high-water mark.
7. Keep the existing articleRoot.scrollHeight progress denominator, reading
   line, rounding and localStorage schema. The root includes header, Markdown
   and structured references; do not silently redefine it as Markdown-only.
8. Preserve native href/hash/query/history, Graph and focused-session origin,
   focus lifecycle, API requests, source content and Backend learning state.

## Historical Closure Scope

Only these eight existing documentation files may change:

- README.md
- alignment.md
- docs/00_PROJECT_STATE.md
- docs/tasks/CURRENT_TASK.md
- roadmap.md
- docs/V1_2_ROADMAP.md
- this task
- docs/P3_038_READER_PROGRESS_OWNERSHIP_REPORT.md

No product, tests, P3-037, workflow, dependency, source or runtime changes.
The implementation allowlist below is historical, not active authorization.
Keep every acceptance condition and original failed/invalidated run. The
historical Graph visibility incident remains OPEN / UNRESOLVED, root cause
UNKNOWN. Formal v1.1.0; candidate none.

## Historical Implementation Allowlist

- frontend/src/components/ArticleDetailView.tsx
- frontend/src/lib/articleWorkspace.ts, bounded progress-ownership helpers only
- frontend/tests/articleWorkspace.test.ts
- scripts/e2e/run_product_e2e.py, additive rendered regressions only
- this task and docs/P3_038_READER_PROGRESS_OWNERSHIP_REPORT.md
- alignment.md, docs/tasks/CURRENT_TASK.md, docs/00_PROJECT_STATE.md,
  roadmap.md, docs/V1_2_ROADMAP.md and README.md
- closure-status/evidence only in the P3-037 canonical task/report

## Exclusions

No Backend/M1/API/schema/provider/data/corpus/Graph/reference changes, new
persistence format, dependencies, lockfiles, workflow changes or release work.
No source access, private Zotero, real/paid provider or external browser request.
No blanket tool-hash lock, storage-only patch, fake progress cap, modified
denominator, test relaxation, canonical fixture mutation or altered exactly-25-
ended-session restart gate. No runtime/private artifact or secret in Git.
Do not repair the separate historical Graph incident within this task.

## Verification

Rendered production Reader and CSS, isolated browser contexts and temporary
fake runtime only. Preserve all existing network/error/transition audits.
Context-owned session routes validate methods, payloads, queries and IDs;
canonical session readback must match before/after, including teardown.
The full acceptance runtime is exclusive: run visual or diagnostic browser/API
probes in separate owned runtimes and remove them before the full command.

- Six fresh tool cases at 390x844, 320x844 and 720x450.
- Two saved-middle cold tool hashes at 390x844, preserving no-focus-transfer.
- Two short-body tool cases at 390x844, with measured root below viewport
  height and tall tools. Preserve genuine short-Article end detection.
- Two desktop/mobile tool-scroll, font/width and resize journeys. Prove aside
  scroll actually moves on desktop, rather than accidentally scrolling window.
- Two desktop/mobile genuine heading/body, Dashboard resume, real end and
  retreat journeys. Resume despite unchanged tool hash/focus where applicable.
  Include body-only viewport shrink/restore without an extra wheel, checking
  displayed and saved progress against the independent current geometry.
  The desktop Dashboard return also holds one unchanged exact-local reference
  response, proves the requested focused heading is initially clamped below
  the reading line, then proves root and document scroll-range growth. Preserve
  requested heading identity and final geometric progress. Before any tool or
  reload action, genuine body input must select a different section with the
  resumed URL/hash unchanged. Keep all existing positives and the 17 journeys.
- One additional desktop clamped-final-heading regression, including its
  resulting scroll, cold restoration, and subsequent genuine body retreat.
- One outgoing mobile Reader-to-Dashboard regression under bounded CPU
  throttling, preserving the settled checkpoint across route/DOM replacement.
  On its return journey, delay one exact local reference response without
  changing its payload, prove Article height growth, and require the resulting
  displayed/stored progress to match independent settled geometry. Reject
  redirects, non-local origins, other methods/queries and repeated reads.
  This supplements the other 15 journeys; no earlier assertion is removed.
- One protected Graph-return entry with a saved checkpoint, two viewport
  changes without body input, exact display/store/recency preservation, and a
  subsequent genuine body-reading positive. The formal matrix has 17 journeys.
- Across representative journeys: immediate and debounced exit, reload/pagehide,
  visible click focus, Back/Forward, exact query and history-entry preservation.
- Include wheel, keyboard, touch and scrollbar ownership paths using real
  browser inputs where available; state clearly any emulation limitation.
- First demonstrate semantic RED on the existing compiled implementation,
  then GREEN and positive reading cases after repair. Helper tests alone do
  not establish rendered correctness.
- npm --prefix frontend run test:articles
- npm --prefix frontend run test:tutor
- npm --prefix frontend run test:references
- npm --prefix frontend run test:graph
- npm --prefix frontend run build
- uv run --project backend --extra dev pytest -q
- uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start
- Existing workflow, suppression, secret, dependency, temporary SBOM, artifact
  and protected-path audits; temporary visual inspection on four standard
  viewports with screenshots removed.
- Two independent final reviews, no unresolved Critical/Important finding.

## Delivery And Gates

Deliver the bounded Reader repair, helper/rendered regressions and truthful
evidence/status documents. PASS / CLOSED requires all local/review/safety
gates and exact-SHA implementation plus separate docs-only closure CI, then
clean synchronized main. Existing failures remain evidence, never waived.

Stop the affected action on unknown worktree drift, a required test/review/CI
failure, artifact/secret finding or necessary scope expansion. Diagnose from
evidence instead of blind reruns. No renewed generic user confirmation.

Implementation commit: fix: preserve meaningful reader progress
CI repair commit: fix: preserve resumed reader section
Closure commit: docs: close P3-038 reader progress ownership
Non-force main push and exact-SHA CI readback are authorized after each gate.
No candidate, tag, Release, attestation or destructive Git action.
