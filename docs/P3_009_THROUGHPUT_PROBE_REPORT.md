# P3-009 Throughput Probe Report

## Status

P3-009 throughput probe: **PASS**

Selected stable tier: **WebBridge, 1 worker, 4-second global navigation interval**

Date: 2026-07-28

## Authorized Envelope

- known canonical Article URLs only;
- maximum 4 browser workers;
- minimum 4-second global navigation-start interval;
- maximum 25 URLs across the probe;
- immediate stop on HTTP 403/429, retry clustering, source-quality failure, or
  material runtime degradation; and
- no archive scan, search-page crawl, access-control bypass, or cookie export.

## Provider Constraint

The authorized desktop Chrome session became available through the local Kimi
WebBridge. The bridge can reliably bind commands and PDF output to exactly one
controlled current tab. A browser-target enumeration attempt was rejected by
the browser, so multiple tabs could not be mapped to Articles without risking
cross-Article PDF assignment.

The safe provider concurrency upper bound is therefore **1 worker**. This is a
provider identity constraint, not a claim that the source site can handle only
one concurrent visitor. Unsafe multi-tab concurrency was not attempted.

## Probe Ladder

The provider-specific ladder used three distinct formula-bearing Articles per
tier:

| Workers | Global interval | URLs | HTTP 200 | PDF PASS | Retries | Median | Max | Result |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 8 s | 3 | 3 | 3 | 0 | 13.151 s | 15.975 s | PASS |
| 1 | 6 s | 3 | 3 | 3 | 0 | 17.247 s | 17.282 s | PASS |
| 1 | 4 s | 3 | 3 | 3 | 0 | 19.547 s | 21.365 s | PASS |

All nine URLs were distinct. Every generated probe PDF passed:

- valid PDF envelope and EOF;
- at least one readable A4 page;
- Article title;
- Chinese text;
- distributed authoritative body anchors; and
- MathJax evidence for formula-bearing Articles.

The differing render durations reflect Article complexity; the probe detected
no material latency or memory degradation. The fastest allowed stable pressure
tier was `1 worker / 4 seconds`.

## Prior HTTP 403 Evidence

Bundled Playwright Chromium and a separate headed browser previously returned
HTTP 403 at the minimum-pressure baseline. The successful probe used the
already connected real desktop Chrome session authorized by the user. No
cookies, profiles, credentials, or browser storage were copied into the
repository or a second browser.

The access change is treated as environment-dependent source availability. It
does not relax HTTP/content/PDF gates or alter the frozen M1 crawler.

## Runtime Controls

The production path enforces:

- one controlled WebBridge tab;
- a shared navigation-start limiter with a 4-second floor;
- bounded retries and 30-second browser-error backoff;
- final URL, HTTP, Article-body, title, A4, body, Chinese, and MathJax gates;
- immediate failure classification;
- sequential Zotero writes;
- append-only resumable checkpoints;
- PDF SHA-256 readback verification; and
- exactly one PDF and zero HTML children per target parent.

Probe evidence remains only under ignored
`.local_data/scientific_spaces/zotero_pdf_sync/throughput_probe.json`.
Temporary probe PDFs were removed; no browser profile, trace, screenshot, or
HTML dump was retained.

## Decision

Throughput feasibility: **PASS**

- safe provider concurrency upper bound: **1 worker**;
- tested interval lower bound: **4 seconds**;
- selected production tier: **1 worker / 4 seconds**; and
- source-access stop and backoff gates remain active.
