# P3-027 Tutor Request Ownership and Accessible Feedback

## Status

PASS / CLOSED

## Task Identity

Make Tutor answers and Quiz feedback belong to the exact submitted context and
remain discoverable to keyboard and assistive-technology users.

## Authoritative Baseline

- Starting commit: `5b1de79f6176db00e2dd2f557ce255f7070b0293`
- Cached `origin/main`: `5b1de79f6176db00e2dd2f557ce255f7070b0293`
- Starting ahead / behind: `0 / 0`
- Previous task: P3-026 PASS / CLOSED
- Previous closure CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33905442849`
- Formal version: `v1.1.0`
- Candidate version: not assigned
- Entry worktree, index, and untracked set: clean
- `REWORK.md` and `.audit`: absent
- Two independent product audits compared the transient Graph-to-Reader
  navigation debt with deterministic Tutor ownership and accessibility gaps.

## Background

- A Tutor request generation is invalidated by a mode change, but not by an
  Article, Graph context, or prompt change. A completed request can therefore
  publish an answer under controls that no longer describe its submitted
  context.
- Tutor loading, answer, empty-result, and Quiz-ready transitions do not have a
  complete live-status or focus contract.
- Quiz scoring inserts the score above the trigger without moving focus or
  announcing the result. Reset has no deterministic keyboard return target.
- The Study mode control declares `tablist` while exposing pressed buttons,
  rather than implementing the required tab roles and keyboard model.
- The P3-026 Graph-to-Reader timeout occurred once and then passed 16 complete
  same-SHA runs. It remains a bounded stress-diagnostic debt, not part of this
  deterministic Tutor revision.

## Goals

1. Bind each Tutor request to an immutable mode, prompt, Article, and Graph
   context snapshot.
2. Prevent any stale success, failure, Quiz, or activity write from publishing
   after the visible request context changes.
3. Announce request progress and move focus predictably to Answer, Quiz,
   empty-result, error, score, and retry targets.
4. Preserve the existing grounded Tutor, source, Quiz, and local activity
   contracts without Backend or API changes.

## Non-Goals

- Tutor model, prompt, RAG, source-selection, citation, or scoring changes
- Backend, API, Provider, Article, Graph, Zotero, or persistence changes
- New Tutor modes, adaptive learning, recommendations, or automatic submission
- Graph-to-Reader transition repair; retain it as a separate stress task
- Dependency, framework, lockfile, workflow, candidate, tag, or Release work

## Request Ownership Contract

1. Each submission captures the exact mode, prompt, selected Article ID, and
   normalized Graph node ID sent to the existing client.
2. Only the latest request generation may publish response, Quiz, error,
   ready status, or recent-activity mutation.
3. Mode, prompt, Article, Graph context, or route-provided context changes
   invalidate an in-flight request and clear output that no longer belongs to
   the visible controls.
4. A stale request may finish at the transport layer but has no visible or
   persisted UI effect.
5. Follow-up selection may preserve the completed answer while placing the
   next prompt and focus in the question field; it does not auto-submit.

## Accessibility And Responsive Contract

- Study modes use one coherent pressed-button group semantics, not an invalid
  partial tab pattern.
- The Tutor workspace exposes a polite atomic status for loading and completed
  outcomes and an assertive error path.
- Answer and non-answer outcomes receive programmatic focus after completion.
- A generated Quiz receives focus at its heading; submitted score receives
  focus and a complete announcement; reset returns focus to the first answer.
- Focus targets remain visibly outlined and in the viewport.
- Long Answer, Quiz review, and error states fit at 1440 x 900, 390 x 844,
  320 x 844, and 720 x 450 without document-level horizontal overflow.

## Allowed Changes

- `frontend/src/components/TutorView.tsx`
- `frontend/src/components/TutorQuizWorkspace.tsx`
- `frontend/src/components/TutorSourceList.tsx` only for Tutor result/Quiz
  responsive containment
- `frontend/src/components/TutorArticlePicker.tsx` only if required for request
  ownership or truthful dynamic status
- `frontend/src/lib/tutorWorkspace.ts`
- `frontend/tests/tutor.test.ts`
- `scripts/e2e/run_product_e2e.py`
- P3-027 canonical, alignment, current-state, roadmap, README, and report files

## Prohibited Actions

- Backend, published API, frozen M1, Article/source records, derived assets,
  Graph data, Tutor persistence, or Provider changes
- Dependency, lockfile, framework, workflow, or release metadata changes
- Source access, external search, private Zotero, real/paid Provider, or other
  non-loopback network access
- Candidate, tag, Release, attestation, force push, or history rewrite
- Runtime/private artifacts, secrets, generated corpus, PDFs, HTML dumps,
  committed screenshots, traces, profiles, caches, or local databases

## Deliverables

- Generation-safe Tutor request ownership
- Accessible Tutor result and Quiz focus/status behavior
- Focused pure tests and Product E2E race, keyboard, and responsive coverage
- `docs/P3_027_TUTOR_REQUEST_OWNERSHIP_AND_ACCESSIBLE_FEEDBACK_REPORT.md`
- Implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance Criteria

### PASS

1. Prompt, Article, Graph, mode, and route-context changes cannot publish a
   stale success, stale failure, stale Quiz, or stale activity mutation.
2. The visible response always belongs to the exact submitted context.
3. Loading and completion states expose truthful live status and `aria-busy`.
4. Answer, empty-result, and error outcomes receive deterministic focus.
5. Quiz generation, scoring, and reset provide deterministic focus, complete
   score announcement, hidden pre-submit answers, and keyboard operation.
6. Study mode semantics contain no partial or invalid tab pattern.
7. Desktop, mobile, and zoom-equivalent dynamic Tutor states have no document
   overflow, clipped controls, hidden result target, or unexpected browser
   errors.
8. Focused Frontend suites, production build, full Backend regression, and
   three isolated Product E2E runs pass with zero external requests.
9. Two independent final reviews plus workflow, dependency, secret, SBOM,
   artifact, and protected-path gates pass.
10. Implementation and closure commits each pass exact-SHA main CI; final
    `main` is clean and synchronized.

### CONDITIONAL

No conditional closure. Any unverified ownership or accessibility claim stays
open.

### BLOCKED

- A request can still publish under changed visible context.
- A keyboard or assistive-technology outcome cannot be made deterministic
  within the allowed Frontend/test/documentation paths.
- A required gate needs Backend, API, data, dependency, workflow, external,
  private, Provider, or release changes.
- Unknown worktree changes or forbidden artifacts appear.

## Execution Plan

1. Persist the bounded task and alignment.
2. Add failing pure request-context tests and focused browser assertions.
3. Implement request snapshot ownership, context invalidation, live status,
   result focus, Quiz score focus, reset focus, and coherent mode semantics.
4. Validate delayed stale requests, keyboard-only Quiz flow, dynamic mobile
   states, and existing grounded-source behavior.
5. Run focused and full gates, obtain two independent reviews, and repair all
   in-scope findings.
6. Commit and push implementation, verify exact-SHA CI, then commit and push a
   docs-only closure and verify its exact-SHA CI.

## Verification Commands

- `npm --prefix frontend run test:tutor`
- `npm --prefix frontend run build`
- `uv run --project backend --extra dev pytest -q`
- `uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`
- repository workflow, suppression, dependency, secret, SBOM, artifact, and
  protected-path gates
- exact-SHA GitHub Actions readback for implementation and closure commits

## Artifact And Secret Policy

Only source, tests, and bounded text evidence may be committed. Temporary
screenshots and runtime state must remain outside the repository and be removed
after extracting bounded results.

## Git Plan

- Implementation commit: `fix: make tutor results context-safe and accessible`
- Push: non-force `main` push after all local gates pass
- CI: exact-SHA implementation readback required
- Closure commit: `docs: close P3-027 tutor feedback revision`
- Push: non-force `main` push after closure evidence is complete
- CI: exact-SHA closure readback required
- Tag / Release: not authorized

## Stop Conditions

- Unknown worktree changes or conflicts appear.
- Correct behavior requires a prohibited Backend, API, data, dependency,
  workflow, external/private, Provider, or release change.
- Tests, build, E2E, security, artifact, review, or exact-SHA CI fail without a
  deterministic in-scope repair.

## Completion Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 121 passed, including 22 Tutor tests
- production build: PASS, 11 routes
- Product E2E: 3/3 runs, 140 checks each, restart persistence PASS,
  0 external requests, unexpected console errors, or page errors
- required request/activity races, keyboard focus paths, and four responsive
  viewports: PASS
- independent final reviews: 2 PASS
- local workflow, suppression, secret, SBOM, artifact, and protected-path
  gates: PASS; dependency audit reserved for exact-SHA CI because it requires
  non-loopback network access
- Implementation commit:
  `b0679da2fd0c70d9148538a08ef942787846c895`
- exact-SHA implementation CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33914369113`
- required implementation CI jobs: PASS; normal-main Docker/release jobs
  skipped as designed; uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA closure CI readback required
  before final reporting
- Report: `docs/P3_027_TUTOR_REQUEST_OWNERSHIP_AND_ACCESSIBLE_FEEDBACK_REPORT.md`

## Next Task

Reassess the bounded Graph-to-Reader/Application Shell transition stress
diagnostic and remaining product convergence evidence. No v1.2 candidate is
assigned.
