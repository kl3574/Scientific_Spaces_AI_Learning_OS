# M1.2 Parser Edge Case Revision

## 1. Current Blocker

M1 Final Freeze remains blocked by article content fidelity for:

- URL: `https://spaces.ac.cn/archives/11787`
- Symptom: live sync imports the article with `Article.content` length `37`
- Validation issue: `content extraction failed: article body not detected`

This is a data quality blocker, not a transient single-article timeout.

## 2. Root Cause

The failing live sync path receives a `200` response for article `11787`, but the captured HTML does not contain the Scientific Spaces article container.

Evidence from the same fetch path used by sync:

- HTTP status: `200`
- HTML length: `9559`
- DOM selectors present:
  - `#content > .Post`: `false`
  - `#content .Post`: `false`
  - `.Post`: `false`
  - `article`: `false`
  - `.entry`: `false`
- Parsed content length: `37`
- Parsed date: `None`
- Parsed category: `None`
- Images: `0`
- References: `0`

The parser cannot recover article body content from this HTML because the body container is absent. The observed output is a page title fragment, not a real short article.

## 3. DOM Evidence Summary

Control evidence from the same live sync run:

| URL | Content length | Date | Category | Images | Formula delimiters |
| --- | ---: | --- | --- | ---: | --- |
| `https://spaces.ac.cn/archives/11777` | `8067` | present | present | `2` | balanced |
| `https://spaces.ac.cn/archives/11782` | `9951` | present | present | `2` | balanced |
| `https://spaces.ac.cn/archives/11784` | `7122` | present | present | `2` | balanced |
| `https://spaces.ac.cn/archives/11787` | `37` | missing | missing | `0` | balanced |
| `https://spaces.ac.cn/archives/11804` | `11117` | present | present | `2` | balanced |

Independent Playwright diagnostics in earlier M1.2 investigation showed that `11787` can expose `#content > .Post` when the browser waits for the article container, but the current sync browser fetch path can return before that container is available or after an incomplete title-only document is observed.

## 4. Fix Strategy

Implemented protective fixes within the allowed M1.2 scope:

1. Preserve MathJax script formulas through Markdown conversion without escaping LaTeX characters.
2. Add a regression fixture for the `11787` article structure using representative, minimal HTML rather than downloaded full HTML.
3. Improve validation so short real notes are not automatically failed, while title-only or page-shell extraction failures are explicitly reported.

Not implemented in this task:

- Browser Access Provider waiting strategy changes.
- Sync failure handling changes.
- Crawler, RSS discovery, storage schema, or M1 Verification standard changes.

## 5. Code Changes

Changed:

- `backend/app/converter/markdown.py`
  - Replaces MathJax scripts with stable placeholders before `markdownify`.
  - Restores raw inline and display LaTeX after Markdown conversion.

- `backend/app/validation/quality.py`
  - Adds content quality classification.
  - Distinguishes real short semantic content from title-only/page-shell extraction failures.
  - Keeps formula delimiter validation unchanged.

- `backend/tests/test_parser_converter.py`
  - Adds a `11787` article structure regression test.
  - Verifies article body selection, formula preservation, images, and references.

- `backend/tests/test_storage_validation_sync.py`
  - Adds a validation regression test for short notes versus extraction failures.

- `backend/tests/fixtures/scientific_spaces_11787_article.html`
  - Minimal representative fixture only.
  - Does not store downloaded full HTML or article artifacts.

## 6. Regression Tests

Command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
20 passed, 2 skipped
```

Regression coverage:

- `11787` fixture title extraction.
- Article body selection over sidebar/comment/navigation noise.
- Non-math script exclusion.
- MathJax inline and display formula preservation.
- Formula delimiter balance.
- Image metadata extraction.
- Reference metadata extraction.
- Validation distinction between true short content and extraction failure.

## 7. Live Validation Result

Command:

```bash
SCIENTIFIC_SPACES_DATA_DIR=/tmp/scientific-spaces-m1-parser-edge-live \
uv run --project backend python -m app.sync --max-articles 5
```

Result:

```text
Scientific Spaces sync completed: discovered=5, imported=5, failed=0, validated=5
```

Metrics:

- Article count: `5`
- Unique URL count: `5`
- Duplicate count: `0`
- `formulas_valid`: `true`
- `images_valid`: `true`
- `title_presence_rate`: `1.0`
- `content_completeness_rate`: `0.8`
- Validation issues:
  - `https://spaces.ac.cn/archives/11787: content extraction failed: article body not detected`

Article `11787` blocker status:

- Not resolved.
- The current browser fetch path imports title-only HTML for this URL.
- Parser/converter changes work on representative complete DOM but cannot reconstruct missing article HTML.

## 8. Remaining Risks

- Browser fetch can return incomplete title-only HTML while reporting HTTP `200`.
- Current browser access success checks only verify non-empty HTML, not article container presence.
- Sync stores parser output even when article body extraction has failed.
- Similar slow-loading or environment-dependent article pages may produce the same failure.

## 9. M1 Freeze Readiness Recommendation

Recommendation:

`B: Need additional M1 work`

M1 Freeze should remain blocked until the live sync path verifies that article `11787` imports with a real article body and no validation issues.

Recommended next task:

Create an M1.3 revision focused on source HTML acquisition quality:

- Browser Access Provider waits for `#content > .Post` or another approved article container.
- Browser Access Provider rejects title-only/page-shell HTML as a fetch failure.
- Sync does not store articles when parser extraction fails.

Do not proceed to M2 until this M1 blocker is resolved.
