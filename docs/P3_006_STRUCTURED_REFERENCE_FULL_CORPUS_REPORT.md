# P3-006 Structured Reference Full-Corpus Report

## Status

- Task: P3-006 Structured Reference Full-Corpus Build and Offline Zotero-Matching Validation
- Result: **CONDITIONAL / CLOSED**
- Machine integrity and compatibility gates: **PASS**
- Finite limitation: 64 deterministic human-review cases are generated, but no real reviewer was available during this task
- Formal version: `v1.1.0`
- Candidate version: not assigned
- Network authorization: not granted and not used
- Private Zotero authorization: not granted and not accessed
- Completion and dependency-repair commits: pushed after separate authorization
- Candidate, tag, Release, and attestation: not performed

CONDITIONAL is used because every required machine gate passed while the actual human-review precision gate remains pending. No Article, provenance, accounting, determinism, recovery, integrity, no-network, resource, test, build, or artifact gate is relaxed.

## Approved Boundary

- Read-only Article Store: `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json`
- Derived runtime root: `.local_data/scientific_spaces/references/full-corpus/`
- Authoritative derived store: `.local_data/scientific_spaces/references/full-corpus/current/`
- Frozen P3-003 extraction, normalization, ID, deduplication, matching, and schema versions were reused unchanged.
- Runtime output remains Git ignored and is not part of this commit.

## Corpus Identity

| Check | Evidence | Result |
| --- | --- | --- |
| File type | regular file, nonsymlink | PASS |
| Inode | `17976707` | recorded |
| Size | `14910166` bytes | recorded |
| Mtime | `2026-07-09 22:48:27.862965851 +0800` | recorded |
| SHA-256 | `3b91f22db548373a6c91bb11a5188fb3e388ab9e19c4429e8e8fac918609a505` | PASS |
| Corpus fingerprint v1 | `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d` | PASS |
| Article count | 1311 | PASS |
| Unique IDs | 1311 | PASS |
| Unique URLs | 1311 | PASS |
| Duplicate IDs / URLs | 0 / 0 | PASS |
| Missing content / malformed Articles | 0 / 0 | PASS |
| Available disk at final preflight | 713543872512 bytes | PASS |

The SHA-256 and corpus fingerprint were identical before controlled interruption, after resume, after no-op reuse, and during the independent store audit. Article mutation count was `0`.

## Implementation

P3-006 adds a dedicated offline full-corpus orchestration layer without changing P3-003 semantics:

- streaming JSON-array Article loading without retaining all Article bodies;
- exact corpus identity and path-safety preflight;
- per-Article extraction payloads with bounded evidence only;
- atomic checkpoints every 50 Articles;
- checkpoint identity binding to corpus SHA/fingerprint, configuration, rule versions, code baseline, and implementation fingerprint;
- stale/corrupt checkpoint rejection and verified resume;
- global deterministic sort/dedup after extraction;
- fake curated and unavailable Zotero matching only;
- reuse of the existing staged, validated, atomic Reference Store installer;
- independent store, resource, artifact, and secret audits.

Identity evidence:

- Code baseline commit: `0496991746196c1d628a06f4fab36c34085a0144`
- Implementation fingerprint: `c53dea7562463a9185b2765c65dc48eb856bd9a28dd54c6614ea3cdeb996b0d8`
- Configuration fingerprint: `6ae6cab10dbbada8810730fcd86c308406bd1f24c25f330c5067d51c374938bc`
- Build fingerprint: `70ab191621aa8819f3c195c116aec5b5ae05f44c0b90fb0d11e6cb4365d5d846`

The implementation fingerprint binds the exact reference implementation bytes used by the pre-commit execution. The status-appropriate local commit is created only after this report and all tracked evidence are finalized.

## Full-Corpus Accounting

| Metric | Result |
| --- | ---: |
| Input Articles | 1311 |
| Processed Articles | 1311 |
| Explicit terminal failures | 0 |
| Unknown Article statuses | 0 |
| Duplicate processed Articles | 0 |
| Input accounting rate | 1.0 |
| Classified Articles | 1311 |
| Detected candidates | 24514 |
| Classified candidates | 24514 |
| Overflow candidates | 0 |
| Silent drops | 0 |
| Classification reconciliation rate | 1.0 |
| Reference records | 12859 |
| Evidence rows | 24514 |
| Zotero match candidates | 12861 |

Record types were 4 DOI, 22 arXiv, 2,187 external HTTP(S) URLs, 10,515 relative/internal URLs, 43 citation-text records, 5 malformed records, and 83 unsupported records. Terminal classifications were 10,821 normalized, 1,907 duplicate, 43 ambiguous, 5 malformed, and 83 rejected.

## Provenance and Determinism

- Provenance completeness rate: `1.0`
- Deterministic ID rate: `1.0`
- Duplicate-group consistency rate: `1.0`
- Orphan or misowned evidence: `0`
- Article/index/identifier foreign-key reconciliation: PASS
- Manifest file hashes and row counts: PASS

Core content hashes:

| File | Rows | SHA-256 |
| --- | ---: | --- |
| `records.jsonl` | 12859 | `7684b4322aa2a25c8fd94ab397a4eb1b2180dec5a36407921993d30adc8ccc33` |
| `evidence.jsonl` | 24514 | `a7e89305705e7fc1c969700ac38608fa434797bc462900a4a2eb0e0e8c919b4c` |
| `article_index.json` | 1 | `71285ea1e4fbcee4ea15f141826a9eca73aeb123ab47d49040e81ce49d4be462` |
| `identifier_index.json` | 1 | `d61c61ed62b01e8f1dffa0cf650a45f6b1617acb0b1a8465a7304fa31894bad4` |
| `zotero_candidates.jsonl` | 12861 | `f2f0fbe0b8c9be81341953762659755b2b49a0f57043e44763ff5eca4916c2b1` |

Deterministic manifest content fingerprint, excluding only `generated_at`: `eea1a0da801e4c9b9adabcc221fbc9cb034b810ea081694fff5413cadff2512d`.

## Recovery and Installation

### Controlled interruption

- Requested interruption point: Article 125
- Exit code: 75, the dedicated expected-interruption code
- Processed before interruption: 125
- Atomic checkpoint writes: 3, at Articles 50, 100, and 125
- Checkpoint state: valid, 125 sorted completed IDs and 125 verified extraction digests
- Article body in checkpoint metadata: absent
- Partial `current` replacement: absent
- Existing authoritative `current` change: none
- Network requests / unexpected attempts: 0 / 0

### Resume and install

- Resume start: validated Article 125 checkpoint
- Resume completion: 1311 Articles
- Final checkpoint status / position: `complete` / 1311
- Checkpoint writes after resume: 29 total for that run sequence
- Sibling staging validation: PASS
- Atomic installation and installed-store revalidation: PASS
- Failed replacement rollback and interrupted-backup recovery: PASS in focused regressions
- Stale configuration/current detection: PASS in focused regressions
- Corrupt payload/checkpoint/index/ownership detection: PASS in focused regressions

### Idempotency and clean determinism

- Unchanged rerun action: `no_op`
- Store content files unchanged: PASS
- Build/config/manifest deterministic fingerprints unchanged: PASS
- Isolated clean rebuild: PASS
- Five core files byte-identical: PASS
- Deterministic manifest fields identical: PASS
- Verification-only clean-build directory removed after comparison: PASS
- Authoritative `current` retained: PASS

## Offline Zotero Validation

Only deterministic fake-curated metadata and provider-unavailable modes were used.

| Metric | Fake curated | Unavailable |
| --- | ---: | ---: |
| Records | 12859 | 12859 |
| Candidate rows | 12861 | 12859 |
| Exact | 2 | 0 |
| Probable | 1 | 0 |
| Ambiguous | 2 | 0 |
| Unmatched | 12856 | 12859 |
| Automatic writes | 0 | 0 |
| Private-library reads | 0 | 0 |
| False exact matches | 0 | 0 |
| Title-only exact matches | 0 | 0 |
| Ambiguous auto-confirmations | 0 | 0 |

Focused fixtures also cover exact DOI, compatible arXiv, probable normalized URL, title-only ambiguity, conflicting strong identifiers, and unavailable-provider behavior. No private Zotero data was read, exported, copied, or mutated.

## Human Review

- Deterministic stratified cases generated: 64
- Strong DOI/arXiv, external URL, internal/relative URL, duplicate group, ambiguous text, rejected/unsupported, high-confidence, malformed, and all fake-match decision classes are represented.
- Reviewer status: 64 pending
- Actual reviewers: 0
- Reviewed cases: 0
- Strong-identifier precision: not yet measurable
- False exact fake-Zotero matches: 0

No reviewer or precision result was fabricated. Limitation owner: a project-designated human reviewer. Required closure action: complete the ignored review payload with at least one real reviewer and re-audit the review aggregate; a second reviewer should independently check at least 10 cases when available.

## Resource Evidence

| Budget | Observed | Limit | Result |
| --- | ---: | ---: | --- |
| Resume wall time | 7.098814 s | 1800 s | PASS |
| Clean rebuild wall time | 7.166606 s | 1800 s | PASS |
| No-op wall time | 4.142043 s | 1800 s | PASS |
| Peak RSS | 468254720 bytes | 1610612736 bytes | PASS |
| Installed store | 63634760 bytes | 536870912 bytes | PASS |
| Checkpoints | 34333198 bytes | included below | PASS |
| Estimated staging + rollback + checkpoint peak | 161602718 bytes | 1610612736 bytes | PASS |
| Reports/logs | 80705 bytes | 10485760 bytes | PASS |

## Verification Evidence

- Focused references: `36 passed`
- Full Backend: `540 passed, 3 skipped`
- Frozen Article/Graph/Zotero API tests: `45 passed`
- Frontend Next.js build: PASS
- Independent full-corpus store audit: PASS
- `git diff --check`: PASS
- Secret audit: PASS, credible/reported/suppressed = 0/0/0
- Artifact audit: PASS, new runtime/private artifacts = 0, new secrets = 0, new local absolute paths = 0
- Source Article SHA before/after: unchanged
- External network requests / unexpected attempts: 0 / 0

The artifact audit retained 24 pre-existing baseline local-path findings separately; P3-006 introduced none. Public source evidence containing generic path examples or URL path segments is not a local runtime-path leak, while actual runtime roots remain blocked by the store audit.

## Dependency Audit Repair Closure

The authorized P3-006 completion commit
`f2496cafa4a54440b19e4491294277b70a1f07cf` reached `main`, where CI run
[`30320834573`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30320834573)
failed only Dependency audit job `90156179263`. The complete log and a local
reproduction reported 11 real blocked runtime npm findings:

- eight advisories affecting direct `next@15.5.20`;
- two advisories affecting direct `postcss@8.5.10`;
- one advisory affecting optional transitive `sharp@0.34.5`.

P3-006-CI-001 applied only the minimum aggregate fixed versions:

- `next@15.5.21`;
- `postcss@8.5.18`;
- `sharp@0.35.0` through a targeted override of Next's optional transitive
  dependency.

GitHub Advisory Database and OSV agreed on all affected and fixed ranges.
Two final local dependency audits were byte-identical and passed with PyPI 40,
npm 219, findings 0, blocked 0, and suppressed 0. Security tests, workflow
policy, suppression validation, secret audit, SBOM, Backend, frontend clean
install/build, Sharp runtime, and Next image-optimizer compatibility passed.

Repair commit `9b0080cbe5c6483de2534ed63f9eeb5c5e5b1dbd`
passed:

- validation workflow-dispatch run
  [`30322598783`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30322598783),
  including Backend, Frontend, dependency audit, workflow policy, secret
  audit, SBOM, Docker compose smoke, and no-publish release evidence;
- main CI run
  [`30322723458`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30322723458),
  with Docker and release evidence correctly skipped by main-push policy.

Both runs produced zero workflow artifacts. The validation release evidence
recorded `publish_authorized=false` and `would_authorize_publish=false`.
Suppressions added: 0. Dependency policy weakened: no. Scanner removed: no.

The Article Store SHA, corpus fingerprint, and Reference Store build
fingerprint remained unchanged. No full-corpus build, source mutation,
Reference Store mutation, source-site/Provider/private-Zotero access,
candidate, tag, Release, or attestation occurred.

## Compatibility and Scope

- Article API: unchanged and regression PASS
- Graph API: unchanged and regression PASS
- Zotero API: unchanged and regression PASS
- Article schema and source store: unchanged
- M1 frozen modules: unchanged
- Legacy API and `/v1.1` API: unchanged
- RAG, Graph storage, Provider defaults, authentication, candidate, tag, and Release: unchanged

## Decision

**P3-006 Status: CONDITIONAL / CLOSED**

All machine acceptance gates passed. The sole finite non-critical limitation is pending real human review, which is explicitly allowed for CONDITIONAL status and does not affect Article immutability, complete accounting, provenance, deterministic IDs, duplicate consistency, recovery, store integrity, no-network behavior, resource budgets, regressions, or artifact safety.

## Next Required Action

Prepare and confirm the separate P3-006.1 Human Review Completion task.
P3-006.1 is not staged and no real-review execution is authorized by this
report.
