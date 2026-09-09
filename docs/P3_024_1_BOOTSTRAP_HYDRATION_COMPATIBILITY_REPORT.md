# P3-024.1 Bootstrap Hydration Compatibility Report

Status: LOCAL VERIFICATION PASS / INTEGRATION CI PENDING

## Current Evidence

Next 15.5.24 is required by the separate security revision, but the existing
bootstrap workaround admits only Next 15.5.21. Installed production React export
is still 19.2.0-canary-0bdb9206-20250818 and App Router hydration remains inside
startTransition. The P3-024 report explicitly requires validation after upgrades.

The original repeat-three E2E fails on React 418/HTML. A first focused Reader/
Dashboard diagnostic is negative; an initial exact-prefix diagnostic has an
incomplete audit due to a harness cleanup error and remains INCONCLUSIVE.
Neither result is overwritten. The corrected harness passes four fake lifecycle
checks before live use and produces qualified RED in 138.56 seconds:

- Prefix completes; one 418/HTML, before Reader entry on Dashboard at event 13.
- Reader entry/exit page-error counts are both one; no error is discarded.
- Fresh-browser/reset-fixture Reader-only control completes without errors.
- All unrelated console/external/unexpected-page counts and cleanup failures: 0.
- 235 bounded events; no observer failure or overflow.
- Next 15.5.24; workaround marker false; source/build/shared bindings stable.
- Owned build and synthetic runtime removed; user backend unchanged.

Detailed evidence and historical failures remain in the P3-005.4 report.
This establishes prefix-associated reproduction, not prefix necessity or an
internal framework root-cause proof. P3-039 is not declared repaired.

## Independent Decision

APPROVED with exact-version-only scope. Add four paths beyond the previous
24-path integration candidate. Preserve all other runtime guards and behavior.
Bind regression evidence to the actual Next manifest/lock/installation and
bundled production React, not root React or an automatically derived guard.

## Validation

The new version-binding test first fails with literal 15.5.21 versus installed
15.5.24; the former-version mismatch case also fails before the rebind. After
changing only the literal/comment, `npm run test:graph` passes all 34 tests.
The runtime assertion reads Next's bundled production React export explicitly,
not the root React version. All one-shot/restoration/expiry guards are unchanged.

The matched counterpart completes with the identical reviewed harness:
`b4484962e5d1f485f0754020f7ec1ad09318d5de81d46b1cc9981aa12c056965`.
The 83.0-second invocation is a matched GREEN: exact prefix complete, React 418
count zero, and external/page-error/unexpected-console/unexpected-page counts
all zero. Reader entry/exit error counts are both zero. Two raw console messages
belong to the original declared error fixtures, not new exemptions. All 148
bounded observations are retained without overflow or unavailable state.
Next 15.5.24 documents show the workaround marker; a non-Next document shows no
marker. The conditional RED-only control correctly does not run.

Copied-source and temporary-build fingerprints intentionally differ from the
baseline; dependencies, shared build, ports, synthetic fixture, delays and
assertions remain unchanged. Within-run bindings, shared state, copy verification,
cleanup and synthetic runtime removal all pass. Metadata-only evidence:

- copied inputs: `b6178de09bd098df82397f0516a1c93cfee290b6f6b88891654d9d4cab5a4a31`
- owned build: `3f6fa901a235f1125a3b2d2cce97fb99672d74e947be42cd5fff3da84a132dc7`
- shared build: `b39eae0a13944cf6515c4b7a486e9cd877db58726b199fb9597999f90b617812`
- dependencies: `bc742ff3249a71f08f150a9ca5b2e94896c6bf73e18a5519e04b814ed4a5ab49`

The diagnostic's `NOT_REPRODUCED` status is not a full-suite result. Independent
review of both frontend paths and the predefined stress contract returns
PASS, Critical 0 / Important 0. The matched evidence admits that stress gate,
not publication or an internal framework root-cause claim.

Fresh ordinary gates after the rebind:

- `uv run --offline --project backend --extra dev pytest -q`: 891 passed,
  4 skipped, 76 existing invalid-escape warnings, 45.86 seconds.
- Frontend `test:articles`, `test:references`, `test:tutor`, `test:graph`:
  73 / 23 / 24 / 34 passed, total 154.
- Security tests: 30 passed, 29 subtests; workflow and suppression policy PASS.
- Two complete dependency audits: each PyPI 40 / npm 245, findings 0, blocked 0,
  suppressed 0. All existing scanners remain required.
- Full SBOM CLI/schema/coverage PASS, forbidden 0, combined 244277 bytes.
  Temporary outputs removed; component totals 40 / 244 / 286. Existing
  P3-005.5 fingerprint evidence is unchanged and still bound to fee813b HEAD.
- Secret audit: credible/reported/suppressed 0. Exactly 28 reviewed candidate
  paths plus the unchanged excluded oracle; index empty, no unexpected paths,
  symlinks, binary runtime artifacts or candidate files above 2 MB.
- Frozen Backend/M1/API, page components, Next configuration and CI workflow
  paths have no diff; `git diff --check` passes.

CI coverage limitation: the existing Frontend job builds the application; it
does not invoke the four frontend unit-test scripts. Their 154 passing tests
are local evidence, not CI evidence. The version-binding regression must be
run during future dependency review; automatic CI execution of those unit
suites is a separate workflow-revision candidate, not silently added here.

At the matched-counterpart checkpoint, predefined stress, original seven-case and repeat-three gates, final
production-build/runtime evidence, independent final integration review and
exact-SHA CI remain pending. No compatibility repair completion or closure is
claimed. Stress retains strict routing; Playwright's installed API documentation
states that routing disables HTTP cache. Its baseline and explicit-CDP cases
therefore do not establish a cache-enabled versus cache-disabled comparison.

## First Stress Attempt

The independently reviewed temporary harness
`d12d5f40e0a80aec0e168ed6392dead8b9b54b32e6f7b8f0b99c2fd8966908de`
passes nine fake lifecycle/output/count tests. Review corrects the draft to the
actual Graph deep link, same-page hard reloads and the model's lowercase
`attention` heading before browser execution. It is not a product change.

The actual invocation stops on its first Graph load, after 16.07 seconds:
FAIL, `audit_failed`, completed 0 / 1400. Raw console, original unexpected-error
ledger, page errors, external requests, pending requests, unexpected pages and
explicit expectations are all zero. The temporary harness's additional blanket
failed-request counter is three. This does not establish React 418 recurrence,
nor does it yet prove that these are harmless framework cancellations.

Browser: Chromium 149.0.7827.55. Source/build/copied-input/fixture/shared-state
bindings remain stable; cleanup errors zero; synthetic runtime and owned build
removed. Graph document SHA-256:
`37bcb3703c751e673cff4b1b0549fdd9955b364073c6dabff38298843a0d0479`.
The historical owned-build digest was recorded truncated (60 hexadecimal
characters); the complete SHA-256 is unavailable in this receipt. It is not
used as a verifiable hash or reconstructed. The later qualified diagnostic and
prospective full stress have their own complete evidence below.
The existing user backend remains untouched. No stress PASS or full-suite
replacement run is claimed. A bounded first-load metadata diagnostic must
classify these terminations before further stress; no blind rerun or new
request/error exemption is permitted.

## Request-Termination Diagnosis

Independent review first rejects incomplete diagnostics: post-cleanup-only
capture, masked capture errors/overflow, and late resource errors hidden by the
first audit failure. These temporary-harness defects are corrected before any
diagnostic execution. Twelve fake tests include a cleanup-created cancellation,
classifier failure, overflow and a later server teardown error. All pass.

The one approved first-load diagnostic, harness
`65d2b52e3b71d96fc3c5e4c5728da5160992f693a9602dd18754551060012d2b`,
completes in 16.13 seconds. Diagnostic validity is true; the original stress
FAIL is retained. Pre-cleanup and post-cleanup snapshots are identical:

| Route bucket | Method/type | Status | Failure | Original prefetch policy before cleanup | Start/response/terminal sequence |
| --- | --- | --- | --- | --- | --- |
| library | GET/fetch | 200 | net::ERR_ABORTED | true | 52/61/67 |
| articles | GET/fetch | 200 | net::ERR_ABORTED | true | 54/64/69 |
| zotero | GET/fetch | 200 | net::ERR_ABORTED | true | 55/65/70 |

Every row has an allowed local origin, RSC plus explicit prefetch evidence and
an exact response-URL match. The unchanged original predicate also checks
main-frame ownership, non-navigation, no service worker and its one-second
ordered lifecycle bound. There is no capture error, overflow, execution failure
or unrelated audit error. All bindings and cleanup pass. This proves the three
observed terminations were already accepted by the original policy before
cleanup; it does not justify ignoring arbitrary aborts or future failures.

Independent code review confirms the temporary blanket raw-failure gate was
stricter than, and inconsistent with, that existing evidence-bound policy.
The minimal adapter correction delegates only to the unchanged original
prefetch predicate. Unrecognized failures still block; raw and recognized
counts remain separate metadata. The original unexpected-error ledger, raw
console/page/external/pending/unexpected-page checks and no-explicit-exemption
requirement are unchanged. Thirteen fake tests now pass, including rejection of
an otherwise identical unrecognized abort and of an independent ledger failure.
No product code or original verifier/classifier was changed. A prospectively
reviewed full stress invocation is still required; the failed attempt is not
relabelled PASS.

## Prospective Full Stress Result

Independent re-review approves the adapter at
`7c53d18da45d154c700c0b8fa30ff519f61f04234332a4a46ad017dff5186b56`,
Critical 0 / Important 0. One prospective full invocation then passes:
1400 / 1400 loads, 10 initial navigations plus 1390 native same-page reloads,
in 1315.91 seconds with Chromium 149.0.7827.55.

| Group | Viewport | Passed loads |
| --- | --- | --- |
| Graph deep link, guarded baseline | 1440x1000 | 500/500 |
| Graph deep link, explicit CDP cache disabled | 1440x1000 | 200/200 |
| Graph deep link | 390x844 | 100/100 |
| Graph deep link | 320x844 | 100/100 |
| Graph deep link | 720x450 | 100/100 |
| Article search | 1440x1000 | 200/200 |
| Dashboard | 1440x1000 and 390x844 | 50/50 each |
| Reader | 1440x1000 and 390x844 | 50/50 each |

All 1400 version/marker, real heading and hydrated-shell checks pass. Ten group
binding checks pass. Console, original unexpected-error ledger, page, external,
pending, unexpected failed-request and unexpected-page counts are zero; explicit
error expectations remain zero. Raw transport cancellations total 1949; all
1949 are recognized by the unchanged original prefetch predicate. They are
reported rather than discarded, and are not claimed to be zero.

Source, fixture, copied-input and shared-state bindings remain unchanged;
cleanup errors zero, temporary runtime and owned frontend removed. The user's
backend still owns port 8000; test ports are free after cleanup. No HTML/body,
image, PDF or trace output is retained.

- source binding: `d5ddff849d7ad0f0c43cbaf4e20dd3ffe90a62fe383ad3b02f7e4f079f03e564`
- owned build: `39bbdc7756bbb9aa97f2bc282dc5c3719ff1d6a1fe66722868e14743a644ffc9`
- Graph SSR hash: `5d6c677a12c2e6eed0196224632c8583e2222b0d40df35d09f9c755cd77fa135`
- Articles SSR hash: `ac4c7ffbae5528a1bc3b911ffba210646f9fad66982b0f4b154e91fefe13cf8d`
- Dashboard SSR hash: `a86a82994d7a7bd34cf1b9739675acbbfa927e28822fc2884f614f86dc1a1b71`
- Reader SSR hash: `c645e9e3a810ddc385f328334331cec9853fef58dca3dbd86a4afee3e75fb57a`

Each SSR hash is stable within this build; different owned builds need not have
the same generated build identifier or response hash. Shared-build/dependency
and copied-input hashes match the matched-counterpart evidence above. This is
the prescribed stress PASS, not a cache-performance comparison, P3-039 repair,
full Product E2E result or publication approval. Original seven-case and
repeat-three replacement verification are the next gates.

## Original Provenance Replacement Gate

After the prospective stress passes, the unchanged seven-case CLI runs with
`SCIENTIFIC_SPACES_E2E_BACKEND_PORT=18000 uv run --offline --project backend
--extra dev python scripts/e2e/check_graph_provenance_return.py`.
Exit 0, schema v1, all seven cases PASS: desktop/mobile round trip, missing
origin and wrong-Article fallback, plus mobile arrival supersession. Fields
for checks not applicable to a scenario remain false; they are not failures.
Console, external, page-error and unexpected-page counts are zero. Source/build
bindings match, the synthetic fixture is unchanged, and runtime removal passes.

## Complete Replacement E2E

The original command completes with exit 0 on 2026-09-09:

```bash
SCIENTIFIC_SPACES_E2E_BACKEND_PORT=18000 uv run --offline --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start
```

Its stdout is projected to bounded diagnostic metadata with jq; bash pipefail
preserves the original exit status. No test assertion or admission rule changes.
Chromium 149.0.7827.55 completes all three runs, each 298/298 checks, with no
failed checks, unexpected console errors, page errors or external requests.
Restart persistence is PASS: two completed states, one bookmark, one note and
25 ended sessions, according to the original four assertions.

The owned production build completes, copy_verified=true,
bindings_stable=true and cleanup_complete=true. Build output is 1591 bytes of
diagnostic stdout, not retained as a build artifact. Exact owned-build SHA-256:
`9b5494cc592c82a0f161219af11bbc6fb0e01d5c0787b40b23e107af6bc2c858`.
Copied-input, dependency and shared-build hashes match the earlier evidence.
The original CLI emits its result after temporary-runtime and owned-build
cleanup; no HTML/body, image, PDF, trace or raw log is exported.

Both completed diagnostic scripts and their owned temporary directory are now
removed. The excluded frame-oracle draft is unchanged. Independent integration
code review has Critical 0 / Important 0; the later historical truncated-digest
documentation finding was explicitly corrected and independently closed.
Final receipt review also passes, Critical 0 / Important 0, approving the exact
28-path integration commit and non-force publication after safety checks.
Exact-SHA main CI still precedes closure. Original
failed runs remain failed; P3-039 remains OPEN / DEFERRED, cause UNKNOWN.
