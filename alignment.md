# P3-011 End-to-End Product Convergence Alignment

Canonical task:
`docs/tasks/P3-011_END_TO_END_PRODUCT_CONVERGENCE.md`

Status: **PASS / CLOSED**

LOCAL DATA READ / APPLICATION RUNTIME AUTHORIZATION: **CONSUMED / CLOSED**

LOCAL FILE MODIFICATION / TEST / COMMIT / PUSH / CI AUTHORIZATION:
**CONSUMED / CLOSED AFTER THE DOCS-ONLY CLOSURE COMMIT**

SOURCE NETWORK / PRIVATE ZOTERO WRITE / REAL PROVIDER AUTHORIZATION:
**NOT GRANTED**

CANDIDATE / TAG / RELEASE AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-010 is PASS / CLOSED at the exact 1,314-Article corpus fingerprint.
- RAG, Graph, and structured Reference assets match the current Article Store.
- The product now needs a real local runtime and browser acceptance cycle that
  proves complete user workflows rather than relying only on component tests.
- M1 frozen modules, existing Article records, and published legacy, `/v1.1`,
  and `/v1.2` API contracts remain protected.
- The entry commit is
  `380f79804fbbde6795a7532f00a9be79b02b3bc0`; entry `main` and
  `origin/main` are synchronized and the worktree is clean.

## 2. Requirements

1. Start the Backend, Frontend, and required local runtime dependencies.
2. Use the existing exact 1,314-Article local corpus and matching derived
   assets.
3. Exercise Reader, Search, Reading History, Learning, Tutor, References, and
   Knowledge Graph through real APIs and browser UI.
4. Add repeatable browser automation instead of relying only on unit tests.
5. Diagnose and fix in-scope defects, then add focused regression coverage.
6. Repeat the complete E2E flow at least three times without flaky failures,
   duplicate writes, or state leakage.
7. Verify desktop and mobile rendering, Markdown, Chinese text, formulas,
   citations, deep links, empty/error states, and restart persistence.
8. Run full Backend, Frontend, Docker, compatibility, secret, artifact, and
   changed-path gates.
9. Create an implementation commit and a docs-only closure commit, push both,
   and verify each exact-SHA main CI run.
10. Do not access the source site, write private Zotero, call a real/paid
    Provider, or assign/create a candidate, tag, or Release.

## 3. Purpose

Converge the current product into a repeatably runnable local system with
evidence that its core user journey works from browser interaction through
Backend persistence and derived knowledge services.

## 4. Planned Execution

1. Persist this alignment and canonical task.
2. Revalidate Git, Article Store identity, derived manifests, runtime
   dependencies, and current test inventory.
3. Build a requirement-to-evidence E2E acceptance matrix.
4. Start Backend and Frontend locally and run API smoke checks.
5. Exercise desktop and mobile browser journeys with Playwright.
6. Verify Reader/Search, History, Learning, Tutor, Reference, and Graph
   behavior, including negative and persistence cases.
7. Classify failures by product defect, test defect, environment limitation,
   or external boundary.
8. Fix only in-scope product/test defects and add regression coverage.
9. Repeat the complete E2E suite three times and verify clean isolation.
10. Run full Backend, Frontend, Docker, API compatibility, secret, artifact,
    and changed-path gates.
11. Update governance and the P3-011 evidence report.
12. Commit and push implementation, verify exact main CI, create and push a
    docs-only closure commit, verify its exact main CI, and finish clean and
    synchronized.

## 5. Selection Rationale

A deterministic local E2E baseline separates application defects from source,
private-library, and paid-provider variability. It provides repeatable browser
evidence while preserving the existing external-side-effect boundaries.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Existing corpus, fake Provider, real local APIs/UI, automated browser E2E | Selected: complete deterministic product validation |
| Include source crawling, private Zotero writes, and real Provider calls | Rejected for this task: separate authorization and side effects required |
| Run only existing unit/build checks | Rejected: cannot prove user workflows |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/P3-011_END_TO_END_PRODUCT_CONVERGENCE.md`
- updated `docs/tasks/CURRENT_TASK.md`
- an explicit E2E acceptance matrix
- repeatable browser E2E tests and runtime configuration
- in-scope Backend/Frontend fixes and regression tests, if required
- `docs/P3_011_END_TO_END_PRODUCT_CONVERGENCE_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation commit and exact main CI evidence
- docs-only closure commit and exact main CI evidence

## 8. Acceptance Criteria

- Backend full tests pass.
- Frontend tests and production build pass.
- Docker compose smoke passes.
- Desktop and mobile core browser journeys pass.
- Reader/Search, Article detail, Reading History, Learning, Tutor, References,
  and Graph have direct runtime evidence.
- Tutor evidence contains valid source citations and does not substitute an
  ungrounded answer.
- The complete E2E suite passes three consecutive isolated runs.
- Required state survives application restart; test-only state does not leak
  across runs.
- Empty, not-found, and Backend-unavailable states are controlled.
- Secret and artifact audits report no credible secret or tracked
  runtime/private artifact.
- Frozen M1 paths, Article source records, and published API contracts remain
  unchanged.
- Source access, private Zotero writes, real Providers, candidate, tag, and
  Release remain untouched.
- Implementation and closure commits are pushed; both exact main CI runs pass;
  final `main` is clean and synchronized.

## Closure Evidence

- implementation commit:
  `579c90252bc6fa594905491646ec07e296340043`
- implementation main CI:
  [`30456388891`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30456388891),
  `success`
- exact-implementation `workflow_dispatch` CI:
  [`30456541072`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30456541072),
  `success`
- Backend, Frontend, Product E2E, workflow policy, dependency, secret, and
  SBOM jobs: PASS
- Docker compose smoke and no-publish release-evidence dry-run: PASS
- uploaded workflow artifacts: 0 for both implementation runs
- candidate, tag, Release, attestation, source access, private Zotero, and real
  Provider actions: 0

The docs-only closure commit must pass its own exact main CI before the final
execution response claims synchronized completion. No subsequent task is
authorized by this closed alignment.

## Stop Conditions

- The current corpus or derived assets are missing or inconsistent.
- The worktree develops unknown changes or conflicts.
- Completion requires a frozen M1 or published API contract change.
- Completion requires source access, a private Zotero write, or a real/paid
  Provider call.
- A critical test, runtime, Docker, secret, or artifact gate fails without an
  in-scope deterministic fix.
- A candidate, tag, Release, or attestation action becomes necessary.
