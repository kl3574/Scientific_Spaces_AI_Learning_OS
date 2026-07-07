# M1 Article Browser Access Evaluation

## Summary

This evaluation checks whether browser-based direct access to known Scientific Spaces article URLs can serve as a candidate M1 source access strategy.

Result:

- Article access feasibility: PASS
- Conclusion: A: Browser article access works
- Recommendation: Consider whether to update the M1 Source Access Strategy, but only through a separate human-approved strategy update. This evaluation does not change crawler, verification, or project state.

## Source Evidence Reviewed

- `docs/M1_VERIFICATION_REPORT.md`
- `docs/M1_BROWSER_ACCESS_EVALUATION.md`
- `docs/M1_ALTERNATIVE_DISCOVERY_EVALUATION.md`
- `ADR/0003-m1-live-source-access-blocker.md`

Relevant prior evidence:

- Homepage access remains blocked.
- Archive discovery access remains blocked.
- Site-search discovery is not a compliant path because `/search/` is disallowed by the observed `robots.txt`.
- Direct article access with the non-browser HTTP path returned `403`.

## Scope And Discipline

- Browser: Playwright Chromium.
- Known article URLs tested: `1`.
- Live browser navigations performed for this evaluation: `2`.
- No crawler, verification, or project-state files were modified.
- No M2-M7 functionality was implemented.
- HTML, PDF, images, attachments, and article正文 were not saved.
- Page metrics were computed in-browser and recorded only as diagnostic metadata.

## Environment

- OS: `Linux-7.0.0-27-generic-x86_64-with-glibc2.43`
- Python via `uv`: `3.11.15`
- Playwright version: `1.61.0`
- Browser: Chromium `149.0.7827.55`

## Article URL Probe

### Article 1

- URL: `https://spaces.ac.cn/archives/6508`
- HTTP status: `200`
- Title: `科学空间浏览指南（FAQ） - 科学空间|Scientific Spaces`
- HTML length: `75098`
- Content availability: PASS
- MathJax availability: PASS
- Article-like selector signal:
  - `#content, .content`: `2`
  - `article`: `0`
  - `.post`: `0`
  - `.entry, .entry-content`: `0`
  - `main`: `0`

Notes:

- A first navigation using `wait_until="domcontentloaded"` timed out after `20` seconds and did not produce an HTTP status.
- A second navigation using `wait_until="commit"` returned status `200`; after a short diagnostic wait, in-browser metrics indicated usable article content and MathJax availability.
- This suggests the page is reachable as a known article URL through a browser path, but the navigation wait strategy matters.

## Feasibility Assessment

Article access feasibility: PASS

Reason:

- A known article URL returned `200` through Playwright Chromium.
- The page title was available.
- HTML length and in-browser text-length signals indicated non-empty content.
- MathJax availability was detected.

## Conclusion

A: Browser article access works

## Recommendation

This is a viable candidate source access strategy only for known article URLs. It does not solve discovery because homepage and archive discovery remain blocked, and site-search discovery is disallowed by the observed robots policy.

Recommended next decision:

1. Decide whether M1 Source Access Strategy should be updated to support browser-based access for known approved article URLs.
2. If approved, document the strategy separately before changing crawler or verification behavior.
3. Keep M1 Verification Blocked until the approved strategy is documented and implemented through a separate task.
