# P3-017 Guided Tutor Study Workspace Report

Status: **PASS / CLOSED**

## 1. Scope And Boundaries

P3-017 changes only the Frontend Tutor workspace, focused Frontend tests,
isolated Product E2E coverage, and task governance. It reuses these published
interfaces without changing them:

- `GET /v1.1/articles`
- `GET /articles/{id}`
- `POST /tutor/ask`
- `POST /tutor/quiz`
- `GET /tutor/sessions`
- `POST /tutor/sessions`

Backend code, frozen M1 paths, Article records, derived RAG/Graph/Reference
assets, dependencies, lockfiles, and API contracts are unchanged. No source
site, private Zotero library, real Provider, candidate, tag, Release, or
attestation action was used.

## 2. Guided Tutor Workspace

- The primary raw Article ID input is removed.
- A bounded six-result Article title/keyword search uses the existing v1.1
  Article list API and displays title plus metadata.
- Article-origin workflow context preselects the Article and preserves its
  exact safe Article/section return path.
- Optional Graph context remains available only under `Advanced context`.
- Explain, Derive, Q&A, Quiz, and Research remain explicit study modes.
- Article search, Tutor request, and recent-activity requests have independent
  status and recovery paths.

## 3. Scientific Answer Rendering

Tutor answers now use the existing `react-markdown`, GFM, MathJax-compatible
Markdown math, and KaTeX stack. Fenced code, inline `$...$`, and block
`$$...$$` are rendered. Raw HTML is not enabled, image loads are replaced by
bounded text, and links pass the project's strict local/external URL policy.

Follow-up questions are buttons. Selecting one fills and focuses the question
field but does not send a request. The current answer remains visible.

## 4. Quiz Contract

- Correct answers, explanations, and answer sources are not rendered before
  submission.
- Existing API options are retained when present.
- The current Backend emits grounded open questions. For suites with at least
  two unique questions, the Frontend deterministically uses the same suite's
  cited correct answers as cross-question choices. It does not invent or fetch
  outside knowledge.
- A single-question suite falls back to a text answer.
- Submission produces exact deterministic scoring, per-question review,
  explanations, and sources.
- `Try again` clears answers and removes all review disclosure.

## 5. Recent Tutor Activity

Each successful Tutor or Quiz request records one session through the existing
session endpoint. The workspace shows at most five reverse-chronological
entries with mode, human-readable Article title, bounded prompt/fallback, and
UTC time. Article, Graph, and session identifiers are never rendered.

Article title hydration is bounded to five session Article IDs. Older request
responses cannot overwrite newer session state. A session read/write failure
preserves the active answer or Quiz and exposes a separate retryable warning.

## 6. Real Local Article Evidence

A temporary local-only browser probe read the existing 1,314-Article Store and
the installed local RAG/Graph/Reference assets. Learning, Tutor, and Zotero
mutable files were redirected to a temporary directory; Tutor and Zotero
providers were fake; every non-loopback browser request was blocked.

Five deterministic mathematical Article samples passed:

| Article | Content characters | Answer | Activity |
| --- | ---: | --- | --- |
| 漫谈重参数：从正态分布到Gumbel Softmax | 13,208 | PASS | PASS |
| n维空间下两个随机向量的夹角分布 | 5,464 | PASS | PASS |
| logsumexp运算的几个不等式 | 7,571 | PASS | PASS |
| 必须要GPT3吗？不，BERT的MLM模型也能小样本学习 | 13,067 | PASS | PASS |
| Transformer升级之路：7、长度外推性与局部注意力 | 9,310 | PASS | PASS |

The first sample also passed answer-hidden Quiz generation, selection,
submission, scoring, and review. Desktop document width was 1,440 px; mobile
document width was 390 px at a 390 x 844 viewport. External requests, console
errors, and page errors were all zero. The temporary script and runtime were
deleted; no Article body, screenshot, trace, profile, or runtime data was
retained.

## 7. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 77.48s
```

### Frontend

- Article, Reader, workflow, and Dashboard helpers: 23 passed
- Structured References: 3 passed
- Tutor presentation and workspace: 19 passed
- Graph and visualization: 10 passed
- focused total: 55 passed
- Next.js 15.5.21 production build: PASS, 9 routes
- Tutor route: 9.75 kB route code, 240 kB first load

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

- complete runs: 3
- successful runs: 3
- checks per run: 28
- Article search/selection and exact return context: PASS
- Markdown, fenced code, and KaTeX: PASS
- follow-up fill/focus without auto-submit: PASS
- Quiz pre-submit disclosure count: 0
- Quiz scoring, review, sources, and reset: PASS
- intentional Tutor session 503 isolation: PASS
- mobile Tutor width: 390 px
- restart persistence: PASS
- external requests: 0
- console errors: 0
- page errors: 0

## 8. Security And Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- explicit workflow permissions: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- security utility tests: 17 passed
- dependency audit: PASS, 40 PyPI / 239 npm / 0 findings
- secret audit: PASS, 0 credible findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS

## 9. Artifact And Protected Paths

- Backend implementation changes: 0
- frozen M1 changes: 0
- Article Store or Article record changes: 0
- derived RAG/Graph/Reference changes: 0
- dependency or lockfile changes: 0
- tracked/untracked PDF, HTML dump, image, trace, profile, cache, database,
  secret, private Zotero, or runtime artifacts: 0

## 10. Known Risks

- Tutor answer quality remains bounded by existing local retrieval and Provider
  behavior; no real Provider quality claim is made.
- Grounded cross-question Quiz choices can be semantically close. They are
  deterministic and source-bound, but they are not pedagogically authored
  distractors.
- The existing session contract normally has no turn text when a session is
  created from this workspace, so recent activity uses a clear mode fallback.
- Article title hydration is intentionally limited to the five displayed
  activities.

## 11. Exact-SHA Main CI

- implementation commit:
  `b66f5b39ae66efa6c4a3c673058ded49f0b7147e`
- run:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33356672629`
- run event / branch / exact head SHA: `push` / `main` /
  `b66f5b39ae66efa6c4a3c673058ded49f0b7147e`
- Backend pytest: PASS
- Frontend build: PASS
- Product E2E three-run gate: PASS
- workflow policy: PASS
- dependency audit: PASS
- secret audit: PASS
- SBOM validation: PASS
- Docker compose smoke: correctly skipped for normal `main` push
- release evidence: correctly skipped for normal `main` push
- uploaded workflow artifacts: 0

The existing Actions Node 20 deprecation annotation remains a non-blocking CI
maintenance risk; the runner successfully used Node 24 and every required job
passed.

## 12. Closure

P3-017 is PASS / CLOSED. This docs-only closure commit must pass exact-SHA main
CI before final completion is reported. No subsequent task or v1.2 candidate
is assigned.
