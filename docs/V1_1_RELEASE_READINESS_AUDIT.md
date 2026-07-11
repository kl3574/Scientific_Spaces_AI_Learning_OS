# v1.1 Release Readiness Audit

## Current Status

- Candidate version: `v1.1.0`
- Current formal version: `v1.0.0`
- Audit: BLOCKED
- Recommendation: C: Blocked
- Audit baseline commit: `f00d596a5ab3ef43a9ef57230ab51eee80fe0d81`
- Audit date: 2026-07-11

The candidate is not ready for release actions. A frozen M2 API behavior changed incompatibly: an unparameterized `GET /articles` now returns only the first 20 Articles instead of the complete matching list. This gate records the blocker and does not modify implementation code, create a tag, or create a GitHub Release.

## Release Scope

Included platform hardening:

- pull-request, main-push, tag-push, and manual CI;
- local development and local production-like deployment profiles;
- security/privacy baseline and provider/secret boundaries;
- opt-in Learning SQLite migration with JSON rollback;
- local inventory, health, cleanup, essential backup, verification, and isolated restore.

Included full-local-corpus scope:

- 1,326 canonical seeds;
- 1,311 validated Articles;
- 15 classified non-importable candidates, 0 unclassified;
- 1,311 Markdown files and 1,311 PDFs;
- full-corpus Reader/Search, RAG, Knowledge Graph, and bounded Tutor selection.

Explicitly excluded:

- multi-user production deployment, authentication, or authorization;
- managed cloud database or complete store migration;
- encrypted/off-site backup service;
- live exhaustive web research or autonomous paper download;
- real-provider semantic-quality certification;
- complete remote-image offline archive or source print parity;
- completion of the conditional year-based legacy partition;
- a claim that all 1,326 canonical URLs yield importable Article content.

## Completed Work

- M1-M7 implementation and verification remain complete.
- P0 deployment, security/privacy, persistence, CI, and evaluation-harness work is present.
- P1 controlled corpus work completed all safely importable candidates and materialized the local Markdown library.
- P2-001 through P2-006 completed full-corpus RAG, Reader UX, Graph, Tutor, PDF, and local-data hardening.
- The latest runtime assets share Article corpus fingerprint `cc8717db54615bfcc426b64826c8b38565ddba901707582657331ae9772cdf5d`.

## Version and Project State Audit

- `Version` remains `v1.0.0`, as required before release creation.
- `Candidate Version` is recorded separately as `v1.1.0`.
- Project phase/status is updated to a blocked v1.1 release-readiness gate, not released or ready-to-tag status.
- M1-M7 PASS records remain intact.
- P1-007 and P1-009 remain `CONDITIONAL`; the audit does not convert historical year-metadata evidence into a full PASS.
- P2-001 through P2-006 remain PASS.
- PDF source-print parity and real-provider quality are not marked complete.
- Backend/frontend package manifests still use internal bootstrap version `0.1.0`; they are private application components and are not published package artifacts. The Git tag remains the product release identifier.

Documentation consistency findings:

- Historical roadmap and v1.0 audit files retain older CI/test snapshots; they are historical evidence, not current candidate status.
- P0 task numbering differs between the initial roadmap and later execution reports. This is a traceability issue, not a runtime or release-contract blocker.
- Dedicated `docs/RELEASE_CI_EVIDENCE_v1.0.0.md` remains the canonical exact-tag v1.0 evidence; other referenced v1.0 runs are later successful reruns.

## Full Regression Results

| Check | Current result |
|---|---|
| Backend pytest | PASS: 453 passed, 3 skipped in 46.71 s |
| Frontend build | PASS: Next.js 15.5.20, 8 routes generated |
| Frontend Graph tests | PASS: 7/7 |
| Frontend Tutor tests | PASS: 13/13 |
| Original RAG/Tutor baseline | PASS: 9 cases, all required rates 100% |
| Full-corpus RAG evaluation | PASS: 12 queries, hit@10 90.91%, errors/fabrications 0 |
| Graph benchmark | PASS: bounded responses; cold 1,347.9 ms; warm max 76.3 ms |
| Tutor Graph context smoke | PASS: 20 nodes, 19 edges, full graph not injected |
| Full-corpus Tutor evaluation | PASS: 42 cases, 0 hard/validity failures |
| PDF resume/idempotency | PASS: 1,311 unchanged, 0 failed, 1,311 validation PASS |
| Configured operations health | PASS: zero issues |
| Essential backup/verify/restore | PASS: 4 files, isolated restore and hash verification PASS |
| Production-like backend/frontend | PASS: API/routes/Article detail/Graph/Tutor smokes |

No source crawl, corpus rebuild, RAG rebuild, Graph rebuild, PDF rebuild, or complete backup was run by this gate.

## CI Audit

Workflow: `.github/workflows/ci.yml`

Triggers confirmed:

- `pull_request`
- `push` to `main`
- `push` of `v*` tags
- `workflow_dispatch`

Jobs confirmed:

- Backend pytest
- Frontend build
- Docker compose smoke

Backend and frontend run on every event. Docker smoke intentionally runs only for manual dispatch and tag pushes.

CI governance limitations:

- `npm run test:graph` and `npm run test:tutor` are not workflow jobs; this gate ran them locally.
- Dependency and dedicated secret scanners are not CI jobs.
- Actions use mutable major-version tags and the `uv` installer is not version-pinned.
- `main` currently has no branch protection requiring the successful checks.

Latest pre-audit main evidence:

- run: `29154850374`
- URL: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29154850374`
- head SHA: `f00d596a5ab3ef43a9ef57230ab51eee80fe0d81`
- conclusion: success
- backend pytest: success
- frontend build: success
- Docker compose smoke: skipped as designed for an ordinary main push

The audit commit has not been pushed by this task, so it has no GitHub Actions run yet. Main CI after that push and exact-tag CI are mandatory release actions.

## Full-Corpus Evidence

Fresh local validation summary:

| Metric | Value |
|---|---:|
| canonical seeds | 1,326 |
| valid imported Articles | 1,311 |
| non-importable classified candidates | 15 |
| unclassified candidates | 0 |
| unique Article URLs | 1,311 |
| duplicate URLs | 0 |
| missing content | 0 |
| invalid imported content | 0 |
| content completeness | 100% |
| metadata completeness | 100% |
| formula validity | 100% |
| Markdown files | 1,311 |

All imported Articles have `id`, `title`, `url`, `content`, and `metadata`, with `date`, `category`, `references`, and `images` metadata keys. Structured reference arrays are currently empty for all 1,311 Articles; this is recorded as a limitation rather than misrepresented as reference extraction coverage.

## Reader/RAG/Graph/Tutor Evidence

Reader:

- `GET /articles` returned the expected summary fields and total 1,311.
- `GET /articles/{id}` returned the frozen detail fields and all metadata keys.
- A real Article detail rendered in Chromium with HTTP 200 and 14,691 visible content characters.
- Core frontend routes returned HTTP 200.

RAG:

- 1,311 Articles, 5,547 chunks, 100% Article coverage.
- Empty/duplicate chunks and missing title/URL/section metadata: 0.
- Current deterministic evaluation retained no-source refusal and citation/source schema behavior.

Graph:

- 52,874 nodes and 82,230 edges with 100% Article coverage.
- Integrity audit has no blocking metrics.
- Current benchmark and 17-check production Graph UI smoke passed with zero external requests or unexpected console errors.

Tutor:

- 42-case deterministic evaluation passed with zero hard or validity failures.
- Current 17-check live local Tutor UI smoke passed with zero external requests and no local-path disclosure.
- Refusal and source-grounding boundaries remain in effect.

## PDF Evidence

- Input and selected Articles: 1,311.
- Valid PDFs: 1,311; failed/corrupt/empty/stale: 0.
- Resume result: 1,311 unchanged; exported/regenerated: 0.
- Total PDF bytes: 830,490,049.
- Total pages: 7,152.
- Formula Articles: 809; formula render failures: 0.
- Remote image placeholders: 4,728; broken/empty image references: 1.
- External network requests: 0.

This is offline derived output. It does not claim remote-image completeness or source-site print parity.

## Backup and Recovery Evidence

Fresh essential backup drill:

- profile: essential; PDF excluded;
- files: 4;
- archive size: 14,978,927 bytes;
- archive mode: `0600`;
- source manifest fingerprint: `828f3c54d24e22fff961ee5b543182221056bd1cb23ae5e1e111c11eac0f425f`;
- independent verify: PASS, zero issues;
- isolated restore: PASS, 4 files;
- source/restored Article counts: 1,311 / 1,311;
- source/restored unique URLs: 1,311 / 1,311;
- source/restored missing content: 0 / 0;
- source/restored Article-store SHA-256: identical.

Configured health returned PASS with zero issues. Without the full-corpus Reader/Tutor environment variables, the same assets return WARN with two actionable configuration notices; that is not data corruption.

The temporary archive and restore tree are removed after this audit. This evidence validates the procedure but does not constitute a retained user backup.

## Deployment and Security Evidence

- Local production-like backend and frontend startup succeeded.
- `/health`, Article API, Graph summary, and core routes passed smoke checks.
- The Article, Graph, and Tutor Chromium smokes made no external request.
- Fake providers remained selected; no real API key was needed.
- Local Docker is unavailable. Existing v1.0 exact-tag CI covers Docker, and the `v1.1.0` tag workflow must provide fresh Docker evidence.
- Security/privacy and deployment verification reports remain PASS for the declared local, single-user scope.
- Authentication, authorization, public exposure, managed storage, and multi-user isolation remain outside the release scope.

## Artifact and Secret Audit

The tracked-file scan covered the 310-file pre-audit baseline. All six task-owned Markdown changes, including four new files, were subsequently inspected through the staged diff before commit.

Results:

- No tracked `.local_data`, corpus store, Markdown library, PDF, FAISS index, chunk store, Graph runtime, backup, restore, DB, browser artifact, log, `node_modules`, `.next`, or `.env`.
- The only tracked HTML files are three bounded parser regression fixtures.
- The largest tracked file is `frontend/package-lock.json` at 122,988 bytes; no large runtime artifact is tracked.
- High-confidence current secret-pattern scan: no match.
- Finite high-confidence secret-pattern scan across `v1.0.0..HEAD`: no match.
- Environment-assignment hits were limited to redacted test/document examples.
- Absolute local paths occur in documentation examples and path-sanitization tests, not runtime/private tracked payloads.
- `.gitignore` correctly covers local corpus, PDF, RAG/FAISS, Graph, databases, backups, restores, browser artifacts, and frontend build/dependency paths.
- The 45-commit `v1.0.0..HEAD` path history contained no runtime artifact path and no new blob at or above 1 MiB.
- Broad image/HTML/profile extensions are not globally ignored, but no current or finite-history tracked artifact exploited those gaps; changing ignore policy is not required by this gate.

Artifact/secret result: PASS.

## Documentation Audit

Created for the candidate:

- `docs/RELEASE_NOTES_v1.1.0_DRAFT.md`
- `CHANGELOG.md`
- `docs/V1_1_RELEASE_CHECKLIST.md`
- this audit report

Updated:

- `docs/00_PROJECT_STATE.md`, while retaining formal `Version: v1.0.0`;
- README candidate status and verification links only.

Historical planning reports intentionally remain unchanged. Superseded statuses must be read together with later completion reports. Missing historical `docs/15_ACCEPTANCE.md`, `docs/31_MVP_BOUNDARY.md`, and the renamed M7 milestone remain documentation hygiene gaps, not release blockers.

## Freeze and Compatibility Audit

- M1 Article schema remains `id`, `title`, `url`, `content`, `metadata` with the four frozen metadata keys.
- A documented targeted P1-003.1 legacy parser revision added `#PostContent` selection and page-chrome removal. It did not remove or reshape the frozen Article contract, and current parser/full-corpus regressions pass. The task naming did not follow the preferred `M1.x` convention; this is recorded as a governance deviation, not a critical contract regression.
- M2 Article summary/detail fields remain present, but the default list behavior is not compatible. At `v1.0.0`, unparameterized `GET /articles` returned every matched Article in original store order and the response contained exactly `items`, `total`, and `query`. The candidate defaults to `page=1`, `page_size=20`, changes ordering, adds response keys, and silently omits items after the first 20. Current tests replaced the old contract assertion instead of preserving a compatibility case.
- Fresh direct reproduction against the completed store returned `total=1311`, `items=20`, `page=1`, `page_size=20`, and `sort=date_desc` for an unparameterized request.
- M3 citations, source fields, and no-source refusal remain covered by current tests and evaluations.
- M4 JSON remains default and SQLite is opt-in. The documented migration requires manual API recreation rather than an identity-preserving importer, and switching back to JSON does not merge writes made while SQLite was active. This is a migration/rollback limitation that must be stated precisely.
- M5 local Zotero access remains read-only.
- M6 provenance/evidence remains source-grounded and the legacy full Graph endpoint remains. However, default `GET /graph/nodes` total semantics changed and managed full-corpus configuration can make `POST /graph/build` return 409. These behaviors need explicit compatibility tests and upgrade notes in the same targeted revision.
- M7 source grounding and refusal aliases remain covered; new summaries and full-corpus selection are additive.

A critical frozen-contract regression was found in the M2 Article list. Passing current tests and UI smoke does not prove backward compatibility because the regression suite now asserts the replacement pagination contract. Full-corpus scaling cannot be classified as wholly additive until this behavior is restored, versioned, or explicitly approved as a breaking release.

## Known Risks and Accepted Limitations

### Blockers

- **M2 Article list compatibility:** unparameterized `GET /articles` silently truncates a v1.0 client-visible result from all matches to 20 and changes default ordering/response shape. This violates the frozen M2 contract and the gate requirement that full-corpus scaling be a compatible enhancement.

### Medium risks

- No authentication, authorization, or multi-user isolation; the system must not be publicly exposed as a production multi-user service.
- JSON stores are not concurrent production storage; SQLite covers only Learning and is opt-in.
- Local data can be lost without a retained verified backup; `git clean -fdX` deletes ignored assets.
- The PDF tree is about 832 MB including metadata, and complete backup/restore needs additional disk.
- Backup encryption and off-site redundancy are not provided.
- Real-provider cost, rate, privacy, latency, and answer quality vary and are not certified.
- Source-site structure/access can change; derived indexes and Graph become stale after corpus changes.
- The Graph is a 75 MB single-process JSON baseline with a visible cold-load cost.
- SQLite migration does not preserve all JSON identities/timestamps automatically, and JSON rollback does not include writes made in SQLite mode.
- Graph default query/build behavior changed under the full-corpus profile and needs explicit compatibility coverage.
- The post-freeze M1 parser fix is documented and tested but was named P1-003.1 rather than an explicit M1.x revision, creating a freeze-governance deviation.

### Low risks

- Historical P0 numbering and CI-run references are not perfectly normalized.
- Backend/frontend package versions are internal `0.1.0` values rather than product tag versions.
- Local Docker is unavailable; tag CI is the required Docker evidence source.
- Structured reference metadata is empty even though inline links remain in content.
- Frontend Graph/Tutor tests are local-only, main has no required branch protection, and CI has no dependency/secret scanner job.
- CI action references and the `uv` installer are not pinned to immutable revisions.

### Accepted limitations

- Local-first and single-user only.
- Fake-provider baseline is structural evidence, not real-LLM certification.
- Tutor Research is local-corpus-only, not exhaustive web research.
- Remote PDF images are placeholders; source print parity is not implemented.
- Year-based legacy partition completion remains conditional.
- Complete backup is not automatically retained, encrypted, or uploaded.

## Proposed Release Procedure

Release actions are blocked. The required sequence is:

1. Commit this blocker report using `docs: record v1.1 release blockers`.
2. Open and execute a targeted `P2-008 v1.1 API Compatibility and Migration Revision`.
3. Restore/version the M2 Article list contract and add a regression with more than 20 Articles that proves the approved no-parameter behavior.
4. Audit M6 default query/build compatibility and document or test the approved behavior.
5. Add a verified migration/rollback procedure that states which Learning identities and writes are preserved.
6. Re-run P2-007 from a clean commit and require recommendation A before any tag action.
7. Only after a PASS re-run: push the audit commit, pass main CI, create annotated tag `v1.1.0`, pass tag CI including Docker, and publish the GitHub Release.

## Proposed Tag

- tag: `v1.1.0`
- type: annotated
- target commit: not authorized while this audit is BLOCKED
- immutable predecessor: `v1.0.0` remains unchanged at peeled target `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6`

## Findings

### Blockers

- Unparameterized `GET /articles` no longer preserves the frozen v1.0 list behavior and can silently hide 1,291 of 1,311 Articles from an unchanged client.

### Medium risks

- Learning migration/rollback fidelity, M6 default behavior compatibility, M1 freeze-governance traceability, local/multi-user security boundary, retained backup discipline, real-provider variability, source drift, and large derived-asset operations.

### Low risks

- Historical documentation numbering/run-reference drift, internal package version labels, local Docker availability, and empty structured reference metadata.

### Accepted limitations

- Local-only scope, fake-provider structural evidence, image placeholders, conditional year metadata, and no built-in encrypted/off-site backup.

## Final Recommendation

C: Blocked.

All current tests, build, evaluations, runtime smokes, PDF idempotency, health, backup/restore, artifact, and secret checks passed. They do not override the frozen API regression. Do not create `v1.1.0`; execute the targeted compatibility/migration revision and re-run this gate.
