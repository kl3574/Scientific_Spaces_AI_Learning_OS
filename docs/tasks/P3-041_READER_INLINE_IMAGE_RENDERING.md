# P3-041 Reader Inline Image Rendering

Status: PASS / CLOSED

Closure: dc7411c73802df1255376996c6daf5810f2a87a9, exact-SHA main CI
34332407397 completed SUCCESS at 2026-09-09T09:50:41Z. All seven required
jobs pass; original 3 x 298/restart and separate image 3 x 8 PASS, clean audits
and zero uploaded artifacts. Docker/release jobs are skipped. The publication
pending statements below are historical checkpoints, not current status.

## Objective And Entry Evidence

Render valid embedded Reader images through the actual Markdown pipeline while
preserving the local-first image and link policy. Do not silently discard a
valid inline PNG before the existing image component receives it.

Entry main and origin/main are 0a203bae2f99e3c2b3223823e7d91437bc27e96a.
Its exact-SHA main CI 34314910981 is completed SUCCESS on 2026-09-09:
all seven required jobs pass, Product E2E is 3 x 298 with restart persistence,
and uploaded artifacts are zero. Docker/release jobs are policy-skipped.
The prior security/isolation/ancestry/bootstrap and P3-040 gates can close.
P3-039 remains OPEN / DEFERRED, historical cause UNKNOWN.

An independently approved owned browser diagnosis on unchanged production
qualifies RED on desktop and mobile. Identical valid 2x2 PNG bytes decode in a
control page; the loaded Reader instead has zero matching images and one
matching unavailable badge. The actual API input and remote placeholder are
correct. Audits are clean, source/fixture bindings stable and cleanup complete.
An installed ReactMarkdown regression independently observes source length
0 instead of 150. Exact-fixture img.src admission alone preserves the source in
an in-memory counterfactual. This is not a claim about all data/blob formats.

The owner authorizes independent review followed by automatic bounded execution.
Both the prospective scope and diagnostic qualification are approved. Prior CI
success satisfies the execution prerequisite; no generic confirmation is needed.

Current local gates pass: Backend 929/4 skipped, Frontend 169, lifecycle contracts
121, production build, original Product E2E 3 x 298 and four restart checks, then
separate image profile 3 x 8. Audits and cleanup pass; independent executable and
scope reviews have no Critical/Important finding. The report preserves earlier
failures and exact receipts. Publication CI still precedes closure.

## Allowed Paths

These fourteen paths are the implementation, offline test and current-governance scope:

- frontend/src/lib/readerImagePolicy.ts
- frontend/src/components/ArticleDetailView.tsx
- frontend/tests/readerImagePolicy.test.mjs
- frontend/scripts/test-articles.sh
- scripts/e2e/run_product_e2e.py
- backend/tests/test_graph_provenance_return.py
- README.md
- alignment.md
- docs/00_PROJECT_STATE.md
- docs/tasks/CURRENT_TASK.md
- roadmap.md
- docs/V1_2_ROADMAP.md
- docs/tasks/P3-041_READER_INLINE_IMAGE_RENDERING.md
- docs/P3_041_READER_INLINE_IMAGE_RENDERING_REPORT.md

These ten additional paths permit status/closure evidence only, not changes to
their requirements, implementation scope or historical failure records:

- docs/tasks/P3-005.3_DEPENDENCY_SECURITY_REPAIR.md
- docs/P3_005_3_DEPENDENCY_SECURITY_REPAIR_REPORT.md
- docs/tasks/P3-005.4_PRODUCT_TEST_RUNTIME_ISOLATION.md
- docs/P3_005_4_PRODUCT_TEST_RUNTIME_ISOLATION_REPORT.md
- docs/tasks/P3-005.5_NPM_DEPENDENCY_ANCESTRY.md
- docs/P3_005_5_NPM_DEPENDENCY_ANCESTRY_REPORT.md
- docs/tasks/P3-024.1_BOOTSTRAP_HYDRATION_COMPATIBILITY.md
- docs/P3_024_1_BOOTSTRAP_HYDRATION_COMPATIBILITY_REPORT.md
- docs/tasks/P3-040_EXPANDED_PROVENANCE_RETURN_CONTINUITY.md
- docs/P3_040_EXPANDED_PROVENANCE_RETURN_CONTINUITY_REPORT.md

Total allowed repository paths: 24. Temporary diagnostic/build/runtime files
may exist only in owned temporary directories and must be removed. Preserve
and exclude scripts/e2e/graph_frame_oracle.js, SHA-256
21b548fe1a6c7923a016053e94881c955a0a4c92b2d33fe2020fed4c8bbd9b34.

## Image Policy

1. A URL exception applies only to node.tagName=img and key=src. Every other
   URL uses upstream defaultUrlTransform. Never use an identity transform or
   enable inline schemes for links.
2. Admit nonempty canonical base64 raster data URLs for PNG, JPEG, GIF, WebP
   and AVIF. Define alphabet, padding and unused padding-bit checks explicitly.
   Reject unsupported MIME types/parameters, SVG, HTML and malformed payloads.
   Encoding/MIME admission is not proof that image bytes can decode.
3. Admit only syntactically valid same-origin blob URLs with a trusted browser
   origin. Compare parsed origins; reject opaque/null/missing/cross-origin
   origins. Blob syntax does not establish existence, MIME or lifetime.
4. Use the same validator and origin semantics at URL transformation and image
   rendering. Unsupported inline URLs lead to the unavailable state, never a
   clickable source link. Existing HTTP/relative image placeholders stay intact.
5. Preserve math, outline anchors, reading state, metadata and ordinary links.
   Do not extract/restructure the full Reader component for this repair.

## Execution And Acceptance

1. Add a focused failing regression through installed ReactMarkdown and
   react-dom/server, not just the image helper. Verify the complete PNG source,
   safe blob classification, malformed/non-raster/cross-origin rejection,
   unchanged ordinary links and blocked inline-scheme links.
2. Keep the existing CommonJS test compilation unchanged. Compile the new helper
   separately as ESM in the owned test directory, with a local dependency link
   and failure cleanup. No package installation or dependency change.
3. Wire the reviewed image policy into Reader and replace its permissive
   inline-prefix predicate. Regression tests turn GREEN without waivers.
4. Add small synthetic positive/negative image fixtures in a separate optional
   image runtime before the existing runtime builds every derived store. Keep
   the default Article fixture and every original E2E function/assertion unchanged;
   add native Reader checks for exact source, visibility, completed decoding,
   2x2 natural dimensions, rejected-inline fallback and remote placeholder.
5. Repeat the qualified desktop/mobile user journey on the repaired production
   build. Record the additive negative fixture separately from the original
   RED. Require clean original audits, stable source/fixture/build bindings and
   removal of owned runtime/build/probe resources. No forced DOM image repair.
6. Run all ordinary Backend and Frontend tests, production build, full original
   three-repeat Product E2E and restart persistence. Local tests use the reviewed
   backend 18000/frontend 3000 isolation; do not stop or reuse the user's 8000
   service or modify the shared frontend build.
   After the original repeat-three and original-runtime restart/teardown, run
   three independent desktop/mobile image-profile repeats against the same
   owned build. Keep original `runs[].checks` unchanged and report the image
   profile separately. Overall PASS requires all repeats, strict pre/post-cleanup
   audits, immutable fixture bindings, matching browser versions and cleanup.
   Do not claim the image fixture passed the original 17 ownership scenarios.
7. Run existing security/SBOM/secret/artifact checks and independent final review
   before commit and non-force publication. All seven required exact-SHA main
   CI jobs must pass before closing P3-041. Skipped jobs are not PASS.

Commands include `uv run --offline --project backend --extra dev pytest -q`,
all four existing Frontend test scripts, the production build through the owned
runtime helper, and `SCIENTIFIC_SPACES_E2E_BACKEND_PORT=18000 uv run --offline
--project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode
start`. Use existing security tools without changing their policies.

## Safety And Delivery

No Backend implementation/M1/API/schema, canonical Article content, Graph storage, dependencies,
locks, workflow, source acquisition, image archive, private Zotero, real/paid
provider, tag, Release or destructive Git change. No runtime/private data,
HTML/body/image/PDF/trace exports or secrets are committed. The tiny synthetic
PNG encoded in test source is a fixture, not a downloaded image artifact.
Public existing audit/SBOM services and GitHub publication/CI readback remain
allowed. Unknown drift, unsafe artifacts/secrets, failed gates or necessary
scope expansion stop the affected action for diagnosis, not a blind rerun.

Commit: `fix: render safe inline reader images`. Include the preceding verified
closure receipts with this genuine implementation, not a receipt-only loop.
Formal version remains v1.1.0; candidate none. The broader platform/GUI objective
remains active beyond this repair, including the unresolved P3-039 incident.

## Reviewed Fixture Isolation Amendment

The initial shared-image fixture failed the original full-suite interior-section
precondition, not the stored-progress/DOM-oracle agreement. One reviewed paired
diagnosis on the same build reproduces that exact desktop failure only with the
added image paragraphs; the original fixture completes both display cases.
All audits, source/fixture bindings and cleanup pass. Independent review approves
the bounded test-only isolation above, within the same paths: no product change,
ratio adjustment, original action/threshold change or assertion waiver.

The first isolated-profile Backend rerun exposed two existing CLI resource-mock
incompatibilities. Independent review explicitly adds only the offline test file
above, making 24 paths. Adapt only resource/UI-body mocks while exercising real
profile orchestration; preserve every original lifetime, secret, environment,
signal and cleanup assertion. Add normal and failing image-phase contracts at
8000/18000, including incomplete checks, mismatched browser/fixture, late audit,
body/startup/teardown failure and interruption. Original runtime cleanup must
succeed before starting the image profile. Preserve completed original results
when the image phase fails. No Backend product or isolation-helper edit is added.
