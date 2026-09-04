# P3-024 Graph Master-Detail Navigation and Focus Continuity Alignment

Canonical task:
`docs/tasks/P3-024_GRAPH_MASTER_DETAIL_NAVIGATION.md`

Status: **PASS / CLOSED**

ORDINARY FRONTEND / TEST / DOCUMENTATION WORK, LOCAL READ-ONLY ARTICLE AND
GRAPH VALIDATION, TEMPORARY ISOLATED FAKE-PROVIDER RUNTIME, LOCAL COMMITS,
NON-FORCE PUSH TO `main`, AND EXACT-SHA CI READBACK: **CONSUMED / CLOSED AFTER
THE DOCS-ONLY CLOSURE COMMIT**

BACKEND / FROZEN M1 / SOURCE RECORD / ARTICLE RECORD / DERIVED ASSET /
DEPENDENCY / LOCKFILE / WORKFLOW / PUBLISHED API CONTRACT MODIFICATION:
**NOT GRANTED**

SOURCE NETWORK / EXTERNAL SEARCH / PRIVATE ZOTERO / REAL OR PAID PROVIDER /
CANDIDATE / TAG / RELEASE / ATTESTATION / DESTRUCTIVE GIT ACTION:
**NOT GRANTED**

## 1. Background

- P3-015 introduced the bounded Graph explorer, and P3-023 added a Concept
  Study Set inside the selected-node inspector.
- A current production-browser audit found that at 390 px the selected detail
  starts about 2,900 CSS px below the page top, after all 20 result cards;
  Knowledge Context is farther below. The current E2E checks prove rendering
  and width, but not viewport reachability, focus continuity, or URL state.
- Selecting a node updates only component state. It does not synchronize the
  canonical `node_id`, move focus, announce the change, or provide a bounded
  mobile return path.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `5448ca90ce8557e99d15d5ff4b3768910a3a5cc6`; ahead / behind is `0 / 0`.
- Entry worktree, index, and untracked set are clean after temporary audit
  screenshots and Playwright metadata were removed. REWORK and `.audit` are
  absent. No v1.2 candidate is assigned.
- Two independent sub-agents reviewed the revised task scope and both returned
  PASS. The repository standing authorization therefore applies without a
  separate user plan-confirmation loop.

## 2. Objective

Make Graph node results, selected detail, and bounded Knowledge Context a
coherent master-detail workspace whose selection, focus, responsive layout,
and browser history remain synchronized without changing Graph data or API
semantics.

## 3. In Scope

- an Explore / Knowledge Context segmented workspace mode
- desktop list-left/detail-right layout with a bounded, scrollable sticky
  inspector
- mobile and zoom Results / Selected segmented navigation with only the active
  panel exposed to the accessibility tree
- persistent detail focus target across idle, loading, loaded, and error states
- originating-result focus restoration with a deterministic heading fallback
- canonical node-selection URL construction and push/replace history rules
- reload and Back/Forward restoration without request or history loops
- bounded safe-label live announcements
- wiring the existing Concept Study Set context action into workspace mode
- focused Frontend tests, Product E2E, read-only real local Graph validation,
  evidence documentation, commits, push, and exact-SHA CI closure

## 4. URL And Interaction Contract

1. Explicit selection of a different node creates one history entry; selecting
   the current node is a no-op.
2. Canonicalization uses replace only. Route restoration never creates a new
   history entry. Workspace and panel mode changes never mutate the URL.
3. The canonical URL contains only validated `node_id`, normalized applied
   `q`, and validated Article workflow fields: `article_id`, `article_title`,
   and `return_to`. Unknown or unsafe parameters are discarded.
4. A node-only URL change preserves in-memory query, type, and page state. A
   changed URL query or reload may reset filters and pagination.
5. Back/Forward and reload make the URL authoritative for selection.
6. Result activation opens Selected on narrow layouts. Mobile or keyboard
   activation focuses the persistent detail region. Back to results preserves
   selection and URL, then restores the originating result if mounted or the
   Results heading fallback otherwise.
7. Context-map or relationship-list selection stays in Context, updates the
   canonical URL, and preserves existing map recentering. Inspect selected
   enters Explore / Selected.

## 5. Out of Scope

- Graph ranking, page size, traversal bounds, entity or relationship semantics
- Backend, schema, API, Graph builder, derived Graph asset, persistence, source,
  Article, or frozen M1 changes
- Concept Study Set, Tutor, Reader, Session, or learning-state contract changes
- dependencies, lockfiles, workflows, global navigation redesign, or broad
  visual restyling
- source access, external search, private Zotero, or real/paid Provider calls
- candidate, tag, Release, attestation, force push, or history rewriting
- Focused Session completion; retain it as a later candidate task

## 6. Planned Execution

1. Persist this alignment, canonical task, and active repository status.
2. Add failing pure tests for canonical URL ownership and history decisions.
3. Implement the minimal Graph workspace navigation model.
4. Integrate responsive modes, stable focus, URL synchronization, live status,
   and bounded sticky detail into the existing Graph components.
5. Extend Product E2E for real viewport intersection, focus restoration,
   canonical history, reload, Back/Forward, context selection, and errors.
6. Validate desktop, 390 x 844, 320 CSS px, and 720 x 450 zoom-equivalent
   behavior in a production browser with no non-loopback requests.
7. Run full regression, build, Product E2E, security, artifact, and protected
   path gates; obtain two independent final implementation reviews.
8. Commit and push implementation, verify exact-SHA CI, then create and push a
   docs-only closure commit and verify its exact-SHA CI.

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-024_GRAPH_MASTER_DETAIL_NAVIGATION.md`
- updated `docs/tasks/CURRENT_TASK.md`
- Graph workspace implementation under `frontend/src/`
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_024_GRAPH_MASTER_DETAIL_NAVIGATION_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- A valid deep link presents Selected immediately at 390 x 844, 320 CSS px,
  and 720 x 450 zoom-equivalent without traversing the Results page.
- Explicit result selection changes the canonical URL once, reaches the
  persistent detail focus target as specified, and Back to results restores a
  deterministic focus target without changing selection or history.
- Back/Forward and reload keep URL and selected UI consistent while preserving
  safe query and Article return context.
- Knowledge Context is one explicit mode action away; Map/List selection,
  recentering, and Inspect selected work without exposing raw IDs.
- Desktop retains simultaneous list/detail exploration. The sticky inspector
  does not clip long details; its first and last controls remain keyboard
  reachable through local scrolling.
- Segmented controls expose complete button-group semantics with `aria-pressed`,
  labelled regions, visible focus, and DOM/focus order matching visual order.
- Deep-link, long-detail, loading, error, retry, same-node, missing-origin,
  context, history, and viewport-intersection cases have automated evidence.
- Three isolated production Product E2E runs pass with zero external requests,
  zero unexpected console/page errors, and no horizontal overflow.
- Backend full tests, focused Frontend tests, production build, workflow,
  suppression, dependency, secret, SBOM, artifact, and protected-path gates
  pass without changing protected code, data, dependencies, or contracts.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Confirmed Test Seams

1. Pure canonical Graph URL and workspace navigation decisions.
2. Browser-visible Graph result/detail/context, focus, and history workflow.

## Stop Conditions

- An unknown worktree change or conflict appears.
- Existing contracts cannot support the workflow without a protected change.
- Required evidence needs source access, private Zotero, external search, or a
  real/paid Provider call.
- A test, build, browser, secret, artifact, review, or CI gate fails without an
  in-scope deterministic repair.
- A candidate, tag, Release, attestation, force push, or history rewrite becomes
  necessary.

## Completion Evidence

- initial implementation commit:
  `86a63bd3c0641e2d3c0e8128a2bd61783fd3ff04`
- initial exact-SHA CI run
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33851459994`
  exposed intermittent production React hydration error 418 in Product E2E
- bounded hydration repair commit:
  `690573eebccc08dc7a73dd7ef4f17fa1eebdd75e`
- repair exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33878201626`
- Backend: 600 passed / 4 skipped
- focused Frontend: 101 passed; production build: PASS
- Product E2E: 10/10 local runs, 73 checks each, zero external requests and
  zero unexpected console/page errors
- hard-reload, responsive, performance, workflow, dependency, secret, SBOM,
  artifact, and protected-path gates: PASS
- final independent implementation reviews: 2 PASS; hydration repair review:
  PASS
- evidence report: `docs/P3_024_GRAPH_MASTER_DETAIL_NAVIGATION_REPORT.md`
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
- candidate, tag, Release, attestation, source, private Zotero, and real
  Provider actions: not performed

## Next Task Staging

`docs/tasks/P3-025_FOCUSED_SESSION_COMPLETION_AND_GUIDED_ADVANCE.md` is staged
as **ALIGNMENT REQUIRED / NOT GRANTED**. This closure grants no P3-025
implementation, runtime access, commit, push, CI, external, or release action.
