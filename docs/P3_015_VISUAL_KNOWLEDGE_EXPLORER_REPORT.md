# P3-015 Visual Knowledge Explorer Report

## 1. Current Status

- task: P3-015 Visual Knowledge Explorer
- local implementation: **PASS**
- implementation commit: `8224b072434c016b348311cb27cc41c4ae593a14`
- implementation exact-SHA main CI: **PASS** ([run 33351208778](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33351208778))
- task closure: **PASS / CLOSED**
- entry commit: `36eafb5915122a9254c0c8e07c2c87c75042d55b`
- candidate version: not assigned

P3-015 turns the existing bounded Graph response into an interactive visual
knowledge explorer. The implementation changes Frontend presentation and test
coverage only; Backend interfaces, Article records, and derived Graph data are
unchanged.

## 2. Baseline and Design

The previous Graph route exposed search, a node list, node details, provenance,
and a textual bounded-context list. Relationships were inspectable but not
visible as a graph.

The selected design adds an exact-pinned `@xyflow/react@12.11.5` presentation
layer over the existing subgraph contract. A project-owned pure layout helper:

- retains the selected node as the exact center;
- sorts nodes and relationships deterministically;
- deduplicates node and relationship identifiers;
- filters relationships whose endpoints are outside the bounded node set;
- limits presentation to 25 nodes and 50 relationships; and
- assigns stable two-ring positions without a physics simulation.

The dependency is MIT licensed, supports the project's React version, and
passed the repository dependency audit with no finding.

## 3. User Experience

### Map and list modes

- `Map` is the default knowledge-context view.
- `List` preserves the complete accessible textual relationship view.
- Both modes preserve loading, empty, error, and retry states.
- Search, node details, provenance, pagination, and existing deep links remain
  available.

### Visual language

- Article, Section, Concept, Formula, and Zotero nodes have distinct symbols,
  names, and colors, so type does not depend on color alone.
- Directed relationships use arrow markers and visible relationship labels.
- The selected center has an explicit ring and `aria-pressed` state.
- A persistent legend identifies every supported node type.

### Interaction and accessibility

- direct node selection recenters the bounded graph;
- pan, pinch zoom, double-click zoom, fit view, and explicit zoom controls are
  available;
- each node is a named native button and supports keyboard activation;
- focus-visible treatment is explicit;
- the existing reduced-motion policy applies to the explorer; and
- the mini-map is shown on larger viewports and hidden on mobile to preserve
  usable canvas space.

### Article continuity

Article -> Graph navigation selects the exact `article:<article_id>` node.
Selecting another node changes only the current Graph selection; the original
Article and section return path remains intact.

## 4. Real Local Graph Evidence

The read-only probe used the exact local Article Store and derived Graph:

- Articles: 1,314
- Graph nodes: 53,046
- Graph relationships: 82,584
- external requests: 0
- private Zotero reads/writes: 0 / 0
- real Provider calls: 0

Representative real nodes were loaded through the existing application
interfaces in Chromium `149.0.7827.55`:

| Type | Node | Result | Bounded context |
| --- | --- | --- | --- |
| Article | `article:74a286498ea0cf9c` | PASS | 5 nodes / 4 relationships |
| Section | `section:943d1e82f53a00fd:1:1.-tqdm-1.-tqdm` | PASS | 14 nodes / 13 relationships |
| Concept | `concept:a-b` | PASS | 2 nodes / 1 relationship |
| Formula | `formula:99e367...` | PASS | 2 nodes / 1 relationship |

The Graph did not contain a real Zotero node, so Zotero presentation is covered
by the typed deterministic fixture rather than a fabricated runtime record.

The Article context probe used Article `74a286498ea0cf9c`, selected its exact
Graph node, explored another node, and returned to
`/articles/74a286498ea0cf9c` successfully.

Geometry and runtime evidence:

- desktop viewport: 1440 x 900; document width: 1440 px
- mobile viewport: 390 x 844; document width: 390 px
- mobile Graph canvas: 350 x 480 px
- visible node/edge rendering: PASS
- overlap or clipped primary control: none observed
- console errors: 0
- page errors: 0

No screenshot, trace, profile, HTML, Article body, or runtime store was retained
in the repository.

## 5. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 76.62s
```

### Frontend

- Article and workflow helpers: 17 passed
- Structured References: 3 passed
- Graph, presentation, and deterministic layout: 10 passed
- Tutor: 13 passed
- focused total: 43 passed
- Next.js 15.5.21 production build: PASS, 9 routes
- `/graph`: 64.9 kB route code, 171 kB first load

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

- complete runs: 3
- successful runs: 3
- checks per run: 22
- visual map selection and keyboard recentering: PASS
- Map/List switching: PASS
- Article -> Graph -> Article continuity: PASS
- mobile visual explorer and 390 px width: PASS
- external requests: 0
- console errors: 0
- page errors: 0
- Backend restart persistence: PASS

## 6. Security and Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- explicit workflow permissions: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- dependency audit: PASS, 40 PyPI / 239 npm / 0 findings
- secret audit: PASS, 0 credible findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM output remained outside the repository

## 7. Protected Boundary Evidence

- Backend implementation changes: 0
- frozen M1 module changes: 0
- Article source-record changes: 0
- derived RAG, Graph, and Reference asset changes: 0
- legacy, `/v1.1`, or `/v1.2` API changes: 0
- source-site requests: 0
- private Zotero reads/writes: 0 / 0
- real or paid Provider calls: 0
- candidate, tag, Release, or attestation actions: 0
- tracked runtime/private artifacts introduced: 0

## 8. Known Risks

1. Dense 25-node contexts can require zoom or pan even though the layout is
   bounded and deterministic.
2. Relationship labels reflect source edge types and can be terse or
   domain-specific.
3. Browser behavior depends on the pinned React Flow dependency and a
   compatible browser runtime.
4. The current local Graph has no Zotero nodes, so that node type has fixture
   and presentation coverage but no real-corpus browser example.
5. The application remains local and single-user.

## 9. Closure State

All authorized local implementation, real-browser, test, build, security,
artifact, and protected-boundary gates are **PASS**. Implementation commit
`8224b072434c016b348311cb27cc41c4ae593a14` passed exact-SHA main CI run
[`33351208778`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33351208778):
Backend, Frontend, Product E2E, workflow policy, dependency, secret, and SBOM
jobs passed; Docker and release evidence were correctly skipped for a normal
`main` push; uploaded artifacts were zero.

P3-015 is **PASS / CLOSED**. This docs-only closure commit is the final
synchronization gate and must pass its own exact-SHA main CI before final
completion is reported.
