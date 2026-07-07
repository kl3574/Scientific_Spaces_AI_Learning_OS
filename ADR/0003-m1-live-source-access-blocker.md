# ADR 0003: M1 Live Source Access Blocks M2 Readiness

## Status

Blocking.

## Context

The M1 verification gate requires evidence that the Scientific Spaces source pipeline is ready for M2.

Fixture-based sync succeeds and is idempotent, but the default online sync path fails in the current execution environment:

```text
SCIENTIFIC_SPACES_DATA_DIR=/tmp/scientific-spaces-m1-live-check \
SCIENTIFIC_SPACES_MAX_PAGES=1 \
uv run --project backend python -m app.sync
```

Observed result:

```text
urllib.error.HTTPError: HTTP Error 403: Forbidden
app.crawler.downloader.DownloadError: Failed to download https://spaces.ac.cn/
```

The verification task explicitly forbids fixing M1 implementation issues in this pass.

## Decision

M1 verification is marked blocked for M2 readiness until the live Scientific Spaces access path is resolved or an approved source-access strategy is documented.

No M1 crawler, downloader, parser, converter, storage, validation, or sync implementation code is changed by this verification gate.

## Consequences

- M1 architecture, schema, fixture sync, and tests can be verified.
- M2 should not start from the assumption that live Scientific Spaces ingestion is operational in this environment.
- A follow-up M1 remediation task should decide whether to use an approved mirror, exported source bundle, rate-limit policy, browser/session-based access, or another source-policy-compliant approach.

## Update: 2026-07-07 Live Access Diagnosis

The blocker remains active after a low-frequency diagnostic pass.

Environment summary:

- OS: `Linux-7.0.0-27-generic-x86_64-with-glibc2.43`
- System Python: `3.10.20`
- Backend Python via `uv`: `3.11.15`
- System `requests`: `2.34.2`
- Backend `requests`: not installed
- Proxy-related environment variables are present.
- `spaces.ac.cn` resolves to `8.130.21.162`.

Access checks:

- `https://spaces.ac.cn/robots.txt` returned `200` and only disallowed `/search/`.
- The independent live integration check for `https://spaces.ac.cn/` returned `403 Forbidden` through the same downloader path used by default sync.

Decision update:

- Keep M1 Verification blocked.
- Do not create a duplicate ADR because this is the same live source access blocker.
- Do not run repeated default sync attempts after the live integration check confirms the same URL and access path returns 403.
- Do not bypass site access controls or use fixture data as a substitute for live verification.
