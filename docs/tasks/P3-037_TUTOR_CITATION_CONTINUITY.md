# P3-037 Tutor Citation Continuity

Status: OPEN / IMPLEMENTATION CI PENDING

## Baseline And Authorization

- Baseline: f87ba6bb0191d08fa84b0b5ef2cdf4d1a79a26db, clean synchronized main.
- Parent P3-036 closure run: 34212438350. Stage this task only after terminal
  exact-SHA success, seven required jobs and complete E2E evidence are read back.
- Formal version: v1.1.0; candidate: none.
- The owner authorizes continued platform/GUI improvement, independent
  sub-agent review and automatic execution without recurring plan confirmation.
- Existing P3-036 report section 22 records prototype evidence, not shipped code.
  Current rendered admission checks and a compiled-component RED corroborate
  the defect. Independent review approves the bounded native-link design.
- The earlier Graph visibility incident remains OPEN / UNRESOLVED, root cause
  UNKNOWN. This task does not repair or waive that incident.

## Objective

A learner can inspect a cited Article without losing the originating Tutor
answer, question, selected Article/Concept context or submitted Quiz work.
Retain the live Tutor tab and open document citations separately.

## Contract

1. Source-list local citations use native anchors with target="_blank",
   rel="noopener noreferrer", and visible accessible " (new tab)" text.
2. Keep resolveSourceArticleId and the existing encodeURIComponent(articleId)
   local route construction unchanged. Metadata ID precedence, chunk fallback
   and unsafe ID rejection stay intact; source URL query/hash is not grafted
   onto local IDs.
3. Source-list original links retain the exact safe external href, adding the
   same isolation attributes and cue. Never activate external sites in tests.
4. TutorMarkdown keeps getSafeTutorMarkdownHref unchanged. Every accepted
   non-hash document href receives the same native-anchor behavior, including
   mixed-case HTTP(S). Preserve raw query order, duplicate parameters, encoded
   values and fragments exactly; separately test browser-resolved destinations.
5. Hash-only links stay in the same document without new-tab attributes/cue.
   Rejected URLs stay noninteractive. Intentional Return to article/concept
   navigation is unchanged and stays in the same tab.
6. While the Reader child exists and after it closes, preserve parent prompt,
   mode, selected Article, populated Graph input or Concept-origin banner and
   Return href, rendered context counts, answer/Quiz choices and nontrivial
   score, disclosure, URL/history state, scroll and initiating-link focus.
7. Exactly one child opens to the expected Reader with window.opener null.
   No additional /tutor/ask, /tutor/quiz or /tutor/sessions POST occurs.
8. Preserve visible keyboard focus, readable cues and no clipping/page overflow
   at 1440x1000, 390x844, 320x844 and 720x450.
9. No persistence across refresh, eviction or closing the Tutor tab is promised.
   No physical-mobile or popup-policy guarantee is inferred from Chromium
   viewport emulation. No window.open, named-window reuse or same-tab fallback.

## Allowed Changes

- frontend/src/components/TutorSourceList.tsx
- frontend/src/components/TutorMarkdown.tsx
- frontend/tests/tutor.test.ts, admission-boundary regressions only
- scripts/e2e/run_product_e2e.py, additive rendered regressions only
- this canonical task and docs/P3_037_TUTOR_CITATION_CONTINUITY_REPORT.md
- alignment.md, docs/tasks/CURRENT_TASK.md, docs/00_PROJECT_STATE.md,
  roadmap.md, docs/V1_2_ROADMAP.md and README.md
- closure-status/evidence only in the P3-036 canonical task/report,
  P3-036.1 canonical task, and P3-005.2 canonical task/report

## Exclusions

No other product component/helper, Backend, API, provider, persistence, storage,
M1 module, Article/source record, corpus, Graph/reference data, matching,
dependency, lockfile, workflow, release/version/candidate, tag or Release change.
No source crawl/search, private Zotero, real/paid provider or non-loopback browser
request. No test-admission relaxation, blanket popup exemption, changed
exactly-25-ended-session restart gate, blind CI rerun or destructive Git.
No private/runtime artifacts, credentials, databases, PDFs, HTML dumps, images,
screenshots, traces, profiles, caches or corpora in Git.

## Verification

- Actual compiled components, never replacement anchors.
- Core 24 cases: Article picker + actual Graph input / public Concept launch,
  Explain list / Explain inline / submitted Quiz list, pointer / Tab-Enter,
  at both 1440x1000 and 390x844.
- Six inline-mode cases: Derive, Q&A and Research at both core widths.
- Four constrained cases: Explain and submitted Quiz source lists, keyboard,
  at 320x844 and 720x450.
- Five unique source rows, expanded disclosure and a citation beyond the first
  three, including a different Article from the selected context. Check
  metadata precedence, chunk fallback, invalid metadata fallback and invalid IDs.
- Nontrivial Quiz result (1/2), retained per-question choices and review.
- Rendered relative/absolute/mixed-case hrefs, repeated/encoded queries,
  fragments, invalid URL families, hash activation and existing intentional
  Article/Concept Return round trips.
- Observe both pages before activation; audit exact destination and one child.
  Compare state before, while open, and after close without focus repair.
- Narrow context-level Reader-session fixtures own their POST/read/end paths
  and validate payloads; actual canonical-store readback must remain unchanged.
  All existing global request/error/page audits and restart checks remain intact.
- Temporary fake-runtime only; no external citations activated. Any screenshots
  needed for visual inspection are temporary and removed.

Commands:

- npm --prefix frontend run test:tutor
- npm --prefix frontend run test:articles
- npm --prefix frontend run test:references
- npm --prefix frontend run test:graph
- npm --prefix frontend run build
- uv run --project backend --extra dev pytest -q
- uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start
- repository workflow, suppression, secret, dependency, temporary SBOM,
  artifact and protected-path gates
- exact-SHA main CI readback, with normal-main Docker/release skips recorded

## Delivery And Status

Deliver the two-component behavior, focused and rendered regressions, this task,
its evidence report and truthful status pointers. Two independent final reviews
must have no unresolved Critical/Important finding.

PASS / CLOSED requires all local, review, safety and exact-SHA implementation
and separate docs-only closure CI gates, with clean synchronized main.
No conditional closure. A required behavior/test/review/safety/CI failure keeps
the task open for evidence-directed diagnosis; do not relax existing assertions.
Unknown worktree drift, forbidden artifacts/secrets, or a necessary out-of-scope
change stops the affected action without overwriting user work.

## Git Plan

Implementation: fix: preserve tutor citation workspace
Then authorized non-force main push and exact-SHA required-job readback.
After success, a separate docs-only closure: docs: close P3-037 tutor citation continuity
Push that commit non-force and verify its exact-SHA CI before final closure.
Do not create/move tags, create/edit Releases, or assign a v1.2 candidate.
