# P3-013 Reader Workspace and Learning Continuity Alignment

Canonical task:
`docs/tasks/P3-013_READER_WORKSPACE_AND_LEARNING_CONTINUITY.md`

Status: **LOCAL GATES PASS / EXACT-SHA CI PENDING**

LOCAL DATA READ / APPLICATION RUNTIME / COMPUTER USE AUTHORIZATION:
**GRANTED**

LOCAL FILE MODIFICATION / TEST / COMMIT / PUSH / CI AUTHORIZATION:
**GRANTED**

SOURCE NETWORK / PRIVATE ZOTERO READ-WRITE / REAL PROVIDER AUTHORIZATION:
**NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-012 is PASS / CLOSED with implementation and docs-only closure exact-SHA
  main CI passing.
- The application has a responsive shell, searchable Article collection,
  learning state, notes, references, Graph, and Tutor.
- Long scientific Articles still lack a section model, current-section
  feedback, scroll restoration, reading progress, and reader display controls.
- Existing Article records, M1 frozen modules, derived assets, and published
  legacy, `/v1.1`, and `/v1.2` API contracts remain protected.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `6b297d8ae21b1b43ef2e6e7a1b0bef51e5d71b83`; entry worktree is clean.
- No REWORK or `.audit` blocker exists at task entry.

## 2. Requirements

1. Build a scientific Article reading workspace over the existing Article
   Detail page.
2. Derive a deterministic outline and stable unique section anchors from the
   existing Markdown without changing Article content.
3. Expose current-section navigation and bounded reading progress.
4. Persist and restore the last meaningful section and progress locally per
   Article.
5. Add local-only text-size and reading-width controls.
6. Add a clear Dashboard Continue Reading entry using existing local reading
   state.
7. Preserve Chinese, Markdown, code, formulas, tables, images, citations, and
   local deep links at desktop and mobile viewports.
8. Keep keyboard navigation, focus, reduced-motion behavior, loading, empty,
   error, and 404 states controlled.
9. Add focused unit and browser regression coverage and complete three
   isolated E2E runs.
10. Run Backend, Frontend, E2E, compatibility, secret, artifact, dependency,
    workflow, suppression, and SBOM gates.

## 3. Purpose

Reduce navigation and recovery cost for long scientific Articles so a learner
can identify structure, move between sections, see progress, leave, and resume
without altering source data or adding a new Backend contract.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Inventory the current Reader, history model, local corpus samples, and test
   boundaries.
3. Establish desktop/mobile browser baselines on three to five local Articles
   containing headings, formulas, code, tables, or long references.
4. Add pure outline, slug, progress, preference, and resume-state helpers with
   focused tests.
5. Integrate an accessible outline, progress display, reader controls, and
   local resume behavior into Article Detail.
6. Add Dashboard Continue Reading behavior without changing Backend data.
7. Re-run real browser journeys, classify issues, and iterate through three
   evidence-driven convergence passes.
8. Extend the isolated product E2E suite and verify state isolation.
9. Run all required local quality and artifact gates.
10. Create and push an implementation commit, verify exact-SHA main CI, then
    create and push a docs-only closure commit and verify its exact-SHA CI.

## 5. Selection Rationale

The Article view is the common entry point for search, learning state,
references, Graph context, and Tutor use. A presentation-only workspace
provides the largest workflow improvement while preserving frozen source data
and published API contracts.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Reader workspace and learning continuity | Selected: directly improves the primary learning workflow using current contracts |
| Dashboard analytics expansion | Deferred: useful, but does not solve long-Article navigation or recovery |
| Visual-only restyling | Rejected: cannot improve continuity or section-level interaction |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-013_READER_WORKSPACE_AND_LEARNING_CONTINUITY.md`
- updated `docs/tasks/CURRENT_TASK.md`
- outline, progress, preference, and resume-state Frontend helpers/components
- Article Detail and Dashboard integration
- focused Frontend tests and expanded `scripts/e2e/` coverage
- `docs/P3_013_READER_WORKSPACE_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- Three to five real local long Articles provide browser evidence for outline,
  formulas, code, tables, references, and responsive behavior.
- Outline entries map to unique stable anchors and keyboard-operable links.
- The active section and progress update while reading; reported progress is
  clamped to 0-100 percent.
- Reopening an Article restores the last meaningful local reading position
  without mutating Article or Backend data.
- Dashboard exposes one unambiguous Continue Reading action when history exists
  and a controlled empty state when it does not.
- Text-size and reading-width preferences persist locally, remain reversible,
  and do not shift fixed controls incoherently.
- At 1440 x 900 and 390 x 844 there is no page-level overflow, overlap, or
  clipped primary control.
- Chinese, Markdown, code, tables, images, citations, and KaTeX remain correct.
- Primary controls are keyboard reachable, visibly focused, and meaningfully
  named; reduced-motion preference is respected.
- Three consecutive isolated E2E runs pass without state leakage or external
  requests.
- Backend full tests, all focused Frontend tests, production build, security,
  artifact, workflow, dependency, and SBOM gates pass.
- Frozen M1 paths, Article records, and published API contracts remain
  unchanged.
- No source access, private Zotero read/write, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Completion requires a frozen M1 or published API contract change.
- Completion requires source access, private Zotero access, or a real/paid
  Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.
