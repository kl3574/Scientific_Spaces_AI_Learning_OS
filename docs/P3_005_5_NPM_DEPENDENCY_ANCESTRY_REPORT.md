# P3-005.5 Npm Dependency Ancestry Report

Status: LOCAL VERIFICATION PASS / INTEGRATION CI PENDING

Current parent gate: P3-024.1 now passes its matched prefix, 1400-load stress,
seven provenance cases, three complete 298-check E2E runs and restart
persistence. Backend 891/4 skipped, Frontend 154, security 30/29 subtests,
two full dependency audits and original full SBOM validation pass. Historical
browser failures below remain recorded, not current unresolved local gates.
Final receipt review and exact-SHA integration CI are still required.

## Reproduction

On 2026-09-09, independent review and the master's separate read-only parser call
both observe the same wrong edge. The locked importer is
`node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@napi-rs/wasm-runtime`
at 1.0.7. Its `@emnapi/runtime` dependency currently points to root 1.11.3 rather
than the nearest ancestor's bundled 1.6.0. All 245 lock records are retained.

The parser checks a direct child then chooses the globally shallowest matching
name, bypassing intervening legal ancestors. The generator preserves that
incorrect edge. Component-set/schema coverage alone does not detect it.
This is a cross-platform inventory-graph defect, not evidence that the current
host installed or executed the wrong WASM dependency.

## Independent Scope Decision

APPROVED: npm resolver only, existing SBOM test path, this report and its canonical
task, plus current governance pointers. Combined candidate: 24 paths. Required
dependencies fail closed; optional omissions follow legal reachability and never
remove inventory. No security policy, scanner, UV parser or product change.

## Verification

The implementing agent reports witnessed RED/GREEN: seven initial failing
subcases for ancestry/required resolution, followed by two optional-reachability
failures before completing that repair. Its final security suite passes 30 tests,
including 15 SBOM tests and six new test methods with parameterized subcases.
The master independently reruns the complete security suite: 30 passed,
29 subtests passed in 0.17 seconds. Final independent review is still required.

Only npm resolution changes. PurePosixPath walks legal ancestors, skips repeated
node_modules/node_modules, includes scoped-package ancestors and stops at the
relative lock root. Unresolved ordinary required edges raise SecurityToolError;
the existing optional allowances now use legal reachability. UV behavior,
security policies, dependency locks and product code are unchanged.

Agent comparison reports exactly one current-lock edge correction: bundled
wasm-runtime 1.0.7 now uses emnapi runtime 1.6.0; the Sharp WASM root consumer
still uses 1.11.3. All 245 inventory records and their identity/version/hash/scope
fingerprint remain unchanged:
`c60f9a470c9f2782f2843d1078a3f764ed781bf7ace717ab79adf388bfbd907d`.
Frontend has 244 components/245 dependency entries; combined has 286/287.
Component fingerprints and the Backend BOM are unchanged. The master compares
the current parser to the HEAD parser against the identical current lock in
memory: all 245 identity/version/hash/scope records and root metadata match,
with exactly the one expected edge change.

Final ordinary Backend: 891 passed, 4 skipped, 76 pre-existing runner-escape
warnings, 46.80 seconds. Original build_sbom.py and validate_sbom.py CLIs both
exit 0: full schema and all coverage checks PASS, combined bytes 244277,
forbidden count 0. Corrected edges appear in frontend and combined artifacts;
the owned temporary output directory is removed. BOM hashes at current HEAD:

- Backend: `6ecf5cc2acc2185bc47777186b2c19bd48edf74a1050b849b838326bf5d00856`
- Frontend: `473f2df6fde7062097d0e0316a318088366d212a098ae31cd010aca1ac1cd131`
- Combined: `d0df4905bc43954d36b69d8dd9058e775ec7f0cf640559cde768e7a5a5672d2e`

Both complete unchanged dependency audits now pass: PyPI 40, npm 245, findings 0,
blocked 0, suppressed 0 on each run. Secret audit also passes with credible,
reported and suppressed counts all 0. Independent final code review: C0/I0 PASS.
These are local worktree artifacts; any later commit requires fresh commit
binding. This revision's local gates pass, but parent browser/publication gates
remain unsatisfied and no closure is claimed.

Full browser verification remains separately blocked by React 418. The negative
focused replay is not a repair. No commit, push, tag or Release has been made.
