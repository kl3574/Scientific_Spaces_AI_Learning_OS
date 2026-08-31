# P3-019 Global Search and Quick Navigation Report

Status: **PASS / CLOSED**

## 1. Scope And Boundaries

P3-019 adds a bounded Frontend aggregation layer to the existing Application
Shell. It reuses the published Article, structured Reference, and Graph APIs;
no Backend route, schema, data asset, dependency, lockfile, workflow, or
Provider contract changed.

Backend code, frozen M1 paths, source and Article records, derived
RAG/Graph/Reference assets, private Zotero data, and release state remained
protected. No source-site request, external search, private Zotero operation,
real Provider call, candidate, tag, Release, or attestation action occurred.

## 2. Global Entry And Quick Navigation

- Desktop and mobile Application Shells expose one `Search` control.
- `Ctrl/Cmd+K` and `/` open the same search surface without visible shortcut
  instructions in the product UI.
- Empty input exposes all five stable workspaces: Dashboard, Articles,
  References, Graph, and Tutor.
- Reopening the keyboard shortcut while the dialog is already open does not
  overwrite its original focus-return target.

## 3. Search Aggregation And Destinations

Queries are normalized to 120 characters, require two characters for content
search, debounce for 250 ms, and request at most five items from each existing
source. `Promise.allSettled` preserves healthy groups when one source fails,
and a monotonic request sequence prevents an older response from replacing a
newer query.

Result behavior is frozen as follows:

- Article: `/v1.1/articles`, with a canonical relevance-search return path.
- Reference: `/v1.2/references`, linked to its source Article.
- Graph: `/v1.1/graph/nodes`, with a bounded exact `node_id` deep link.
- Workspace: existing stable navigation roots only.

Visible titles and descriptions are normalized and bounded to 180 characters.
Article Markdown is converted to plain preview text. DOI and arXiv identifiers
remain readable; other Reference types use stable semantic labels. Raw
Reference evidence, internal IDs, Markdown anchors, MathJax source, and the
`__article_root__` sentinel are not rendered as result labels.

## 4. Keyboard And Accessibility

- autofocus: PASS
- Arrow Up / Arrow Down wrap through results: PASS
- Enter activation from the search input: PASS
- Escape close: PASS
- Tab / Shift+Tab focus trap: PASS
- trigger focus restoration: PASS
- semantic modal dialog and grouped headings: PASS
- screen-reader loading/result/failure announcements: PASS
- body scroll lock and reduced-motion compatibility: PASS

## 5. Search States

- empty quick-navigation state: PASS
- one-character guidance: PASS
- loading state: PASS
- no-results state: PASS
- aggregate unavailable state: PASS
- one-source partial failure with healthy results retained: PASS
- stale response suppression: PASS

The Product E2E suite intentionally returns one Reference `503`; Article and
Graph results remain usable and the dialog reports one bounded source notice.

## 6. Real Local Data Evidence

A temporary local-only browser probe read these existing assets:

- Article Store: 1,314 Articles / 14,970,258 bytes
- Graph: 53,046 nodes / 82,584 edges
- structured References: 12,904 records

Learning, Tutor, and Zotero mutable files were redirected to a temporary
directory. Tutor and Zotero providers were fake, and every non-loopback browser
request was blocked. The temporary mutable directory was removed after the
probe.

Five queries passed at both 1,440 x 900 and 390 x 844:

| Query | Article | Reference | Graph |
| --- | ---: | ---: | ---: |
| `Attention` | 5 | 5 | 5 |
| `矩阵` | 5 | 5 | 5 |
| `Gumbel Softmax` | 5 | 0 | 1 |
| `KL散度` | 5 | 5 | 5 |
| `1905.05526` | 1 | 1 | 0 |

Across both viewports the probe observed 42 Article, 32 Reference, and 32
Graph results. Each query returned usable local content; a source group was
omitted when it had no match rather than represented as a failure.

- external requests: 0
- unexpected console errors: 0
- page errors: 0
- source failures: 0
- descriptions over 180 characters: 0

## 7. Responsive Visual Evidence

Final screenshots were inspected from the real local corpus after the
production build:

- desktop viewport/document: 1,440 / 1,440 px
- desktop dialog: 672 px wide
- mobile viewport/document: 390 / 390 px
- mobile dialog: 374 px wide
- clipped controls, overlap, or horizontal overflow: 0
- raw Markdown, MathJax, internal sentinel, or raw identifier labels: 0

Visual review found and corrected four presentation issues before this final
gate: Markdown Article previews, a duplicate browser-native clear affordance,
raw Reference formula/Markdown titles, and raw Reference section markers.
Screenshots and all temporary visual artifacts were deleted after inspection.

## 8. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 75.88s
```

### Frontend

- global search: 5 passed
- Article/Reader/workflow/navigation: 27 passed
- structured References: 3 passed
- Graph: 10 passed
- Tutor: 19 passed
- focused total: 64 passed
- Next.js 15.5.21 production build: PASS, 9 routes
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

- complete runs: 3
- successful runs: 3
- checks per run: 37
- global search quick navigation, partial failure, keyboard, deep links, and
  stale-response checks: PASS
- restart persistence: PASS
- mobile document widths: 390 px
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
- temporary screenshots, SBOMs, E2E JSON, mutable stores, and local servers:
  cleaned

## 11. Known Risks

- Each content query fans out to three existing local APIs. The interaction is
  bounded and debounced, but no new shared Backend index or cross-source
  ranking contract is introduced.
- Source totals represent each API's own matching semantics; an absent group
  means no match, not a global relevance judgment.
- Graph exact-node deep links depend on the installed Graph asset remaining
  compatible with the existing node-detail endpoint.
- Authentication, multi-user isolation, hosted deployment, and concurrent
  mutable-store guarantees remain deferred outside P3-019.

## 12. Exact-SHA Main CI

Implementation commit
`c92b08990490b1d55296eaafbd829462394a2f21` passed exact-SHA main CI run
[`33389364565`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33389364565).

- Workflow policy: PASS
- Backend pytest: PASS
- Secret audit: PASS
- SBOM validation: PASS
- Dependency audit: PASS
- Frontend build: PASS
- Product E2E, including three repeated runs: PASS
- Docker compose smoke: SKIPPED as designed for a normal `main` push
- Release evidence dry-run: SKIPPED as designed for a normal `main` push
- uploaded workflow artifacts: 0
- overall conclusion: SUCCESS

## 13. Closure

P3-019 is `PASS / CLOSED`. Local acceptance and the implementation exact-SHA
main CI gate passed without widening the authorized boundary. This docs-only
closure commit requires its own exact-SHA main CI readback before final
reporting. No subsequent task or v1.2 candidate is assigned.
