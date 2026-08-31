# P3-014 Integrated Learning Workflow Alignment

Canonical task:
`docs/tasks/P3-014_INTEGRATED_LEARNING_WORKFLOW.md`

Status: **ACTIVE / IMPLEMENTATION AUTHORIZED**

LOCAL DATA READ / APPLICATION RUNTIME / COMPUTER USE AUTHORIZATION:
**GRANTED**

LOCAL FILE MODIFICATION / TEST / COMMIT / PUSH / CI AUTHORIZATION:
**GRANTED**

SOURCE NETWORK / PRIVATE ZOTERO READ-WRITE / REAL PROVIDER AUTHORIZATION:
**NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-013 Reader Workspace and Learning Continuity is PASS / CLOSED with its
  repair and docs-only closure exact-SHA main CI passing.
- The product already has a responsive shell, searchable Article collection,
  structured Reader, learning state, notes, references, Graph, Zotero metadata
  links, and Tutor.
- These capabilities remain distributed across routes, so the next improvement
  should reduce context loss and dead ends across the complete learning journey.
- Existing Article records, frozen M1 modules, derived assets, and published
  legacy, `/v1.1`, and `/v1.2` API contracts remain protected.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `5be49f05d1bf8055a8e844237fc7a058ca7c90d7`; entry worktree is clean.
- No REWORK or `.audit` blocker exists at task entry.

## 2. Requirements

1. Audit the real local desktop and mobile learning journey using existing
   Article data.
2. Improve the Dashboard -> search -> reading -> notes/bookmark -> Tutor/Graph
   -> return-to-reading workflow.
3. Prioritize navigation dead ends, lost Article context, unclear state, and
   mobile interaction issues found by evidence.
4. Reuse existing API and learning-state contracts; add no Backend contract.
5. Preserve Chinese, Markdown, formulas, code, references, and responsive
   rendering.
6. Add focused unit and browser regression coverage and complete three
   isolated Product E2E runs.
7. Run Backend, Frontend, E2E, compatibility, secret, artifact, dependency,
   workflow, suppression, and SBOM gates.
8. Replace generated agent-specific repository instructions with concise,
   platform-neutral governance while preserving task, safety, and Git controls.

## 3. Purpose

Turn the existing feature set into a coherent learning workflow in which a
learner can see what they are studying, choose the next relevant action, move
into existing learning tools with Article context, and return to the same
reading position without source-data or Backend changes.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Remove generated agent-specific instructions from `AGENTS.md` and retain a
   concise platform-neutral governance contract.
3. Inventory current Dashboard, Article, Tutor, Graph, notes/bookmark, route,
   local-state, corpus, and E2E boundaries.
4. Establish desktop and mobile browser baselines on three to five real local
   Articles and rank workflow defects by user impact.
5. Select and implement two to four high-impact Frontend-only corrections.
6. Preserve route context, safe return paths, controlled states, keyboard
   behavior, and reduced-motion behavior.
7. Add pure helper/component regression tests and extend isolated Product E2E.
8. Re-run real browser journeys and converge on stable desktop/mobile behavior.
9. Run all required local quality, compatibility, security, and artifact gates.
10. Create and push an implementation commit and verify exact-SHA main CI.
11. Create and push a docs-only closure commit and verify its exact-SHA main CI.

## 5. Selection Rationale

P3-013 made long Articles navigable and resumable. The highest-value next step
is connecting the existing Dashboard, Reader, Tutor, Graph, and learning-state
surfaces so users can complete a study loop without losing context. This uses
current contracts and directly improves the primary product workflow.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Integrated learning workflow | Selected: improves the complete user journey using current contracts |
| Visual-only restyling | Rejected: cannot resolve context loss or navigation dead ends |
| New Backend analytics | Deferred: requires contract and persistence expansion outside this task |

## 7. Deliverables

- updated `alignment.md`
- concise platform-neutral `AGENTS.md`
- `docs/tasks/P3-014_INTEGRATED_LEARNING_WORKFLOW.md`
- updated `docs/tasks/CURRENT_TASK.md`
- bounded Frontend helpers/components under `frontend/src/`
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_014_INTEGRATED_LEARNING_WORKFLOW_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- Three to five real local Articles provide desktop/mobile workflow evidence.
- At 1440 x 900 and 390 x 844, primary controls do not overflow, overlap, or
  become unreachable.
- A learner can move from Dashboard to an Article, enter at least two existing
  learning tools, and return to the same Article context.
- Article identity, safe return path, and reading resume state are preserved.
- Loading, empty, error, and 404 states remain controlled.
- Chinese, Markdown, code, references, images, and KaTeX remain correct.
- Primary controls are keyboard reachable, visibly focused, meaningfully named,
  and respect reduced-motion preference.
- Three consecutive isolated Product E2E runs pass without state leakage or
  external requests.
- Backend full tests, all focused Frontend tests, production build, security,
  artifact, workflow, dependency, and SBOM gates pass.
- Frozen M1 paths, Article records, Backend implementation, and published API
  contracts remain unchanged.
- No source access, private Zotero read/write, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- `AGENTS.md` contains no generated hook ecosystem, agent-specific interaction
  dependency, or tool-specific session-maintenance instructions.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Completion requires a frozen M1, Backend, or published API contract change.
- Completion requires source access, private Zotero access, or a real/paid
  Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.
