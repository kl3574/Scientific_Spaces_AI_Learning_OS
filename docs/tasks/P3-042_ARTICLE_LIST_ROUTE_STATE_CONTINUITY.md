# P3-042 Article List Route State Continuity

Status: OPEN / CI BLOCKED

Publication 8e38d0359df84e67af76541195ebeda99226e1df is synchronized.
Exact-SHA CI 34354525791 fails Product E2E at the existing hashless guided
Reader Back focus assertion (run_product_e2e.py:19480). Six other required jobs
pass. Diagnose that precise failure on an owned synthetic runtime; do not rerun
CI blindly, relax the assertion, close this task or start the Graph replay.
Reader/Shell product edits remain outside this task and require a separately
reviewed bounded revision. The local acceptance below remains historical evidence.

Local product and regression gates pass: Backend 1147/4 skipped, Frontend 179,
owned build, unchanged original E2E 3 x 298/restart/image and the corrected
native36/component6 counterpart. The latter has zero stderr through process
exit; the report preserves its SDK diagnostic RED and exact scope of evidence.
Security/SBOM and two independent implementation/scope reviews pass. These local
gates preceded publication; failed exact-SHA CI now holds closure. Preserve the
published implementation during diagnosis. No further generic user confirmation
is required.

## Objective And Evidence

Keep the Article List's applied query, sort, page, results and URL consistent
through local controls, same-component Shell navigation and browser history.
Preserve unsubmitted search drafts during local URL echoes, sorting and paging.

Entry main, cached origin/main and remote main are
dc7411c73802df1255376996c6daf5810f2a87a9. P3-041 exact-SHA CI 34332407397
completed SUCCESS on 2026-09-09T09:50:41Z: all seven required jobs pass,
original E2E 3 x 298, four restart checks and separate image profile 3 x 8.
Unexpected errors/external requests and uploaded artifacts are zero. Docker
and release evidence jobs are policy-skipped. P3-041 is PASS / CLOSED.
P3-039 stays OPEN / DEFERRED, historical cause UNKNOWN.

A qualified unchanged-production probe starts at the filtered Attention list,
activates the native Articles link and reaches bare /articles with main focus
and history 2 -> 3. Across 117 samples over 30.94 seconds the previous query,
sort and one-result UI persist. Reloading the same URL correctly returns all
three fixture Articles and default filters, backed by API 200. Audits, source,
fixture and owned-build bindings and cleanup pass. This is behavioral RED,
not by itself proof of a React root cause. The report records its exact binding.

The owner's standing direction permits independent review followed by automatic
bounded execution without another plan confirmation. Two prospective reviews
approve the following scope and mandatory ownership/regression contracts.
The initial-only local-state hypothesis must be tested through actual component
wiring, not declared repaired because a pure helper passes.

## Exact Allowed Paths

- frontend/src/components/ArticleListView.tsx
- frontend/src/lib/articleListNavigation.ts
- frontend/tests/articleListNavigation.test.ts
- frontend/scripts/test-articles.sh
- scripts/e2e/check_article_list_navigation.py
- scripts/e2e/run_product_e2e.py
- backend/tests/test_article_list_navigation.py
- backend/tests/test_graph_provenance_return.py
- docs/tasks/P3-042_ARTICLE_LIST_ROUTE_STATE_CONTINUITY.md
- docs/P3_042_ARTICLE_LIST_ROUTE_STATE_CONTINUITY_REPORT.md
- alignment.md
- README.md
- docs/00_PROJECT_STATE.md
- docs/tasks/CURRENT_TASK.md
- roadmap.md
- docs/V1_2_ROADMAP.md
- docs/tasks/P3-041_READER_INLINE_IMAGE_RENDERING.md
- docs/P3_041_READER_INLINE_IMAGE_RENDERING_REPORT.md

At most 18 paths. Optional helper/contract paths are not permission to broaden
directories. The last two paths permit prior-task closure receipts only.
Preserve and exclude scripts/e2e/graph_frame_oracle.js, SHA-256
21b548fe1a6c7923a016053e94881c955a0a4c92b2d33fe2020fed4c8bbd9b34.

## State And Interaction Contract

1. Reuse existing Article list parsing/canonicalization without changing its
   rules. Validate hook snapshots against the actual browser pathname/search
   before accepting external navigation or canonicalizing its URL.
2. Track local replacements separately from external navigation. Remove the
   unconditional state-to-URL effect; it must not overwrite navigation with
   an old tuple. Accept external q/sort/page together and reconcile the draft.
3. Local Search/Clear/Sort/paging still replace the current history entry;
   Shell still owns push and focus. Back/Forward must not add history entries.
   Canonically equivalent parameters must not cause duplicate result requests.
4. A local URL echo must not erase subsequently typed text, reset selection,
   refetch or move focus. Sorting and paging preserve unsubmitted drafts.
   Same-condition Search remains an explicit refresh. Preserve Clear/Retry
   focus and all existing selection/session-capture behavior.
5. Invalidate superseded generations and selection when a transition is
   accepted, not only when its next request starts. Preserve requestKey and
   monotonic generation protections, including A -> B -> A. Old success or
   failure cannot restore rows/selection, overwrite current results or steal
   focus. Pending/failed new generations expose no actionable stale rows.

## Execution And Required Verification

1. Record alignment and entry/RED evidence; add focused route ownership tests.
2. Implement only the bounded Article List synchronization and optional pure
   helper. Borrow Graph's snapshot/echo pattern, not its domain or focus logic.
3. Retain the original three-Article RED/GREEN browser journey. Separately
   build a 22-Article synthetic fixture for native Next/Previous cases before
   any derived stores are built. Keep default fixture and all original E2E
   functions/assertions unchanged; no source or private records are used.
4. Verify actual desktop/mobile component wiring: filtered entry -> bare
   Shell reset; bare entry -> local filter -> bare reset; submit then type;
   draft plus Sort and Next/Previous; full-tuple Back/Forward; canonical
   equivalence; same-condition refresh; Clear/Retry and Shell focus/history.
5. Use readiness-qualified, request-specific delayed old success/failure and
   A -> B -> A cases. Verify current rows, selection and focus after release.
   Keep the existing strict network/error ledger; no blanket waivers.
   Supplement the native cases with an independently reviewed real React
   component scheduling contract: qualify acceptance-before-effect and batched
   A -> B -> A using actual act/Profiler and controlled API promises, without
   replacing React hooks/scheduler or rewriting the tested component. Observe
   positive controls and isolated mutant RED for immediate invalidation and
   revision advance. Generated bundles and labelled mutants stay in owned
   temporary copies; no production injection or additional permanent path.
6. A dedicated additive navigation profile must propagate failure, incomplete
   named coverage, late audit or cleanup failure into overall non-PASS while
   retaining completed original results. Its separate fixture, audits and
   result counts must not be presented as part of the original 298 checks.
7. Run all four Frontend test scripts, ordinary Backend tests, an owned
   production build, original repeat-three/restart and existing image profile,
   new navigation cases, existing security/SBOM/secret/artifact checks and two
   independent final reviews. Exact-SHA main CI precedes closure.

Commands include:

- uv run --offline --project backend --extra dev pytest -q
- npm --prefix frontend run test:articles
- npm --prefix frontend run test:references
- npm --prefix frontend run test:tutor
- npm --prefix frontend run test:graph
- SCIENTIFIC_SPACES_E2E_BACKEND_PORT=18000 uv run --offline --project backend python scripts/e2e/check_article_list_navigation.py
- SCIENTIFIC_SPACES_E2E_BACKEND_PORT=18000 uv run --offline --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start

Use the existing owned frontend-runtime helper for the production build and
backend 18000/frontend 3000 isolation. Never stop/reuse the user's backend on
8000 or mutate shared frontend/.next. Remove owned temporary resources.

## Safety, Delivery And Stop Conditions

No Article page wrapper, Shell, Graph, Backend product, frozen M1, API/schema,
canonical content/corpus, persistence, dependencies/locks/workflows, source
access, private Zotero, real/paid Provider, candidate, tag, Release or destructive
Git change. No runtime/private artifacts, HTML/body/image/PDF/trace exports or
secrets are committed. Existing public security services and reviewed GitHub
publication/CI readback remain allowed. Formal version stays v1.1.0.

Unknown worktree drift, forbidden artifacts/secrets, necessary protected-scope
change or a failed required gate stops the affected action for diagnosis, not
blind rerunning or weakening acceptance. There is no conditional closure.

After full local PASS and two final reviews, commit
`fix: synchronize article list navigation state`, non-force push main and verify
all seven required exact-SHA CI jobs. Include prior verified closure receipts
with this genuine implementation; no receipt-only self-hash commit loop.
The full platform/GUI objective remains active beyond this task.
