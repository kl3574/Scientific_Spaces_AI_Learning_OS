# M1 Source Access Strategy Revision

## Current Status

- M1 Source Pipeline implementation: PASS
- Existing crawler/parser/converter/storage/validation: implemented
- Fixture pipeline: PASS
- M1 Verification: BLOCKED
- Current blocker: live source access path and article URL discovery strategy

This report evaluates a revised M1 access strategy:

```text
RSS Discovery
-> Article URL
-> Playwright Browser Access
-> Existing Parser
-> Article Storage
```

This report does not modify crawler code, verification criteria, project state, or M2-M7 functionality.

## Previous Blocker

The previous default M1 live source path depended on homepage/archive access:

- `https://spaces.ac.cn/`: blocked with `403`
- `https://spaces.ac.cn/content.html`: blocked with `403`
- Playwright homepage access: blocked with `403`

Known article browser access later proved that direct article URLs can sometimes be accessed with Playwright Chromium, but article URL discovery remained unresolved until the RSS/feed evaluation.

## New Evidence

### RSS Discovery Format

| Field | Value |
|---|---|
| Feed URL | `https://spaces.ac.cn/feed` |
| Status | `200 OK` |
| Content-Type | `application/rss+xml; charset=UTF-8` |
| Bytes read for diagnostic parsing | `20358` |
| Items in RSS sample | `10` |
| Article URLs in RSS sample | `10` |
| URL format | `https://spaces.ac.cn/archives/{numeric_id}` |

First RSS items checked:

| URL | Source field | URL format valid |
|---|---|---|
| `https://spaces.ac.cn/archives/11804` | `link` | yes |
| `https://spaces.ac.cn/archives/11787` | `link` | yes |
| `https://spaces.ac.cn/archives/11784` | `link` | yes |
| `https://spaces.ac.cn/archives/11782` | `link` | yes |
| `https://spaces.ac.cn/archives/11777` | `link` | yes |

RSS discovery assessment:

- RSS discovery output is structured and parseable.
- RSS article URLs use a stable numeric archive URL format.
- RSS can replace homepage/archive discovery for recent article URL discovery.
- RSS should not be assumed to provide a complete historical archive without additional policy approval and verification.

### Browser Access Provider Validation

| Field | Value |
|---|---|
| Browser provider | Playwright Chromium |
| Browser version | `Chromium 149.0.7827.55` |
| Playwright version | `1.61.0` |
| Python version | `3.11.15` |
| OS | `Linux-7.0.0-27-generic-x86_64-with-glibc2.43` |
| Article URLs tested | `5` |
| PDF/download handling | Playwright context used `accept_downloads=False`; PDF/archive URL requests were aborted |

Article URL checks:

| URL | HTTP status | Title | HTML obtained | HTML length | Content availability | MathJax availability |
|---|---:|---|---|---:|---|---|
| `https://spaces.ac.cn/archives/11804` | `403` | `让炼丹更科学一些（七）：步长调度与权重平均 - 科学空间\|Scientific Spaces` | yes | `66044` | FAIL | PASS |
| `https://spaces.ac.cn/archives/11787` | timeout | not available | no | not available | FAIL | FAIL |
| `https://spaces.ac.cn/archives/11784` | `200` | `强制间隔投影（Margin-Enforcing Projection） - 科学空间\|Scientific Spaces` | yes | `70442` | PASS | PASS |
| `https://spaces.ac.cn/archives/11782` | `200` | `MoE环游记：9、门控归一化之争 - 科学空间\|Scientific Spaces` | yes | `67378` | PASS | PASS |
| `https://spaces.ac.cn/archives/11777` | `200` | `流形上的最速下降：6. Muon + 双旋转 - 科学空间\|Scientific Spaces` | yes | `66062` | PASS | PASS |

Browser access assessment:

- Browser access can obtain article HTML metadata and MathJax indicators for feed-discovered URLs.
- Three of five feed-discovered URLs passed full browser content checks in this low-frequency sample.
- One URL returned `403` while still exposing title, HTML length, and MathJax signals.
- One URL timed out at navigation commit within the diagnostic timeout.
- A production implementation would need per-URL validation, bounded retries, timeout handling, and failure reporting.

## Proposed Strategy

Use RSS/feed as the discovery layer and Playwright Chromium as the browser access layer.

Proposed pipeline:

1. RSS Discovery
   - Fetch `https://spaces.ac.cn/feed` with low frequency.
   - Parse RSS XML with a structured XML parser.
   - Extract item `link` fields matching `https://spaces.ac.cn/archives/{numeric_id}`.
   - Deduplicate article URLs.

2. Article URL Validation
   - Validate URL format before browser access.
   - Reject non-article paths, PDF links, attachments, and non-Scientific-Spaces hosts.

3. Playwright Browser Access
   - Use Chromium in an isolated, non-persistent browser context.
   - Use `accept_downloads=False`.
   - Abort direct PDF/archive attachment requests.
   - Apply bounded timeout and retry policy.
   - Record only diagnostic metadata during validation.

4. Existing Parser
   - Reuse the existing parser/converter path after the strategy is formally approved.
   - Preserve Markdown, math, image references, and references according to M1 parser requirements.

5. Article Storage
   - Reuse existing Article storage and idempotent upsert behavior.
   - Store only approved article records during implementation, not during strategy evaluation.

## Replacement Assessment

Can this replace homepage/archive discovery?

Assessment: yes, for recent RSS-discoverable articles.

Reason:

- Homepage and archive access are blocked in this environment.
- RSS/feed is accessible and exposes valid article URLs.
- Browser access can retrieve usable article content for a subset of feed URLs.

Boundary:

- RSS/feed should be treated as a replacement for homepage/archive discovery only for the feed's coverage window.
- It should not be treated as full historical corpus discovery unless separately verified and approved.

## Risks

1. Feed coverage risk
   - RSS may only expose recent items and may not cover all historical articles.

2. Browser variability risk
   - Current sample showed mixed results: three full passes, one `403`, and one timeout.
   - Implementation needs retry, timeout, and per-article failure reporting.

3. Operational complexity
   - Playwright introduces browser runtime dependencies and requires CI/runtime setup.

4. Source policy risk
   - Strategy must remain low frequency and avoid bypassing site access controls.

5. Storage policy risk
   - This evaluation did not save HTML or article正文.
   - Any implementation must explicitly decide when and how approved article content is persisted.

## M1 Verification Impact

This report does not change M1 Verification status.

Impact assessment:

- The previous blocker can be reframed from "no live source path" to "strategy revision required."
- RSS discovery provides a viable replacement for homepage/archive discovery for recent articles.
- Browser article access provides a viable candidate article retrieval layer, but it is not yet implemented in the M1 pipeline.
- M1 Verification should remain BLOCKED until the revised strategy is approved, implemented, and verified end to end.

Required future verification before unblocking M1:

1. Implement RSS discovery in M1 source pipeline through a separate task.
2. Implement browser access provider through a separate task.
3. Add opt-in live tests for RSS discovery and browser article access.
4. Verify parser/storage integration without saving forbidden diagnostic artifacts.
5. Run default sync through the revised strategy and confirm idempotent storage.

## Validation Scope

- RSS requests in this evaluation: `1`
- Browser article URL tests in this evaluation: `5`
- Full-site crawling: not performed
- Pagination traversal: not performed
- PDF downloads: not performed
- HTML saved to disk: no
- Article正文 saved to disk: no
- Images or attachments saved to disk: no
- Cache artifacts saved to repository: no

## Strategy Feasibility

Strategy feasibility: PASS

Reason:

- RSS discovery is accessible, structured, and returns valid article URL format.
- Browser article access can retrieve usable article content signals for feed-discovered URLs.
- Existing parser and storage components are already available for a future implementation revision.

## Recommendation

Proceed to an M1 implementation revision task, with explicit safeguards:

1. Keep RSS as the primary discovery source.
2. Keep browser access bounded, low-frequency, and non-persistent.
3. Add per-URL validation and failure reporting.
4. Do not claim M1 Verification Passed until the revised strategy is implemented and verified end to end.

## Conclusion

A: Ready for implementation revision
