# Structured Reference Extraction Pilot Report

## Current Status

- Task: P3-003 Structured Reference Extraction Pilot
- Date: 2026-07-15
- Formal version: `v1.1.0`
- Candidate version: not assigned
- Scope Decision baseline: A
- Pilot status: PASS
- Network mode: offline, enforced
- Source mutation: none
- Private Zotero access: none
- Real provider access: none

## Implemented Boundary

The pilot adds an independent `backend/app/references/` boundary for reference contracts, Markdown-aware extraction, normalization, deterministic deduplication, provenance, optional read-only matching, JSONL derived-store lifecycle, and audits. It adds operator CLIs under `scripts/references/` and focused synthetic or metadata-only fixtures under `backend/tests/`.

The implementation does not modify `Article.content`, `metadata.references`, M1 modules, the Article storage schema, legacy APIs, or `/v1.1` APIs. The derived store remains under ignored `.local_data/` runtime storage.

## Fixture Dataset

| Fixture group | Cases | Result |
| --- | ---: | --- |
| DOI | 15 | PASS |
| arXiv | 15 | PASS |
| URL | 32 | PASS |
| Citation text | 8 | PASS |
| Total normalization cases | 70 | PASS |

The focused suite also covers Markdown/code/math contexts, no-reference status, candidate bounds, exact and possible duplicates, cross-Article evidence, version-aware arXiv grouping, unavailable matching, conflicting strong identifiers, store corruption, stale configuration, checksum/index mismatch, failed-install rollback, interrupted-state recovery, no-op reuse, network blocking, and artifact/secret scan boundaries.

- Fixture case count: 70
- Fixture failures: 0
- DOI exactness: 1.0
- arXiv exactness: 1.0
- Safe-URL exactness: 1.0
- Malformed/forbidden classification exactness: 1.0
- Expected deterministic duplicate behavior: 1.0

## Input and Selection

- Selection-only Article inventory: 1,311
- Extracted Articles: 75
- Unselected Articles: 1,236
- Unselected reference output count: 0
- Selection fingerprint: `fa4965056df510b6a9d1dd0760830edff24bf2afc33efcdddb1d49a66eb55323`
- Rule: deterministic stable stratification by date, content length, formula density, link count, reference-like markers, and edge-case tags

Selected strata included 27 legacy and 48 modern Articles, 19 short and 25 long Articles, 48 formula-heavy Articles, 8 code-bearing Articles, 5 duplicate-like Articles, 3 malformed-like Articles, 3 DOI-tagged Articles, and 3 arXiv-tagged Articles.

Selected Article IDs:

```text
01f8de7ee9c89253 03dfe77de35ec4ec 04940ba539e75000 04de71f1c8b03511 05e74d0321c3a6d6
077b4c354fced1b1 0cd412258aba9789 0d510af4e2dd837a 1005453fcd9e779e 1040c4f179689d87
16d4eafd1185b9d4 183b06046ae90318 1ccb8aa1ece5b675 1ebc42b58f3dff26 201e66f6e58f5078
2411a01f0eee9c46 28b3de7bcb40672e 2ca18dd865450432 3005032d61411d87 30832e4c3b7ac210
34f0025b3432bb22 34f5d22e39757106 354e51839b04edeb 36af9e59f7e5b273 36e8247c51d6f8fd
3f882bd86232da34 44f4da2eba77d4a0 4dee89c899cc1855 52744edb3195cae0 531d13a6675206f1
55583c31265ab3dc 59cf9269289e0196 68441d48f88c5de6 6a8eb25e9eba5478 710303f1515ad26e
78df2e9524c884bd 830b82cd90b993fa 84bf11e505b791c6 8617e50bb0c2ba01 87d6e7f900635751
8bcc6cc56f0550f2 936c7f9e9af6eea5 949a6a2892a483c1 a0f59fb23e8457f4 a901ea6ed6668c0f
acda072dbe5b0413 b14482d5b85763b7 b3631a253706bd0f b56c82bc216367fc bb3b34feaedf0248
bbb9633119bda0db c10628495483e2c5 caaf04e5e54f8414 ccef54458ad8f390 cd6a60a89379bee9
cde22c800fd3d0bf cfae169048406035 d1485351829145c4 d4af193b5bb5e0c0 d6928b63b030937f
d8183d1675603ed5 d93707e62072bddc d9b64061190662cb d9e3df62cf844535 dbd716d4c1c76529
e3f45b1820c68841 e4539b3ee91ddf70 e9851624fcb77aa8 ea674b70cab4827c ee01c25c4bd7bd43
f2fc16d378a44c89 f5873190f35ea42d fdc8089a206a0514 fea9d34df3596d37 ff03145eb599e50a
```

## Pilot Results

| Metric | Result | Gate |
| --- | ---: | --- |
| Articles classified | 75/75 (1.0) | PASS |
| Candidates detected | 1,578 | evidence |
| Candidates classified | 1,578 | PASS |
| Candidate overflow | 0 | PASS |
| Silent drops | 0 | PASS |
| Reference records | 987 | evidence |
| Evidence rows | 1,578 | evidence |
| Provenance completeness | 1.0 | PASS |
| Deterministic ID rate | 1.0 | PASS |
| Duplicate-group consistency | 1.0 | PASS |

Record types were 4 DOI, 4 arXiv, 190 external HTTP(S) URLs, 787 relative/internal URLs, and 2 code-context candidates correctly rejected as unsupported. Classification totals were 858 normalized, 127 deterministic duplicates, and 2 rejected.

Safe links are reference candidates, not claims of scientific relevance. Internal anchors, images, and other non-paper URLs remain separately typed and never become exact scientific or Zotero identities without a strong identifier.

## Extraction Rules

Extraction is Markdown-aware and bounded to 512 candidates per Article. It recognizes DOI, arXiv, Markdown and plain HTTP(S) links, relative/internal links, unsafe schemes, and citation lines in reference sections. Fenced-code candidates are terminally classified as rejected, overflow receives an explicit classification, and every detected candidate reconciles to a classified result.

## Normalization

DOI and arXiv identities are normalized without remote resolution. URL normalization preserves identity-bearing query, fragment, and reserved path escapes; removes only the explicit tracking-key allowlist; resolves relative links against the Article origin; distinguishes non-default ports; and rejects credentials, unsafe schemes, localhost, loopback, private, link-local, multicast, reserved, and unspecified addresses.

- DOI normalization exactness: 1.0
- arXiv normalization exactness: 1.0
- Safe-URL normalization exactness: 1.0
- Malformed/forbidden classification exactness: 1.0

## Provenance

Every record retains complete, sorted evidence IDs. Each evidence row includes the source Article ID/title/URL, nearest Markdown section, bounded source span and context, raw-reference hash, candidate ordinal, extraction rule/version, and corpus fingerprint.

- Provenance required-field completeness: 1.0
- Orphan or misowned evidence: 0
- Unselected Article evidence/record output: 0

## Duplicate Grouping

Equal DOI, version-aware arXiv, and complete normalized URL identities merge deterministically while retaining cross-Article evidence. Different arXiv versions and similar citation text may share a possible group but do not exact-merge.

- Deterministic ID rate: 1.0
- Duplicate-group consistency: 1.0
- Expected duplicate behavior exactness: 1.0

## Reference Store

- Manifest/schema/hash/count/index/referential audit: PASS
- Record/evidence/index orphan count: 0
- Store build fingerprint: `5d264745b7e1b3b96554e36011f328fda44d6184c62df3aaeb80ec4b30e11973`
- Configuration fingerprint: `8532797c7646fa9e4c3d8fc8099e31457bcd091565b9775895f78b9bbf4e7a2b`
- Same-input second install: validated no-op
- Stale configuration detection: PASS
- Corrupt payload detection: PASS
- Checksum/index mismatch detection: PASS
- Failed-install rollback: PASS
- Interrupted backup recovery: PASS
- Local absolute paths in runtime store: 0

## Zotero Matching

- Provider boundary: deterministic fake/unavailable, read-only
- Candidate decisions: 987 unmatched
- Automatic Zotero/library/link/decision writes: 0
- False exact Zotero fixture matches: 0
- DOI/arXiv exact matching requires no conflicting strong identifier
- URL-only matching is at most probable; title-only matching remains ambiguous

## Zero-Network Evidence

- External network requests: 0
- Unexpected network attempts: 0
- Browser/network subprocess launches: 0

## Idempotency

- Same-input second install: validated no-op
- Build fingerprint remained `5d264745b7e1b3b96554e36011f328fda44d6184c62df3aaeb80ec4b30e11973`
- Core derived-store content fingerprints remained unchanged
- Human review is bound to the current store build and stale review evidence is rejected

## Integrity and Corruption

- Manifest, schema, file hash, row count, index, and referential integrity: PASS
- Stale configuration detection: PASS
- Corrupt payload and schema detection: PASS
- Checksum/index mismatch detection: PASS
- Failed-install rollback: PASS
- Interrupted-state recovery: PASS
- Parent-traversal and symlink output protections: PASS

## Article Immutability

- Article store SHA-256 before/after: `3b91f22db548373a6c91bb11a5188fb3e388ab9e19c4429e8e8fac918609a505`
- Corpus fingerprint before/after: `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d`
- Article and corpus mutation count: 0

## Human Review

- Deterministic cases reviewed: 30
- Strong identifiers reviewed: 8
- Strong-identifier numerator/denominator: 8/8
- Strong-identifier precision: 1.0
- Reviewer count: 1
- Disagreements: 0
- Invalid or stale review cases: 0
- Second reviewer fabricated: no
- Single-review limitation: true

The reviewed set included all 8 pilot DOI/arXiv records, both rejected code-context URL candidates, and 20 stable URL/duplicate candidates. Normalized identity, bounded evidence, duplicate behavior, and fake/unavailable Zotero decisions were manually checked. A second independent reviewer was unavailable; this limitation is explicit and does not reduce the 95% threshold.

## Resource Use

- Elapsed time: 3.444176 seconds
- Peak traced memory: 83,467,181 bytes
- Runtime output: 4,610,618 bytes
- Runtime files: ignored and not committed

## Regression Evidence

- Focused reference tests: 26 passed
- Frozen Article/Graph/Zotero API regressions: 45 passed
- Complete Backend suite: 495 passed, 3 skipped
- Frontend production build: PASS
- Next.js static generation: 8/8 pages
- Reference Store audit: PASS

## Artifact and Secret Audit

- Artifact/secret audit: PASS
- Current-change runtime/private artifacts: 0
- Current-change secret patterns: 0
- Current-change local absolute paths: 0

The artifact scanner separately reports 22 unchanged historical documentation, test, and smoke-script paths as baseline findings. They predate P3-003 and are not current-change artifacts. `.env.example` is a tracked configuration template, not a runtime `.env` file. Regression tests prove that a newly tracked `.env`, a current-change local path, or a secret-like token still blocks the audit.

## Limitations

- This is a 75-Article pilot, not a full 1,311-Article reference build.
- The pilot performs syntactic extraction and conservative identity normalization; it does not prove scientific relevance or bibliographic correctness.
- The fake/unavailable Zotero boundary proves deterministic read-only behavior, not private-library match coverage.
- Human review used one reviewer. A second independent reviewer remains desirable for later full-corpus evaluation.
- External site and provider metadata were intentionally not queried.

## Recommendation

P3-003 status: PASS.

Recommendation: **A: Ready for P3-004 Real Provider Evaluation Design**.

All mandatory deterministic integrity, precision, no-network, no-mutation, compatibility, test/build, and artifact gates passed. This PASS does not authorize P3-006 full-corpus processing, private Zotero access, product API/UI integration, push, candidate assignment, tag, or Release.

## GitHub Synchronization and Closure

- Implementation commit: `fb5419fc31222be738178a3ed65cf11dfb9192fe`
- Commit message: `feat: add structured reference extraction pilot`
- Remote branch: `main`
- Main CI run: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29415222974`
- CI event/ref/SHA: `push` / `main` / `fb5419fc31222be738178a3ed65cf11dfb9192fe`
- Backend pytest: PASS
- Frontend build: PASS
- Docker compose smoke: SKIPPED by the normal main-push workflow policy
- P3-003 lifecycle status: PASS / CLOSED
- P3-004 canonical task: `docs/tasks/P3-004_REAL_PROVIDER_EVALUATION_DESIGN.md`
- P3-004 status: ALIGNMENT REQUIRED
- P3-004 implementation authorization: NOT GRANTED

No tag or Release was created. No real provider, paid request, private Zotero data, full-corpus reference build, or runtime/private artifact was used for closure.
