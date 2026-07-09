# P1-003.1 Seed and Legacy Article Fix

## Current Status

- Previous P1-003 status: BLOCKED
- P1-003.1 fix: PASS
- P1-003 20-Article Medium Batch Phase: PASS
- Recommendation: A: Ready for P1-004 50-article phase

This revision is a targeted P1 fix. It does not execute a 50-article, 100-article, or full-corpus crawl, does not generate PDFs, and does not commit Article corpus/runtime artifacts.

## Root Cause

The previous P1-003 run was blocked by related discovery, seed, parsing, and resume issues:

- RSS only provided the recent article window. A second-page RSS check did not extend discovery coverage, so RSS alone was insufficient for the 20-article medium batch.
- Manual seeds were unstable and could include legacy or non-standard pages such as `https://spaces.ac.cn/archives/12`.
- `archives/12` exposed a legacy/special-page extraction issue: the parsed content could collapse to title/page shell and trigger sidebar/comment/share/navigation contamination checks.
- The pilot selected `limit` candidates before validating them, so a failed candidate reduced the final valid Article count instead of being skipped and replaced.
- Existing runtime Articles outside the selected seed prefix were not counted first toward the cumulative 20-article target, which caused unnecessary extra live fetches on rerun.

## Uploaded Reference Files Used

External toolkit references were used only as design input:

- `/home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json`: used as the approved full seed-list format reference. It contains 1326 article metadata entries and remains outside git.
- `/home/lkx/Downloads/kexuefm_pdf_toolkit/fetch_articles.py`: used as the seed updater reference only.
- `/home/lkx/Downloads/kexuefm_pdf_toolkit/download_pdfs.py`: used as the print cleanup selector reference only.
- `/home/lkx/Downloads/kexuefm_pdf_toolkit/README.md`: used to confirm the PDF workflow boundary and that PDF batch export is not part of this task.

The full seed list remains outside git. PDF workflow code was not imported and no PDF batch was run.

## Fixes

- Added approved seed-list support for JSON object, JSON list, and text URL files.
- Reused canonicalization to normalize `spaces.ac.cn` and `kexue.fm` archive aliases to `https://spaces.ac.cn/archives/{id}`.
- Rejected non-article URLs before browser access.
- Added legacy `#PostContent` body selection and page chrome cleanup before Markdown conversion.
- Classified invalid candidates separately from invalid imported content.
- Allowed invalid legacy/non-article candidates to be skipped and replaced without writing contaminated content to storage.
- Counted existing valid runtime Articles first toward the cumulative target before fetching additional seed candidates.

## Seed List Behavior

Implemented seed-file loading supports:

- JSON object format with an `articles` list.
- JSON list format.
- Text files with one URL per line.

Accepted article URLs are canonicalized to:

```text
https://spaces.ac.cn/archives/{id}
```

Rejected before browser access:

- search URLs
- category/tag URLs
- comments/fragments after canonical dedupe
- non-article paths
- unsupported hosts

When `--seed-file` is supplied, the pilot can use the seed list as the candidate source without requiring RSS discovery. This avoids duplicate overlap between recent RSS items and the full seed prefix.

## Archives/12 Handling

Targeted live diagnostics:

- URL: `https://spaces.ac.cn/archives/12`
- Initial browser diagnostic result: HTTP 403 in the current environment.
- Targeted seed probe: `archives/12` was fetched/parsed as a non-importable candidate and skipped.
- Replacement behavior: `https://spaces.ac.cn/archives/119` was imported successfully.

Targeted seed probe metrics:

| Metric | Value |
|---|---:|
| status | PASS |
| target_count | 1 |
| discovered_url_count | 2 |
| canonical_url_count | 2 |
| selected_count | 1 |
| attempted_count | 2 |
| imported_count | 1 |
| invalid_candidate_count | 1 |
| invalid_imported_content_count | 0 |
| skipped_non_article_or_legacy_page | 1 |
| sample_article_ids | 119 |

Decision:

- `archives/12` is not written to storage when it does not meet Article quality gates.
- The pilot continues to later approved seed candidates to satisfy the valid Article target.

## Contamination Guard Behavior

Parser/converter regression coverage now includes legacy `#PostContent` structure and page chrome removal.

Guarded page chrome includes:

- `#Sidebar`
- `#Header`
- `#Footer`
- `#PostComment`
- `#MainMenuiPad`
- `#share`
- `#kimi`
- `.navigation`
- classes containing `sidebar`, `menu`, or `comment`

Regression checks verify:

- title extraction remains correct
- content comes from the article body
- MathJax/LaTeX delimiters are preserved
- images and references are preserved
- sidebar/comment/share/navigation content does not enter `Article.content`

## Validation Metric Changes

The pilot summary now distinguishes:

- `invalid_candidate_count`: fetched/parsed candidates that are not importable and are not written.
- `invalid_imported_content_count`: invalid content already present in the Article store.
- `skipped_non_article_or_legacy_page`: candidate skip count for legacy/non-article/page-shell cases.

Success requires:

- valid cumulative Article target reached
- `invalid_imported_content_count=0`
- content completeness and formula validation pass
- no page chrome contamination in imported content

## Live Rerun Result

Command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --limit 20 \
  --delay-seconds 5 \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Final result:

| Metric | Value |
|---|---:|
| status | PASS |
| target_count | 20 |
| discovered_url_count | 20 |
| canonical_url_count | 20 |
| duplicate_count | 0 |
| selected_count | 20 |
| attempted_count | 0 |
| imported_count | 20 |
| failed_count | 0 |
| skipped_count | 20 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| invalid_candidate_count | 0 |
| invalid_imported_content_count | 0 |
| parser_quality_issues | 0 |

The final command used existing validated runtime Articles after the cumulative resume fix. A preceding live run with the same seed file imported additional real Articles, then exposed the resume-counting issue; no invalid imported content was written.

## Tests

Backend:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
113 passed, 2 skipped
```

Frontend:

```bash
npm run build
```

Result:

```text
Compiled successfully
```

RAG/tutor evaluation:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Result:

```text
Overall: PASS
```

## Artifact Policy

Runtime outputs remain under ignored `.local_data/`.

No PDF, HTML dump, image, browser trace/profile/cache, full seed list, Article corpus JSON, or runtime artifact is intended for git.

## Remaining Risks

- External browser access can still fail transiently.
- Legacy pages can remain non-importable and must continue to be skipped instead of forced into storage.
- The full 1326-entry seed list is an operator input and must remain outside git.
- Runtime Article store state affects cumulative reruns; reports must record whether a run is fresh or resumed.

## Recommendation

A: Ready for P1-004 50-article phase
