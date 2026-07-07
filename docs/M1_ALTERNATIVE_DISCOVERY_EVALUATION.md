# M1 Alternative Discovery Evaluation

## Summary

This evaluation checks whether a compliant article discovery or article access path exists while the M1 live source access blocker remains active.

Result:

- Discovery feasibility: FAIL
- Article access: FAIL
- Recommendation: Keep M1 Verification Blocked. Do not use archive, direct article, or site-search paths as a live source path from this environment.

## Source Evidence Reviewed

- `docs/M1_VERIFICATION_REPORT.md`
- `docs/M1_LIVE_ACCESS_STRATEGY.md`
- `docs/M1_BROWSER_ACCESS_EVALUATION.md`
- `ADR/0003-m1-live-source-access-blocker.md`

Relevant prior evidence:

- Homepage access returns `403`.
- Requests/urllib access returns `403`.
- Playwright browser access returns `403`.
- `robots.txt` allows `/` but disallows `/search/`.

## Request Discipline

- Response content was used only for diagnosis.
- Full HTML was not saved.
- Article正文 was not saved.
- Images and attachments were not downloaded or saved.
- No pagination, archive crawling, bulk discovery, or repeated retries were performed.
- Live Scientific Spaces requests in this evaluation: `2`.

## Probe Results

### A. Official Archive Page

- URL: `https://spaces.ac.cn/content.html`
- Requested: yes
- Status: `403 Forbidden`
- Title: not available from diagnostic sample
- HTML obtained: yes, but only a short error response sample was read
- Diagnostic bytes read: `122`
- Content-Type: `text/html;charset=utf8`
- Content validity: FAIL
- Interpretation: The official archive path is not usable for compliant article discovery from this environment.

### B. Single Article Page

- URL: `https://spaces.ac.cn/archives/6508`
- Requested: yes
- Status: `403 Forbidden`
- Title: not available from diagnostic sample
- HTML obtained: yes, but only a short error response sample was read
- Diagnostic bytes read: `123`
- Content-Type: `text/html;charset=utf8`
- Content validity: FAIL
- Interpretation: Direct article access is not usable from this environment.

### C. Search Discovery URL

- URL assessed: `https://spaces.ac.cn/search/`
- Requested: no
- Status: `SKIPPED_POLICY`
- Reason: Existing `robots.txt` evidence records `Disallow: /search/`; this evaluation does not request disallowed site-search paths.
- Title: not applicable
- HTML obtained: no
- Content validity: FAIL
- Interpretation: Site search is not a compliant discovery path under the observed robots policy.

## Feasibility Assessment

Discovery feasibility: FAIL

Reason:

- The official archive page returns `403`.
- The site-search path is disallowed by the observed robots policy and was not requested.
- No compliant live discovery path was established.

Article access: FAIL

Reason:

- The direct article URL returns `403`.
- The diagnostic response does not provide valid article content for source ingestion.

## Recommendation

Keep M1 Verification Blocked.

Next decision should be human/source-policy driven:

1. Request an approved source access method from the site owner/operator.
2. Approve an official export, mirror, or documented source bundle before changing ingestion behavior.
3. Do not treat archive, direct article, site-search, fixture, or browser-blocked access as M2 readiness evidence.
