# P3-005.2 SBOM Schema Transport Report

Status: **PASS / CLOSED**

Parent docs-only closure `f87ba6b` passes exact-SHA CI `34212438350`, all seven
required jobs including SBOM, three 243-check E2E runs, restart persistence
and zero uploaded artifacts. No pin, validation or acceptance change. Original
HTTP cause remains unknown; historical failure evidence below is unchanged.

## Failure Evidence

At `55ba624951df30c5fe803dcaebb3213185010f1c`, exact-SHA run
[`34205485973`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34205485973),
SBOM job `101993861976`, logs show:

- 2026-09-08 08:37:25 UTC: generation PASS, Backend 40 components, Frontend
  239, combined 281, matching the run commit.
- 08:37:28 UTC: `sbom_validation=BLOCKED reason=CycloneDX schema unavailable:
  HTTPError`; exit code 2, before JSON schema validation.

The original log does not expose an HTTP status, rate limit, response body
or remote cause. Do not infer one. The failure is distinct from the previous
Graph rendering incident. Parent closure remains open.

## Reproduction And Cause

A zero-network command calls production `_schema_validate`, injecting HTTP
503 only for the API and valid digest-pinned bytes for the existing alternate.
It fails immediately in under one second with three primary attempts and zero
alternate attempts. HTTP 503 is a synthetic test condition, not the observed
CI status. The implementation ignores the already-pinned `schema_url`.

Baseline existing security unittest suite: 17 PASS. It lacks transport tests
and is outside ordinary Backend pytest collection, so the revision adds
offline tests under `backend/tests` without changing workflow/test configuration.

## Reviewed Fix

Independent read-only scope/security review approves API, official raw,
eligible raw retry with three explicit attempts total; unchanged pins, TLS,
validator and all acceptance gates. Permanent raw HTTP failure and any digest
mismatch stop immediately. Transport diagnostics are metadata only. Review
identified and addressed the CI test-collection gap. No root cause is claimed
for the external HTTP response itself.

## Validation

- Production-loader regression RED before implementation: the available
  alternate was not used. Initial implementation: 38 PASS in 0.30s, collected by
  the ordinary `backend/tests` pytest path.
- Full Backend: 667 passed, 4 skipped, 4 pre-existing invalid-escape warnings,
  38.19s. No live-source tests were enabled.
- Existing security unittest suite: 17 PASS; workflow pin/permission policy
  PASS (19/19 pins), suppression policy PASS (zero suppressions), secret audit
  PASS (zero credible/reported/suppressed findings).
- Fresh Frontend production build: PASS, Next.js 15.5.21, 11 generated routes;
  no Frontend source/config/lock change.
- Actual unmodified transport/full-validator invocation: PASS; exact lock
  coverage, 40/239/281 components, combined 241026 bytes, zero forbidden values.
  Temporary SBOM and schema directories removed.
- Separate controlled primary-outage probe: API failure is synthetic HTTP
  503, actual pinned official raw response is HTTP 200. Production fallback,
  unchanged digest and real pinned validator all PASS. This is live alternate
  validation, not evidence of the original CI's HTTP cause. Temporary files
  removed; no Article/corpus/private data accessed or saved.
- Policy, workflow, locks, Backend application, Frontend and Product E2E runner
  diff against the baseline: empty.

An initial test harness mocked global `subprocess.run`, accidentally replacing
the builder's Git timestamp read; five setup tests failed before validation.
The correction confines the validator subprocess mock to the loaded security
module. Generated SBOM tests use TemporaryDirectory with teardown assertions;
imports/path are restored. This was a test-isolation error, not a product or
CI failure. It does not waive any negative test.

Final review identified response-cleanup boundaries, then regression coverage
increased to 40 and 42 tests. Error bodies must close without being read;
cleanup exceptions must be terminal and sanitized; a completed wrong-digest
body cannot become fallback-eligible merely because context closure failed;
failed closure cannot leave valid bytes accepted after later exhaustion.
The final focused suite passes 42/42 in 0.34s. The intermediate full Backend
run after the first cleanup change passes 669/4 skipped in 38.38s. Final
post-tightening full Backend: **671 passed, 4 skipped, 4 existing warnings,
38.75s**. The actual final build/validate CLI again passes schema/coverage/size/
artifact gates and removes its TemporaryDirectory. Final independent code/spec
review approves the exact cleanup fixes with no remaining Critical/Important
finding; reviewers did not independently rerun the parent's test executions.

Final staged safety audit: PASS, exactly the 12 allowed Markdown/Python files,
no unstaged/untracked files, no runtime/private artifact, staged bytes equal
working files, protected paths unchanged, zero credible/reported/suppressed
secret findings. The global artifact-path scan matches only the unchanged
`.env.example` template. New exact-SHA CI: PENDING. Baseline CI completed with
only SBOM failed; other six required jobs pass, Product E2E 3 x 243, restart
PASS, zero unexpected/external errors and zero uploaded artifacts.

## Impact And Risks

This is a security-tool availability repair only. It is not a product, Graph,
provider, API, schema-pin or workflow change. Both official transports remain
external dependencies; if neither is usable the gate still blocks. Retry is
bounded but not a global time/redirect bound. Full validator execution is still
required, and its existing runtime dependencies can also be unavailable.
No secret/runtime artifacts are intended for commit or publication.

## Exact-SHA Implementation CI

- Commit: `73329956a6a69cf738e42f571df8b924aacf3deb`, non-force pushed to main.
- Run: [`34208984649`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34208984649),
  terminal SUCCESS, exact head SHA verified. Backend, Frontend, Product E2E,
  workflow, dependency, secret and SBOM jobs all PASS. Docker and release
  evidence correctly SKIPPED for normal main push.
- SBOM job `102005189995`: full schema/coverage validation PASS, combined
  241026 bytes, zero forbidden values. This CI uses the healthy API path;
  actual alternate access was separately validated locally under a synthetic
  primary outage. Do not claim the original remote HTTP cause was reproduced.
- Backend job `102005190218`: 667 passed, 8 skipped, 4 warnings, 84.04s.
  The eight skip positions were mapped against all 675 collected tests:
  four existing opt-in live/PDF cases and four existing local Node-renderer
  cases. Backend CI does not install Frontend node_modules; those four cases
  pass locally. All 42 new schema regressions ran; no new skip rule was added.
- Product E2E job `102005190265`: Chromium 149.0.7827.55, 3/3 complete runs,
  243/243 checks each; bookmark/completed-state/ended-session/note restart PASS;
  unexpected console/page errors, external requests and static-chunk
  cancellations zero. Full log JSON was parsed in memory, not saved.
- Uploaded artifacts: zero by run artifact API. Local main/cached origin/main
  and live remote main match; worktree clean.
- The observer and one log fetch encountered TLS timeouts. Re-reading the
  same run/job confirmed progress and terminal success; no workflow rerun.

Resume the independently reviewed parent docs-only closure. This report does
not claim that unexecuted closure CI is already PASS. The historical schema
failure remains FAILED and the unrelated Graph incident remains OPEN.
