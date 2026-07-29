# M1.4 Incremental Source and Zotero PDF Sync Report

Date: 2026-07-29

Status: **LOCAL PASS / AWAITING MAIN CI**

## 1. Scope

M1.4 adds an explicit incremental command for newly published Scientific
Spaces RSS Articles. It does not modify the frozen crawler, parser, converter,
storage implementation, Article schema, legacy API, `/v1.1` API, candidate,
tag, or Release state.

The authorized flow is:

```text
official RSS
  -> missing canonical Article URLs
  -> one-tab WebBridge acquisition
  -> existing parser and quality validator
  -> atomic Article Store append
  -> browser-printed A4 PDF
  -> sequential Zotero synchronization
  -> readback audit
```

## 2. Command

The default command is read-only:

```bash
uv run --project backend python \
  scripts/zotero/update_latest_blog_pdfs.py
```

Apply a validated delta only after Zotero Desktop and the WebBridge desktop
session are connected:

```bash
uv run --project backend python \
  scripts/zotero/update_latest_blog_pdfs.py --write
```

The command requires the successful ignored P3-009 throughput probe evidence,
uses its one-worker/four-second tier, acquires only RSS URLs absent from the
Article Store, and writes all checkpoints, backups, summaries, and temporary
PDFs under ignored `.local_data/`.

## 3. Safety Design

- RSS discovery is capped at 100 items and defaults to 50.
- The Article acquisition provider supports exactly one WebBridge tab.
- HTTP 403/429, invalid status, wrong URL, missing body, parser failure, and
  quality failure stop the delta before Article or Zotero writes.
- All missing Articles must validate before the atomic Store append.
- Existing Article records are compared using canonical per-record digests.
- A rolling pre-update recovery copy is written before each non-empty delta.
- Zotero writes are sequential and reuse the existing PDF quality/readback
  contract.
- Every final parent must have exactly one PDF and zero HTML children.
- The default invocation is a no-write preview; `--write` is explicit.
- An exclusive lock prevents concurrent runs against the same checkpoints.

## 4. GitHub Synchronization Prerequisite

The prior P3-009 commit
`048a0f9d1e9b0162e1d020a7c6a98ed4e961e27a` was pushed without history
rewrite. Main CI run
[`30413184122`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30413184122)
passed Backend pytest, Frontend build, workflow policy, dependency audit,
secret audit, and SBOM validation. Docker and release evidence were correctly
skipped for the ordinary main push.

## 5. Live Delta Result

The official feed returned 10 bounded Article URLs. Seven already existed and
three were new:

| URL | Title | Content chars | Images | References |
| --- | --- | ---: | ---: | ---: |
| `https://spaces.ac.cn/archives/11814` | LogSumExp和Softmax的泰勒展开 | 8,532 | 2 | 0 |
| `https://spaces.ac.cn/archives/11818` | 基于排序不等式的相似度指标 | 11,182 | 2 | 0 |
| `https://spaces.ac.cn/archives/11823` | 将Softmax Attention线性化为Gated DeltaNet | 23,696 | 2 | 0 |

Live write result:

- discovered: 10
- missing: 3
- acquired: 3
- stored: 3
- source browser navigations: 3
- Article Store: 1,311 -> 1,314
- existing 1,311 records unchanged: true
- content completeness rate: 1.0
- formulas valid: true
- validation issues: none
- Store SHA-256 before:
  `3b91f22db548373a6c91bb11a5188fb3e388ab9e19c4429e8e8fac918609a505`
- Store SHA-256 after:
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`

The empty reference arrays reflect the source pages parsed in this delta; they
are not dropped extraction results. All required metadata keys are present.

## 6. PDF and Zotero Result

The private root collection `苏剑林博客` completed at:

- parents: 1,314
- PDF children: 1,314
- HTML children: 0
- duplicate parents/PDFs: 0
- failed/deferred Articles: 0

All three new PDFs passed local and Zotero readback:

| URL | Size | Pages | A4 | Title | Chinese | MathJax | Body samples |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| `/archives/11814` | 602,014 bytes | 3 | PASS | PASS | PASS | PASS | 3/3 |
| `/archives/11818` | 621,651 bytes | 3 | PASS | PASS | PASS | PASS | 3/3 |
| `/archives/11823` | 723,838 bytes | 5 | PASS | PASS | PASS | PASS | 3/3 |

No PDF, HTML, image, browser profile, trace, Zotero identifier, or private
library export is committed.

## 7. Idempotency

The immediate second `--write` run passed with:

- missing Articles: 0
- Article acquisitions: 0
- Store writes: 0
- source navigations: 0
- PDF navigations: 0
- Zotero writes: 0
- Store count: 1,314 -> 1,314
- parents/PDF/HTML: 1,314 / 1,314 / 0
- staging PDFs after completion: 0

## 8. Test Evidence

Backend:

- focused incremental/Zotero/WebBridge tests: 16 passed, 1 skipped
- separately marked WebBridge live test: 1 passed, 5 deselected
- full suite: 592 passed, 4 skipped

Frontend:

- Article tests: 3 passed
- Reference tests: 3 passed
- Tutor tests: 13 passed
- Graph tests: 8 passed
- production build: PASS

Feature smoke:

- Reader total: 1,314
- title/content search found all three new Articles
- Article detail returned full content and complete metadata for all three
- Zotero Desktop local API and Connector: PASS
- existing Reference Store against the 1,314-Article Store:
  HTTP 503 `reference_store_stale`, as designed
- secret audit: PASS, zero credible findings
- frozen crawler/parser/converter/storage changed paths: none
- tracked runtime/private artifact findings: none (`.env.example` is the
  intentional secret-free template)

## 9. Derived Store Boundary

M1.4 deliberately does not rebuild RAG, Graph, or Reference Store artifacts.
Those immutable derived snapshots still correspond to the frozen 1,311-Article
corpus. Reader/Search and Zotero include 1,314 Articles immediately; the
Reference API explicitly rejects the stale snapshot instead of silently
serving mismatched provenance.

A separate, explicitly aligned derived-asset refresh task is required before
the three new Articles can appear in RAG, Graph, or structured references.
This limitation is not an M1.4 source/PDF/Zotero blocker.

## 10. Acceptance

Local implementation, live import, PDF fidelity, Zotero cardinality,
idempotency, Backend tests, Frontend tests/build, and compatibility checks:
**PASS**.

Main CI for the M1.4 implementation commit: **PENDING**.

Final M1.4 state remains **LOCAL PASS / AWAITING MAIN CI** until that exact
commit passes required GitHub Actions.
