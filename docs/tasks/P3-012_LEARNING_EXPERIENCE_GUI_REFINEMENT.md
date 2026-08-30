# P3-012 Learning Experience and GUI Refinement

## Status

LOCAL PASS / CI PENDING

## Objective

Converge the existing Scientific Spaces learning platform into a coherent,
responsive, accessible, and browser-verified learning experience without
changing protected data or published API contracts.

## Authoritative Alignment

`alignment.md`

## Entry State

- branch: `main`
- entry commit: `5933c17481a98db4b296eabac3a9d8947cd06704`
- P3-011: PASS / CLOSED
- exact local corpus: 1,314 Articles with matching derived assets
- candidate version: not assigned

## Evidence Method

Use the local `deep-research` skill to preserve an explicit chain from user
goal and browser observation to hypothesis, root cause, fix, and post-fix
evidence. Use Computer Use against the real local application; use automated
Playwright for repeatable regression. Do not use external websites in this
task.

## In Scope

- shared application shell and navigation
- Dashboard, Article List, and Article Detail UX
- Tutor, Structured References, and Knowledge Graph presentation
- loading, empty, error, and not-found states
- responsive behavior at desktop and mobile viewports
- keyboard, focus, semantic-label, and baseline accessibility improvements
- Frontend regression and product E2E coverage
- task evidence, commit, push, and exact-SHA CI closure

## Protected Boundaries

- no frozen M1 source, parser, converter, storage, sync, PDF, or Zotero changes
- no Article source-record mutation
- no legacy, `/v1.1`, or `/v1.2` API contract changes
- no source-site access or private Zotero reads/writes
- no real or paid Provider calls
- no candidate, tag, Release, or attestation
- no committed local stores, indexes, databases, screenshots, traces, browser
  profiles, credentials, secrets, or generated runtime assets

## Required User Journey

```text
open Dashboard
  -> navigate or search Articles
  -> open and read Markdown/formula content
  -> inspect and update bounded learning state
  -> inspect Reading History and References
  -> follow local Graph context
  -> use grounded Tutor
  -> exercise controlled empty/error/not-found states
  -> repeat on desktop and mobile
```

## Deliverables

- GUI/UX evidence and convergence matrix
- audited and refined Frontend experience
- reusable visual and interaction patterns
- focused component and browser regression tests
- three-pass convergence, responsive, accessibility, and negative-state
  evidence
- P3-012 implementation report and governance updates
- implementation and docs-only closure commits with exact main CI

## Acceptance

- all required pages and user-journey stages have real browser evidence
- every fixed issue has before, cause, correction, and post-fix evidence
- desktop and 390 px mobile layouts have no page-level overflow or overlap
- primary controls are keyboard reachable and visibly focused
- Chinese, Markdown, code, formulas, images, citations, and local deep links
  remain correct
- loading, empty, not-found, and unavailable states are controlled
- the third convergence pass has no unresolved high-severity product defect
- three consecutive isolated E2E runs pass without state leakage
- Backend, Frontend, compatibility, secret, artifact, and CI gates pass
- protected boundaries remain unchanged
- final branch is clean and synchronized

## Local Evidence

- real-corpus Chromium convergence: 3 passes, final PASS
- Backend: 600 passed, 4 skipped
- focused Frontend: 30 passed
- production build: PASS
- isolated product E2E: 3 / 3 complete runs PASS, 17 checks per run
- dependency, secret, workflow, suppression, and SBOM gates: PASS
- report: `docs/P3_012_LEARNING_EXPERIENCE_GUI_REFINEMENT_REPORT.md`
- exact-SHA main CI: pending implementation push

## Stop Rule

Stop without widening scope if completion requires a protected contract,
external side effect, private data action, release action, or unresolved
critical regression.
