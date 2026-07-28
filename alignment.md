# P3-006.2 Review UX Pilot and Zotero Collection Sync Alignment

Canonical task:
`docs/tasks/P3-006_2_REVIEW_UX_ZOTERO_COLLECTION_SYNC.md`

## 1. Background

- P3-006 remains `CONDITIONAL / CLOSED`.
- P3-006.1 Stage A produced a 64-case bounded worksheet, but Stage B remains
  `HUMAN_REVIEW_INCOMPLETE`.
- The bounded excerpts are not ergonomic enough for the operator's intended
  review.
- The user requested a separate three-case full-context pilot and explicitly
  authorized creating the private local Zotero collection `苏剑林博客` plus
  one controlled test item.
- This task must not redefine the 64-case P3-006.1 closure gate.

## 2. Requirements

1. Create or reuse exactly one root Zotero collection named `苏剑林博客`.
2. Verify the collection through Zotero Desktop readback.
3. Add at most one controlled real Scientific Spaces article item.
4. Add an idempotent downstream Zotero sync adapter for Article metadata.
5. Sync Web Page metadata first; a PDF attachment is optional and must not
   block metadata synchronization.
6. Match by Article ID and canonical URL so repeat synchronization does not
   create duplicates.
7. Do not modify the frozen crawler or source pipeline.
8. Create a separate three-case pilot using authoritative full Article content.
9. Keep full content, worksheets, collection keys, private metadata, and all
   runtime output outside Git.
10. Run focused tests, the Backend suite, security/artifact checks, and create
    one local commit. Do not push.

## 3. Purpose

Provide an ergonomic, local full-context review pilot while establishing a
safe, opt-in Zotero archive destination for future Scientific Spaces articles.

## 4. Planned Execution

1. Recheck governance, Git, Article identity, current Zotero integration, and
   Zotero Desktop readiness.
2. Persist this alignment and the P3-006.2 canonical task.
3. Start Zotero Desktop if necessary.
4. Create or reuse `苏剑林博客`, then verify its unique collection identity.
5. Implement a downstream collection sync client and CLI without touching M1.
6. Test idempotency, collection targeting, unavailable-Zotero behavior, and
   metadata mapping with fixtures.
7. Synchronize one controlled real Article and verify collection membership.
8. Generate an ignored three-case full-context pilot package.
9. Run tests, secret/artifact audits, changed-path checks, and confirm source
   stores are unchanged.
10. Update aggregate governance/report files and create one local commit.

## 5. Selection Rationale

A downstream adapter preserves the frozen acquisition pipeline and makes
external Zotero writes explicit, restartable, and independently testable.
The three-case pilot improves review ergonomics without weakening the existing
64-case formal evidence contract.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Write to Zotero directly from the crawler | Rejected: violates M1 freeze and couples acquisition to a private application |
| Manual Zotero import only | Rejected as the long-term path: not idempotent automation |
| Replace the formal 64 cases with 3 | Rejected: insufficient evidence for the existing precision gate |
| Downstream sync plus separate 3-case pilot | Selected |

## 7. Deliverables

- `docs/tasks/P3-006_2_REVIEW_UX_ZOTERO_COLLECTION_SYNC.md`
- `backend/app/zotero/sync.py`
- `backend/tests/test_zotero_sync.py`
- `scripts/zotero/sync_scientific_spaces.py`
- `docs/P3_006_2_REVIEW_UX_ZOTERO_SYNC_REPORT.md`
- Updated current-task, project-state, and v1.2-roadmap pointers
- Private local Zotero collection `苏剑林博客`
- One controlled real test item at most
- Ignored three-case full-context pilot package
- One local commit; no push

## 8. Acceptance Criteria

- The target collection exists exactly once and readback succeeds.
- Repeating sync for the same Article returns a no-op and creates no duplicate.
- The item is a Web Page with title, URL, date, category, and Article ID
  provenance.
- No unrelated Zotero item or collection is changed or deleted.
- The three pilot cases cover strong identifier, duplicate, and ambiguous or
  Zotero strata and expose authoritative full Article content locally.
- The pilot is marked `PILOT ONLY` and cannot close P3-006.1.
- M1 crawler, Article Store, Reference Store, and the existing 64-case
  worksheet remain byte-unchanged.
- No private Zotero data, collection key, full Article content, runtime file,
  local path, or secret is tracked.
- Focused and full Backend tests pass; secret and artifact audits pass.
- Commit message is exactly
  `feat: add Scientific Spaces Zotero collection sync`.
- Push, P3-007, candidate, tag, Release, and attestation remain not performed.
