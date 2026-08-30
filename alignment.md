# P3-012 Learning Experience and GUI Refinement Alignment

Canonical task:
`docs/tasks/P3-012_LEARNING_EXPERIENCE_GUI_REFINEMENT.md`

Status: **PASS / CLOSED**

LOCAL DATA READ / APPLICATION RUNTIME / COMPUTER USE AUTHORIZATION:
**CONSUMED / CLOSED**

LOCAL FILE MODIFICATION / TEST / COMMIT / PUSH / CI AUTHORIZATION:
**CONSUMED / CLOSED AFTER THE DOCS-ONLY CLOSURE COMMIT**

SOURCE NETWORK / PRIVATE ZOTERO READ-WRITE / REAL PROVIDER AUTHORIZATION:
**NOT GRANTED**

CANDIDATE / TAG / RELEASE AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-011 is PASS / CLOSED with deterministic local E2E and exact-SHA CI.
- The product is functionally complete but needs a systematic learning
  experience and GUI convergence pass based on real browser operation.
- The local `deep-research` skill supplies the evidence method, while Computer
  Use supplies direct interaction and visual evidence against the local app.
- Existing Article data, M1 frozen modules, derived assets, and published
  legacy, `/v1.1`, and `/v1.2` API contracts remain protected.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `5933c17481a98db4b296eabac3a9d8947cd06704`; entry worktree is clean.
- No REWORK or `.audit` blocker exists at task entry.

## 2. Requirements

1. Read and apply the local `deep-research`, `kimi-webbridge`, and, for hard
   defects, `diagnosing-bugs` skills.
2. Start the real local Backend and Frontend against approved local assets.
3. Operate Dashboard, Article List, Article Detail, Tutor, References,
   Knowledge Graph, and the shared shell through a real browser.
4. Audit desktop and mobile navigation, hierarchy, readability, feedback,
   interaction efficiency, consistency, responsiveness, and accessibility.
5. Build an evidence matrix with page, action, observation, severity, root
   cause, proposed correction, and verification criteria.
6. Fix confirmed in-scope issues and re-operate the browser to verify actual
   improvement.
7. Complete at least three discover-fix-reverify convergence passes, with the
   last pass free of unresolved high-severity product defects.
8. Add focused Frontend regression tests and repeatable browser E2E evidence.
9. Run Backend, Frontend, E2E, compatibility, secret, artifact, and CI gates.
10. Commit and push implementation and closure evidence, then verify exact-SHA
    main CI.

## 3. Purpose

Turn the verified functional platform into a coherent learning product whose
primary workflows are easy to scan, navigate, read, and operate on desktop and
mobile, with every material change grounded in observed browser evidence.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Read the applicable research, browser, and diagnosis skills.
3. Inventory routes, components, tests, design tokens, and runtime boundaries.
4. Start the real Backend and Frontend and use Computer Use on the local app.
5. Capture temporary desktop/mobile screenshots and conduct the first full
   page and workflow audit.
6. Convert observations into a severity-ranked evidence and fix matrix.
7. Implement focused shell, page, responsive, state, and accessibility fixes.
8. Re-run the same browser journeys and iterate until high-severity issues are
   resolved and the solution converges.
9. Extend component and product E2E regression coverage.
10. Run three complete isolated E2E passes and all required quality gates.
11. Update the P3-012 report and governance documents.
12. Create and push an implementation commit, verify exact-SHA main CI, then
    create and push a docs-only closure commit and verify its CI.

## 5. Selection Rationale

Real browser operation exposes layout, focus, scrolling, state, and workflow
defects that static inspection cannot prove. The deep-research method keeps
observations, hypotheses, fixes, and acceptance evidence traceable instead of
turning the task into an unbounded aesthetic rewrite.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Deep-research method plus real Computer Use and automated regression | Selected: strongest direct evidence and convergence loop |
| Code and screenshot review only | Rejected: cannot prove real interaction |
| Full Frontend rewrite | Rejected: excessive regression and migration risk |
| Cosmetic CSS-only pass | Rejected: insufficient for workflow, state, and accessibility defects |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-012_LEARNING_EXPERIENCE_GUI_REFINEMENT.md`
- updated `docs/tasks/CURRENT_TASK.md`
- a GUI/UX evidence and convergence matrix
- improved `frontend/src/` pages, components, and styles
- focused Frontend tests and updated `scripts/e2e/` coverage
- `docs/P3_012_LEARNING_EXPERIENCE_GUI_REFINEMENT_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- All primary pages are opened and operated through a real browser.
- The Dashboard -> Search -> Article -> Learning/History ->
  Tutor/References/Graph journey is connected and browser-verified.
- Each fixed issue has reproduction evidence, a root-cause account, a code or
  design correction, and post-fix browser plus regression evidence.
- At 1440 x 900 and 390 x 844 viewports there is no page-level horizontal
  overflow, incoherent overlap, or clipped primary control.
- Chinese, Markdown, code, images, and KaTeX content render correctly.
- Loading, empty, error, 404, and Backend-unavailable states are controlled.
- Primary commands are keyboard reachable, focus is visible, and interactive
  controls expose meaningful accessible names.
- Three convergence passes complete; the final pass has no unresolved
  high-severity product defect.
- Frontend tests and production build pass; Backend full tests pass.
- The complete browser E2E suite passes three consecutive isolated runs.
- Existing Article data, frozen M1 paths, and published legacy, `/v1.1`, and
  `/v1.2` API contracts remain unchanged.
- Temporary screenshots under `/tmp`, traces, profiles, builds, databases, and
  local corpus artifacts are not committed.
- No source access, private Zotero read/write, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Closure Evidence

- implementation commit:
  `75652e3d7a6a43d5b92f56d06aface7a7fc19d85`
- implementation main CI:
  [`33322848683`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33322848683),
  `success`
- Backend, Frontend, Product E2E, workflow policy, dependency, secret, and
  SBOM jobs: PASS
- Docker compose smoke and release evidence: correctly skipped for a normal
  `main` push
- uploaded workflow artifacts: 0
- source access, private Zotero, real Provider, candidate, tag, Release, and
  attestation actions: 0

The docs-only closure commit must pass its own exact-SHA main CI before the
final execution response claims synchronized completion. No subsequent task is
authorized by this closed alignment.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Completion requires a frozen M1 or published API contract change.
- Completion requires source access, private Zotero access, or a real/paid
  Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.
