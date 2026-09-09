# P3-034.1 Guided Reader History Focus Report

Status: LOCAL VERIFICATION PASS / PUBLICATION CI PENDING
Reader incident: OPEN / UNKNOWN
P3-042: OPEN / CI BLOCKED

## Evidence And Decision

Published 8e38d035 fails exact-SHA CI 34354525791 at the unchanged guided Reader
hashless Back focus assertion, not the Graph assertion. Backend 1143/8 skipped,
Frontend and four security jobs pass; Product E2E fails. Uploaded artifacts: 0.
The parent P3-042 report records the complete failure and local counter-evidence.

One Reader-helper prefix and one conditional original outer-prefix replay on
unchanged owned production both return valid NOT_REPRODUCED. Their whole-process
stderr and strict pre/post/late audit counts are zero; fixture/source/shared
bindings and owned cleanup pass. These are not a repair or a remote gate PASS.

Independent review approves failure-only evidence at the original checkpoint,
not another local negative replay. The installed Playwright 1.61.0 assertion
uses both activeElement identity and ownerDocument.hasFocus; record these
separately so a background-document state is not confused with the wrong DOM
focus owner. Neither condition has been established for the failed CI run.

## Scope

The canonical twelve-path list permits only test diagnostics and documentation.
The original assertion, timeout, normal path and every audit remain unchanged.
Reader/Shell/ArticleList/Graph and all Backend/API/data/provider code are frozen
for this revision. No Graph replay, source/private/paid access or Release action.
Preserve the excluded frame oracle. No generic confirmation is required.

## Verification

The implemented diagnostic runs only after the original AssertionError. Its
single synchronous DOM projection exports fixed categories, strict booleans and
finite/null geometry. Unknown output and capture/serialization failures produce
a constant unavailable note. A 1536-byte UTF-8 limit bounds output. Annotation
failure still re-raises the same original assertion; success does not capture.

Current local evidence on 2026-09-09:

- Focused contracts: 37 PASS, including the actual assertion-wrapper AST and
  actual JavaScript projection in a fake DOM. The initial 31 cases failed before
  implementation and passed afterward; six additional cases then passed.
- Backend: `uv run --offline --project backend --extra dev pytest -q` exits 0:
  1184 passed, 4 skipped, 592 existing escape-sequence warnings in 67.37 seconds.
- Frontend: test:articles 83 + 15, test:references 23, test:tutor 24 and
  test:graph 34 pass; total 179. These do not substitute for browser acceptance.
- AST equivalence: removing the new import/helper and unwrapping the precise
  assertion restores the original runner AST. Of 136 original top-level
  functions, 135 are unchanged; only the Reader focus helper is wrapped and one
  diagnostic function is added.
- Independent concrete code review: C0 / I0, suitable for the full browser
  gate. Scope review: C0 / I1 on overclaiming the failed CI's active element;
  the parent report now records both active element and document focus UNKNOWN.

The canonical full browser command now exits 0 with complete JSON output:

`SCIENTIFIC_SPACES_E2E_BACKEND_PORT=18000 uv run --offline --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start`

- Owned production build: PASS; Chromium 149.0.7827.55.
- Original Product E2E: 3/3 complete runs, 298/298 checks each, including the
  original guided Reader history focus assertion. All three have zero console
  errors, page errors and external requests. This is NOT_REPRODUCED, not a fix.
- Restart persistence: PASS for bookmark, completed states, ended sessions and note.
- Reader image profile: 3 x 8 checks PASS; zero unexpected errors or external
  requests; fixture stable and runtime removed.
- Native Article navigation: ten desktop/mobile cases, 36 checks PASS; pre/post
  cleanup audits all zero, errors empty, fixtures/bindings stable, runtime removed.
- Actual component contract: three current-code cases PASS. The three deliberate
  mutants fail with stale_success_read, stale_failure_read and
  replacement_fetch_missing respectively. These expected negative controls make
  the six-case profile PASS; they are not ignored product failures. Audits are
  zero, errors empty, bindings stable and runtime removed.
- Whole-process output parses as the complete receipt, without extra driver
  exception output. Owned copy verification, shared-state stability and cleanup
  all pass. No source/private/paid request or product change occurred.

Bindings:

- Runner: `800dc6cb0cd553d26859c4263e42f32f39ef713c86ad8987fe42458e74d36edb`.
- Diagnostic tests: `7b75a0be15045fd8117afb4cc9bb5c42a38a25f547b47949b89a304c07e6dd92`.
- Owned build: `bef351192f0e9b8c034e0aab705f9520e46bf40b646feca58374c1255da0a1cb`.
- Inputs: `e07a277c340108eb4a9b0dd11410b020dae0eb11b1714271dcd3d84c44f428b0`.
- Dependencies: `bc742ff3249a71f08f150a9ca5b2e94896c6bf73e18a5519e04b814ed4a5ab49`.
- Shared build: `b39eae0a13944cf6515c4b7a486e9cd877db58726b199fb9597999f90b617812`.

Workflow policy and suppression checks pass; secret audit reports credible=0,
reported=0, suppressed=0. Candidate scope is exactly twelve paths; protected
product/dependency/workflow paths are unchanged and the excluded oracle retains
its canonical hash. Final independent code/evidence and scope/spec reviews both
report C0 / I0 and authorize the exact twelve-path publication after final staged
safety checks. The owned ports are released and a fresh AST equivalence check
passes. One substantive diagnostic commit/non-force push and all seven required
exact-SHA CI jobs follow; remote acceptance is not yet claimed.

Reader cause remains UNKNOWN even if diagnostic CI passes; P3-042 is not
automatically closed. Preserve failed CI 34354525791. Do not repeat negative
prefixes, waive the original assertion or start the deferred Graph replay.
