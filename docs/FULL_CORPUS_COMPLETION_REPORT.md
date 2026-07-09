# Full Corpus Completion Report

## Current Status

- P1-015 Final Corpus Completion Batch: PASS
- Completion definition: all importable canonical Articles completed
- Recommendation: A: Ready for post-corpus RAG/Graph/Tutor scaling tasks

## Completion Definition

This gate completes the approved canonical seed set by importing every safely importable `Article.content` record and classifying every non-importable candidate. It does not require 1326 valid Articles because parser quality gates must not be weakened for legacy or structurally invalid pages.

## Scope

| Metric | Result |
| --- | ---: |
| total_seed_count | 1326 |
| canonical_url_count | 1326 |
| final_valid_article_count | 1311 |
| non_importable_candidate_count | 15 |
| remaining_unclassified_seed_count | 0 |
| year-based claim | no |
| PDF batch | no |
| runtime artifact commit | no |

The approved local seed file was used only as runtime input:

```text
/home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

The full seed file was not copied into the repository and was not committed.

## Execution Summary

Final completion command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json \
  --delay-seconds 8 \
  --complete-all-seed
```

Execution evidence:

| Metric | Result |
| --- | ---: |
| existing_runtime_count | 1000 |
| final_valid_article_count | 1311 |
| unique newly attempted seed count | 326 |
| newly_imported_count | 311 |
| source retry attempts after initial completion | 2 |
| delay_seconds | 8.0 |
| concurrency | 1 |
| max_consecutive_failures | 5 |
| initial completion elapsed_seconds | 5324.305 |
| resolved resume elapsed_seconds | 60.804 |
| final idempotent elapsed_seconds | 0.624 |

Resume behavior:

- Existing 1000 valid Articles were reused from local runtime storage.
- Previously classified non-importable candidates were reused.
- `archives/654` had one transient browser failure and succeeded on resume.
- `archives/142` had a stale `net::ERR_CONNECTION_CLOSED` terminal classification from the first run; the runner was fixed to treat that as transient and the article succeeded on resume.

## Candidate Classification

| Category | Count |
| --- | ---: |
| valid_imported | 1311 |
| invalid_candidate | 15 |
| non_importable_candidate | 15 |
| skipped_non_article_or_legacy_page | 15 |
| permanent_failure | 0 |
| browser_transient_failure_open | 0 |
| remaining_unclassified_seed_count | 0 |

Non-importable candidates:

| URL | Reason |
| --- | --- |
| `https://spaces.ac.cn/archives/1023` | formula delimiters look unbalanced |
| `https://spaces.ac.cn/archives/116` | formula delimiters look unbalanced |
| `https://spaces.ac.cn/archives/12` | content extraction failed; page chrome contamination detected |
| `https://spaces.ac.cn/archives/196` | formula delimiters look unbalanced |
| `https://spaces.ac.cn/archives/2709` | article body not detected |
| `https://spaces.ac.cn/archives/3604` | formula delimiters look unbalanced |
| `https://spaces.ac.cn/archives/3644` | formula delimiters look unbalanced |
| `https://spaces.ac.cn/archives/3936` | formula delimiters look unbalanced |
| `https://spaces.ac.cn/archives/4797` | formula delimiters look unbalanced |
| `https://spaces.ac.cn/archives/49` | formula delimiters look unbalanced |
| `https://spaces.ac.cn/archives/531` | article body not detected |
| `https://spaces.ac.cn/archives/561` | formula delimiters look unbalanced |
| `https://spaces.ac.cn/archives/639` | page chrome contamination detected |
| `https://spaces.ac.cn/archives/9444` | page chrome contamination detected |
| `https://spaces.ac.cn/archives/9775` | page chrome contamination detected |

The classification registry is ignored runtime output:

```text
.local_data/scientific_spaces/corpus/pilot/completion_classifications.json
```

## Import and Validation Metrics

| Metric | Result |
| --- | ---: |
| final_valid_article_count | 1311 |
| duplicate_count | 0 |
| missing_content_count | 0 |
| invalid_imported_content_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| parser_quality_issues_open | 0 |
| consecutive_failure_peak | 1 |

All invalid candidates were rejected before storage. No invalid imported content entered the runtime Article store.

## Idempotent Rerun

Final idempotent rerun command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json \
  --delay-seconds 8 \
  --complete-all-seed
```

Final idempotent result:

| Metric | Result |
| --- | ---: |
| status | PASS |
| attempted_count | 0 |
| newly_imported_count | 0 |
| final_valid_article_count | 1311 |
| non_importable_candidate_count | 15 |
| remaining_unclassified_seed_count | 0 |
| elapsed_seconds | 0.624 |

The final rerun reused local Article storage and terminal classifications. It did not fetch article source pages.

## Local Corpus Materialization

Command:

```bash
uv run --project backend python scripts/corpus/materialize_local_library.py \
  --article-store-path .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --output-dir .local_data/scientific_spaces/corpus/local_library
```

Result:

| Metric | Result |
| --- | ---: |
| article_count | 1311 |
| exported_markdown_count | 1311 |
| missing_content_count | 0 |
| no_source_fetch | true |

## Final Local Corpus Audit

Command:

```bash
uv run --project backend python scripts/corpus/audit_local_library.py \
  --article-store-path .local_data/scientific_spaces/corpus/pilot/article_store/articles.json \
  --local-library-dir .local_data/scientific_spaces/corpus/local_library
```

Result:

| Metric | Result |
| --- | ---: |
| audit status | PASS |
| article_store_count | 1311 |
| unique_url_count | 1311 |
| duplicate_count | 0 |
| missing_content_count | 0 |
| markdown_file_count | 1311 |
| index_json_count | 1311 |
| index_csv_count | 1311 |
| materialization_summary_count | 1311 |
| sample_frontmatter_valid | true |
| sample_content_non_empty | true |
| no_source_fetch | true |

## Artifact Policy

Not committed:

- runtime Article store
- local Markdown library
- full seed file
- PDF files
- HTML dumps
- browser trace/profile/cache
- FAISS/vector cache

Runtime outputs remain under ignored `.local_data/`.

## Test Evidence

Targeted final-completion tests:

```text
uv run --project backend --extra dev pytest -q backend/tests/test_full_corpus_pilot.py backend/tests/test_seed_list.py backend/tests/test_local_corpus_audit.py
55 passed
```

Regression tests for transient network classification:

```text
uv run --project backend --extra dev pytest -q backend/tests/test_full_corpus_pilot.py::test_transient_failures_are_classified_separately backend/tests/test_full_corpus_pilot.py::test_complete_all_seed_retries_stale_terminal_registry_entry_for_transient_network_failure
2 passed
```

Full verification:

```text
uv run --project backend --extra dev pytest -q
173 passed, 2 skipped
```

```text
npm run build
PASS
```

```text
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
Overall: PASS
```

## Risks and Limitations

- Year metadata remains conditional; year-based legacy stress is still blocked by unavailable per-article year/date metadata.
- The corpus contains safe importable Article content only, not every canonical seed as a valid Article.
- Full-corpus PDF export was not run in this gate.
- RAG, Graph, and Tutor scaling rebuilds against the 1311-Article corpus still need separate post-corpus tasks.
- Future source changes can alter browser acquisition behavior; the runner preserves bounded retry and failure logging.

## Recommendation

A: Ready for post-corpus RAG/Graph/Tutor scaling tasks.
