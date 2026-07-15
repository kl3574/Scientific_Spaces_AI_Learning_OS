# P3-003 Structured Reference Extraction Pilot

## Status

PASS

BOUNDED OFFLINE PILOT COMPLETED

## Task Identity

P3-003 Structured Reference Extraction Pilot

## Authoritative Baseline

- Starting commit: `edc6e4a4f619c8b7bc0cd3de480fbd64a463aabf`
- Previous task: P3-002 v1.2 Product Requirements and Architecture, PASS
- Scope decision: A
- Formal version: `v1.1.0`
- Candidate version: Not assigned
- Applicable ADRs: ADR 0006, ADR 0007, ADR 0008
- Applicable governance: root `AGENTS.md`, `docs/tasks/README.md`, and a separately confirmed `alignment.md`

## Background

The validated local corpus contains 1,311 Articles whose frozen `id`, `title`, `url`, `content`, and `metadata` contracts remain authoritative. Structured references are currently embedded in Markdown while `metadata.references` remains empty. P3-002 approved an independent, deterministic, offline derived-reference architecture that preserves M1, Article content, released APIs, and local-first defaults.

This specification is the canonical contract for the user-confirmed P3-003 execution alignment. Implementation and a 50-100 Article offline pilot are authorized within the listed paths and gates. Push, tag, and Release remain unauthorized.

## Goal

Validate a bounded, deterministic, offline Structured Reference Extraction architecture covering:

- DOI, including wrapped and malformed forms;
- modern, legacy, and versioned arXiv identifiers;
- safe HTTP(S), relative, and internal URLs;
- citation text and complete provenance;
- deterministic IDs and duplicate grouping;
- a derived Reference Store with atomic build, rollback, integrity, stale/corruption detection, and idempotent reuse;
- explainable read-only Zotero candidate matching against fake or unavailable providers;
- zero external network requests and zero source mutation.

## Non-Goals

- Do not modify `Article.content` or `metadata.references`.
- Do not modify M1 crawler, browser access, parser, converter, validation, storage, or sync.
- Do not process all 1,311 Articles or implement the full-corpus build.
- Do not access source sites, DOI/arXiv/publisher metadata services, or other literature websites.
- Do not read or export a private Zotero library and do not write to Zotero.
- Do not implement real-provider evaluation or CI Security/Release Provenance milestones.
- Do not modify legacy or `/v1.1` APIs.
- Do not assign a v1.2 candidate or create a tag or GitHub Release.

## In Scope

- At least 60 deterministic synthetic or metadata-only fixtures.
- A deterministic offline pilot over 50-100 local Articles, targeting 75.
- Markdown-aware extraction, conservative normalization, complete classification, provenance, deduplication, and store lifecycle checks.
- Fake/unavailable Zotero matching behavior with no write capability.
- A bounded aggregate pilot report that contains IDs, hashes, counts, strata, metrics, and review evidence but no Article bodies.

## Out of Scope

- Full-corpus reference processing.
- Product API or UI integration.
- Graph integration or storage migration.
- Remote image archive, authentication, multi-user, public deployment, or managed storage.
- Private user decisions, real-provider calls, paid requests, or external metadata resolution.

## Allowed Implementation Areas

Only after a separate P3-003 execution alignment is explicitly confirmed:

- `backend/app/references/`
- `backend/tests/references/`
- `backend/tests/fixtures/references/`
- `scripts/references/`
- `docs/STRUCTURED_REFERENCE_PILOT_REPORT.md`
- `.gitignore`, limited to reference runtime output
- `README.md`, limited to the pilot command
- `docs/00_PROJECT_STATE.md`
- `alignment.md`

No implementation path is authorized by the current task-authority persistence work.

## Prohibited Actions

- Network access from extraction or matching, including source-site and identifier resolution.
- Full 1,311-Article reference build or any sample outside 50-100 Articles.
- Article/M1 mutation, frozen contract changes, legacy API changes, or `/v1.1` API changes.
- Real provider, paid call, private Zotero access/export, Zotero write, automatic link confirmation, or title-only exact match.
- Commit of corpus content, Article bodies, runtime reference stores, credentials, databases, PDFs, images, Graph/RAG data, traces, profiles, caches, or private user data.
- Candidate version, tag, Release, force push, or unapproved push.

## Inputs

- Existing validated local Article store, explicitly configured and treated as read-only.
- Approved contracts in `docs/V1_2_PRD.md`, `docs/V1_2_ARCHITECTURE.md`, `docs/V1_2_DATA_MODEL.md`, `docs/V1_2_THREAT_MODEL.md`, `docs/V1_2_EVALUATION_PLAN.md`, `docs/V1_2_ACCEPTANCE.md`, and `docs/V1_2_EXECUTION_PLAN.md`.
- ADR 0006 for derived persistence, ADR 0007 for provider boundaries, and ADR 0008 for later CI security work.
- Synthetic/bounded committed fixtures and fake/unavailable Zotero providers only.

## Data Contracts

### ReferenceEvidence

One immutable occurrence with stable Article identity, nearest Markdown section, optional stable span, bounded evidence, raw-reference hash, extraction rule/version, classification, and corpus fingerprint. Cross-Article evidence never collapses.

### ReferenceRecord

One canonical reference identity with type, classification, normalized identifier/URL, DOI or version-aware arXiv fields, deterministic ID, complete sorted evidence IDs, primary source fields, duplicate group, rule versions, confidence, and fingerprints. Citation text does not claim exact paper identity.

### ReferenceManifest

The versioned integrity root containing schema/rule/config/corpus/build fingerprints, deterministic file hashes and counts, network-request count, source asset identity, and integrity version. Only a complete validated manifest may become current.

### ZoteroMatchCandidate

A minimal, explainable, bounded comparison against fake or read-only Zotero metadata. Exact requires a non-conflicting strong DOI or version-compatible arXiv identifier; URL-only is at most probable; title-only remains ambiguous. It is never a user decision and has no write operation.

## Runtime Output

```text
.local_data/scientific_spaces/references/pilot/
├── manifest.json
├── records.jsonl
├── evidence.jsonl
├── article_index.json
├── identifier_index.json
├── zotero_candidates.jsonl
└── reports/
```

All runtime output is Git ignored. `evidence.jsonl` is included because the approved `ReferenceEvidence` serialization contract requires it. The store contains no full Article bodies or local absolute paths.

## Fixture Coverage

The suite must include at least:

- bare DOI, DOI URL, balanced punctuation, malformed DOI, and Unicode/spoofing candidates;
- modern, legacy, versioned, and malformed arXiv identifiers;
- HTTP/HTTPS, relative/internal URLs, fragments, identity-bearing and tracking queries, credential-bearing URLs, unsafe schemes, and IDN hosts;
- Chinese and English citation text;
- exact, same-section, cross-section, cross-Article, and possible textual duplicates;
- no-reference Articles, stable/unstable spans, pathological long candidates, high candidate counts, Markdown, code, math, and link contexts;
- stale manifests, corruption, checksum/index mismatch, interrupted install, rollback recovery, and unchanged no-op reruns.

Committed fixtures must be synthetic or bounded citation metadata and must not contain long Article bodies.

## Deliverables

- Reference contracts, extractor/normalizer/deduplicator, provenance and bounded classification implementation.
- Atomic deterministic derived-store implementation and audit tooling.
- At least 60 fixtures and focused tests.
- A no-network pilot CLI over 50-100 Articles.
- Fake/unavailable read-only Zotero matching seam.
- `docs/STRUCTURED_REFERENCE_PILOT_REPORT.md` with metrics, IDs/strata, review evidence, fingerprints, resource use, and artifact audit.
- A status-appropriate local commit; push requires separate authorization.

## Acceptance Criteria

### PASS

- `fixture_case_count >= 60`
- `fixture_fail_count = 0`
- `50 <= pilot_article_count <= 100`
- `articles_classified_rate = 1.0`
- valid DOI, arXiv, safe-URL, malformed/forbidden classification, and expected deterministic deduplication exactness are `1.0`
- `silent_drop_count = 0`
- `provenance_complete_rate = 1.0`
- `deterministic_id_rate = 1.0`
- `duplicate_group_consistency_rate = 1.0`
- manifest, schema, hash, count, index, and referential integrity are PASS
- stale detection, corruption detection, failed-install rollback, and interrupted-state recovery are PASS
- unchanged rerun is a validated no-op with an unchanged build/content fingerprint
- `Article.content` and Article corpus fingerprint remain unchanged
- `external_network_request_count = 0`
- automatic Zotero/library/link/decision writes are `0`
- false `exact` Zotero fixture matches are `0`
- human-reviewed strong-identifier precision is at least `95%`
- tracked runtime/private artifacts are `0`
- Backend regression, Frontend build, and frozen API compatibility are PASS

### CONDITIONAL

Deterministic integrity passes, but human-reviewed strong-identifier precision is below 95%, or a finite bounded syntax/rule review remains. Record exact cases and create P3-003.x. P3-006 may not begin.

### BLOCKED

Any Article mutation, wrong exact identity, false exact Zotero match, provenance loss, silent drop, network access, corrupt/partial install, non-idempotency, frozen-contract regression, test/build failure, private/runtime artifact, or unauthorized action blocks progression.

## Verification Commands

Planned commands that must be implemented by a separately authorized P3-003 task:

```bash
uv run --project backend --extra dev pytest -q backend/tests/references/
uv run --project backend python scripts/references/run_reference_pilot.py \
  --article-store <ignored-article-store> \
  --sample-size 75 \
  --output-dir .local_data/scientific_spaces/references/pilot \
  --no-network
uv run --project backend --extra dev pytest -q
npm --prefix frontend run build
```

The execution task must also verify input/output accounting, Article fingerprints, deterministic rerun fingerprints, store corruption/rollback, frozen API contracts, and tracked artifact/secret policy.

## Artifact and Secret Policy

Never track or attach Article corpus/content exports, full derived stores, private Zotero payloads or decisions, provider output, API keys, authorization headers, `.env`, databases, backups, PDFs, HTML/images, RAG/FAISS/Graph data, browser profiles/traces/caches, or local absolute paths. Reports use bounded IDs, hashes, safe URLs, counts, and aggregate metrics.

## Git Plan

- PASS commit: `feat: add structured reference extraction pilot`
- CONDITIONAL commit: `docs: record conditional structured reference pilot`
- BLOCKED commit: `docs: record structured reference pilot blockers`
- Push: requires separate authorization; default is local commit only
- CI: required after any separately authorized push
- Tag: prohibited
- Release: prohibited

## Stop Conditions

- A frozen contract or M1/Article mutation is required.
- The sample cannot remain within 50-100 Articles.
- A network, real-provider, paid, private-Zotero, or full-corpus action is required.
- Unknown worktree drift, test/build failure, credible artifact/secret hit, or unresolved data-identity/security ambiguity appears.
- Required implementation falls outside the allowed paths.

## Completion Evidence

- Commit: local PASS commit with message `feat: add structured reference extraction pilot`; hash is recorded in Git history and the execution report
- CI: pending an authorized push
- Report: `docs/STRUCTURED_REFERENCE_PILOT_REPORT.md`
- Focused tests: 26 passed
- Frozen API regressions: 45 passed
- Complete Backend suite: 495 passed, 3 skipped
- Frontend production build: PASS
- Pilot: 75 Articles, 1,578/1,578 candidates classified, zero network, zero mutation, 30 human-reviewed cases, strong-identifier precision 1.0
- Store and artifact/secret audits: PASS

## Next Task

P3-004 Real Provider Evaluation Design alignment and explicit authorization.
