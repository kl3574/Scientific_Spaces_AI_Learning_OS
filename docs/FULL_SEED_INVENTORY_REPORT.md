# Full Seed Inventory Report

## Current Status

- P1-007 Full Seed Inventory Dry Run: CONDITIONAL
- Canonical seed inventory: PASS
- Year-based partition inventory: CONDITIONAL
- Full corpus execution: NOT STARTED
- Recommendation: C: Need seed source decision

This task performed seed inventory only. It did not access article body pages, did not import `Article.content`, did not execute a 200/400/700/1000/1326 batch, did not execute full corpus processing, did not generate PDFs, and did not commit runtime corpus data.

## Scope

Included:

- Read approved local seed metadata.
- Parse seed entries.
- Canonicalize article URLs.
- Deduplicate by canonical URL / archive ID.
- Reject non-article URLs.
- Compute cumulative target partitions.
- Compute year-based partition structure when year metadata is present.
- Write ignored runtime inventory summary.

Excluded:

- live article fetch
- BrowserArticleFetcher
- parser/converter live content path
- Article storage writes
- PDF export
- full corpus execution
- 200/400/700/1000/1326 content batches
- committed full seed list
- committed runtime artifacts

## Seed Source

Approved local seed path:

```text
/home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json
```

Seed source policy:

- The seed file was used only as local runtime input.
- The full 1326-entry `article_list.json` was not copied into the repository.
- The committed report includes aggregate metrics and limited sample IDs only.

Seed format observed:

| Field | Value |
|---|---:|
| JSON shape | object with `articles` list |
| raw count | 1326 |
| parsed count | 1326 |
| item keys | `id`, `url`, `title` |
| date/year field present | no |

## Canonicalization Result

Dry-run command:

```bash
uv run --project backend python scripts/corpus/run_seed_inventory.py \
  --seed-file /home/lkx/Downloads/kexuefm_pdf_toolkit/article_list.json \
  --output-dir .local_data/scientific_spaces/corpus/inventory \
  --year-partition true
```

Result:

| Metric | Value |
|---|---:|
| raw_seed_count | 1326 |
| parsed_seed_count | 1326 |
| canonical_url_count | 1326 |
| duplicate_count | 0 |
| rejected_url_count | 0 |
| non_article_url_count | 0 |
| kexue_alias_count | 0 |
| spaces_canonical_count | 1326 |
| min_archive_id | 4 |
| max_archive_id | 11804 |

Sample first 10 archive IDs:

```text
11804, 11787, 11784, 11782, 11777, 11772, 11767, 11760, 11750, 11738
```

Sample last 10 archive IDs:

```text
13, 11, 10, 9, 8, 7, 6, 5, 4, 12
```

Canonical URL policy verified:

- Accepted final format: `https://spaces.ac.cn/archives/{id}`.
- `spaces.ac.cn` archive URLs canonicalize to the expected final host.
- `kexue.fm` alias handling is covered by regression tests and canonicalizes to the expected final host.
- Non-article URL rejection is covered by regression tests.

## Data Quality

| Metric | Value |
|---|---:|
| missing_id_count | 0 |
| missing_url_count | 0 |
| missing_title_count | 0 |
| missing_year_count / unknown_year_count | 1326 |

Data quality decision:

- URL inventory quality is sufficient for cumulative staged execution planning.
- Year-based partition execution is not ready because the current seed file does not include date/year metadata.
- Title values in the seed appear intentionally shortened for some entries; this is acceptable for seed inventory because title is not the Article content source of truth.

## Year Statistics

Year stats from seed metadata:

```json
{}
```

Unknown year count:

```text
1326
```

Decision:

- Year statistics cannot be computed from the current approved seed file.
- This is not a URL inventory blocker, but it blocks reliable year-based batch partitioning.
- A later seed source decision or metadata enrichment task is required before a year-based legacy stress batch can be executed.

## Cumulative Batch Partitions

Cumulative partitions from the 1326 canonical seed URLs:

| Target | Already completed | New needed | Candidate end index |
|---|---:|---:|---:|
| 200 | 100 | 100 | 200 |
| 400 | 100 | 300 | 400 |
| 700 | 100 | 600 | 700 |
| 1000 | 100 | 900 | 1000 |
| 1326 | 100 | 1226 | 1326 |

Execution rule:

- Each target is cumulative.
- The existing 100 valid runtime Articles are counted first.
- Later content batches must only fetch the delta needed for the target.
- Every content batch must finish with an idempotent rerun.

## Year-Based Partitions

Configured year partitions:

| Partition | Count | Legacy-heavy |
|---|---:|---|
| 2026-2024 | 0 | false |
| 2023-2021 | 0 | false |
| 2020-2018 | 0 | false |
| 2017-2015 | 0 | false |
| 2014-2012 | 0 | true |
| 2011-2009 | 0 | true |

Interpretation:

- Counts are zero because the current seed lacks date/year fields, not because there are no articles in those years.
- The partition definitions are available for future enriched seed metadata.
- Year-based legacy stress testing should not be scheduled until year metadata is available and validated.

## Inventory Runtime Output

Runtime output path:

```text
.local_data/scientific_spaces/corpus/inventory
```

Runtime file written:

```text
inventory_summary.json
```

Artifact policy:

- Runtime output is ignored and not committed.
- No Article store was created.
- No progress file, failed URL log, validation summary, PDF, HTML dump, browser trace/profile, DB file, or cache is intended for git.

## Test Evidence

Targeted inventory tests:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_seed_inventory.py
```

Result:

```text
7 passed
```

Covered behavior:

- article_list object format parsing
- `spaces.ac.cn` archive URL canonicalization
- `kexue.fm` archive URL alias canonicalization
- non-article URL rejection
- duplicate archive ID dedupe
- missing title counted but not blocked
- missing URL rejected
- cumulative partition target computation
- year-based partition count computation when year metadata exists
- runtime output under ignored `.local_data`
- no Article storage write by inventory dry-run

Full backend tests:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
129 passed, 2 skipped
```

Frontend build:

```bash
npm run build
```

Result:

```text
Compiled successfully
```

RAG/Tutor eval:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Result:

```text
Overall: PASS
```

## Risks

1. Year metadata gap
   - Current seed only contains `id`, `url`, and `title`.
   - Year-based partitioning requires enriched seed metadata or a separate metadata source.

2. Title truncation in seed
   - Some seed titles appear shortened.
   - This is acceptable for URL inventory, but seed title should not be treated as authoritative Article metadata.

3. Old article legacy drift
   - Full corpus includes low archive IDs and likely old DOM structures.
   - Legacy stress testing remains necessary before full execution.

4. Seed freshness
   - The local seed is an operator-provided snapshot.
   - RSS remains useful for recent freshness checks.

5. Local path dependency
   - The approved seed currently lives outside the repository.
   - Future operators need either the same local path or an explicitly approved equivalent seed path.

6. Full corpus runtime duration
   - Full content execution remains a multi-hour browser workflow and should proceed through staged gates only.

## Recommendation

C: Need seed source decision

Rationale:

- Canonical URL inventory is clean and complete for the current 1326-entry seed.
- The dry-run did not access live article pages and did not write Article storage.
- The current seed cannot support year-based partition counts because it lacks date/year metadata.
- Before the legacy stress batch, choose a year metadata source or approve cumulative-only execution for the next content phase.
