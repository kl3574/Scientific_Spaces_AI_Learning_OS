# P3-030 Shell Modal-Origin Route Focus Continuity Report

## 1. Status

- Local implementation: **PASS**
- Independent final review: **PASS**, 2/2 reviewers, 0 Critical / 0 Important
- Exact-SHA implementation main CI: **PASS**
- Task closure: **PASS / CLOSED**; docs-only closure exact-SHA CI pending
- Candidate version: not assigned

Implementation commit `eabccf1d20d62e12dc5bf4d85181a4c66fe68ad3`
passed exact-SHA main CI run
[`33948697098`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33948697098).
This docs-only closure commit requires its own exact-SHA main CI before final
reporting.

## 2. Implemented Contract

- Shell route identity is normalized pathname plus sorted query parameters;
  hash-only changes remain outside this task.
- Next.js `onNavigate` distinguishes accepted same-tab local navigation from
  modified or new-tab activation.
- Search and Drawer dismissal restore their opener, including connected
  focusable SVG elements.
- Accepted cross-route navigation closes the originating modal and transfers
  focus only after the target identity commits.
- Same-identity activation bypasses the Router, preserves URL, history, and
  scroll, and applies the current-main fallback.
- Destination-owned focus wins. Shell focuses persistent `main#main-content`
  only when focus remains on `body`, is disconnected, or still belongs to the
  Shell origin.
- Operation tokens and cancellable animation frames make stale dismissal and
  route callbacks inert across reopen, superseding navigation, and history
  cancellation.
- A completed or superseded transition that never commits its target recovers
  focus to the current route without relying on a fixed frame timeout.

## 3. Regression Evidence

Pure navigation tests cover canonical identity, safe local target resolution,
main fallback eligibility, route-commit ownership, and pending transition
lifecycle behavior.

Product E2E covers:

- initial hydration without a focus jump;
- Search Escape, Close, backdrop, hidden-opener, same-URL, workspace, Article,
  Graph, query-history, pathname-history, and modified/new-tab paths;
- Drawer Escape, Close, backdrop, same-route, and cross-route paths;
- more than 120 observed animation frames before a delayed RSC route is
  released, with no pre-commit main focus;
- nested stale animation-frame cancellation;
- overlapping slow A-to-B navigation followed by history cancellation;
- continuous `focusin` traces proving no transient focus behind an active
  modal during modified activation, close/reopen, or overlap cancellation;
- real Graph destination ownership, real Graph-origin Reader heading
  ownership, and focus restoration to a React Flow SVG edge;
- visible persistent-main focus and no external browser requests.

## 4. Local Test Evidence

| Gate | Result |
| --- | --- |
| Articles/navigation tests | PASS, 58/58 |
| References tests | PASS, 3/3 |
| Tutor tests | PASS, 22/22 |
| Graph tests | PASS, 29/29 |
| Focused Frontend total | PASS, 112/112 |
| Frontend production build | PASS, 11 routes |
| Backend regression | PASS, 600 passed / 4 skipped |
| Product E2E | PASS, 3/3 independent runs, 177 checks each |
| Chromium | 149.0.7827.55 |
| Restart persistence | PASS, 3/3 |
| External browser requests | 0 |
| Unexpected console errors | 0 |
| Page errors | 0 |

The three final E2E runs used isolated temporary runtime stores and left no
result JSON, screenshot, trace, profile, or mutable data in the repository.

## 5. Review Evidence

Review identified and repaired overlapping-transition ownership, a focusable
SVG opener omission, and several insufficiently discriminating browser
oracles. Final review was repeated against the same pinned implementation
snapshot. Both independent reviewers returned PASS with zero Critical or
Important findings.

The final regression suite now observes continuous focus ownership instead of
checking only the eventual active element.

## 6. Security And Repository Safety

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- Action pin and explicit permission rates: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS
- changed paths: P3-030 allowlist only
- Backend, frozen M1, route-view, API, persistence, dependencies, lockfiles,
  workflows, source/Article data, derived assets, and release metadata changed:
  0
- non-loopback network, source, private Zotero, and real/paid Provider access: 0

The local dependency audit was deferred because it requires registry access,
which this task prohibits. Exact-SHA implementation main CI ran and passed it.
The tracked `.env.example` is an existing credential-free template, not a
runtime or secret artifact.

## 7. Exact-SHA Implementation CI

| Gate | Result |
| --- | --- |
| Head SHA | `eabccf1d20d62e12dc5bf4d85181a4c66fe68ad3` |
| Backend pytest | PASS |
| Frontend build | PASS |
| Product E2E, three runs | PASS |
| Dependency audit | PASS |
| Workflow and suppression policy | PASS |
| Secret audit | PASS |
| SBOM validation | PASS |
| Docker compose smoke | SKIPPED as designed for normal `main` push |
| Release evidence dry-run | SKIPPED as designed for normal `main` push |
| Uploaded workflow artifacts | 0 |

## 8. Known Limits

- Route identity intentionally excludes hash-only changes.
- Focus continuity is limited to Shell-owned Global Search and mobile Drawer
  operations; generic navigation focus policy remains outside this task.
- Browser focus behavior depends on supported Next.js navigation events and
  Chromium semantics covered by the production E2E suite.

## 9. Boundary Result

P3-030 changed only the Shell, its navigation helpers, focused tests, Product
E2E, and task governance documents. No Backend, frozen pipeline, product data,
dependency, workflow, external/private, Provider, candidate, tag, Release, or
attestation work occurred.

## 10. Next Gate

Push this docs-only closure commit and require its exact-SHA main CI to pass.
No subsequent task or v1.2 candidate is staged by P3-030 closure.
