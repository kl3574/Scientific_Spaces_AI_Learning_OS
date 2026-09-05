# P3-032 Related-Paper Context Ownership and Accessible Feedback

## Status

PASS / CLOSED

## Task Identity

Make the Reader's Related Papers workspace truthful, Article-owned, safe under
concurrent requests, and usable with keyboard and assistive technology without
changing the existing Zotero API or any private Zotero data.

## Authoritative Baseline

- Starting commit and cached `origin/main`:
  `00508b844d63016a5f7e4321725b245cdde4ef4e`
- Starting ahead / behind: `0 / 0`
- Entry worktree, index, and untracked set: clean
- Previous task: P3-031 PASS / CLOSED
- P3-031 implementation and docs-only closure exact-SHA main CI: PASS
- `REWORK.md`, `.audit`, and repository-root `AGENTS.md`: absent
- Formal version: `v1.1.0`; candidate version: not assigned
- Two independent read-only scope reviews identified one Critical Article-
  ownership defect and converged on the bounded contract below.
- The product owner explicitly directed bounded platform and GUI work to run
  automatically after independent sub-agent review without recurring plan
  confirmation.

## Evidence

- A delayed Article A link-list response can overwrite Article B state because
  current requests have no Article/generation owner.
- A stale A row can therefore combine its item key with B's current `articleId`
  and issue a DELETE against the wrong Article.
- Search, link, unlink, and export have no duplicate activation or stale-result
  guards.
- The first Unlink activation immediately mutates persistence and provides no
  confirmation or response-loss reconciliation.
- Initial loading is rendered as a false empty state; failures can coexist with
  the same empty claim.
- Search, relationship, and note controls lack persistent labels; repeated
  actions lack target-specific accessible names; status and BibTeX results do
  not have deterministic announcement or focus behavior.
- Existing focused and Product E2E suites do not cover this workspace.

## Goals

1. Bind every Related Papers read, mutation, and export to an exact Article,
   generation, operation, and relevant query/item/link-set identity.
2. Prevent stale completions and duplicate activations from changing another
   Article, issuing extra mutations, or replacing newer results.
3. Make link-list loading, empty, unavailable, failed, pending, success, and
   uncertain states distinct and truthful.
4. Require an Article-owned two-phase confirmation before unlinking a project
   relation while stating that the Zotero library item is retained.
5. Reconcile rejected or response-lost mutations with exactly one read-only
   link-list request and never replay a mutation automatically.
6. Add persistent labels, target-specific action names, live feedback, stable
   focus, and a named keyboard-usable BibTeX disclosure.
7. Keep populated, pending, failure, confirmation, and long BibTeX states usable
   without page-level overflow at all required viewports.

## Non-Goals

- Backend, API, provider, persistence, schema, or Zotero Desktop changes
- Editing an existing link's relation type or note through silent upsert
- Deleting any Zotero library item, attachment, PDF, or source record
- Copy/download controls or a standalone Zotero Library redesign
- Reader learning/session, Search, Tutor, Graph, References, or corpus changes
- Dependencies, lockfiles, workflows, candidate, tag, Release, or attestation
- Real/private Zotero access, source access, external search, or paid Providers

## Interaction And Ownership Contract

1. Each operation token contains `articleId`, `generation`, `operationId`, and
   `kind`, plus query, item key, or link-set fingerprint when applicable.
2. Article changes invalidate every old owner and reset links, query, results,
   note, feedback, confirmation, and BibTeX before controls become usable.
3. Query edits invalidate old search results. Repeated submission of the same
   pending query is a no-op; a new query may supersede it, and only the latest
   owned result may render.
4. Provider availability and the persisted project link list load
   independently. Provider unavailability disables Search, Link, and BibTeX
   but does not hide successfully loaded local project links.
5. Only one link/unlink mutation intent or request may exist per panel. An
   already-linked search result is rendered as `Linked` and sends zero POSTs.
6. First Unlink activation creates an immutable Article/generation/item intent,
   sends zero DELETEs, and focuses Cancel. The confirmation states that the
   project link and relationship note are removed permanently while the Zotero
   library item remains.
7. Confirm emits exactly one DELETE. Cancel, Escape, navigation before confirm,
   and repeated confirmation emit zero additional DELETEs.
8. A confirmed successful mutation updates the current list functionally and
   invalidates BibTeX without an automatic list reload.
9. A rejected or lost mutation response triggers exactly one owned link-list
   reconciliation and never replays POST or DELETE. If readback establishes the
   outcome, render it truthfully. If readback also fails, preserve the current
   rendering, label persistence unconfirmed, lock mutations, and require a
   manual read-only reload.
10. BibTeX export is owned by the current link fingerprint. Repeated activation
    while pending emits one POST; Article or link-set changes invalidate output.
    The UI does not claim that every requested record was exported.
11. The exact-count guarantee is scoped to one panel instance, not backend
    exactly-once behavior or multi-tab concurrency.

## Allowed Changes

- `frontend/src/components/ZoteroLinksPanel.tsx`
- `frontend/src/components/ArticleDetailView.tsx` only for an Article `key`,
  the Reading tools grid item's `min-width` constraint, and a synchronous
  ordinary Article-to-Article `main` / destination-heading focus handoff
- `frontend/src/lib/zotero.ts`
- `frontend/src/lib/zoteroLinkOperations.ts`
- `frontend/tests/zoteroLinkOperations.test.ts`
- `frontend/scripts/test-references.sh`
- `scripts/e2e/run_product_e2e.py`
- this canonical task, alignment, current-state, roadmap, README, and report
  files for P3-032

## Prohibited Actions

- Any `backend/**`, API, storage, provider, frozen M1, source/Article record,
  corpus, Graph, reference store, or derived-asset change
- Any Zotero Desktop/private-library mutation or non-loopback access
- Any dependency, lockfile, framework configuration, workflow, release/version,
  tag, attestation, or candidate change
- Any unrelated Reader, Search, Tutor, Graph, or learning behavior change
- Force push, history rewrite, or destructive Git operation
- Runtime/private artifacts, credentials, databases, PDFs, HTML dumps, images,
  screenshots, traces, profiles, caches, or generated corpora in Git

## Deliverables

- Pure Article/generation/operation ownership and functional list helpers
- Truthful, accessible Related Papers workspace with safe mutation reconciliation
- Focused helper tests and Product E2E request/focus/responsive regressions
- `docs/P3_032_RELATED_PAPER_CONTEXT_OWNERSHIP_AND_ACCESSIBLE_FEEDBACK_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. Initial loading, successful empty, unavailable-provider, and failed-list
   states are mutually truthful and expose appropriate busy/live semantics.
2. Search labels, loading, no-match, result count, failure, supersession, and
   exact request counts pass for mouse and keyboard input.
3. Article A delayed completions cannot alter Article B data, feedback, output,
   focus, controls, or request targets.
4. Rapid Link activation emits one POST; linked results emit zero POSTs; all
   competing mutation launchers remain locked while intent/request is active.
5. Unlink open/cancel/Escape/navigation emits zero DELETEs; confirmed repeated
   activation emits exactly one DELETE and keeps connected visible focus,
   including the ordinary Article-to-Article route handoff.
6. Mutation rejection or response loss emits one mutation plus one read-only
   reconciliation, never replays, and represents established or uncertain state
   accurately.
7. BibTeX is a named disclosure with exactly one pending export, explicit empty,
   error, and result states, keyboard-focusable local scrolling, and immediate
   invalidation when Article or links change.
8. Target-specific action names, persistent form labels, atomic status, alerts,
   and success/failure focus behavior are verified.
9. Populated long content, pending, alerts, confirmation, and long BibTeX pass
   at `1440x900`, `390x844`, `320x844`, and `720x450` without page overflow or
   clipped controls.
10. Focused Frontend tests, production build, full Backend regression, three
    Product E2E runs, two final independent reviews, and repository safety gates
    pass with zero unexpected external requests or console/page errors.
11. Implementation and closure commits each pass exact-SHA main CI; final main
    is clean and synchronized.

### CONDITIONAL

No conditional closure. Any unverified cross-Article mutation, uncertain-state,
request-count, or focus contract keeps the task open.

### BLOCKED

- A stale completion can affect another Article or target a current Article
  with an old item key.
- A mutation occurs before confirmation, repeats, or is automatically replayed.
- An uncertain persistence result is displayed as confirmed.
- Focus disconnects, falls to `body`, or crosses Article generations.
- Correctness requires a prohibited Backend, API, dependency, private/external,
  workflow, or release change.
- A required test, review, safety, artifact, or exact-SHA CI gate cannot be
  repaired within the allowlist.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Persist the reviewed bounded task and active alignment.
2. Add failing pure ownership/list-transition tests and browser regressions.
3. Implement Article-owned reads, one mutation lane, unlink confirmation,
   reconciliation, accessible feedback, and BibTeX disclosure.
4. Run focused/full local gates, obtain two independent final reviews, and
   repair every in-scope Critical or Important finding.
5. Commit and non-force push the implementation, verify exact-SHA CI, then
   create and push a docs-only closure commit and verify its exact-SHA CI.

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

## Local Gate Result

- focused Frontend tests: PASS, 120/120
- production build: PASS, 11 routes
- Backend regression: PASS, 600 passed / 4 skipped
- Product E2E: PASS, 3/3 complete runs; restart persistence PASS
- external requests, unexpected console errors, and page errors: 0
- final independent reviews: PASS, 2/2, 0 Critical / 0 Important
- workflow, suppression, secret, temporary SBOM, artifact, and protected-path
  gates: PASS
- local dependency audit: deferred because it requires prohibited registry
  access; exact-SHA CI evidence is required
- evidence report:
  `docs/P3_032_RELATED_PAPER_CONTEXT_OWNERSHIP_AND_ACCESSIBLE_FEEDBACK_REPORT.md`
- implementation commit:
  `e7b317042df728e568bb5f4d328c678ac3102f0a`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33965187190`
- required implementation jobs: PASS; normal-main Docker and release evidence
  skipped as designed; uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting

## Git Plan

- Implementation commit:
  `fix: make Related Papers interactions Article-owned`
- Push: non-force `main` push after local gates pass
- CI: exact-SHA implementation readback required
- Closure commit:
  `docs: close P3-032 Related Papers reliability`
- Push: non-force `main` push after implementation CI evidence is recorded
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Stop Conditions

Stop rather than widen scope if an unknown worktree change appears or correct
behavior needs any prohibited Backend, API, persistence, dependency, workflow,
external/private, Provider, or release change.
