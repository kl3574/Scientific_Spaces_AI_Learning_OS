# P3-024 Graph Master-Detail Navigation and Focus Continuity Report

Status: **PASS / CLOSED**

## 1. Scope And Boundaries

P3-024 turns the existing Graph results, selected-node detail, and Knowledge
Context into one coherent master-detail workspace. The implementation is
Frontend-only apart from focused tests, Product E2E, and governance evidence.

Backend code, frozen M1 modules, source and Article records, Graph builders and
derived assets, dependencies, lockfiles, workflows, published APIs, private
Zotero data, Provider defaults, and release state remained unchanged. No
source request, external search, private Zotero action, real Provider call,
candidate, tag, Release, attestation, force push, or history rewrite occurred.

The user-requested removal of the unrelated agent-authored `AGENTS.md` is kept
in a separate commit and does not change product behavior or P3-024 scope.

## 2. Workspace Contract

- Explore and Knowledge Context are explicit workspace modes.
- Desktop retains simultaneous Results and Selected inspection.
- Narrow and zoomed layouts expose a Results / Selected segmented control and
  keep only the active panel in the accessibility tree.
- The desktop inspector is sticky, height-bounded, and independently
  scrollable so long details do not hide their final controls.
- Existing Concept Study Set actions open Knowledge Context without a hash
  jump or a second navigation model.
- Context map and relationship-list selection stay in Context and preserve
  graph recentering; Inspect selected returns to Explore / Selected.

## 3. Canonical URL And History

The pure `graphWorkspace` model owns canonical Graph URL construction and
history decisions:

- a different valid node selection performs one `pushState`;
- selecting the current node is a no-op;
- query Apply/Clear and URL canonicalization use `replaceState`;
- restoration from reload or Back/Forward never pushes;
- workspace and responsive panel changes never mutate browser history; and
- canonical URLs retain only a validated node, normalized applied query, and
  validated Article workflow context.

Unknown parameters, unsafe identities, and fragments are removed. A node-only
history transition preserves current in-memory filters and pagination, while
a changed route query may intentionally reset them. Back across the `/graph`
route boundary is not intercepted or rewritten.

## 4. Focus And Accessibility

- selection from Results moves focus to one persistent detail region;
- loading, loaded, and error replacement does not discard that focus target;
- Back to results restores the originating result when mounted, otherwise the
  Results heading fallback;
- Context selection keeps focus in the Context region through asynchronous
  graph replacement;
- direct Graph navigation from same-route global search reaches the visible
  selected detail rather than an inactive panel;
- segmented controls use button-group semantics and `aria-pressed`;
- Results, Selected, and Knowledge Context are labelled regions;
- keyboard focus has a visible nonzero outline; and
- live selection messages use safe labels bounded to 120 characters and never
  expose raw node IDs.

## 5. Responsive And Failure Evidence

Automated browser evidence covers desktop, 390 x 844 mobile, 320 CSS px, and
720 x 450 zoom-equivalent viewports. Valid deep links open Selected directly,
without traversing the 20-result page. All checked layouts avoid horizontal
overflow.

The browser suite also covers empty selection, delayed summary loading, detail
loading, detail failure and retry, same-node selection, missing result origin,
context selection, canonicalization, reload, Back/Forward, and route-boundary
Back behavior. Partial failures remain local to their panel and do not create
false success feedback.

## 6. Real Local Data Evidence

Read-only validation used the installed Article and Graph stores:

- Article count: 1,314
- Article Store SHA-256:
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`
- Graph nodes: 53,046
- Graph edges: 82,584
- Graph Store SHA-256:
  `b39efa24e5ab5b4b625114542fd29aa087e504f578fd899c110a3fe5041cb473`
- bounded `Attention` query: 5 results
- bounded selected-node context: 25 nodes / 24 edges

The Article and Graph hashes are unchanged from the P3-023 handoff. A bounded
local-only browser probe rendered desktop and mobile Graph workspaces with
valid map geometry, directly reachable mobile detail, zero non-loopback
requests, and no console or page errors.

## 7. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 39.08s
```

### Frontend

- Article, Reader, workflow, and navigation: 33 passed
- structured References: 3 passed
- Tutor: 20 passed
- Graph, workspace, Concept Study Set, and hydration guard: 27 passed
- global search: 5 passed
- Saved Learning Library: 5 passed
- Focused Session: 8 passed
- focused total: 101 passed
- Next.js 15.5.21 production build: PASS, 11 routes
- `/graph`: 68.3 kB route / 182 kB first load
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py \
  --repeat 10 --frontend-mode start
```

- formal complete runs: 10
- formal successful runs: 10
- checks per run: 73
- Graph responsive reachability, focus, URL, history, context, and retry:
  PASS in every run
- existing Article, Reader, Tutor, Session, Library, Search, and Graph flows:
  PASS in every run
- Chromium: 149.0.7827.55
- external requests: 0 in every run
- unexpected console errors: 0 in every run
- page errors: 0 in every run

## 8. Security And Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action full-SHA pin rate: 100 percent
- explicit workflow and job permission rate: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- dependency audit: PASS, 40 PyPI / 239 npm packages / 0 findings
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM schema, dependency coverage, and forbidden-value checks: PASS
- temporary evidence cleanup: PASS

## 9. Artifact And Protected Paths

- Backend implementation changes: 0
- frozen M1 changes: 0
- source or Article record changes: 0
- Graph builder or derived-asset changes: 0
- dependency, lockfile, or workflow changes: 0
- published API changes: 0
- tracked runtime/private artifact additions: 0
- `.env`, credential, PDF, HTML dump, image, trace, profile, cache, mutable
  store, corpus, generated SBOM, or local E2E result additions: 0

The tracked `.env.example` template remains the only broad environment-pattern
match and is not a secret or runtime artifact.

## 10. Independent Review And Known Risks

Two independent final implementation reviews returned PASS after focus
continuity in Context, same-route global-search handoff, direct 390 x 844 deep
links, fragment canonicalization, and route-driven Context focus were made
explicit and covered by tests.

The initial implementation commit exposed intermittent production React error
418 in exact-SHA CI. Instrumented local reproduction found that Next 15.5.21
starts App Router hydration in a transition lane and its bundled React canary
can yield with a stale hydration cursor. Stable SSR response hashes, a failure
before the first host node was claimed, and reproduction on both Graph and
Articles excluded data drift and a Graph-only DOM mismatch.

The repair uses Next's client instrumentation entry point to remove only that
first bootstrap hydration call from transition context. It is restricted to
production App Router, exact Next `15.5.21`, exact bundled React
`19.2.0-canary-0bdb9206-20250818`, a non-error document, and an empty
before-interactive script queue. It preserves and restores the complete
property descriptor before hydration, delegates every captured later call to
the original transition implementation, expires after one microtask if unused,
and fails open for unsupported runtimes. No framework package was patched and
no dependency or lockfile changed.

Final clean-build stress evidence:

- Graph deep link: 500 / 500 normal hard reloads
- Graph deep link with browser cache disabled: 200 / 200
- Graph at 390 x 844, 320 x 844, and 720 x 450: 100 / 100 each
- Articles search route: 200 / 200
- response variants: one stable SSR hash per route
- page errors / unexpected console errors / external requests: 0 / 0 / 0
- 20-load performance sample per Graph and Articles: zero long tasks; median
  hydrated time 143.15 ms and 115.60 ms respectively
- ten complete Product E2E runs: PASS, including subsequent same-route and
  cross-route navigation, Back/Forward, 404, controlled errors, and persistence

The workaround is intentionally version-bound. A future Next or React upgrade
will skip it and must re-run the hard-reload regression before removal or
replacement.

An independent final repair review returned PASS after checking one-shot
consumption, descriptor restoration, subsequent-transition delegation,
fail-open guards, error-route behavior, diagnostic cleanup, and protected
scope.

The Graph remains bounded by existing result and traversal limits, and its
runtime still depends on external data shape remaining compatible with the
published contracts. P3-024 does not claim graph completeness or alter
learning semantics.

## 11. Exact-SHA Main CI

Initial implementation commit:
`86a63bd3c0641e2d3c0e8128a2bd61783fd3ff04`.

Initial exact-SHA CI:
`https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33851459994`
completed with Product E2E failure; Backend, Frontend, workflow policy,
dependency audit, secret audit, and SBOM validation passed. Docker and release
evidence were skipped as expected for an ordinary `main` push.

Hydration repair commit:
`690573eebccc08dc7a73dd7ef4f17fa1eebdd75e`.

Hydration repair exact-SHA main CI:
`https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33878201626`.

The repair run completed successfully for the exact repair SHA. Backend pytest,
Frontend build, three-run Product E2E, workflow and suppression policy,
dependency audit, secret audit, and SBOM validation all passed. Docker compose
smoke and release evidence were skipped as designed for an ordinary `main`
push. Uploaded artifacts: 0.

Required CI evidence:

- Backend pytest
- Frontend build
- three-run Product E2E
- workflow and suppression policy
- dependency audit
- secret audit
- SBOM validation
- expected Docker and release-evidence skip behavior for a normal `main` push
- zero uploaded artifacts

## 12. Closure State

P3-024 is PASS / CLOSED. Its implementation and bounded hydration repair pass
local acceptance and exact-SHA main CI. This docs-only closure commit requires
its own exact-SHA main CI before final reporting. No v1.2 candidate is assigned.
P3-025 Focused Session Completion and Guided Advance is staged as ALIGNMENT
REQUIRED / NOT GRANTED; no P3-025 implementation is part of this closure.
