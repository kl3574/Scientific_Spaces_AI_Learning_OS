# P3-016 Learning Dashboard Command Center Report

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

## 1. Baseline

- entry branch: `main`
- entry commit and cached `origin/main`:
  `38e5d50990acb3886b84480417721806c1e6ec25`
- entry worktree: clean
- P3-015: PASS / CLOSED
- local Article Store used read-only: 1,314 Articles
- Backend and published API changes: none

The previous Dashboard already exposed the project title, summary counters,
Continue Reading, recent Articles, and separate recent-activity lists. Its main
limitations were equal-weight metrics, overlapping activity surfaces, raw
Article IDs in Sessions, and an all-or-nothing request failure path.

## 2. Implemented Design

The Dashboard is now a compact command center with five bounded surfaces:

1. Learning Overview derives completion, in-progress, saved, and note signals
   from existing Article and learning-stat fields.
2. Continue Learning selects the newest valid local Reader/history position
   and preserves its exact safe section fragment.
3. Next Actions links directly to the existing Articles, Tutor, Graph, and
   Zotero routes.
4. Learning Activity merges recent learning, Reader/research sessions, and
   browser history into one reverse-chronological list capped at eight events.
5. New in Library retains five date-sorted Article entries and the full
   library count.

Article title resolution prefers current Article evidence, falls back through
learning/history evidence, and never displays a raw Article ID as a title.
All presentation arithmetic and list selection are implemented in the pure
`frontend/src/lib/dashboard.ts` module.

## 3. Resilience and Boundaries

Article and learning-stat requests use independent settled results. One failed
request preserves all successful remote data and browser-local Reader state,
while a bounded warning and Retry action remain visible. Fully empty and fully
failed states remain controlled.

No Backend endpoint, persistence schema, Article record, frozen M1 module,
derived RAG/Graph/Reference asset, legacy API, `/v1.1` API, or `/v1.2` API was
changed. No dependency or lockfile was changed.

## 4. Real Local Article Browser Evidence

A temporary local-only Playwright probe used the existing 1,314-Article Store
read-only. Learning, Tutor, Graph, Reference, and Zotero runtime paths were
redirected to a temporary directory; Tutor and Zotero providers were fake.
All non-loopback requests were blocked.

- viewport checks: 1440 x 900 and 390 x 844
- library count: 1,314
- latest real Article titles rendered: 5
- exact resume sample: `521a5341f8f043db`, 42 percent, safe section fragment
- desktop document width: 1,440 px
- mobile document width: 390 px
- mobile Continue Learning action: y=807 px, height=36 px, bottom=843 px
- external requests: 0
- console errors: 0
- page errors: 0
- overlap, navigation wrap, or clipped primary action: none

Temporary screenshots and the probe script were deleted after visual review.
No Article body, HTML, image, trace, profile, or runtime store was retained.

## 5. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 74.37s
```

### Frontend

- Article, Reader, workflow, and Dashboard helpers: 23 passed
- Structured References: 3 passed
- Graph and deterministic visualization: 10 passed
- Tutor: 13 passed
- focused total: 49 passed
- Next.js 15.5.21 production build: PASS, 9 routes
- Dashboard route: 7.02 kB route code, 113 kB first load

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

- complete runs: 3
- successful runs: 3
- checks per run: 24
- command-center and exact resume checks: PASS
- independent partial-failure and Retry checks: PASS
- mobile Continue Learning action fully inside 390 x 844 viewport: PASS
- state leakage between runs: none
- Backend restart persistence: PASS
- external requests: 0
- console errors: 0
- page errors: 0

## 6. Security and Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- explicit workflow permissions: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- dependency audit: PASS, 40 PyPI / 239 npm / 0 findings
- secret audit: PASS, 0 credible findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM output cleanup: PASS

## 7. Artifact and Protected-Path Evidence

- Backend implementation changes: 0
- frozen M1 path changes: 0
- Article source-record changes: 0
- derived RAG, Graph, Reference, or PDF asset changes: 0
- dependency or lockfile changes: 0
- tracked runtime/private artifacts introduced: 0
- source-site requests: 0
- private Zotero reads/writes: 0 / 0
- real or paid Provider calls: 0
- candidate, tag, Release, or attestation actions: 0

## 8. Known Risks

1. Completion and aggregate counters reflect the existing learning-state API;
   browser-local Reader progress remains a separate resume signal.
2. A session whose Article title is absent from all available Dashboard
   evidence is labeled `Untitled article` instead of exposing an internal ID.
3. Article and learning-state availability still depends on the local Backend,
   but a single failed request no longer hides independent content.

## 9. Decision

P3-016 local implementation status: **PASS**.

The implementation is ready for its first exact-SHA `main` CI run. P3-016 is
not CLOSED until the implementation commit and a later docs-only closure
commit both pass exact-SHA CI and the final branch is clean and synchronized.
