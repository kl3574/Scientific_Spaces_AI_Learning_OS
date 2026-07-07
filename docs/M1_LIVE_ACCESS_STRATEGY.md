# M1 Live Source Access Strategy

## Summary

Status: still blocked.

The live Scientific Spaces source path remains inaccessible from the current execution environment. The current blocker is consistent with the existing `ADR/0003-m1-live-source-access-blocker.md`, so no new ADR is created.

## Environment

- OS: `Linux-7.0.0-27-generic-x86_64-with-glibc2.43`
- System Python: `3.10.20`
- Backend Python via `uv`: `3.11.15`
- System `requests`: `2.34.2`
- Backend `requests`: not installed
- Network environment summary:
  - Proxy environment variables are present: `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and lowercase equivalents are set.
  - DNS resolution for `spaces.ac.cn` returned `8.130.21.162`.
  - The crawler uses Python standard library `urllib.request`, not `requests`.

## Current Crawler Access Policy

Source: `backend/app/crawler/downloader.py`.

- User-Agent: `ScientificSpacesAILearningOS/0.2`
- Headers: only `User-Agent` is sent by the default fetcher.
- Timeout: `20` seconds.
- Retry: `download_url()` defaults to `3` retries with `0.5` seconds incremental backoff.
- Live diagnostic check used `retries=1` and `backoff_seconds=0` to avoid repeated live requests.
- Cache: `FileCache` prevents repeated downloads after a successful response; no cache is written for the current 403 failure.

## Robots Check

Live request count: 1.

Command behavior:

- URL: `https://spaces.ac.cn/robots.txt`
- User-Agent: `ScientificSpacesAILearningOS/0.2`
- Timeout: `20` seconds

Observed result:

```text
status: 200
content-type: text/plain
sample:
User-agent: *
Disallow: /search/
```

Interpretation:

- `robots.txt` is reachable.
- The root index path `/` is not disallowed by the observed robots policy.
- The 403 is not explained by a robots rule that blocks `/`.

## Live Integration Check

Live request count: 1.

Command:

```bash
RUN_LIVE_TESTS=1 uv run --project backend --extra dev pytest -m live backend/tests/test_live_access.py -q
```

Observed result:

```text
urllib.error.HTTPError: HTTP Error 403: Forbidden
app.crawler.downloader.DownloadError: Failed to download https://spaces.ac.cn/
```

Interpretation:

- The independent live integration check uses the same URL and downloader path as the default sync entry path for the index page.
- Because it confirmed the same `https://spaces.ac.cn/` access path returns 403, default `python -m app.sync` was not repeated in this task to avoid duplicate live requests.

## Access Strategy

The project should not bypass access controls or submit manually downloaded content.

Recommended next steps:

1. Keep `M1 Verification Blocked` until live access is resolved or an approved source access method is documented.
2. Ask the source owner or operator for an approved access method if automated ingestion is expected.
3. If an approved mirror or exported source bundle is provided later, document it in source policy before changing ingestion behavior.
4. Keep the fixture-based pipeline tests for parser, converter, storage, validation, and idempotency, but do not treat fixture success as live source verification.

## Request Discipline

This diagnostic pass used two live requests total:

1. `https://spaces.ac.cn/robots.txt`
2. `https://spaces.ac.cn/`

No high-frequency crawling, bulk page discovery, artificial download submission, or access-control bypass was attempted.
