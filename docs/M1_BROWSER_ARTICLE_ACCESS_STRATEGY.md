# M1 Browser Article Access Strategy

## Summary

This document evaluates whether browser-based direct access to known Scientific Spaces article URLs can be considered as an M1 Source Pipeline access strategy candidate.

Article access feasibility: PASS

Strategy recommendation:

Browser article access can be considered as a candidate strategy for known, approved article URLs only. It does not solve URL discovery, and it should not update M1 Verification or project state without a separate human-approved strategy change.

Conclusion:

A: Browser article access can be considered for M1 strategy

## Source Evidence Reviewed

- `docs/M1_ARTICLE_BROWSER_ACCESS_EVALUATION.md`
- `docs/M1_LIVE_ACCESS_STRATEGY.md`
- `docs/M1_VERIFICATION_REPORT.md`
- `ADR/0003-m1-live-source-access-blocker.md`

Relevant constraints and prior evidence:

- Homepage access remains blocked.
- Archive discovery access remains blocked.
- Site search is not a compliant source because `/search/` is disallowed by the observed robots policy.
- The non-browser downloader path still returns `403` for live source access.
- Prior browser article evaluation showed `https://spaces.ac.cn/archives/6508` can return `200` with content and MathJax available.

## Scope

- Browser: Playwright Chromium.
- Known article URL candidates tested in this strategy pass: `5`.
- URL source: existing local project context only; no homepage, archive, search, crawler, or discovery crawl was used.
- HTML, PDF, images, attachments, and article正文 were not saved.
- Page metrics were computed in-browser and recorded only as diagnostic metadata.
- No crawler, verification, or project-state files were modified.
- No M2-M7 functionality was implemented.

## Environment

- OS: `Linux-7.0.0-27-generic-x86_64-with-glibc2.43`
- Python via `uv`: `3.11.15`
- Playwright version: `1.61.0`
- Browser: Chromium `149.0.7827.55`

## Probe Policy

Two browser probe modes were used:

1. Resource-conservative browser mode:
   - Playwright Chromium with image, media, font, PDF, archive, and common image extension requests aborted.
   - Purpose: reduce non-content resource access while checking article HTML availability.
2. Normal browser recheck:
   - Playwright Chromium without route-level resource aborts.
   - Purpose: check URLs that failed or behaved inconsistently in resource-conservative mode.

No response body, full HTML, article正文, image, PDF, or attachment was written to disk.

## Known Article URL Results

| URL | Status | Title | Content Availability | MathJax Availability | Notes |
|---|---:|---|---|---|---|
| `https://spaces.ac.cn/archives/6508` | `200` in prior normal browser evidence; `403` in this resource-conservative pass; `200` in normal recheck | `科学空间浏览指南（FAQ） - 科学空间\|Scientific Spaces` | PASS in prior evidence; FAIL in current recheck | PASS in prior evidence; FAIL in current recheck | Reachable through browser, but behavior varied by run/mode. |
| `https://spaces.ac.cn/archives/100` | `200` | `400年前的今天，望远镜诞生了 - 科学空间\|Scientific Spaces` | PASS | PASS | Current resource-conservative browser pass. |
| `https://spaces.ac.cn/archives/101` | `200` | `祝大家七夕快乐！ - 科学空间\|Scientific Spaces` | PASS | PASS | Current resource-conservative browser pass. |
| `https://spaces.ac.cn/archives/102` | `200` | `【NASA每日一图】经典的猎户座星云 - 科学空间\|Scientific Spaces` | PASS | PASS | Current resource-conservative browser pass. |
| `https://spaces.ac.cn/archives/500` | `404` in normal recheck; timeout in resource-conservative pass | `页面没找到 - 科学空间\|Scientific Spaces` | FAIL | PASS in normal recheck page shell | Not a usable article URL in this sample. |

## Feasibility Assessment

Article access feasibility: PASS

Reason:

- Three known article URLs returned `200` and showed content availability plus MathJax availability in the current strategy pass.
- One previously validated known article URL, `https://spaces.ac.cn/archives/6508`, has prior browser evidence of `200`, content availability, and MathJax availability.
- One sampled URL was not usable as an article source.

Important limitation:

- Browser article access is not equivalent to source discovery. The project still needs an approved way to obtain known article URLs.
- The `6508` result varied across probe modes/runs, so a production strategy would need explicit browser wait rules, per-URL validation, retry limits, and low-frequency access discipline.

## Strategy Recommendation

Browser article access should be treated as a candidate M1 source access strategy, not as an accepted replacement for the current pipeline.

Recommended strategy boundary:

1. Only use approved known article URLs.
2. Do not use homepage, archive, or site search discovery until a compliant discovery strategy is approved.
3. Use Playwright Chromium only when non-browser HTTP access remains blocked.
4. Validate each article with explicit checks:
   - HTTP status is `2xx`.
   - title is present.
   - content availability passes an in-browser metric check.
   - MathJax or math-rendering support is detected when expected.
5. Do not save raw HTML, article正文, images, PDFs, or attachments unless a separate source policy explicitly approves it.
6. Keep access low-frequency and bounded.
7. Do not update M1 Verification until this strategy is reviewed, documented as accepted, implemented through a separate task, and verified end to end.

## Conclusion

A: Browser article access can be considered for M1 strategy

This conclusion does not unblock M1 Verification by itself. It only establishes that browser-based access to known article URLs is a viable candidate for human review and possible future strategy update.
