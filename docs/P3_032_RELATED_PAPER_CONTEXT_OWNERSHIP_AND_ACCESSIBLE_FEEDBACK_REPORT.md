# P3-032 Related-Paper Context Ownership and Accessible Feedback Report

## 1. Status

- Local implementation: **PASS**
- Independent final review: **PASS**, 2/2 reviewers, 0 Critical / 0 Important
- Exact-SHA implementation main CI: **PASS**
- Task closure: **PASS / CLOSED**; docs-only closure exact-SHA CI pending
- Candidate version: not assigned

Implementation commit `e7b317042df728e568bb5f4d328c678ac3102f0a`
passed exact-SHA main CI run
[`33965187190`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33965187190).
This docs-only closure commit requires its own exact-SHA main CI before final
reporting.

## 2. Implemented Contract

- Every Related Papers read, search, mutation, reconciliation, and export is
  bound to the current Article generation and operation identity.
- Query identity is normalized consistently with the transport. Repeated
  submission of the same pending query is inert, while a newer query
  supersedes older results.
- Provider availability and the persisted project-link list load independently.
  Provider failure never hides a successfully loaded local link list.
- Link and Unlink share one synchronous mutation lane. Competing launchers and
  export remain locked while an intent or mutation is active.
- A successful mutation updates the current list functionally and invalidates
  stale BibTeX without an automatic list reload.
- A rejected or response-lost mutation performs exactly one read-only
  reconciliation, never replays the write, and locks further writes when
  persistence remains unconfirmed.

## 3. Article Ownership And Request Evidence

The Product E2E request ledger records method, path, query, and request body.
It verifies:

- delayed Article A list, search, export, mutation, and reconciliation
  completions cannot change Article B data, controls, feedback, focus, BibTeX,
  or request targets;
- a rapid Link activation emits one exact POST, including Article ID, item key,
  relation type, and note;
- an already-linked result emits zero POST requests;
- only item keys in the current linked-paper set are exported;
- a pending export emits one request and is invalidated by Article or link-set
  changes; and
- response loss and explicit rejection each emit one mutation plus one
  read-only link-list reconciliation with no replay.

The exact-count guarantee is intentionally scoped to one mounted panel. It
does not claim backend exactly-once semantics or multi-tab serialization.

## 4. Unlink Safety And Reconciliation

- First Unlink activation creates an immutable Article/item intent and sends
  zero DELETE requests.
- The inline confirmation explains that the project relation and note are
  removed permanently while the Zotero library item is retained.
- Cancel, `Escape`, and Article navigation before confirmation send zero DELETE
  requests and leave the rendered relation intact.
- Keyboard confirmation sends exactly one DELETE; repeated activation cannot
  send another request.
- Successful readback establishes the persisted result without guessing.
  Failed readback preserves the current rendering, reports uncertainty, locks
  mutations, and exposes a manual read-only reload.

## 5. Accessibility And Focus Evidence

- Search, relationship, and note inputs have persistent labels.
- Link, Unlink, Cancel, retry, and export controls have target-specific names.
- Confirmation controls reference the exact consequence text through
  accessible descriptions.
- The linked-paper region exposes truthful busy state; independent atomic live
  regions announce list and mutation feedback without conflating them.
- Search result count, no-match, error, pending, success, and uncertainty
  messages remain distinct.
- BibTeX is a named disclosure with explicit pending, ready, empty, and error
  states and a keyboard-focusable local scroll region.
- Ordered focus traces cover confirmation open, Cancel, `Escape`, success,
  rejection, response loss, retries, and Article navigation. No trace falls to
  `body`, targets a disconnected element, or crosses Article generations.
- Ordinary Article-to-Article navigation synchronously hands focus from the
  persistent `main` region to the destination Article heading.

## 6. Responsive Evidence

The E2E suite validates populated, pending, error, confirmation, uncertainty,
and long BibTeX states at `1440x900`, `390x844`, `320x844`, and `720x450`.
Long unbroken titles, queries, notes, feedback, and BibTeX stay inside the page;
BibTeX overflow remains local and keyboard-scrollable. No page-level horizontal
overflow or clipped action control was observed.

## 7. Local Test Evidence

| Gate | Result |
| --- | --- |
| Articles/Reader tests | PASS, 59/59 |
| References and Related Papers tests | PASS, 10/10 |
| Tutor tests | PASS, 22/22 |
| Graph tests | PASS, 29/29 |
| Focused Frontend total | PASS, 120/120 |
| Frontend production build | PASS, 11 routes |
| Backend regression | PASS, 600 passed / 4 skipped |
| Product E2E | PASS, 3/3 complete runs; every emitted check true |
| Chromium | 149.0.7827.55 |
| Restart persistence | PASS |
| External browser requests | 0 |
| Unexpected console errors | 0 |
| Page errors | 0 |

The Product E2E uses isolated fake providers and temporary runtime stores. It
left no result JSON, screenshot, trace, profile, private Zotero data, or mutable
product data in the repository.

## 8. Review Evidence

The initial reviews identified false empty state after repeated list failures,
missing rejected-mutation coverage, incomplete exact-payload evidence, an
outdated roadmap pointer, missing ordinary Article-route focus handoff,
incomplete mutation live/busy semantics, generic confirmation naming, dynamic
text overflow risk, and incomplete visible BibTeX invalidation evidence.

All findings were repaired. Two independent reviewers then inspected the final
worktree and returned PASS with zero Critical or Important findings. One review
focused on Article/generation ownership and exact request behavior; the other
focused on keyboard, accessibility, focus continuity, and responsive behavior.

## 9. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action pin and explicit permission rates: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS
- `git diff --check`: PASS
- changed paths: P3-032 allowlist only
- tracked forbidden runtime/private artifacts: 0
- Backend, frozen M1, API, provider, persistence, dependencies, lockfiles,
  workflows, source/Article/Graph/reference data, derived assets, and release
  metadata changed: 0
- source network, private Zotero, external search, and real/paid Provider
  access: 0

The local dependency audit was not run because it requires registry network
access, which P3-032 prohibits locally. Exact-SHA implementation CI ran and
passed that gate.

## 10. Exact-SHA Implementation CI

| Gate | Result |
| --- | --- |
| Head SHA | `e7b317042df728e568bb5f4d328c678ac3102f0a` |
| Run | [`33965187190`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33965187190) |
| Frontend build | PASS |
| Backend pytest | PASS |
| Product E2E, three runs | PASS |
| Dependency audit | PASS |
| Workflow and suppression policy | PASS |
| Secret audit | PASS |
| SBOM validation | PASS |
| Docker compose smoke | SKIPPED as designed for normal `main` push |
| Release evidence dry-run | SKIPPED as designed for normal `main` push |
| Uploaded workflow artifacts | 0 |

The run completed with `conclusion=success`, `event=push`, `headBranch=main`,
and an exact `headSha` match. GitHub emitted non-blocking Node 20 deprecation
notices for pinned upstream Actions; changing workflows is outside P3-032.

## 11. Known Limits

- The Frontend controls one request per accepted intent but cannot guarantee
  backend exactly-once persistence or serialize another browser tab.
- An unresolved response-loss readback intentionally blocks another mutation
  until a manual reload establishes current persistence.
- Provider availability still depends on the existing backend integration; no
  provider or private Zotero behavior changed.
- Browser behavior is verified with Chromium and the repository's current
  React/Next.js runtime.
- Copy, download, relation editing, Zotero-item deletion, and a standalone
  Zotero Library workspace remain outside P3-032.

## 12. Boundary Result

P3-032 changes only the allowlisted Related Papers/Reader Frontend, pure helper
and tests, Product E2E, and governance documents. It does not modify Backend,
published APIs, persistence, frozen source processing, product data,
dependencies, workflows, private integrations, candidate metadata, tags,
Releases, or attestations.

## 13. Next Gate

Push this docs-only closure commit and require its exact-SHA main CI to pass.
No subsequent task or v1.2 candidate is staged by P3-032 closure.
