# M1 Final Freeze Report

## Current Status

| Item | Status | Evidence |
|---|---|---|
| M1 Source Pipeline | PASS | RSS discovery, browser access, parser, converter, storage, validation, and sync modules are present. |
| M1 Verification | PASS | `docs/00_PROJECT_STATE.md` records `M1 Verification Passed`. |
| M1 PDF Export | PASS | `docs/M1_PDF_EXPORT_EVALUATION.md` records 5/5 live PDF exports. |
| M1.3 Browser Acquisition Quality Revision | PASS | `docs/M1_BROWSER_ACCESS_QUALITY_REVISION.md` records source HTML body-gate and sync import-quality gate. |
| M1 Final Freeze Re-run | PASS | Fresh live sync imported and validated 5 real articles with no validation issues. |
| M2 Readiness | A: Ready for M2 | M1 output is stable enough for M2 Scientific Reader input. |

This freeze re-run is an acceptance handoff only. It does not implement M2 Reader, Search, RAG, Learning System, or M3-M7 behavior.

## Architecture Freeze

### Discovery

Frozen strategy:

- RSS Discovery

Input:

- `https://spaces.ac.cn/feed`

Output:

- Article URLs matching `https://spaces.ac.cn/archives/{numeric_id}`

Implementation:

- `backend/app/crawler/rss.py`
- `discover_rss_article_urls(feed_url=DEFAULT_FEED_URL, fetch_xml=default_fetch_xml, max_items=None) -> list[str]`

### Access

Frozen strategy:

- Playwright Browser Access

Input:

- Article URL

Output:

- `BrowserFetchResult(url, html, title, status, mathjax_available)`

Implementation:

- `backend/app/crawler/browser.py`
- `BrowserArticleFetcher.fetch(url) -> BrowserFetchResult`
- `BrowserArticleFetcher.fetch_many(urls) -> list[BrowserFetchResult]`

M1.3 quality gate:

- Browser fetch waits for an approved article body selector.
- Browser fetch rejects title-only or shell HTML without an article body.
- Sync performs a parsed-article import-quality check before storage.

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

Frozen independent capability:

- PDF Export

Implementation:

- `backend/app/export/pdf.py`
- `ArticlePdfExporter.export(url, output_path) -> PdfExportResult`
- `validate_pdf_file(path, url="") -> int`

Boundary:

- PDF export is not wired into `python -m app.sync`.
- PDF export is not part of M2 Reader or RAG.

## Data Contract Freeze

Frozen Article schema:

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
| Content fidelity for imported articles | PASS |
| Formula validity | PASS |

Reference preservation note:

- The fresh sample exposes the `references` metadata field for every article.
- The sampled articles did not contain extracted explicit reference entries, so `references_count=0` is accepted as preservation of source metadata shape, not field loss.
- Image metadata was preserved with 2-3 images per sampled article.

## Interface Freeze

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

## Test Evidence

### Ordinary Pytest

Command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
23 passed, 2 skipped in 0.22s
```

### M1 Live Sync Re-run

First attempt:

- Result: RSS discovery failed with a TLS handshake timeout while reading `https://spaces.ac.cn/feed`.
- Classification: transient external network risk.
- Decision: non-blocking because the delayed low-frequency retry completed successfully and produced enough live evidence for content-quality validation.

Successful retry command:

```bash
SCIENTIFIC_SPACES_DATA_DIR=/tmp/scientific-spaces-m1-final-freeze-rerun \
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
| failed count | 0 |

Imported article URLs:

- `https://spaces.ac.cn/archives/11777`
- `https://spaces.ac.cn/archives/11782`
- `https://spaces.ac.cn/archives/11784`
- `https://spaces.ac.cn/archives/11787`
- `https://spaces.ac.cn/archives/11804`

Validation report:

```json
{
  "content_completeness_rate": 1.0,
  "formulas_valid": true,
  "images_valid": true,
  "issues": [],
  "title_presence_rate": 1.0,
  "total_available": 5,
  "total_checked": 5
}
```

### Content Fidelity

Result: PASS

| URL | Title | Content length | Images | References | Metadata keys | Fidelity |
|---|---|---:|---:|---:|---|---|
| `https://spaces.ac.cn/archives/11777` | `流形上的最速下降：6. Muon + 双旋转` | 14260 | 2 | 0 | `category,date,images,references` | PASS |
| `https://spaces.ac.cn/archives/11782` | `MoE环游记：9、门控归一化之争` | 12025 | 2 | 0 | `category,date,images,references` | PASS |
| `https://spaces.ac.cn/archives/11784` | `强制间隔投影（Margin-Enforcing Projection）` | 8963 | 2 | 0 | `category,date,images,references` | PASS |
| `https://spaces.ac.cn/archives/11787` | `矩阵函数近似中的暴力美学` | 19933 | 3 | 0 | `category,date,images,references` | PASS |
| `https://spaces.ac.cn/archives/11804` | `让炼丹更科学一些（七）：步长调度与权重平均` | 19140 | 2 | 0 | `category,date,images,references` | PASS |

Forbidden content checks:

| Check | Result |
|---|---|
| Content acquired from article body container | PASS |
| Sidebar/recent-comment content absent | PASS |
| Share script text absent | PASS |
| Comment area absent | PASS |
| Page title/site-title marker absent | PASS |
| Navigation residue absent | PASS |

Navigation note:

- `https://spaces.ac.cn/archives/11804` contains the phrase `上一篇` inside the article's own discussion of a previous post.
- This is article正文 context, not page navigation residue.

### Formula Validity

Result: PASS

| Check | Result |
|---|---|
| `formulas_valid=true` | PASS |
| MathJax source preserved | true |
| Delimiter balanced | true |
| Inline delimiter counts even | true |
| Block delimiter counts even | true |

Formula delimiter counts:

| URL | `$` count | `$$` count | Balanced |
|---|---:|---:|---|
| `https://spaces.ac.cn/archives/11777` | 148 | 24 | true |
| `https://spaces.ac.cn/archives/11782` | 186 | 22 | true |
| `https://spaces.ac.cn/archives/11784` | 174 | 0 | true |
| `https://spaces.ac.cn/archives/11787` | 276 | 0 | true |
| `https://spaces.ac.cn/archives/11804` | 224 | 44 | true |

### 11787 Blocker Status

Previous blocker:

- `https://spaces.ac.cn/archives/11787` was previously imported with only title-level content.
- Previous failure mode: HTTP `200` and non-empty HTML were accepted even when the article body container was absent.

Current result:

| Field | Value |
|---|---|
| URL | `https://spaces.ac.cn/archives/11787` |
| Title | `矩阵函数近似中的暴力美学` |
| Content length | 19933 |
| Metadata keys | `category,date,images,references` |
| Images | 3 |
| References | 0 |
| Formula delimiters balanced | true |
| Validation issues | `[]` |
| Status | Resolved |

Decision:

- The `11787` blocker is resolved.

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
| MathJax status | 5/5 PASS |

PDF export status:

- PASS as independent export capability.
- Not connected to source sync or M2.

### Browser Transient Risk Classification

Observed in this freeze re-run:

- One RSS feed TLS handshake timeout occurred before article discovery.
- A delayed low-frequency retry completed successfully.
- Successful retry imported and validated 5/5 articles.
- Browser article fetch failures on the successful run: 0.

Classification:

- Non-blocking risk.

Reason:

- The failure was transient and external to parser/storage/content quality.
- The pipeline has bounded retry and failure logging for article browser access.
- The successful retry produced enough live evidence to verify content fidelity, formulas, storage, validation, and `11787`.

Blocking threshold:

- If RSS discovery cannot be completed after a reasonable low-frequency retry, or if browser failures prevent content-quality validation, the freeze must be blocked.

### Homepage Browser Probe Decision

File checked:

- `backend/tests/test_browser_access.py`

Decision:

- The file is not present in the current worktree.
- It was previously a temporary homepage `403` diagnostic probe, not part of the frozen RSS/browser article strategy.
- No file action was needed.

## Known Risks

1. RSS coverage scope
   - RSS is stable for recent discovery but should not be treated as full historical archive coverage.

2. Browser runtime dependency
   - Live source sync and PDF export depend on Playwright Chromium availability.

3. Transient browser/source access fluctuation
   - RSS or article access can intermittently time out or fail.
   - Mitigation: bounded retry, failure logging, and quality gates that avoid storing invalid articles.

4. External site changes
   - Scientific Spaces markup and access behavior can change outside project control.

5. Playwright maintenance cost
   - Browser-based acquisition adds runtime and CI maintenance overhead.

6. ADR follow-up
   - `ADR/0003-m1-live-source-access-blocker.md` still records the original homepage access blocker as `Blocking`.
   - The implemented RSS/browser strategy supersedes the original blocked homepage/archive path for M1 operation, but ADR status has not been updated by this freeze gate.

## M2 Readiness

A: Ready for M2

Reason:

- RSS discovery works for the M1 source boundary.
- Browser access now enforces an article-body acquisition gate.
- Parser and converter preserve article body, images metadata, and math delimiters for the fresh live sample.
- Storage upsert produced no duplicates.
- Validation passed with `issues=[]`.
- The `11787` blocker is resolved.
- PDF export remains a separate PASS capability.

M2 Scientific Reader can use the frozen M1 Article output as input, while keeping M1 implementation changes behind explicit M1.x revision tasks.

## Post-freeze Change Rule

Freeze governance rule:

- After M1 freeze passes, any M1 implementation change must be created as an `M1.x revision task`.
- Frozen M1 code must not be directly modified from M2 or later milestone work.
