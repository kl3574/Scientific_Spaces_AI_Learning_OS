# Scientific Spaces AI Learning OS v1.2 Roadmap

Status: P3-004 and P3-005 are PASS / CLOSED; P3-006 is CONDITIONAL / RISK ACCEPTED / CLOSED with all machine gates passing and its dependency-audit repair PASS / CLOSED; P3-006.1's remaining 61 cases are WAIVED / PAUSED; P3-006.2 and P3-006.3 are PASS / CLOSED; P3-007 is CONDITIONAL / RISK ACCEPTED / CLOSED with exact-implementation main and manual Docker CI passing; P3-009 is PASS / CLOSED for the canonical 1,311-Article corpus and private Zotero PDF synchronization; M1.4 incremental Article/PDF/Zotero synchronization is PASS / CLOSED at 1,314 Articles; P3-010 derived asset refresh is PASS / CLOSED at the same 1,314-Article fingerprint; P3-011, P3-012, P3-013, P3-014, and P3-015 product convergence tasks are PASS / CLOSED with exact-SHA main CI passing; no candidate version or subsequent task is assigned.

Scope Decision: **A - Structured References, opt-in Real Provider Evaluation, and CI Security/Release Provenance**

## Executive Summary

v1.2 will improve scientific provenance and release trust without changing the local-first default. The approved planning scope is:

- Main theme: structured reference extraction and Zotero linking.
- Data-quality/evaluation theme: opt-in real-provider evaluation harness.
- Platform theme: CI security and release provenance.

Graph storage optimization is the strongest deferred engineering candidate, but P3-002 found no blocking performance target; its migration and regression cost make it better suited to v1.3. Remote image archiving is deferred, and multi-user architecture remains v2.0 discovery.

## Evidence Base

- v1.1.0 clean-clone install, runtime, migration, backup, restore, and exact-tag Docker paths passed.
- The completed corpus contains 1,311 valid Articles, but structured `metadata.references` arrays are empty.
- Zotero models already represent DOI and URL metadata, while Article-to-Paper provenance is incomplete.
- Fake-provider evaluation is deterministic and strong, but it does not measure real-provider quality, latency, cost, or failure behavior.
- The full Graph is approximately 75 MB JSON and requires cold deserialization/index construction.
- Remote images are deliberately represented by offline placeholders.
- CI uses mutable major Action tags and has no dependency scan, secret scan, SBOM, or release attestation workflow.
- The product is explicitly local-first and has no auth/authz or multi-user isolation.

## Product Objectives

1. Turn inline scientific references into normalized, provenance-bearing records that can link to Zotero items without changing source meaning.
2. Measure real embedding/chat providers through an explicit, local, opt-in harness while keeping fake providers as the default and CI baseline.
3. Strengthen repository and release supply-chain evidence without adding runtime product dependencies.
4. Preserve v1.0 legacy and `/v1.1` API contracts throughout v1.2 work.

## Non-Goals

- No authentication, authorization, public multi-user deployment, or concurrent-user database architecture.
- No default real provider, paid CI call, committed credential, or provider-specific product lock-in.
- No implicit remote-image download during startup, sync, Reader use, PDF export, or CI.
- No full Graph storage migration in v1.2; a future v1.3 architecture task requires a measured performance requirement and rollback design.
- No change to the frozen M1 source pipeline in ordinary v1.2 work. Any M1 implementation change requires a separate M1.x revision task.
- No claim that reference extraction or Zotero matching proves scientific correctness.

## Evaluated Workstreams

### Real Provider Quality Evaluation

Add explicit embedding/chat provider experiments for cost, latency, errors, citation faithfulness, answer quality, privacy, fallback behavior, and rate limits. Credentials remain local; fake providers remain default; CI never calls paid services.

### Structured Reference Extraction

Extract DOI, arXiv IDs, and URLs from existing `Article.content`; normalize and deduplicate them; preserve exact article/section evidence; and produce candidate Zotero matches with confidence and provenance. Prefer a derived reference store so the frozen M1 parser and Article schema remain untouched.

### Graph Storage and Cold-Start

Replace repeated large-JSON cold loading with indexed/lazy storage, schema migration, bounded queries, integrity checks, and corruption recovery. This requires careful compatibility and rollback work because legacy Graph routes remain frozen.

### Remote Image Local Archive

Offer an explicit opt-in archive with bounded source pressure, checksum verification, attribution, resume/retry, local-path rewriting, and Reader/PDF integration. It must never run from ordinary startup or CI.

### CI and Repository Security

Add dependency and secret scanning, immutable Action pinning, branch-protection guidance, SBOM generation, release provenance, and artifact attestation. Keep generated evidence bounded and avoid shipping private runtime data.

### User Data and Multi-Profile Architecture

Investigate authentication, authorization, profile isolation, database migration, and concurrent writes. This changes the product trust model and belongs to v2.0 discovery rather than v1.2 implementation.

## Prioritization Matrix

Scoring uses:

`Priority Score = (User impact * Evidence strength * Risk reduction * Strategic alignment) - (Implementation effort * Regression risk * Operational cost)`

All dimensions use 1-5 relative engineering scores. They are not economic-value estimates.

| Candidate | User impact | Evidence | Risk reduction | Alignment | Effort | Regression | Ops cost | Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B Structured references | 5 | 5 | 4 | 5 | 3 | 3 | 2 | **482** |
| E CI/security provenance | 4 | 4 | 5 | 5 | 3 | 2 | 2 | **388** |
| A Real-provider evaluation | 4 | 4 | 4 | 4 | 3 | 2 | 4 | **232** |
| C Graph storage/cold-start | 3 | 5 | 4 | 4 | 4 | 4 | 3 | **192** |
| D Remote image archive | 3 | 4 | 2 | 3 | 4 | 3 | 4 | **24** |
| F Multi-profile architecture | 2 | 2 | 4 | 2 | 5 | 5 | 5 | **-93** |

### Score Rationale

- B has direct corpus-wide evidence: 1,311 empty structured reference arrays and an existing Zotero boundary. A derived store limits operational cost, while extraction/matching accuracy creates moderate regression risk.
- E reduces supply-chain risk across every release. Existing CI is compact, so scanning and provenance can be added without product-runtime changes.
- A closes a declared quality gap and reuses the existing harness, but paid calls, privacy review, rate limits, and provider variance raise operational cost.
- C addresses a measured 75 MB cold-load baseline, but storage migration and frozen Graph compatibility make it the riskiest near-term architecture change.
- D improves offline fidelity but adds source pressure, copyright/attribution, storage, retry, and rewrite complexity for a non-core limitation.
- F has high cost and regression exposure while current evidence does not show a multi-user requirement; it changes the trust and deployment model.

## Approved Scope

P3-002 selected Scope Decision A. The three included workstreams have independent, additive boundaries. Approval does not assign `v1.2.0` as a candidate and does not authorize implementation, a real-provider call, private Zotero access, or a full-corpus reference build.

Architecture set:

- `docs/V1_2_PRD.md`
- `docs/V1_2_ARCHITECTURE.md`
- `docs/V1_2_DATA_MODEL.md`
- `docs/V1_2_THREAT_MODEL.md`
- `docs/V1_2_EVALUATION_PLAN.md`
- `docs/V1_2_ACCEPTANCE.md`
- `docs/V1_2_EXECUTION_PLAN.md`
- `docs/ADR/0006-derived-reference-store.md`
- `docs/ADR/0007-real-provider-evaluation-boundary.md`
- `docs/ADR/0008-ci-security-and-release-provenance.md`

### P3-002 Approval Evidence

- Starting `main` and `origin/main`: `fdba4d8759f36704fcc928fff504526d0c5e1781`, ahead/behind `0/0`.
- Published `v1.1.0` peeled target: `3efbe2a792a9853f1bac456f0287c3b5b62713ce`.
- P3-001 main CI run `29179023882`: Backend PASS, Frontend PASS, Docker correctly skipped for a main push.
- P3-002 Backend verification: 469 passed, 3 skipped.
- P3-002 Frontend production build: PASS, static generation 8/8.
- Existing OpenAPI was inspected; no `/v1.2` implementation exists and all named `/v1.2` contracts remain planned.
- Changed-path allowlist, Markdown fence, Git diff, tracked large-file, runtime/private artifact, and bounded known-secret-pattern checks passed. `gitleaks` is unavailable locally, consistent with the recorded security-baseline tooling limitation.
- No product/frozen implementation, real provider, private Zotero library, full corpus, push, tag, or Release operation occurred.

### Main Theme - Structured Reference Extraction and Zotero Linking

- Define a `ReferenceRecord` contract with normalized identifier, source type, article ID, section/evidence, extraction rule version, and provenance.
- Build a deterministic derived index from existing Article content; do not fetch sources and do not mutate M1 during the pilot.
- Normalize DOI, arXiv, and HTTP(S) references with explicit duplicate rules.
- Produce explainable Zotero match candidates; no automatic write to a user's Zotero library.
- Add bounded Article/Paper link APIs only as additive contracts.

### Data-Quality Theme - Real Provider Evaluation Harness

- Add an opt-in, non-CI runner over a curated grounded case set.
- Record provider/model identity, latency, token/cost metadata when available, errors, citation faithfulness, refusal behavior, and answer-quality review fields.
- Redact secrets and response metadata that can expose private configuration.
- Keep fake-provider regression results as the release gate; real-provider results remain comparative evidence, not the default runtime.

### Platform Theme - CI Security and Release Provenance

- Pin third-party Actions to immutable commit SHAs with update policy.
- Add dependency and secret scanning with documented triage rules.
- Generate an SBOM and provenance/attestation for release evidence without bundling runtime data.
- Document branch protection and release signer/attestation verification.

## Architecture Implications

- Reference extraction should be a derived pipeline beside, not inside, frozen M1 acquisition/parser code.
- A versioned reference manifest should bind Article-store fingerprint, extractor version, normalized records, and failure classifications.
- Zotero linking should consume reference records through a small matching interface and preserve candidate confidence/evidence.
- Real-provider evaluation should extend the existing evaluation boundary through provider adapters, explicit opt-in, bounded cases, and aggregate output.
- CI security belongs under workflow/configuration ownership and must not change local fake-provider behavior.
- Graph C remains an isolated future storage adapter proposal; legacy Graph services cannot be rewritten opportunistically.

## Data Migration Implications

- The reference pilot writes a new ignored or explicitly managed derived store and leaves `Article.content` unchanged.
- Repeated extraction over the same Article fingerprint and rule version must be idempotent and byte/deterministically equivalent.
- Every failed or unsupported reference candidate receives a classification; silent drops are not allowed.
- Any later backfill of `metadata.references` requires an explicit, atomic migration and M1.x governance decision.
- Provider evaluation output is aggregate/audit data, not user learning state.
- CI provenance artifacts must exclude corpus, PDF, Graph, RAG, database, backup, and secrets.

## Compatibility Policy

- Preserve legacy Article and Graph response keys, ordering, status codes, and unbounded semantics where frozen.
- Preserve bounded `/v1.1` pagination/filter behavior.
- Add reference fields or endpoints additively; old clients must continue to work unchanged.
- Keep JSON Learning default and SQLite opt-in behavior unchanged unless a separately approved migration task says otherwise.
- Any storage format change requires versioned schema, migration, verification, rollback, and corruption recovery.

## Security and Privacy

- Never commit API keys, provider responses containing secrets, Zotero private exports, or user learning data.
- Real-provider evaluation requires explicit operator consent and a documented data-sent boundary.
- Reference URLs must reject local/file/executable schemes and strip credentials where displayed.
- CI scanners must use least privilege; workflow permissions should be explicit.
- SBOM/provenance output must describe source dependencies without embedding runtime corpus assets.
- Remote source access remains outside the recommended v1.2 scope.

## Evaluation Plan

### Structured References

- Curated positive/negative fixtures for DOI, arXiv, URL, malformed, duplicate, and section-provenance cases.
- Exact normalization and provenance assertions for every deterministic fixture.
- Pilot report over a bounded corpus sample before any full-corpus derived build.
- Full run must classify every input Article, report coverage/duplicates/failures, and be idempotent.
- Zotero matching reports exact, ambiguous, and unmatched groups separately; ambiguous matches are never auto-linked.

### Real Providers

- Use a fixed, source-grounded case set and record provider/model/config identity.
- Measure request success, latency distribution, rate-limit/retry behavior, citation schema, citation faithfulness, refusal correctness, and human-review fields.
- Record actual provider-reported usage/cost where available without projecting business value.
- Run only with explicit credentials and budget limits outside CI.

### CI and Provenance

- Existing backend pytest, frontend build, and tag/manual Docker jobs remain green.
- Dependency/secret scans have documented severity and suppression policy.
- Actions are pinned immutably and update automation is reviewed.
- SBOM and release provenance are reproducible and contain no forbidden runtime artifact.

## Milestones

### P3-002 - v1.2 Product Requirements and Architecture

Status: PASS. Scope Decision A approved contracts, boundaries, threat model, data flow, compatibility rules, evaluation budgets, and release criteria. No candidate version was assigned.

### P3-003 - Structured Reference Extraction Pilot

Status: **PASS / CLOSED**. Deterministic extraction/indexing passed on fixtures and a bounded 75-Article sample. Implementation commit `fb5419fc31222be738178a3ed65cf11dfb9192fe` passed main CI run `29415222974` for Backend and Frontend; Docker was correctly skipped for the normal main push.

### P3-004 - Real Provider Evaluation Design

Status: **PASS / CLOSED**. The isolated fake/dry-run harness implements provider consent, secret handling, fixed case selection, hard budgets, bounded metrics, terminal failure taxonomy, redaction/retention, and artifact auditing. Focused tests passed 35/35, the full Backend suite passed 530 with 3 skipped, the Frontend build passed, and deterministic evidence recorded zero external network requests. Implementation commit `0bf90e518549bea7549409cde72a3befda0c340d` passed main CI run `29627617727`: Backend and Frontend succeeded, and Docker compose smoke was correctly skipped for the normal main push. The report is `docs/P3_004_REAL_PROVIDER_EVALUATION_DESIGN_REPORT.md`. This PASS does not authorize a real call or enable a real provider by default.

### P3-005 - CI Security and Release Provenance

Status: **PASS / CLOSED**. Implementation commit `80e8823e2ba8403f347df762de3107298f6bc4b1` and P3-005.1 fix commit `666e93f043788e03133c3532e69b9fd2dcfa01ea` were validated on the exact fix commit by workflow-dispatch run [`29635940873`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29635940873). Local closure commit `ff19c520ac9650a36c5073665864aa4086160565` then passed main CI run [`29637475061`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29637475061). The canonical task is `docs/tasks/P3-005_CI_SECURITY_AND_RELEASE_PROVENANCE.md`.

The implementation adds immutable Action pins, least-privilege workflow permissions, dependency and secret scanning, validated Backend/Frontend/combined CycloneDX 1.6 SBOMs, exact-tag/manual provenance boundaries, branch-protection guidance, and verification documentation while preserving current CI jobs. Backend, Frontend, Docker compose smoke, workflow policy, dependency audit, secret audit, SBOM validation, and manual release-evidence dry-run passed. The dry-run recorded `would_authorize_publish=false` and `publish_authorized=false`, uploaded no workflow artifact, and left all tags and Releases unchanged. Push to `main`, candidate assignment, tag, Release, formal attestation publication, real-provider calls, and private-data access remain prohibited without separate authorization.

### P3-006 - Structured Reference Full-Corpus Build and Zotero Matching

Status: **CONDITIONAL / RISK ACCEPTED / CLOSED**. The exact approved 1,311-Article corpus produced 12,859 deterministic reference records and 24,514 provenance rows with complete accounting, zero silent drops, zero source mutations, and zero network requests. Checkpoint/resume, controlled interruption, atomic install, rollback, corruption/stale detection, no-op reuse, clean byte determinism, fake/unavailable matching, resource budgets, Backend, Frontend, compatibility, artifact, and secret gates passed.

The product owner reviewed and approved exactly three pilot cases and explicitly
waived the remaining 61 formal cases. Human-review precision remains
unmeasured; no 64/64 or precision result is claimed. This accepted limitation
does not change the machine evidence and is recorded in ADR 0009 and
`docs/P3_006_STRUCTURED_REFERENCE_FULL_CORPUS_REPORT.md`. Implementation and
exact-corpus authorization are consumed/closed.

Completion commit `f2496cafa4a54440b19e4491294277b70a1f07cf` exposed a dependency-audit failure on main. The separately authorized P3-006-CI-001 task classified it as real npm vulnerabilities and applied only minimum fixed versions with zero suppressions and no policy weakening. Repair commit `9b0080cbe5c6483de2534ed63f9eeb5c5e5b1dbd` passed full validation run [`30322598783`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30322598783), including Docker and no-publish release evidence, then passed main CI run [`30322723458`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30322723458). Both runs produced zero workflow artifacts. P3-006-CI-001 is PASS / CLOSED.

### P3-006.1 - Human Review Completion

Status: **REMAINDER WAIVED / PAUSED**. The canonical task is
`docs/tasks/P3-006_1_HUMAN_REVIEW_COMPLETION.md`.

P3-006.1 defines a future two-stage process for validating the existing
64-case packet, preparing an ignored worksheet, waiting for at least one real
natural-person reviewer, validating completed decisions, and reporting only
aggregate metrics and irreversible fingerprints.

The product owner elected not to execute this larger review and accepted the
resulting risk after approving three pilot cases. This does not mark the
remaining cases complete and does not produce a precision metric. The task
remains available as a remediation path if stronger human evidence is needed.

### P3-006.2 - Review UX Pilot and Zotero Collection Sync

Status: **PASS / CLOSED**.

P3-006.2 is a separately authorized usability and downstream-integration task.
It does not replace the formal 64-case P3-006.1 gate. It may create or reuse
one private root collection named `苏剑林博客`, write at most one controlled
real Scientific Spaces item, add an idempotent downstream metadata sync
adapter, and create an ignored three-case full-context review pilot. External
network access, bulk Zotero import, source/store mutation, push, P3-007,
candidate, tag, Release, and attestation remain prohibited.

The unique root collection and one controlled Web Page passed local readback;
the repeated sync returned `existing` without a second write. A separate
ignored three-case pilot now exposes authoritative full Article content for
strong-identifier, duplicate-group, and ambiguous-text review. Focused tests
passed 9/9, the Backend suite passed 549 tests with 3 skipped, and source/store,
secret, artifact, and browser checks passed. Evidence is in
`docs/P3_006_2_REVIEW_UX_ZOTERO_SYNC_REPORT.md`.

### P3-006.3 - Zotero Printed PDF Attachment Sync

Status: **PASS / CLOSED**.

P3-006.3 corrected the downstream representation from HTML snapshots to
browser-printed PDF attachments for only the three P3-006.2 pilot Articles.
The existing metadata-complete Web Page parents were preserved. Each approved
parent now has exactly one local PDF child and zero live HTML children in
`苏剑林博客`.

All three A4 PDFs passed local format, page, title, Chinese, distributed
Article-content, MathJax, and Zotero byte-readback checks. The three replaced
HTML children were moved to Zotero Trash only after joint 3/3 PDF readback.
The repeated three-Article command returned `existing` with zero browser
fetches, zero duplicate writes, and zero additional trash operations. Focused
tests passed 21/21 and the Backend suite passed 561 tests with 3 skipped.
Source/store integrity remained unchanged; the temporary localhost Zotero
debugger was disabled and normal API/Connector readiness was restored.
Evidence is in `docs/P3_006_3_ZOTERO_FULL_TEXT_SNAPSHOT_REPORT.md`.
Implementation, private Zotero, and bounded network authorizations are
consumed/closed; push was not performed.

### P3-007 - v1.2 Integration and Release Readiness

Status: **CONDITIONAL / RISK ACCEPTED / CLOSED**.

ADR 0009 records exactly three reviewed and approved pilot cases, 61 waived
formal cases, no measured precision, and the browser-printed PDF-only Zotero
full-text policy. P3-007 therefore proceeds as an explicit risk exception,
not as a claim that the original human-review gate passed.

Additive bounded `/v1.2` Reference APIs, Article Detail references, read-only
Zotero candidate states, and Tier 1/Tier 2 operations integration are complete.
Backend, Frontend, browser, fake-provider, workflow, dependency, secret, SBOM,
and no-publish release-evidence gates passed locally. The implementation commit
was pushed and exact-implementation GitHub Actions runs `30341443480` and
`30341652046` passed. The manual run additionally passed Docker compose smoke
and no-publish release evidence and produced zero workflow artifacts. No
candidate was assigned. Evidence is in
`docs/P3_007_V1_2_RELEASE_READINESS_REPORT.md`.

### P3-009 - Full Corpus Acquisition and Zotero PDF Sync

Status: **PASS / CLOSED**.

The user-connected desktop Chrome WebBridge passed a bounded nine-Article
probe at one worker and 8-, 6-, then 4-second global intervals. Every request
returned HTTP 200 and every A4/body/Chinese/MathJax PDF gate passed with zero
retries. The bridge can safely bind exactly one current tab, so one worker is
the provider concurrency cap and four seconds is the selected interval floor.

The canonical inventory reconciled to 1,326 URLs: 1,311 valid Articles, 15
classified non-importable URLs, and zero unclassified URLs. The private Zotero
root collection now has 1,311 provenance-matched parents, 1,311 PDF children,
zero HTML children, and zero duplicates. The idempotent rerun made zero source
navigations and zero Zotero writes.

Backend passed 587 tests with 3 skipped; all 27 focused Frontend tests and the
production build passed. Reader/Search, RAG, Tutor, Graph, Zotero, secret,
artifact, and changed-path gates passed. Three newer RSS URLs outside the
frozen inventory remain an explicit M1.x source-delta candidate. Evidence is in
`docs/P3_009_THROUGHPUT_PROBE_REPORT.md` and
`docs/P3_009_FULL_CORPUS_RUN_REPORT.md`.

### M1.4 - Incremental Source and Zotero PDF Sync

Status: **PASS / CLOSED**.

This separately authorized M1.x revision leaves frozen M1 modules and existing
Article records unchanged. It adds a read-only-by-default command that reads
the official RSS feed, acquires only missing canonical Article URLs through
the validated one-tab/four-second WebBridge tier, validates all source content
before an atomic append, and then reuses the established browser-printed PDF
and Zotero readback contracts.

The live delta discovered 10 feed URLs and imported three missing Articles.
The Article Store grew from 1,311 to 1,314 with all existing records unchanged.
The private `苏剑林博客` collection completed at 1,314 parents, 1,314 PDFs,
zero HTML children, and zero duplicates. The immediate rerun made zero source
or PDF navigations and zero Article or Zotero writes. Local Backend,
Frontend, Reader/Search, content, formula, PDF, Zotero, and artifact gates
passed.

RAG, Graph, and structured Reference Store outputs remain explicit immutable
1,311-Article snapshots. The Reference API correctly reports a stale corpus
fingerprint against the new Article Store; no derived rebuild is implicit in
M1.4. Evidence is in
`docs/M1_4_INCREMENTAL_SOURCE_ZOTERO_SYNC_REPORT.md`.
Implementation commit `2fbed9c566dd92cd4b97b1222869fde19251cfe0`
passed main CI run
[`30414826425`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30414826425),
including Backend, Frontend, workflow policy, dependency, secret, and SBOM
jobs. Docker and release evidence were correctly skipped for the normal push.

### P3-010 - Incremental Derived Asset Refresh

Status: **PASS / CLOSED**.

P3-010 adds an offline, read-only-by-default operations command over the exact
1,314-Article Store. RAG, Graph, and structured Reference assets are built in
isolated staging directories using deterministic fake providers, jointly
validated, backed up, and installed through a coordinated transaction with
complete-bundle rollback.

The local refresh produced 5,570 RAG chunks, 53,046 Graph nodes, 82,584 Graph
edges, 12,904 Reference records, and 24,598 Reference evidence rows. Archives
11814, 11818, and 11823 are represented in all relevant stores and each was
retrieved at RAG rank 1 by an evidence-bearing query. The Reference API now
reports a valid 1,314-Article store instead of `reference_store_stale`.

The immediate execute rerun was a no-op with no new backup or manifest
replacement. Injected build, install, and post-install failures preserve or
restore the prior complete bundle. The exact 1,311-Article RAG, Graph, and
Reference snapshots remain recoverable under ignored local data. No source
network, browser, private Zotero, real Provider, candidate, tag, or Release
action occurred. Evidence is in
`docs/P3_010_INCREMENTAL_DERIVED_ASSET_REFRESH_REPORT.md`.
Implementation commit
`e66d9f32358ba09b6d89fce5e86877a80a52f032` passed exact main CI run
[`30452018708`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30452018708):
Backend, Frontend, workflow policy, dependency audit, secret audit, and SBOM
validation succeeded; Docker and release evidence were correctly skipped for
the normal main push.

### P3-011 - End-to-End Product Convergence

Status: **PASS / CLOSED**.

P3-011 runs the real FastAPI and built Next.js applications against both the
exact 1,314-Article local runtime and a deterministic isolated three-Article
E2E fixture. It validates Dashboard, Reader/Search, Article Markdown and
formulas, Reading History, Learning state, Structured References, Knowledge
Graph, Tutor Explain/Derive/Quiz/Research modes, local deep links, controlled
errors, mobile layout, and persistence after Backend restart.

The implementation fixes duplicate Reader sessions caused by repeated
development effects and mobile overflow in Article List and KaTeX content.
The complete automated suite passed three consecutive runs with 16 checks per
run, zero external requests, zero unexpected console/page errors, and 390 px
document widths at a 390 px viewport. Backend passed 600 tests with 4 skipped;
all 27 focused Frontend tests, production build, dependency, secret, workflow
policy, and SBOM gates passed.

Implementation commit
`579c90252bc6fa594905491646ec07e296340043` passed normal main CI run
[`30456388891`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30456388891).
The same exact SHA passed manual `workflow_dispatch` run
[`30456541072`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30456541072),
including Docker compose smoke and no-publish release evidence. Both runs
reported zero uploaded artifacts. Evidence is in
`docs/P3_011_END_TO_END_PRODUCT_CONVERGENCE_REPORT.md`.

### P3-012 - Learning Experience and GUI Refinement

Status: **PASS / CLOSED**.

P3-012 applies three evidence-driven real-browser passes to the exact local
1,314-Article product. It improves route-aware navigation, Dashboard density,
Article preview readability, long-Article learning-tool access, external-image
safety, structured-reference wrapping, Graph summary density, Tutor mode
stability, keyboard focus, and application identity without changing Backend
contracts or frozen Article data.

Local evidence passed 600 Backend tests with 4 skipped, all 30 focused
Frontend tests, the production build, three complete isolated E2E runs with 17
checks each, workflow and suppression policy, dependency and secret audits,
and temporary SBOM validation. Implementation commit
`75652e3d7a6a43d5b92f56d06aface7a7fc19d85` passed exact-SHA main CI run
[`33322848683`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33322848683)
with zero uploaded artifacts. Evidence is in
`docs/P3_012_LEARNING_EXPERIENCE_GUI_REFINEMENT_REPORT.md`.

### P3-013 - Reader Workspace and Learning Continuity

Status: **PASS / CLOSED**.

P3-013 extends the existing Article Detail presentation with deterministic
section anchors, an accessible outline, current-section and progress feedback,
local resume state, local display preferences, and a Dashboard Continue Reading
entry. It is constrained to existing Article and learning contracts and does
not modify Backend routes, frozen M1 modules, Article records, source access,
private Zotero, or Provider behavior.

The canonical task is
`docs/tasks/P3-013_READER_WORKSPACE_AND_LEARNING_CONTINUITY.md`. Real-corpus
browser checks, 36 focused Frontend tests, 600 Backend tests, production build,
10 isolated E2E stress runs, and security/supply-chain gates pass. Initial
implementation commit `f0d9a04c71efa503fa74ff45af4d26484cadb55e`
exposed a remote resume race. Repair commit
`1d5606c4db1cc1c3177f404652788269f66cdc61` passed exact-SHA main CI run
[`33325595191`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33325595191),
including Backend, Frontend, and three Product E2E runs. Evidence is in
`docs/P3_013_READER_WORKSPACE_REPORT.md`.

### P3-014 - Integrated Learning Workflow

Status: **PASS / CLOSED**.

P3-014 connects the existing Article List, Reader, Tutor, Graph, Dashboard,
and learning-state surfaces through bounded, canonical local context. Article
search/sort/page state is URL-addressable; Article Detail exposes Tutor and
Graph actions; both tools preserve the exact Article and Reader section while
allowing normal interaction before returning.

Five real Articles from the exact local 1,314-Article Store passed desktop and
390 px browser checks with exact Tutor prefill, exact Graph Article-node
selection, same-section return, zero overflow, zero external requests, and
zero console/page errors. Local gates passed 600 Backend tests with 4 skipped,
41 focused Frontend tests, the production build, three isolated Product E2E
runs with 20 checks each, and workflow, dependency, secret, SBOM, artifact,
and protected-path audits. `AGENTS.md` was reduced to platform-neutral project
governance with generated agent/hook instructions removed. Evidence is in
`docs/P3_014_INTEGRATED_LEARNING_WORKFLOW_REPORT.md`.

Initial implementation run `33349166132` passed every job except Product E2E,
where unsequenced UI writes exposed a JSON learning-store test race. The
Backend contract remains unchanged; the E2E repair waits for each observable
writeback and passed 10/10 local stress iterations. Repair commit
`82eab2386c703b0768806900402771e7911f8f58` passed exact-SHA main CI run
[`33349379685`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33349379685),
including Backend, Frontend, three Product E2E runs, workflow policy,
dependency, secret, and SBOM jobs with zero uploaded artifacts.

### P3-015 - Visual Knowledge Explorer

Status: **PASS / CLOSED**.

P3-015 turns the existing bounded Graph response into an interactive visual
map while retaining the list, detail, provenance, and Article-context
workflow. The task is Frontend-only apart from tests and governance; Backend
interfaces and derived Graph data remain protected. The canonical task is
`docs/tasks/P3-015_VISUAL_KNOWLEDGE_EXPLORER.md`.

Local evidence: 600 Backend tests with 4 skipped, 43 focused Frontend tests,
production build, three Product E2E runs with 22 checks each, and real local
desktop/mobile Graph probes are PASS. Implementation commit
`8224b072434c016b348311cb27cc41c4ae593a14` passed exact-SHA main CI run
`33351208778`. Evidence is in
`docs/P3_015_VISUAL_KNOWLEDGE_EXPLORER_REPORT.md`.

## Release Criteria

- P3-002 scope and architecture approved with no unresolved compatibility ambiguity.
- All existing Backend tests and Frontend builds pass; exact-tag Docker smoke remains required.
- Legacy and `/v1.1` Article/Graph contracts remain unchanged unless a new versioned API is explicitly approved.
- Structured-reference deterministic fixtures pass exactly; the full run is classified, provenance-complete, and idempotent.
- No automatic ambiguous Zotero link and no mutation of Article source content.
- Real-provider evaluation remains opt-in, bounded, secret-safe, and absent from CI/default startup.
- Security scans, immutable Action pins, SBOM, and provenance evidence pass under documented policies.
- Migration/rollback and corruption-recovery evidence exists for every new persisted format.
- No Critical or Important release finding remains open.
- No private/runtime artifact is tracked or attached to the release.

## Risks

- Reference syntax is heterogeneous and may produce false matches without section-level evidence and conservative normalization.
- DOI/arXiv normalization can merge distinct versions if identity rules are too aggressive.
- Zotero metadata varies by item type and local library quality.
- Real-provider quality and cost can drift by model/version; every report needs provider identity and date.
- Security scanners can create noisy findings without triage ownership.
- Scope can expand into Graph migration, image archiving, or multi-user storage; those remain explicit deferrals.

## Deferred to v2.0

- Authentication and authorization.
- Multiple user/profile identities and isolation.
- Concurrent-write guarantees and managed database architecture.
- Public deployment, tenant administration, quotas, and abuse controls.
- Migration of local single-user private data into a hosted service.

## Next Recommended Task

P3-015 is PASS / CLOSED after implementation exact-SHA main CI. No subsequent
task or v1.2 candidate is assigned; the next task requires fresh alignment and
authorization. Tag, Release, attestation, real Provider,
source access, and private Zotero actions remain unauthorized.
