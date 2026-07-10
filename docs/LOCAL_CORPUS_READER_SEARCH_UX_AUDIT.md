# Local Corpus Reader and Search UX Audit

## Current Status

- P2-002 Local Corpus Reader/Search UX Audit: PASS
- P2-001 prerequisite commit: `83cb42902e9471e1eecac89c834b1b21fd0716a9`
- P2-001 push CI: PASS ([run 29063931865](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29063931865))
- Recommendation: A: Ready for P2-003 Knowledge Graph Scaling Plan

This audit reads the existing local Article store and RAG index. It did not crawl Scientific Spaces, fetch Article HTML, rebuild the corpus, generate PDFs, or commit runtime data.

## Input Corpus

| Check | Result |
|---|---:|
| Article store | `.local_data/scientific_spaces/corpus/pilot/article_store/articles.json` |
| Article count | 1311 |
| Unique URL count | 1311 |
| Missing content count | 0 |
| Minimum content length | 1074 characters |
| Maximum content length | 69679 characters |
| Metadata keys | `date`, `category`, `references`, `images` |
| Articles with images | 1311 |
| Image metadata entries | 4708 |
| Articles with references | 0 |
| RAG indexed articles | 1311 |
| RAG chunks | 5547 |

The Reader is configured with:

```bash
SCIENTIFIC_SPACES_ARTICLE_STORE=.local_data/scientific_spaces/corpus/pilot/article_store/articles.json
```

`SCIENTIFIC_SPACES_ARTICLES_FILE` remains the legacy override and takes precedence. Reader/API code does not read `article_list.json`, the Markdown materialization, PDF output, or the FAISS index as Article body storage.

A full-corpus quality pass checked all 1311 stored Articles:

| Metric | Result |
|---|---:|
| title_presence_rate | 1.0 |
| content_completeness_rate | 1.0 |
| images_valid | true |
| formulas_valid | true |
| validation issues | `[]` |

## Article API Audit

### List

`GET /articles` now supports:

- `page`, default `1`, minimum `1`
- `page_size`, default `20`, range `1..100`
- `q`, title/content substring search
- `category`, case-insensitive exact metadata match
- `sort`: `date_desc`, `archive_desc`, `title_asc`, or `relevance`

The response includes `items`, `total`, `query`, `category`, `sort`, `page`, `page_size`, `total_pages`, `has_next`, and `has_previous`. List items include `id`, `title`, `url`, `metadata`, and `content_preview`; they never include full `content`.

Default ordering is valid date descending with archive ID and Article ID fallbacks. A non-empty query defaults to relevance ordering, placing title matches ahead of content-only matches and then applying date/archive fallbacks. No year-coverage conclusion is inferred from the date field.

### Pagination

| Request | Status | Total | Returned | Page state |
|---|---:|---:|---:|---|
| `page=1&page_size=20` | 200 | 1311 | 20 | first page, next=true |
| `page=25&page_size=20` | 200 | 1311 | 20 | middle page, previous/next=true |
| `page=66&page_size=20` | 200 | 1311 | 11 | final page, next=false |
| `page=67&page_size=20` | 200 | 1311 | 0 | beyond range, next=false |
| `page_size=100` | 200 | fixture total | bounded | accepted maximum |
| `page=0` | 422 | - | - | rejected |
| `page_size=0` | 422 | - | - | rejected |
| `page_size=101` | 422 | - | - | rejected |

### Search and Detail

- Search uses Unicode substring matching with `casefold()`. It does not use an English tokenizer, embedding, FAISS, LLM, or source fetch.
- Duplicate URLs are collapsed before filtering and pagination; the last stored record wins, matching Article upsert semantics.
- The lightweight loader caches parsed records by resolved path, modification time, and file size and reloads when the store changes.
- `GET /articles/{id}` returns the complete stored `content` and metadata.
- Missing detail returns `404 Article not found`.
- A missing Article store returns an empty paginated response instead of crashing.

The `archives/11787` detail check returned Article ID `fa0f240c54f24dd6`, title `矩阵函数近似中的暴力美学`, content length `18043`, all four metadata keys, 3 images, and 0 references.

## Search Quality

Title/content counts overlap when a term appears in both fields. Latency is five warm/local TestClient repetitions in milliseconds.

| Query | Results | Title matches | Content matches | Median | p95 | Top results |
|---|---:|---:|---:|---:|---:|---|
| Transformer | 116 | 35 | 116 | 35.970 | 107.312 | Transformer升级之路 21; 20; 19 |
| Attention | 126 | 16 | 126 | 37.024 | 37.555 | Attention Residuals; 低精度Attention; 时空之章 |
| Muon | 43 | 15 | 43 | 36.490 | 37.528 | 流形上的最速下降 6; 官方版Muon; 流式幂迭代 5 |
| Adam | 113 | 5 | 113 | 37.649 | 40.045 | Adam最优超参数; AdamW渐近估计下; 上 |
| 扩散模型 | 45 | 31 | 45 | 34.820 | 35.368 | 扩散模型漫谈 31; 30; 29 |
| 矩阵 | 283 | 30 | 283 | 39.380 | 40.209 | 矩阵函数近似; 奇异值熵; 谱范数 |
| 变分法 | 22 | 2 | 22 | 36.918 | 37.533 | 借助变分法; 变分法技巧; 炼丹更科学 6 |
| 微分方程 | 113 | 10 | 113 | 37.835 | 38.228 | 特征线法; 随机微分方程; ARXIV分布 |
| 天文 | 172 | 16 | 172 | 37.027 | 39.699 | Lamost夏令营; 北大夏令营; 天文奥赛 |
| BERT | 139 | 26 | 139 | 38.982 | 39.620 | BERT-whitening; bert4keras; CoSENT |
| GAN | 96 | 24 | 96 | 39.592 | 39.797 | IGN; ReFlow到WGAN-GP; 扩散ODE的GAN |
| VAE | 47 | 11 | 47 | 39.432 | 39.814 | FSQ/VQ-VAE; DDPM/自回归VAE; UniVAE |
| 概率 | 266 | 16 | 266 | 40.261 | 40.788 | 概率不等式; 概率空间; Softmax替代品 |
| 费曼 | 43 | 19 | 43 | 39.513 | 40.858 | 费曼100年; 费曼迷; 费曼与朗道 |
| 不存在的关键词 | 0 | 0 | 0 | 33.569 | 34.360 | empty |

All 14 supported smoke queries returned results. Relevance ordering put title matches first. The unsupported query returned an empty page with status 200 and no synthetic result.

## Frontend Reader Audit

### Routes and States

| Route | Result |
|---|---|
| `/` | Dashboard loads five recent Articles but uses API `total=1311` for the corpus count. Explicit loading/error/empty behavior is present. |
| `/articles` | Loads 20 summaries, displays total/range/page state, supports search, Previous/Next pagination, and loading/error/empty states. |
| `/articles/[id]` | Loads full content only for the selected Article, records basic reading history, renders metadata, and has loading/missing-Article error states. |

Long titles and metadata use wrapping constraints. The shared navigation wraps on narrow screens. Desktop and 390 px mobile checks found no page-level horizontal overflow; code and large formulas scroll within their own containers.

Reading history remains localStorage-only and capped by the existing M2 helper. It stores only `id`, `title`, `url`, and `last_read_at`; it does not cache Article.content.

### Markdown and Large Articles

The detail view renders GFM Markdown, headings, safe external links, images with fallback UI, code blocks, and KaTeX formulas. Relative Article links are resolved against `https://spaces.ac.cn` and external links use `target=_blank` plus `noopener noreferrer`.

Display-only normalization handles preserved MathJax forms (`\(...\)`, `\[...\]`, legacy `\newcommand{name}`, and inline/multiline `$$...$$`). The stored Article.content is not modified.

| Article ID | Stored length | Render check | KaTeX errors | Overflow |
|---|---:|---|---:|---|
| `03dfe77de35ec4ec` | 69679 | longest Article, 11 headings, 123 KaTeX nodes, 7 image metadata entries | 0 | false |
| `69e708f3cca249cf` | long | Attention Article, 13 headings, 66 KaTeX nodes, 2 code blocks | 0 | false |
| `fa0f240c54f24dd6` | 18043 | archives/11787, 9 headings, 138 KaTeX nodes, 1 code block | 0 | false |
| `29218a444f29cfbe` | 1234 | old short Article, 2 image metadata entries | 0 | false |
| `892568a3c8be41d5` | 1808 | older Chinese Article, 3 image metadata entries | 0 | false |

Five rapid Article-detail loads produced 15/15 successful learning reads and 5/5 successful session writes after Reader calls were ordered as concurrent reads followed by the JSON write. This avoids a read/write race without changing the frozen learning backend.

## Citation Navigation

A full-corpus in-memory RAG index smoke returned five Article chunk sources for `69e708f3cca249cf` (`《Attention is All You Need》浅读（简介+代码）`). Each source displayed:

- source title matching the Article store;
- section and chunk index;
- `Open local article` -> `/articles/69e708f3cca249cf`;
- `Open original source` -> `https://spaces.ac.cn/archives/4765`.

The local citation click requested the local Next route and `GET /articles/69e708f3cca249cf`. Network inspection found no request to `/archives/4765`; no Article page was re-fetched. Graph/Zotero/learning sources do not receive false local Article links unless they carry an explicit `metadata.article_id`.

## Performance Baseline

Environment: Linux `7.0.0-27-generic` x86_64, backend Python `3.11.15`, Node `22.22.1`, npm `11.4.2`. Results are local loopback measurements, not cross-device SLAs.

### Backend API

Twenty warm TestClient repetitions; times are milliseconds.

| Check | Bytes | min | mean | median | p95 | max |
|---|---:|---:|---:|---:|---:|---:|
| list page 1 | 17618 | 2.640 | 3.034 | 3.068 | 3.369 | 3.437 |
| list middle page | 18745 | 2.365 | 2.679 | 2.658 | 2.975 | 3.081 |
| title search | 19422 | 31.580 | 32.337 | 32.366 | 33.059 | 33.201 |
| content search | 20467 | 34.377 | 35.472 | 35.198 | 36.944 | 37.143 |
| no-result search | 173 | 31.599 | 32.668 | 32.682 | 33.306 | 33.750 |
| Article detail | 24477 | 0.832 | 1.152 | 1.039 | 2.053 | 2.102 |

The API has no seconds-scale blocking at 1311 Articles. Search is a cached in-memory linear substring scan; it remains acceptable at this corpus size.

### Frontend

Ten warm production-server HTTP repetitions:

| Route | Bytes | mean | median | p95 |
|---|---:|---:|---:|---:|
| `/` | 7587 | 1.930 ms | 1.707 ms | 3.720 ms |
| `/articles` | 8756 | 1.626 ms | 1.435 ms | 2.957 ms |
| `/articles/fa0f240c54f24dd6` shell | 8974 | 6.803 ms | 7.372 ms | 9.355 ms |

Playwright end-to-end interaction baseline: search `91 ms`, next page `31 ms`, and local Article navigation until reader content visible `244 ms`. Production build passed. No route loaded all 1311 full bodies.

## Fixes Applied

Backend:

- Added bounded pagination, category filtering, deterministic sorting, relevance ordering, and response metadata.
- Added a modification-aware lightweight Article cache and duplicate URL collapse.
- Added the full-corpus `SCIENTIFIC_SPACES_ARTICLE_STORE` configuration alias.
- Expanded API regression coverage for pagination boundaries, multilingual search, detail content, cache reload, duplicate URLs, and missing storage.

Frontend:

- Added list totals, page/range state, Previous/Next controls, and explicit loading/error/empty states.
- Added Dashboard loading/error behavior and paginated total handling.
- Added GFM/KaTeX rendering, legacy MathJax display normalization, safe links, image fallback, metadata lists, and long-content layout constraints.
- Added internal Tutor citation links while retaining canonical source links.
- Made the shared navigation and long titles responsive.
- Sequenced Reader learning reads before the session write to avoid local JSON read/write contention.

Configuration and documentation:

- Updated `.env.example` and README with the ignored full-corpus Reader path and API bounds.

## Artifact and Privacy Policy

- No corpus, Markdown library, Article JSON, RAG index, FAISS file, embedding cache, PDF, downloaded HTML, image, trace, profile, API key, or runtime store is committed.
- `.local_data/`, `.next/`, `node_modules/`, evaluation outputs, and Playwright artifacts remain ignored or were removed after testing.
- Reader/API behavior uses the local Article store and does not invoke crawler, browser acquisition, parser, converter, or sync code.
- Browser reading history contains summaries only. Full Article.content is not written to localStorage.
- Existing external image URLs may be requested by the browser when an Article is rendered; Article HTML pages are not fetched.

## Regression Evidence

| Check | Result |
|---|---|
| P2-001 GitHub Actions Backend pytest | PASS |
| P2-001 GitHub Actions Frontend build | PASS |
| P2-001 push Docker compose smoke | skipped by existing push policy |
| `uv run --project backend --extra dev pytest -q` | 201 passed, 2 skipped |
| `npm run build` | PASS, 8 routes generated |
| original `run_rag_tutor_eval.py` | PASS, 9 cases, all grounding rates 100% |
| full-corpus RAG evaluation | PASS, hit@10 90.9%, source/refusal schema rates 100%, 0 fabrications/errors |
| full-corpus Article validation | PASS, 1311/1311, formulas valid, no issues |
| backend local corpus runtime smoke | PASS |
| frontend production/Playwright smoke | PASS |

Normal CI remains fixture-only and does not require the ignored 1311-Article store.

## Risks

- Content search is linear over cached Article text. It is fast at 1311 Articles but should be profiled again if the corpus grows substantially before introducing a separate search index.
- Dates are currently valid ISO values for all 1311 records, but this audit does not claim complete or authoritative historical year coverage.
- One category value is URL-like source metadata. The Reader preserves it rather than inventing a corrected category.
- All current reference arrays are empty, so non-empty reference presentation is covered defensively in code but not by full-corpus runtime evidence.
- Article images are remote dependencies and may fail as external assets change; the UI provides fallback text.
- KaTeX compatibility can vary for future MathJax macros. The current five-Article smoke, including the longest Article and archives/11787, had zero rendering errors.
- The Article Detail client bundle is larger because of Markdown/KaTeX dependencies, and very large Articles still incur client rendering cost.
- Local JSON stores remain unsuitable for multi-user concurrency. Reader request ordering removes the observed local read/write race but does not change that backend limitation.
- The full-corpus path is local configuration and must be supplied in each runtime environment; CI intentionally uses fixtures.

## Recommendation

A: Ready for P2-003 Knowledge Graph Scaling Plan

Reader/Search now uses the complete local corpus with bounded transport, stable search and pagination, full detail content, grounded local citation navigation, and acceptable local performance. P2-003 should remain a separate task and must not back-edit the frozen source corpus.
