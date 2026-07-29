# P3-011 End-to-End Product Convergence

## Status

LOCAL PASS / EXACT-SHA CI PENDING

## Objective

Prove and converge the complete local product journey over the exact current
1,314-Article corpus through repeatable APIs, browser automation, persistence,
Docker, and CI evidence.

## Authoritative Alignment

`alignment.md`

## Entry State

- branch: `main`
- entry commit:
  `380f79804fbbde6795a7532f00a9be79b02b3bc0`
- Article count: 1,314
- P3-010 derived assets: PASS / CLOSED
- entry worktree: clean and synchronized
- candidate version: not assigned

## Authorized Actions

- existing local corpus and derived-asset reads: GRANTED
- local Backend/Frontend runtime and browser automation: GRANTED
- local code/docs/tests, commit, push, and CI inspection: GRANTED
- source network or browser acquisition: NOT GRANTED
- private Zotero writes: NOT GRANTED
- real/paid Provider calls: NOT GRANTED
- candidate, tag, Release, or attestation: NOT GRANTED

## Required User Journey

```text
start system
  -> open dashboard
  -> search Article
  -> open and read Article
  -> record reading history
  -> update bounded learning state
  -> use grounded Tutor
  -> inspect References
  -> inspect Knowledge Graph
  -> restart and verify required persistence
  -> repeat complete isolated E2E flow three times
```

## Boundaries

- Do not modify frozen M1 acquisition, parser, converter, storage, sync, PDF,
  or Zotero synchronization modules.
- Do not mutate existing Article source records.
- Do not change legacy, `/v1.1`, or `/v1.2` contracts.
- Do not fetch source pages, write private Zotero, call real Providers, or
  enable paid/default network behavior.
- Do not commit local stores, indexes, databases, credentials, secrets,
  browser profiles, screenshots, traces, videos, or generated runtime assets.
- Do not assign a candidate or create/move a tag or Release.

## Deliverables

- deterministic E2E acceptance matrix
- automated browser E2E coverage
- in-scope fixes and focused regression tests
- three-run stability and persistence evidence
- complete Backend, Frontend, Docker, compatibility, artifact, and secret
  evidence
- P3-011 implementation report and governance updates
- implementation and closure commits with successful exact main CI runs

## Acceptance

- all required user-journey stages have direct API and browser evidence
- desktop and mobile behavior pass
- grounded citations, errors, deep links, and persistence pass
- three consecutive isolated E2E runs pass without flaky failures or state
  leakage
- all full regression, Docker, secret, artifact, and frozen-path gates pass
- final branch is clean and synchronized

## Stop Rule

Stop without widening scope if corpus integrity, frozen contracts, external
side-effect boundaries, repeatability, persistence, secret/artifact policy, or
prohibited release/provider/private-data boundaries cannot be preserved.
