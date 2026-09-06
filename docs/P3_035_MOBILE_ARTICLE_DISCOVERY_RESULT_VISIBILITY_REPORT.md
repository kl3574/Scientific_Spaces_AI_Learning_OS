# P3-035 Mobile Article Discovery Result Visibility Report

## 1. Status

- Local implementation: **PASS**
- Independent final review: **PASS**, 2/2 reviewers, 0 Critical / 0 Important
- Exact-SHA implementation main CI: **PASS**
- Task closure: **PASS / CLOSED**
- Exact-SHA docs-only closure CI: **PENDING FOR THIS COMMIT**
- Candidate version: not assigned

All required local behavior, regression, browser, review, and repository safety
gates pass. Implementation commit
`6f5844c80b092a1919f20e5e93f75a9b6ae1e38a` passed exact-SHA main CI run
[`34010502972`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34010502972).
This docs-only commit records the completed task closure and requires its own
exact-SHA main CI readback before final reporting.

## 2. Entry Evidence

Controlled local Chromium used the isolated three-Article fixture runtime and
made zero non-loopback requests. Before implementation, the first rendered
Article had these top coordinates:

| Viewport | First Article top | Viewport result |
| --- | ---: | --- |
| `1440x900` | `419px` | visible |
| `390x844` | `712px` | title only near viewport end; preview below fold |
| `320x844` | `780px` | title only near viewport end; preview below fold |
| `720x450` | `491px` | fully below fold |

The zero-selection Focused Session region occupied `178px` at `390x844`,
`226px` at `320x844`, and `122px` at `720x450`. Top pagination consumed
additional result-before-content space even for a one-page fixture.

## 3. Root Cause

The Article List gives persistent pre-result space to secondary batch actions
that cannot yet run, and places page navigation before rather than after the
current page. At narrow widths, Search and Clear also occupy separate full rows.
All controls fit horizontally, but the vertical priority delays the first useful
result.

## 4. Implemented Repair

- Keep the search field and sort control full width on mobile while placing the
  two command buttons in one row.
- Keep Select page and Open Focused Session available at zero selection.
- Mount Clear selection and Add selected to session only when a current-page
  selection exists.
- Place pagination after the current result list and omit it for one-page data.
- Preserve existing keyboard, feedback, error, capacity, duplicate, query,
  paging, and history behavior.

No Backend, API, persistence, data, dependency, lockfile, workflow, or release
surface changed.

## 5. Responsive Evidence

The same isolated three-Article fixture runtime produced the following
post-change geometry at `scrollY=0`:

| Viewport | Before Article top | After Article top | After title top | After preview top | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| `1440x900` | `419px` | `359px` | `377px` | `465px` | PASS |
| `390x844` | `712px` | `552px` | `570px` | `698px` | PASS, title and preview visible |
| `320x844` | `780px` | `572px` | `590px` | `718px` | PASS, title and preview visible |
| `720x450` | `491px` | `387px` | `405px` | `517px` | PASS, title visible |

Document widths remained exactly `390px`, `320px`, and `720px` in the three
constrained viewports. No page-level horizontal overflow or overlapping control
was observed. The pre-change E2E assertion independently failed RED because the
narrow preview was outside the initial viewport at `y=926`; the final assertion
passes in all three complete runs.

## 6. Interaction Regression

- Search, Clear, all four sort modes, request-race handling, normalized query,
  page, browser Back, and browser Forward behavior remain covered.
- One-page result sets render no pager. The existing two-page fixture keeps
  working Previous/Next navigation after the current result list.
- Select page and Open Focused Session remain available with zero selection.
- Clear and Add appear after individual or page selection and retain the
  existing success, duplicate, capacity, storage-failure, selection-retention,
  and live-feedback behavior.
- Existing keyboard ordering and focus feedback pass. The pre-existing Clear
  selection focus return to `BODY` is unchanged from the `c248eb4` baseline and
  is recorded below as a separate follow-up candidate, not a regression in this
  task.

## 7. Local Test Evidence

| Gate | Result |
| --- | --- |
| Articles/Reader tests | PASS, 67/67 |
| References tests | PASS, 21/21 |
| Tutor tests | PASS, 22/22 |
| Graph tests | PASS, 29/29 |
| Focused Frontend total | PASS, 139/139 |
| Frontend production build | PASS, 11 routes |
| Backend regression | PASS, 600 passed / 4 skipped |
| Product E2E | PASS, 3/3 complete runs; 221 checks per run |
| Chromium | 149.0.7827.55 |
| Restart persistence | PASS |
| External browser requests | 0 |
| Unexpected console errors | 0 |
| Page errors | 0 |

The Product E2E directly asserts `scrollY === 0`, title intersection at all four
required viewports, portrait preview intersection, single-page pager omission,
multi-page result-following navigation, and the complete Session capture path.

## 8. Independent Review Evidence

Two independent final reviewers inspected the complete allowlisted diff and
ran separate browser checks. Both reported 0 Critical and 0 Important findings
and returned `FINAL REVIEW PASS`. Both independently reproduced the final
`390x844`, `320x844`, and `720x450` geometry and confirmed no horizontal
overflow, lost search/paging action, or Session capture regression.

## 9. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- security utility tests: PASS, 17/17
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- dependency audit: PASS, 40 PyPI / 239 npm packages, 0 findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- changed and untracked paths: P3-035 allowlist only
- tracked forbidden runtime/private artifacts introduced: 0
- source access, external search, private Zotero, and real/paid Provider calls: 0

Temporary browser evidence and SBOM output remain outside the repository and
are not part of the candidate commit.

## 10. Deferred Review Findings

The entry reviewers separately identified stale Article IDs, mutation focus
return, ordinary-navigation session completion, Reader duplicate H1 semantics,
and Graph/Reference extraction-noise presentation. None is caused by this
candidate and each crosses a different behavior or ownership boundary. They are
retained as evidence for later bounded tasks rather than widening P3-035.

## 11. Exact-SHA Implementation CI

- implementation commit:
  `6f5844c80b092a1919f20e5e93f75a9b6ae1e38a`
- exact-SHA main CI:
  [`34010502972`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34010502972)
- event / branch / head SHA: `push` / `main` /
  `6f5844c80b092a1919f20e5e93f75a9b6ae1e38a`
- Backend pytest: PASS
- Frontend build: PASS
- Product E2E: PASS
- dependency, workflow, suppression, secret, and SBOM jobs: PASS
- normal-main Docker and release evidence: skipped as designed
- uploaded artifacts: 0
- non-blocking platform notice: GitHub reported the future Node.js 20 Action
  runtime deprecation; workflow changes are outside P3-035 scope

## 12. Next Gate

Create and non-force push this authorized docs-only closure commit and require
its exact-SHA main CI to pass. No subsequent task or v1.2 candidate is staged;
later work continues through a separate bounded task.
