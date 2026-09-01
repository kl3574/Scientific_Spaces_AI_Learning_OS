# P3-021 Focused Study Session Report

Status: **PASS / CLOSED**

## 1. Scope And Boundaries

P3-021 adds a Frontend-only Focused Study Session at `/session`. It converts
readable Saved Learning records into one bounded browser-local queue while
reusing existing Article, Library, Reader Progress, workflow, Shell, and
global-search contracts.

Backend code, frozen M1 paths, source and Article records, derived
RAG/Graph/Reference assets, dependencies, lockfiles, workflows, published
APIs, private Zotero data, Provider defaults, and release state remained
protected. No source request, private Zotero operation, external search, real
Provider call, candidate, tag, Release, or attestation action occurred.

## 2. Session Model

The pure `studySession` model provides:

- one versioned browser-local record under
  `scientific-spaces-study-session-v1`;
- a hard ceiling of 20 unique Articles;
- bounded safe Article and section identifiers;
- readable titles that cannot equal the internal Article identifier;
- deterministic add, deduplicate, reorder, activate, remove, and clear
  operations;
- a stable active Article plus previous/current/next position lookup;
- canonical Reader destinations that retain `/session` as the return path;
- fail-closed JSON parsing with invalid, duplicate, and over-limit counts;
- normalized timestamps and deterministic fallback to the first healthy item.

The queue stores only Article identity, readable title, optional section,
added time, active identity, update time, and format version. It does not copy
Article content, add a server entity, or change a persistence schema.

## 3. Workspace Behavior

Saved Learning exposes an `Open study session (N)` route and an Add action on
each readable record. Adding an Article does not navigate away or change the
current Library query, view, or sort. Duplicate and full-queue actions are
bounded, and unavailable browser storage disables writes explicitly.

`/session` provides:

- queue count and current position;
- one direct Continue action for the active Article;
- readable ordered rows with Current or Queued state;
- move up/down, set-current, and remove controls;
- a two-step clear action;
- refresh restoration of order and active position;
- loading, empty, unavailable, recovered, and write-failure feedback.

A failed browser-local write retains the user's latest in-memory queue for the
current page and displays a warning. It does not pretend persistence
succeeded.

## 4. Reader And Navigation Contract

Article Detail accepts only the exact `/session` root in addition to its
existing canonical Article List and Saved Library return paths. Session Reader
links preserve optional safe section anchors.

When opened from Session, Reader:

- marks the current Article active in the local queue;
- displays `Article X of N`;
- exposes the correct previous and next readable Article links;
- labels the return action `Back to study session`;
- keeps Tutor and Graph return context on the same safe Article destination.

Session is present in desktop navigation, the accessible mobile drawer, and
empty-query global quick navigation. Existing routes retain their prior
selection and contextual trails.

## 5. Failure And Recovery Evidence

- empty queue: actionable Saved Learning route, PASS
- unavailable `localStorage` read: explicit unavailable state, PASS
- unavailable `localStorage` write: in-memory operation plus warning, PASS
- malformed JSON: fail-closed empty recovery, PASS
- duplicate record: omitted and counted, PASS
- unsafe or ID-only title: omitted without visible raw identifier, PASS
- missing active record: first healthy item selected, PASS
- over-limit record: first 20 healthy unique records retained, PASS
- healthy records alongside bad records: remain usable, PASS

No recovery state renders discarded identifiers, exception payloads, Article
content, or private local paths.

## 6. Accessibility And Responsive Behavior

- semantic page, section, list, navigation, status, and progress landmarks:
  PASS
- exact accessible names for reorder, activate, remove, add, previous, and
  next controls: PASS
- disabled boundary and current-item controls: PASS
- two-step destructive clear action: PASS
- keyboard-reachable shared Shell and queue controls: PASS
- visible shared focus treatment: PASS
- reduced-motion mobile context: PASS
- screen-reader loading, empty, recovered, unavailable, and write-failure
  feedback: PASS
- desktop and mobile navigation: PASS
- horizontal page overflow at 390 px: 0

Desktop and mobile screenshots were inspected for overlap, clipping, title
wrapping, queue density, control fit, and hierarchy. The temporary screenshots
and runtime data were deleted after inspection.

## 7. Real Local Data Evidence

A temporary local-only browser probe read the installed Article Store:

- Article count: 1,314
- Article Store bytes: 14,970,258
- Article Store SHA-256:
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`

Two real Chinese mathematics Articles were represented through isolated
temporary Learning State, Bookmark, Reading History, and Session records.
Existing mutable learning data was not read or changed. Tutor and Zotero
providers remained fake, and every non-loopback browser request was blocked.

- real Saved Learning add action: PASS
- two-Article Session order and current position: PASS
- readable Chinese titles: PASS
- desktop viewport/document: 1,440 / 1,440 px
- mobile viewport/document: 390 / 390 px
- external requests: 0
- console errors: 0
- page errors: 0

## 8. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 37.84s
```

### Frontend

- Article/Reader/workflow/navigation: 29 passed
- Saved Learning Library: 5 passed
- Focused Study Session: 6 passed
- global search: 5 passed
- structured References: 3 passed
- Graph: 10 passed
- Tutor: 19 passed
- focused total: 77 passed
- Next.js 15.5.21 production build: PASS, 11 routes
- `/session`: PASS, 2.41 kB route / 111 kB first load
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

- formal complete runs: 3
- formal successful runs: 3
- checks per run: 48
- Library add, URL-state retention, queue reorder, active restoration, Reader
  previous/next/return, remove, and clear: PASS
- stale-record, storage-read, and storage-write states: PASS
- desktop/mobile/quick navigation: PASS
- restart persistence: PASS
- Chromium: 149.0.7827.55
- mobile Session document width: 390 px
- external requests: 0
- unexpected console errors: 0
- page errors: 0

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

The tracked `backend/app/crawler/cache.py` source module is the only broad
artifact-name match. It predates P3-021, is unchanged, and is not runtime
cache data.

## 11. Known Risks

- Queue persistence is intentionally browser-local and single-profile.
  Cross-device synchronization, authentication, multi-user isolation, and
  concurrent-write guarantees remain out of scope.
- A queue record can outlive its Article Store entry. Its readable title stays
  visible, while the existing Reader unavailable state handles a missing
  Article without mutating the queue automatically.
- Browser storage denial prevents refresh persistence. The UI keeps the latest
  in-memory operation visible and reports the failed save.
- The queue is capped at 20 Articles and has no server-side learning-plan or
  completion semantics by design.
- GitHub Actions currently emits an upstream Node 20 deprecation annotation
  for pinned Actions running under Node 24 compatibility. It did not affect
  any required job and workflow changes were outside P3-021 scope.

## 12. Exact-SHA Main CI

Implementation commit:
`df4500c17b2456aedde36a039a60a92f631e6ea9`.

Exact-SHA main CI:
[`33489296319`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33489296319),
`success` for the exact implementation SHA.

- Backend pytest: PASS
- Frontend build: PASS
- Product E2E, including three repeated runs: PASS
- workflow policy: PASS
- dependency audit: PASS
- secret audit: PASS
- SBOM validation: PASS
- Docker compose smoke: skipped as designed for a normal `main` push
- release-evidence dry-run: skipped as designed
- uploaded workflow artifacts: 0

Normal-main Docker compose smoke and release-evidence jobs are expected to
skip under the existing workflow policy. No workflow, tag, Release, candidate,
or attestation change is authorized by P3-021.

## 13. Closure

P3-021 is `PASS / CLOSED`. Local acceptance and the implementation commit's
exact-SHA main CI passed without widening the authorized boundary. This
docs-only closure commit must pass its own exact-SHA main CI before final
reporting; no new task is assigned or authorized.
