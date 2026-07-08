# M1.3 Browser Access Quality Revision

## 1. Current Blocker

M1 Final Freeze was blocked because live sync imported:

- URL: `https://spaces.ac.cn/archives/11787`
- Previous content length: `37`
- Previous issue: `content extraction failed: article body not detected`

The previous M1.2 parser investigation showed that the parser can extract `11787` correctly when the browser HTML contains the article DOM, but the sync fetch path could return a title-only HTML document with HTTP `200`.

## 2. Root Cause

The Browser Access Provider accepted any HTTP `2xx` response with non-empty HTML.

That allowed a title-only page shell to pass as a successful article fetch even though it did not include an approved article body container such as:

- `#content > .Post`
- `#content .Post`
- `.Post`
- `article`
- `.post`
- `.entry`
- `#article`

Once that incomplete HTML reached parser/storage, `Article.content` became a page-title fragment rather than the article body.

## 3. Fix Strategy

Implemented a source HTML acquisition quality gate:

1. Browser fetch waits for an approved article body selector before collecting HTML.
2. Browser fetch success validation rejects non-empty HTML if no article body selector exists.
3. Title-only HTML triggers bounded retry instead of being returned as success.
4. Sync performs a second import-quality check after parsing and skips articles that fail content extraction validation.

This keeps incomplete source HTML out of storage while preserving existing parser, converter, storage schema, RSS discovery, and M1 Verification standards.

## 4. Code Changes

Changed:

- `backend/app/crawler/browser.py`
  - Added approved article body selectors.
  - Added article container validation for `BrowserFetchResult`.
  - Added Playwright `wait_for_selector` before HTML capture.

- `backend/app/sync.py`
  - Added per-article import quality gate after parsing.
  - Skips and records parser extraction failures before storage.

- `backend/tests/test_browser_provider.py`
  - Added regression coverage for title-only HTML retry.
  - Added regression coverage for title-only HTML rejection after bounded retries.

- `backend/tests/test_storage_validation_sync.py`
  - Added sync defense-in-depth coverage so parser extraction failures are not stored.

## 5. Regression Tests

Targeted commands:

```bash
uv run --project backend --extra dev pytest backend/tests/test_browser_provider.py -q
uv run --project backend --extra dev pytest backend/tests/test_storage_validation_sync.py::test_sync_runner_skips_browser_results_without_article_body -q
```

Full command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
23 passed, 2 skipped
```

## 6. Live Validation Result

Command:

```bash
SCIENTIFIC_SPACES_DATA_DIR=/tmp/scientific-spaces-m1-browser-quality-live \
uv run --project backend python -m app.sync --max-articles 5
```

Result:

```text
Scientific Spaces sync completed: discovered=5, imported=5, failed=0, validated=5
```

Validation metrics:

- Article count: `5`
- Unique URL count: `5`
- Duplicate count: `0`
- `title_presence_rate`: `1.0`
- `content_completeness_rate`: `1.0`
- `images_valid`: `true`
- `formulas_valid`: `true`
- `issues`: `[]`

Article `11787` live result:

- Title: `矩阵函数近似中的暴力美学`
- Content length: `18559`
- Date: `2026-06-25`
- Category: `数学研究`
- Images: `3`
- Formula delimiters: balanced
- Page-title marker in content: `false`
- Article body signal: `true`

## 7. Remaining Risks

- External site DOM changes may require updating the approved selector list.
- Browser runtime remains a required M1 source access dependency.
- Network or site-side transient failures can still occur, but title-only HTTP `200` responses are no longer accepted as successful article fetches.

## 8. M1 Freeze Readiness Recommendation

Recommendation:

`A: Ready for M1 Final Freeze Re-run`

The specific `11787` content fidelity blocker is resolved by current live evidence. The next step is to rerun the M1 Final Freeze & Handoff Gate and let that gate update project state if all freeze criteria pass.
