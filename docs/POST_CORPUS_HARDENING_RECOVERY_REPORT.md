# Post-Corpus Hardening and Recovery Report

## Current Status

- P2-006 Post-Corpus Product Hardening and Recovery: **PASS**
- Execution date: 2026-07-11
- Scope: local inventory, tiering, backup, verification, isolated restore, rebuild guidance, cleanup, health, and capacity
- Source fetches: 0
- Full PDF regenerations: 0
- Additional verification gate: not created

The local corpus can now be inventoried, backed up, verified, restored into an isolated directory, and checked for stale or corrupt derived artifacts. The real essential-backup drill completed successfully and all temporary backup/restore output was removed after evidence collection.

## Local Data Inventory

The runtime manifest is written atomically to the ignored path:

`.local_data/scientific_spaces/operations/local_data_manifest.json`

Final manifest fingerprint:

`4c87e3e3438f088a2cca6317245c58f2718289e5ed033d02cce58273cbba5f73`

The manifest has 34 asset records: 8 Tier 1 definitions, 23 Tier 2 definitions/observed legacy outputs, and 3 Tier 3 definitions. Optional missing stores remain represented with `exists=false`; four Tier 1 assets currently exist.

| Asset | Tier | Records | Size bytes | Source fingerprint |
|---|---:|---:|---:|---|
| Article store | 1 | 1,311 | 14,910,166 | `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d` |
| Classification registry | 1 | 15 | 3,177 | n/a |
| Corpus progress | 1 | 1 root record | 54,803 | n/a |
| Learning JSON | 1 | 21 sessions/user records | 5,743 | n/a |
| Markdown library | 2 | 1,311 | 14,466,537 | Article fingerprint |
| PDF library and metadata | 2 | 1,311 | 832,364,106 | Article fingerprint |
| RAG index | 2 | 5,547 chunks | 18,512,364 | Article fingerprint |
| Knowledge Graph | 2 | 135,104 nodes + edges | 75,304,505 | Article fingerprint |
| Evaluation output | 2 | 9 files | 31,795 | n/a |
| Cache/log/temp currently present | 3 | 0 | 0 | n/a |

Total `.local_data/scientific_spaces` size at the final audit was 955,746,238 bytes.

## Source-of-Truth Policy

Tier 1 contains the authoritative Article store, completion classification registry, corpus progress, Learning/bookmark/note/session data, Zotero links, Tutor sessions, optional SQLite persistence, and conservatively classified user-created files. These assets are protected from cleanup and selected by the default essential profile.

Tier 2 contains outputs that can be recreated from Tier 1: Markdown, PDF, RAG chunks/FAISS, Knowledge Graph, derived manifests, evaluation output, and historical corpus probe output. The initial real audit exposed historical `p1_003_*` probe files as unclassified; the policy was corrected so they are Tier 2 and do not inflate essential backups.

Tier 3 contains browser profiles/caches, traces, logs, temporary/staging files, and similar disposable runtime output. Tier 3 is excluded from every backup profile.

The entire `.local_data` directory is not disposable. Tier 1 must be backed up before destructive maintenance.

## Unified Manifest

Each asset record contains:

- `asset_type`
- relative `relative_path`
- `tier`
- `size_bytes`
- `record_count`
- deterministic `fingerprint`
- `source_fingerprint`
- `schema_version`
- `rebuild_command`
- `required_for_restore`
- `contains_user_data`
- `backup_priority`

The top-level deterministic fingerprint is computed from sorted asset records and excludes `generated_at`. A 1-worker and 4-worker fixture audit produce the same fingerprint. The manifest contains no absolute path, secret, note body, or API key. Writes use a same-directory temporary file, `fsync`, and `os.replace`.

## Backup Design

`essential` is the default profile and includes Tier 1 only. In the current runtime it selected:

1. Article store
2. Completion classifications
3. Corpus progress
4. Learning JSON

`complete` selects Tier 1 and Tier 2. The CLI requires an explicit `--include-pdf` or `--exclude-pdf` choice for complete backups; essential always excludes PDF.

Archive creation uses a staging `.zip.partial` outside the source root, streams each source file once while computing SHA-256, writes an internal `backup_manifest.json`, verifies before publication when `--verify` is used, and atomically renames the completed archive. Source and archive symlinks are rejected. The archive mode is restricted to `0600` on this platform.

`.env`, private key files, browser profiles, traces, caches, and logs are excluded. No upload, cloud transfer, or custom encryption occurs.

## Backup Execution

The real command used the 4-worker essential profile and a temporary destination under `/tmp`.

| Metric | Result |
|---|---|
| Status | PASS |
| Profile | essential |
| PDF included | false |
| Data files | 4 |
| Archive size | 14,978,927 bytes |
| Archive mode | `0600` |
| Elapsed time | under 1 second |
| Source manifest fingerprint | `4c87e3e3438f088a2cca6317245c58f2718289e5ed033d02cce58273cbba5f73` |

The final backup/verify/restore rerun used the final inventory snapshot after the PDF idempotency report refresh. The Article source fingerprint remained unchanged throughout the task.

## Backup Verification

Independent verification returned **PASS** with zero issues.

| Asset | Verified record count |
|---|---:|
| Article store | 1,311 |
| Classification registry | 15 |
| Corpus progress | 1 |
| Learning JSON | 21 |

Verification covered archive readability, manifest schema, required files, per-file sizes and SHA-256 hashes, record counts, profile/tier policy, PDF policy, duplicate/unmanifested entries, truncation, absolute paths, path traversal, Windows drive paths, symlink entries, and archive/restore path agreement.

## Restore Execution

The verified backup was restored to `/tmp/scientific-spaces-p2-006-smoke/restore`, never over the current `.local_data` tree.

| Metric | Result |
|---|---|
| Status | PASS |
| Restored files | 4 |
| Post-restore hash verification | PASS |
| Atomic staging/install | PASS |
| Elapsed time | 0.404 seconds |

Restore rejects non-directory and non-empty targets unless overwrite is explicit, always rejects the protected current data root, validates the backup before extraction, prevents Zip Slip and symlink escape, writes into staging, and removes staging after failure. Tests cover rollback without a partial target.

## Restored Data Audit

| Check | Source | Restored | Result |
|---|---:|---:|---|
| Article count | 1,311 | 1,311 | PASS |
| Unique URL count | 1,311 | 1,311 | PASS |
| Missing content | 0 | 0 | PASS |
| Article fingerprint | `cc8717...cdf5d` | `cc8717...cdf5d` | PASS |
| Classification asset fingerprint | `520cfe...e0f3` | `520cfe...e0f3` | PASS |
| Learning records | 21 | 21 | PASS |
| Learning sessions | 21 | 21 | PASS |
| Learning states/bookmarks/notes | 0/0/0 | 0/0/0 | PASS |
| Zotero links | absent/0 | absent/0 | PASS |
| Tutor session store | absent/0 | absent/0 | PASS |
| SQLite Learning store | absent/0 | absent/0 | PASS |

As a restored-data derived-capability check, the restored Article store was materialized offline into a temporary Markdown library: 1,311 input Articles, 1,311 Markdown outputs, 0 missing-content records, 0 rejected IDs, and `no_source_fetch=true`.

The backup, restore tree, generated Markdown, and supporting result files were removed from `/tmp` after the audit.

## Derived Artifact Rebuild

The health report never performs an expensive rebuild. It reports the explicit remediation command:

```text
Markdown: uv run --project backend python scripts/corpus/materialize_local_library.py
PDF:      uv run --project backend python scripts/export/export_local_corpus_pdfs.py
RAG:      uv run --project backend python scripts/rag/build_full_corpus_index.py
Graph:    uv run --project backend python scripts/graph/build_full_corpus_graph.py
```

Markdown source provenance is recorded in the unified manifest. Existing PDF, RAG, and Graph manifests record the Article corpus fingerprint. A mismatch is reported as stale; rebuild is never automatic.

## Cleanup Safety

Cleanup is dry-run by default and supports only:

- `temp`
- `logs`
- `browser-cache`
- `evaluation-output`
- `stale-derived`
- `all-derived`

There is no `clean-all` option. Tier 1 paths and the complete data root are hard-protected. Executing `all-derived` additionally requires `--confirm-derived-delete`.

The real dry-run covered temp, logs, browser cache, and evaluation output. It identified one evaluation directory containing 31,795 bytes and deleted nothing.

## Health Check

With the completed-corpus Reader/Tutor environment variables configured, the final health check returned **PASS** with zero issues. Article, classification, unified manifest, Markdown, PDF, RAG, Graph, Reader, Tutor, Learning, Tutor sessions, Zotero, and capacity all passed.

Without those environment variables, the same data integrity checks pass and the overall result is **WARN** with two actionable non-data issues:

- `READER_ARTICLE_STORE_NOT_CONFIGURED`
- `TUTOR_FULL_CORPUS_NOT_CONFIGURED`

Every health issue includes `issue_code`, `affected_asset`, `remediation_command`, `rebuildable`, and `backup_required_first`.

## Storage Capacity

| Metric | Bytes |
|---|---:|
| Article store | 14,910,166 |
| Markdown | 14,466,537 |
| PDF library and metadata | 832,364,106 |
| RAG | 18,512,364 |
| Graph | 75,304,505 |
| Logs/temp | 0 |
| Total local data | 955,746,238 |
| Estimated essential backup | 14,973,889 |
| Estimated complete backup | 955,746,238 |
| Free disk | 734,708,887,552 |

Capacity status is **PASS**. Free space is far above twice the complete local-data size and is sufficient for complete backup, isolated restore, and PDF rebuild. The checker emits distinct warnings for low overall space, insufficient complete-backup space, insufficient PDF-rebuild space, and insufficient restore space.

## Security and Privacy

- Backups are private local data and are never uploaded automatically.
- `.env`, API-key files, private-key files, logs, traces, profiles, and caches are excluded by policy.
- Reports contain counts and hashes, not user note bodies or Article bodies.
- Archives and restored files use current-user-only permissions where supported.
- Source and archive symlinks, traversal, absolute paths, drive paths, duplicate entries, unmanifested files, and hash/count mismatches are rejected.
- No custom encryption algorithm was introduced. Encryption and off-site retention require a separate architecture/operations decision.

## Documentation

`README.md` now documents data locations, source-of-truth and rebuildable assets, essential/complete backup, explicit PDF policy, verification, isolated restore, health, safe cleanup, rebuild commands, and capacity expectations.

It also contains an explicit warning that `git clean -fdX` deletes ignored Article corpus, Markdown, PDF, RAG, Graph, unified manifest, and other `.local_data` state.

`.env.example` now exposes the completed full-corpus Reader/RAG/Graph configuration, and `.gitignore` explicitly excludes local backup and restore artifacts.

## Regression Evidence

| Check | Result |
|---|---|
| Operations fixture tests | PASS, 38 tests |
| Backend pytest | PASS, 453 passed / 3 skipped in 42.74 seconds |
| Next.js production build | PASS, 8/8 static/dynamic routes generated |
| Deterministic RAG/Tutor baseline | PASS, 9 cases, all required rates 100% |
| Full-corpus RAG evaluation | PASS, 12 queries, expected hit@10 90.9%, retrieval errors 0, unsupported fabrications 0 |
| Graph/Tutor bounded smoke | PASS, 20 nodes, 19 edges, full graph not injected, local path not exposed |
| Full-corpus Tutor evaluation | PASS, 42 cases, 0 hard failures, 0 validity failures |
| PDF manifest/idempotency | PASS, 1,311 unchanged, 0 exported/regenerated/failed, 1,311 validation PASS, external requests 0 |

Normal CI remains fixture-only and does not require ignored runtime corpus data.

## Artifact Check

- No `.env`, database, PDF, ZIP/TAR, FAISS, chunks, graph runtime, `.local_data`, restore tree, backup archive, trace/profile/cache, or `node_modules` file is tracked.
- `git diff --check`: PASS.
- Python compile check for operations modules and scripts: PASS.
- Real backup/restore and evaluation files under `/tmp`: removed.
- Current `.local_data` was not deleted, restored over, or committed.

## Limitations

- Backup is a local snapshot, not encrypted or replicated off-site.
- JSON stores do not yet provide a coordinated application-wide write lock; schedule backup while local writes are quiescent for the strongest snapshot semantics.
- Complete backup with PDF is approximately 956 MB and must be requested explicitly.
- Reader/Tutor full-corpus paths must be exported or loaded from the provided environment profile; otherwise health reports WARN.
- Restore is local filesystem recovery, not a multi-user migration protocol.

## Recommendation

**Status: PASS**

**A: Ready for v1.1 release-readiness audit**

The source-of-truth assets have a verified essential backup and isolated restore path, rebuildable assets have explicit provenance and remediation commands, cleanup cannot remove Tier 1, and the full regression suite remains green.
