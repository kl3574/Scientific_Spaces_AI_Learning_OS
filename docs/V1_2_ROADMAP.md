# Scientific Spaces AI Learning OS v1.2 Roadmap

Status: P3-004 and P3-005 PASS / CLOSED; P3-005 has exact-commit remote validation and main CI evidence; P3-006 is canonically staged with ALIGNMENT REQUIRED; no candidate version is assigned.

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

Status: **ALIGNMENT REQUIRED**. The canonical task is `docs/tasks/P3-006_STRUCTURED_REFERENCE_FULL_CORPUS.md`. Implementation, full-corpus, network, and private Zotero authorization are all **NOT GRANTED**.

After a separately confirmed execution alignment and explicit data-access boundaries, the planned task may build and audit the complete derived Reference Store, prove no-network/no-mutation/idempotency/recovery, and evaluate read-only matching. Private Zotero access remains optional and separately authorized.

### P3-007 - v1.2 Integration and Release Readiness

Integrate additive reference API/UI and operations boundaries, then run compatibility, migration, security, artifact, local runtime, Docker, SBOM/provenance, and documentation gates. Recommend a candidate only from completed evidence and separate user authorization.

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

`P3-006 Execution Alignment Confirmation`

Confirm or revise the P3-006 execution alignment. Until confirmation, no corpus/Article access, full-corpus processing, network access, private Zotero operation, candidate, tag, Release, or P3-006 implementation is authorized.
