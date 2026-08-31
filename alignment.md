# P3-017 Guided Tutor Study Workspace Alignment

Canonical task:
`docs/tasks/P3-017_GUIDED_TUTOR_STUDY_WORKSPACE.md`

Status: **LOCAL PASS / IMPLEMENTATION CI PENDING**

LOCAL ARTICLE DATA READ / APPLICATION RUNTIME / COMPUTER USE AUTHORIZATION:
**GRANTED FOR P3-017**

FRONTEND / TEST / DOCUMENTATION MODIFICATION, COMMIT / PUSH / CI INSPECTION
AUTHORIZATION: **GRANTED FOR P3-017**

BACKEND / FROZEN M1 / SOURCE RECORD / DERIVED RAG-GRAPH-REFERENCE / PRIVATE
ZOTERO / REAL PROVIDER AUTHORIZATION: **NOT GRANTED**

CANDIDATE / TAG / RELEASE / ATTESTATION AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-016 Learning Dashboard Command Center is PASS / CLOSED with its
  implementation and docs-only closure exact-SHA main CI passing.
- Dashboard, Reader, integrated navigation, and the Graph workspace expose a
  coherent learning flow, but the Tutor remains an API-oriented form.
- The Tutor exposes raw Article and Graph identifiers, renders the answer as
  plain text, reveals Quiz answers immediately, presents follow-up questions
  as static text, and reduces recent sessions to a count.
- Existing Article, Tutor answer, Quiz, source, workflow-context, and session
  interfaces are sufficient for this task; no Backend or persisted-data
  change is required.
- Entry branch is `main`; entry commit and cached `origin/main` are both
  `739ac4e24b1c3ff735b50f1062ffb7c9c799e4f0`; entry worktree is clean.
- No REWORK or `.audit` blocker exists at task entry.

## 2. Requirements

1. Turn `/tutor` into a guided study workspace while preserving Explain,
   Derive, QA, Quiz, and Research modes.
2. Replace the primary raw Article ID input with human-readable Article title
   search and selection through the existing Article API.
3. Preserve Article-to-Tutor workflow context and exact return to the original
   Article and section.
4. Move optional Graph Node input into an Advanced Context disclosure.
5. Render grounded answers as safe Markdown with code, inline math, and block
   math using existing Frontend dependencies and without raw HTML execution.
6. Implement a real Quiz interaction: answers and explanations remain absent
   before submission; learners select answers; submission reveals score,
   correct answers, explanations, and sources; retry/reset is available.
7. Make each follow-up question an explicit action that fills the next prompt
   without automatically submitting a request.
8. Replace the session count with a bounded, readable recent Tutor activity
   view that does not expose raw IDs.
9. Keep the active answer or Quiz usable if Article search or session loading
   fails independently.
10. Preserve keyboard access, visible focus, reduced motion, error recovery,
    and stable desktop/mobile geometry.

## 3. Purpose

Make the Tutor an actual learning workspace in which a learner can select an
Article by title, ask and follow up on grounded questions, complete a Quiz
without premature answer disclosure, and review recent Tutor activity.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Audit the existing Article, Tutor, Quiz, workflow-context, and session
   interfaces and current Product E2E fixture behavior.
3. Add a pure Frontend Tutor workspace model for Article selection, Quiz
   state/scoring, follow-up actions, and bounded session presentation.
4. Refactor `TutorView` into an Article context picker, mode/prompt workspace,
   optional advanced context, safe scientific response renderer, interactive
   Quiz, grounded source context, and recent activity surface.
5. Add focused Frontend tests and extend isolated Product E2E checks.
6. Validate three to five representative real local Articles at 1440 x 900
   and 390 x 844 with mutable state isolated, fake providers, and all external
   requests blocked.
7. Run Backend, Frontend, production build, Product E2E, dependency, secret,
   workflow, suppression, SBOM, artifact, and protected-path gates.
8. Create and push an implementation commit and verify exact-SHA main CI.
9. Create and push a docs-only closure commit and verify exact-SHA main CI.

## 5. Selection Rationale

The Tutor is the remaining high-value learning surface that still exposes
implementation identifiers and non-interactive output. Existing interfaces
and dependencies already support the intended experience, so a pure Frontend
workspace model delivers measurable usability and learning improvements
without widening Backend or data contracts.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Guided Tutor study workspace | Selected: directly improves the core learning workflow using existing contracts |
| Zotero GUI expansion | Deferred: useful for source operations but less central to guided learning |
| Global visual restyling | Rejected: broad churn without a bounded workflow outcome |
| Backend conversation API extension | Deferred: current response and session interfaces are sufficient |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-017_GUIDED_TUTOR_STUDY_WORKSPACE.md`
- updated `docs/tasks/CURRENT_TASK.md`
- project-owned Tutor workspace model and bounded components under
  `frontend/src/`
- focused Frontend tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_017_GUIDED_TUTOR_STUDY_WORKSPACE_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation and docs-only closure commits with exact-SHA CI evidence

## 8. Acceptance Criteria

- The primary Tutor flow requires no raw Article ID and supports bounded title
  search, explicit Article selection, clear selection, and clear reset.
- Article-origin context is preselected and the exact Article/section return
  link remains correct.
- Answers safely render Markdown, fenced code, inline `$...$`, and block
  `$$...$$`; raw HTML and unsafe links do not execute.
- Quiz answers, explanations, and answer sources are not rendered before
  submission; selectable answers, deterministic scoring, review, and retry
  work after submission.
- Follow-up actions fill the question field, move focus to it, and never
  auto-submit.
- Recent Tutor activity is reverse chronological, bounded, human-readable,
  and contains no raw Article, Graph, or session IDs.
- Article search and session failures are independently recoverable and do not
  remove an active answer or Quiz.
- At 1440 x 900 and 390 x 844, primary content has no page overflow, overlap,
  clipped action, or unusable control.
- Three to five real local Articles pass browser validation with temporary
  mutable state, fake providers, zero external requests, and no console or
  page errors.
- Three consecutive isolated Product E2E runs pass without state leakage.
- Backend full tests, focused Frontend tests, production build, dependency,
  secret, workflow, suppression, SBOM, artifact, and protected-path gates
  pass.
- Backend, frozen M1 paths, Article records, derived RAG/Graph/Reference
  assets, dependencies, lockfiles, and published API contracts remain
  unchanged.
- No source access, private Zotero read/write, real Provider call, candidate,
  tag, Release, or attestation action occurs.
- Implementation and closure commits pass exact-SHA main CI; final `main` is
  clean and synchronized.

## Stop Conditions

- The worktree develops unknown modifications or conflicts.
- Completion requires Backend, frozen M1, source-record, derived-asset,
  dependency, lockfile, or published-interface changes.
- Completion requires source access, private Zotero access, or a real/paid
  Provider call.
- A required test, build, browser, secret, artifact, or CI gate fails without
  an in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.
