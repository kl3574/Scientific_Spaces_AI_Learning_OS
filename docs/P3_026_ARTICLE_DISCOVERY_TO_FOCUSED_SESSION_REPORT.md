# P3-026 Article Discovery to Focused Session Report

Status: **LOCAL PASS / CI PENDING**

## 1. Scope And Boundaries

P3-026 turns `/articles` into a truthful discovery workspace and adds an
explicit path from current results into the existing browser-local Focused
Session. The implementation is limited to the Article list, a pure planning
helper, focused tests, Product E2E, and task documentation.

Backend code, published APIs, frozen M1 modules, Article and source records,
the Focused Session schema and limit, dependencies, lockfiles, workflows, and
release metadata remain unchanged. No source access, external search, private
Zotero action, real Provider call, candidate, tag, Release, or attestation was
performed.

## 2. Article Result Ownership

- Every Article result request owns a monotonically increasing generation.
- Query, sort, page, and explicit retry each start a new generation.
- Only the latest generation may publish rows, pagination, errors, or status.
- A pending or failed generation exposes no actionable rows.
- Selection is page-scoped and clears when a new result generation starts.

Product E2E covers stale failure, stale success, A-B-A query ordering, sorting,
pagination, retry, pending-row suppression, failed-row suppression, and
selection reset.

## 3. Truthful Independent Badges

Learning State and Bookmark data use independent request generations and
independent retry actions. A successful Learning State response that omits an
Article means `unread`. A failed response displays `Status unavailable` and
does not erase a successful Bookmark result. The reverse partial-failure case
also preserves the successful Learning State result.

Badge reads remain informational. They do not determine Session eligibility
and capture performs no Learning State or Bookmark mutation.

## 4. Focused Session Capture

The Article list provides native labelled checkboxes, page selection controls,
one `Add selected to session` command, and an explicit `/session` link. Capture
reloads browser storage immediately before planning, appends accepted Articles
in current visible order through the existing bounded queue helper, and makes
at most one save attempt.

Existing queue order and active identity are preserved. An empty queue uses
the existing rule that activates its first accepted Article. Added, already
present, invalid, capacity-omitted, storage-unavailable, and failed-save
outcomes are counted explicitly. Failed persistence keeps the selection for a
retry. Successful persistence clears only records classified as added or
already present, including the edge case where an invalid visible candidate
shares an existing identifier.

Capture does not change the Article-list URL, navigate automatically, or write
server Learning or Bookmark state. Same-tab and cross-tab queue changes update
the count and `In session` labels.

## 5. Storage And Feedback Truth

- A storage read failure reports `Focused Session unavailable`, never `0/20`.
- Capture after a read failure performs no Session write and preserves the
  current selection.
- A storage write failure reports that no changes were saved and preserves the
  current selection.
- Duplicate-only and full-queue outcomes do not rewrite an unchanged queue.
- External queue changes clear obsolete capture feedback. If that feedback had
  focus, focus moves to the persistent capture region.
- Storage recovery remains visible until a successful persisted mutation
  replaces the recovered state.

## 6. Accessibility And Responsive Evidence

The capture controls use native buttons, links, and labelled checkboxes. One
persistent polite and atomic live region receives deterministic focus after an
explicit capture command and has a visible two-pixel outline. Feedback is
invalidated safely when its result is no longer current.

At 1440 x 900, 390 x 844, 320 x 844, and 720 x 450, Product E2E performs a
continuous keyboard sequence from the Article checkbox to the Session link and
capture action, activates the command with Enter, verifies focused live
feedback, checks viewport intersection, and checks document and control width.
The 320-pixel case renders and verifies the longest storage-write failure text.

## 7. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 39.87s
```

### Frontend

- Article, Reader, Dashboard, workflow, navigation, and capture planning:
  46 passed
- Focused Session and completion model: 13 passed
- structured References: 3 passed
- Tutor: 20 passed
- Graph and Concept Study Set: 27 passed
- global search: 5 passed
- Saved Learning Library: 5 passed
- focused total: 119 passed
- Next.js 15.5.21 production build: PASS, 11 routes
- Article list: 6.49 kB route / 116 kB first load
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py \
  --repeat 3 --frontend-mode start
```

- complete runs: 3
- successful runs: 3
- checks per run: 113
- restart persistence: PASS
- Chromium: 149.0.7827.55
- non-loopback requests: 0
- unexpected console errors: 0
- page errors: 0

## 8. Security, Artifact, And Protected Paths

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action full-SHA pin rate: 100 percent
- explicit workflow and job permission rate: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- dependency audit: PASS, 40 PyPI / 239 npm packages / 0 findings
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- temporary SBOM cleanup: PASS
- Backend, workflow, dependency, lockfile, published API, frozen M1, Article,
  source, and Focused Session contract changes: 0
- new runtime/private artifacts: 0

Three tracked HTML files reported by the broad artifact pattern are existing
Backend parser fixtures from the baseline, not P3-026 additions. The unrelated
agent-authored `AGENTS.md` remains absent.

## 9. Independent Review

Two independent final reviews returned PASS after their findings were repaired.
Repairs included truthful Session-unavailable presentation, stale feedback
invalidation, exact invalid-item selection retention, expanded stale-success /
sort / page / retry evidence, continuous keyboard coverage, explicit control
states, persistent badge retry progress, retry-start focus, and prevention of
late retry completion stealing focus after the learner moves elsewhere.

## 10. Known Risks

- The Focused Session remains browser-local and subject to browser-storage
  eviction; this task does not create cross-device or multi-user persistence.
- Search and badge data are separate existing reads. Partial availability is
  represented explicitly rather than hidden behind one combined state.
- Result generation guards prevent stale UI commits but do not cancel the
  underlying HTTP work; request cancellation is unnecessary for correctness
  and remains outside this bounded task.
- Capture is deliberately page-scoped. Cross-page selection and generated
  recommendations remain out of scope.

## 11. Current Decision

Local implementation, verification, and two independent final reviews are
PASS. The task remains open until the implementation commit is pushed and its
exact SHA passes main CI. A separate docs-only closure commit and exact-SHA CI
readback are then required. No v1.2 candidate is assigned.
