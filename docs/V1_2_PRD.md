# v1.2 Product Requirements

Status: Approved for planning

Scope Decision: **A - Structured References, opt-in Real Provider Evaluation, and CI Security/Release Provenance**

Formal version: `v1.1.0`

Candidate version: Not assigned

## Problem Statement

Scientific Spaces AI Learning OS can read and ground answers in 1,311 local Articles, but the completed corpus has empty structured `metadata.references` arrays. References remain embedded in Markdown as links and citation text, so users cannot reliably inspect normalized identifiers, trace a citation to its Article section, or compare it with a local Zotero item.

The deterministic fake-provider baseline proves system contracts, grounding, refusal, and bounded context behavior, but it does not measure real-provider latency, cost, failure modes, or answer quality. Any real-provider evaluation therefore needs an explicit data-egress and budget boundary before it is used.

The release pipeline runs backend, frontend, and conditional Docker checks, but its third-party Actions use mutable major tags and it lacks integrated dependency/secret scanning, SBOM generation, and release attestation evidence.

## Evidence

- P3-001 post-release validation passed at `fdba4d8759f36704fcc928fff504526d0c5e1781`; no Critical or Important findings remain.
- The Article store contains 1,311 valid, unique Articles with complete content and metadata, while structured reference arrays are empty.
- The M5 Zotero provider already exposes read-only metadata and tolerates an unavailable local API.
- Fake-provider RAG/Tutor evaluation is deterministic and offline, but does not certify a real model.
- CI currently uses `actions/checkout@v4`, `actions/setup-python@v5`, and `actions/setup-node@v4` rather than immutable full commit SHAs.
- Runtime corpus, PDF, RAG, Graph, evaluation, user, and backup data are ignored local artifacts and must remain outside Git and release assets.

## Target Users

- A local reader who wants to inspect the sources cited by a Scientific Spaces Article.
- A researcher who wants explainable candidate links between Article references and a local Zotero library.
- A maintainer who needs bounded, consented real-provider quality evidence without changing safe defaults.
- A release operator who needs verifiable dependency, workflow, SBOM, and release provenance evidence.

## User Journeys

### Inspect Structured References

1. The user opens an Article already stored locally.
2. The UI requests a bounded `/v1.2` reference page for that Article.
3. The user sees identifier type, normalized identifier, source section, evidence, and derived/stale status.
4. Ambiguous or malformed records are visible as classifications rather than silently omitted.

### Review Zotero Candidates

1. The user opens a reference or Zotero review view.
2. The system requests candidates from the configured read-only provider.
3. Exact, probable, ambiguous, unmatched, and rejected states are shown with matched and conflicting fields.
4. No candidate changes Zotero or an Article automatically. A future explicit user decision is stored separately from rebuildable extraction output.

### Evaluate a Real Provider

1. An operator selects a fixed case set outside CI.
2. The runner displays provider/model identity, data categories, request cap, cost cap, and whether Article snippets will be sent.
3. The operator supplies every required acknowledgement and bounded budget.
4. Redacted local results record reliability, latency, usage, grounding, and human review without credentials or private user data.

### Verify a Release

1. CI runs existing backend and frontend gates with immutable Action pins and least privilege.
2. Security jobs report dependency and secret findings under an expiring suppression policy.
3. A release job generates a bounded CycloneDX SBOM and attests its digest for the exact tag commit.
4. A verifier checks the tag, workflow identity, SBOM digest, and GitHub attestation without receiving local runtime data.

## Goals

1. Produce deterministic, provenance-complete structured reference records from existing Article content without source access or Article mutation.
2. Produce explainable Zotero match candidates while preserving the read-only provider boundary and explicit human control.
3. Define and later implement an opt-in, budgeted, redacted real-provider evaluation harness while keeping fake providers as the default and CI baseline.
4. Strengthen workflow integrity, dependency/secret visibility, SBOM evidence, and exact-release provenance.
5. Preserve every frozen v1.0, `/v1.1`, M3-M7, persistence, backup, and restore contract.

## Non-Goals

- No mutation of `Article.content`, `metadata.references`, M1 parser/converter/validation, or the Article schema.
- No DOI, arXiv, publisher, or other remote metadata resolution.
- No automatic Zotero write, automatic candidate confirmation, or export of a complete private Zotero library.
- No default real provider, paid CI request, product startup dependency, or claim of real-model correctness.
- No Graph storage migration, remote image archive, authentication, multi-user/profile isolation, public deployment, or managed database.
- No v1.2 candidate declaration, tag, release, or release date during planning.

## Functional Requirements

### Structured References

- The planned pipeline reads the frozen Article store and writes only a derived Reference Store.
- It recognizes DOI, arXiv, safe HTTP(S) URLs, relative/internal URLs, citation text, unsupported input, and malformed input.
- Every detected candidate receives a classification; no candidate is silently dropped.
- Exact identifier and exact normalized-URL duplicates may merge deterministically while retaining all evidence.
- Possible textual duplicates remain separate and are grouped only for review.
- Every record is traceable to Article ID, title, canonical URL, section, optional stable span, evidence, extraction rule, and corpus fingerprint.
- The store supports atomic build, rollback, integrity checks, stale detection, deterministic ordering, and idempotent no-op reuse.

### Zotero Matching

- Extraction works when Zotero Desktop or its local API is absent.
- Matching consumes `ReferenceRecord` and returns bounded `ZoteroMatchCandidate` values.
- Exact DOI or arXiv matches may be classified `exact` only when no conflicting strong field exists.
- Normalized URL matches are `probable` unless corroborated by a strong identifier.
- Title-only matches remain `ambiguous` and cannot be auto-confirmed.
- Candidate generation never writes to Zotero, the Article store, existing M5 links, or the Tier 1 review store.

### Versioned API and UI

- Planned endpoints are additive under `/v1.2`: reference list, detail, Article references, Zotero candidates, and summary.
- Lists use default page size 20 and maximum page size 100; provenance defaults to 5 and is capped at 20 per record.
- Responses contain no local absolute path, complete private Zotero payload, full-corpus dump, or Article body.
- Article Detail gains a separate Structured References section; the Zotero view gains matched, ambiguous, and unmatched filters.
- Loading, empty, error, stale-index, ambiguity, pagination, and safe-link states are required.

### Real Provider Evaluation

- The planned runner requires real-provider selection, data-sent acknowledgement, request cap, estimated-cost cap, case set, and ignored output directory.
- It sends only bounded case instructions and approved Article snippets. It sends no notes, Learning state, Tutor history, private Zotero metadata, complete corpus, or secrets.
- It records provider/model/config identity, reliability, latency, usage/cost, grounding, and human-review fields.
- Raw output is disabled by default; redacted and aggregate output stays under ignored local storage.

### CI Security and Provenance

- Third-party Actions are pinned to reviewed full commit SHAs with source-version comments.
- Workflow permissions are explicit and least-privileged per job.
- Python and npm lockfiles receive dependency scans; tracked files and bounded history receive secret scans.
- Suppressions require an advisory/finding ID, rationale, owner, review link, and expiry.
- Release evidence includes a bounded CycloneDX JSON SBOM and GitHub artifact attestation for exact release subjects only.

## Security and Privacy Requirements

- Reject or redact credential-bearing URLs and reject local, executable, `file:`, `javascript:`, and `data:` schemes.
- Bound candidate length, parsing work, regex complexity, API pages, provenance, provider cases, requests, tokens, output, retries, and cost.
- Treat Article text as untrusted data, not provider instructions.
- Never log API keys, authorization headers, secret-bearing environment values, full sensitive prompts, or raw provider metadata that may contain secrets.
- Treat Zotero item metadata, user-reviewed decisions, provider output, and user data as private local data.
- CI artifacts must exclude corpus, PDF, Graph, RAG, database, backups, local paths, credentials, and private runtime stores.

## Compatibility Requirements

- Existing `/articles`, `/articles/{id}`, legacy Graph routes, `/v1.1/articles`, and `/v1.1/graph/*` response keys, ordering, bounds, and status behavior remain unchanged.
- M3 citation/no-source, M4 Learning, M5 read-only provider, M6 provenance/evidence, and M7 grounding/refusal contracts remain unchanged.
- New Article reference data is fetched through `/v1.2`; it is not injected into existing Article responses.
- JSON remains the default Learning backend; SQLite remains opt-in and explicit migration/export behavior remains unchanged.
- v1.1 inventory, backup, restore, cleanup, and rebuild semantics remain unchanged until a separately approved operations revision.

## Success Metrics

- P3-003 has at least 60 deterministic fixtures and a 50-100 Article no-network pilot.
- Valid DOI/arXiv/URL fixture normalization, candidate classification, provenance, and expected deterministic deduplication are 100% exact.
- Silent-drop count, Article mutation count, private-data emission count, unexpected network request count, and automatic Zotero write count are zero.
- Strong-identifier human-reviewed pilot precision is at least 95%; any false `exact` Zotero match blocks progression.
- Repeated extraction against the same corpus/rule fingerprint is a validated no-op with unchanged content fingerprints.
- P3-004 fake/dry-run tests prove every consent, budget, redaction, retention, and network guard without a real call.
- P3-005 preserves backend, frontend, and conditional Docker gates; all Action references are immutable; no unsuppressed Critical/High dependency or secret finding remains.
- SBOM/provenance subjects match the exact release commit and contain zero forbidden artifact paths or secrets.

## Release Scope

Scope Decision A approves these workstreams for v1.2 planning:

1. Structured Reference Extraction and explainable, read-only Zotero candidate matching.
2. An opt-in Real Provider Evaluation Harness with fake/dry-run acceptance and no required paid run.
3. CI Security and Release Provenance with immutable pins, scanners, CycloneDX SBOM, and exact-release attestation.

Approval means the milestones may be implemented under their own task alignments and gates. It does not assign `v1.2.0` as a candidate.

## Deferred Scope

- v1.3 candidate: Graph indexed/lazy storage migration if measured cold-start or growth evidence justifies it.
- v1.3 candidate: explicit remote image archive, subject to source pressure, copyright, storage, attribution, and rollback review.
- v2.0 discovery: authentication, authorization, multi-profile isolation, concurrent-user persistence, and public deployment.
- Separate M1.x governance: any write to `metadata.references` or change to the frozen source pipeline.

## Decisions Requiring Future User Approval

P3-002 has no unresolved critical architecture ambiguity. Separate explicit approval is still required before:

- any real-provider or paid request, including provider/model, data scope, case set, and budget;
- access to a private Zotero library or recording user-reviewed decisions;
- a full 1,311-Article reference build;
- any M1.x migration into `metadata.references`;
- external repository-setting changes such as branch protection;
- assigning a v1.2 candidate, creating a tag, or publishing a Release.
