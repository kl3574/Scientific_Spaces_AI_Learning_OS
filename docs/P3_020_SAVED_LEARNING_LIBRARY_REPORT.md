# P3-020 Saved Learning Library Report

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

## 1. Scope And Boundaries

P3-020 adds a Frontend-only Saved Learning Library at `/library`. It joins the
existing Learning State, Bookmark, Reading History, Reader Progress, and recent
learning-summary records without adding a Backend route, schema, entity, or
persistence model.

Backend code, frozen M1 paths, source and Article records, derived
RAG/Graph/Reference assets, dependencies, lockfiles, workflows, published APIs,
private Zotero data, Provider defaults, and release state remained protected.
No source request, private Zotero operation, external search, real Provider
call, candidate, tag, Release, or attestation action occurred.

## 2. Saved Learning Model

The pure `savedLibrary` view model:

- joins records only by bounded safe `article_id`;
- prefers readable Bookmark or Reading History titles and recent Article
  summaries over internal identifiers;
- applies canonical Learning State after recent summaries so stale summaries
  cannot overwrite current status;
- classifies active, bookmarked, and recent records deterministically;
- normalizes progress to integer values from 0 through 100;
- accepts only safe Article and section identifiers;
- reports title-unresolved records as an aggregate unavailable count without
  displaying their IDs;
- limits the public workspace to 100 unique readable Articles and reports any
  older omitted count.

No Article detail fan-out or hidden content fetch is used to fill missing
titles. This keeps the workspace bounded and prevents a local state record from
turning into an unbounded Article query.

## 3. Workspace Behavior

`/library` provides:

- one readable summary for all records, in-progress records, bookmarks, and
  recent activity;
- `All`, `Continue`, `Saved`, and `Recent` segmented views;
- bounded title, section, and status filtering;
- deterministic recent-activity, title, and progress sorting;
- `Continue Learning`, `Bookmarked`, and `Recently Read` sections;
- progress, status, saved state, last meaningful section, and activity date;
- direct access to the existing Article Reader;
- an explicit route to the full Article List.

The Dashboard primary action and Next Actions surface point to saved learning.
Desktop navigation, mobile navigation, and empty-query global quick navigation
all expose the `Saved` workspace. The shared Shell identifies the route as
`Saved Learning` without exposing an internal Article identifier.

## 4. Reader Return Contract

Library state is canonicalized into `q`, `view`, and `sort` parameters. Reader
links encode that exact local path in the existing `from` parameter and retain
the last safe section anchor. Article Detail accepts only canonical `/articles`
or `/library` return paths, rejects external or malformed paths, and labels a
Library-origin return as `Back to saved library`.

Tutor and Graph return-context parsing continues to round-trip the same safe
Article destination. Existing Article List return behavior remains unchanged.

## 5. Data And Failure States

The workspace requests Learning State, Bookmarks, and Learning Stats through
`Promise.allSettled` while Reading History and Reader Progress remain local.

- loading: explicit refresh state;
- empty: guidance to browse Articles;
- partial: healthy remote and local records remain usable with a retry action;
- unavailable with local records: local results remain visible with a bounded
  remote-unavailable notice;
- unavailable without local records: explicit unavailable state and retry;
- no filter matches: explicit no-results state and clear action.

Raw unavailable IDs, exception payloads, Article content, and private local
paths are not rendered.

## 6. Accessibility And Responsive Behavior

- semantic page, section, list, status, alert, and progress landmarks: PASS
- segmented-view `aria-pressed` state: PASS
- explicit filter and sort accessible names: PASS
- keyboard-reachable links, buttons, input, and select: PASS
- visible shared focus treatment: PASS
- reduced-motion browser preference: PASS
- screen-reader loading, partial, unavailable, and empty feedback: PASS
- desktop and mobile Shell navigation: PASS
- horizontal page overflow at 390 px: 0

## 7. Real Local Data Evidence

A temporary local-only browser probe read the installed Article Store:

- Article count: 1,314
- Article Store bytes: 14,970,258
- Article Store SHA-256:
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`

Two real Articles were represented through isolated temporary Learning State,
Bookmark, Reading History, and Reader Progress. Existing mutable learning data
was not read or changed. Tutor and Zotero providers were fake, and all
non-loopback browser requests were blocked.

- continue-learning records: PASS
- bookmarked records: PASS
- recently read records: PASS
- Chinese titles and section labels: PASS
- 57 and 100 percent progress presentation: PASS
- desktop viewport/document: 1,440 / 1,440 px
- mobile viewport/document: 390 / 390 px
- external requests: 0
- page errors: 0

Desktop and mobile screenshots were inspected for overlap, clipping, density,
long-title wrapping, control fit, and hierarchy. All screenshots and temporary
mutable files were deleted after inspection.

## 8. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 74.34s
```

### Frontend

- Saved Learning Library: 5 passed
- Article/Reader/workflow/navigation: 28 passed
- global search: 5 passed
- structured References: 3 passed
- Graph: 10 passed
- Tutor: 19 passed
- focused total: 70 passed
- Next.js 15.5.21 production build: PASS, 10 routes
- `/library`: PASS, 7.76 kB route / 114 kB first load
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

- formal complete runs: 3
- formal successful runs: 3
- checks per run: 42
- empty, complete, partial, and unavailable Library states: PASS
- filter, sort, Reader destination, and exact return state: PASS
- desktop/mobile/quick navigation: PASS
- restart persistence: PASS
- mobile Library document width: 390 px
- external requests: 0
- unexpected console errors: 0
- page errors: 0

An exploratory production run observed one React hydration mismatch before a
clean production rebuild. A development diagnostic run passed, followed by the
formal 3/3 run and a separate 10/10 production stress run. Across those 13
consecutive production runs, 546 checks passed with zero hydration/page error,
state leakage, external request, or unexpected console error.

## 9. Security And Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- explicit workflow permissions: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- security utility tests: 17 passed
- dependency audit: PASS, 40 PyPI / 239 npm / 0 findings
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS

## 10. Artifact And Protected Paths

- Backend implementation changes: 0
- frozen M1 changes: 0
- source or Article record changes: 0
- derived RAG/Graph/Reference changes: 0
- dependency, lockfile, or workflow changes: 0
- published API changes: 0
- tracked runtime/private artifacts: 0
- `.env`, credential, PDF, HTML dump, image, trace, profile, cache, mutable
  store, corpus, or generated SBOM additions: 0
- temporary screenshots, E2E JSON, SBOMs, mutable stores, and local servers:
  cleaned

The tracked `.env.example` template is the only broad artifact-pattern match;
it predates P3-020 and contains no credential.

## 11. Known Risks

- Learning State and Reader Progress entries without any readable Bookmark,
  History, or recent-summary title cannot be shown. They remain counted as
  unavailable rather than exposing an ID or causing Article-detail fan-out.
- Reading History is intentionally capped at eight entries and Reader Progress
  at fifty by their existing stores; the Library does not expand those
  persistence contracts.
- The page reflects single-browser local history plus the existing local
  Backend learning store. Cross-device synchronization, authentication,
  multi-user isolation, and concurrent-write guarantees remain out of scope.
- Browser storage denial degrades local progress/history only; remote learning
  records remain usable.
- A single exploratory hydration mismatch did not recur in 13 consecutive
  production runs. Exact-SHA CI remains the final implementation gate.

## 12. Exact-SHA Main CI

Implementation commit and exact-SHA main CI: **PENDING**.

Normal-main Docker compose smoke and release-evidence jobs are expected to
skip under the existing workflow policy. No workflow, tag, Release, candidate,
or attestation change is authorized by P3-020.

## 13. Closure

P3-020 is `LOCAL PASS / IMPLEMENTATION CI PENDING`. Local acceptance passed
without widening the authorized boundary. Closure requires the implementation
commit's exact-SHA main CI, a docs-only closure commit, and that closure
commit's exact-SHA main CI before final `PASS / CLOSED` status.
