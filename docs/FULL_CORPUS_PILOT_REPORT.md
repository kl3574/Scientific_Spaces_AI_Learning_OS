# Full Corpus Pilot Report

## Current Status

- P1-001 Pilot: PASS
- Scope: bounded 10-article pilot only
- Recommendation: A: Ready for 100-article medium batch planning

This task implemented and executed a controlled full-corpus pilot workflow. It did not execute a full crawl, did not generate a PDF batch, did not submit article corpus artifacts, and did not change M1-M7 frozen contracts.

## Scope

Selected article count:

- `10`

Discovery method:

- RSS recent discovery from `https://spaces.ac.cn/feed`
- No seed file was used.
- No manual URL list was used.
- No archive ID probing was used.
- No search pages or search engine scraping were used.

No full crawl confirmation:

- The pilot selected only the first 10 canonical RSS article URLs.
- The runner enforces `limit <= 30`.
- The runner enforces `concurrency = 1`.

No PDF batch confirmation:

- The pilot does not call `ArticlePdfExporter`.
- No PDF files were generated.
- PDF export remains independent from Article.content success.

Coverage notes:

- Ordinary/new recent Scientific Spaces articles were covered through RSS.
- Mathematical/formula-heavy articles were covered, and `formula_valid_rate=1.0`.
- Category metadata was present for imported articles.
- `references` and `images` metadata fields were preserved for every imported article.
- No approved old seed URL was available for this pilot; historical coverage remains a seed-list limitation.
- No short article was encountered in the current RSS sample; `short_content_count=0`.

## Implementation Changes

Files changed:

- `backend/app/crawler/canonical.py`
- `backend/app/corpus/__init__.py`
- `backend/app/corpus/pilot.py`
- `backend/tests/test_canonical_urls.py`
- `backend/tests/test_full_corpus_pilot.py`
- `scripts/corpus/run_full_corpus_pilot.py`
- `docs/FULL_CORPUS_PILOT_REPORT.md`
- `docs/00_PROJECT_STATE.md`
- `README.md`
- `.gitignore`

Helper modules:

- `canonicalize_article_url(url)`
- `extract_archive_id(url)`
- `canonicalize_article_urls(urls)`
- `FullCorpusPilot`
- `PilotConfig`
- `PilotSummary`
- `classify_failure_reason(reason)`

CLI command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py --limit 10 --delay-seconds 3
```

CLI safeguards:

- `--limit` defaults to `10`.
- `--max-limit` defaults to `30`.
- `limit > 30` is rejected.
- `concurrency > 1` is rejected.
- `delay_seconds < 3` is rejected.
- `output_dir` must be under an ignored `.local_data` runtime directory.
- `--dry-run` is available and does not fetch articles.

## Discovery and Canonicalization

Live result:

| Metric | Value |
|---|---:|
| discovered_url_count | 10 |
| canonical_url_count | 10 |
| duplicate_count | 0 |
| selected_count | 10 |
| rejected URLs | 0 |

Sample article IDs:

- `11738`
- `11750`
- `11760`
- `11767`
- `11772`
- `11777`
- `11782`
- `11784`
- `11787`
- `11804`

Canonical URL policy:

- `spaces.ac.cn` article URLs normalize to `https://spaces.ac.cn/archives/{id}`.
- `kexue.fm` archive aliases normalize to the `spaces.ac.cn` canonical host.
- Non-article paths are rejected before browser access.

## Polite Crawling Evidence

Live pilot settings:

| Setting | Value |
|---|---:|
| concurrency | 1 |
| request_delay_seconds | 3.0 |
| selected_count | 10 |
| attempted_count | 10 |
| elapsed_seconds | 161.212 |

Retry/backoff:

- Browser fetcher uses bounded retry.
- Default pilot browser fetcher uses `retries=2`.
- Default pilot browser fetcher uses `backoff_seconds=3`.

Robots/source policy handling:

- The pilot checks `https://spaces.ac.cn/robots.txt` through `RobotFileParser` before article fetches.
- If robots/source policy cannot be confirmed, live pilot returns `BLOCKED` before fetching articles.
- This live run proceeded after the policy check.

Transient failures:

- `browser_transient_failures=0`
- `permanent_failures=0`
- `failed_url_categories={}`

Post-run resume check:

- A later default resume attempt encountered a source-side RSS/TLS transient before article selection.
- The command was stopped to avoid an unbounded wait before the robots timeout fix was added.
- Regression coverage now verifies discovery failures are summarized and existing runtime progress can be preserved or reconstructed from the runtime Article store.
- The final resume command returned `PASS` from the runtime Article store with `attempted_count=0`, `imported_count=10`, and `skipped_count=10`; no article refetch was needed.

Failure taxonomy implemented:

- timeout / TLS / handshake: `browser_transient`
- HTTP 403 / 429: `browser_transient`
- missing article body / empty HTML / content extraction failure: `invalid_content`
- robots/source policy failure: `permanent_failure`

## Import and Validation Result

Live pilot result:

| Metric | Value |
|---|---:|
| attempted_count | 10 |
| imported_count | 10 |
| failed_count | 0 |
| skipped_count | 0 |
| content_completeness_rate | 1.0 |
| formula_valid_rate | 1.0 |
| metadata_completeness_rate | 1.0 |
| short_content_count | 0 |
| invalid_content_count | 0 |
| browser_transient_failures | 0 |
| permanent_failures | 0 |

Parser quality issues:

```text
[]
```

Article metadata check:

- Imported articles: 10
- Every imported article has `date`, `category`, `references`, and `images` metadata keys.
- Image counts ranged from 2 to 5.
- Explicit extracted reference entries were 0 for the current sample, but the `references` field is preserved in every Article record.

Quality gate result:

- HTTP success was not treated as article success.
- Browser HTML was required to pass the existing article body gate.
- Parsed content was validated before storage.
- Invalid content was not written to Article storage.
- No sidebar/comment/share script/navigation contamination was reported.
- Formula delimiter validation passed.

## Artifact Policy

Runtime output path:

```text
.local_data/scientific_spaces/corpus/pilot
```

Runtime files created:

- `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json`
- `.local_data/scientific_spaces/corpus/pilot/failed_urls.jsonl`
- `.local_data/scientific_spaces/corpus/pilot/progress.json`
- `.local_data/scientific_spaces/corpus/pilot/validation_summary.json`

Git ignore status:

- `.local_data/` ignores all runtime pilot outputs.
- `.gitignore` also contains corpus/runtime/PDF/cache-related ignore rules.

No committed artifacts:

- No article corpus JSON committed.
- No PDF committed.
- No HTML dump committed.
- No runtime progress, failed URL, validation summary, browser profile, trace, cache, FAISS index, or embedding cache committed.

## Test Evidence

Targeted TDD tests:

```text
uv run --project backend --extra dev pytest -q backend/tests/test_canonical_urls.py backend/tests/test_full_corpus_pilot.py
15 passed in 0.07s
```

Backend pytest:

```text
uv run --project backend --extra dev pytest -q
102 passed, 2 skipped in 3.85s
```

Frontend build:

```text
npm run build
Compiled successfully
Generated static pages (8/8)
```

Eval CLI:

```text
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
Overall: PASS
```

Live pilot command:

```bash
uv run --project backend python scripts/corpus/run_full_corpus_pilot.py --limit 10 --delay-seconds 3
```

Live pilot result:

```json
{
  "status": "PASS",
  "discovered_url_count": 10,
  "canonical_url_count": 10,
  "duplicate_count": 0,
  "selected_count": 10,
  "attempted_count": 10,
  "imported_count": 10,
  "failed_count": 0,
  "skipped_count": 0,
  "content_completeness_rate": 1.0,
  "formula_valid_rate": 1.0,
  "metadata_completeness_rate": 1.0,
  "invalid_content_count": 0,
  "browser_transient_failures": 0,
  "permanent_failures": 0
}
```

## Risks

Source volatility:

- RSS and article access can change outside project control.

Browser transient errors:

- Timeout, TLS handshake, HTTP 403, and HTTP 429 are classified separately from data-quality blockers.

Parser drift:

- External DOM changes can still require a future M1.x/P1.x targeted fix.

Seed coverage limitations:

- RSS recent discovery does not prove historical full-corpus coverage.
- Old article coverage requires an approved seed list or separately approved backfill strategy.

Full run scaling risks:

- JSON Article storage is acceptable for pilot, but full corpus should be evaluated against persistence and backup policy.
- Downstream RAG, graph, and tutor performance must be measured before large corpus operation.

## Recommendation

A: Ready for 100-article medium batch planning

Recommended next task:

- P1-002 100-Article Medium Batch Planning / Gate
