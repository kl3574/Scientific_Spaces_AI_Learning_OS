# Current Task

## Task

`docs/tasks/P3-018_UNIFIED_APPLICATION_SHELL_AND_NAVIGATION.md`

## Status

P3-018 LOCAL REPAIR PASS / REPAIR CI PENDING

## Entry Baseline

- branch: `main`
- HEAD / cached `origin/main`:
  `abadf6d03aa5f7632085bb2393dfbad35c1ea6ff`
- ahead / behind: `0 / 0`
- worktree and index: clean
- REWORK / `.audit`: absent
- predecessor: P3-017 PASS / CLOSED

## Authorization

- P3-018 local Article data reads, local Backend/Frontend runtime, and isolated
  browser validation: GRANTED
- P3-018 Frontend/docs/tests changes, local commits, push, and CI inspection:
  GRANTED
- Backend, frozen M1, source records, derived assets, dependencies, lockfiles,
  workflows, and published API contracts: NOT GRANTED
- source network, private Zotero, and real/paid Provider: NOT GRANTED
- candidate, tag, Release, and attestation: NOT GRANTED

## Required Closure

- complete local functional, browser, security, artifact, and boundary gates
- implementation commit and exact-SHA main CI
- docs-only closure commit and exact-SHA main CI
- clean synchronized final `main`

## Local Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 59 passed
- production build: PASS
- Product E2E: 10 of 10 stress runs plus 3 of 3 formal runs, 32 checks per run
- real local Article shell probe: 5 of 5 PASS at 1440 x 900 and 390 x 844
- external requests, unexpected console errors, and page errors: 0
- workflow, suppression, dependency, staged secret audit, security utility,
  and temporary SBOM gates: PASS
- initial implementation commit:
  `86ff3cf971acc73feb298918e89f4468e6814e3b`
- initial CI run `33370930585`: Product E2E BLOCKED; all other required jobs
  PASS
- local repair: PASS; repair commit and exact-SHA repair CI: pending
