# P3-005.4 Product Test Runtime Isolation Report

Status: PASS / CLOSED

## Closure Receipt

Replacement integration [0a203bae2f99e3c2b3223823e7d91437bc27e96a](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/commit/0a203bae2f99e3c2b3223823e7d91437bc27e96a)
passes exact-SHA [main CI 34314910981](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34314910981),
completed SUCCESS at 2026-09-09T06:14:45Z. All seven required jobs pass.
Product E2E: three runs of 298 checks, no failed checks, restart persistence
four checks true, zero unexpected console/page errors or external requests.
Uploaded artifacts: 0. Docker/release jobs are policy-skipped, not PASS.
The prior local gates and independent final reviews remain recorded below.

Current task: [P3-041 Reader Inline Image Rendering](tasks/P3-041_READER_INLINE_IMAGE_RENDERING.md),
OPEN / IMPLEMENTATION, not completed by this prior CI. P3-039 remains
OPEN / DEFERRED, historical cause UNKNOWN. Formal version v1.1.0; candidate None.

Historical record follows: earlier pending/open gate statements describe their
pre-closure checkpoints, not current status. Original failures, requirements,
thresholds and scope are retained unchanged.

## Current Replacement Evidence

With the separately reviewed P3-024.1 exact-version rebind, the original
seven-case CLI passes 7/7 and complete Product E2E passes three runs of 298
checks plus restart persistence. All unexpected console/page/external counts
are zero. The temporary frontend is built from verified inputs; copy, shared
bindings and cleanup pass. Backend 18000/frontend 3000 remain the test endpoints;
the user's backend on 8000 is untouched. Detailed fresh receipts and the
1400-load stress PASS are in the P3-024.1 report. Historical failures below are
not overwritten. Exact-SHA integration CI is still pending.

## Reproduction And Root Cause

The seven-case CLI exits 2 at server_setup, zero cases, clean audit, unchanged
bindings and removed temporary data. Local socket inspection identifies port
8000 as owned by an existing user-terminal backend. The runner hard-codes that
port for startup/restart, browser/control API, routing and audit predicates.
The application build also embeds its API endpoint. Changing only the launch
port would either fail validation or contact the unrelated backend.

The existing backend is not test-owned and was not stopped or reused. The
namespace availability check fails UID-map permission. No policy bypass occurs.

## Independent Design Review

ACCEPT with frontend fixed at 127.0.0.1:3000, matching unchanged backend CORS.
Only the backend port is configurable. Use an owned source-identical temporary
frontend build, strict environment/copy controls, actual build bindings and
owned process groups. Replace, never widen, the backend origin allowlist.

The canonical task contains the five executable paths and all unchanged gates.
No application implementation or application runtime configuration is changed. The
preserved security candidate remains uncommitted; no original failure is waived.

## Validation

The first independent pre-browser review holds actual build/browser execution
for two Important findings: the Playwright driver inherits the unsanitized
Python environment, and a server leader can exit while its owned descendants
survive. The full CLI also needs SIGTERM routed through owned-runtime cleanup.
These are test infrastructure defects, not product or acceptance changes.

On 2026-09-09, the helper's 85 offline contracts and 24 security tests pass
together: 109 passed, 6 subtests passed. The helper now provides an exact,
restoring process-environment scope and preserves installed browser discovery
before changing HOME. No browser download or actual build was performed.

The caller-level leader-exit regression first fails with only SIGTERM observed;
after the bounded fix it passes with SIGTERM then SIGKILL of the owned group.
The subsequent caller suite records 14 RED cases: twelve environment-lifetime
cases across both CLIs, both backend ports and success/startup-error/interrupt,
plus SIGTERM at full-CLI build entry and suite body. Both CLI lifetimes now use
the restoring environment scope; full-CLI SIGTERM unwinds owned resources and
restores the prior handler before emitting its result. These are process-local
mocked driver/server/signal boundaries, not live-browser evidence.

The final focused command passes 168 tests (83 caller, 85 helper) in 6.27 seconds.
Missing-group reaping, termination escalation and final timeout propagation
also pass. The 72 warnings come from the two existing invalid JavaScript string
escapes in the full runner, imported repeatedly by these tests. Independent
pre-browser re-review now passes with 0 Critical / 0 Important. It approves the
sequential isolated production build, seven cases and original repeat-three
suite at backend 18000/frontend 3000; it is not publication approval.

Current secret audit: PASS, credible/reported/suppressed 0. Workflow policy:
PASS, 1 workflow, 19 actions, pin and permission rates 1.000. Suppressions: 0.
Backend/Frontend locks and the excluded oracle retain their reviewed hashes.
The user backend still owns 127.0.0.1:8000; neither 3000 nor 18000 is occupied.
No unrelated service was connected to or stopped.

Full final Backend: 891 passed, 4 skipped, 76 warnings in 44.60 seconds. The
warnings are the same two pre-existing escapes, not new failures.

The actual alternate-port seven-case CLI now exits 0 / PASS: three desktop and
four mobile cases, audit PASS, external/console/page/unexpected-page counts all
0, bindings_equal=true, fixture_unchanged=true and runtime_removed=true. The
helper's owned production build and shared-state/cleanup checks also completed
without exception. Afterward only the unchanged user backend remains on 8000;
test ports 3000 and 18000 have no listener. No screenshot, trace or raw log was
exported. The seven-case schema remains v1.

The original `--repeat 3 --frontend-mode start` CLI terminates with exit 1 after
131.29 seconds. The unchanged Graph deep-link-reopen audit reports an earlier
`reader-fragment-route-owner` homepage page error: React production error 418
(HTML hydration). No complete iteration or restart-persistence result exists;
full E2E is BLOCKED, not retried or waived. stderr bytes: 0.

The owned runtime still reports copy_verified=true, bindings_stable=true and
cleanup_complete=true. Input hash:
`15892f3aaec0227db911db2d03bf1541c1a3f673cea5b23e700ed89587433656`;
temporary build:
`32a196285da2a1d49b4ace91fd3ae5476a437e5d3049916501c35d0db6b80ec6`;
shared build:
`b39eae0a13944cf6515c4b7a486e9cd877db58726b199fb9597999f90b617812`;
dependencies:
`bc742ff3249a71f08f150a9ca5b2e94896c6bf73e18a5519e04b814ed4a5ab49`.
Only the existing user backend remains listening on 8000. No runtime artifact
or raw output was saved; structured stdout hash:
`8eb6367d306466359a1fa06aa3cc9f6e1e2c37259dac6b446202a97eef62c766`.

Inspection identifies a concrete compatibility candidate: the existing
bootstrap hydration workaround only admits Next 15.5.21, whereas the security
repair installs 15.5.24. Installed bundled React is still the exact supported
`19.2.0-canary-0bdb9206-20250818`, and App Router still calls hydrateRoot inside
startTransition. The earlier P3-024 report explicitly requires revalidation on
framework upgrades. This is a diagnosis candidate, not yet a causal or repair
claim. No application source has been changed. Independent diagnostic review
precedes any focused replay or separately scoped compatibility revision.

Full E2E, restart persistence, final integration review and replacement exact-SHA
CI remain unsatisfied. No commit or publication is authorized by partial success.

## Bounded Hydration Diagnostic

Independent review permits one unchanged Reader fragment-ownership journey and
one fresh-context Dashboard control on a single owned build, with the original
full-suite synthetic fixture/reset. Observation is passive and metadata-only:
page ordinal, main-frame route enum, event sequence, error code and the existing
Next version/workaround marker. No version spoofing, scheduler change, expanded
guard, product repair, CPU/cache matrix or full-suite retry is permitted.

Both cases complete in 69.58 seconds with no React 418 or strict-audit errors.
There are 89 bounded events, no overflow and no failed observation. Next 15.5.24
is observed with the workaround marker false. Chromium: 149.0.7827.55. Copied
input, shared build and dependency hashes match the failed full run. Temporary
build hash: `eadd399c83cde7548eeb77bdf73db6d3ba4c27622423d0e3327a698cde139bfd`.
Shared-state checks and both temporary cleanups pass; the user service remains.

Verdict: NOT_REPRODUCED / causal attribution INCONCLUSIVE. The original full
failure remains a blocker. This is not evidence that the compatibility gap is
harmless or repaired. Any next diagnostic must be separately bounded and
independently reviewed; no product guard change has been made.

The next independently approved exact-prefix attempt captures candidate React
418/HTML at event 78, Reader route, page ordinal 6, Next 15.5.24 and marker false.
It terminates in 81.48 seconds with a harness AttributeError: LocalOnlyBrowser
does not expose a contexts attribute. Its final case/audit record is incomplete,
so the verdict remains INCONCLUSIVE, not qualified RED. No test listener or
browser remains afterward; the user backend is unchanged. No whole-suite retry
or product change follows this incomplete observation.

Independent review admits one corrected prefix attempt, tracking only the
returned owned LocalOnlyContext wrappers, retaining the case before execution,
guarding every settlement/close and always attempting browser close. Four
synthetic lifecycle checks pass, including absent contexts API and settlement,
context-close and browser-close failures. The corrected diagnostic uses an
execution bound of 180 seconds excluding build. Reader-only comparison is allowed
once only if the prefix produces fully audited target RED. The temporary harness
is outside the repository and will be removed after use.

Corrected result: REPRODUCED in 138.56 seconds, Chromium 149.0.7827.55. The exact
prefix completes with one React 418/HTML and zero unrelated console/external/
unexpected-page errors. At Reader entry (event 63) the page-error count is already
one; Reader exit (event 149) retains that one. Passive event 13 attributes the
error to Dashboard on page ordinal 3, before Reader entry. Next is 15.5.24 and
the workaround marker is false. The two raw-console records after Reader are
the existing declared HTTP-error fixture, not unexpected errors.

The conditional fresh-browser/reset-fixture Reader-only control then completes
without page or other audit errors. Both cases have zero cleanup errors and
stable source/build/shared-state bindings. There are 235 events, no overflow or
observer failure; synthetic runtime and owned build are removed. Input/shared/
dependency hashes remain the same; temporary build:
`1697a828b8a511e2deef00e53407b6f93f00229bc83804c680bf169014d66bb3`.

This is prefix-associated reproduction, not proof that the prefix is necessary
or that the skipped workaround is causal. It admits independent assessment of
an exact-version compatibility counterfactual, not an automatic guard extension.
The original full browser gate remains failed. No product source is changed yet.

Fresh unchanged Frontend suites pass: Articles 73, Tutor 24, References 23 and
Graph 33, total 153. No application or frozen implementation path differs from
HEAD, and `git diff --check` passes. The tracked artifact-path check has no hit.

Original P3-040 CI 34290207866 is now terminal failure, solely Dependency audit;
Product E2E succeeds at 2026-09-09T00:08:51Z. Uploaded artifacts: 0. This is the
old dependency set, not replacement validation.
