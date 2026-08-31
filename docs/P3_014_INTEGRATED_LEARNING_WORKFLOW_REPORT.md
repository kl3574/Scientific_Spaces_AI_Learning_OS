# P3-014 Integrated Learning Workflow Report

## 1. Current Status

- task: P3-014 Integrated Learning Workflow
- local implementation: **PASS**
- exact-SHA main CI: **PENDING**
- task closure: **PENDING**
- entry commit: `5be49f05d1bf8055a8e844237fc7a058ca7c90d7`
- candidate version: not assigned

P3-014 connects the existing Dashboard, Article List, Reader, Tutor, Graph,
and learning-state surfaces without changing Backend code, Article records,
derived assets, or published API contracts.

## 2. Baseline Evidence

The pre-implementation audit used the read-only local 1,314-Article Store and
three representative Articles.

- Article pages exposed zero `Ask tutor` actions and zero `Explore graph`
  actions.
- Article back navigation always returned to `/articles`, losing search state.
- Opening Tutor with Article query parameters left Article ID empty and
  provided no Article return action.
- Opening Graph with Article query parameters did not select the Article node
  and provided no Article return action.
- Article List search did not persist its query in the URL.
- The same missing learning actions were observed at the 390 px viewport.
- External browser requests: 0.

These findings selected three bounded corrections: canonical list URL state,
safe Article-context links, and same-Article/same-section return continuity.

## 3. Implementation

### Canonical list state

- Article List reads bounded `q`, `sort`, and `page` values from the URL.
- Applied search, sort, and pagination state is written to a canonical local
  URL with `replaceState`.
- Article links carry only the canonical Article List return path.
- Back navigation restores the exact search state after a learning-tool round
  trip.

### Article learning actions

- Article Detail exposes one `Ask tutor` and one `Explore graph` action in the
  existing Reading tools column.
- Both actions carry the exact Article ID, a bounded display title, a safe
  local return path, and the current section fragment.
- Cross-origin, cross-Article, malformed ID, unsafe node, and oversized input
  values fail closed to bounded local defaults.

### Tutor and Graph continuity

- Tutor displays the current Article context, pre-fills Article ID, and
  provides a return action to the exact Article section.
- Graph displays the same context, selects only the matching
  `article:<article_id>` node, and preserves the return action while the user
  explores other nodes.
- Context parsing is presentation-only and does not alter Tutor or Graph API
  contracts.

### Repository governance

`AGENTS.md` is now a concise platform-neutral repository contract. Generated
Kimi hook ecosystem text, tool-specific interaction requirements, and session
maintenance instructions were removed while task authority, safety, Git,
artifact, and exact-CI rules were retained.

## 4. Real-Corpus Browser Evidence

Chromium `149.0.7827.55` exercised five real Articles from the exact local
1,314-Article Store. Mutable learning, Tutor, and Zotero files were redirected
to temporary storage, fake providers remained selected, and every external
request was blocked.

| Article | Tutor context | Graph Article node | Same return path | KaTeX | Code | Image placeholders | Desktop overflow | Mobile overflow |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `acaac952bd9e2de1` | PASS | PASS | PASS | 7 | 4 | 6 | no | no |
| `5e4f3611bec2fce1` | PASS | PASS | PASS | 237 | 4 | 2 | no | no |
| `69e708f3cca249cf` | PASS | PASS | PASS | 66 | 2 | 4 | no | no |
| `9e4e72bf9edb585e` | PASS | PASS | PASS | 138 | 4 | 4 | no | no |
| `f6fe9a28445ce49b` | PASS | PASS | PASS | 150 | 1 | 2 | no | no |

For all 5/5 Articles:

- the selected outline section survived Article -> Tutor -> Article and
  Article -> Graph -> Article navigation;
- Article List query state survived the complete round trip;
- Tutor Article ID was pre-filled with the exact source Article;
- Graph loaded the exact Article node and still allowed another node to be
  selected;
- document widths were exactly 1440 px and 390 px at their corresponding
  viewports;
- both learning actions remained fully inside the 390 px viewport;
- external requests, console errors, and page errors were all zero.

No screenshot, trace, profile, HTML, Article body, or runtime store was retained.

## 5. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 75.69s
```

### Frontend

- Article, presentation, Reader workspace, and workflow helpers: 17 passed
- Structured References: 3 passed
- Graph: 8 passed
- Tutor: 13 passed
- focused total: 41 passed
- Next.js 15.5.21 production build: PASS, 9 routes

### Product E2E

```text
uv run --project backend --extra dev python \
  scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start
```

- complete runs: 3
- successful runs: 3
- checks per run: 20
- integrated Article -> Tutor/Graph -> Article flow: PASS
- Graph context followed by free node exploration: PASS
- Article search URL and back-to-results restoration: PASS
- mobile learning actions and 390 px widths: PASS
- external requests: 0
- console errors: 0
- page errors: 0
- Backend restart persistence: PASS

## 6. Security and Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- explicit workflow permissions: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- dependency audit: PASS, 40 PyPI / 219 npm / 0 findings
- tracked, untracked, and bounded-history secret audit: PASS, 0 credible findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 219 Frontend / 261 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS

## 7. Protected Boundary Evidence

- Backend implementation changes: 0
- frozen M1 module changes: 0
- Article source-record changes: 0
- derived RAG, Graph, and Reference asset changes: 0
- legacy, `/v1.1`, or `/v1.2` API changes: 0
- dependency or lockfile changes: 0
- source-site requests: 0
- private Zotero reads/writes: 0 / 0
- real or paid Provider calls: 0
- candidate, tag, Release, or attestation actions: 0
- tracked runtime/private artifacts introduced: 0

## 8. Known Risks

1. List and Reader position state remain browser-local and do not synchronize
   across devices or profiles.
2. URL context is intentionally bounded to Article identity and a safe local
   return path; it does not persist arbitrary Tutor form or Graph filter state.
3. Browser verification depends on a compatible Chromium runtime.
4. The application remains a local, single-user system.

## 9. Closure State

All authorized local implementation, browser, test, build, security, artifact,
and protected-boundary gates are **PASS**. P3-014 remains active until the
implementation commit and a later docs-only closure commit each pass exact-SHA
main CI. No v1.2 candidate or subsequent task is assigned.
