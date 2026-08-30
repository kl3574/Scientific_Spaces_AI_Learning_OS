# P3-012 Learning Experience and GUI Refinement Report

## 1. Status

- Task: P3-012 Learning Experience and GUI Refinement
- Entry commit: `5933c17481a98db4b296eabac3a9d8947cd06704`
- Local implementation: **PASS**
- Exact-SHA main CI: **PENDING**
- Task status: **LOCAL PASS / CI PENDING**
- Candidate version: not assigned

This task refines the existing local learning product. It does not change any
Backend route, published API contract, frozen M1 module, Article source record,
derived corpus asset, or private Zotero data.

## 2. Evidence Method

The audit followed an evidence-first loop:

1. inventory the product routes, components, runtime, and protected boundaries;
2. reproduce behavior in real Chromium against the exact local 1,314-Article
   runtime;
3. rank observations by workflow and data-safety impact;
4. identify the narrowest presentation-layer root cause;
5. implement a bounded correction and focused regression check; and
6. repeat the same desktop/mobile journey until no high-severity defect remains.

The local `deep-research`, `kimi-webbridge`, and `diagnosing-bugs` instructions
were applied. The Kimi desktop connector probe returned `no extension
connected`; it was not used to access an external site. Direct Chromium and the
interactive Playwright Computer Use session supplied the real local-browser
evidence instead.

## 3. Browser Environment

- application: real local FastAPI plus built Next.js
- Article corpus: 1,314 Articles
- Graph: 53,046 nodes / 82,584 edges
- structured References: 12,904 records
- browser: Chromium `149.0.7827.55`
- desktop viewport: `1440 x 900`
- mobile viewport: `390 x 844`
- mutable learning/Tutor/Zotero-link state: isolated temporary files
- source-site navigation: 0
- private Zotero reads/writes: 0 / 0
- real or paid Provider calls: 0

Screenshots and machine-readable browser observations were kept only under
`/tmp` during validation and are not repository deliverables.

## 4. Evidence and Convergence Matrix

| Page / action | Before evidence | Severity | Root cause | Correction | Final verification |
| --- | --- | --- | --- | --- | --- |
| Shared shell navigation | No route exposed `aria-current`; mobile links occupied two rows | High | static server component rendered identical links on every route | route-aware `PrimaryNav`, one-row responsive grid, sticky shell, semantic `main` | all six routes expose exactly one correct current item; mobile nav rows `2 -> 1` |
| Keyboard entry | no skip link and inconsistent browser-default focus | High | shell lacked a bypass link and shared focus token | visible-on-focus skip link and explicit amber `3px` focus outline | first `Tab` focuses `Skip to content` at both viewports; outline and offset verified |
| Dashboard first viewport | six metrics were one card per row; `Recent Articles` began at `1047px` | High | no mobile grid constraint and card-heavy hierarchy | compact semantic metrics band, primary actions, divider-based recent lists | two metric columns; `Recent Articles` begins at `612px` on 390 x 844 |
| Article search and scan | 6 of 20 sampled previews exposed headings, links, or other Markdown syntax | Medium | API preview was rendered directly as display text | deterministic presentation-only Markdown-to-text helper and dense result list | 0 of 20 sampled `Attention` results expose tested Markdown markers; search, sort, clear, empty state pass |
| Long Article learning workflow | `Learning State` began at `21320px` in a `23021px` mobile document | High | the tools aside followed the complete Article in the document | first-viewport `Reading tools` anchor, focusable target, sticky desktop tools, return link | entry is at `272px`; activation focuses the tools at the viewport top; return link works |
| Article image behavior | two Scientific Spaces image requests were attempted automatically | High | relative/external Markdown images were normalized to live source URLs | local-only placeholder with explicit user-controlled source link; only `data:`/`blob:` images render inline | two placeholders rendered and external browser request count is 0 |
| Structured Reference evidence | pass 2 mobile detail expanded to `1052px` | High | a long unbroken evidence URL lacked an anywhere wrap constraint | bounded evidence wrapping in the presentation component | final mobile Article document width is exactly `390px` |
| Graph summary | four summary cells stacked on mobile | Medium | summary grid started at one column | stable two-column mobile summary band | two columns on mobile and four on desktop; no clipped values |
| Tutor modes | `Research` wrapped to a second row on mobile | Medium | flexible wrapping did not reserve five stable tracks | five-track segmented control with stable text sizing | all five modes remain on one row at both viewports |
| Browser console identity | browser requested a missing favicon | Low | no application icon metadata asset | local application icon | icon returns locally; no unexpected console error in the product E2E suite |

## 5. Three-Pass Convergence

### Pass 1 - Discovery

Result: **BLOCKED**.

- active primary navigation items: 0
- mobile navigation rows: 2
- mobile Dashboard statistic columns: 1
- `Recent Articles` top: 1047 px
- raw Markdown previews: 6 / 20 sampled results
- mobile `Learning State` top: 21320 px
- external Article image requests: 2

### Pass 2 - Main Fix Verification

Result: **BLOCKED**.

The shell, Dashboard, Article tools entry, external-image policy, Graph, and
Tutor corrections worked. The pass exposed a new mobile Article width of 1052
px and remaining inline heading markers in whitespace-compacted previews. The
overflow was traced to a long structured-reference evidence string rather than
KaTeX or the shell.

### Pass 3 - Final Convergence

Result: **PASS**.

- six primary pages checked at both viewports
- page-level horizontal overflow: 0
- unlabeled visible focusable controls: 0
- clipped primary controls: 0
- incorrect or missing active navigation items: 0
- external browser resource requests: 0
- uncaught page errors: 0
- raw tested Markdown preview markers: 0 / 20
- controlled empty, Article 404, and Backend 503 states: PASS
- real formula rendering and local Tutor query: PASS
- unresolved high-severity product defects: 0

The only console errors in the broad pass were the deliberately exercised
Article `404` and Backend `503`. The isolated product E2E classifies those
expected failures and reports zero unexpected console errors.

## 6. Interactive Computer Use Journey

The interactive browser session performed this real local journey:

```text
Dashboard
  -> Articles
  -> search Attention (128 results)
  -> open Archive 11823
  -> open Reading tools
  -> set status to reading
  -> save bookmark
  -> add an isolated learning note
  -> verify note readback
  -> resize to 390 x 844
  -> verify keyboard Skip Link and focus ring
```

The app remained local-only. The Zotero page used the configured fake,
read-only provider; the Tutor used the fake provider.

## 7. Implementation Summary

- shared route-aware navigation and accessible shell
- compact Dashboard statistics and scan-oriented activity sections
- Article sort/clear controls and presentation-only plain-text previews
- accessible long-Article reading-tools jump and sticky desktop tools
- explicit local-only external-image placeholders
- mobile-safe structured-reference wrapping
- stable Graph summary and Tutor mode tracks
- local application icon and shared focus/selection styling
- focused preview tests and expanded product E2E assertions
- exact security patch upgrades for `postcss` and transitive `nanoid`

## 8. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 78.22s
```

### Frontend

- Article and presentation: 6 passed
- Structured References: 3 passed
- Tutor: 13 passed
- Graph: 8 passed
- focused total: 30 passed
- production build: PASS, 9 routes generated including the local icon

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

- complete runs: 3
- successful runs: 3
- checks per run: 17
- external requests: 0
- unexpected console errors: 0
- page errors: 0
- mobile list/detail widths: 390 / 390 in every run
- Backend restart persistence: PASS

### Security and Supply Chain

- workflow policy: PASS, 19 immutable Action uses
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- dependency audit: PASS, 40 PyPI / 219 npm / 0 findings
- secret audit: PASS, 0 credible findings
- temporary SBOM: PASS, 261 combined components / 0 forbidden values
- temporary SBOM cleanup: PASS

The first dependency audit detected a newly published `postcss`/`nanoid`
advisory chain. Exact patch upgrades from `postcss 8.5.18` to `8.5.23` and
`nanoid 3.3.16` to `3.3.18` removed all findings without a Next.js major
upgrade. All Frontend build and E2E gates were rerun after the lockfile change.

## 9. Protected Boundary Evidence

- Backend implementation changes: 0
- frozen M1 module changes: 0
- Article source-record mutations: 0
- legacy, `/v1.1`, and `/v1.2` API contract changes: 0
- source-site requests: 0
- private Zotero reads/writes: 0 / 0
- real or paid Provider calls: 0
- candidate, tag, Release, or attestation actions: 0
- tracked runtime/private artifacts introduced: 0

The legacy P3-003 artifact heuristic still reports two pre-existing
documentation strings as `secret_pattern`; the authoritative tracked/history
secret scanner classifies zero credible findings, and the artifact scan reports
zero tracked runtime/private artifacts.

## 10. Known Risks and Deferred Candidate

1. Some frozen Article records contain MathJax accessibility text duplicated
   beside the preserved LaTeX source. KaTeX renders the formal expression, but
   the duplicated source text can remain visually noisy. Removing it with a
   heuristic risks deleting scientific content. This is recorded as an M1.x
   content-fidelity candidate and was not changed in P3-012.
2. Browser automation depends on a compatible Chromium runtime.
3. The product remains a local, single-user application.
4. External images are intentionally not loaded automatically; users must
   explicitly open an image at its source.

## 11. Decision

Local implementation, real-browser convergence, responsive behavior,
accessibility, negative states, full Backend, Frontend, E2E, dependency,
secret, workflow, SBOM, and protected-boundary gates: **PASS**.

Current task state: **LOCAL PASS / CI PENDING**.

P3-012 may be marked **PASS / CLOSED** only after the implementation commit and
the subsequent docs-only closure commit both pass exact-SHA main CI.
