# ADR 0005: M1 Post-Freeze Corpus Compatibility Revisions

Status: Accepted

Date: 2026-07-11

## Context

Since tag `v1.0.0` (M1 freeze line), this repository implemented a corpus execution expansion and a set of parser/candidate-handling fixes while remaining on the M1 source-pipeline boundary.

This ADR records a compatibility audit for:
- `v1.0.0..HEAD` (M1-visible runtime path changes)
- existing `docs/P1_003_1_SEED_AND_LEGACY_FIX.md`

## Revision Marker

- Scope: **M1 post-freeze compatibility revision**
- Marker: `M1.x` style change packet for corpus/runtime compatibility, not schema migration.
- Required precondition for this revision: audited M1 pipeline behavior and evidence in `P1-003.1` + cumulative batch reports.

## Audit Scope and Non-Scope

In scope:
- `backend/app/corpus/`, `backend/app/crawler/canonical.py`, `backend/app/parser/article.py`, `backend/app/corpus/seeds.py`, `scripts/corpus/*`
- M1 batch evidence docs: `docs/MEDIUM_BATCH_*`, `docs/CUMULATIVE_*`, `docs/P1_003_1_*`, `docs/FULL_CORPUS_COMPLETION_REPORT.md`

Out of scope:
- M2-M7 feature growth (`tutor`, `graph`, `rag`, `learning`, `pdf`, etc.) that does not alter M1 contracts.

## Parser / Browser / Converter / Validation Delta

### Parser
- Changed file(s): `backend/app/parser/article.py`
- Changes:
  - Added `#PostContent` preference in content-root selection:
    - `("#PostContent", ".entry-content", ... )`
  - Added browser-page chrome cleanup before Markdown conversion:
    - selectors: `#Sidebar`, `#Header`, `#Footer`, `#PostComment`, `#MainMenuiPad`, `#share`, `#kimi`, `.navigation`, class contains `sidebar|menu|comment`
  - Kept output model unchanged (`ParsedArticle`: `title`, `url`, `content`, `date`, `category`, `images`, `references`).
- Evidence: implementation diff in `backend/app/parser/article.py`; regression test covers chrome filtering (`backend/tests/test_parser_converter.py`) and legacy body extraction (`docs/P1_003_1_SEED_AND_LEGACY_FIX.md`).

### Browser/Crawler path
- Changed file(s): `backend/app/crawler/canonical.py`
- Changes:
  - Added canonicalization for `spaces.ac.cn` / `www.spaces.ac.cn` / `kexue.fm` / `www.kexue.fm` archive URLs.
  - Rejects non-article URLs (search/category/comment/tag/fragment/unsupported host) before browser access.
  - Deduplicates canon candidates and records rejections.
- No changes in `backend/app/crawler/browser.py` are in this range (`git diff` in `backend/app/crawler` only shows `canonical.py`).
- Evidence:
  - `backend/app/crawler/canonical.py`
  - canonical behavior assertions in `backend/tests/test_canonical_urls.py` and `backend/tests/test_seed_list.py`

### Converter
- `v1.0.0..HEAD` changes to `backend/app/converter` are **explicitly none** (diff range check returns empty).
- No converter contract change.

### Validation
- `v1.0.0..HEAD` changes to `backend/app/validation` are **explicitly none** (diff range check returns empty).
- No validation contract change.

## Change Classification (M1-relevant)

| Type | Commit | Paths | Key impact |
|---|---|---|---|
| Expansion | `a398dd7` | `backend/app/corpus/pilot.py`, `backend/app/crawler/canonical.py`, CLI/scripts | Added bounded corpus pilot runner, runtime output artifacts, resume/policy checks |
| Bug | `ae28f56` | `backend/app/corpus/pilot.py`, `backend/app/parser/article.py`, `backend/tests/*`, `docs/P1_003_1...` | Fixed P1 medium-batch blocker: seed selection was not replacing invalid candidates, legacy DOM contamination, and invalid content could still consume target slots |
| Expansion | `6998f0d`, `9fc4dbd`, `cb955a3`, `9d281bd`, `f4d5221`, `a598267` | `backend/app/corpus/pilot.py` + scripts + tests | Grew bounded targets to 50/100/200/400/700/1000 with stricter rate-limit delay policy and resume semantics |
| Expansion | `5506a1c` | `backend/app/corpus/materialization.py`, `scripts/corpus/materialize_local_library.py` | Added local corpus materialization from stored Articles |
| Expansion | `5ff8cdd` | `backend/app/corpus/audit.py`, `backend/app/corpus/pilot.py`, `scripts/corpus/audit_local_library.py` | Added full completion + audit path (`--complete-all-seed`, terminal classification) |
| Contract | `ae28f56` + follow-up tests | `backend/app/corpus/pilot.py`, `backend/app/corpus/seeds.py` | Added/locked summary contract fields (`target_count`, `invalid_candidate_count`, `invalid_imported_content_count`, `skipped_non_article_or_legacy_page`, `remaining_unclassified_seed_count`, `final_completion_definition_used`) |
| Docs/operational | `e913a5c`, `bf6e40f`, `b3c0dc9`, `1b4c4ce`, `78d0696`, others | `docs/*` | Blocked/plan/risk capture and execution-state evidence updates |

## Required audit points requested

- `#PostContent` handling: implemented in parser selector fallback chain.
- Page chrome fix: removed before conversion via `_remove_page_chrome` and explicit contamination guard in quality issues.
- Candidate replacement: implemented in pilot loop by continuing through canonical list and replacing failed/legacy candidates; invalid candidates classified (not written) and skipped.
- Legacy skip: category `skipped_non_article_or_legacy_page` added and counted for non-article/legacy pages.
- Existing evidence of this behavior: `docs/P1_003_1_SEED_AND_LEGACY_FIX.md` + `backend/tests/test_full_corpus_pilot.py::test_invalid_candidate_is_skipped_and_replaced_without_storage_write`.

## Evidence Set (runtime/test/reports)

- `docs/P1_003_1_SEED_AND_LEGACY_FIX.md`
  - Reports `P1-003.1 fix: PASS`; command + metrics; invalid candidate count / skipped legacy behavior.
- `docs/MEDIUM_BATCH_20_ARTICLES_REPORT.md`
  - Initial `P1-003` blocked state and required follow-up trigger.
- `docs/MEDIUM_BATCH_50_ARTICLES_REPORT.md`
  - `P1-004` PASS.
- `docs/MEDIUM_BATCH_100_ARTICLES_REPORT.md`
  - `P1-005` PASS.
- `docs/CUMULATIVE_200_ARTICLES_REPORT.md`
  - `P1-008` PASS.
- `docs/CUMULATIVE_400_ARTICLES_REPORT.md`
  - `P1-011` PASS.
- `docs/CUMULATIVE_700_ARTICLES_REPORT.md`
  - `P1-012` PASS.
- `docs/CUMULATIVE_1000_ARTICLES_REPORT.md`
  - `P1-013` PASS.
- `docs/FULL_CORPUS_COMPLETION_REPORT.md`
  - `P1-015` PASS (1311 valid Articles, 15 non-importable candidates, no invalid imported content).
- Additional compatibility-oriented tests in affected range:
  - `backend/tests/test_full_corpus_pilot.py`
  - `backend/tests/test_seed_list.py`
  - `backend/tests/test_parser_converter.py`
  - `backend/tests/test_full_corpus_graph`, `backend/tests/test_full_corpus_rag_evaluation`, and aggregate backend/full-suite commands in phase reports.

## Article Schema Impact

- No storage schema file changes in `v1.0.0..HEAD` under `backend/app/storage`.
- Parser still feeds the same `StoredArticle` shape:
  - `id`, `title`, `url`, `content`, `metadata`
  - metadata required keys remain `date`, `category`, `references`, `images`.
- `ArticleStore` and schema-facing interfaces are not mutated in this diff window; post-freeze contracts remain aligned with M1 interface docs.

## Frozen M1 Compatibility

- The M1 final freeze rule requires post-freeze M1 edits to go through explicit M1.x revision tasks.
- This ADR serves that revision gate for corpus expansion/fixes.
- No storage schema drift and no parser output shape drift were introduced in this window.
- Canonicalization becomes stricter pre-browser, which is a contract-compatible tightening (reject non-archive URLs before sync), with no Article shape change.
- **No actual incompatibility in code-level contract is detected.**
  - Blocker remains only external/source-volatility risk (network, browser runtime behavior), already documented as operational risk in prior M1/M2 freeze reports, not as an internal M1 schema/interface regression.

## Decision

Treat the recorded post-freeze changes as one explicit M1.x compatibility revision. Keep the verified parser, canonicalization, candidate-replacement, and legacy-skip fixes. They are compatible with the frozen Article schema and improve source fidelity without changing the M1 storage or sync interface.

Future modifications to M1 crawler, browser access, parser, converter, validation, storage, or sync code still require a new M1.x revision task and evidence. This ADR is not blanket authorization for further M1 edits.

## Consequences

- No M1 compatibility blocker remains for the v1.1 candidate.
- Existing verified content fixes must not be rolled back to recover older faulty extraction behavior.
- Corpus expansion reports remain operational evidence, while the frozen Article data contract remains authoritative.
- External source and browser volatility remains a runtime risk rather than a schema incompatibility.

## Rollback and Verified-Fix Integrity

- No rollback/revert/rewrite commits detected in `v1.0.0..HEAD` (`git log --oneline --grep='revert|rollback' v1.0.0..HEAD` returned none).
- Verified fixes from `P1-003.1` are still present and consumed by later phases (50/100/200/400/700/1000 and final completion all-importable mode).
- Therefore: **No rollback of verified fixes** in this revision scope.
