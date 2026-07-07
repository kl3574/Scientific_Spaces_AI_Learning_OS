# M1 Article Discovery Strategy Evaluation

## 1. Current Status

- M1 Implementation: PASS
- M1 Verification: BLOCKED
- Remaining blocker: Article URL Discovery

Context:

- The M1 crawler/parser/converter/storage/validation implementation is present and fixture-based pipeline checks passed.
- Default homepage access remains blocked from this environment.
- Official archive access through `https://spaces.ac.cn/content.html` remains blocked.
- Playwright browser access to known article URLs can work, but known URL access does not solve URL discovery by itself.

## 2. Discovery Candidates

### Candidate A: Official Sitemap

Checks:

| URL | HTTP Status | Title | Article URL Found | Compliant | Recommended |
|---|---:|---|---|---|---|
| `https://spaces.ac.cn/robots.txt` | `200` | not applicable | no | yes | no |
| `https://spaces.ac.cn/sitemap.xml` | `404` | `页面没找到 - 科学空间\|Scientific Spaces` | yes, in the 404 page shell sample | no as sitemap | no |

Assessment:

- `robots.txt` is reachable and does not advertise a sitemap in the observed response.
- `sitemap.xml` does not provide a valid sitemap; it returns `404`.
- Although the `404` page shell contained archive-style links in the diagnostic sample, a `404` page is not a reliable or recommended official sitemap source.

Candidate A result:

- Official sitemap discovery: FAIL
- Compliant: no for sitemap discovery
- Recommended: no

### Candidate B: RSS/feed

Checks:

| URL | HTTP Status | Title | Article URL Found | Compliant | Recommended |
|---|---:|---|---|---|---|
| `https://spaces.ac.cn/feed` | `200` | `科学空间\|Scientific Spaces` | yes | yes | yes |
| `https://spaces.ac.cn/rss.xml` | `404` | `页面没找到 - 科学空间\|Scientific Spaces` | yes, in the 404 page shell sample | no as RSS endpoint | no |

Assessment:

- `https://spaces.ac.cn/feed` returns `application/rss+xml; charset=UTF-8`.
- The diagnostic sample contained article archive URLs.
- This is the strongest official discovery candidate observed in this evaluation.
- Scope limitation: RSS/feed is usually a recent-item feed, not guaranteed to be a complete historical article index.

Candidate B result:

- RSS/feed discovery: PASS
- Compliant: yes
- Recommended: yes, as the primary official discovery candidate for recent article URL discovery

### Candidate C: Official Archive/Index

Checks:

| URL | HTTP Status | Title | Article URL Found | Compliant | Recommended |
|---|---:|---|---|---|---|
| `https://spaces.ac.cn/content.html` | `403` | not available | no | no from this environment | no |

Assessment:

- The known official archive/index path remains blocked from this environment.
- No pagination traversal or bulk archive discovery was attempted.
- Prior homepage and Playwright homepage checks also remained blocked.

Candidate C result:

- Official archive/index discovery: FAIL
- Compliant: no usable access path from this environment
- Recommended: no

### Candidate D: Search Engine Discovery

Checks:

| URL / Query | HTTP Status | Title | Article URL Found | Compliant | Recommended |
|---|---:|---|---|---|---|
| `site:spaces.ac.cn/archives Scientific Spaces` | not applicable; external search metadata only | multiple indexed Scientific Spaces article titles | yes | requires approved search API / policy | conditional |

Observed indexed URLs from one low-frequency external search query included:

- `https://spaces.ac.cn/archives/12`
- `https://spaces.ac.cn/archives/1658`
- `https://spaces.ac.cn/archives/3319`
- `https://spaces.ac.cn/archives/11647`
- `https://spaces.ac.cn/archives/6508`
- `https://spaces.ac.cn/archives/11750`
- `https://spaces.ac.cn/archives/11693`

Assessment:

- Search engine discovery can find article URLs without crawling Scientific Spaces directly.
- It is not an official Scientific Spaces source.
- It should not be used in an automated pipeline unless an approved search API and usage policy are documented.
- This evaluation used one search query only and did not perform large-scale search.

Candidate D result:

- Search discovery: PASS as evidence of indexed URL availability
- Compliant: conditional; requires explicit approval of search provider/API policy
- Recommended: no as default M1 strategy; possible fallback only after approval

### Candidate E: Manual Seed URL

Checks:

| URL / Source | HTTP Status | Title | Article URL Found | Compliant | Recommended |
|---|---:|---|---|---|---|
| Existing local known article URL set, including `https://spaces.ac.cn/archives/6508` | not applicable for discovery; article access separately verified by browser probes | known titles available through browser article checks | yes | yes if manually approved | conditional |

Assessment:

- Manual seed URLs are viable as input because browser article access can work for known URLs.
- Manual seed URLs do not solve automated discovery.
- This strategy is reproducible only if the seed list is approved, versioned, and maintained as source metadata.

Candidate E result:

- Manual seed discovery: PASS as a controlled input mechanism
- Compliant: yes if the seed list is manually approved and does not include downloaded article content
- Recommended: conditional fallback if RSS/feed scope is insufficient

## Request Discipline

- Scientific Spaces live HTTP requests in this evaluation: `5`.
- External search queries in this evaluation: `1`.
- No full-site scan was performed.
- No pagination traversal was performed.
- No large-scale search was performed.
- No article HTML, article正文, PDF, image, attachment, or cache data was saved.
- Only diagnostic metadata was written to this report.

## Discovery Feasibility

Discovery feasibility: PASS

Reason:

- The official RSS/feed endpoint `https://spaces.ac.cn/feed` is accessible and exposes article archive URLs.
- Search engine metadata can also discover article URLs, but it requires a separate approved search-provider policy.
- Manual seed URL input is viable as a controlled fallback, but it is not automated official discovery.

## Recommended Strategy

A: Official discovery available

Primary recommendation:

- Use `https://spaces.ac.cn/feed` as the first official discovery candidate for M1 Source Access Strategy Revision.

Required strategy boundaries:

1. Treat RSS/feed as an official but likely recent-item discovery source.
2. Do not assume RSS/feed provides a complete historical corpus unless separately verified and approved.
3. Combine feed-discovered URLs with the already evaluated browser article access strategy only after a separate strategy revision task approves the design.
4. Keep search-engine discovery as an explicitly approved fallback only, not the default source.
5. Keep manual seed URLs as a controlled fallback for known approved articles if feed coverage is insufficient.

## Recommendation

This is worth entering M1 Source Access Strategy Revision.

The recommended next task should not modify M2 or unblock verification directly. It should decide whether to revise M1 source access around:

1. Official RSS/feed URL discovery.
2. Browser-based article access for feed-discovered or manually approved article URLs.
3. Low-frequency validation and no raw-content persistence unless source policy explicitly permits it.

M1 Verification should remain BLOCKED until the revised strategy is formally approved, implemented, and verified end to end.
