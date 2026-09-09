# P3-041 Reader Inline Image Rendering Report

Status: PASS / CLOSED

## Publication And Closure

Implementation dc7411c73802df1255376996c6daf5810f2a87a9 is verified on local
main, cached origin/main and live remote main. [Exact-SHA main CI 34332407397](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34332407397)
completed SUCCESS at 2026-09-09T09:50:41Z. All seven required jobs pass.
Product log readback confirms 3 x 298 original checks, no failed checks,
zero console/page/external errors and four true restart checks. The separate
image profile passes 3 x 8 exact named checks, with matching Chromium
149.0.7827.55, zero console/page/external/unexpected-page counts, no errors,
stable fixtures and removed runtime. Uploaded artifacts: zero.
Docker and release evidence are policy-skipped, not PASS.

A local monitoring connection ended on TLS handshake timeout; a read of the
same run established SUCCESS. No rerun, moved tag, Release or artifact upload
was performed. P3-041 is closed; P3-039 remains OPEN / DEFERRED and UNKNOWN.
The pending statements below preserve earlier checkpoints. This receipt is
carried with the genuine P3-042 implementation, not a receipt-only commit loop.

## Prior Gate

Commit 0a203bae2f99e3c2b3223823e7d91437bc27e96a is synchronized with main.
[Exact-SHA CI 34314910981](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34314910981)
completes SUCCESS at 2026-09-09T06:14:45Z. All seven required jobs PASS.
Remote Backend: 887 passed / 8 skipped / 76 existing warnings, 103.23 seconds;
the corresponding local result was 891 passed / 4 skipped. Remote Product E2E:
three complete runs, each 298 checks, no failed checks or unexpected
console/page/external errors, Chromium 149.0.7827.55 and restart persistence PASS.
Docker and release-evidence jobs are policy-skipped; uploaded artifacts: 0.
Action-runtime Node 20 deprecation annotations are a separate maintenance item,
not a product Node version change or failed job. No workflow change is made here.

## Root Cause And Qualified RED

Reader configures custom image components but leaves ReactMarkdown's default
URL transformation active. That filter removes inline data/blob schemes before
MarkdownImage sees them, making its intended inline-rendering branch unreachable
for the tested PNG. The existing normalization preserves this data URL.

The first canned PNG failed offline decoding and was discarded before browser
execution. It is not qualified image evidence. A fresh 2x2 raster PNG is generated
and decoded in memory using installed Sharp. Its 150-character data URL reaches
the installed Markdown parser, but the image component receives an empty src.
The regression exits 1, actual length 0 versus expected 150. An in-memory
counterfactual admitting only that exact img.src preserves the complete source;
all other URLs retain the upstream default. No product code changed for this.

One independently approved production-browser diagnostic uses the existing
three-Article synthetic fixture. Its input loader is amended before existing
builders generate derived data and fingerprints, not afterward. Identical PNG
bytes decode in an owned, observed blank page. Results on unchanged production:

| Check | Desktop 1440x1000 | Mobile 390x844 |
| --- | --- | --- |
| Actual detail input confirmed | true | true |
| Reader body ready | true | true |
| Matching image count | 0 | 0 |
| Matching unavailable badge | 1 | 1 |
| External placeholder preserved | true | true |
| Outcome | RED | RED |

Chromium: 149.0.7827.55. Positive control: true. All pre/post-cleanup
console/external/page/unexpected-page counts are zero, request count 64,
errors empty, source and fixture stable, runtime removed. Owned frontend
copy/bindings/cleanup all pass. Probe SHA-256:
934b3c1569a8127152271455d4736b314e8a8d58b9e6d11c07a6333da6cdd5fb.
Owned build: 86b4a3f36fe269b45ae87519d35562250d1afe06cf35db9ff03d2a7b3bb5e036.
The owned script and directory are removed; no downloaded or rendered artifact
is retained. Independent qualification review: C0 / I0, QUALIFIED_RED for this
PNG case, not every data/blob format and not a completed repair.

## Scope And Verification

The independent prospective scope review is approved and its prior-CI
prerequisite is now satisfied. The initial scope had thirteen base paths
and ten status-only preceding-closure paths. The reviewed offline-test amendment
adds one Backend test path, making fourteen base and ten closure paths, exactly
24 repository paths in the current canonical task.
Implementation, focused regression and bounded production-browser GREEN pass.
The initial full regression failed; the reviewed isolation and harness repairs
now pass the replacement original three-repeat/restart and separate image gates,
as recorded below. New exact-SHA publication CI remains pending.
No P3-041 completion or publication is claimed. P3-039 remains OPEN / DEFERRED,
historical cause UNKNOWN, with its unchanged draft excluded.

## Implementation Candidate

Reader now supplies an img.src-only URL transform and uses the same admission
helper before rendering. PNG/JPEG/GIF/WebP/AVIF require nonempty canonical base64
with balanced quartets, legal padding and zero unused padding bits. SVG, HTML,
MIME parameters and malformed encodings are not admitted. Browser-origin blob
URLs are syntactically constrained and compared using parsed origins; absent,
opaque or foreign origins fail closed. Other URL attributes retain the installed
upstream default transform. Unsupported inline images show unavailable, while
ordinary remote/relative images retain their explicit source placeholder.

The initial candidate added the same qualified PNG and an additional rejected
SVG to the shared synthetic loader. That changed the derived references and
failed the full-suite geometry precondition recorded below. The current candidate
keeps the original loader unchanged and adds those paragraphs only in a separate
image profile before all derived stores/fingerprints are built. Eight image
checks cover exact src, visible 2x2 decoding, non-raster rejection and the remote
placeholder across desktop/mobile. The negative fixture is additional to the
original RED; it is not an identical diagnostic input or harness hash.

## Local Verification

| Gate | Current result |
| --- | --- |
| Ordinary Backend | Replacement candidate: 929 passed / 4 skipped; earlier failures retained below |
| CLI lifecycle and image-phase contracts | 121 passed, including 38 new parameter combinations |
| Frontend References / Tutor / Graph | 23 / 24 / 34 passed |
| Frontend Articles / real Markdown policy | 73 existing + 15 image-policy tests passed; 88 total |
| Owned production build and desktop/mobile GREEN | PASS; both viewports decode the exact 2x2 PNG; isolated profile now passes 3 x 8 checks |
| Full three-repeat Product E2E and restart | Replacement PASS: 3 x 298 original checks, four restart checks, then 3 x 8 image checks; initial failure retained below |
| Security unit tests | 30 passed |
| Workflow and suppression policy | PASS; no suppressions |
| Dependency audit | PASS; PyPI 40, npm 245, findings/blocked/suppressed 0 |
| Secret audit | PASS; credible/reported/suppressed 0 |
| Temporary SBOM/schema | PASS; 40/244/286 components, 244277 combined bytes; forbidden 0; cleanup PASS |

The replacement gate does not relabel the initial failed invocation or establish
pending exact-SHA publication CI success. No shared frontend
build, user backend, source corpus or private Zotero state is modified.

Focused RED/GREEN command: `npm run test:articles` in `frontend/`. With the
upstream-only baseline, all 73 existing tests passed and the complete-source
regression failed with 0 rather than 150 characters. Before blob support, the
expanded policy suite had 11 passed / 4 failed. The final implementation passes
73 existing and all 15 added tests. All four Frontend scripts therefore pass
169 tests in total. Original CommonJS compilation is unchanged; the separate
ESM output and dependency link are removed by the existing temporary cleanup.

Two independent five-path code/test reviews report Critical 0 / Important 0.
They cover production wiring, strict URL admission, native image assertions,
fixture timing and unchanged original E2E checks. The subsequent bounded
production GREEN is recorded separately below. The subsequent full-suite failure
is recorded below; static review does not establish its result.

The first repaired-build probe returned INCONCLUSIVE at setup with zero browser
cases, not a product FAIL or GREEN. Read-only checks showed both new Frontend
files absent from the unchanged isolation helper's tracked-input inventory;
the Reader already imported the missing policy module. After the completed
reviews and secret/path audit, only those two new files were explicitly staged.
Both are now included by the original inventory. The same probe was rerun with
no product, build-helper, guard, fixture or acceptance change. The initial
pre-browser failure is retained rather than counted as successful validation.

## Production Browser GREEN

The unchanged probe code, now receiving the complete tracked build inputs,
exits 0 PASS. Desktop 1440x1000 and mobile 390x844 each have exactly one matching
image, complete native decoding to 2x2 pixels, no positive unavailable badge,
correct detail input and visible body/math. All four image-policy checks pass
per viewport, including rejected SVG fallback and the existing remote-image
placeholder. No forced DOM repair, remote image fetch or source data is used.

Chromium: 149.0.7827.55. Positive control true; errors empty; before/after cleanup
console/external/page/unexpected-page counts all zero; request count 65. Source
and fixture stability, owned-copy validation, shared-state bindings and runtime
cleanup are true. Owned build:
db5f731419e80be1a5a3ab247abccd9188db99a500632cc248ccbf7413a4db49.
Input binding:
0b2bb915a203f5d736d27cc87623185690d7a3dd25886e1cd00c692b9a334c6b.
Shared build remains:
b39eae0a13944cf6515c4b7a486e9cd877db58726b199fb9597999f90b617812.
Probe SHA-256:
ba510a22c362cae76d5b2dcf91df422e48f8ab2c6d8ad2fbabc7977e092a57ef.
Its additional negative fixture and assertion helper differ from the original
diagnostic; the qualified PNG bytes and desktop/mobile user journey are retained.

## Full Regression Failure

The required command with backend 18000, `--repeat 3 --frontend-mode start`,
exits 1. It reaches the first iteration's existing desktop display/reading-tools
ownership case, then fails `no genuine interior section` after a genuine body
wheel. The stored checkpoint and independent DOM oracle agree on References at
55 percent. The unchanged test requires a non-terminal body section other than
References. This is not a timeout/403 risk and is not waived.

Failure geometry: viewport 1280x900 after display reflow; scrollY 1024;
References top -0.21875; Markdown height 989.046875; Article root height
2646.046875. The native wheel target is a fixed fraction of Article root height,
which also includes the following structured-reference panel. Fixture/layout
coupling is a hypothesis, not yet a confirmed cause or product regression.

All owned-build input/dependency/shared-build bindings remain stable and cleanup
passes. No owned frontend or three-repeat runtime directory remains. No complete
three-round result or restart PASS is inferred from the partial first iteration.
Publication is withheld. A bounded, independently reviewed paired fixture
diagnosis follows; original assertions and product code are unchanged.

## Paired Fixture Diagnosis And Isolation

One independently reviewed pair uses the same repaired production build with
two fresh synthetic runtimes. Candidate retains the two added image paragraphs;
control removes exactly those paragraphs before all builders run. All other
Article fields are equal. Each arm calls the unchanged display scenario filter
once, preserving the original mobile and desktop assertions and native actions.

The probe's first review found one cleanup-error qualification defect. The
correction preserves a bounded exception chain, admits only one known interior
assertion failure, rejects unknown/cleanup failures and reports completed-case
lower bounds. Four offline failure-chain contracts pass, including an interior
failure followed by teardown failure. Re-review: Critical 0 / Important 0.

Result: exit 0, OBSERVED / CANDIDATE_ONLY_INTERIOR_FAILURE. Candidate completes
mobile then reproduces the exact desktop failure, including progress 55,
References top -0.21875, root/Markdown heights 2646.046875/989.046875 and scrollY
1024. Control completes both mobile and desktop display cases. Requests:
candidate 166, control 266. All per-arm console/external/page/unexpected-page
counts zero; fixture/source stability and runtime cleanup true; errors empty.
Chromium is 149.0.7827.55 in both arms. Same owned build:
0dc2a4ff58b12916a21c2f3fcc7ca68fab6af25730f6fca8a9c2186f4cd09a25.
Reviewed probe SHA-256:
9291e6ccc2428cdddc3200ad331ac2b21ce7b3f76438b91ccf35d0dd167602c7.
The probe and owned directory are removed after execution.

Pure extraction confirms candidate/control have 5/3 reference candidates and
777/540 content characters. This establishes an observed fixture association,
not a defect in the product's progress denominator. It does not replace the
failed full-suite gate or prove every possible enlarged-Article layout.

Independent design review approves a separate image-profile runtime within the
same build after original repeat-three and original-runtime restart/teardown.
The five original functions `_load_fixture_articles`, `_run_single_iteration`,
`_verify_reader_progress_ownership`, `run_browser_suite` and
`verify_backend_restart_persistence` are AST-identical to HEAD. No original
threshold, native gesture or assertion is adjusted. Original 298-check runs stay
intact; the new profile reports three separate eight-check runs. Overall PASS
also requires the image profile, matching browser versions, strict final audits,
immutable Article/Graph/reference bindings and cleanup. At that checkpoint,
replacement verification and concrete final review were pending; no new full-suite
PASS was claimed. Their completed receipts follow below.

The first Backend rerun after profile isolation has 889 passed, 4 skipped and
2 failed (76 existing warnings, 44.93s). The existing CLI environment-lifetime
tests for full-suite success at ports 8000/18000 mock `prepare(root)` without
the new optional profile argument and provide only the original UI-body mock.
Their environment restoration, secret isolation and resource-cleanup assertions
still pass, but success correctly fails because the new mandatory profile cannot
execute through those mocks. No bypass is added to the runner. An independently
reviewed one-file test-harness scope amendment is now approved; product Backend and
the runtime isolation helper remain unchanged. No further browser/full rerun or
publication occurs before this regression is corrected and independently reviewed.

The only added path is `backend/tests/test_graph_provenance_return.py`. Its
existing twelve CLI lifetime combinations and environment/private-state/signal
assertions must remain. Resource and UI-body mocks adapt to the independent
profile while its real orchestration, coverage checks, fixture binding, audits
and cleanup execute. New negative cases cover incomplete checks, incorrect
browser or fixture, body/startup/teardown failure, late audit and interruption.
The runner resets mutable data before each repeat, audits even failed iterations
after resource exit, and preserves completed original runs/restart on image-phase
failure. Original temporary-runtime cleanup must succeed before the profile starts.
Independent static re-review had Critical 0 / Important 0. At that checkpoint,
focused execution and the full replacement gates were pending, not inferred from
the review; their subsequent execution results follow below.

The expanded negative suite then reproduced a genuine coverage-gate defect:
replacing one required image check with an unrelated true check retained eight
values and incorrectly returned PASS at both ports. Focused result was 119 passed
and 2 failed. The runner now requires the exact eight desktop/mobile image keys
and literal `True` values. Replacement focused result is 121 passed, 148 warnings,
8.90 seconds; all original twelve lifecycle combinations remain. The additional
38 cases cover normal ordering/repeat isolation, 17 failure modes at both ports,
and original temporary-directory cleanup failure at both ports.

Ordinary Backend now passes 929 tests with 4 skipped and 152 warnings in 47.91
seconds. The warnings are repeated imports of the same two existing invalid
escape-sequence locations, not new product behavior. All four Frontend scripts
pass again: Articles 73 + 15, References 23, Tutor 24, Graph 34; total 169.
The five original functions named above remain AST-identical to the entry commit.
Final six-path executable review and 24-path documentation/scope review both
report Critical 0 / Important 0. Secret audit passes with zero credible, reported
or suppressed findings. At that checkpoint, new-profile production execution and
replacement full E2E were pending. Their completed receipts follow; none of these
results relabel the historical failed full run.

## Isolated Image Profile Verification

The real `_run_reader_inline_image_profile` runs against a fresh owned production
build with backend 18000/frontend 3000. It completes three repeats, each with
all eight exact desktop/mobile checks true. Chromium is 149.0.7827.55. Each
repeat's final external-request, console-error, page-error and unexpected-page
counts is zero. Errors are empty; immutable fixtures are stable and the runtime
is removed. The owned frontend copy, shared-state bindings and cleanup all pass.

Owned build:
5b4a7322887b937b46dcb7adec400af30d911f9ce86f83b7561fcf3e52833c18.
Input binding:
0b2bb915a203f5d736d27cc87623185690d7a3dd25886e1cd00c692b9a334c6b.
Shared build remains:
b39eae0a13944cf6515c4b7a486e9cd877db58726b199fb9597999f90b617812.
Dependencies remain:
bc742ff3249a71f08f150a9ca5b2e94896c6bf73e18a5519e04b814ed4a5ab49.
No diagnostic script, screenshot, image export or runtime artifact is retained.
This confirms the isolated image phase, not the complete original product gate.

Security rechecks pass: 30 unit tests, workflow policy (19 actions, complete
pinning/permission coverage), suppression policy (zero suppressions), secret
audit (zero findings) and dependency audit (PyPI 40/npm 245, zero findings).
SBOM regeneration/schema validation also passes: Backend 40, Frontend 244,
combined 286 components, 244277 combined bytes, full lock coverage and zero
forbidden artifacts. Its owned temporary directory is removed. The manifest
commit remains the entry SHA until publication; this is not new-commit CI evidence.

The changed/untracked inventory matches all 24 allowed paths plus the preserved,
excluded frame-oracle draft, with no unexpected path. A broad tracked-artifact
pattern initially flags only the unchanged `.env.example`. Full content inspection
and independent review classify it as a public configuration template: local
defaults, fake providers and an empty API key, not runtime/private data. No real
`.env` or generated asset is exempted by that classification. The secret audit
has zero findings and the two lockfiles and excluded oracle retain their hashes.
The replacement full gate was then executed as recorded below. Publication
requires the final receipt and safety review; task closure still requires the
new commit's exact-SHA CI, not the prior integration's CI.

## Replacement Full Gate

On 2026-09-09 the unchanged complete CLI, with backend 18000, `--repeat 3` and
`--frontend-mode start`, exits 0 PASS. Started at 08:06:52Z, completed at
08:48:24Z; elapsed 2492.06 seconds. Environment: Linux 7.0.0-28-generic,
Python 3.11.15, Node 22.22.1, uv 0.11.21, Chromium 149.0.7827.55.

- Original runs: 3/3 PASS, exactly 298 checks each; failed checks empty.
- Original console/page/external error counts: zero in every run.
- Original six mobile page widths: 390, equal to the 390 viewport in every run.
- Restart: bookmark, completed states, ended sessions and note all true.
- Separate image profile: 3/3 PASS, exactly eight required checks each;
  desktop/mobile exact PNG source and visible native 2x2 decoding pass.
- Image final console/page/external/unexpected-page counts: zero in every run.
- Image errors empty, immutable fixture stable and runtime removed.
- Original and image browser versions match; owned frontend copy, shared
  bindings and cleanup all pass. Stderr bytes: zero.

The unchanged audit ledger classifies 1145 framework prefetch cancellations,
67 route-transition cancellations and 12 declared route-read cancellations.
These are not counted as unexpected errors; no classification rule is changed.
The eight image checks remain separate, not reported as 306 original checks.
The removed original runtime and terminal process were independently read back.
No downloaded content, screenshot, profile, trace or other runtime export remains.

Owned build:
7876febb38438c00474a30813c6338d333939a54b05c04a0705c034c646a295d.
Input, shared-build and dependency bindings match the isolated-profile values
above. The earlier failed full run and paired diagnosis remain historical facts,
not waived assertions or evidence that P3-039 was repaired.

Local verification is PASS. Publish only the 24 reviewed paths with
`fix: render safe inline reader images`, excluding the preserved frame oracle.
P3-041 remains open until all seven required exact-SHA main CI jobs pass.

## Limits

URL admission does not prove that arbitrary raster bytes decode. The actual
browser evidence is specific to the valid PNG fixture. Blob admission does not
create an object URL or prove its content type, existence or lifetime. Remote
image download/archive, SVG rendering and inline links remain outside this
repair. The unresolved P3-039 Graph incident is not claimed fixed by this work.
