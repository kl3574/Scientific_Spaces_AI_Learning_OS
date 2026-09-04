# P3-027 Tutor Request Ownership and Accessible Feedback Report

Status: **LOCAL ACCEPTANCE PASS / IMPLEMENTATION EXACT-SHA CI PENDING**

## 1. Scope And Boundaries

P3-027 makes Tutor results belong to the exact submitted mode, prompt,
Article, and Graph context. It also makes loading, Answer, Quiz, score, reset,
empty-result, and error outcomes discoverable through coherent status and
focus behavior.

The change is limited to Tutor Frontend components, a pure request-ownership
helper, focused tests, Product E2E, and governance documentation. Backend
code, published APIs, frozen M1 modules, Article/source records, Graph data,
Tutor persistence, Providers, dependencies, lockfiles, workflows, and release
metadata remain unchanged. No external source, private Zotero, or real/paid
Provider was accessed.

## 2. Request Ownership

- Each submission captures an immutable snapshot of mode, question, selected
  Article ID, and normalized Graph node ID.
- A generation guard permits only the latest matching request to publish an
  Answer, Quiz, empty result, error, ready status, or activity mutation.
- Prompt, Article, Graph, mode, route-provided context, same-route context
  removal, and unmount invalidate pending ownership.
- Stale transport completions remain silent and cannot write recent activity.
- Follow-up selection preserves the accepted answer and places the next prompt
  in the question field. Submitting that prompt creates a new generation.

Pure tests cover exact ownership matching and each context dimension. Product
E2E covers delayed stale success, failure, Quiz, activity completion, route
changes, same-route context removal, and unmount.

## 3. Activity Ordering

Activity persistence and session readback now use separate monotonic request
ownership. A failed activity POST publishes its exact failure only while its
Tutor generation remains current. An older pending session GET cannot erase a
newer activity error, and delayed completions after an ordinary context change
remain silent.

Product E2E verifies the ordering explicitly: an old session GET remains
pending, the newer activity POST fails, the exact error is published, and the
released old GET cannot replace it. Follow-up selection preserves that error;
follow-up submission or an ordinary context change clears it.

## 4. Accessible Status And Focus

- The workspace exposes truthful `aria-busy` state.
- A separate polite, atomic live status announces request progress and
  accepted completion without being hidden inside the busy region.
- Accepted Answer, empty-result, refusal, error, and generated Quiz outcomes
  receive deterministic programmatic focus with visible outlines.
- Study modes use a labelled pressed-button group with exactly one active
  choice and no incomplete tablist semantics.
- Focus remains attached only to the current accepted result; stale work cannot
  steal focus.

## 5. Quiz Interaction

- A generated Quiz focuses its workspace heading.
- Answers remain hidden before submission.
- The submitted score is a polite, atomic status and receives focus.
- Reset returns focus to the first answer control.
- Keyboard-only generation, answer selection, submission, scoring, and reset
  are covered by Product E2E.

## 6. Responsive Containment

Long Tutor answers, sources, Quiz choices, review text, empty states, and error
messages use bounded widths and anywhere wrapping where necessary. Product E2E
checks document width, focused-target visibility, and dynamic result geometry
at 1440 x 900, 390 x 844, 320 x 844, and 720 x 450.

## 7. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 39.75s
```

### Frontend

- Article and Reader suites: 46 passed
- global search: 5 passed
- Graph and Concept Study Set: 27 passed
- structured References: 3 passed
- Saved Learning Library: 5 passed
- Focused Session: 13 passed
- Tutor: 22 passed
- focused total: 121 passed
- Next.js 15.5.21 production build: PASS, 11 routes
- Tutor route: 11.9 kB / 243 kB first load
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py \
  --repeat 3 --frontend-mode start
```

- complete runs: 3
- successful runs: 3
- checks per run: 140
- restart persistence: PASS
- Chromium: 149.0.7827.55
- non-loopback requests: 0
- unexpected console errors: 0
- page errors: 0

The runner now owns complete process groups, so production Frontend children
are terminated after every isolated run and ports 3000/8000 are not leaked.

## 8. Security, Artifact, And Protected Paths

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action full-SHA pin rate: 100 percent
- explicit workflow and job permission rate: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- temporary SBOM cleanup: PASS
- Backend, workflow, dependency, lockfile, published API, frozen M1, Article,
  source, Graph-data, Tutor-persistence, and Provider changes: 0
- new runtime/private artifacts: 0

The dependency audit requires registry/network access and was not run locally
because P3-027 prohibits non-loopback network access. The existing exact-SHA
CI gate will run it before task closure.

## 9. Independent Review

Two independent final reviews returned PASS after all in-scope findings were
repaired. The correctness review verified generation ownership, paired-state
cleanup, activity ordering, and stale readback suppression. The accessibility
review verified route/unmount invalidation timing, deterministic response
gates, pressed-button mode semantics, result/Quiz focus, and all four required
viewports.

## 10. Known Risks

- Transport work is generation-guarded rather than cancelled. Correctness does
  not depend on cancellation, but stale requests may still consume local fake
  runtime work until completion.
- Recent activity remains backed by the existing persistence contract; this
  task does not add cross-device or multi-user behavior.
- Earlier pre-final stress attempts observed intermittent existing Application
  Shell hydration behavior on non-Tutor navigation. The final exact snapshot
  passed all three 140-check runs with zero console/page errors. This remains a
  separately bounded Shell/navigation stress debt, not a Tutor ownership
  failure.

## 11. Current Decision

P3-027 local acceptance is PASS. Focused tests, the production build, full
Backend regression, three-run Product E2E, local security/artifact gates, and
two independent reviews pass. The implementation commit and exact-SHA main CI
remain required before the task can be marked PASS / CLOSED. No v1.2 candidate
is assigned.
