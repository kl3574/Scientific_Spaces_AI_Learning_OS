# P3-003 Structured Reference Extraction Pilot Execution Alignment

## 1. Background

P3-002 is PASS under Scope Decision A. Canonical task authority is synchronized at commit `6674f0a85c0f92e0976cf7eb46fe9c626679ef40`, with architecture baseline `edc6e4a4f619c8b7bc0cd3de480fbd64a463aabf`. P3-003 is a bounded, deterministic, offline pilot over 50-100 Articles, targeting 75. It is not a full-corpus build.

The user explicitly authorized this execution alignment. Local implementation, validation, pilot execution, and one status-appropriate local commit are authorized. Push, tag, and Release are not authorized.

## 2. Authoritative Inputs

- `AGENTS.md`
- `docs/tasks/README.md`
- `docs/tasks/CURRENT_TASK.md`
- `docs/tasks/P3-003_STRUCTURED_REFERENCE_PILOT.md`
- `docs/V1_2_PRD.md`
- `docs/V1_2_ARCHITECTURE.md`
- `docs/V1_2_DATA_MODEL.md`
- `docs/V1_2_THREAT_MODEL.md`
- `docs/V1_2_EVALUATION_PLAN.md`
- `docs/V1_2_ACCEPTANCE.md`
- `docs/V1_2_EXECUTION_PLAN.md`
- ADR 0006, ADR 0007, and ADR 0008
- `docs/00_PROJECT_STATE.md`, `docs/V1_2_ROADMAP.md`, and this alignment

Formal version remains `v1.1.0`. No candidate version is assigned.

## 3. Goals And Purpose

Validate deterministic offline extraction for DOI, modern/legacy/versioned arXiv, safe HTTP(S) and relative/internal URLs, citation text, complete provenance, stable IDs, duplicate grouping, an atomic derived Reference Store, fake/unavailable read-only Zotero matching, no-op reuse, integrity/recovery, zero network, and zero Article mutation.

## 4. Non-Goals

- No mutation of `Article.content`, `metadata.references`, M1, Article storage, legacy APIs, or `/v1.1` APIs.
- No full 1,311-Article extraction/build.
- No product API/UI, Graph integration, P3-004, P3-005, or P3-006 implementation.
- No source-site/identifier lookup, real provider, paid call, or private Zotero access/write.
- No v1.2 candidate, tag, GitHub Release, or push.

## 5. Exact Implementation Scope And Plan

Allowed paths and responsibilities:

- `backend/app/references/`: contracts, extraction, normalization, deduplication, provenance, store lifecycle, matcher, and integrity.
- `backend/tests/references/`: focused contract, failure, network, store, and matcher tests.
- `backend/tests/fixtures/references/`: at least 60 compact deterministic fixtures.
- `scripts/references/`: pilot runner and store/artifact audit commands.
- `docs/STRUCTURED_REFERENCE_PILOT_REPORT.md`: bounded evidence report.
- `.gitignore`: reference runtime output only, and only if current rules are insufficient.
- `README.md`: pilot command only.
- `docs/00_PROJECT_STATE.md`, `docs/tasks/CURRENT_TASK.md`, and `docs/tasks/P3-003_STRUCTURED_REFERENCE_PILOT.md`: status/evidence synchronization only.
- `alignment.md`: this confirmed alignment.

Execution order: contracts and fixtures; extractor/normalizer; deduplication/provenance; deterministic JSONL store; fake/unavailable matcher; pilot/audit CLI; 75-Article pilot and human review; regression/build/audits; status-appropriate local commit.

JSONL payload plus JSON indexes is selected because it is streamable, deterministic, offline, and independent of frozen Article/M1 state. Backfilling Article metadata and a monolithic JSON store are rejected; SQLite is deferred until measured evidence justifies it.

The canonical report path is `docs/STRUCTURED_REFERENCE_PILOT_REPORT.md`. The older path in `docs/V1_2_ACCEPTANCE.md` is treated as a documentation consistency note, not a second report.

## 6. Inputs

The Article store is explicitly configured and read-only. Its before/after fingerprint must match. Selection-only inventory may inspect IDs, metadata, length, lexical marker counts, Markdown/math/code/link tags, and deterministic selection hashes across the store, but it may not extract, deduplicate, match, or serialize references for unselected Articles. Extraction is limited to the final 50-100 Articles, default 75.

## 7. Fixture Plan

At least 60 deterministic synthetic or metadata-only fixtures cover bare/wrapped/malformed/confusable DOI; modern/legacy/versioned/malformed arXiv; safe, relative/internal, tracking, identity-query, fragment, credential, unsafe-scheme, and IDN URLs; Chinese/English citation text; same-section, cross-section, cross-Article, exact, and possible duplicates; no-reference, long/high-count candidates; Markdown/math/code/link contexts; stable/unstable spans; stale/corrupt/checksum/index/interrupted/rollback/no-op store cases. No long Article body is committed.

## 8. Pilot Selection Plan

Target 75 Articles. Compute deterministic feature tags without reference output. Rank Articles by `SHA-256("P3-003-selection/v1\\0" + article_id)`. In fixed strata order, select up to three unselected Articles for DOI, arXiv, URL, Chinese/English citation, multi-link, no-reference, malformed-like, duplicate-like, long, short, legacy, formula/Markdown/code, then fill by round-robin date/content-length/formula/link/reference-token strata. Record selected IDs, tags, aggregate inventory counts, and selection-rule fingerprint. Never emit output for unselected Articles.

## 9. Data Contracts

`ReferenceEvidence` contains immutable evidence/reference IDs, Article identity, section, nullable stable span, bounded evidence/raw hash, ordinal, rule/version, classification, and corpus fingerprint. `ReferenceRecord` contains type/classification, normalized identity fields, primary source, complete sorted evidence IDs, source count, deterministic duplicate group, confidence, rule versions, and corpus/build/record fingerprints. `ReferenceManifest` is the complete integrity root for schema/rule/config/corpus/build fingerprints, counts, file hashes, source identity, network count, and complete status. `ZoteroMatchCandidate` is a minimal explainable read-only comparison and never a user decision.

JSON/JSONL uses UTF-8, sorted keys, compact separators, stable ordering, and trailing newlines. IDs use versioned SHA-256 identities with at least 128 retained bits. No absolute paths, Article bodies, credentials, or complete private-library payloads are permitted.

## 10. Extraction And Normalization Rules

DOI handling removes approved wrappers and only structurally unmatched terminal punctuation while preserving valid internal punctuation and balanced parentheses; no network validation. arXiv supports modern, legacy, and explicit versions; base/version identity remains separate and distinct versions do not exact-merge. URL handling permits HTTP(S), preserves identity-bearing query/fragment data, removes only the tracking allowlist, rejects credentials/unsafe schemes, and classifies relative/internal links separately. Citation text retains bounded evidence and cannot claim exact identity without a strong identifier.

## 11. Duplicate Policy

Equal DOI or version-aware arXiv keys exact-merge. Equal complete safe normalized URLs merge only without strong-field conflict. Text similarity creates possible groups only. Evidence collapses only for the same Article, section, span/raw hash, and rule version; cross-Article evidence is always retained. Group IDs are deterministic. Ambiguous text is never auto-merged.

## 12. Derived Store Lifecycle

Runtime root is `.local_data/scientific_spaces/references/pilot/` with `manifest.json`, `records.jsonl`, `evidence.jsonl`, `article_index.json`, `identifier_index.json`, `zotero_candidates.jsonl`, and `reports/`.

Build in a private sibling staging directory; reject symlinks/path escape; canonicalize and hash payloads; write the manifest last; validate schema, counts, hashes, indexes, foreign keys, and fingerprints; atomically rename with one rollback directory; restore on failure; recover interrupted state. Stale and corrupt states are distinct. Identical valid input/schema/rules/configuration must produce a validated no-op with unchanged content/build fingerprints.

## 13. Zotero Boundary

Only deterministic fake items and a no-socket unavailable provider are allowed. The matcher has no write method. Exact requires a non-conflicting DOI or version-compatible arXiv identifier; URL-only is at most probable; title-only is ambiguous. No private library, M5 link write, Article write, or Tier 1 decision write is permitted.

## 14. Zero-Network Controls

Tests and pilot fail closed on socket/HTTP access and browser/network subprocess launch. Any attempted access increments an unexpected-attempt counter before raising. No browser starts. PASS requires `external_network_request_count = 0` and `unexpected_network_attempt_count = 0`.

## 15. Metrics

Record fixture count/failures; pilot IDs/strata; Article/candidate/type/classification counts; classification coverage; DOI/arXiv/URL/malformed exactness; input/output reconciliation; silent drops; provenance completeness; deterministic IDs; duplicate consistency; orphan count; manifest/schema/hash/count/index/referential integrity; stale/corruption/rollback/interrupted recovery; elapsed time, peak memory, rows, and bytes; no-op fingerprints; network counts; Article before/after fingerprints; automatic writes; false exact Zotero matches; artifact violations; and human-review precision.

## 16. Human Review

Review at least 30 deterministic pilot candidates. Include exact/probable candidates up to 20 per group, suspicious high-confidence outputs, and a stable sample of ambiguous/malformed/no-reference results. Record reviewer status, extraction validity, normalized identity, evidence sufficiency, duplicate decision, Zotero decision, and comment. A second reviewer independently reviews at least 10 cases when available; never fabricate one. Disagreement remains in the denominator. A single-review limitation is reported but does not lower the 95% precision threshold or alone block deterministic implementation.

## 17. PASS / CONDITIONAL / BLOCKED

PASS requires at least 60 fixtures with zero failures; 50-100 pilot Articles; complete classification, exact normalization/deduplication/provenance/deterministic-ID/integrity; zero silent drops, network attempts, Article mutation, writes, false exact matches, and tracked artifacts; passing rollback/recovery/no-op; human strong-identifier precision at least 95%; and passing Backend, Frontend, and frozen compatibility checks.

CONDITIONAL applies only when deterministic integrity passes but reviewed precision is below 95% or a finite bounded syntax/rule review remains. Record exact cases and create P3-003.x; P3-006 cannot begin.

BLOCKED applies to Article mutation, wrong exact identity, false exact Zotero match, provenance loss, silent drop, network access/attempt, partial/corrupt install, non-idempotency, frozen regression, test/build failure, artifact/secret, or unauthorized action.

## 18. Verification Commands

```bash
uv run --project backend --extra dev pytest -q backend/tests/references/
uv run --project backend python scripts/references/run_reference_pilot.py \
  --article-store <ignored-article-store> \
  --sample-size 75 \
  --output-dir .local_data/scientific_spaces/references/pilot \
  --no-network
uv run --project backend python scripts/references/audit_reference_store.py \
  --article-store <ignored-article-store> \
  --reference-store .local_data/scientific_spaces/references/pilot \
  --no-network
uv run --project backend --extra dev pytest -q \
  backend/tests/test_article_api.py \
  backend/tests/test_graph.py \
  backend/tests/test_full_corpus_graph.py \
  backend/tests/test_zotero_api.py
uv run --project backend --extra dev pytest -q
npm --prefix frontend run build
uv run --project backend python scripts/references/audit_reference_artifacts.py \
  --repo-root . \
  --reference-store .local_data/scientific_spaces/references/pilot \
  --redact
git diff --check
git status --short
```

## 19. Git Plan

- PASS: `feat: add structured reference extraction pilot`
- CONDITIONAL: `docs: record conditional structured reference pilot`
- BLOCKED: `docs: record structured reference pilot blockers`
- Create one local commit only. Do not push, force-push, amend synchronized history, rebase `main`, create/move tags, or create a Release.

## 20. Stop Conditions

Stop if work requires a path outside the allowlist; M1/Article/frozen API changes; extraction over more than 100 Articles; full-corpus processing; network/real-provider/private-Zotero access; Article mutation; silent drop/provenance loss/wrong exact identity/false exact match; unrecoverable partial store; test/build failure; artifact/secret hit; unknown worktree drift; or unresolved architecture/data/security ambiguity.

## 21. Confirmation

The user explicitly confirmed this alignment and authorized P3-003 implementation, the bounded 75-Article offline pilot, required validation, and one status-appropriate local commit. Push, tag, and Release remain unauthorized.
