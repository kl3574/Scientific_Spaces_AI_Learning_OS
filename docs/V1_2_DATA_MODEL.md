# v1.2 Data Model

Status: Approved planning contract

## Conventions

### Serialization

- JSON and JSONL are UTF-8 without a byte-order mark.
- Canonical content serialization uses sorted object keys, compact separators, finite numbers only, and one trailing newline per JSONL record.
- Record arrays and JSONL rows use documented stable ID ordering. Set-like fields are deduplicated and sorted.
- Timestamps use UTC RFC 3339 with `Z`. Timestamps never define record identity and are excluded from deterministic content fingerprints.
- IDs use a model-specific prefix plus lowercase SHA-256 over a versioned canonical identity string. Truncated hashes must retain at least 128 bits.
- Optional values serialize as `null`; missing required keys are invalid.
- Local absolute paths, credentials, auth headers, and unredacted credential-bearing URLs are invalid in every model.

### Privacy Classes

| Class | Meaning |
| --- | --- |
| `public_project` | Repository metadata or public source identifiers safe for committed fixtures/reports |
| `local_corpus` | Derived from Article content; local runtime data that is not committed |
| `private_user` | Zotero metadata, review decisions, notes, or provider output tied to a local user |
| `secret` | Credentials, tokens, authorization headers; forbidden in all records |

### Storage Tiers

| Tier | Meaning |
| --- | --- |
| Tier 1 | Authoritative user/project state requiring backup and protected cleanup |
| Tier 2 | Rebuildable output derived from Tier 1 sources |
| Tier 3 | Disposable cache, raw debug output, log, staging, or temporary data |

## ReferenceRecord

One canonical reference identity plus complete links to its evidence. Deterministic exact duplicates merge into one record; possible textual duplicates remain separate records with the same duplicate group.

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `reference-record/v1` |
| `reference_id` | string | yes | Stable hash ID from type and canonical identity or candidate identity |
| `reference_type` | enum | yes | `doi`, `arxiv`, `http_url`, `relative_or_internal_url`, `citation_text`, `unsupported`, `malformed` |
| `classification` | enum | yes | `extracted`, `normalized`, `duplicate`, `ambiguous`, `unsupported`, `malformed`, `rejected` |
| `canonical_key` | string/null | yes | Versioned normalized identity used for exact grouping; null when unsupported |
| `normalized_identifier` | string/null | yes | Canonical DOI/arXiv identifier or conservative text candidate key |
| `normalized_url` | string/null | yes | Safely normalized HTTP(S) URL |
| `doi` | string/null | yes | Lowercase DOI without wrapper |
| `arxiv_id` | string/null | yes | Canonical base arXiv ID without `vN` |
| `arxiv_version` | integer/null | yes | Explicit positive version, otherwise null |
| `source_article_id` | string | yes | Deterministically selected primary evidence Article ID |
| `source_article_title` | string | yes | Primary evidence Article title |
| `source_article_url` | HTTP(S) URL | yes | Primary evidence canonical Article URL |
| `source_section` | string | yes | Primary nearest Markdown heading or exact sentinel `__article_root__` |
| `source_span_start` | integer/null | yes | Stable primary start offset into the exact Article content, when available |
| `source_span_end` | integer/null | yes | Exclusive primary end offset; null with start when unstable |
| `evidence_text` | string | yes | Bounded, display-safe primary evidence |
| `raw_reference` | string | yes | Exact raw candidate unless sensitive URL userinfo required redaction |
| `evidence_ids` | string[] | yes | Complete, sorted references to `ReferenceEvidence` rows |
| `source_count` | integer | yes | Complete distinct evidence count; equals `len(evidence_ids)` |
| `extraction_rule` | string | yes | Stable extractor rule name |
| `extraction_rule_version` | string | yes | Rule-set version used for this record |
| `confidence` | number | yes | Deterministic extractor confidence in `[0,1]`; not a correctness probability |
| `duplicate_group_id` | string/null | yes | Stable exact or possible-duplicate group ID |
| `corpus_fingerprint` | string | yes | Source Article corpus fingerprint |
| `build_id` | string | yes | Reference manifest build fingerprint |
| `record_fingerprint` | string | yes | SHA-256 over canonical record fields excluding timestamps/build ID |

Invariants:

- DOI records require `doi == normalized_identifier` and no arXiv value.
- arXiv records require `arxiv_id`; their canonical key includes an explicit version marker (`none` or `vN`).
- HTTP URL records require an allowed normalized URL with no credentials.
- Citation-text records do not claim an exact paper identity.
- `source_span_start` and `source_span_end` are both null or satisfy `0 <= start < end <= len(Article.content)`.
- The primary source fields match the first evidence under deterministic evidence ordering.
- No record contains full Article content.

Serialization: one row in `records.jsonl`.

Privacy/Tier: `local_corpus`, Tier 2.

## ReferenceEvidence

An immutable occurrence supporting a reference record.

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `reference-evidence/v1` |
| `evidence_id` | string | yes | Stable hash of Article, section, stable span/raw hash, and rule version |
| `reference_id` | string | yes | Owning canonical reference |
| `source_article_id` | string | yes | Frozen Article ID |
| `source_article_title` | string | yes | Frozen Article title |
| `source_article_url` | HTTP(S) URL | yes | Frozen canonical source URL |
| `source_section` | string | yes | Nearest Markdown heading or exact sentinel `__article_root__` |
| `source_span_start` | integer/null | yes | Stable candidate start offset |
| `source_span_end` | integer/null | yes | Stable exclusive end offset |
| `evidence_text` | string | yes | Bounded context around the candidate |
| `raw_reference` | string | yes | Raw or security-redacted candidate |
| `raw_reference_hash` | string | yes | Hash of the original candidate bytes; never reversible |
| `candidate_ordinal` | integer | yes | Zero-based deterministic occurrence order in the Article |
| `extraction_rule` | string | yes | Rule name |
| `extraction_rule_version` | string | yes | Rule version |
| `classification` | enum | yes | Initial candidate classification, including rejected/malformed |
| `corpus_fingerprint` | string | yes | Source corpus identity |

Invariants:

- Same Article/section/span-or-raw-hash/rule duplicates collapse to one evidence row.
- Evidence from different Articles never collapses.
- Credential userinfo and forbidden schemes are redacted/classified before serialization.
- Evidence length is bounded by configuration recorded in the manifest.

Serialization: one row in `evidence.jsonl`.

Privacy/Tier: `local_corpus`, Tier 2.

## ReferenceManifest

The integrity and lifecycle root for a Reference Store.

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `reference-manifest/v1` |
| `record_schema_version` | string | yes | Expected `ReferenceRecord` schema |
| `evidence_schema_version` | string | yes | Expected `ReferenceEvidence` schema |
| `candidate_schema_version` | string | yes | Expected Zotero candidate schema |
| `corpus_fingerprint` | string | yes | Source Article fingerprint |
| `corpus_fingerprint_version` | integer | yes | Fingerprint algorithm version |
| `extractor_version` | string | yes | Whole extraction rule-set version |
| `normalization_version` | string | yes | Normalization contract version |
| `matcher_version` | string/null | yes | Zotero matcher version or null when not run |
| `configuration_fingerprint` | string | yes | Safe, secret-free canonical build configuration hash |
| `build_fingerprint` | string | yes | Deterministic identity over source/config/schema/content hashes |
| `generated_at` | timestamp | yes | Audit timestamp, excluded from build identity |
| `status` | enum | yes | `complete`; other values cannot be installed as current |
| `counts` | object | yes | Articles, candidates, records, evidence, classifications, duplicates, failures |
| `files` | object[] | yes | Relative path, byte size, row count, SHA-256 |
| `source_asset_id` | string | yes | Logical Article-store asset name, never an absolute path |
| `rebuild_command` | string | yes | Repository-relative planned CLI invocation with no private path |
| `network_request_count` | integer | yes | Must be zero for reference builds |
| `integrity_rule_version` | string | yes | Audit rule version |

Invariants:

- Every listed file exists and matches size/hash/row count.
- Every record/evidence/index/candidate reference resolves exactly once.
- Count totals reconcile with row classifications and no silent-drop equation.
- `build_fingerprint` excludes `generated_at` but includes every content digest.
- Only a complete, validated manifest may be atomically installed.

Serialization: `manifest.json`.

Privacy/Tier: `local_corpus`, Tier 2.

## ZoteroMatchCandidate

A minimal, explainable comparison against one read-only Zotero item.

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `zotero-match-candidate/v1` |
| `candidate_id` | string | yes | Stable hash of reference, item key, and matcher version |
| `reference_id` | string | yes | Input reference |
| `zotero_item_key` | string/null | yes | Local Zotero item key; null for the explicit unmatched outcome |
| `item_type` | string/null | yes | Zotero item type; null for unmatched |
| `title` | string/null | yes | Bounded item title; null for unmatched |
| `doi` | string/null | yes | Normalized item DOI |
| `url` | string/null | yes | Safe normalized item URL |
| `arxiv_id` | string/null | yes | Extracted canonical item arXiv base ID |
| `arxiv_version` | integer/null | yes | Explicit item version |
| `match_method` | enum | yes | `doi_exact`, `arxiv_exact`, `url_normalized`, `title_creator_year`, `combined` |
| `match_score` | number | yes | Deterministic ranking score in `[0,1]`, not a correctness probability |
| `matched_fields` | string[] | yes | Sorted fields that agree |
| `conflicting_fields` | string[] | yes | Sorted strong fields that conflict |
| `provenance` | object | yes | Reference evidence IDs and safe matcher/rule versions |
| `decision` | enum | yes | `exact`, `probable`, `ambiguous`, `unmatched`, `rejected` |
| `matcher_version` | string | yes | Matching rule-set version |
| `zotero_snapshot_fingerprint` | string/null | yes | Hash over compared minimal fields, not the complete library; null for unmatched |

Invariants:

- `exact` requires DOI or version-compatible arXiv equality and zero conflicting strong fields.
- URL-only matches are at most `probable`; title-only matches are `ambiguous`.
- `unmatched` uses null item fields and a stable candidate ID derived from the reference plus the unmatched sentinel.
- Candidate rows never imply a user decision and never trigger a write.
- Abstracts, notes, collections, tags, attachments, and complete-library exports are excluded.

Serialization: one row in `zotero_candidates.jsonl`.

Privacy/Tier: `private_user` when built from a real local library, otherwise `local_corpus`; Tier 2.

## UserReviewedReferenceDecision

Authoritative explicit local review state, separated from rebuildable candidates.

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `reference-review-decision/v1` |
| `decision_id` | string | yes | Stable local decision ID |
| `reference_id` | string | yes | Reviewed reference ID at decision time |
| `reference_canonical_key` | string/null | yes | Reconciliation key across derived rebuilds |
| `candidate_id` | string/null | yes | Reviewed candidate, if one existed |
| `zotero_item_key` | string/null | yes | Selected/rejected local item key |
| `decision` | enum | yes | `confirmed`, `rejected`, `corrected`, `cleared` |
| `manual_identifier` | string/null | yes | Explicit correction, never inferred automatically |
| `reason_code` | string | yes | Structured review rationale |
| `annotation` | string/null | yes | Optional bounded private note |
| `reviewer` | string | yes | Local opaque profile ID, default `local-user`; no identity claim |
| `created_at` | timestamp | yes | Creation time |
| `updated_at` | timestamp | yes | Last explicit change |
| `source_build_fingerprint` | string | yes | Derived build reviewed |
| `decision_fingerprint` | string | yes | Integrity hash over decision content |

Invariants:

- Only an explicit user operation creates/changes a decision.
- A derived rebuild never deletes or rewrites decisions.
- Stale/unresolved canonical keys are reported for review and not silently rebound.
- Decision storage uses atomic replacement, backup, and schema validation.

Serialization: values in `.local_data/scientific_spaces/references/reviewed/decisions.json`, keyed by `decision_id`.

Privacy/Tier: `private_user`, Tier 1.

## ProviderEvaluationRun

Aggregate identity, consent, budget, and outcome for one fake/dry-run or separately authorized real-provider evaluation.

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `provider-evaluation-run/v1` |
| `run_id` | string | yes | Random local run ID; not derived from a secret |
| `provider_kind` | enum | yes | `fake`, `real` |
| `provider_name` | string | yes | Adapter/provider name |
| `model_name` | string | yes | Requested model |
| `model_version_identifier` | string/null | yes | Provider-reported or operator-recorded version |
| `endpoint_category` | enum | yes | `embedding`, `chat`, `combined` |
| `requested_at` | timestamp | yes | Run start |
| `completed_at` | timestamp/null | yes | Terminal time |
| `configuration_fingerprint` | string | yes | Secret-free config hash |
| `embedding_dimension` | integer/null | yes | Embedding dimension when relevant |
| `context_limit` | integer/null | yes | Documented context limit |
| `output_limit` | integer/null | yes | Configured output cap |
| `retry_settings` | object | yes | Bounded attempts/backoff |
| `timeout_seconds` | number | yes | Per-request timeout |
| `pricing_metadata_source` | string/null | yes | Dated public/operator source, no credential URL |
| `consent` | object | yes | Explicit booleans for real provider and data sent |
| `data_categories_sent` | string[] | yes | Declared categories; excludes private user/Zotero data |
| `case_set_id` | string | yes | Fixed dataset ID/version |
| `case_count` | integer | yes | Selected cases |
| `max_requests` | integer | yes | Hard request cap |
| `max_estimated_cost` | number | yes | Hard currency cap for real runs |
| `currency` | string | yes | ISO currency code |
| `provider_reported_usage` | object | yes | Aggregate tokens/requests when available |
| `cost` | object | yes | Reported and estimated aggregate cost with assumptions |
| `result_counts` | object | yes | Success/error/refusal/review counts |
| `status` | enum | yes | `planned`, `running`, `completed`, `budget_stopped`, `failed`, `cancelled` |
| `output_policy` | object | yes | Redaction/raw/retention settings |

Invariants:

- Real runs require all consent flags and positive request/cost caps before any request.
- API keys, authorization headers, secret environment values, full sensitive prompts, and raw sensitive metadata are forbidden.
- Aggregate usage reconciles with case results; cap violations stop new requests.

Serialization: aggregate `run.json` under ignored evaluation output.

Privacy/Tier: `private_user` for real output, `local_corpus` for fake; Tier 2 aggregate, Tier 3 raw/debug.

## ProviderEvaluationCaseResult

One bounded, redacted result within a provider run.

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `provider-evaluation-case/v1` |
| `run_id` | string | yes | Parent run |
| `case_id` | string | yes | Fixed case ID |
| `task_type` | enum | yes | `explain`, `derive`, `qa`, `quiz`, `research`, `unsupported`, `no_source`, `citation_conflict`, `long_context`, `provider_error` |
| `expected_mode` | string | yes | Expected application mode |
| `expected_source_ids` | string[] | yes | Public Article IDs only |
| `expected_refusal` | boolean | yes | Refusal expectation |
| `allowed_source_count` | integer | yes | Case budget |
| `sensitive_data_classification` | enum | yes | `public_fixture` or `local_corpus_excerpt`; private-user cases are prohibited |
| `request_index` | integer | yes | Monotonic request number |
| `status` | enum | yes | `success`, `timeout`, `rate_limited`, `provider_error`, `validation_error`, `budget_skipped` |
| `latency_ms` | number/null | yes | End-to-end request latency |
| `retry_count` | integer | yes | Bounded retry count |
| `usage` | object | yes | Input/output/embedding token counts when available |
| `estimated_cost` | number/null | yes | Case cost under recorded pricing assumptions |
| `source_ids_returned` | string[] | yes | Citation identity only |
| `metrics` | object | yes | Grounding/refusal/derive checks, never labeled true correctness |
| `response_digest` | string/null | yes | Digest of raw response when retained in memory |
| `redacted_response` | string/null | yes | Optional bounded redacted text |
| `provider_error_code` | string/null | yes | Sanitized taxonomy value |
| `human_review` | object | yes | Correctness/relevance/completeness/math/clarity/status/disagreement fields |

Invariants:

- Case results contain no API key, auth header, private user data, private Zotero metadata, or local absolute path.
- Automated heuristics are stored as metrics, never as `correct=true` unless a human rubric supplies that judgment.
- Raw provider metadata is not serialized.

Serialization: one row in a redacted `cases.jsonl`; optional raw output is a separate Tier 3 file and defaults off.

Privacy/Tier: `private_user` for real output, otherwise `local_corpus`; Tier 2 redacted, Tier 3 raw.

## SecurityFindingSuppression

A reviewable, expiring exception for a dependency or secret-scanner finding.

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `security-suppression/v1` |
| `suppression_id` | string | yes | Stable repository ID |
| `scanner` | string | yes | Scanner/tool identity |
| `finding_id` | string | yes | Advisory/rule fingerprint |
| `ecosystem` | string/null | yes | Python, npm, GitHub Actions, secret, or null |
| `package_or_path` | string | yes | Narrow package/path scope; no secret value |
| `severity` | enum | yes | `critical`, `high`, `medium`, `low`, `unknown` |
| `rationale` | string | yes | Technical accepted-risk explanation |
| `owner` | string | yes | Maintainer role/account |
| `review_url` | HTTP(S) URL | yes | Issue/advisory/review evidence |
| `created_at` | date | yes | Approval date |
| `expires_on` | date | yes | Mandatory expiry |
| `scope_fingerprint` | string | yes | Exact finding/package/path/version scope |

Invariants:

- Expired, overbroad, unmatched, ownerless, or linkless suppressions fail policy validation.
- Suppressions never contain a matched secret or disable an entire scanner.
- A dependency version change invalidates a version-scoped suppression unless re-reviewed.

Serialization: planned tracked YAML/JSON policy under `.github/security/`, reviewed as code.

Privacy/Tier: `public_project`, repository policy (not runtime tier).

## ReleaseProvenanceRecord

Small release evidence record linking exact Git objects, workflow identity, SBOM, and attestation.

| Field | Type | Required | Definition |
| --- | --- | --- | --- |
| `schema_version` | string | yes | `release-provenance/v1` |
| `release_version` | string | yes | Exact release version |
| `tag_name` | string | yes | Annotated release tag |
| `tag_object_sha` | SHA-1/SHA-256 string | yes | Git tag object identity |
| `peeled_commit_sha` | SHA-1/SHA-256 string | yes | Exact source commit |
| `repository` | string | yes | `kl3574/Scientific_Spaces_AI_Learning_OS` |
| `workflow_name` | string | yes | GitHub Actions workflow |
| `workflow_file` | string | yes | Repository-relative workflow path |
| `workflow_run_id` | integer | yes | GitHub run database ID |
| `workflow_run_url` | HTTP(S) URL | yes | Evidence URL |
| `workflow_ref` | string | yes | Exact tag ref |
| `workflow_sha` | string | yes | Must equal peeled commit |
| `build_subjects` | object[] | yes | Relative artifact name, media type, byte size, SHA-256 |
| `sbom_format` | string | yes | `CycloneDX-1.6-JSON` |
| `sbom_sha256` | string | yes | SBOM digest |
| `attestation_subject_digest` | string | yes | Verified subject digest |
| `attestation_url` | HTTP(S) URL | yes | GitHub attestation evidence |
| `generator_versions` | object | yes | SBOM/attestation tools and immutable Action SHAs |
| `build_timestamp` | timestamp | yes | Deterministic tag/commit-derived timestamp |
| `verification_commands` | string[] | yes | Safe public verification commands |
| `artifact_policy_result` | enum | yes | `pass` only when forbidden-artifact scan is clean |

Invariants:

- Tag, workflow ref, workflow SHA, and peeled commit agree exactly.
- Every subject digest verifies and is bounded.
- Subjects exclude corpus, Article store, PDF, RAG, Graph, database, backup, private provider/Zotero data, secrets, and absolute paths.
- Attestation permission is present only in the dedicated release evidence job.

Serialization: bounded release-evidence JSON and corresponding GitHub attestation.

Privacy/Tier: `public_project`, release artifact/evidence.

## Normalization Policy

### DOI

1. Apply conservative Unicode normalization to wrapper text while preserving the raw candidate.
2. Accept bare `10.<registrant>/<suffix>`, `doi:`, `https://doi.org/`, and `http://dx.doi.org/` forms.
3. Remove the wrapper and surrounding whitespace; lowercase the DOI because DOI names are case-insensitive.
4. Remove only whitespace-separated or structurally unmatched terminal punctuation (`.`, `,`, `;`, `:`, or unmatched closing bracket). Never strip DOI-valid internal punctuation or a balanced closing parenthesis.
5. Validate the complete candidate locally. Never resolve it over the network.

### arXiv

- New style: `YYMM.NNNN` or `YYMM.NNNNN`, optional `vN`.
- Old style: lowercase archive/category plus `/NNNNNNN`, optional `vN`.
- Store the base in `arxiv_id` and an explicit version in `arxiv_version`.
- Exact identity includes the version state. Two equal explicit versions merge; two different versions do not. Versioned and unversioned records may share a possible-version duplicate group but do not exact-merge.

### URL

- Permit only `http` and `https`; lowercase scheme and IDNA-normalized host, remove default ports, normalize dot segments and percent-encoding of unreserved bytes, and preserve path case.
- Preserve unknown query keys, values, order, and duplicates. Remove only the explicit tracking allowlist: `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `gclid`, and `fbclid`.
- Preserve non-empty fragments because they may identify a document section; only an empty trailing `#` is removed.
- Reject missing/invalid hosts, local/executable schemes, and URLs containing userinfo. Redact userinfo before evidence serialization and store only a one-way raw hash.
- Resolve relative/internal links only against the canonical Article origin and keep their type distinct; they do not identify a paper automatically.

### Citation Text

- Normalize whitespace and maintain a separate casefolded comparison key while preserving bounded original evidence.
- Text without DOI/arXiv/URL remains a candidate. It cannot set an exact identity or exact Zotero decision.
- Similarity features may use title, creator, year, and venue tokens only for ranking/grouping, with uncertainty exposed.

## Deduplication Policy

1. **Exact identifier duplicate:** equal DOI canonical keys or equal version-aware arXiv canonical keys merge. All evidence is retained.
2. **Normalized URL duplicate:** equal complete safe normalized URLs merge when no strong identifier conflict exists. A conflict keeps records separate and marks them ambiguous.
3. **Possible textual duplicate:** deterministic similarity may assign a shared group, but records never merge automatically.

`duplicate_group_id` is a stable hash over group type, rule version, and key. `source_count` always reflects complete unique evidence even when an API returns a bounded subset.

## Versioning and Migration

- Schema versions change when fields, requiredness, semantics, or normalization identity change.
- Extraction/normalization/matcher rule versions change when behavior changes even if schemas do not.
- A compatible reader may read older schemas but never rewrite them in place.
- Derived stores migrate by staged converter plus validation or by rebuild from Articles. The old directory remains rollback evidence until installation verifies.
- Tier 1 review decisions require an explicit forward/reverse migration, backup, identity reconciliation, and count/fingerprint audit.
- Any Article `metadata.references` migration is outside this contract and requires a separate M1.x decision.
