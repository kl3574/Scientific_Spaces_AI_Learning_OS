# M1 Final Freeze Report

## 1. Current Status

| Item | Status | Evidence |
|---|---|---|
| M1 Source Pipeline | PASS | Modules present; ordinary pytest passes. |
| M1 Verification | PASS | `docs/00_PROJECT_STATE.md` records `M1 Verification Passed`. |
| M1 PDF Export | PASS | `docs/M1_PDF_EXPORT_EVALUATION.md` records 5/5 live PDF exports. |
| M1.1 Content Fidelity Revision | PASS for implemented fix | `docs/M1_CONTENT_FIDELITY_REVISION.md` records parser root and script-filtering fixes. |
| M1 Final Freeze Re-run | BLOCKED | Fresh live sync still produced one imported article with invalid content length. |

This is a freeze re-run after M1.1. It does not implement M2 Reader, Search, RAG, Learning System, or any new source-pipeline behavior.

## 2. Architecture Freeze

The current M1 architecture remains unchanged by this gate.

### Discovery

Current:

- RSS Discovery

Input:

- `https://spaces.ac.cn/feed`

Output:

- Article URL list matching `https://spaces.ac.cn/archives/{numeric_id}`

Implementation:

- `backend/app/crawler/rss.py`
- `discover_rss_article_urls(feed_url=DEFAULT_FEED_URL, fetch_xml=default_fetch_xml, max_items=None) -> list[str]`

### Access

Current:

- Playwright Browser Access

Input:

- Article URL

Output:

- `BrowserFetchResult(url, html, title, status, mathjax_available)`

Implementation:

- `backend/app/crawler/browser.py`
- `BrowserArticleFetcher.fetch(url) -> BrowserFetchResult`
- `BrowserArticleFetcher.fetch_many(urls) -> list[BrowserFetchResult]`

### Processing

Parser:

- `backend/app/parser/article.py`
- `parse_article_html(html: str, *, url: str) -> ParsedArticle`

Converter:

- `backend/app/converter/markdown.py`
- `html_to_markdown(html: str, base_url: str | None = None) -> str`

Storage:

- `backend/app/storage/article_store.py`
- `ArticleStore.upsert(article: ParsedArticle) -> StoredArticle`
- `ArticleStore.list_articles() -> list[StoredArticle]`
- `ArticleStore.count() -> int`

Validation:

- `backend/app/validation/quality.py`
- `ArticleQualityValidator.validate(articles) -> ValidationReport`

### Export

Current:

- PDF Export as an independent capability.

Implementation:

- `backend/app/export/pdf.py`
- `ArticlePdfExporter.export(url, output_path) -> PdfExportResult`
- `validate_pdf_file(path, url="") -> int`

Boundary:

- PDF export is not wired into `python -m app.sync`.
- PDF export is not part of M2 Reader or RAG.

## 3. Data Contract Freeze

The Article schema shape remains valid:

```text
Article
├── id
├── title
├── url
├── content
└── metadata
    ├── date
    ├── category
    ├── references
    └── images
```

Fresh live sample data contract result:

| Check | Result |
|---|---|
| `id`, `title`, `url`, `content`, `metadata` present | PASS |
| Metadata keys include `date`, `category`, `references`, `images` | PASS |
| Duplicate URLs absent | PASS |
| Content fidelity for all imported articles | FAIL |

The contract shape is stable, but one imported article failed the content quality threshold, so M1 is not ready to freeze as M2 input.

## 4. Interface Freeze

### Discovery Interface

```python
discover_rss_article_urls(
    feed_url: str = DEFAULT_FEED_URL,
    *,
    fetch_xml: Callable[[str], str] = default_fetch_xml,
    max_items: int | None = None,
) -> list[str]
```

### Browser Access Interface

```python
BrowserFetchResult(
    url: str,
    html: str,
    title: str,
    status: int | None,
    mathjax_available: bool,
)

BrowserArticleFetcher.fetch(url: str) -> BrowserFetchResult
BrowserArticleFetcher.fetch_many(urls: list[str]) -> list[BrowserFetchResult]
```

### Parser Interface

```python
ParsedArticle(
    title: str,
    url: str,
    date: str | None,
    category: str | None,
    content: str,
    images: list[str],
    references: list[dict[str, str]],
)

parse_article_html(html: str, *, url: str) -> ParsedArticle
```

### Storage Interface

```python
StoredArticle(
    id: str,
    title: str,
    url: str,
    content: str,
    metadata: dict[str, Any],
)

ArticleStore.upsert(article: ParsedArticle) -> StoredArticle
ArticleStore.list_articles() -> list[StoredArticle]
ArticleStore.count() -> int
```

### Export Interface

```python
PdfExportResult(
    url: str,
    output_path: Path,
    status: str,
    title: str,
    http_status: int | None,
    file_size_bytes: int,
    duration_seconds: float,
    mathjax_available: bool,
    error: str | None = None,
)

ArticlePdfExporter.export(url: str, output_path: Path | str) -> PdfExportResult
validate_pdf_file(path: Path | str, *, url: str = "") -> int
```

Interface freeze status:

- Interfaces are documented.
- Final M2 handoff remains blocked until live imported article content quality is consistently valid.

## 5. Test Evidence

### Ordinary Pytest

Command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
18 passed, 2 skipped in 0.20s
```

### M1 Live Sync Re-run

Command:

```bash
SCIENTIFIC_SPACES_DATA_DIR=/tmp/scientific-spaces-m1-freeze-rerun \
uv run --project backend python -m app.sync --max-articles 5
```

Result:

```text
Scientific Spaces sync completed: discovered=5, imported=5, failed=0, validated=5
```

Stored article metrics:

| Metric | Value |
|---|---:|
| article count | 5 |
| unique URL count | 5 |
| duplicate count | 0 |

Imported article URLs:

- `https://spaces.ac.cn/archives/11777`
- `https://spaces.ac.cn/archives/11782`
- `https://spaces.ac.cn/archives/11784`
- `https://spaces.ac.cn/archives/11787`
- `https://spaces.ac.cn/archives/11804`

Validation report:

```json
{
  "content_completeness_rate": 0.8,
  "formulas_valid": true,
  "images_valid": true,
  "issues": [
    "https://spaces.ac.cn/archives/11787: content shorter than 300 characters"
  ],
  "title_presence_rate": 1.0,
  "total_available": 5,
  "total_checked": 5
}
```

### Content Fidelity Gate

Result: FAIL

Evidence:

| URL | Title | Content length | Content fidelity |
|---|---|---:|---|
| `https://spaces.ac.cn/archives/11777` | `流形上的最速下降：6. Muon + 双旋转` | 12128 | PASS |
| `https://spaces.ac.cn/archives/11782` | `MoE环游记：9、门控归一化之争` | 9952 | PASS |
| `https://spaces.ac.cn/archives/11784` | `强制间隔投影（Margin-Enforcing Projection）` | 7123 | PASS |
| `https://spaces.ac.cn/archives/11787` | `矩阵函数近似中的暴力美学` | 38 | FAIL |
| `https://spaces.ac.cn/archives/11804` | `让炼丹更科学一些（七）：步长调度与权重平均` | 11118 | PASS |

Forbidden content checks:

| Check | Result |
|---|---|
| Sidebar/recent-comment content absent | PASS |
| Share script absent | PASS |
| Comment area absent | PASS |
| Navigation noise absent for 4/5; one article contains related-content navigation phrase | RISK |

Interpretation:

- M1.1 fixed the previous sidebar/comment/script contamination for the successful article-body parses.
- However, one imported article was accepted into storage with only title-level content.
- This is an imported-data quality failure, not a simple browser timeout.

### Formula Validity Gate

Result: PASS

| Check | Result |
|---|---|
| `formulas_valid=true` | PASS |
| MathJax source preserved | true |
| Delimiter balanced | true |
| Inline delimiter counts even | true |
| Block delimiter counts even | true |

Formula delimiter counts in fresh live sample:

| URL | `$` count | `$$` count |
|---|---:|---:|
| `https://spaces.ac.cn/archives/11777` | 140 | 16 |
| `https://spaces.ac.cn/archives/11782` | 140 | 0 |
| `https://spaces.ac.cn/archives/11784` | 158 | 0 |
| `https://spaces.ac.cn/archives/11787` | 0 | 0 |
| `https://spaces.ac.cn/archives/11804` | 144 | 0 |

### PDF Export

Evidence source:

- `docs/M1_PDF_EXPORT_EVALUATION.md`

Result:

| Metric | Value |
|---|---:|
| articles tested | 5 |
| PDF exports succeeded | 5 |
| PDF exports failed | 0 |
| PDF success rate | 100% |

PDF export status:

- PASS as independent export capability.
- Not connected to source sync or M2.

### Browser Transient Failure Assessment

This re-run had:

- browser discovered articles: 5
- browser imported articles: 5
- browser fetch failures: 0

No timeout or 403 occurred in this run.

Decision rule:

- Single article timeout or one-off 403 can be a non-blocking risk if bounded retry and failure logging are active and enough valid articles remain for content validation.
- This run did not produce a browser transient failure. It produced one invalid imported content record, which is a freeze blocker.

### Homepage Browser Probe Decision

File checked:

- `backend/tests/test_browser_access.py`

Decision:

- The file is not present in the current worktree.
- It was previously treated as a temporary homepage `403` diagnostic probe, not a long-term regression test.
- No action is required in this re-run.

## 6. Known Risks

1. RSS coverage
   - RSS is valid for recent discovery but may not represent the full Scientific Spaces historical archive.

2. Browser runtime dependency
   - Live source sync and PDF export depend on Playwright Chromium availability.

3. External site changes
   - Scientific Spaces markup and access behavior can change without project control.

4. Content extraction completeness
   - One fresh live imported article produced only title-level content.
   - The pipeline needs an M1.x rule to reject or retry invalid content before storage.

5. Related-content/navigation noise
   - Fresh checks found one related-content navigation phrase in an imported article.
   - This is secondary to the content-length blocker but should be considered in the next revision.

6. Historical ADR drift
   - `ADR/0003-m1-live-source-access-blocker.md` still records the original homepage access blocker as `Blocking`.
   - Later RSS/browser implementation resolved project-state verification, but the ADR has not been superseded by a new ADR.

## 7. M2 Readiness

B: Need additional M1 work

Reason:

- RSS discovery works.
- Browser access worked for 5/5 articles in this re-run.
- Storage idempotency and Article schema are stable.
- Formula validity passed.
- PDF export remains ready as an independent capability.
- Content fidelity did not pass for all imported articles because `https://spaces.ac.cn/archives/11787` was stored with only title-level content.

M2 Scientific Reader should not consume this source output as frozen input until an explicit M1.x revision task prevents invalid-content imports or retries invalid article parses.

## 8. Post-freeze Change Rule

The intended freeze governance rule remains:

- After M1 freeze passes, any M1 implementation change must be created as an `M1.x revision task`.
- Frozen M1 code must not be directly modified from M2 or later milestone work.

Because this freeze re-run did not pass, `M1 Freeze Passed` is not added to project state.
