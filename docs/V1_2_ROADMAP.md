# Scientific Spaces AI Learning OS v1.2 Roadmap

This document owns product priorities, remaining requirements and deferrals.
[Project state](00_PROJECT_STATE.md) owns current status;
[CURRENT_TASK](tasks/CURRENT_TASK.md) points to the active canonical scope.
Formal release remains v1.1.0, with no v1.2 release candidate assigned.

## Next Planned Work

The owner approved the two-Article, 12-case v3 affine reference content in the
[human decision](reviews/P3_044_AFFINE_V3_HUMAN_DECISION.json). It is
development/regression data, not an unseen holdout, and the approval does not
cover unmeasured model responses.

1. First, plan controlled-response, claim-level offline regression using the
   approved v3 cases. Keep evidence relations, expected answer behavior and
   source IDs separate; a valid citation must not count as a correct claim.
   This is the proposed next bounded task, not implemented by this synchronization.
2. Separately authorize any real-model sample evaluation or retrieval-strategy
   comparison, with explicit data, provider/model identity, budget and reporting.
3. Consider a minimal LearningAttempt/ReviewSchedule answer-and-review loop.
4. Consider source-anchor notes with recoverable export/import.
5. Consider human-reviewed prerequisite relations and local learning paths.

Reader P3-042 remains OPEN / CI BLOCKED and Graph P3-039 OPEN / DEFERRED,
both with historical cause UNKNOWN. P3-043 local Reader implementation has only
partial verification; its missing terminal acceptance record must be resolved
before independent integration. See [project state](00_PROJECT_STATE.md).
No new task number or product implementation is created by this roadmap update.

## Executive Summary

v1.2 will improve scientific provenance and release trust without changing the local-first default. The approved planning scope is:

- Main theme: structured reference extraction and Zotero linking.
- Data-quality/evaluation theme: opt-in real-provider evaluation harness.
- Platform theme: CI security and release provenance.

Graph storage optimization is the strongest deferred engineering candidate, but P3-002 found no blocking performance target; its migration and regression cost make it better suited to v1.3. Remote image archiving is deferred, and multi-user architecture remains v2.0 discovery.

## Planning Basis

This scope and the relative scoring below originate from the P3-002 planning
baseline, not a fresh performance or quality measurement. The baseline's corpus,
Graph-size and reference gaps explain the original priorities. Current delivery
and verification state is maintained in [project state](00_PROJECT_STATE.md).

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

P3-002 selected Scope Decision A. The three included workstreams have independent, additive boundaries. Planning approval alone neither assigns a release candidate nor authorizes a real-provider call, private Zotero access or a full-corpus build. The current user-authorized synchronization is described in [alignment](../alignment.md).

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

### Main Theme - Structured Reference Extraction and Zotero Linking

- Define a `ReferenceRecord` contract with normalized identifier, source type, article ID, section/evidence, extraction rule version, and provenance.
- Build a deterministic derived index from existing Article content; do not fetch sources and do not mutate M1 during the pilot.
- Normalize DOI, arXiv, and HTTP(S) references with explicit duplicate rules.
- Produce explainable Zotero match candidates; no automatic write to a user's Zotero library.
- Add bounded Article/Paper link APIs only as additive contracts.

### Data-Quality Theme - Real Provider Evaluation Harness

- Keep the implemented P3-004 fake/dry-run harness separate from its non-executable real planned gate; any future real runner requires a separately authorized bounded task.
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

## Delivery and Unfinished Review References

Completed implementation histories are kept in their original reports:

| Workstream | Canonical evidence |
| --- | --- |
| Structured-reference pilot and full-corpus build | [Pilot report](STRUCTURED_REFERENCE_PILOT_REPORT.md), [P3-006](P3_006_STRUCTURED_REFERENCE_FULL_CORPUS_REPORT.md) |
| Provider consent, budgets and fake/dry-run harness | [P3-004](P3_004_REAL_PROVIDER_EVALUATION_DESIGN_REPORT.md) |
| CI security and release provenance | [P3-005](P3_005_CI_SECURITY_PROVENANCE_REPORT.md) |
| Reference integration and risk acceptance | [P3-007](P3_007_V1_2_RELEASE_READINESS_REPORT.md), [ADR 0009](ADR/0009-p3-007-review-risk-and-zotero-pdf-policy.md) |
| Source delta and recoverable derived refresh | [M1.4](M1_4_INCREMENTAL_SOURCE_ZOTERO_SYNC_REPORT.md), [P3-010](P3_010_INCREMENTAL_DERIVED_ASSET_REFRESH_REPORT.md) |
| Product convergence and subsequent Reader/Tutor workflows | [P3-011](P3_011_END_TO_END_PRODUCT_CONVERGENCE_REPORT.md), [canonical task collection](tasks/) |
| Tutor mode requests and affine reference preparation | [P3-044 implementation](P3_044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION_REPORT.md), [review preparation](P3_044_AFFINE_REVIEW_PREPARATION_REPORT.md) |

The earlier P3-006 reference packet approved exactly three pilot cases; 61 formal
cases remain WAIVED / PAUSED and precision is unmeasured. This is not the P3-044
affine packet. [P3-006.1](tasks/P3-006_1_HUMAN_REVIEW_COMPLETION.md) preserves the
remediation path: validate the 64-case packet, prepare an ignored worksheet,
obtain real human decisions, validate their binding, then publish only aggregate
metrics and irreversible fingerprints. No waived case is counted as completed.

## Deferred Engineering Requirements

Graph storage/cold-start work remains a separate measured proposal: establish a
performance target before indexed/lazy storage, bounded queries, versioned
migration, rollback, integrity and corruption-recovery work. Preserve legacy
Graph routes throughout; P3-039 diagnosis does not authorize storage migration.

Remote-image archiving remains opt-in and deferred. Any proposal must retain
source-pressure limits, attribution, checksums, resume/retry, safe local-path
rewriting and Reader/PDF integration. Ordinary startup, reading and CI must not
start a remote download.

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

- Historical intermittent Graph selected-Article visibility failure remains OPEN,
  root cause UNKNOWN. Preserve its failing checkpoint and original assertion;
  non-reproduction is not a repair. See the [Graph report](P3_039_GRAPH_NODE_RENDERING_RELIABILITY_REPORT.md).
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
