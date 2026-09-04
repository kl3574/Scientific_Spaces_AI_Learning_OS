# P3-028 Graph-Reader Round-Trip Reliability

## Status

LOCAL PASS / IMPLEMENTATION READY; EXACT-SHA CI PENDING

## Task Identity

Preserve a learner's exact Knowledge Graph context when opening an Article,
make the round trip keyboard-reachable, and replace ambiguous browser evidence
with URL-first destination checks.

## Authoritative Baseline

- Starting commit: `4daac776bd706cc27c646b31f17fee03c8edeb01`
- Cached `origin/main`: `4daac776bd706cc27c646b31f17fee03c8edeb01`
- Starting ahead / behind: `0 / 0`
- Previous task: P3-027 PASS / CLOSED
- Previous closure CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33915076653`
- Formal version: `v1.1.0`
- Candidate version: not assigned
- Entry worktree, index, and untracked set: clean
- `REWORK.md` and `.audit`: absent
- Two independent audits approved the bounded Graph-Reader reliability scope.

## Background

- Graph Article actions link directly to `/articles/{id}` and discard the
  selected `node_id` and applied Graph query.
- Reader consequently exposes `Back to articles`, so explicit return and hard
  reload cannot recover the originating Graph workspace.
- Graph-origin Reader navigation and the return transition leave keyboard
  focus on the document body rather than a useful destination.
- Existing Product E2E can falsely accept a Graph-to-Reader transition because
  it looks for an Article title that is already visible in the Graph workflow
  banner before proving that the URL changed.
- One historical same-SHA CI run remained on `Loading article` after a 200
  response. Corrected local stress passed 100/100, so no causal framework fix
  is claimed. The Reader still needs bounded failure recovery.

## Goals

1. Preserve a canonical, safe Graph return path containing the supported
   `node_id` and normalized `q` state.
2. Route every Graph-origin Article action through the existing Article detail
   href contract.
3. Move keyboard focus to useful Reader and Graph destinations across the
   round trip.
4. Keep the Reader loading state truthful and provide bounded timeout/error
   recovery without allowing stale responses to publish.
5. Make browser evidence URL-first, destination-scoped, responsive, and
   repeatable.

## Non-Goals

- Native-document navigation or speculative React/Next hydration changes
- Backend, API, Article, Graph data, persistence, or storage changes
- New search, learning, Graph semantics, Tutor, Zotero, or Provider features
- Dependency, framework, lockfile, workflow, candidate, tag, or Release work
- Claiming a root-cause fix for the unreproduced historical loading event

## Return And Focus Contract

1. A Graph return path accepts only local `/graph` state, a supported safe
   `node_id`, and a normalized bounded `q`; hashes, unknown parameters,
   workflow nesting, external origins, and malformed values are removed or
   rejected.
2. Selected Article nodes, provenance Article sources, and Concept Study Set
   Article actions use `createArticleDetailHref` with the current canonical
   Graph return path.
3. Reader exposes `Return to graph` for a non-Concept Graph origin and retains
   the existing Concept-specific return wording.
4. A completed Graph-origin navigation focuses the Reader heading. Returning
   restores the selected Graph region or originating Article action.
5. Only the latest Article request generation may render, write reading
   history, load learning context, or claim focus.
6. Timeout and transport failures expose `Retry article` and preserve the safe
   return action.

## Allowed Changes

- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/components/ConceptStudySetPanel.tsx`
- `frontend/src/components/GraphNodeDetail.tsx`
- `frontend/src/components/GraphView.tsx`
- `frontend/src/lib/articles.ts` only for optional abort-signal support
- `frontend/src/lib/learningWorkflow.ts`
- `frontend/src/lib/graphWorkspace.ts` only for bounded navigation/focus state
- `frontend/tests/learningWorkflow.test.ts`
- `frontend/tests/graphWorkspace.test.ts`
- `frontend/tests/articles.test.ts` only for abort-signal contract coverage
- `scripts/e2e/run_product_e2e.py`
- P3-028 canonical, alignment, current-state, roadmap, README, and report files

## Prohibited Actions

- Backend, published API, frozen M1, source/Article records, derived assets,
  Graph data/builders, persistence schema, or Provider changes
- AppShell or version-bound bootstrap hydration workaround changes without a
  new deterministic causal reproduction
- Dependency, lockfile, framework, workflow, or release metadata changes
- Source access, external search, private Zotero, real/paid Provider, or other
  non-loopback network access
- Candidate, tag, Release, attestation, force push, or history rewrite
- Runtime/private artifacts, secrets, generated corpus, PDFs, HTML dumps,
  committed screenshots, traces, profiles, caches, or local databases

## Deliverables

- Canonical Graph return-path handling for all Graph-origin Article links
- Reader and Graph round-trip focus continuity
- Bounded Article loading failure and retry behavior
- Pure regression tests and corrected Product E2E round-trip coverage
- `docs/P3_028_GRAPH_READER_ROUND_TRIP_RELIABILITY_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. `/graph?node_id=article%3Acrb-formula&q=CRB` produces an Article href with
   that exact canonical state encoded in `from`.
2. Unsafe origins, fragments, malformed or oversized node IDs, unknown
   parameters, and recursive workflow state cannot enter the return href.
3. Selected-node, provenance, and Concept Study Set Article actions preserve
   Graph state.
4. Browser evidence proves the Article pathname before asserting a heading
   scoped to `article#article-start`; loading surfaces are gone.
5. Reader exposes an exact durable Graph return href after client navigation
   and hard reload.
6. Graph-origin Reader completion and the return transition have deterministic
   visible focus without adding extra history entries.
7. Loading exposes one polite busy state; failure/timeout exposes retry; stale
   generations cannot render or persist.
8. The round trip fits 1440 x 900, 390 x 844, 320 x 844, and 720 x 450 without
   clipped targets or horizontal overflow.
9. Corrected 100-transition stress and three full Product E2E runs pass with
   zero external requests or unexpected console/page errors.
10. Focused Frontend suites, production build, full Backend regression, two
    independent final reviews, and repository safety gates pass.
11. Implementation and closure commits each pass exact-SHA main CI; final
    `main` is clean and synchronized.

### CONDITIONAL

No conditional closure. Unverified return, focus, recovery, or browser evidence
keeps the task open.

### BLOCKED

- Graph context or keyboard focus remains lost on the supported round trip.
- Latest-generation ownership cannot be preserved within the allowed paths.
- A required gate needs a prohibited Backend, API, data, dependency, workflow,
  external/private, Provider, or release change.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Persist the bounded task and approved alignment.
2. Add red pure tests for canonical Graph return state and correct the browser
   oracle to require URL-first Reader-root evidence.
3. Implement return-path propagation, destination focus, and bounded loading
   recovery with latest-generation ownership.
4. Validate keyboard Back/Forward, hard reload, stale/failed requests, four
   viewports, and corrected transition stress.
5. Run full local gates, obtain two independent final reviews, and repair all
   in-scope findings.
6. Commit and push implementation, verify exact-SHA CI, then commit and push a
   docs-only closure and verify its exact-SHA CI.

## Verification Commands

- `npm --prefix frontend run test:articles`
- `npm --prefix frontend run test:graph`
- `npm --prefix frontend run build`
- `uv run --project backend --extra dev pytest -q`
- focused corrected 100-transition Graph-to-Reader stress
- `uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
- repository workflow, suppression, dependency, secret, SBOM, artifact, and
  protected-path gates
- exact-SHA GitHub Actions readback for implementation and closure commits

## Artifact And Secret Policy

Only source, tests, and bounded text evidence may be committed. Temporary
screenshots and runtime state must remain outside the repository and be removed
after extracting bounded results.

## Local Verification Result

- focused Frontend: 125/125 PASS
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 PASS, 154 checks each, restart persistence PASS
- corrected 100-transition stress: PASS, CPU throttle 4, cache disabled,
  301/301 Article responses HTTP 200
- required responsive, storage-denial, failure, stale-generation, saved-progress,
  and keyboard-focus scenarios: PASS
- external requests, unexpected console errors, and page errors: 0
- independent final reviews: 2 PASS, no Critical or Important findings
- implementation and closure exact-SHA CI: pending

## Git Plan

- Implementation commit: `fix: preserve Graph Reader round trips`
- Push: non-force `main` push after all local gates pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-028 Graph Reader reliability`
- Push: non-force `main` push after closure evidence is complete
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Stop Conditions

- Unknown worktree changes or conflicts appear.
- Correct behavior requires a prohibited Backend, API, data, dependency,
  workflow, external/private, Provider, or release change.
- Tests, build, E2E, security, artifact, review, or exact-SHA CI fail without a
  deterministic in-scope repair.
