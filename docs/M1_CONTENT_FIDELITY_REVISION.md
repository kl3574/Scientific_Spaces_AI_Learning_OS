# M1.1 Article Content Fidelity Revision

## Current Issue

M1 Final Freeze Gate was blocked because fresh live sync produced `Article.content` that was not reliable article body content.

Observed blocker from `docs/M1_FINAL_FREEZE_REPORT.md`:

- RSS discovery and browser access worked.
- Articles were imported and deduplicated.
- Stored content samples started with sidebar/comment-like text instead of the article body.
- `formulas_valid=false` in the freeze live validation sample.

This M1.1 revision does not implement M2 Reader, Search, RAG, or Learning System behavior.

## Root Cause

The root cause was in article parsing and Markdown conversion:

1. Parser root selection preferred `.content`.
   - Scientific Spaces live article pages use `#content > .Post` for the article body area.
   - A separate `.content` block can contain sidebar/comment content.
   - The parser selected that sidebar/comment block before reaching the article body.

2. Converter allowed non-math script text into Markdown.
   - Scientific Spaces article body includes share-widget JavaScript.
   - `markdownify(strip=["script"])` removed the tag but preserved script text.
   - This polluted `Article.content` with UI script text.

Formula corruption in the freeze report was a downstream symptom of parsing non-body text and script/comment content.

## Evidence

### Live HTML Diagnosis

Diagnostic URL:

- `https://spaces.ac.cn/archives/11777`

Browser access result:

| Field | Value |
|---|---|
| HTTP status | `200` |
| HTML length | `66279` |
| MathJax available | `true` |

Relevant selector evidence:

| Selector | Result |
|---|---|
| `.content` | Found one sidebar/comment-like block, text length `482` |
| `#content` | Found main page content block, text length `8001` |
| `#content > .Post` | Found article body area, text length `7217` |

Existing parser selected:

```text
div.content
```

Correct parser root:

```text
#content > .Post
```

### Parser Output Before Fix

For `https://spaces.ac.cn/archives/11777`, parser output had:

- correct title through fallback `<h1>`
- content from sidebar/comment links
- no images
- no references
- unbalanced dollar delimiters from non-article text

### Parser Output After Fix

Live validation after the fix produced article bodies with:

- article title/header
- article opening body paragraphs
- no recent-comment sidebar content
- no share-widget script text
- balanced formula delimiters

## Fix Plan

Implemented within the allowed M1.1 scope:

1. `backend/app/parser/article.py`
   - Prefer Scientific Spaces live article container selectors:
     - `#content > .Post`
     - `#content .Post`
     - `.Post`
   - Remove `.content` from article-root fallback selection.
   - Allow category extraction from the article root or the parent `#content` area so `#tools` category metadata can still be captured.

2. `backend/app/converter/markdown.py`
   - Delete non-math `<script>` nodes before Markdown conversion.
   - Keep MathJax `<script type="math/tex">` and `<script type="math/tex; mode=display">` conversion behavior.
   - Delete `<style>` nodes before Markdown conversion.

3. `backend/tests/test_parser_converter.py`
   - Add regression coverage for Scientific Spaces live DOM structure.
   - Verify title, category, article body text, formula preservation, image extraction, references, and exclusion of sidebar/comment/script text.

4. `backend/tests/fixtures/scientific_spaces_live_post_article.html`
   - Add a representative Scientific Spaces live page structure:
     - sidebar `.content`
     - main `#content > .Post`
     - MathJax formula scripts
     - image
     - references
     - category outside `.Post`
     - non-math share script

## Validation Result

### Regression Test

Command:

```bash
uv run --project backend --extra dev pytest backend/tests/test_parser_converter.py -q
```

Result:

```text
3 passed
```

The new regression test first failed against the old parser because the parser selected sidebar `.content`. It then passed after the parser/converter fix.

### Full Pytest

Command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
18 passed, 2 skipped in 0.22s
```

### Live Content Fidelity Validation

Command:

```bash
SCIENTIFIC_SPACES_DATA_DIR=/tmp/scientific-spaces-m1-content-fidelity-live \
uv run --project backend python -m app.sync --max-articles 5
```

Result:

```text
Scientific Spaces sync completed: discovered=5, imported=4, failed=1, validated=4
```

Imported live article URLs:

- `https://spaces.ac.cn/archives/11782`
- `https://spaces.ac.cn/archives/11784`
- `https://spaces.ac.cn/archives/11787`
- `https://spaces.ac.cn/archives/11804`

Content fidelity checks:

| Check | Result |
|---|---|
| Content starts with article title/body context | PASS |
| Sidebar recent-comment content absent | PASS |
| Share-widget script text absent | PASS |
| Metadata keys include `date`, `category`, `references`, `images` | PASS |
| Formula validation | PASS |

Validation report:

```json
{
  "content_completeness_rate": 1.0,
  "formulas_valid": true,
  "images_valid": true,
  "issues": [],
  "title_presence_rate": 1.0,
  "total_available": 4,
  "total_checked": 4
}
```

Notes:

- The live validation was bounded to at most five RSS articles.
- One article failed at browser access during this live run; this is an access availability event, not a content fidelity failure for imported articles.
- RSS discovery and browser access strategy were not modified.

## Outcome

M1.1 content fidelity revision succeeded for imported live articles:

- `formulas_valid=true`
- article body sample correct
- sidebar/comment text excluded
- non-math script text excluded

Recommended next step:

- Re-run M1 Final Freeze & Handoff Gate as a separate task.
