# P3-033 Structured Reference Review Round Trip Report

## 1. Status

- Local implementation: **PASS**
- Independent final review: **PASS**, 2/2 reviewers, 0 Critical / 0 Important
- Exact-SHA implementation main CI: **PENDING**
- Task closure: **IN PROGRESS**
- Candidate version: not assigned

This report records the local implementation gate. P3-033 remains open until
the implementation commit and a later docs-only closure commit each pass
exact-SHA main CI.

## 2. Implemented Workflow

- Every Article structured-reference row now exposes an internal review action
  carrying its exact `reference_id` and a bounded local return target.
- `/zotero` provides a searchable and filterable structured-reference result
  list beside an explicit selected-record evidence workspace.
- Selecting a result loads its exact detail and bounded Zotero candidates;
  changing selection immediately removes the previous record's presentation.
- A verified return opens the originating Article reference page and focuses
  the exact asynchronous row. References observed in more than one Article are
  validated against the requested Article rather than forced to a primary one.

## 3. Canonical Route And Ownership

The canonical URL represents query, reference type, classification, page,
selected reference, candidate filter, and an optional sanitized Article
return. Invalid, redundant, overlong, external, credentialed, or mismatched
values are removed by a server canonical redirect.

List, detail, candidate, and Article-return verification each use an
independent generation and exact request key. A result renders only while it
owns the current operation and, for detail/candidates, carries the selected
reference identity. A selected deep link remains available even when it is
outside the visible result page. An unavailable high page canonicalizes once
to the last available page without showing a false empty state.

## 4. Evidence And Candidate Truth

- The selected workspace shows identity, type, classification, source Article,
  section, observed-source count, and a concise evidence preview.
- The provenance disclosure renders every occurrence returned by the frozen
  `provenance_limit=20` contract, keeps the complete count visible, and states
  when the API result is truncated.
- Candidate filtering is local to the currently owned bounded response and
  emits no additional reference request.
- Loading, result-empty, detail failure, candidate-empty, filtered-empty,
  identity mismatch, retry, and outside-page states remain distinct.

## 5. Accessibility And Responsive Evidence

Search and filters have persistent labels; generic search controls have
workspace-specific accessible names. Accepted search, pagination, selection,
candidate-filter, return, and retry actions place visible focus on their owned
result target, including pending and repeated-failure states.

The Product E2E covers selected detail, visible long candidate metadata, and
candidate-filter focus at `1440x900`, `390x844`, `320x844`, and `720x450`.
Long identifiers, evidence, provenance, and candidate fields wrap without
page-level horizontal overflow.

## 6. Reader Regression Repair

An independent review caught a temporary weakening of the existing Reader
late-section regression. Diagnosis showed that the new Article reference
panel depended on the `useSearchParams()` object itself. A hash-only outline
navigation could therefore clear the panel and briefly change page geometry.

The panel now synchronizes only on the stable parsed `reference_page` value.
The original `1440x1000` Reader viewport, duplicate `数值检查` target, exact
active-section assertion, and exact persisted section remain intact and pass.
No Reader component or Reader contract changed.

## 7. Local Test Evidence

| Gate | Result |
| --- | --- |
| References and Related Papers tests | PASS, 21/21 |
| Articles/Reader tests | PASS, 59/59 |
| Tutor tests | PASS, 22/22 |
| Graph tests | PASS, 29/29 |
| Focused Frontend total | PASS, 131/131 |
| Frontend production build | PASS, 11 routes |
| Backend regression | PASS, 600 passed / 4 skipped |
| Product E2E | PASS, 3/3 complete runs; every emitted check true |
| Chromium | 149.0.7827.55 |
| Restart persistence | PASS |
| External browser requests | 0 |
| Unexpected console errors | 0 |
| Page errors | 0 |

The E2E evidence includes exact Article round trips, multi-Article provenance,
page-two return, list/detail/candidate races, response identity mismatch,
repeated failures and retries, URL canonicalization, Next/Previous pagination,
reload, Back/Forward, an out-of-range page, a selected record outside the
current page, zero candidates, candidate-filter history, and all four required
viewports.

## 8. Review Evidence

Initial independent reviews identified incomplete multi-Article return
ownership, a false out-of-range empty state, lost unsubmitted search drafts,
pending retry-focus gaps, generic search names, incomplete pagination/history
coverage, hidden candidate metadata during narrow overflow measurement, and a
weakened Reader regression. Each finding was repaired within the P3-033
allowlist.

Two independent final reviewers then inspected the complete worktree. Both
reported no Critical or Important finding; one explicitly verified the
original Reader viewport and late duplicate-heading coverage.

## 9. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action pin and explicit permission rates: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS
- changed paths: P3-033 allowlist only
- tracked forbidden runtime/private artifacts: 0
- source network, private Zotero, external search, and real/paid Provider access: 0

The local dependency audit is deferred to exact-SHA CI because it requires
registry network access, which P3-033 does not authorize locally.

## 10. Boundaries And Known Limits

P3-033 changes no Backend, published API, persistence, reference data,
extractor, matcher, frozen source processing, dependency, lockfile, workflow,
private Zotero state, version, candidate, tag, Release, or attestation.

The Frontend consumes the frozen 20-occurrence provenance and 20-candidate
bounds; it does not claim unbounded review or full-library candidate search.
Request ownership is scoped to one Frontend instance and does not establish
Backend exactly-once or multi-tab serialization. Browser behavior is verified
with the repository's current Chromium and Next.js runtime.

## 11. Next Gate

Create and non-force push the implementation commit, require exact-SHA main CI
to pass, then create the docs-only closure commit and require its own exact-SHA
main CI. No subsequent task or v1.2 candidate is staged here.
