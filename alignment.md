# P3-015 Visual Knowledge Explorer Alignment

Canonical task:
`docs/tasks/P3-015_VISUAL_KNOWLEDGE_EXPLORER.md`

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

LOCAL CORPUS READ / APPLICATION RUNTIME / COMPUTER USE AUTHORIZATION:
**GRANTED FOR P3-015**

FRONTEND / TEST / DOCUMENTATION MODIFICATION, OFFICIAL NPM REGISTRY READ,
COMMIT / PUSH / CI INSPECTION AUTHORIZATION: **GRANTED FOR P3-015**

SOURCE NETWORK / PRIVATE ZOTERO READ-WRITE / REAL PROVIDER AUTHORIZATION:
**NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-014 Integrated Learning Workflow is PASS / CLOSED with its implementation,
  repair, and docs-only closure exact-SHA main CI passing.
- The existing Graph route exposes search, a node list, node details, and a
  bounded textual relationship list, but it does not visually present the
  returned knowledge network.
- Existing `/graph/summary`, `/v1.1/graph/nodes`, `/graph/nodes/{node_id}`, and
  `/v1.1/graph/subgraph` interfaces already provide the bounded data needed for
  a visual explorer without Backend or data-contract changes.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `36eafb5915122a9254c0c8e07c2c87c75042d55b`; entry worktree is clean.
- No REWORK or `.audit` blocker exists at task entry.

## 2. Requirements

1. Upgrade `/graph` from a list-and-text surface to an interactive visual
   knowledge explorer while preserving the existing list and detail views.
2. Add an explicit Map/List segmented view and retain bounded search and node
   selection behavior.
3. Visualize the selected subgraph with deterministic layout, typed nodes,
   relationship labels, selected/focused states, and a visible legend.
4. Support pan, zoom, fit-view, direct node selection, keyboard access, and
   reduced-motion behavior on desktop and mobile.
5. Preserve Article -> Graph context, exact Article-node centering, free graph
   exploration, and same-Article/section return navigation.
6. Reuse current Graph interfaces and data; add no Backend or published API
   contract.
7. Add focused unit and browser regression coverage and complete three
   isolated Product E2E runs.
8. Run Backend, Frontend, E2E, dependency, secret, workflow, suppression,
   SBOM, artifact, and protected-path gates.

## 3. Purpose

Make relationships among Articles, Sections, Concepts, Formulas, and Zotero
items directly inspectable so a learner can understand and navigate local
knowledge context instead of reconstructing it from a text list.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Add the exact pinned `@xyflow/react@12.11.5` dependency and lockfile entry.
3. Implement one deep visualization module with a small typed interface and a
   deterministic bounded layout for the existing subgraph response.
4. Integrate Map/List controls, visual legend, viewport controls, selection,
   and controlled loading/empty/error states into `GraphView`.
5. Preserve the existing textual detail and relationship representation as an
   accessible fallback and complementary inspection surface.
6. Add pure layout/presentation tests and Graph interaction regression tests.
7. Extend isolated Product E2E for visual map selection, Article context,
   return navigation, keyboard access, and responsive geometry.
8. Validate three to five real local Graph nodes at 1440 x 900 and 390 x 844
   with all external requests blocked.
9. Run all required local quality, compatibility, security, and artifact gates.
10. Create and push an implementation commit and verify exact-SHA main CI.
11. Create and push a docs-only closure commit and verify its exact-SHA main CI.

## 5. Selection Rationale

The Graph data and bounded retrieval interfaces already exist, while the
current GUI renders relationships only as prose. React Flow supplies mature
viewport and interaction behavior; a project-owned deterministic layout keeps
the module bounded, reproducible, and testable without adding physics or
Backend complexity.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| React Flow plus deterministic bounded layout | Selected: complete interaction with one pinned dependency |
| Hand-written SVG interaction stack | Rejected: duplicates zoom, pan, focus, and accessibility behavior |
| Dashboard-only refinement | Deferred: does not address the largest remaining visual capability gap |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-015_VISUAL_KNOWLEDGE_EXPLORER.md`
- updated `docs/tasks/CURRENT_TASK.md`
- `frontend/src/components/GraphVisualization.tsx`
- `frontend/src/lib/graphVisualization.ts`
- bounded updates to Graph presentation, tests, styles, and Product E2E
- pinned Frontend manifest and lockfile updates
- `docs/P3_015_VISUAL_KNOWLEDGE_EXPLORER_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- Map/List switching, direct node selection, zoom, pan, and fit-view work.
- The selected node and up to 25 nodes / 50 relationships are rendered from
  the exact bounded response with deterministic positions.
- Node types and relationship direction are visually distinguishable without
  relying on color alone; selected and keyboard-focused states are explicit.
- Article context selects the exact `article:<article_id>` node, remains stable
  during free exploration, and returns to the exact Article section.
- Existing list, detail, provenance, loading, empty, error, and retry behavior
  remains available and controlled.
- At 1440 x 900 and 390 x 844, the explorer has stable dimensions with no page
  overflow, overlap, clipped primary action, or inaccessible control.
- Three to five real local nodes across representative types pass browser
  validation with zero external requests, console errors, and page errors.
- Primary controls are keyboard reachable, visibly focused, meaningfully named,
  and respect reduced-motion preference.
- Three consecutive isolated Product E2E runs pass without state leakage.
- Backend full tests, all focused Frontend tests, production build, security,
  artifact, workflow, dependency, and SBOM gates pass.
- Frozen M1 paths, Article records, Backend implementation, derived Graph data,
  and published API contracts remain unchanged.
- No source access, private Zotero read/write, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Completion requires Backend, frozen M1, Graph data, or published interface
  changes.
- Completion requires source access, private Zotero access, or a real/paid
  Provider call.
- The pinned dependency introduces an unresolved security or compatibility
  finding.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.
