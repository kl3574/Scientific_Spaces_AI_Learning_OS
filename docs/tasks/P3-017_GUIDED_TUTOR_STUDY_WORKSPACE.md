# P3-017 Guided Tutor Study Workspace

Status: **PASS / CLOSED**

## Objective

Replace the Tutor's API-oriented form and passive output with a guided,
grounded study workspace using only existing Frontend clients and published
interfaces.

## Entry Evidence

- branch: `main`
- entry commit: `739ac4e24b1c3ff735b50f1062ffb7c9c799e4f0`
- cached `origin/main`: `739ac4e24b1c3ff735b50f1062ffb7c9c799e4f0`
- ahead / behind: `0 / 0`
- worktree and index: clean
- REWORK / `.audit`: absent
- predecessor: P3-016 PASS / CLOSED

## In Scope

- human-readable Article search and selection for Tutor context
- exact Article/section return context
- optional advanced Graph context
- safe Markdown, code, and KaTeX response rendering
- selectable Quiz answers, delayed review, score, and reset
- actionable follow-up prompts
- bounded readable recent Tutor activity
- partial Article/session failure recovery
- focused Frontend tests, isolated Product E2E, and local Article browser probes
- governance, implementation evidence, commits, push, and exact-SHA CI closure

## Out of Scope

- Backend or published API changes
- frozen M1/source pipeline changes
- Article record or storage changes
- RAG, Graph, or Reference derived-asset rebuilds or mutations
- dependency or lockfile changes
- private Zotero access
- source-site access
- real or paid Provider calls
- candidate, tag, Release, or attestation actions

## Planned Changes

- `frontend/src/components/TutorView.tsx`
- bounded Tutor components under `frontend/src/components/`
- pure Tutor presentation/workspace helpers under `frontend/src/lib/`
- focused tests under `frontend/tests/`
- Tutor regression coverage in `scripts/e2e/run_product_e2e.py`
- `alignment.md`, task/status/report/roadmap/README documentation

## Acceptance

1. Article context is selected by title in the primary flow; raw IDs are not
   required or displayed.
2. Article-origin Tutor navigation retains an exact safe return link.
3. Markdown, code, inline math, and block math render safely.
4. Quiz answers, explanations, and sources remain absent before submission;
   score and review appear only after submission.
5. Follow-up questions fill and focus the next prompt without auto-submit.
6. Recent activity is bounded, readable, reverse chronological, and ID-free.
7. Independent search/session failures do not destroy active output.
8. Desktop/mobile, keyboard, focus, reduced-motion, and error states pass.
9. Three to five real local Articles and three repeated Product E2E runs pass
   with fake providers, isolated mutable state, and zero external requests.
10. Full local quality, compatibility, security, artifact, and protected-path
    gates pass without Backend, dependency, lockfile, data, or API changes.
11. Implementation and docs-only closure commits each pass exact-SHA main CI;
    final `main` is clean and synchronized.

## Authorization

- local Article data read: CONSUMED / CLOSED
- local Backend/Frontend runtime and Computer Use: CONSUMED / CLOSED
- Frontend/tests/docs edits, local commits, push, and CI inspection: CONSUMED
  / CLOSED AFTER THE DOCS-ONLY CLOSURE COMMIT
- Backend/frozen M1/source records/derived assets: NOT GRANTED
- source network/private Zotero/real Provider: NOT GRANTED
- candidate/tag/Release/attestation: NOT GRANTED

## Stop Conditions

Stop if an unknown worktree change appears, an in-scope gate cannot be fixed
without widening scope, a protected path or artifact changes, external/private
access becomes necessary, or any release action becomes necessary.

## Closure Evidence

- local acceptance: PASS
- implementation commit:
  `b66f5b39ae66efa6c4a3c673058ded49f0b7147e`
- implementation exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33356672629`
- implementation CI jobs: Backend, Frontend, Product E2E, workflow,
  dependency, secret, and SBOM PASS
- normal-main Docker and release evidence jobs: correctly skipped
- implementation CI artifacts: 0
- docs-only closure commit: this commit; exact-SHA CI required before final
  reporting
