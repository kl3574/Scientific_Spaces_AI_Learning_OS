# P3-034 Ordinary Route and Reader Hash Focus Continuity Report

## 1. Status

- Local implementation: **PASS**
- Independent final review: **PASS**, 2/2 reviewers, 0 Critical / 0 Important
- Exact-SHA implementation main CI: **PENDING**
- Task closure: **OPEN / CI PENDING**
- Candidate version: not assigned

All required local behavior, regression, browser, review, and repository safety
gates pass. The implementation commit and exact-SHA main CI remain before the
docs-only closure commit.

## 2. Implemented Focus Contract

- Shell route identity is pathname plus normalized query; hash-only navigation
  remains owned by the destination view.
- Initial hydration does not move focus.
- An ordinary committed local route preserves a connected meaningful focus
  target inside `main`; otherwise the Shell focuses `main#main-content`
  without scrolling.
- Desktop rail and brand navigation use the accepted Next.js navigation
  lifecycle. Same-route activation changes neither URL, history, nor scroll and
  focuses current main content.
- Browser Back and Forward use the same destination-owner/main-fallback rule.
- Focus-operation generations invalidate stale route, history, modal, and
  deferred callbacks.
- Destination-owned intent is one-shot, source-and-target exact, bounded, and
  invalidated by a newer focus operation.

## 3. Reader Hash Ownership

- `#article-start`, `#article-outline`, and `#reading-tools` are explicit,
  focusable, visibly styled destinations.
- Managed outline entries preserve the existing history state and focus their
  exact Unicode heading.
- Structured-reference targets retain deferred ownership across bounded loading
  and retry, while stale request generations cannot claim focus.
- Guided Session entry and cross-route history replay focus the visible Article
  H1. Same-mounted hash-only history to an unmanaged heading focuses the exact
  visible heading instead.
- Reader position restoration does not scroll a currently focused guided H1 out
  of view.
- Graph return ownership is declared only for an exact `node_id`; query-only
  Graph routes correctly fall back to Shell main focus.

## 4. Regression And Race Coverage

The Product E2E covers desktop rail and brand navigation, ordinary content
links, same-route activation, Back/Forward, normalized query changes, delayed
route commits, overlapping navigation, superseding operations, modal
ownership, source removal, Search, Drawer, Reader, Graph, Tutor, and Reference
destination owners.

Reader-specific coverage includes cold hydration, fixed hash targets, encoded
Chinese headings, managed and unmanaged heading history, guided Session entry
and Forward replay, structured-reference delayed success/failure/retry, user
cancellation, and stale response generations. Focus traces distinguish actual
focus or disconnected-node transitions from passive route-event snapshots.

## 5. Local Test Evidence

| Gate | Result |
| --- | --- |
| Articles/Reader tests | PASS, 67/67 |
| References tests | PASS, 21/21 |
| Tutor tests | PASS, 22/22 |
| Graph tests | PASS, 29/29 |
| Focused Frontend total | PASS, 139/139 |
| Frontend production build | PASS, 11 routes |
| Backend regression | PASS, 600 passed / 4 skipped |
| Product E2E | PASS, 3/3 complete runs; 217 checks per run |
| Chromium | 149.0.7827.55 |
| Restart persistence | PASS |
| External browser requests | 0 |
| Unexpected console errors | 0 |
| Page errors | 0 |

The E2E exercised `1440x900`, `390x844`, `320x844`, and `720x450` behavior
without page-level overflow or focus loss.

## 6. Independent Review Evidence

Two independent final reviewers inspected the complete allowlisted diff after
all repairs. Both reported 0 Critical and 0 Important findings and returned
`FINAL REVIEW PASS`.

Earlier findings led to bounded repairs for source-bound destination intents,
Graph query-only fallback, structured-reference request ownership, guided
Reader history provenance, same-mounted unmanaged heading history, and the
guided H1/reading-position race. Each repaired case is covered by the final
passing E2E.

## 7. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action pin and explicit permission rates: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- security utility tests: PASS, 17/17
- dependency audit: PASS, 40 PyPI / 239 npm packages, 0 findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS
- changed paths: P3-034 allowlist only
- tracked forbidden runtime/private artifacts introduced: 0
- source access, external search, private Zotero, and real/paid Provider calls: 0

Ignored local build, test, virtual-environment, and runtime directories remain
untracked and are not part of the implementation commit.

## 8. Boundaries

P3-034 changes only the bounded Shell/Reader/structured-reference Frontend
ownership logic, pure navigation tests, Product E2E, and governance documents.
It changes no Backend, API, persistence, source record, Article record, corpus,
Graph/Reference data, dependency, lockfile, workflow, version, candidate, tag,
Release, or attestation.

The repository contains no actual `AGENTS.md` in or above this checkout and no
tracked `AGENTS.md`; therefore no generated AGENTS content was changed or
committed. Chat-only instructions attributed to another agent were not treated
as repository policy.

## 9. Exact-SHA Implementation CI

- implementation commit: this commit
- non-force push to `main`: pending
- exact-SHA main CI: pending
- required jobs: Backend, Frontend, three-run Product E2E, dependency,
  workflow/suppression, secret, and SBOM
- normal-main Docker and release evidence: expected to skip by workflow policy
- uploaded artifacts required: 0

## 10. Next Gate

Create and non-force push the implementation commit, require exact-SHA main CI
to pass, then record that evidence in the authorized docs-only closure commit.
No subsequent task or v1.2 candidate is staged here.
