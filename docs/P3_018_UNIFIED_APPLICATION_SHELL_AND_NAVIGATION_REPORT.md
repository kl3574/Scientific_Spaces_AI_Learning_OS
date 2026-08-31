# P3-018 Unified Application Shell and Navigation Report

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

## 1. Scope And Boundaries

P3-018 changes only the shared Frontend shell, route presentation, bounded
workspace states, focused Frontend tests, isolated Product E2E coverage, and
task governance. It reuses published Backend interfaces and existing route
contracts without changing them.

Backend code, frozen M1 paths, Article records, derived RAG/Graph/Reference
assets, dependencies, lockfiles, workflows, and API contracts are unchanged.
No source site, private Zotero library, real Provider, candidate, tag, Release,
or attestation action was used.

## 2. Architecture Decision

The stable global workspaces are:

- Dashboard: `/`
- Articles: `/articles`
- References: `/zotero`
- Graph: `/graph`
- Tutor: `/tutor`

P3-014 Workflow is an integrated cross-route behavior, not a standalone route.
P3-018 therefore preserves its Article, section, Tutor, and Graph context
instead of adding a decorative `/workflow` page.

One root `AppShell` now owns the global frame. A shared route model supplies
labels, icons, active matching, and contextual route trails to desktop and
mobile navigation. Article detail trails display `Articles / Article`; raw
Article identifiers are not exposed as navigation labels.

## 3. Application Shell

- Desktop uses a stable 15-rem sticky workspace rail and a full-width content
  region.
- Mobile uses a sticky header and modal workspace drawer rather than
  compressing five destinations into one row.
- The current workspace is exposed visually, through `aria-current`, and via a
  screen-reader live label.
- Primary navigation preserves explicit deep-link URLs and does not invent or
  rewrite workspace query state.
- The prior per-page `ReaderShell` wrappers were removed so every route shares
  one semantic `aside`, `nav`, and `main` hierarchy.

## 4. Responsive And Accessibility Behavior

- The mobile drawer traps focus, autofocuses its close control, closes on
  Escape or route selection, restores focus to its trigger, and locks body
  scrolling while open.
- Existing visible-focus and reduced-motion behavior is preserved.
- Desktop and 390 x 844 mobile checks found no page-width overflow, clipped
  global navigation, or shell/content overlap.
- Mobile retains a compact current-workspace label while the wider contextual
  trail remains desktop-only, preserving first-viewport workspace actions.

## 5. Shared Workspace States

A project-owned `WorkspaceState` band standardizes bounded loading, empty,
error, and unavailable presentation. Article list, Article detail, Zotero
References, route loading, global errors, and unknown routes use the shared
surface where applicable. Auxiliary failures remain local to their workspace
and do not erase otherwise usable content.

## 6. Real Local Article Evidence

A temporary local-only browser probe read the existing canonical Article Store
at `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json`.
The store contained 1,314 Articles and 14,970,258 bytes. Installed local
Graph, RAG, and Reference data were read; mutable Learning, Tutor, and Zotero
stores were redirected to a temporary directory; fake providers were used;
and every non-loopback browser request was blocked.

Five deterministic mathematical Article samples passed at both 1,440 x 900
and 390 x 844:

| Article | Content characters | Shell/workflow |
| --- | ---: | --- |
| 漫谈重参数：从正态分布到Gumbel Softmax | 13,208 | PASS |
| n维空间下两个随机向量的夹角分布 | 5,464 | PASS |
| logsumexp运算的几个不等式 | 7,571 | PASS |
| 必须要GPT3吗？不，BERT的MLM模型也能小样本学习 | 13,067 | PASS |
| Transformer升级之路：7、长度外推性与局部注意力 | 9,310 | PASS |

Reader to Graph to Reader and Reader to Tutor to Reader preserved the exact
Article context. References navigation also passed. Mobile Article list,
Article detail, Tutor, and Graph document widths were exactly 390 px. External
requests, unexpected console errors, and page errors were all zero.

Temporary runtime files and screenshots used for visual inspection were
deleted. No Article body, screenshot, trace, profile, or runtime data was
retained.

## 7. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 74.39s
```

### Frontend

- Article, Reader, workflow, Dashboard, shell, and navigation helpers: 27 passed
- Structured References: 3 passed
- Tutor presentation and workspace: 19 passed
- Graph and visualization: 10 passed
- focused total: 59 passed
- Next.js 15.5.21 production build: PASS, 9 routes
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

- complete runs: 3
- successful runs: 3
- checks per run: 32
- five desktop workspace destinations and active state: PASS
- Article detail contextual trail without raw ID: PASS
- global unknown-route state: PASS
- mobile drawer open, focus trap, Escape, focus return, and route close: PASS
- mobile navigation to Graph: PASS
- existing Reader/Graph/Tutor return context: PASS
- restart persistence: PASS
- external requests: 0
- unexpected console errors: 0
- page errors: 0

## 8. Security And Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- explicit workflow permissions: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- security utility tests: 17 passed
- dependency audit: PASS, 40 PyPI / 239 npm / 0 findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS
- staged secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings

## 9. Artifact And Protected Paths

- Backend implementation changes: 0
- frozen M1 changes: 0
- Article Store or Article record changes: 0
- derived RAG/Graph/Reference changes: 0
- dependency, lockfile, or workflow changes: 0
- tracked/untracked PDF, HTML dump, image, trace, profile, cache, database,
  secret, private Zotero, or runtime artifacts: 0

## 10. Known Risks

- The mobile drawer requires client-side JavaScript; server-rendered page
  content remains available, but drawer interaction does not.
- Existing local JSON learning-store concurrent-write behavior remains a v2
  deferred architecture concern. Three isolated E2E runs passed for this
  task.
- P3-018 adds no authentication, multi-user isolation, or hosted deployment
  behavior.
- `References` is the learner-facing label for the existing `/zotero`
  workspace; the underlying route and contracts remain unchanged.
- Workflow remains intentionally cross-route and has no standalone global
  navigation destination.

## 11. Exact-SHA Main CI

Implementation commit and exact-SHA main CI evidence are pending. Normal
`main` push policy must run Backend, Frontend, Product E2E, workflow,
dependency, secret, and SBOM jobs; Docker and release evidence should remain
skipped.

## 12. Closure

P3-018 is locally PASS. It becomes PASS / CLOSED only after both the
implementation commit and the subsequent docs-only closure commit pass
exact-SHA main CI, with final `main` clean and synchronized.
