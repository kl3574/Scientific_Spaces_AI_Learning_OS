# Local Corpus Materialization Report

## Current Status

- Local Corpus Materialization: PASS
- Source access: NOT USED
- PDF generation: NOT USED
- Runtime artifact commit: NOT USED

This task materializes the existing runtime Article store into local Markdown files. It does not fetch Scientific Spaces pages, does not call crawler/browser providers, does not generate PDFs, and does not commit exported Markdown, JSON, or CSV runtime outputs.

## Input Article Store

```text
.local_data/scientific_spaces/corpus/pilot/article_store/articles.json
```

Observed input:

| Metric | Value |
| --- | ---: |
| article count | 700 |
| records with content | 700 |
| missing content count | 0 |

## Output Library

Runtime output path:

```text
.local_data/scientific_spaces/corpus/local_library/
```

Generated runtime files:

```text
.local_data/scientific_spaces/corpus/local_library/articles/*.md
.local_data/scientific_spaces/corpus/local_library/index/articles_index.json
.local_data/scientific_spaces/corpus/local_library/index/articles_index.csv
.local_data/scientific_spaces/corpus/local_library/reports/local_library_summary.json
```

Materialization command:

```bash
uv run --project backend python scripts/corpus/materialize_local_library.py
```

Result:

| Metric | Value |
| --- | ---: |
| article_count | 700 |
| exported_markdown_count | 700 |
| missing_content_count | 0 |
| index JSON entries | 700 |
| index CSV generated | yes |
| summary JSON generated | yes |

## Markdown Format

Each exported Article Markdown file uses this structure:

```markdown
---
id: ...
title: ...
url: ...
date: ...
category: ...
---

# title

content
```

Filenames are generated from the archive ID plus a safe title slug. Unsafe path characters are removed, and files are written under the ignored `articles/` runtime subdirectory.

## No Source Fetch Confirmation

The materialization code reads only the local Article store JSON and writes local files. It does not import crawler/browser source modules, does not fetch RSS, does not access article URLs, and does not perform search-page discovery.

The runtime summary records:

```text
no_source_fetch: true
```

## Artifact Policy

Runtime output remains under ignored `.local_data/`.

Not committed:

- exported Markdown files
- local library index JSON
- local library index CSV
- local library summary JSON
- Article runtime store
- source seed list
- PDF files
- HTML dumps
- browser traces/profiles/cache

Committed:

- materialization code
- CLI wrapper
- tests
- this report

## Test Evidence

Targeted materialization tests:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_local_corpus_materialization.py
```

Result:

```text
6 passed
```

Backend test suite:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
161 passed, 2 skipped
```

Frontend build:

```bash
npm run build
```

Result:

```text
PASS
```

RAG/Tutor eval:

```bash
uv run --project backend python scripts/eval/run_rag_tutor_eval.py
```

Result:

```text
Overall: PASS
```

## Next Task

Push the local materialization commit and then continue with the next approved P1 task. The current local library is useful for human review and downstream offline corpus inspection, but it is runtime output and must remain outside git.
