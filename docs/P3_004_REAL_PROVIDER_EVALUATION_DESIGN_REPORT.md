# P3-004 Real Provider Evaluation Design Report

Date: 2026-07-15

Status: **PASS / CLOSED**

Real-provider request authorization: **NOT GRANTED**

## 1. Scope Result

P3-004 implemented the operator-only provider-evaluation safety boundary using deterministic fake providers and dry-run behavior. It made no real or paid request, read no provider credential, accessed no private Zotero/user data, and changed no product startup, API, UI, Article, M1, legacy, or `/v1.1` contract.

P3-004 PASS proves the local control architecture only. It does not authorize real-provider construction or execution.

## 2. Architecture

The implementation is isolated under `backend/app/evaluation/provider_eval/`:

- `models.py`: versioned run, case-result, request-envelope, consent, limit, output-policy, and preflight contracts.
- `policy.py`: approved-case loading, exact key allowlists, fail-closed consent/budget/pricing checks, request construction, and output confinement.
- `adapters.py`: deterministic fake adapter only; it has no network or credential capability.
- `runner.py`: preflight-before-construction ordering, request/cost/retry accounting, terminal classification, metrics, and bounded output.
- `output.py`: redaction and atomic raw-off report writing.
- `operations.py`: path-confined output audit, 30-day redacted retention planning, and explicit run deletion.

For `provider=real`, the runner returns a `planned` preflight result with `adapter_construction_authorized=false` and `network_authorized=false`. It does not construct any adapter or write run artifacts.

## 3. Data Contracts

### ProviderEvaluationRun

The serialized `provider-evaluation-run/v1` record contains provider/model/config identity, consent state, declared data categories, request/cost/context/output/retry/timeout caps, usage/cost assumptions, result counts, status, and output policy. It contains no credential, auth header, complete prompt, raw provider metadata, or local path.

### ProviderEvaluationCaseResult

Each `provider-evaluation-case/v1` row contains fixed case identity, task/source expectations, public-data classification, monotonic request index, terminal status, bounded usage/cost/latency/retry metadata, returned source IDs, automated heuristic fields, response digest, optional bounded redacted text, sanitized error class, and explicit pending human-review fields.

### Request Envelope

The exact top-level allowlist is:

```text
schema_version, case_id, task_type, instruction, protocol,
data_classification, evidence
```

Evidence is bounded by source and context caps and enclosed in explicit `UNTRUSTED_ARTICLE_EVIDENCE` delimiters. Fixture prompt-injection text remains evidence and cannot alter the fixed protocol object.

## 4. Consent and Budget Matrix

| Scenario | Result | Adapter constructions | Network requests |
| --- | --- | ---: | ---: |
| Real selection without acknowledgements | `consent_missing` | 0 | 0 |
| Zero/negative/unbounded request, cost, context, output, timeout, or retry limit | `budget_invalid` | 0 | 0 |
| Real selection with unknown pricing/date | `budget_invalid` | 0 | 0 |
| Valid real-mode P3-004 preflight | `planned`; no artifacts | 0 | 0 |
| Fake request cap reached | remaining cases `budget_stopped` | fake only | 0 external |
| Fake estimated-cost cap reached | stop before next attempt | fake only | 0 external |
| Long context/output | deterministically truncated to caps | fake only | 0 external |

The preflight reports provider/model, endpoint category, case set/count, request/cost/context/output/timeout/retry caps, pricing metadata, declared data categories, bounded snippet policy, excluded private data, and ignored-local output policy.

## 5. Deterministic Dry-Run Evidence

Command:

```bash
uv run --project backend python scripts/eval/run_real_provider_eval.py \
  --provider fake \
  --case-set backend/tests/fixtures/evaluation/provider_cases.json \
  --dry-run \
  --output-dir .local_data/scientific_spaces/evaluation/real_provider/dry-run
```

Run ID: `2d7679b33bf04937a634d7e490ef8869`

| Metric | Result |
| --- | ---: |
| Fixed cases | 15 |
| Fake request attempts | 18 |
| Successful cases | 9 |
| Expected terminal-error cases | 6 |
| Retries | 3 |
| Request success rate | 0.5 (9 successful / 18 attempts) |
| Refusals | 3 |
| Estimated fixture cost | 0.018 USD |
| External network requests | 0 |
| Raw output | disabled |
| Human reviews completed | 0 |

The terminal matrix covered `timeout`, `rate_limited`, `auth_error`, `server_error`, `malformed_response`, and `validation_error`. Preflight and budget tests additionally covered `consent_missing`, `budget_invalid`, and `budget_stopped`.

The reported success rate and other automated metrics are explicitly labeled heuristics, not human correctness or real-provider quality.

## 6. Redaction, Retention, and Artifact Evidence

Fake output contained only:

```text
run.json
cases.jsonl
aggregate.json
```

No `raw/` directory was created. The audit scanned all three files and reported:

- findings: 0
- secret/auth-header patterns: 0
- local absolute paths: 0
- private field names: 0
- forbidden artifact types: 0

Redacted case output defaults to 30-day retention. Aggregate and run metadata remain until operator deletion. Cleanup is dry-run by default, supports an explicit run ID or age threshold, preserves aggregate evidence during retention cleanup, and rejects path escape, symlinks, or ambiguous run IDs.

After the bounded evidence above was recorded, the explicit run-deletion command removed the generated run. A post-cleanup audit reported 0 files and 0 findings; no evaluation runtime output remains in the task worktree.

## 7. Test Evidence

| Gate | Result |
| --- | --- |
| Focused provider-evaluation tests | `35 passed` |
| Frozen evaluation/RAG/Tutor compatibility selection | `110 passed` |
| Full Backend suite | `530 passed, 3 skipped` |
| Frontend production build | PASS, Next.js 15.5.20, static generation 8/8 |
| Fake dry-run | PASS |
| Valid real preflight plan | PASS, adapter/network disabled |
| Output artifact audit | PASS, 0 findings |

No CI result is claimed because this task authorizes a local commit only and explicitly does not authorize push.

## 8. Compatibility and Risk

- Existing fake providers remain product and CI defaults.
- Existing network-capable providers were not imported, wrapped, constructed, or changed.
- No dependency, lockfile, `.gitignore`, frontend source, product API, or frozen module changed.
- Actual provider latency, usage, model quality, immutable version identity, retention enforcement, and pricing accuracy remain unmeasured. These are expected real-provider limitations, not P3-004 design failures.
- Any real request remains a separate task with named provider/model, cases, data categories, request/cost caps, currency, dated pricing source, retention policy, and explicit operator acknowledgement.

## 9. Decision

**PASS / CLOSED**

The fake/dry-run architecture satisfies ADR 0007 and the P3-004 acceptance gate. The next recommended task is separately staging and aligning P3-005 CI Security and Release Provenance. No P3-005 implementation is authorized by this report.
