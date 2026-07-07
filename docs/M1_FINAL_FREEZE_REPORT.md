# M1 Final Freeze Report

## 1. Current Status

| Item | Status | Evidence |
|---|---|---|
| M1 Source Pipeline | PASS | M1 implementation modules are present and ordinary pytest passes. |
| M1 Verification | PASS in project state | `docs/00_PROJECT_STATE.md` records `M1 Verification Passed`. |
| M1 PDF Export | PASS | `docs/M1_PDF_EXPORT_EVALUATION.md` records 5/5 live PDF exports. |
| M1 Final Freeze Gate | BLOCKED | Fresh live sync evidence shows stored `content` is not reliably article body content. |

This report is an audit and handoff gate. It does not implement M2 Reader, Search, RAG, Learning System, or any M1 implementation change.

## 2. Architecture Freeze

The following M1 architecture is the current implementation baseline. It is documented here for freeze review, but the final handoff is not approved because of the live content extraction risk in Section 5.

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

The Article storage schema matches the M1 milestone and data model documents:

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

Implementation evidence:

- `StoredArticle` in `backend/app/storage/article_store.py` defines `id`, `title`, `url`, `content`, and `metadata`.
- `ArticleStore.upsert()` derives `metadata.date`, `metadata.category`, `metadata.references`, and `metadata.images`.

Data contract status:

- Schema shape: PASS
- Metadata keys: PASS in fresh live sample
- Article body semantic quality: BLOCKED by fresh live sample evidence

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
- Interfaces are not approved as final M2 handoff until M1 content extraction is revised through an M1.x revision task.

## 5. Test Evidence

### Ordinary Pytest

Command:

```bash
uv run --project backend --extra dev pytest -q
```

Result:

```text
17 passed, 3 skipped in 0.22s
```

### M1 Live Sync

Command:

```bash
SCIENTIFIC_SPACES_DATA_DIR=/tmp/scientific-spaces-m1-freeze-live \
uv run --project backend python -m app.sync --max-articles 5
```

First run:

```text
Scientific Spaces sync completed: discovered=5, imported=5, failed=0, validated=5
```

Repeated run with the same data directory:

```text
Scientific Spaces sync completed: discovered=5, imported=5, failed=0, validated=5
```

Stored article metrics after repeated sync:

| Metric | Value |
|---|---:|
| article count | 5 |
| unique URL count | 5 |
| duplicate count | 0 |

Validation result after repeated sync:

```json
{
  "total_available": 5,
  "total_checked": 5,
  "title_presence_rate": 1.0,
  "content_completeness_rate": 1.0,
  "images_valid": true,
  "formulas_valid": false,
  "issues": [
    "https://spaces.ac.cn/archives/11777: formula delimiters look unbalanced",
    "https://spaces.ac.cn/archives/11782: formula delimiters look unbalanced",
    "https://spaces.ac.cn/archives/11784: formula delimiters look unbalanced",
    "https://spaces.ac.cn/archives/11787: formula delimiters look unbalanced",
    "https://spaces.ac.cn/archives/11804: formula delimiters look unbalanced"
  ]
}
```

Additional local inspection of the temporary live store showed the stored `content` starts with recent comment/sidebar entries rather than the article body for the sampled URLs. No article正文 or HTML was committed.

Freeze interpretation:

- Discovery: PASS
- Browser access: PASS
- Storage idempotency: PASS
- Schema shape: PASS
- Validation title/content/image thresholds: PASS
- Formula validation: FAIL
- Article body extraction quality: BLOCKING RISK

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

### Untracked Browser Probe Decision

File checked:

- `backend/tests/test_browser_access.py`

Decision:

- Deleted as a temporary diagnostic file.

Reason:

- The file tested browser access to `https://spaces.ac.cn/`, which is the known homepage `403` path.
- Current accepted M1 access strategy uses RSS discovery plus direct article browser access.
- Keeping the probe as a long-term regression test would encode an obsolete negative path and would fail when explicitly run with live browser markers.

## 6. Known Risks

1. RSS coverage
   - RSS is valid for recent discovery but may not represent the full Scientific Spaces historical archive.

2. Browser runtime dependency
   - Live source sync and PDF export depend on Playwright Chromium availability.

3. External site changes
   - Scientific Spaces markup and access behavior can change without project control.

4. Parser selector risk
   - Fresh live evidence indicates the current parser/content root selection can store non-body page content.

5. Formula preservation risk
   - Fresh live validation reported unbalanced formula delimiters for all five sampled articles.

6. Historical ADR drift
   - `ADR/0003-m1-live-source-access-blocker.md` still records the original homepage access blocker as `Blocking`; later RSS/browser implementation resolved project-state verification, but the ADR has not been superseded by a new ADR.

## 7. M2 Readiness

B: Need additional M1 work

Reason:

- M1 infrastructure and source access are operational.
- Article schema and storage idempotency are stable.
- PDF export is operational as an independent capability.
- However, fresh live sync evidence shows stored `content` is not reliable article body content, and formula validation currently fails for the sampled live articles.

M2 Scientific Reader should not consume this source output as frozen input until an explicit M1.x revision task fixes or validates article body extraction quality.

## 8. Post-freeze Change Rule

The intended freeze governance rule is:

- After M1 freeze passes, any M1 implementation change must be created as an `M1.x revision task`.
- Frozen M1 code must not be directly modified from M2 or later milestone work.

Because this freeze gate did not pass, this report records the rule but does not activate `M1 Freeze Passed` in project state.
