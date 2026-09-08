# P3-037 Tutor Citation Continuity Report

Status: OPEN / IMPLEMENTATION CI PENDING

## Baseline And Cause

Baseline f87ba6b is the verified P3-036 docs-only closure. Exact-SHA CI
34212438350 passes all seven required jobs and three complete 243-check E2E
runs, with restart persistence and zero uploaded artifacts. No current REWORK,
audit failure or pre-existing worktree modification was found. Historical
Graph visibility remains a separate OPEN / UNRESOLVED incident.

Tutor stores live answers, context and Quiz results in the mounted workspace.
The source list uses a same-tab Next Link, and Markdown only assigns a new
tab to lowercase HTTP(S) links. Source inspection therefore unmounts the
workspace; Back cannot restore that component state. The earlier four-case
rendered reproduction and 22-case native-anchor prototype are recorded in
P3-036 report sections 20 and 22, not treated as compiled-fix validation.

Fresh baseline Chromium admission probe: four exact accepted hrefs (relative,
lowercase HTTP, mixed-case HTTP and hash), four rejected non-links, metadata
ID precedence and chunk fallback PASS. Relative and mixed-case citations
have no target; lowercase HTTP alone has target=_blank. No external requests
or unexpected errors; all temporary runtime data removed.

The compiled-component regression goes RED on the first valid local source:
expected target=_blank, actual None. Its initial draft first failed a test
locator that incorrectly treated the answer article as parent of its sibling
source sidebar. The locator was corrected before recording the product RED.
No product accessibility/DOM defect is inferred from that test-authoring error.

## Reviewed Repair

Only TutorSourceList and TutorMarkdown product code changes. Native document
links use _blank, noopener noreferrer and a visible accessible new-tab cue.
Existing href admission/encoding stays unchanged; hashes and intentional
Article/Concept Returns remain same-tab. No new persisted state or Provider.

Independent design review requires Article and public Concept origins,
submitted nontrivial Quiz state, a different destination Article, exact URL
and source preservation, and before/during/after state comparisons. Separate
test review identified three gaps, addressed before persisting the helper:
unowned session-end writes now fail closed, ordered source cards/links are
snapshotted, and inherited fieldset disabledness uses :disabled.

## Validation

- Focused Frontend: 143/143 PASS (Tutor 24, Articles 67, References 23,
  Graph 29), including two new admission-boundary tests.
- Fresh production build: PASS, Next.js 15.5.21, 11 generated routes.
- Compiled rendered continuity: 34/34 scenarios plus four hash-activation
  checks PASS (38 checks). All 24 two-origin/core cases, six other-mode cases
  and four constrained layouts pass. Actual source cards, Graph/Concept
  context and submitted 1/2 Quiz work match before, while the Reader child
  exists, and after it closes. Hrefs/destinations, null opener, one child,
  retained focus and unchanged canonical Reader-session readback pass.
  Extra Tutor POSTs, external requests, unexpected pages/errors: 0.
- Visual inspection: 1440x1000 Explain, 390x844 Quiz, 320x844 Explain and
  720x450 Quiz. Cues/readable source buttons and keyboard outlines are visible
  without horizontal overflow. Four supplemental interaction checks pass;
  all four temporary screenshots, owned servers and fixture stores removed.
- Backend: 671 passed, 4 skipped, 4 pre-existing invalid-escape warnings,
  38.41s. No new warning or live test was enabled.
- Security unittest: 17 PASS. Workflow 19/19 pins and explicit permissions,
  zero suppressions, zero credible/reported/suppressed secrets, dependency
  audit 40 Python / 239 npm packages and zero findings: PASS.
- Temporary full SBOM validation: schema and lock coverage PASS, combined
  241026 bytes, forbidden values 0. Generated files removed. Its metadata
  identifies baseline HEAD f87ba6b; final implementation CI is still required.
- Full three-run Product E2E: PASS, exit 0, 1955.73s. Chromium
  149.0.7827.55 completes all three runs with 281/281 checks each, including
  38 Tutor citation checks per run. Console errors, page errors, external
  requests and static-chunk cancellations: 0. Restart bookmark, completed
  states, exactly-25-ended-session and note persistence checks: PASS.
  The terminal tool result was recovered from its execution record at
  2026-09-08T11:13:54.708Z after the session handle had closed; no test was
  restarted because of the truncated observation. Its final script blob is
  7c71ac2eeaef57b5989d0a504b80f0fcf098bcd7, unchanged at readback.
- Two independent final reviews found no Critical/Important issue and the
  same minor coverage gap: Return-link attributes were not in the shared
  continuity snapshot. Raw href/target/rel and link text are now captured.
  The earlier full invocation was deliberately interrupted (SIGINT, exit -2)
  while still running, so the final test version could be verified. It is
  CANCELLED / SUPERSEDED, not a product failure or PASS; its shutdown
  TargetClosedError is not evidence of a GUI defect. Owned runtime cleanup
  completed. The new full invocation uses script blob
  7c71ac2eeaef57b5989d0a504b80f0fcf098bcd7. No blind CI rerun occurred.
- Both independent reviewers re-read that exact snapshot correction and
  approve with 0 Critical / 0 Important / 0 Minor remaining. Their reviews
  are read-only code/spec checks; runtime results were supplied by the parent
  executions, not independently rerun by those reviewers.
- Final documentation review found stale secondary task/status instructions.
  Current pointers now agree; retained older instructions are explicitly
  historical. Its correction readback approves with zero remaining findings.
- Pre-commit audit: 17 allowlisted paths, two new Markdown documents only;
  protected product/data/dependency/workflow paths unchanged. Existing three
  bounded fixture HTML files are unchanged, not new downloads. Secret scan
  (including untracked/staged documents), suppression policy, workflow policy
  and diff whitespace checks PASS. Fresh remote main equals baseline f87ba6b;
  published v1.0.0 and v1.1.0 object/peeled refs remain unchanged.
- Implementation exact-SHA CI and separate docs-only closure CI: pending.
  This is not a completed or shipped task.

## Boundaries And Risks

Native separate-tab behavior preserves a live originating tab only. Refresh,
eviction, closing that tab and physical-mobile popup policy are not covered.
External citations are inspected, not activated. Reader-session fixtures are
local to the new browser cases, with canonical-store readback unchanged; the
existing exactly-25-ended-sessions restart assertion is not adjusted.

No Backend, frozen M1, API, schema, data/corpus, provider, dependency, lockfile,
workflow, release, candidate or tag changes are part of this work.
