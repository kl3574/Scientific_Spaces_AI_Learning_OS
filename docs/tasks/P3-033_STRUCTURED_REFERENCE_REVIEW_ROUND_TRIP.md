# P3-033 Structured Reference Review Round Trip and Context Ownership

## Status

LOCAL IMPLEMENTATION PASS / IMPLEMENTATION CI PENDING

## Task Identity

Make a structured reference discovered while reading directly reviewable in the
standalone References workspace, keep every list/detail/candidate result owned
by the selected reference and route state, and provide a reliable return to the
originating Article reference without changing Backend or Zotero data.

## Authoritative Baseline

- Starting commit and cached `origin/main`:
  `306f207c5e5953064dceef3e0e0a5ffbd26b9136`
- Starting ahead / behind: `0 / 0`
- Entry worktree, index, and untracked set: clean
- Previous task: P3-032 PASS / CLOSED with implementation and closure exact-SHA
  main CI PASS
- `REWORK.md`, `.audit`, and repository-root `AGENTS.md`: absent
- Formal version: `v1.1.0`; candidate version: not assigned
- Two independent read-only GUI reviews found Important gaps. The product-flow
  review identified this bounded reference round trip as the highest-value
  immediate task; application-wide ordinary-route focus continuity remains a
  separate candidate.
- The product owner explicitly directed bounded platform and GUI work to run
  automatically after independent sub-agent review without recurring plan
  confirmation.

## Evidence

- Article Detail renders each structured reference only as an external link;
  it cannot open that exact record in the References workspace.
- `/zotero` loads one 20-record page, auto-selects its first record, and offers
  no reference search, type/classification filter, or `reference_id` deep link.
- The current reference corpus contains about 12,859 records, so page-by-page
  select navigation is not a viable review workflow.
- Candidate state is not cleared or owner-checked during a reference change;
  a previous record's candidates can remain visible while the new request is
  pending.
- Existing APIs already support bounded reference query/filter, single-record
  provenance, and candidate lookup, so the defect can be fixed in Frontend only.
- Browser inspection found raw evidence visually dense; this task confines a
  concise preview to the standalone review so it does not alter the Reader's
  existing outline/scroll geometry.
- Existing focused and Product E2E suites do not exercise `/zotero` or an
  Article-reference-to-review round trip.

## Goals

1. Add an internal review action for each Article structured reference that
   targets the exact `reference_id` and carries a bounded local Article return.
2. Make reference query, type, classification, page, selection, and candidate
   filter canonical URL state that survives reload and Back/Forward.
3. Replace the page-only selector with a searchable, filterable reference
   result list and an explicit selected-record evidence/detail workspace.
4. Bind reference-list, detail, and candidate requests to exact request
   generations and identities; stale completions must never render.
5. Distinguish loading, empty, failed, selected, candidate-empty, and retry
   states with accurate accessible status and focus behavior.
6. Return to the exact Article reference row and restore visible keyboard focus
   after its asynchronous page loads.
7. Present concise selected-record evidence in the standalone review while
   exposing every provenance occurrence available from the frozen bounded
   v1.2 detail contract, its complete source count, truthful truncation, and
   the Reader's existing evidence.
8. Keep the master-detail review usable without page-level overflow at desktop,
   mobile portrait, narrow mobile, and short landscape viewports.

## Non-Goals

- Backend, API, provider, persistence, schema, extractor, matcher, or store changes
- Creating, editing, linking, unlinking, or deleting Zotero records
- Reading or mutating any private Zotero Desktop library
- Changing reference evidence, source Article content, or derived assets
- General application-wide route-focus behavior outside this round trip
- Reader learning/session, Tutor, Graph, Search shell, or corpus changes
- Dependencies, lockfiles, workflows, candidate, version, tag, Release, or attestation
- Source network, external search, or real/paid Provider access

## Route And Ownership Contract

1. Canonical review state contains bounded `q`, `reference_type`,
   `classification`, positive `page`, exact `reference_id`, candidate filter,
   and an optional sanitized local Article `return_to` path.
2. Only local `/articles/{id}` return paths are accepted. External,
   credentialed, malformed, mismatched, overlong, or unrelated routes fall back
   safely and are never rendered as navigation targets.
3. Filter submission resets page and selection. Page and record selection use
   one canonical history entry per accepted user action; Back, Forward, and
   reload restore the represented state.
4. List, detail, and candidate operations each carry a monotonic generation and
   exact request key. A completion may render only when it still owns both.
5. Selection immediately hides previous detail/candidates. Candidate output is
   additionally valid only when its response `reference_id` equals the current
   selected record.
6. A deep-linked selected record remains reviewable even when it is not present
   on the current result page; its detail endpoint is the authority.
7. Candidate filtering is local presentation state over the currently owned,
   bounded candidate response and does not claim a full-library search.
8. The Article return target encodes the source Article, reference page, and
   exact row anchor. After the row exists, focus moves to that row without
   crossing Article/reference generations.
9. The exact-count and ownership guarantees are scoped to this Frontend
   instance, not Backend exactly-once or multi-tab behavior.

## Allowed Changes

- `frontend/src/app/zotero/page.tsx`
- `frontend/src/components/ZoteroLibraryView.tsx`
- `frontend/src/components/ZoteroReferenceReview.tsx`
- `frontend/src/components/StructuredReferencesPanel.tsx`
- `frontend/src/lib/references.ts`
- `frontend/src/lib/referenceReview.ts`
- `frontend/tests/references.test.ts`
- `frontend/tests/referenceReview.test.ts`
- `frontend/scripts/test-references.sh`
- `scripts/e2e/run_product_e2e.py`
- this canonical task, `alignment.md`, `docs/tasks/CURRENT_TASK.md`,
  `docs/00_PROJECT_STATE.md`, `roadmap.md`, `docs/V1_2_ROADMAP.md`, `README.md`,
  and the P3-033 evidence report

## Prohibited Actions

- Any `backend/**`, API, provider, persistence, storage schema, frozen M1,
  source/Article record, corpus, Graph, reference store, matcher, or derived-asset change
- Any Zotero Desktop/private-library read or mutation, real Provider call,
  source access, external search, paid request, or non-loopback browser request
- Any dependency, lockfile, framework configuration, workflow, release/version,
  tag, attestation, or candidate change
- Any unrelated Reader, shell navigation, Search, Tutor, Graph, or learning change
- Force push, history rewrite, destructive Git action, or published-tag change
- Runtime/private artifacts, secrets, databases, PDFs, downloaded HTML, images,
  screenshots, traces, profiles, caches, or generated corpora in Git

## Deliverables

- Pure route parsing/serialization, local-return sanitization, and request-owner helpers
- Article reference review links, standalone evidence disclosure, and return focus
- Searchable/filterable References master-detail workspace with owned requests
- Focused pure tests and Product E2E deep-link/race/history/focus/responsive coverage
- `docs/P3_033_STRUCTURED_REFERENCE_REVIEW_ROUND_TRIP_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. Every Article structured reference can open `/zotero` at its exact
   `reference_id`; no page scanning or identity guessing is required.
2. Search, type, classification, page, selected record, candidate filter, and
   safe Article return state round-trip canonically through the URL and survive
   reload plus Back/Forward.
3. The selected workspace displays reference identity, type, classification,
   source Article, source section, source count, bounded evidence, and
   provenance truthfully.
4. Delayed list/detail/candidate completions cannot replace newer state;
   A-to-B switching never renders A detail or candidates under B.
5. Loading, no-results, unavailable/failed, retry, selected, no-candidate, and
   filtered-empty states are distinct and expose correct busy/live semantics.
6. Article return accepts only the owned source Article target, restores the
   saved structured-reference page, and focuses the exact visible row after
   asynchronous loading.
7. Standalone review evidence is concise by default; the collapsed disclosure
   contains every occurrence returned by the frozen 20-row v1.2 bound with
   source Article identity, complete occurrence count, and explicit truncation.
   Long identifiers/evidence/candidate metadata wrap without hiding provenance
   or changing Reader scroll geometry. Unbounded provenance pagination remains
   a separate API-revision candidate and is not claimed by this Frontend task.
8. Keyboard use and focus remain visible; controls have persistent labels and
   target-specific names; direct load does not strand focus on `body` after an
   explicit round-trip action.
9. Deep-link, filter, failure/retry, rapid-switch, history, and return semantics
   pass in the desktop integration context. Representative selected-detail and
   candidate-filter focus plus layout/overflow checks pass at `1440x900`,
   `390x844`, `320x844`, and `720x450` with zero page-level horizontal overflow.
10. Focused Frontend tests, production build, full Backend regression, three
    Product E2E runs, two final independent reviews, and repository safety gates
    pass with zero unexpected external requests or console/page errors.
11. Implementation and closure commits each pass exact-SHA main CI; final main
    is clean and synchronized.

### CONDITIONAL

No conditional closure. Any stale-record rendering, unsafe return, broken
history restoration, or unverified focus/route contract keeps the task open.

### BLOCKED

- The exact reference cannot be selected without Backend/API changes.
- A stale list, detail, or candidate completion can render under newer state.
- A return target can escape the local owned Article or focus the wrong record.
- Correctness requires private Zotero, source/external network, dependency,
  workflow, schema, storage, or frozen-module changes.
- A required test, review, safety, artifact, or exact-SHA CI gate cannot be
  repaired within the allowlist.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Persist this reviewed bounded task and active alignment.
2. Add failing pure route/ownership tests and browser regressions.
3. Implement canonical URL state, safe local return, owned list/detail/candidate
   reads, and the master-detail review workspace.
4. Add Article review entry, concise evidence disclosure, and asynchronous
   exact-row return focus.
5. Run focused/full local gates, obtain two independent final reviews, and
   repair every in-scope Critical or Important finding.
6. Commit and non-force push the implementation, verify exact-SHA CI, then
   create and push a docs-only closure commit and verify its exact-SHA CI.

## Verification Commands

- `npm --prefix frontend run test:references`
- `npm --prefix frontend run test:articles`
- `npm --prefix frontend run test:tutor`
- `npm --prefix frontend run test:graph`
- `npm --prefix frontend run build`
- `uv run --project backend --extra dev pytest -q`
- `uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
- repository workflow, suppression, dependency, secret, temporary SBOM,
  artifact, and protected-path gates
- exact-SHA GitHub Actions readback for implementation and closure commits

## Git Plan

- Implementation commit: `feat: add structured reference review round trip`
- Push: non-force `main` push after all local gates pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-033 reference review workflow`
- Push: non-force `main` push after implementation CI evidence is recorded
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Stop Conditions

Stop rather than widen scope if an unknown worktree change appears or correct
behavior needs any prohibited Backend, API, persistence, dependency, workflow,
external/private, Provider, or release change.

## Local Gate Result

The final worktree passes 131 focused Frontend tests, the 11-route production
build, 600 Backend tests with 4 skipped, three complete Product E2E runs,
restart persistence, two independent final reviews, and all local non-network
safety gates. External requests and unexpected console/page errors are zero.
The implementation commit still requires exact-SHA main CI before closure.
