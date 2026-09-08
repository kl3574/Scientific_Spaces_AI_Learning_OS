# Current Task

## Active Implementation Task

`docs/tasks/P3-036_WORKSPACE_MUTATION_FOCUS_CONTINUITY.md`

Bounded E2E evidence repair after failed closure CI; product scope unchanged.

## Staged Task

None

## Last Closed Task

`docs/tasks/P3-035_MOBILE_ARTICLE_DISCOVERY_RESULT_VISIBILITY.md`

## Status

- P3-026: PASS / CLOSED
- P3-027: PASS / CLOSED
- P3-028: PASS / CLOSED
- P3-029: PASS / CLOSED
- P3-030: PASS / CLOSED
- P3-031: PASS / CLOSED
- P3-032: PASS / CLOSED
- P3-033: PASS / CLOSED
- P3-034: PASS / CLOSED
- P3-035: PASS / CLOSED
- P3-036: REOPENED / CI EVIDENCE REPAIR

## Authorization

- P3-024 Frontend, tests, governance documentation, local read-only Article and
  Graph validation, isolated fake-provider runtime, local commits, non-force
  push, and exact-SHA CI authorization: CONSUMED / CLOSED
- P3-025 Frontend implementation, focused tests, isolated fake-runtime
  validation, local commit, non-force push, and exact-SHA CI execution:
  CONSUMED / CLOSED after its docs-only closure commit
- P3-026 bounded Frontend implementation, focused tests, governance
  documentation, isolated fake-runtime validation, local commits, non-force
  push, and exact-SHA CI execution: CONSUMED / CLOSED after this docs-only
  closure commit
- P3-027 bounded Tutor Frontend implementation, focused tests, governance
  documentation, isolated fake-runtime validation, local commits, non-force
  push, and exact-SHA CI execution: CONSUMED / CLOSED after this docs-only
  closure commit
- P3-028 bounded Graph/Reader Frontend implementation, focused tests,
  governance documentation, isolated fake-runtime validation, local commits,
  non-force push, and exact-SHA CI execution: CONSUMED / CLOSED after this
  docs-only closure commit
- P3-029 bounded Reader Frontend implementation, focused tests, governance
  documentation, isolated fake-runtime validation, local commits, non-force
  push, and exact-SHA CI execution: CONSUMED / CLOSED after this docs-only
  closure commit
- P3-030 bounded Shell Frontend implementation, focused tests, governance
  documentation, isolated fake-runtime validation, local commits, non-force
  push, and exact-SHA CI execution: CONSUMED / CLOSED after this docs-only
  closure commit
- P3-031 bounded Reader Frontend implementation, pure tests, Product E2E,
  governance documentation, isolated fake-runtime validation, local commits,
  non-force push, and exact-SHA CI execution: CONSUMED / CLOSED after this
  docs-only closure commit
- P3-032 bounded Related Papers Frontend implementation, pure tests, Product
  E2E, governance documentation, isolated fake-runtime validation, local
  commits, non-force push, and exact-SHA CI execution: CONSUMED / CLOSED after
  this docs-only closure commit
- P3-033 bounded Reference/Reader Frontend implementation, pure tests, Product
  E2E, governance documentation, isolated fake-runtime validation, local
  commits, non-force push, and exact-SHA CI execution: CONSUMED / CLOSED after
  this docs-only closure commit
- P3-034 bounded Shell/Reader Frontend implementation, pure tests, Product E2E,
  governance documentation, isolated fake-runtime validation, local commits,
  non-force push, and exact-SHA CI execution: CONSUMED / CLOSED after this
  docs-only closure commit
- P3-035 bounded Article List Frontend implementation, Product E2E, governance
  documentation, isolated fake-runtime validation, local commits, non-force
  push, and exact-SHA CI execution: CONSUMED / CLOSED after this docs-only
  closure commit
- P3-036 bounded Frontend focus ownership, Product E2E, governance
  documentation, isolated fake-runtime validation, local commits, non-force
  push, and exact-SHA CI execution: AUTHORIZED for the remaining bounded
  evidence repair and closure
- Backend, frozen M1, source records, Article records, derived assets,
  dependencies, lockfiles, workflows, and published API contracts: NOT GRANTED
- source network, private Zotero, external search, real/paid Providers,
  candidate, tag, Release, and attestation: NOT GRANTED

## P3-026 Closure Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 119 passed
- production build: PASS, 11 routes
- Product E2E: 3/3 formal local runs plus 10/10 single-core stress runs,
  113 checks each; external requests and unexpected console/page errors: 0
- request ownership, independent badge reads, truthful Session capture,
  storage failures, keyboard focus, and four required viewport cases: PASS
- final implementation reviews: 2 PASS
- workflow, dependency, secret, SBOM, artifact, and protected-path gates: PASS
- implementation commit:
  `57333916e668516ff8e04b3062ffbc3365b72236`
- implementation exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33902645777`
- required implementation CI jobs: PASS; normal-main Docker and release evidence
  skipped as designed; uploaded artifacts: 0
- evidence report:
  `docs/P3_026_ARTICLE_DISCOVERY_TO_FOCUSED_SESSION_REPORT.md`
- docs-only closure commit:
  `5b1de79f6176db00e2dd2f557ce255f7070b0293`
- docs-only closure exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33905442849`
- required closure CI jobs: PASS; normal-main Docker/release jobs skipped as
  designed; uploaded artifacts: 0

## P3-027 Closure Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 121 passed, including 22 Tutor tests
- production build: PASS, 11 routes
- Product E2E: 3/3 runs, 140 checks each, restart persistence PASS,
  0 external requests, unexpected console errors, or page errors
- immutable request ownership, activity/readback ordering, deterministic
  result and Quiz focus, coherent mode semantics, and four required responsive
  viewports: PASS
- independent final reviews: 2 PASS
- local workflow, suppression, secret, SBOM, artifact, and protected-path
  gates: PASS
- implementation commit:
  `b0679da2fd0c70d9148538a08ef942787846c895`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33914369113`
- Frontend, Backend, Product E2E, dependency, secret, SBOM, workflow, and
  suppression jobs: PASS; normal-main Docker/release jobs skipped as designed;
  uploaded artifacts: 0
- evidence report:
  `docs/P3_027_TUTOR_REQUEST_OWNERSHIP_AND_ACCESSIBLE_FEEDBACK_REPORT.md`
- docs-only closure commit:
  `7997cceca268bae1e43806efb5460674a699dc92`
- docs-only closure exact-SHA main CI: PASS, run `34011480204`

## P3-027 Closure CI

- exact-SHA closure run:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33915076653`
- required jobs: PASS; normal-main Docker/release jobs skipped as designed;
  uploaded artifacts: 0

## P3-028 Local Evidence

- focused Frontend: 125 passed
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 runs, 154 checks each, restart persistence PASS
- corrected Graph-to-Reader stress: 100/100 PASS with CPU throttle 4 and
  cache disabled; 301 Article responses, all HTTP 200
- exact return paths, selected/provenance/Study Set origins, Back/Forward,
  hard reload, saved progress, storage denial, error fallback, timeout/retry,
  stale side effects, visible focus, and four viewports: PASS
- external requests, unexpected console errors, and page errors: 0
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- evidence report:
  `docs/P3_028_GRAPH_READER_ROUND_TRIP_RELIABILITY_REPORT.md`

## P3-028 Closure Evidence

- implementation commit:
  `315e446ade3b6565da2d00879b9379a91b08788c`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33929384828`
- Frontend, Backend, Product E2E, dependency, secret, SBOM, workflow, and
  suppression jobs: PASS
- normal-main Docker and release evidence jobs: skipped as designed
- uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting

## P3-031 Local Evidence

- focused Frontend: 113 passed
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 runs, 177 checks each; restart persistence PASS
- exact request counts, reconciliation lock, ordered continuous-focus traces,
  and four required viewports: PASS
- external requests, unexpected console errors, and page errors: 0
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- evidence report: `docs/P3_031_READER_NOTE_DELETION_SAFETY_REPORT.md`

## Next Gate

The P3-036 Tutor activity pre-close repair exposed by run `34178687022` passes
3/3 local Product E2E runs with 227/227 checks each, all focused/full local
regressions, the production build, safety gates, and two independent reviews.
Next verify its exact-SHA main CI, then record and verify a docs-only closure
commit. No later task or v1.2 candidate is staged.

## P3-033 Local Evidence

- focused Frontend: 131/131 PASS
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 complete runs; restart persistence PASS
- exact reference round trips, canonical route/history, independent request
  ownership, truthful failures/retries, and four required viewports: PASS
- external requests, unexpected console errors, and page errors: 0
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- workflow, suppression, secret, temporary SBOM, artifact, and protected-path
  gates: PASS
- evidence report:
  `docs/P3_033_STRUCTURED_REFERENCE_REVIEW_ROUND_TRIP_REPORT.md`

## P3-033 Closure Evidence

- implementation commit:
  `b97dd56fbad4a1f5b9da8742bd923b7dc267c51d`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33976815403`
- Frontend, Backend, three-run Product E2E, dependency, workflow/suppression,
  secret, and SBOM jobs: PASS
- normal-main Docker and release evidence jobs: skipped as designed
- uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting

## P3-033 Closure CI

- docs-only closure commit:
  `b7159446dd96e893a64c72fa81d9baeb00a14eb1`
- exact-SHA closure run:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33977608632`
- required jobs: PASS; normal-main Docker/release jobs skipped as designed;
  uploaded artifacts: 0

## P3-034 Entry Evidence

- two independent reviews: 2 Important ordinary-route focus findings; no
  Critical finding
- controlled local Chromium: desktop rail focus remained outside main;
  ordinary content navigation and Back settled on `BODY`
- external requests during reproduction: 0
- canonical task:
  `docs/tasks/P3-034_ORDINARY_ROUTE_AND_HASH_FOCUS_CONTINUITY.md`
- evidence report:
  `docs/P3_034_ORDINARY_ROUTE_AND_HASH_FOCUS_CONTINUITY_REPORT.md`

## P3-034 Local Evidence

- focused Frontend: 139/139 PASS
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 complete runs, 217 checks each; restart persistence PASS
- ordinary routes, Back/Forward, same-route semantics, delayed and superseded
  navigation, destination ownership, and Reader hash focus: PASS
- external requests, unexpected console errors, and page errors: 0
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- workflow, suppression, dependency, secret, temporary SBOM, artifact, and
  protected-path gates: PASS
- implementation commit:
  `05d18ffc9c359446d264bf8baa79785420af7769`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34005666793`
- required implementation jobs: PASS; normal-main Docker and release jobs
  skipped as designed; uploaded artifacts: 0

## P3-034 Closure Evidence

- task disposition: PASS / CLOSED
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
- active task: none
- staged task: none

## P3-034 Closure CI

- docs-only closure commit:
  `c248eb43ce69ba14d8836f4a81a7f27f522d2ca0`
- exact-SHA closure run:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34006691288`
- required jobs: PASS; normal-main Docker/release jobs skipped as designed;
  uploaded artifacts: 0

## P3-035 Entry Evidence

- controlled Chromium first Article top: `419px` at `1440x900`, `712px` at
  `390x844`, `780px` at `320x844`, and `491px` at `720x450`
- portrait previews and the short-landscape first result are below the initial
  viewport content target
- responsive independent reviewer: Important finding confirmed
- workflow independent reviewer: no equivalent geometry measurement, so no
  contradiction; 0 Critical findings across both reviews
- external requests during controlled fixture measurement: 0
- canonical task:
  `docs/tasks/P3-035_MOBILE_ARTICLE_DISCOVERY_RESULT_VISIBILITY.md`
- evidence report:
  `docs/P3_035_MOBILE_ARTICLE_DISCOVERY_RESULT_VISIBILITY_REPORT.md`

## P3-035 Local Evidence

- initial viewport contract: PASS at `390x844`, `320x844`, and `720x450`
- focused Frontend: 139/139 PASS
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 runs, 221 checks each, restart persistence PASS
- external requests, unexpected console errors, and page errors: 0
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- workflow, suppression, dependency, secret, temporary SBOM, artifact, and
  protected-path gates: PASS
- exact-SHA implementation CI: PASS, run `34010502972`

## P3-035 Implementation CI

- implementation commit:
  `6f5844c80b092a1919f20e5e93f75a9b6ae1e38a`
- exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34010502972`
- required jobs: PASS; normal-main Docker/release jobs skipped as designed;
  uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting

## P3-035 Closure CI

- docs-only closure commit:
  `7997cceca268bae1e43806efb5460674a699dc92`
- exact-SHA closure run:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34011480204`
- required jobs: PASS; normal-main Docker/release jobs skipped as designed;
  uploaded artifacts: 0

## P3-036 Entry Evidence

- exact entry HEAD and cached `origin/main`:
  `7997cceca268bae1e43806efb5460674a699dc92`
- controlled Chromium: Article List, Reader, Saved Learning, Focused Session,
  and Concept capture actions repeatedly settled on `BODY`
- two independent reviews: 0 Critical / 10 Important categories, including
  additional Graph and Tutor focus-loss paths
- isolated three-Article fixture, fake providers, temporary storage, and zero
  external requests
- canonical task:
  `docs/tasks/P3-036_WORKSPACE_MUTATION_FOCUS_CONTINUITY.md`
- evidence report:
  `docs/P3_036_WORKSPACE_MUTATION_FOCUS_CONTINUITY_REPORT.md`

## P3-036 Local Evidence

- focused Frontend: 139/139 PASS
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 complete runs, 225/225 checks each; restart persistence PASS
- external requests, unexpected console errors, and page errors: 0
- all required mutation-focus targets, async ownership, visible focus, and four
  required viewport cases: PASS
- independent final reviews: 2 PASS, 0 Critical / 0 Important / 0 Minor
- workflow, suppression, secret, temporary SBOM, artifact, and protected-path
  gates: PASS
- local dependency audit: deferred to exact-SHA CI because registry network
  access is outside P3-036 authorization
- initial implementation commit:
  `d864cc1755b050a1dfeb247beaaa8a9d20a2eab3`
- initial exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34019342064`
- initial required jobs except Product E2E: PASS; Product E2E attempt 1 exposed
  global intentional-404 count coupling; unchanged-SHA attempt 2 exposed an
  existing Dashboard readiness race; uploaded artifacts: 0
- bounded repair: exact page-scoped 404 ownership and semantic Dashboard
  stabilization; endpoint negative matrix, 10/10 404 probes, 20/20 Shell stress,
  final 3 x 225 Product E2E checks, and 2/2 final reviews PASS
- cumulative repair commit:
  `39369ea430e942ce12c176fb9a9ca24111e59ef3`
- repair exact-SHA main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34023028516`
- required repair jobs: PASS; normal-main Docker/release jobs skipped as
  designed; uploaded artifacts: 0
- task disposition: PASS / CLOSED
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting

## P3-032 Local Evidence

- focused Frontend: 120/120 PASS
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 complete runs; restart persistence PASS
- external requests, unexpected console errors, and page errors: 0
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- workflow, suppression, secret, temporary SBOM, artifact, and protected-path
  gates: PASS
- evidence report:
  `docs/P3_032_RELATED_PAPER_CONTEXT_OWNERSHIP_AND_ACCESSIBLE_FEEDBACK_REPORT.md`

## P3-032 Closure Evidence

- implementation commit:
  `e7b317042df728e568bb5f4d328c678ac3102f0a`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33965187190`
- required implementation jobs: PASS; normal-main Docker and release evidence
  skipped as designed; uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting

## P3-031 Closure Evidence

- implementation commit:
  `f944d2df79505bcca0f22276b1138d84fe1f161b`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33956965124`
- unchanged-SHA attempt 2 required jobs: PASS; normal-main Docker/release jobs
  skipped as designed; uploaded artifacts: 0
- attempt 1 failed only at a pre-existing P3-028 Graph-origin Reader progress
  assertion; the same SHA passed attempt 2
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting

## P3-029 Closure Evidence

- local verification: 130 focused Frontend tests; production build with 11
  routes; 600 Backend tests with 4 skipped; Product E2E 3/3 with 155 checks
  each; restart persistence PASS; zero external requests or unexpected
  console/page errors
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- implementation commit:
  `7b4ac74cd0d4b2e7ce708511387a78eb5f61b7b7`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33935734608`
- required implementation jobs: PASS; normal-main Docker/release jobs skipped
  as designed; uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting

## P3-029 Closure CI

- exact-SHA closure run:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33936738702`
- required jobs: PASS; normal-main Docker/release jobs skipped as designed;
  uploaded artifacts: 0

## P3-030 Local Evidence

- focused Frontend: 112 passed
- production build: PASS, 11 routes
- Backend: 600 passed / 4 skipped
- Product E2E: 3/3 runs, 177 checks each, restart persistence PASS
- external requests, unexpected console errors, and page errors: 0
- independent final reviews: 2 PASS, 0 Critical / 0 Important
- workflow, suppression, secret, temporary SBOM, artifact, and protected-path
  gates: PASS
- evidence report:
  `docs/P3_030_SHELL_MODAL_ORIGIN_ROUTE_FOCUS_CONTINUITY_REPORT.md`
- implementation commit:
  `eabccf1d20d62e12dc5bf4d85181a4c66fe68ad3`
- exact-SHA implementation main CI:
  `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33948697098`
- required implementation jobs: PASS; normal-main Docker/release jobs skipped
  as designed; uploaded artifacts: 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
