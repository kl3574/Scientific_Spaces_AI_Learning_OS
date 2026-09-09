# P3-005.3 Dependency Security Repair Report

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

Current evidence: the independently reviewed P3-024.1 exact Next rebind passes
the matched prefix with no unexpected errors, stable bindings and cleanup.
Predefined stress passes 1400/1400 loads; original provenance cases pass 7/7;
complete Product E2E passes 3 x 298 checks and restart persistence. All original
unexpected-error/external-request audits pass. The P3-005.5 nearest-ancestor repair passes independent review, all 30
security tests and full SBOM validation. Current Backend is 891 passed / 4 skipped
(45.86 seconds); Frontend is 154 passed. Workflow, suppression and secret gates
pass with zero findings. These supersede only the older pending local snapshots
below, not the failed original CI or the remaining publication gates. The exact
28-path integration still requires final receipt review and replacement main CI.
Owned diagnostic scripts, production builds and synthetic runtimes are removed;
the user's existing backend and excluded frame-oracle draft remain untouched.
The complete fresh receipts are in the P3-024.1 compatibility report.

Active prerequisite: independently reviewed P3-005.4 backend-port isolation,
recorded in docs/P3_005_4_PRODUCT_TEST_RUNTIME_ISOLATION_REPORT.md. This is an
explicit test-only revision, not a waiver of the seven-case/full browser gates.

## Failure And Classification

Classification: REAL_DEPENDENCY_VULNERABILITY. At
fee813b96c6940840bfab73185e9e77e3e594e34, [CI 34290207866](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34290207866)
job 102274840215 exits 1: eight findings, eight blocked, zero suppressed.
The local unmodified `python scripts/security/run_dependency_audit.py` reproduces
the same eight findings and counts on 2026-09-09 (PyPI 40 / npm 239, exit 1).
Python findings come from pip-audit/OSV; npm findings from npm-audit/OSV.
Scanner UNKNOWN severity remains blocking, not downgraded. This establishes a
vulnerable inventory, not a demonstrated exploit of the running platform. No
exploit, source-site or private-data probe was performed.

## Verified Fix Selection

Upstream advisories and exact public registry metadata were read on 2026-09-09.

| Locked package | Finding | Minimum fixed | Selected |
| --- | --- | --- | --- |
| next 15.5.21 | [GHSA-2xp9-vwfh-vxw4](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4) | 15.5.24 | 15.5.24 |
| next 15.5.21 | [GHSA-p293-qw3h-jr36](https://github.com/vercel/next.js/security/advisories/GHSA-p293-qw3h-jr36) | 15.5.24 | 15.5.24 |
| sharp 0.35.0 | [GHSA-rgj7-g3m4-5g8c](https://github.com/lovell/sharp/security/advisories/GHSA-rgj7-g3m4-5g8c) | 0.35.4 | 0.35.4 |
| httpx2 2.5.0 | [CVE-2026-84378](https://github.com/pydantic/httpx2/security/advisories/GHSA-f2fp-rgf2-35cp) | 2.10.0 | 2.12.0 |
| httpx2 2.5.0 | [CVE-2026-84379](https://github.com/pydantic/httpx2/security/advisories/GHSA-h4x7-gw46-3wm6) | 2.11.0 | 2.12.0 |
| httpx2 2.5.0 | [CVE-2026-84380](https://github.com/pydantic/httpx2/security/advisories/GHSA-pf96-p4fj-6566) | 2.11.0 | 2.12.0 |
| httpcore2 2.5.0 | [CVE-2026-84381](https://github.com/pydantic/httpx2/security/advisories/GHSA-7mj9-2mp8-4m2p) | 2.10.0 | 2.12.0 |
| httpx2 2.5.0 | [CVE-2026-84382](https://github.com/pydantic/httpx2/security/advisories/GHSA-8xx6-hgc6-gc2m) | 2.12.0 | 2.12.0 |

Registry HTTP 200 for [Next](https://registry.npmjs.org/next/15.5.24),
[Sharp](https://registry.npmjs.org/sharp/0.35.4),
[HTTPX2](https://pypi.org/pypi/httpx2/2.12.0/json) and
[HTTPCore2](https://pypi.org/pypi/httpcore2/2.12.0/json).
Both Python releases are non-yanked and support Python 3.11. Next supports
existing React 19/Node 22 and its Sharp range admits 0.35.4. Sharp requires Node
>=20.9.0; retain the precise security override.

Installed Starlette 1.3.1 TestClient preferentially imports HTTPX2. Removing it
would switch existing tests to a deprecated HTTPX fallback, not repair their
dependency. HTTPX2 2.12.0 requires HTTPCore2 exactly 2.12.0; existing AnyIO
4.14.1, IDNA 3.18 and truststore 0.10.4 satisfy its other requirements.
Independent scope review approves upgrading the pair rather than removal.

## Verification

- Independent initial scope review: APPROVED, 12-path candidate; the necessary
  SBOM generator/test amendment below extends this to exactly 14 paths.
- Local pre-update audit: RED reproduced, eight findings/blocked, zero suppressed.
- Targeted Python lock update changes only HTTPX2/HTTPCore2 to 2.12.0.
- Next/Sharp lock update also requires @emnapi/runtime 1.11.3 for Sharp WASM.
  The other six added entries materialize existing Tailwind bundle metadata.
- Independent lock review permits exactly those six records after provenance
  verification. Locked installation and image compatibility now pass as below.
- Full Backend before isolation: 770 passed / 4 skipped, six existing warnings,
  40.28 seconds. Final combined candidate: 891 passed / 4 skipped, 76 warnings,
  44.60 seconds; the warnings are two pre-existing runner string escapes.
- Frontend: Articles 73, Tutor 24, References 23, Graph 33; total 153 PASS.
- Production build: PASS, Next 15.5.24, 11 generated static pages, 13.35 seconds.
- Two complete post-update dependency audits: PASS, each PyPI 40 / npm 245,
  findings 0 / blocked 0 / suppressed 0. Original scanners remain operational.
- Security unit tests: 24 PASS, including nine SBOM tests (seven additive).
- Workflow policy: PASS, 1 workflow / 19 actions, pin and permission rates 1.000.
- Suppression validation: PASS, dependency 0 / secret 0.
- Secret audit: PASS, credible 0 / reported 0 / suppressed 0.
- Original full SBOM schema and coverage validation: PASS, forbidden 0.
- Seven-case E2E on new dependencies with the independently reviewed P3-005.4
  isolation: 7/7 PASS, audit clean, source/build/fixture unchanged and runtime
  removed. Full repeat-three exits 1 with React hydration error 418 before any
  completed iteration; restart persistence is not reached. The P3-005.4 report
  records exact evidence and the version-bound bootstrap compatibility candidate.
  No completion is inferred from the old dependency set.
- Independent generator/test review: 0 Critical / 0 Important. Full final
  publication review remains after the browser gates.
- Replacement commit and exact-SHA CI: pending.

P3-040 local results validate the original dependency set, not this update. Its
original CI is now terminal FAILURE solely from Dependency audit. Product E2E
passes 3 x 298 checks and restart persistence, with zero unexpected/external
errors and uploaded artifacts. No CI restart or waiver. P3-039 OPEN / DEFERRED.

## Bundled Metadata Provenance

Final independent security review reports a new Important graph-fidelity issue.
The master independently reproduces it in memory: bundled
`@napi-rs/wasm-runtime@1.0.7` resolves its `@emnapi/runtime` edge to root 1.11.3,
instead of the nearest ancestor's bundled 1.6.0. All 245 lock records remain
present; component/schema counts do not prove correct dependency edges.
The current parser checks only a direct child and then picks the globally
shallowest matching name. This is a cross-platform SBOM graph defect, not proof
of an incorrect dependency loaded on this host. The parser is outside the
existing 21-path scope; no parser fix has yet been made. A separate bounded
ancestry-resolution revision is under independent scope review. Publication
remains held for this finding and the genuine browser failure.

An owned empty temporary directory seeded only with the changed manifest and
HEAD lock reproduces the same 45 changed package records, including six bundled
records. No candidate was adopted from that diagnostic and the directory was
removed. This rules out a warm node_modules-only explanation.

The unchanged @tailwindcss/oxide-wasm32-wasi 4.1.17 public tarball (1,677,138
bytes) was read in memory, matched against the existing SHA-512 integrity, and
its six package manifests were inspected without extraction or file writes:

| Bundled package | Version |
| --- | --- |
| @emnapi/core | 1.6.0 |
| @emnapi/runtime | 1.6.0 |
| @emnapi/wasi-threads | 1.1.0 |
| @napi-rs/wasm-runtime | 1.0.7 |
| @tybys/wasm-util | 0.10.1 |
| tslib | 2.8.1 |

All names/versions match the generated inBundle records. Parent version and
tarball integrity are unchanged. Inventory increases npm 239 to 245; no record
is omitted from auditing. First post-update complete dependency audit: PASS,
PyPI 40 / npm 245, zero findings/blocked/suppressed. This does not imply SBOM,
installation, browser or CI completion.

## SBOM Duplicate-Identity Revision

The original temporary CLI build succeeds (Backend 40, Frontend 245, combined
286), but the unchanged validator exits 2 with `duplicate SBOM bom-ref:
pkg:npm/tslib@2.8.1`. Temporary files are removed. This is a real failing gate,
not permission to prune the already-bundled inventory.

Root cause: ecosystem generation emits a component/dependency entry for every
installation occurrence, while the existing bom_ref identifies package/version.
Independent review approves only build_sbom.py and tests/test_sbom.py as a
necessary amendment. Normalize identical identities, union dependencies, retain
runtime precedence and all available hashes, reject conflicts and preserve
different versions. Validator, policy, scanner and combined-builder contracts
remain unchanged.

Regression RED: the original build_all structural validation rejects duplicate
tslib; the new aggregation test sees two components instead of one. GREEN:
all nine SBOM tests and 24 total security tests pass. Regressions cover occurrence
order, runtime precedence, merged edges, hash retention/conflicts, identity
conflicts, distinct versions/ecosystems and current-lock combined-BOM retention.
Duplicate-free fixture output retains the exact pre-change canonical SHA-256:
`9ea30ccb9e04599d75efc8f4647d972459cefdb0475ea519fd1a1772f4b71145`.

Original CLI generation and full unchanged validator pass in an owned temporary
directory, removed afterward. Components: Backend 40 / Frontend 244 / combined
286; dependency entries: 41 / 245 / 287. The npm audit still inventories all 245
installation records. Aggregation removes no package version or available hash.
Combined output is 244,278 bytes; schema, both lock coverages and forbidden
artifact checks pass. No validator, lock-parser, combined-builder or policy edit.

## Locked Installation And Image Compatibility

`uv sync --project backend --extra dev --locked` exits 0 and updates only the
HTTPX2/HTTPCore2 pair. The CI-equivalent local npm 10.9.8 invocation
`npm --prefix frontend ci --no-audit --no-fund` exits 0; the owned npm execution
and child logs both record successful termination. Global npm remains unchanged.
Lockfile SHA-256 values before and after installation are identical:

- backend/uv.lock: `4f3fcb2e518ad412fd33e7a2618d6d39db7e65e8e8df62f101c70c7ce0e633ff`
- frontend/package-lock.json: `cd63f56a809437eb0658442641af6a75591e7462deafa61e679b99b1242f875b`

The in-memory compatibility probe verifies Sharp 0.35.4 PNG resize and Next
15.5.24 optimization from a synthetic 16x12 PNG to 8x6 PNG, WebP, JPEG and AVIF.
An independent fresh Sharp child decodes each output: 105 / 58 / 323 / 284 bytes.
No image file or network request is produced.

Retained initial diagnostic failure: decoding Next's AVIF output through the
same Sharp instance raises unsupported-image-format. Installed Next getSharp
explicitly blocks HEIF input, consistent with the linked upstream AVIF security
advisory. This is not a corrupt-output finding: the independent decoder succeeds.
The corrected diagnostic also asserts that Next rejects AVIF input. No loader
is unblocked and no installed package/application code is changed. AVIF input
optimization remains an upstream security limitation, not general image support.

## Browser Environment Gate

The unchanged seven-case command exits 2 at server_setup before any case executes.
It reports audit PASS, all error/external counts 0, unchanged source/build/fixture
bindings and runtime_removed=true. Port 8000 is occupied by an existing backend
in a user-terminal scope, not a test-owned process. It was neither stopped nor
reused, and its runtime data was not read. Port 3000 is free at this observation.

An isolated user/network namespace availability check fails with UID-map
Operation not permitted. No privilege or host-policy bypass was attempted.
The owner was asked only to release the occupied test port, not to reconfirm the
task plan. Full repeat-three E2E has not started on the changed dependencies.
Once the port is available, run both unchanged browser gates; retain all current
assertions, strict audits, build bindings and runtime cleanup requirements.

No repair commit or push is allowed until those local gates and final review pass.
P3-040 remains open; the original CI failure is not waived. The broader platform
and GUI improvement goal remains active.
