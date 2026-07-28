# P3-006.2 Review UX Pilot and Zotero Collection Sync

## Status

PASS / CLOSED

IMPLEMENTATION AUTHORIZATION: CONSUMED / CLOSED

PRIVATE ZOTERO READ/WRITE AUTHORIZATION:
CONSUMED / CLOSED FOR COLLECTION `苏剑林博客` AND ONE CONTROLLED TEST ITEM

LOCALHOST ZOTERO API/CONNECTOR AUTHORIZATION: CONSUMED / CLOSED

EXTERNAL NETWORK AUTHORIZATION: NOT GRANTED

PUSH AUTHORIZATION: NOT GRANTED

## Task Identity

P3-006.2 Review UX Pilot and Zotero Collection Sync

## Background

P3-006.1 retains a formal 64-case review contract. Its bounded evidence is
appropriate for a safe packet but is not sufficiently ergonomic for the
operator's preferred review workflow. This task creates a separate three-case
full-context pilot without changing that formal gate.

The user also authorized one narrowly scoped private Zotero integration:
create or reuse the root collection `苏剑林博客`, synchronize one controlled
real Scientific Spaces Article, and implement an opt-in downstream adapter for
future Article metadata synchronization.

## Goals

1. Create or uniquely reuse the target private Zotero collection.
2. Synchronize Web Page metadata idempotently by Article ID and canonical URL.
3. Keep Zotero writes downstream from the frozen source pipeline.
4. Permit optional PDF attachment metadata without making PDF availability a
   prerequisite for item synchronization.
5. Create exactly three representative full-context review cases locally.
6. Keep all private/runtime data outside Git.

## Non-Goals

- No change to the 64-case P3-006.1 acceptance gate.
- No P3-006 or P3-006.1 status upgrade.
- No M1 crawler, browser, parser, converter, storage, validation, or sync
  modification.
- No Article Store or Reference Store mutation.
- No bulk Zotero import.
- No private Zotero export or broad library inventory.
- No Zotero item deletion, merge, or unrelated update.
- No source-site request, Provider call, or paid service.
- No push, P3-007, candidate, tag, Release, or attestation.

## Allowed Tracked Changes

```text
alignment.md
backend/app/zotero/
backend/tests/test_zotero_sync.py
scripts/zotero/
docs/tasks/P3-006_2_REVIEW_UX_ZOTERO_COLLECTION_SYNC.md
docs/tasks/CURRENT_TASK.md
docs/00_PROJECT_STATE.md
docs/V1_2_ROADMAP.md
docs/P3_006_2_REVIEW_UX_ZOTERO_SYNC_REPORT.md
```

## Private Zotero Boundary

- Target collection name: `苏剑林博客`
- Collection placement: root user-library collection
- Existing exact-name collection: reuse only when unique
- Duplicate exact-name collections: stop
- Test write budget: at most one real Scientific Spaces Article item
- Existing matching item: reuse/no-op; do not create a duplicate
- Unrelated collections/items: read or write prohibited
- Collection key and item key: runtime evidence only, never tracked
- Credentials and private metadata: never read, printed, or tracked

## Sync Contract

The adapter accepts an existing stored Article and maps:

```text
itemType = webpage
title = Article.title
url = canonical Article.url
date = metadata.date when present
websiteTitle = Scientific Spaces
language = zh-CN
extra = Scientific Spaces Article ID: <Article.id>
tags = Scientific Spaces plus category when present
collections = target collection key
```

The adapter must:

- resolve exactly one target collection;
- search the target collection for Article ID or canonical URL;
- return `existing` without writing when matched;
- fail closed on conflicting duplicates;
- create at most one item per invocation;
- verify the created item through local readback;
- never hide a connector/API error.

PDF attachment is optional and deferred unless an already generated local PDF
is explicitly supplied by a future invocation. Metadata sync must work without
one.

## Three-Case Pilot

Runtime root:

```text
.local_data/scientific_spaces/references/full-corpus/reviews/p3-006-2-pilot-3/
```

The package may contain:

```text
pilot_manifest.json
reviewer.html
pilot_review.csv
```

Requirements:

- exactly three deterministic cases;
- prefer distinct Articles;
- strata: strong identifier, duplicate group, and ambiguous or Zotero case;
- full Article content is read from the authoritative local Article Store;
- full content may exist only in this ignored local package;
- no verdict is generated or defaulted;
- the package is visibly marked `PILOT ONLY`;
- the existing P3-006.1 package is not modified.

## Verification

- Focused Zotero sync tests
- Full Backend tests
- Runtime collection/item readback
- Repeated controlled sync no-op verification
- Three-case package schema and full-context checks
- `git diff --check`
- changed-path allowlist
- tracked runtime/private-artifact audit
- secret audit
- Article Store and Reference Store hash comparison
- final clean index/worktree after commit

## Git Plan

Exactly one local commit:

```text
feat: add Scientific Spaces Zotero collection sync
```

Push is not authorized.

## Stop Conditions

- Git drift, REWORK, or FAIL audit
- Zotero Desktop cannot be made available safely
- Target collection is duplicated or ambiguous
- A write would affect an unrelated item or collection
- More than one real item write is required
- External network, credentials, or private export is required
- Frozen source/store changes
- Test, secret, artifact, or changed-path failure
- P3-006.1 formal evidence would be modified
- Push, candidate, tag, Release, or attestation would be required

## Completion States

PASS requires the unique collection, one controlled sync/readback, repeated
no-op, three-case pilot, tests, audits, report, and local commit.

CONDITIONAL is allowed only when code/tests/pilot pass but Zotero Desktop
availability prevents the authorized live write. No live-write PASS may be
claimed.

BLOCKED applies to unsafe/ambiguous private-library state, source/store drift,
data leakage, or failed tests/audits.

## Completion Evidence

- Unique root collection `苏剑林博客`: PASS
- Controlled Web Page import/readback: PASS
- Repeated synchronization no-op: PASS
- Three-case full-context pilot: PASS / PILOT ONLY
- Focused sync tests: 9 passed
- Full Backend suite: 549 passed, 3 skipped
- Secret and tracked-artifact checks: PASS
- Article Store, Reference Store, and formal 64-case identities: unchanged
- Evidence: `docs/P3_006_2_REVIEW_UX_ZOTERO_SYNC_REPORT.md`
- Push, P3-007, candidate, tag, Release, and attestation: not performed
