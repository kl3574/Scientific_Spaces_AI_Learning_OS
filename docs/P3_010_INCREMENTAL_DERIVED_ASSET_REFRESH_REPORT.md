# P3-010 Incremental Derived Asset Refresh Report

Date: 2026-07-29

Status: **PASS / CLOSED**

## 1. Scope

P3-010 refreshes three persisted local derived assets from the exact current
Article Store:

```text
1,314-Article Store
  -> deterministic fake RAG build
  -> deterministic Knowledge Graph build
  -> deterministic structured Reference build
  -> staged integrity and compatibility validation
  -> recoverable prior-snapshot backup
  -> coordinated transactional install
  -> post-install validation
```

It does not access Scientific Spaces, use browser acquisition, read or write
private Zotero, call a real Provider, mutate Article records, modify frozen M1
modules, change published APIs, assign a candidate, or create a tag or
Release.

## 2. Exact Source Identity

- Article count: 1,314
- Article Store SHA-256:
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`
- corpus fingerprint:
  `ff2824ca675ee0f7b6d82d8a3c63a08c5d3f6df99f5b79495c896367c8afbce6`
- duplicate or missing target Articles: 0
- Article Store SHA before/after refresh: unchanged

Target mapping:

| Archive | Article ID | Title |
| --- | --- | --- |
| 11814 | `5bb93e76eca2e42d` | LogSumExp和Softmax的泰勒展开 |
| 11818 | `0a1ea65bc70bf1cf` | 基于排序不等式的相似度指标 |
| 11823 | `bc334b1d82463d02` | 将Softmax Attention线性化为Gated DeltaNet |

## 3. Implementation

`backend/app/operations/derived_refresh.py` provides:

- exact count, byte SHA, corpus fingerprint, and target-Article preflight;
- a default read-only inspection path;
- an exclusive local refresh lock;
- isolated RAG, Graph, and Reference staging builds;
- an outer zero-network guard plus existing Reference network guard;
- staged and post-install integrity validation;
- recoverable pre-install backup with per-component tree digests;
- atomic directory replacement for each component and complete-bundle rollback
  on install or post-install failure;
- semantic target-Article checks across all three assets; and
- idempotent no-op when the installed bundle already matches.

`scripts/ops/refresh_derived_assets.py` exposes the operation as an explicit
CLI. `--execute` is required for writes. Expected count, SHA, and fingerprint
are mandatory, and output is restricted to ignored `.local_data`.

The three component directory renames are coordinated under one refresh lock
and rolled back as one bundle. POSIX does not provide one rename spanning
three existing directory roots, so concurrent application readers are not a
globally isolated database transaction during the brief switch. The completed
state is all-or-nothing, and local operators should avoid starting a long-lived
service during a refresh.

## 4. Dry-Run Evidence

The initial command ran without `--execute` and returned:

- action: `refresh_required`
- current RAG Article count: 1,311
- current Graph Article count: 1,311
- current Reference Article count: 1,311
- common stale fingerprint:
  `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d`
- approved source count: 1,314
- install performed: false
- backup created: false
- external network requests: 0

No `derived_refresh` runtime directory existed after the dry-run.

## 5. Build Result

| Asset | Article count | Main output | Fingerprint |
| --- | ---: | --- | --- |
| RAG | 1,314 | 5,570 chunks, 100% Article coverage | current corpus fingerprint |
| Graph | 1,314 | 53,046 nodes, 82,584 edges | `456ff4f53c9ca9b025b022d75d0480d1d44859e99b2cb36be1d18f52317f191e` |
| References | 1,314 | 12,904 records, 24,598 evidence rows | `d50e5850872b383d77d4b4dd28180a0eea6829e0a1d3b5d161dde0e3efe135fd` |

RAG uses `deterministic-hash-v1`, dimension 128. Reference extraction
accounting, classification reconciliation, provenance completeness,
deterministic IDs, duplicate-group consistency, and resource budgets passed.
Reference matching used fake-curated and unavailable modes only.

The Reference build remains `CONDITIONAL` solely because the previously
accepted P3-006 human-review remainder is still pending/waived. All P3-010
machine gates passed; P3-010 does not claim a new human precision result.

## 6. Recovery and Installation

Before installation, the complete prior RAG, Graph, and Reference roots were
copied to:

```text
.local_data/scientific_spaces/derived_refresh/backups/
  20260729T122024Z-ff2824ca675e-ecd6233c/
```

Backup evidence:

| Component | Prior Articles | Prior fingerprint | Files | Bytes | Tree SHA-256 |
| --- | ---: | --- | ---: | ---: | --- |
| RAG | 1,311 | `cc8717...cdf5d` | 6 | 18,512,367 | `f073658a63e15b7b2fcee9b0db79c64bdb267be09486dc3f99fe98bee2e86488` |
| Graph | 1,311 | `cc8717...cdf5d` | 9 | 75,309,694 | `54c1434e31346c57d9fb1e65453cc95a8eb0a337cf485d083a04ff292dfa73ab` |
| References | 1,311 | `cc8717...cdf5d` | 1,328 | 98,228,222 | `fb2508c64e300a56dd5e69d4d1bdcde77f90a7b58723b653560f93a2097f7e97` |

The backup is ignored and not committed. Staged validation passed before any
production rename. Post-install validation passed after all three renames.
No rollback cleanup warning, staging directory, rollback directory, or
temporary artifact remained.

## 7. New Article Coverage

| Archive | RAG chunks | RAG rank | Graph nodes | References | Evidence |
| --- | ---: | ---: | ---: | ---: | ---: |
| 11814 | 7 | 1 | 78 | 23 | 28 |
| 11818 | 7 | 1 | 84 | 20 | 24 |
| 11823 | 9 | 1 | 126 | 25 | 32 |

RAG ranking used each title plus bounded Article evidence. Graph checks used
the Article ID filter. Reference checks used the complete Article index, so an
Article with zero references would still be represented rather than treated
as missing.

## 8. Idempotency and Failure Evidence

The immediate second `--execute` invocation returned:

- action: `no_op`
- install performed: false
- backup path: null
- new backup count: 0
- RAG/Graph/Reference manifest timestamps: unchanged
- Article Store SHA: unchanged

Focused tests cover:

- default read-only CLI and API behavior;
- ignored-output path enforcement;
- independent deterministic semantic fingerprints;
- staged end-to-end fixture refresh;
- verified prior-state backup;
- no-op rerun;
- injected build failure before installation;
- injected failure after a component rename; and
- injected post-install validation failure.

Both installation failure tests restored all three prior components with
matching tree content.

## 9. Compatibility Evidence

Real local-asset TestClient smoke passed:

- `GET /health`: PASS
- legacy `GET /articles?q=...`: PASS
- `GET /v1.1/articles?q=...`: PASS
- legacy Article detail: PASS
- Graph summary and Article-filtered `/v1.1` nodes: PASS
- `/v1.2/reference-summary`: HTTP 200, `status=valid`, 1,314 Articles
- `/v1.2/articles/{id}/references`: HTTP 200
- grounded fake-provider Tutor over persisted RAG: PASS, target Article cited,
  no refusal

An exact-title-only Tutor probe did not select Archive 11814 in the final five
diversified fake-embedding sources. The evidence-bearing query selected it.
This is recorded as a deterministic fake-retrieval relevance limitation, not
a stale-index or compatibility failure; direct RAG target checks ranked all
three new Articles first.

No legacy, `/v1.1`, or `/v1.2` route or response contract changed.

## 10. Test Evidence

Local evidence before the implementation commit:

- focused P3-010 tests: 8 passed
- full Backend suite: 600 passed, 4 skipped
- Frontend Article tests: 3 passed
- Frontend Reference tests: 3 passed
- Frontend Tutor tests: 13 passed
- Frontend Graph tests: 8 passed
- Frontend production build: PASS, 8/8 pages generated
- current local API/feature smoke: PASS
- installed Reference full-corpus audit: PASS, checkpoint complete at 1,314,
  zero issues
- workflow policy: PASS, 16/16 Action uses pinned
- suppression validation: PASS, zero dependency or secret suppressions
- canonical tracked/history secret audit: PASS, zero credible findings
- security tool tests: 17 passed
- temporary SBOM build and validation: PASS, 261 combined components, zero
  forbidden values

The final full Backend command was run from the repository root with
`UV_OFFLINE=1`. Implementation commit
`e66d9f32358ba09b6d89fce5e86877a80a52f032` passed exact main CI run
[`30452018708`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30452018708).
Backend pytest, Frontend build, workflow policy, dependency audit, secret
audit, and SBOM validation passed. Docker compose smoke and release evidence
were correctly skipped for the normal main push.

## 11. Safety and Artifact State

- source/browser network requests: 0
- unexpected network attempts: 0
- Article mutations: 0
- private Zotero reads/writes: 0/0
- real or paid Provider calls: 0
- tracked runtime/private assets: 0
- committed PDF/HTML/image/index/database/backup assets: 0
- candidate/tag/Release changes: 0
- frozen M1 implementation paths changed: 0

The 187 MB recovery backup, refreshed FAISS/Graph/Reference stores, lock, and
run summary remain ignored under `.local_data`.

The older `audit_repository_artifacts` helper reported two lexical key-pattern
matches spanning ordinary words in an existing public ADR filename; both
predate P3-010 and contain no credential. That helper still reported zero
tracked runtime/private artifacts and zero new local paths. The canonical
bounded tracked/history secret audit reported zero credible, reported, or
suppressed findings. This false-positive classification is recorded rather
than suppressed or used to weaken policy.

## 12. Remaining Risks

- P3-006 human-review precision remains unmeasured; this task does not expand
  or close that accepted risk.
- Fake embeddings are deterministic but not a quality substitute for a real
  embedding model.
- Three-root installation is recoverable and all-or-nothing at completion,
  but is not globally isolated from concurrent readers without a shared
  application transaction pointer.
- Runtime stores must be rebuilt again after a future Article Store change;
  M1.4 deliberately does not trigger this operation implicitly.
- The source Article Store and ignored recovery backup remain local assets and
  need normal host backup discipline.

## 13. Acceptance Status

All local P3-010 functional, identity, staging, backup, rollback, target
coverage, idempotency, compatibility, offline, source-integrity, and artifact
requirements: **PASS**.

Implementation main CI: **PASS**.

Final task status: **PASS / CLOSED**.

The docs-only closure commit is the final authorized repository write. Its
exact `main` CI run is verified after push and reported as closure evidence;
no third evidence-only commit is required.
