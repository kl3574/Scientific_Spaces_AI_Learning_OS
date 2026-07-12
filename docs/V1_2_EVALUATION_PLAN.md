# v1.2 Evaluation Plan

Status: Approved planning contract

No command in this document authorizes a real provider, private Zotero access, or full-corpus reference build. Commands marked **planned** do not exist at P3-002 and must be implemented and verified in the named future milestone.

## Evaluation Principles

1. Deterministic fixtures establish contract correctness; bounded pilots expose corpus variation.
2. Every input candidate or Article reconciles to an output/classification. Silent drops are failures.
3. Article content and frozen contracts are compared before/after every reference run.
4. No-network tests fail on any unexpected socket/HTTP request.
5. Fake-provider and fake-Zotero baselines remain mandatory and reproducible.
6. Automated metrics are not described as true scientific correctness; designated quality fields require human review.
7. Runtime/private output stays ignored and is deleted or retained under an explicit policy.

## P3-003 Structured Reference Pilot

### Fixture Strategy

Commit at least 60 small, synthetic or citation-metadata-only cases. Do not commit long Article bodies. The suite must include positive and negative cases for:

- bare/wrapped DOI, balanced punctuation, malformed DOI, Unicode/confusable text;
- new/old arXiv identifiers, explicit versions, unversioned/versioned pairs, malformed versions;
- HTTP(S), relative/internal, tracking parameters, identity-bearing queries/fragments, credentials, forbidden schemes, IDN hosts;
- citation text without identifiers, title/creator/year variation, possible duplicates, conflicting identifiers;
- same-section duplicate evidence, cross-section and cross-Article evidence, stable/unstable spans;
- no-reference Articles, long citations, high candidate counts, Markdown/math/code/link contexts;
- stale manifests, corrupt JSONL/index/checksum, interrupted install, rollback recovery, and no-op rerun.

### Pilot Selection

- Size: 50-100 Articles; target 75 unless available corpus composition requires another value in the allowed range.
- Selection: deterministic stratification by date range, content length, formula density, link count, reference-like token count, and known no-reference cases.
- Include legacy, long, and math-heavy Articles, but do not weaken frozen Article validity rules.
- Record only Article IDs and aggregate strata in committed reports; do not commit Article bodies or the derived store.
- The pilot is local and offline. It reads an explicitly configured Article store and writes an ignored temporary/pilot directory.

### Metrics and Thresholds

| Metric | PASS threshold |
| --- | ---: |
| Fixture count | >= 60 |
| Input candidate classification coverage | 100% |
| Valid DOI normalization exactness | 100% |
| Valid arXiv normalization exactness | 100% |
| Valid safe-URL normalization exactness | 100% |
| Malformed/forbidden fixture classification exactness | 100% |
| Expected deterministic duplicate behavior | 100% |
| Provenance required-field completeness | 100% |
| Orphan record/evidence/index count | 0 |
| Silent-drop count | 0 |
| Unexpected network requests | 0 |
| Article mutation count/fingerprint change | 0 |
| Automatic Zotero/library/link/decision writes | 0 |
| Same-input no-op integrity | PASS, unchanged file/content fingerprints |
| Strong-identifier human-review precision | >= 95% |
| False `exact` Zotero fixture matches | 0 |

Confidence scores are diagnostic rank values. They are not calibrated probabilities.

### Human Review

- Review at least 30 deterministic pilot candidates: all `exact`/`probable` matches up to 20 each, all false-looking high-confidence candidates, and a deterministic sample of ambiguous/malformed/no-reference outputs.
- Two reviewers are preferred for at least 10 cases; disagreement is reported, not overwritten.
- Review fields: extraction validity, normalized identity, evidence sufficiency, duplicate decision, Zotero decision, and comment.
- Any false `exact` Zotero decision or provenance pointing to the wrong Article/section blocks progression.

### Budget

- Articles: 50-100.
- Network requests: 0.
- Zotero: fake fixture by default; no private library required.
- Candidate evidence returned per API record: default 5, max 20.
- Reference API page: default 20, max 100.
- Runner records elapsed time, peak memory, record/evidence counts, and bytes. P3-003 sets future performance guards from measured pilot evidence rather than inventing a cross-machine SLA.

### Planned Commands

P3-003 must implement equivalent commands before its gate; these paths are planned, not current:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_reference_*.py
uv run --project backend python scripts/references/run_reference_pilot.py \
  --article-store <ignored-article-store> \
  --sample-size 75 \
  --output-dir .local_data/scientific_spaces/references/pilot \
  --no-network
```

## P3-004 Real Provider Evaluation Design

P3-004 implements consent, budget, adapter, output, and fake/dry-run behavior only. It must not make a paid or real-provider request without a separate user authorization after that design passes.

### Case Taxonomy

The fixed metadata-only case set covers:

- `explain`, `derive`, `qa`, `quiz`, and `research`;
- `unsupported`, `no_source`, and `citation_conflict`;
- `long_context` with bounded truncation;
- `provider_error` including timeout, 429/rate limit, malformed response, and server failure.

Each case has ID, expected mode, expected Article IDs, expected refusal, allowed source count, sensitive-data classification, human-review rubric, and deterministic fake baseline. No fixture contains a copyrighted long Article body.

### Consent and Budget Tests

The dry-run gate proves:

- real provider selection without any required acknowledgement/cap/case/output setting fails before adapter construction;
- the preflight exactly lists data categories, case/request counts, provider/model, cost cap, and Article-snippet policy;
- notes, Learning state, Tutor history, private Zotero metadata, complete corpus, local paths, keys, and auth headers cannot enter a request envelope;
- request count, timeout, retry, context/output, and estimated-cost caps stop additional work;
- unknown pricing blocks a cost-bounded real run rather than silently reporting zero;
- CI/default startup cannot select the real path.

### Reliability Metrics

- request success rate;
- timeout rate;
- retry rate and retry count;
- rate-limit count;
- sanitized provider error taxonomy;
- validation and budget-stop counts.

### Latency Metrics

For successful requests: minimum, mean, median, p95, and maximum milliseconds. Dataset size and warm/cold conditions accompany the result.

### Usage and Cost Metrics

- input, output, and embedding tokens;
- provider-reported request/usage values when available;
- provider-reported cost when available;
- estimated cost only with dated pricing source, currency, formula, and assumptions;
- request and cost budget violations.

No projected business value or unqualified cost comparison is permitted.

### Grounding Metrics

- citation schema validity and required source support;
- citation faithfulness under the review rubric;
- answers without sources and unsupported fabrications;
- refusal correctness and Derive evidence compliance;
- source-count/context bounds.

### Quality and Human Review

- correctness, relevance, completeness, mathematical consistency, and clarity use explicit ordinal rubrics;
- every rating records review status and reviewer disagreement;
- automated lexical/format heuristics remain separate fields and are never named answer correctness;
- a real model comparison is invalid if provider/model/config/case versions differ without disclosure.

### Output and Retention

```text
.local_data/scientific_spaces/evaluation/real_provider/
<run-id>/
├── run.json
├── cases.jsonl          # redacted
├── aggregate.json
└── raw/                 # absent by default
```

- Aggregate reports: retained locally until operator deletion.
- Redacted case reports: 30-day default retention.
- Raw output: disabled; if separately authorized, 7-day default retention and Tier 3.
- A planned deletion command must support run ID and age threshold, dry-run by default, and refuse paths outside the configured evaluation root.
- Output scans reject credentials, auth headers, private user/Zotero fields, absolute paths, and forbidden runtime artifact copies.

### Planned Commands

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_real_provider_evaluation_*.py
uv run --project backend python scripts/eval/run_real_provider_eval.py \
  --provider fake \
  --case-set backend/tests/fixtures/evaluation/<planned-case-set>.json \
  --dry-run \
  --output-dir .local_data/scientific_spaces/evaluation/real_provider/dry-run
```

The planned command must pass with fake/dry-run and zero network requests.

## P3-005 CI Security and Release Provenance

### Test Matrix

| Area | Evidence |
| --- | --- |
| Baseline CI | Backend pytest and Frontend build on PR/main; Docker on manual/tag |
| Action integrity | Every third-party `uses:` value is a full immutable SHA with source-version comment |
| Permissions | Workflow default and per-job permissions match the approved least-privilege matrix |
| Python dependencies | Locked graph audited by pinned Python scanner |
| npm dependencies | `package-lock.json` audited by npm and independent OSV-compatible scanner |
| Secrets | Tracked-file and bounded-history scan; GitHub secret scanning status when available |
| Suppressions | Schema, exact scope, owner, URL, and future expiry validation |
| SBOM | CycloneDX schema, both ecosystems, exact commit, bounded/deterministic fields |
| Provenance | Exact tag/ref/SHA/subject digest and GitHub attestation verification |
| Artifact policy | No runtime/private file, local path, or secret in scan/SBOM/provenance output |

### Severity Policy

- Unsuppressed Critical or High runtime dependency finding: BLOCKED.
- Medium finding: must be fixed or have a narrowly reviewed, unexpired suppression before release; it remains visible.
- Low finding: reported and triaged; not automatically release-blocking.
- Secret finding with credible credential material: BLOCKED and incident handling; never print the value.
- Scanner failure, stale database beyond documented tolerance, or policy-validator failure: release gate fails closed.
- Suppression expiry and version-scope mismatch are failures, not warnings.

### SBOM Budget

- Format: CycloneDX 1.6 JSON.
- Ecosystems: complete locked Python and npm graphs.
- Maximum artifact size: 5 MiB.
- Commit-derived timestamp and sorted normalized components support reproducibility.
- Zero absolute paths, secret patterns, and forbidden runtime names.
- Project commit, tool versions, component counts, and SHA-256 are recorded.

### Provenance Evidence

- Exact annotated tag and peeled commit.
- Tag-triggered workflow name, file, run ID/URL, ref, and SHA.
- Backend, frontend, Docker, scan, and SBOM results.
- SBOM and release-evidence subject digests.
- GitHub attestation URL and verification command.
- Evidence that earlier published tags were not moved.

## P3-006 Full-Corpus Reference Build and Matching

This milestone requires a separate future authorization. It does not run during P3-002.

### Budget and Gate

- Input: exactly the then-current validated Article-store count and fingerprint; the v1.1 baseline is 1,311.
- Network requests: 0.
- Every input Article has a terminal processing status.
- Candidate classification coverage, provenance completeness, referential integrity, and Article immutability: 100%.
- Silent drops, corrupt rows, orphan indexes, duplicate IDs, and unexpected writes: 0.
- Repeated unchanged run: validated no-op with unchanged build/content fingerprints.
- Corruption and failed replacement preserve or restore the previous valid store.
- Zotero matching acceptance uses fake/curated fixtures. A private local library remains optional and separately authorized; absence cannot invalidate extraction.

## P3-007 Integration and Release Readiness

Required evidence:

- all frozen legacy and `/v1.1` compatibility suites;
- M3-M7 grounding/refusal/provenance suites;
- JSON default, SQLite opt-in migration/export, backup/restore, and cleanup protection;
- reference API/UI bounded smoke and stale/error/ambiguity states;
- fake/dry-run provider safety suite;
- backend pytest, frontend build, manual/tag Docker;
- dependency/secret policy, CycloneDX SBOM, exact-tag attestation;
- documentation consistency, artifact/private-data scan, and no unresolved Critical/Important architecture or release finding.

A real-provider run and private Zotero access are not required release gates. If separately run, their evidence is explicitly labeled optional and cannot replace deterministic gates.

## Failure Taxonomy

| Domain | Codes/Classes |
| --- | --- |
| Reference input | unsupported, malformed, rejected, over_limit |
| Reference integrity | source_missing, span_invalid, orphan_evidence, count_mismatch, checksum_mismatch, stale_store, corrupt_store |
| Deduplication | identifier_conflict, version_conflict, url_conflict, possible_text_duplicate |
| Zotero | provider_unavailable, item_missing, exact, probable, ambiguous, unmatched, rejected, stale_item |
| Provider | consent_missing, budget_invalid, budget_stopped, timeout, rate_limited, auth_error, server_error, malformed_response, validation_error |
| CI | immutable_pin_failure, permission_failure, dependency_finding, secret_finding, scanner_failure, suppression_invalid, sbom_invalid, attestation_invalid |

Failures retain identifiers, safe context, owner, and remediation without secrets or Article bodies.

## No-Network Verification

- Reference and fake-provider tests monkeypatch socket/HTTP clients to fail on any call.
- Browser/network processes are not launched by reference builds.
- Zotero-unavailable tests point to a closed loopback endpoint only; no private library is read.
- CI fixture jobs require no external product/provider service beyond dependency installation and GitHub platform actions.
- Reports record `network_request_count=0` for reference and fake/dry-run evaluation.

## Artifact Policy

Never commit or attach:

- Article corpus/content exports, full reference stores, private Zotero payloads or decisions;
- provider prompts/raw output, API keys, authorization headers, `.env`, databases, backups;
- PDF, image, RAG/FAISS, Graph, HTML, browser profile/trace/cache, logs, or local absolute paths.

Committed fixtures contain synthetic/bounded metadata only. Committed reports use counts, IDs, hashes, safe URLs, and aggregate metrics.

## Release Evidence Decision

P3-007 may recommend candidate assignment only when all mandatory deterministic and security gates pass. Exact-tag CI, SBOM, and attestation occur only after a separately authorized release operation. A real-provider quality report is optional comparative evidence and cannot turn a failing grounding/compatibility gate into PASS.
