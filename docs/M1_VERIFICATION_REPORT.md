# M1 Verification Report

## Architecture Check

Result: PASS for module presence and internal pipeline structure.

Evidence:

- `backend/app/crawler/` contains `cache.py`, `discovery.py`, and `downloader.py`.
- `backend/app/parser/article.py` contains the article parser and `ParsedArticle`.
- `backend/app/converter/markdown.py` contains HTML-to-Markdown conversion.
- `backend/app/storage/article_store.py` contains Article persistence.
- `backend/app/validation/quality.py` contains quality validation.
- `backend/app/sync.py` contains the unified sync entry point.

The pipeline order is represented by `SyncRunner.run()`:

1. discover article URLs
2. download article HTML
3. parse HTML
4. upsert Article records
5. validate stored Articles
6. write validation report

## Data Schema Check

Result: PASS.

Evidence:

- `backend/app/storage/article_store.py` defines `StoredArticle` with:
  - `id`
  - `title`
  - `url`
  - `content`
  - `metadata`
- `StoredArticle.to_dict()` serializes the same five fields.
- `ArticleStore.upsert()` derives `metadata` with:
  - `date`
  - `category`
  - `references`
  - `images`

This matches `docs/04_DATA_MODEL.md` and `milestones/M1_SOURCE_PIPELINE.md`.

## Test Check

Result: PASS for automated test coverage requested by the gate.

Fresh command:

```bash
uv run --project backend --extra dev pytest
```

Result:

```text
9 passed
```

Coverage evidence by file:

- Crawler: `backend/tests/test_crawler.py`
- Parser and converter: `backend/tests/test_parser_converter.py`
- Storage: `backend/tests/test_storage_validation_sync.py`
- Validation: `backend/tests/test_storage_validation_sync.py`
- Sync idempotency: `backend/tests/test_storage_validation_sync.py`

Fixture sync idempotency command:

```bash
uv run --project backend python -m app.sync \
  --data-dir /tmp/scientific-spaces-m1-verification/data \
  --index-file /tmp/scientific-spaces-m1-verification/index.html \
  --article-dir /tmp/scientific-spaces-m1-verification/articles \
  --max-pages 1
```

The command was run twice against the same fixture input.

Result:

```json
{
  "article_count": 1,
  "report": {
    "total_available": 1,
    "total_checked": 1,
    "title_presence_rate": 1.0,
    "content_completeness_rate": 1.0,
    "images_valid": true,
    "formulas_valid": true,
    "issues": []
  }
}
```

Forbidden-scope scan:

```bash
rg -n "Article API|Frontend Reader|Search UI|router\\.get\\(\\\"/articles|router\\.get\\('/articles|@router\\.get\\(\\\"/articles|RAG|Embedding|FAISS|LLM|Zotero|Knowledge Graph|AI Tutor|LearningState|Bookmark|Conversation|Citation|vector" backend frontend .github -S
```

Result: no matches.

## Risks

Result: BLOCKING RISK for live source access.

The default online sync path currently fails in this environment:

```bash
SCIENTIFIC_SPACES_DATA_DIR=/tmp/scientific-spaces-m1-live-check \
SCIENTIFIC_SPACES_MAX_PAGES=1 \
uv run --project backend python -m app.sync
```

Observed result:

```text
urllib.error.HTTPError: HTTP Error 403: Forbidden
app.crawler.downloader.DownloadError: Failed to download https://spaces.ac.cn/
```

This means the pipeline is verified with fixture input, but live Scientific Spaces ingestion is not verified as operational.

ADR:

- `ADR/0003-m1-live-source-access-blocker.md`

Non-blocking documentation gap already recorded:

- `ADR/0002-m1-source-pipeline-boundary-assumptions.md`

## M2 Readiness

Result: BLOCKED.

M1 passes module, schema, test, fixture idempotency, ADR, and forbidden-scope checks. However, M2 should not start until the live Scientific Spaces access blocker is resolved or an approved source-access strategy is accepted.

Project state should not be marked `M1 Verification Passed` while the default live sync path fails.
