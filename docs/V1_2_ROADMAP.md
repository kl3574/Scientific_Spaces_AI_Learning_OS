# Scientific Spaces AI Learning OS v1.2 Roadmap

Status: Proposed after P3-001; scope is not yet an approved candidate release.

## Executive Summary

v1.2 should improve scientific provenance and release trust without changing the local-first default. The recommended scope is:

- Main theme: structured reference extraction and Zotero linking.
- Data-quality/evaluation theme: opt-in real-provider evaluation harness.
- Platform theme: CI security and release provenance.

Graph storage optimization is the strongest deferred engineering candidate, but its migration and regression cost make it better suited to v1.3 unless P3-002 establishes a blocking performance target. Remote image archiving is deferred, and multi-user architecture remains v2.0 discovery.

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
- No full Graph storage migration unless P3-002 approves a measured performance requirement and rollback design.
- No change to the frozen M1 source pipeline in ordinary v1.2 work. Any M1 implementation change requires a separate M1.x revision task.
- No claim that reference extraction or Zotero matching proves scientific correctness.

## Candidate Workstreams

### Candidate A - Real Provider Quality Evaluation

Add explicit embedding/chat provider experiments for cost, latency, errors, citation faithfulness, answer quality, privacy, fallback behavior, and rate limits. Credentials remain local; fake providers remain default; CI never calls paid services.

### Candidate B - Structured Reference Extraction

Extract DOI, arXiv IDs, and URLs from existing `Article.content`; normalize and deduplicate them; preserve exact article/section evidence; and produce candidate Zotero matches with confidence and provenance. Prefer a derived reference store so the frozen M1 parser and Article schema remain untouched.

### Candidate C - Graph Storage and Cold-Start

Replace repeated large-JSON cold loading with indexed/lazy storage, schema migration, bounded queries, integrity checks, and corruption recovery. This requires careful compatibility and rollback work because legacy Graph routes remain frozen.

### Candidate D - Remote Image Local Archive

Offer an explicit opt-in archive with bounded source pressure, checksum verification, attribution, resume/retry, local-path rewriting, and Reader/PDF integration. It must never run from ordinary startup or CI.

### Candidate E - CI and Repository Security

Add dependency and secret scanning, immutable Action pinning, branch-protection guidance, SBOM generation, release provenance, and artifact attestation. Keep generated evidence bounded and avoid shipping private runtime data.

### Candidate F - User Data and Multi-Profile Architecture

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

## Recommended Scope

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

Approve contracts, scope boundaries, threat model, data flow, compatibility rules, evaluation budgets, and release criteria. This approval is required before assigning a v1.2 candidate version.

### P3-003 - Structured Reference Extraction Pilot

Implement deterministic extraction/indexing on fixtures and a bounded Article sample. Produce normalization, provenance, duplicate, and Zotero-match evidence before a full-corpus run.

### P3-004 - Real Provider Evaluation Design

Specify provider consent, secret handling, case selection, budgets, metrics, failure taxonomy, and report format. A design PASS does not enable a real provider by default.

### P3-005 - CI Security and Release Provenance

Add immutable pins, scanning, SBOM, provenance, least-privilege workflow permissions, and verification documentation while preserving current CI jobs.

### P3-006 - v1.2 Integration and Release Planning

Run compatibility, migration, security, artifact, local runtime, Docker, and documentation gates. Decide the final candidate only from completed evidence.

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

## First Recommended Task

`P3-002 v1.2 Product Requirements and Architecture`

The task should approve or reject the proposed three-theme scope before any implementation or candidate-version declaration.
