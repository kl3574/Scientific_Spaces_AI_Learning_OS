# P3-006.2 Review UX Pilot and Zotero Collection Sync Report

## Status

**PASS / CLOSED**

P3-006.2 delivered a local three-case full-context review pilot and a
downstream, opt-in Scientific Spaces Article-to-Zotero metadata adapter. It did
not modify the frozen source pipeline or the formal P3-006.1 review gate.

## Zotero Collection

- Target: private root collection `苏剑林博客`
- Exact root collection count after readback: 1
- Zotero Desktop: 9.0.6
- Creation safety: Desktop stopped cleanly, a database backup was created
  outside the repository, SQLite `quick_check` passed before restart, and the
  local API confirmed the collection after restart
- Collection key exposure: none; only an irreversible fingerprint was used in
  runtime evidence
- Unrelated item deletion, merge, or update: 0

## Synchronization Contract

The new adapter maps a stored Scientific Spaces Article to one Zotero
`webpage` with title, canonical HTTPS URL, date, `Scientific Spaces` website
title, `zh-CN` language, Article ID provenance, and source/category tags.

Safety behavior:

- exact-name root collection resolution uses a bounded name query;
- matching uses both canonical URL and Article ID;
- duplicate or conflicting matches fail closed;
- dry-run is the CLI default;
- a write requires `--write`;
- Connector/API failures remain visible;
- successful writes require local collection readback;
- collection and item keys are never emitted, only SHA-256 fingerprints.

## Controlled Live Result

The authorized test used Article ID `42ca3db9ef053ea5`, URL
`https://spaces.ac.cn/archives/6508`.

| Check | Result |
| --- | --- |
| First explicit write | `created` |
| Second explicit write | `existing` |
| Matching target items | 1 |
| Item type | Web Page |
| Title/date/website/language | PASS |
| Article ID provenance | PASS |
| Source tag | PASS |
| PDF attachment | Not required; not created |

Only localhost Zotero API/Connector access was used. No source-site request,
real Provider, paid service, or broad private-library export occurred.

## Three-Case Full-Context Pilot

Runtime package:

```text
.local_data/scientific_spaces/references/full-corpus/reviews/p3-006-2-pilot-3/
```

It contains only:

```text
pilot_manifest.json
pilot_review.csv
reviewer.html
```

| Stratum | Article ID | Content length |
| --- | --- | ---: |
| strong_identifier | `68441d48f88c5de6` | 35,390 |
| duplicate_group | `573354a74b26d9a3` | 1,891 |
| ambiguous_text | `d3b2db76b2e5a2dd` | 6,066 |

The local reviewer page contains the full authoritative `Article.content` for
all three cases, bounded reference evidence, case metadata, blank manual
judgment controls, and a local CSV download action. It is visibly marked
`PILOT ONLY`; it neither modifies nor replaces the formal 64-case packet.

Browser verification used headless Chromium:

- rendered case sections: 3
- full-content sections: 3
- external script/style assets: 0
- horizontal overflow at 1440 px: 0
- default human verdicts: 0

## Source Integrity

| Evidence | Result |
| --- | --- |
| Article Store SHA-256 | `3b91f22db548373a6c91bb11a5188fb3e388ab9e19c4429e8e8fac918609a505` |
| Reference Store build fingerprint | `70ab191621aa8819f3c195c116aec5b5ae05f44c0b90fb0d11e6cb4365d5d846` |
| Formal review-case SHA-256 | `9618349de7ba2f8f3f3f2f2595d7f4a43ab8b5d799abd5bd31201970e6ba7b73` |
| M1/source module changes | 0 |
| Article/Reference Store mutations | 0 |
| P3-006.1 packet mutations | 0 |

## Verification

- Focused Zotero synchronization tests: 9 passed
- Full Backend suite: 549 passed, 3 skipped
- Repeated live synchronization no-op: PASS
- Runtime metadata and collection-membership readback: PASS
- Three-case schema/full-context/browser checks: PASS
- `git diff --check`: PASS
- Changed-path allowlist: PASS
- Secret audit: PASS, 0 credible findings
- Runtime/private artifact tracking: 0

## Boundaries

- P3-006 remains `CONDITIONAL / CLOSED`.
- P3-006.1 remains `HUMAN_REVIEW_INCOMPLETE / PAUSED`.
- No P3-007, candidate version, tag, Release, attestation, or push occurred.
- Any additional Zotero write or P3-006.1 Stage B action requires a new,
  explicit authorization.
