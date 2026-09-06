# P3-034 Ordinary Route and Reader Hash Focus Continuity

## Status

LOCAL IMPLEMENTATION PASS / CI PENDING

## Task Identity

Make ordinary same-tab navigation announce its committed destination through
visible keyboard focus, while preserving every existing destination-owned
focus contract and repairing the Reader's explicit mobile hash destinations.

## Authoritative Baseline

- Starting commit and cached `origin/main`:
  `b7159446dd96e893a64c72fa81d9baeb00a14eb1`
- Starting ahead / behind: `0 / 0`
- Entry worktree, index, and untracked set: clean
- Previous task: P3-033 PASS / CLOSED
- P3-033 docs-only closure exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33977608632`
- Required closure jobs: PASS; normal-main Docker and release jobs skipped as
  designed; uploaded artifacts: 0
- `REWORK.md`, `.audit`, and repository-root `AGENTS.md`: absent
- Formal version: `v1.1.0`; candidate version: not assigned
- Two independent read-only GUI reviews identified the same Important ordinary
  route-focus gap. One also reproduced two non-focusable Reader hash targets.
- The product owner explicitly directed bounded platform and GUI improvements
  to continue automatically after independent sub-agent review without
  recurring plan confirmation.

## Evidence

- The desktop primary rail does not pass the existing Shell navigation handler,
  while the mobile Drawer does.
- Route commits without Shell-modal ownership are classified as `invalidate`,
  so the Shell deliberately performs no destination fallback.
- Controlled local Chromium reproduction recorded:
  - desktop Dashboard to Articles: focus remained on the persistent Articles
    rail link;
  - Dashboard content link to Articles: focus became `BODY`;
  - browser Back to Dashboard: focus remained `BODY`;
  - same-route desktop Dashboard activation: URL/history remained stable, but
    focus stayed on the rail link.
- Independent reviewers additionally reproduced Article List to Reader,
  Reader to Tutor, References/Graph rail navigation, and ordinary mobile
  content navigation losing focus.
- Reader `#article-outline` and `#article-start` targets are not programmatically
  focusable, while the managed outline headings and Reading tools target are.
- P3-030 explicitly excluded generic navigation focus policy, and P3-033 kept
  this work as a separate candidate.

## Goals

1. Give ordinary committed local route transitions a Shell main fallback.
2. Preserve focus already claimed by a meaningful destination inside main.
3. Include desktop rail and brand navigation in the accepted Shell navigation
   lifecycle, including same-route behavior.
4. Apply the same ownership rule to unmodalized browser Back and Forward.
5. Keep query/history, delayed transition, cancellation, and stale callback
   handling deterministic.
6. Make Reader Outline, Reading tools, and Back to article hash destinations
   explicitly focusable and visibly focused.
7. Add user-visible browser regression evidence across desktop and mobile.

## Non-Goals

- Backend, API, provider, persistence, schema, source, Article record, corpus,
  Graph data, Reference data, or derived-asset changes
- Replacing the router, introducing a new navigation framework, or changing
  published URL contracts
- Restyling route views or changing learning, Tutor, Graph, Search, Reference,
  Zotero, or corpus behavior
- Dependencies, lockfiles, workflow, candidate, version, tag, Release, or
  attestation changes
- Source network, external search, private Zotero, or real/paid Provider access

## Public Test Seams

1. `navigation.ts` pure route-commit and fallback-decision helpers.
2. The rendered application Shell observed through active element, URL,
   history length, visible focus, and committed destination content.
3. The rendered Reader's public Outline, Reading tools, and Back to article
   links and their explicit fragment targets.

## Focus Contract

1. Initial hydration never moves focus.
2. Accepted Search and Drawer navigation retain their existing pending-route
   ownership and stale-operation cancellation.
3. A changed route without pending modal ownership is an ordinary committed
   route, not a stale-operation invalidation.
4. After commit, a connected focused element inside `main#main-content` owns
   focus. Otherwise Shell focuses main without scrolling.
5. A mismatched pending route remains invalid and cannot claim focus.
6. Desktop rail and brand navigation use the existing accepted Next.js
   navigation event. Same-route activation creates no history entry and focuses
   current main; modified or new-tab activation is not intercepted.
7. Hash-only changes stay outside Shell route identity. Reader hash links focus
   their exact targets locally and expose a visible focus treatment.
8. New route, modal, or focus operations invalidate older deferred callbacks.

## Allowed Changes

- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/PrimaryNav.tsx`
- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/components/StructuredReferencesPanel.tsx`
- `frontend/src/lib/navigation.ts`
- `frontend/tests/navigation.test.ts`
- `frontend/scripts/test-articles.sh`
- `scripts/e2e/run_product_e2e.py`
- this canonical task, `alignment.md`, `docs/tasks/CURRENT_TASK.md`,
  `docs/00_PROJECT_STATE.md`, `roadmap.md`, `docs/V1_2_ROADMAP.md`, `README.md`,
  and the P3-034 evidence report

## Prohibited Actions

- Any `backend/**`, API, persistence, storage, frozen M1, source/Article record,
  corpus, Graph/Reference data, matcher, provider, or derived-asset change
- Any dependency, lockfile, framework configuration, workflow, release/version,
  candidate, tag, Release, or attestation change
- Any source access, external search, private Zotero read/mutation, real/paid
  Provider call, or non-loopback browser request
- Force push, history rewrite, destructive Git action, or published-tag change
- Runtime/private artifacts, secrets, databases, PDFs, downloaded HTML, images,
  screenshots, traces, profiles, caches, or generated corpora in Git

## Deliverables

- Pure ordinary-route classification and main-fallback policy
- Shell integration for desktop rail, brand, ordinary Link, and history commits
- Explicit Reader hash focus targets
- Focused pure tests and Product E2E route/hash/history/ownership coverage
- `docs/P3_034_ORDINARY_ROUTE_AND_HASH_FOCUS_CONTINUITY_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. Initial hydration leaves document focus unchanged.
2. Keyboard activation of each desktop primary workspace reaches the correct
   route and settles on visible main focus unless that destination owns a more
   specific focus target.
3. Dashboard, Articles, Saved, Session, Reader, References, Graph, and Tutor
   ordinary local links never settle on `BODY` or a source-route Shell link.
4. Browser Back and Forward restore the represented pathname/query/hash and
   apply the same destination-owner/main-fallback rule without adding history.
5. Different-route activation creates exactly one history entry. Same-route
   rail or brand activation creates none and does not change URL or scroll.
6. A delayed destination is not focused before route commit; a superseding
   navigation or destination-owned target cannot be overwritten by stale Shell
   focus.
7. Search, Drawer, Graph, Reader, and Reference-owned focus behavior remains
   intact with no intermediate Shell focus theft.
8. Reader Outline, Reading tools, and Back to article links focus their exact
   visible fragment targets; managed outline entries still focus their heading.
9. Modified/new-tab and external activation remains native and is never
   converted into same-tab Shell navigation.
10. Desktop, `390x844`, `320x844`, and `720x450` coverage records no page-level
    overflow, focus loss, external request, or unexpected console/page error.
11. Focused Frontend tests, production build, full Backend regression, three
    Product E2E runs, two independent final reviews, and repository safety gates
    pass.
12. Implementation and closure commits each pass exact-SHA main CI; final main
    is clean and synchronized.

### CONDITIONAL

No conditional closure. Unverified route or hash focus ownership keeps the task
open.

### BLOCKED

- Ordinary local navigation can still settle on `BODY` or a source Shell link.
- Shell fallback can steal focus from a destination-owned target.
- Correctness requires a prohibited route-view, Backend, API, persistence,
  dependency, workflow, external/private, Provider, or release change.
- A required test, review, safety, artifact, or exact-SHA CI gate cannot be
  repaired within the allowlist.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Persist this independently reviewed bounded task and active alignment.
2. Add one failing pure route/fallback test and one failing browser route slice.
3. Implement ordinary commit classification and destination-aware Shell fallback.
4. Add desktop rail/brand same-route ownership and Reader hash focus targets.
5. Extend route/history/delay/ownership/mobile E2E coverage one slice at a time.
6. Run focused/full local gates, obtain two independent final reviews, and
   repair every in-scope Critical or Important finding.
   Two independent reviews authorized the bounded structured-reference panel
   ownership repair after both identified its internal autofocus as an
   Important conflict with the Reader focus state machine.
7. Commit and non-force push implementation, verify exact-SHA CI, then create
   and push a docs-only closure commit and verify its exact-SHA CI.

## Verification Commands

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

## Local Evidence

- focused Frontend: 139/139 PASS
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 runs, 217 checks each; restart persistence PASS
- ordinary route, query/history, delay/cancellation, destination ownership,
  Reader fixed/managed/unmanaged hash, and four required viewport cases: PASS
- external requests, unexpected console errors, and page errors: 0
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- workflow, suppression, dependency, secret, temporary SBOM, artifact, and
  protected-path gates: PASS
- implementation commit and exact-SHA main CI: pending

## Git Plan

- Implementation commit: `fix: preserve ordinary route focus continuity`
- Push: non-force `main` push after all local gates pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-034 route focus continuity`
- Push: non-force `main` push after implementation CI evidence is recorded
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Stop Conditions

Stop rather than widen scope if an unknown worktree change appears or correct
behavior needs any prohibited Backend, route-view beyond the Reader hash targets,
API, persistence, dependency, workflow, external/private, Provider, or release
change.
