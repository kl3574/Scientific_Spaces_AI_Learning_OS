# M1.4 Incremental Source and Zotero PDF Sync Alignment

Canonical task:
`docs/tasks/M1-4_INCREMENTAL_SOURCE_ZOTERO_SYNC.md`

Status: **LOCAL PASS / AWAITING MAIN CI**

NETWORK / PRIVATE ZOTERO WRITE AUTHORIZATION: **CONSUMED / CLOSED**

LOCAL FILE MODIFICATION / COMMIT / PUSH AUTHORIZATION: **GRANTED THROUGH MAIN CI CLOSURE**

CANDIDATE / TAG / RELEASE AUTHORIZATION: **NOT GRANTED**

## 1. Background

- P3-009 completed the frozen 1,311-Article corpus and private Zotero
  browser-printed PDF synchronization in local commit
  `048a0f9d1e9b0162e1d020a7c6a98ed4e961e27a`.
- That commit was one commit ahead of cached `origin/main` when P3-009 closed
  and has not yet been synchronized to GitHub.
- A low-frequency RSS check observed at least three newer Scientific Spaces
  Article URLs outside the frozen 1,326-URL inventory.
- M1 is frozen. This separately authorized M1.4 task adds an incremental
  orchestration path without mutating existing Article content, schemas, or
  legacy/API contracts.
- The accepted private Zotero representation remains one browser-printed A4
  PDF child and zero live HTML children per Article parent.

All repository, remote, feed, browser, and Zotero facts must be revalidated
before use.

## 2. Requirements

1. Revalidate Git state and confirm the P3-009 commit is the only unpushed
   commit.
2. Push the P3-009 commit to `origin/main` and verify its main CI.
3. Add a local CLI that reads the official Scientific Spaces RSS feed and
   discovers only Article URLs missing from the configured Article Store.
4. Fetch only missing canonical Articles through the authorized desktop
   browser path; do not scan archive IDs or crawl archive/search pages.
5. Reuse existing parser, converter, Article Store, PDF validator, and Zotero
   contracts without changing existing stored `Article.content`.
6. Generate browser-printed A4 PDFs after MathJax settles and synchronize them
   into the private Zotero root collection `苏剑林博客`.
7. Persist resumable runtime checkpoints and make repeated runs idempotent.
8. Keep Zotero writes sequential and require exactly one PDF and zero HTML
   children per new parent.
9. Add unit, integration, and separately marked live tests.
10. Run full Backend, Frontend, feature, secret, artifact, and changed-path
    validation.
11. Create and push one implementation commit, then verify main CI.
12. Do not call a real or paid AI Provider or commit private/runtime data.

## 3. Purpose

Provide a repeatable incremental update command that safely carries newly
published Scientific Spaces Articles into the local Article Store and private
Zotero PDF collection without reprocessing the completed corpus.

## 4. Planned Execution

1. Persist this alignment and canonical M1.4 task.
2. Verify the local branch, commit, remote, authentication, and CI workflow.
3. Push and validate the existing P3-009 commit.
4. Inspect current RSS, browser acquisition, parser, storage, PDF, Zotero, and
   checkpoint interfaces.
5. Implement additive incremental discovery and orchestration under non-frozen
   paths.
6. Add deterministic fixture tests and isolated live markers.
7. Run a read-only delta preview, then a bounded authorized live update for
   missing RSS Articles.
8. Validate Article content, metadata, formulas, PDF fidelity, Zotero
   cardinality, and readback.
9. Rerun the command to prove zero unnecessary fetches and zero writes.
10. Run complete local validation and repository audits.
11. Update governance/report files, commit, push, and verify main CI.

## 5. Selection Rationale

An additive CLI keeps source discovery, browser acquisition, parsing, PDF
printing, and Zotero writes explicit and recoverable. RSS provides a bounded
official discovery surface. Reusing existing contracts avoids destabilizing
the frozen full-corpus pipeline.

## 6. Alternatives

| Option | Decision |
| --- | --- |
| Add an explicit incremental CLI | Selected: bounded, testable, and resumable |
| Modify the original full-corpus sync directly | Rejected: unnecessary frozen-path risk |
| Reprocess all 1,311 Articles on every update | Rejected: slow and creates needless source access |
| Install a background scheduler immediately | Deferred until the manual incremental path has live evidence |

## 7. Deliverables

- updated `alignment.md`
- `docs/tasks/M1-4_INCREMENTAL_SOURCE_ZOTERO_SYNC.md`
- updated `docs/tasks/CURRENT_TASK.md`
- `backend/app/zotero/incremental_sync.py`
- `scripts/zotero/update_latest_blog_pdfs.py`
- focused Backend tests and separately marked live tests
- `docs/M1_4_INCREMENTAL_SOURCE_ZOTERO_SYNC_REPORT.md`
- updated `README.md`, `docs/00_PROJECT_STATE.md`, and
  `docs/V1_2_ROADMAP.md`
- implementation commit:
  `feat: add incremental blog Zotero PDF sync`
- main-push CI evidence for P3-009 and M1.4

## 8. Acceptance Criteria

- P3-009 commit is pushed without history rewrite and its required main CI
  jobs pass.
- Official RSS discovery deterministically identifies existing versus missing
  canonical Article URLs without archive scanning.
- Every imported Article has valid title, content, metadata, balanced formula
  delimiters, and preserved references/images.
- Existing Article records and content remain byte-for-byte unchanged.
- Every new Zotero parent has exactly one validated browser-printed A4 PDF and
  zero live HTML children.
- The immediate rerun produces zero Article fetches, zero Zotero writes, and
  zero duplicate parent/PDF records.
- Unit and integration tests pass; live tests are separately marked and do not
  affect default CI.
- Full Backend tests, Frontend focused tests/build, Reader/Search and relevant
  offline feature smokes pass.
- Secret and artifact audits report no credible secret or tracked
  runtime/private artifact.
- No frozen M1 module, Article schema, legacy/API contract, candidate, tag,
  Release, real Provider, or paid request change occurs.
- The M1.4 implementation commit is pushed, required GitHub Actions pass, and
  final `main` is clean and synchronized with `origin/main`.

## Stop Conditions

- The task requires changing frozen crawler/parser/converter/storage code or a
  published contract.
- The working tree contains unknown changes or conflicts.
- Source policy, HTTP, content, browser, PDF, or Zotero quality gates fail
  after bounded retry/backoff.
- Existing Article content would need mutation.
- A secret or private/runtime artifact would enter Git.
- A real/paid Provider, candidate, tag, or Release action becomes necessary.
