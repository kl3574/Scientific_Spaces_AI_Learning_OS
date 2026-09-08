# P3-036 Workspace Mutation Focus Continuity

## Status

REOPENED / CI EVIDENCE REPAIR

## Task Identity

Preserve an explicit, visible keyboard-focus owner when an in-page action
disables, replaces, or removes its initiating control across the learning
workspace.

## Authoritative Baseline

- Starting commit and cached `origin/main`:
  `7997cceca268bae1e43806efb5460674a699dc92`
- Starting ahead / behind: `0 / 0`
- Entry worktree, index, and untracked set: clean
- Previous task: P3-035 PASS / CLOSED
- P3-035 docs-only closure exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34011480204`
- Required closure jobs: PASS; normal-main Docker and release jobs skipped as
  designed; uploaded artifacts: 0
- `REWORK.md` and `.audit`: absent
- Formal version: `v1.1.0`; candidate version: not assigned
- The product owner directed continued platform and GUI improvement with
  independent sub-agent review and without recurring plan-confirmation pauses.

## Background

Two independent GUI reviews and a controlled local Chromium probe found that
successful state transitions frequently leave `document.activeElement` on
`BODY` when a pressed control becomes disabled or is replaced. Reproduced
surfaces include Article selection, Reader learning/bookmark/note/session
actions, Saved Learning capture, Focused Session queue mutations, Graph
search/paging and Concept capture, and Tutor context/activity actions. Existing
note deletion, completion reconciliation, queue-confirmation entry, and
non-boundary item movement already have valid focus owners and must remain so.

## Goals

1. Give every reproduced state-changing interaction a deterministic next focus
   owner that is visible and semantically related to the result.
2. Preserve keyboard position across controls that disable, unmount, or switch
   rendering mode.
3. Preserve live feedback and avoid stealing focus after the user has moved to
   another control during an asynchronous operation.
4. Keep route, storage, request ownership, data writes, and business outcomes
   unchanged.
5. Keep all required desktop, mobile, narrow, and short-landscape layouts free
   of focus clipping or page-level overflow.

## Non-Goals

- Backend, API, persistence, storage schema, Article/source records, corpus,
  Graph/Reference data, Tutor provider, or derived-asset changes
- New learning, search, RAG, Graph, Tutor, Zotero, or synchronization features
- Visual redesign, localization, authentication, multi-user behavior, or data
  migration
- Dependency, lockfile, framework configuration, workflow, version, candidate,
  tag, Release, or attestation changes
- Source network, external search, private Zotero, or real/paid Provider access

## Public Test Seams

1. Keyboard activation in the rendered `/articles`, Reader, `/library`,
   `/session`, `/graph`, and `/tutor` workspaces.
2. The resulting `document.activeElement`, visible focus treatment, live
   feedback, URL, and public rendered state after each committed transition.
3. Existing isolated fake-runtime network and storage observations in Product
   E2E; no private implementation state or production data is inspected.

## Required Focus Contract

- Article selection Clear returns focus to the stable Focused Session capture
  region.
- Reader learning-state, bookmark, and standalone timer mutations focus a
  stable result region; note create/update focuses note feedback; entering edit
  focuses its textarea; cancel restores the matching Edit action.
- Saved Learning Clear returns to the filter input; successful Session capture
  focuses a persistent, visible result target for the exact initiating item.
- Focused Session cancel restores Clear queue; confirm-clear focuses the empty
  recovery action; Set current, boundary moves, and removals focus the changed
  or nearest surviving item without falling to `BODY`.
- Graph Apply and pagination focus the Nodes result heading; Clear focuses the
  graph search input; Concept capture focuses its mutation result.
- Tutor Article search focuses its first result; clearing context returns to the
  search input; activity retry focuses a stable activity result region.
- Async completion may only claim focus that the same current operation still
  owns. A later user focus move, route, modal, or request supersedes it.

## Allowed Changes

The additional candidate-filter lifecycle repair is explicitly bounded by
`P3-036.1_REFERENCE_CANDIDATE_FOCUS_LIFECYCLE.md`. It follows exact-SHA CI
`34188149037` and a fresh browser RED, and is not an expansion into matching,
API, data or other Reference/Shell behavior.

- `frontend/src/components/ArticleListView.tsx`
- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/components/SavedLibraryView.tsx`
- `frontend/src/components/StudySessionView.tsx`
- `frontend/src/components/GraphView.tsx`
- `frontend/src/components/ConceptStudySetPanel.tsx`
- `frontend/src/components/TutorArticlePicker.tsx`
- `frontend/src/components/TutorActivity.tsx`
- `frontend/src/components/TutorView.tsx`
- focused pure Frontend tests if a reusable state helper becomes necessary
- `scripts/e2e/run_product_e2e.py`
- this canonical task, `alignment.md`, `docs/tasks/CURRENT_TASK.md`,
  `docs/00_PROJECT_STATE.md`, `roadmap.md`, `docs/V1_2_ROADMAP.md`, `README.md`,
  and the P3-036 evidence report

## Prohibited Actions

- Any `backend/**`, API, persistence, storage, frozen M1, source/Article record,
  corpus, Graph/Reference data, matching, provider, or derived-asset change
- Any dependency, lockfile, framework configuration, workflow, release/version,
  candidate, tag, Release, or attestation change
- Any source access, external search, private Zotero read/mutation, real/paid
  Provider call, or non-loopback browser request
- Force push, history rewrite, destructive Git action, or published-tag change
- Runtime/private artifacts, secrets, databases, PDFs, downloaded HTML, images,
  screenshots, traces, profiles, caches, or generated corpora in Git

## Deliverables

- Deterministic focus ownership for every required interaction above
- Race-safe async focus behavior that does not override later user intent
- Product E2E regression coverage at public rendered seams
- Preservation evidence for already-correct mutation and navigation paths
- `docs/P3_036_WORKSPACE_MUTATION_FOCUS_CONTINUITY_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. None of the required keyboard-activated transitions settles on `BODY`, a
   disconnected element, or an unrelated Shell fallback.
2. Every target in the Required Focus Contract receives visible focus without
   changing the current route or corrupting scroll position.
3. Pending/success/error, storage failure, duplicate, capacity, stale response,
   retry, cancellation, and empty-state outcomes remain truthful and usable.
4. A user focus move after an async action begins is not overwritten when that
   action later settles.
5. Existing note-delete, completion/timer reconciliation, queue confirmation,
   and non-boundary reorder focus behavior remains correct.
6. Existing request counts, browser storage writes, URL/history state, and API
   payloads remain unchanged.
7. No page-level horizontal overflow or clipped focused target occurs at
   `1440x900`, `390x844`, `320x844`, or `720x450`.
8. Focused Frontend tests, production build, full Backend regression, three
   Product E2E runs, two independent final reviews, and repository safety gates
   pass.
9. Implementation and closure commits each pass exact-SHA main CI; final
   `main` is clean and synchronized.

### CONDITIONAL

No conditional closure. Any reproduced action without a deterministic focus
owner keeps the task open.

### BLOCKED

- A required path still settles on `BODY`, a disconnected target, or unrelated
  Shell fallback.
- Focus restoration changes a data write, route, request, or business outcome,
  or steals focus from a newer user interaction.
- Correctness requires a prohibited Backend, API, data, dependency, workflow,
  external/private, Provider, or release change.
- A required test, review, safety, artifact, or exact-SHA CI gate cannot be
  repaired within the allowlist.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Preserve the current Chromium `BODY` outcomes as RED evidence.
2. Add public Product E2E assertions for the required focus contract.
3. Repair one rendered workspace slice at a time and rerun the bounded local
   probe after each slice.
4. Verify async ownership and preserve already-correct paths.
5. Run focused/full local gates and obtain two independent final reviews.
6. Commit and non-force push implementation, verify exact-SHA CI, then create
   and push a docs-only closure commit and verify its exact-SHA CI.

## Verification Commands

- bounded local Chromium mutation-focus probe using the isolated fixture runtime
- `npm --prefix frontend run test:articles`
- `npm --prefix frontend run test:references`
- `npm --prefix frontend run test:tutor`
- `npm --prefix frontend run test:graph`
- `npm --prefix frontend run build`
- `uv run --project backend --extra dev pytest -q`
- `uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
- repository workflow, suppression, dependency, secret, temporary SBOM,
  artifact, and protected-path gates
- exact-SHA GitHub Actions readback for implementation and closure commits

## Git Plan

- Implementation commit: `fix: preserve workspace mutation focus`
- Push: non-force `main` push after all local gates and final reviews pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-036 mutation focus continuity`
- Push: non-force `main` push after implementation CI evidence is recorded
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Historical Local Gate Result

PASS. Focused Frontend tests passed `139/139`; the production build produced 11
routes; Backend regression passed with 600 tests and 4 skips; Product E2E passed
3/3 complete runs with 225/225 checks per run, restart persistence PASS, and
zero external requests, unexpected console errors, or page errors. Every focus
contract and required viewport passed. Two independent final reviewers reported
0 Critical, 0 Important, and 0 Minor findings. Workflow, suppression, secret,
temporary SBOM, artifact, and protected-path gates pass. The network-dependent
dependency gate passed in exact-SHA CI. The cumulative implementation repair is
complete; this docs-only closure commit still requires exact-SHA main CI.

Initial implementation commit `d864cc1755b050a1dfeb247beaaa8a9d20a2eab3`
passed every remote job except Product E2E. Its first attempt exposed a global
intentional-404 count race; an unchanged-SHA rerun exposed Dashboard-readiness
coupling in the existing same-route brand assertion. The bounded E2E repair now
correlates every accepted 404 console event and response to an exact loopback
endpoint, removes the global 404 allowance, and waits for semantic Dashboard
completion before capturing scroll. Predicate negatives, 10 Article/route 404
probes, 20 Shell stress runs, three complete 225-check Product E2E runs, and two
final independent reviews pass. Exact-SHA repair CI passed in run
[`34023028516`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34023028516).

Cumulative repair commit `39369ea430e942ce12c176fb9a9ca24111e59ef3`
passed exact-SHA main CI run
[`34023028516`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34023028516).
Backend, Frontend, Product E2E, dependency, workflow/suppression, secret, and
SBOM jobs passed; normal-main Docker and release evidence skipped as designed;
uploaded artifacts were zero. This docs-only closure commit consumes the
remaining P3-036 authorization and requires its own exact-SHA main CI readback.

## Stop Conditions

Stop rather than widen scope if an unknown worktree change appears or correct
behavior needs any prohibited Backend, API, persistence, data, dependency,
workflow, external/private, Provider, or release change.

## Current Repair Gate (2026-09-08)

The earlier local and CI results above are historical. Later closure and
repair runs failed, most recently `34178687022` at exact SHA
`6844a4073134902337e58d07bb9d947fcc1d4814`. Its final ledger audit found an
unfinished Tutor activity GET after answer focus and premature test-page
closure. No product-code change is needed for this reproduced lifecycle issue.

The bounded E2E repair now waits for the exact activity read's successful
terminal event before closure. The unchanged audit still rejects timeouts,
headers-only responses, HTTP failures, and ordinary aborts. Local evidence:
3/3 complete E2E runs with 227/227 checks each, restart persistence PASS,
139 Frontend tests, 600 Backend tests with 4 skips, production build PASS,
two independent reviews without blocking findings, and safety gates PASS.
External requests and unexpected console/page errors are zero. The tested
script blob is `7a7bf03e4471b1d7e98b04f99a0d50f68087608c`.

Repair commit message: `test: await Tutor activity before page closure`.
The repair and docs-only closure still require exact-SHA main CI. The task
remains REOPENED / CI EVIDENCE REPAIR; no later task or candidate is authorized
by this record. Detailed evidence is in section 13 of the P3-036 report.

### Subsequent Navigation Caller Repair

The Tutor repair at `d80780506fed84d4def4342c904954e9b049f22d` passed the
non-E2E jobs in CI `34180979475`, but Product E2E rejected two undeclared
response-backed route cancellations. A minimal slow Graph browser probe
reproduced the failure; the Reference page-two return has matching CI evidence.

The initial bounded repair adds existing declaration/settlement/completion
instrumentation to 35 existing navigation callers and exact slow-Graph terminal
validation. No product behavior, classifier, or verification standard changes.
Caller-only snapshot: `db3a61543c4acfcc01b2fc5b0783083197383339`.
Focused slow-Graph execution passes 3/3. The first full invocation on the
preceding 16-caller patch exposed another undeclared Session-to-Reader return;
seven Reader caller pairs are now included without changing its modal races,
and the focused Reader function passes 3/3. An independent follow-up audit
identified 12 further ordinary desktop/mobile round-trip gaps, now covered by
the same existing helpers. These static omissions are not separate reproduced
failures. Its full invocation failed at Reader-to-Graph completion because
Graph canonicalizes query ordering without changing any values. The subsequent
repair adds an opt-in, declaration-frozen query-order alias certificate to the
E2E evidence model. Only exact encoded parameter permutations are eligible;
canonical completion, HTTP 200 response provenance, terminal ordering,
navigation ownership, and zero-or-one alias cancellation are checked. Pending
requests and certificate mutation remain failures. Global URL identity and
existing required-cancellation cardinality do not change. This is a narrowly
scoped classifier extension; it is not product code or an M1 standard change.
Final local gates and two independent reviews pass on script blob
`95feae7950c002127199941e2719832828e87233`: Backend 600/4 skipped, Frontend
139, production build, full HTTP contract including 156 new scenarios, and
3/3 complete Product E2E runs with 227 checks each. Restart persistence passes;
external requests and unexpected console/page errors are zero. Implementation
and docs-only closure exact-SHA CI remain required.

Repair commit message: `test: complete Shell and reference route evidence`.
Section 14 of the task report is the current evidence source. P3-036 remains
REOPENED / CI EVIDENCE REPAIR.
