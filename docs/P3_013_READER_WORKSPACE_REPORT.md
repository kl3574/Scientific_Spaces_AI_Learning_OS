# P3-013 Reader Workspace and Learning Continuity Report

## 1. Current Status

- task: P3-013 Reader Workspace and Learning Continuity
- local implementation: **PASS**
- implementation exact-SHA main CI: **PENDING**
- task closure: **PENDING**
- entry commit: `6b297d8ae21b1b43ef2e6e7a1b0bef51e5d71b83`
- candidate version: not assigned

P3-013 adds a presentation-only, local-first reading workspace over the
existing Article and learning contracts. It does not change Article records,
Backend routes, frozen M1 modules, or published API contracts.

## 2. Baseline Evidence

Five real Articles from the exact local 1,314-Article Store were inspected at
desktop and mobile viewports before implementation.

| Article | Markdown headings | Baseline heading IDs | Baseline outline | Baseline resume |
| --- | ---: | --- | ---: | --- |
| `acaac952bd9e2de1` | 7 | all absent | 0 | reopened at top |
| `5e4f3611bec2fce1` | 24 | all absent | 0 | reopened at top |
| `69e708f3cca249cf` | 13 | all absent | 0 | reopened at top |
| `9e4e72bf9edb585e` | 18 | all absent | 0 | reopened at top |
| `f6fe9a28445ce49b` | 12 | all absent | 0 | reopened at top |

The baseline Dashboard had no Continue Reading action. Article Detail exposed
no current-section or progress state, and its only local storage key was the
existing reading-history key.

## 3. Implementation

### Outline and Anchors

- derives an ordered h2-h4 outline from prepared Markdown
- ignores fenced-code pseudo-headings
- creates deterministic Unicode-safe IDs
- resolves duplicate and suffix-collision cases globally
- maps anchors by Markdown source line, avoiding render-order state
- strips legacy source permalink markers from heading presentation only
- moves keyboard focus to the selected heading

### Reading Position

- reports a clamped integer progress value from 0 through 100
- tracks the last section crossing the reading line
- persists at a bounded 300 ms interval and on page hide/unmount
- persists explicit outline choices immediately
- restores an explicit URL fragment before saved local state
- stores at most 50 per-Article records in browser local storage

The local record contains only Article ID, section ID/title, bounded progress,
and timestamp. It does not mutate Article or Backend data.

### Display Preferences

- compact, comfortable, and large text sizes
- focused and wide reading measures
- local persistence with fail-closed parsing and defaults
- reversible segmented controls with accessible names and pressed state
- reduced-motion CSS disables nonessential transitions and animation

### Dashboard Continuity

- one unambiguous Continue Reading action for the latest history item
- section title and bounded progress disclosure
- section-fragment deep link when a safe saved section exists
- controlled `No article in progress.` state when history is empty

### Content Presentation

The existing Markdown, GFM, KaTeX, code, table, citation, external-image
placeholder, and local deep-link behavior is preserved. A narrow
presentation-only normalization fixes CommonMark strong markers followed
immediately by Chinese text without modifying stored Article content.

## 4. Real-Corpus Browser Evidence

Chromium `149.0.7827.55` inspected the five baseline Articles against the real
read-only local Article Store. Mutable learning/Tutor/Zotero files were
redirected to temporary storage, fake providers were used, and all external
requests were blocked.

| Article | Outline / headings | KaTeX | Code | Tables | Image placeholders | Desktop width | Mobile width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `acaac952bd9e2de1` | 7 / 7 | 7 | 4 | 1 | 6 | 1440 | 390 |
| `5e4f3611bec2fce1` | 24 / 24 | 237 | 4 | 0 | 2 | 1440 | 390 |
| `69e708f3cca249cf` | 13 / 13 | 66 | 2 | 0 | 4 | 1440 | 390 |
| `9e4e72bf9edb585e` | 18 / 18 | 138 | 4 | 0 | 4 | 1440 | 390 |
| `f6fe9a28445ce49b` | 12 / 12 | 150 | 1 | 0 | 2 | 1440 | 390 |

Results:

- outline count matched rendered h2-h4 count for 5/5 Articles
- non-empty globally unique anchors: 74/74
- page-level overflow: 0 at 1440 px and 390 px
- mobile Outline entry: `272.5px`, inside the first 844 px viewport for 5/5
- external requests: 0
- unexpected console errors: 0
- uncaught page errors: 0
- first-Article strong lead rendered as `前言：`, not literal Markdown markers

The real navigation closure saved section `模型结果检验` at 20 percent,
generated a Dashboard fragment link, and reopened at scroll position 3220
with the same section active. The recomputed post-restore progress was 29
percent after current viewport/layout measurement.

## 5. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 74.32s
```

### Frontend

- Article, presentation, and Reader workspace: 11 passed
- Structured References: 3 passed
- Graph: 8 passed
- Tutor: 13 passed
- focused total: 35 passed
- production build: PASS, 9 routes generated

### Product E2E

```text
uv run --project backend --extra dev python \
  scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start
```

- complete runs: 3
- successful runs: 3
- checks per run: 19
- outline focus/anchors/progress/preferences: PASS
- Dashboard Continue Reading and section restore: PASS
- mobile reduced-motion and width checks: PASS
- external requests: 0
- unexpected console errors: 0
- page errors: 0
- Backend restart persistence: PASS

## 6. Security and Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- explicit workflow permissions: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- dependency audit: PASS, 40 PyPI / 219 npm / 0 findings
- tracked/history secret audit: PASS, 0 credible findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 219 Frontend / 261 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS

## 7. Protected Boundary Evidence

- Backend implementation changes: 0
- frozen M1 module changes: 0
- Article source-record changes: 0
- legacy, `/v1.1`, or `/v1.2` API changes: 0
- dependency or lockfile changes: 0
- source-site requests: 0
- private Zotero reads/writes: 0 / 0
- real or paid Provider calls: 0
- candidate, tag, Release, or attestation actions: 0
- tracked runtime/private artifacts introduced: 0

Temporary browser screenshots, E2E JSON, mutable runtime stores, and SBOMs
were created outside the repository and removed after evidence extraction.

## 8. Defect Convergence

1. The first E2E probe read progress during the first smooth-scroll frame.
   The assertion was corrected to await committed progress state.
2. A three-run probe then showed that leaving during smooth outline navigation
   could preserve progress without a section. The product behavior was changed
   to deterministic immediate positioning plus immediate explicit-section
   persistence. This was treated as a product defect, not a test relaxation.
3. Three consecutive final runs passed after the fix.

## 9. Known Risks

1. Resume state and display preferences are browser-local and do not synchronize
   across devices or browser profiles.
2. Outline extraction intentionally covers the h2-h4 ATX structure present in
   the validated corpus samples; changing frozen source heading formats is an
   M1.x concern, not a P3-013 change.
3. Browser verification depends on a compatible Chromium runtime.
4. The application remains a local, single-user system.

## 10. Closure State

Local implementation and all authorized local gates are **PASS**. P3-013
remains open until the implementation commit is pushed, its exact-SHA main CI
passes, and a separate docs-only closure commit also passes exact-SHA main CI.
