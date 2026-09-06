# P3-036 Workspace Mutation Focus Continuity Report

## 1. Status

- Local implementation: **PASS**
- Independent final review: **PASS**, 2/2 reviewers, 0 Critical / 0 Important /
  0 Minor
- Exact-SHA implementation main CI: **BLOCKED ON INITIAL COMMIT; REPAIR CI PENDING**
- Task closure: **PENDING**
- Candidate version: not assigned

All required local behavior, regression, browser, review, and offline repository
safety gates pass. The implementation must still pass exact-SHA main CI before
P3-036 can be closed.

## 2. Entry Evidence

Two independent reviewers audited exact entry HEAD
`7997cceca268bae1e43806efb5460674a699dc92` with Chromium
`149.0.7827.55`, an isolated three-Article fixture, fake providers, temporary
runtime storage, and loopback-only networking. A separate controlled probe
reproduced the core failures and observed zero blocked external requests.

The probe found `document.activeElement === document.body` after Article List
selection clearing; Reader bookmark, learning-state, note, and session
mutations; Saved Learning capture; Concept capture; and Focused Session queue
mutations. The independent reviews additionally reproduced Graph search and
paging, Saved Learning filter clearing, Tutor Article/context mutations, Tutor
activity retry, and boundary queue movement. These were rendered
focus-ownership defects rather than data or API failures.

## 3. Root Cause

Affected controls became disabled, unmounted, or switched rendering mode as
their state committed. Although visible feedback often updated correctly, no
stable element inherited focus and the browser fell back to `BODY`. Several
async paths also lacked operation-specific ownership, so a delayed result could
either lose focus or override a newer user action.

## 4. Implemented Repair

- Article List selection clearing returns focus to its persistent capture
  region; search clearing returns to the search input; retry completion owns the
  stable list status only while its operation remains current.
- Reader bookmark, learning-state, note create/update/edit/cancel/delete,
  completion, timer, session ending, and guided-advance outcomes use exact
  Article, note, generation, and interaction ownership before moving focus.
- Saved Learning filtering and Session capture restore focus to the filter or
  exact initiating Article result without stealing a later focus move.
- Focused Session clear confirmation, cancellation, current-item changes,
  boundary moves, removal, and empty-queue recovery use stable local targets.
- Graph search, clearing, paging, Reader round trips, and Knowledge Context
  loading preserve destination and request ownership, including initial-frame
  and terminal async transitions.
- Concept capture and Tutor Article/activity mutations use persistent result
  regions or exact search results with request and interaction-version guards.
- All programmatic targets expose a visible focus indicator.

No request count, payload, route, history, storage write, data record, API, or
business outcome changed. No Backend, dependency, lockfile, workflow, source,
private Zotero, or release surface changed.

## 5. Race And Regression Evidence

Permanent browser assertions cover delayed note deletion, completion, timer,
guided advance success/error, Graph article return, Graph Knowledge Context
initial/terminal frames, Tutor search/retry, overlapping Tutor searches whose
older response settles last, and retry successors across Article List, Saved
Learning, and Focused Session.

The suite also preserves the already-correct note-delete confirmation,
completion reconciliation, queue-confirmation entry, non-boundary movement,
Graph keyboard selection, and Reader hash-focus contracts. During development,
new RED assertions exposed stale focus assumptions and an initial-frame Graph
race; each was repaired and rerun to GREEN before the formal evidence below.

## 6. Local Test Evidence

| Gate | Result |
| --- | --- |
| Articles/Reader tests | PASS, 67/67 |
| References tests | PASS, 21/21 |
| Tutor tests | PASS, 22/22 |
| Graph tests | PASS, 29/29 |
| Focused Frontend total | PASS, 139/139 |
| Frontend production build | PASS, 11 routes |
| Backend regression | PASS, 600 passed / 4 skipped |
| Product E2E | PASS, 3/3 complete runs; 225/225 checks per run |
| Chromium | 149.0.7827.55 |
| Restart persistence | PASS |
| External browser requests | 0 |
| Unexpected console errors | 0 |
| Page errors | 0 |

The formal Product E2E ran at `1440x900`, `390x844`, `320x844`, and
`720x450`. Every constrained document width matched its viewport, focused
targets remained available, and no page-level horizontal overflow was found.

## 7. Independent Review Evidence

Two independent final reviewers inspected the complete allowlisted diff after
the final race repairs. A follow-up reviewer found two fail-closed URL ownership
edge cases during the CI-test repair; both were fixed and both reviewers then
reported 0 Critical, 0 Important, and 0 Minor findings. No reviewer edited
repository files.

## 8. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- changed and untracked paths: P3-036 allowlist only
- tracked forbidden runtime/private artifacts introduced: 0
- source access, external search, private Zotero, and real/paid Provider calls: 0

The local dependency audit was not invoked because it requires registry network
access, which P3-036 does not authorize. The existing exact-SHA CI dependency
job remains the required evidence for that gate. Temporary browser and SBOM
evidence stayed outside the repository and is removed before commit.

## 9. Initial Exact-SHA CI And Bounded Repair

Implementation commit `d864cc1755b050a1dfeb247beaaa8a9d20a2eab3`
triggered exact-SHA main CI run
[`34019342064`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34019342064).
Backend, Frontend, dependency, workflow/suppression, secret, and SBOM jobs
passed; normal-main Docker and release evidence skipped as designed; uploaded
artifacts were zero.

The Product E2E job exposed two independent test-evidence races:

- attempt 1 completed the product flow but treated a repeated intentional
  Article 404 as unexpected because the harness used a global count allowance;
- unchanged-SHA attempt 2 reached the existing ordinary Shell test before a
  Dashboard layout had reached its observable terminal state, so its immediate
  scroll snapshot differed after same-route brand activation.

The bounded repair keeps every product assertion strict. Intentional 404s are
now consumed only when the shared and page-scoped console sequences match and
every console location and response URL has the exact HTTP loopback host, port,
path, and empty credentials/params/query/fragment. The global 404 allowance is
removed. The Shell test waits for Dashboard `aria-busy=false` and animation
frames before establishing scroll, while preserving exact history, URL, focus,
and scroll assertions.

Repair evidence:

- endpoint predicate: 2 valid forms accepted; 9 malformed or unrelated forms
  rejected; unowned shared errors rejected
- intentional 404 browser probe: 10/10 PASS
- ordinary Shell route-focus stress: 20/20 PASS
- final Product E2E: 3/3 runs, 225/225 checks each, restart persistence PASS,
  and zero external requests, console errors, or page errors
- final independent reviews: 2/2 PASS, 0 Critical / 0 Important / 0 Minor

## 10. Final Disposition Before Repair CI

Local result: **PASS**. P3-036 remains open until the cumulative repair commit
passes exact-SHA main CI. A separate docs-only closure commit and its own
exact-SHA CI are then required. No v1.2 candidate, tag, or Release is assigned.
