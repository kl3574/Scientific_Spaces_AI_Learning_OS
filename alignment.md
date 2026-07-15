# P3-004 Real Provider Evaluation Design - Confirmed Execution Alignment

## 1. Background

- Current task: `P3-004 Real Provider Evaluation Design`.
- Canonical specification: `docs/tasks/P3-004_REAL_PROVIDER_EVALUATION_DESIGN.md`.
- Previous task: P3-003 Structured Reference Extraction Pilot, `PASS / CLOSED`.
- Formal version: `v1.1.0`; candidate version: not assigned.
- P3-004 implements and verifies the approved provider-evaluation safety architecture with deterministic fake providers and dry-run behavior only.
- P3-004 PASS does not authorize a real, paid, credentialed, or network request.
- Execution alignment was explicitly confirmed by the user before implementation.

## 2. Requirements

1. Define versioned `ProviderEvaluationRun` and `ProviderEvaluationCaseResult` contracts plus evaluation-owned provider metadata.
2. Fail closed before adapter construction when consent is missing, budgets are invalid, pricing is unknown, or data is disallowed.
3. Restrict request envelopes to fixed instructions and bounded approved public-corpus evidence, delimited as untrusted input.
4. Enforce positive request, cost, context, output, timeout, and retry limits.
5. Support deterministic fake success and terminal failure cases without constructing a network-capable provider.
6. Produce bounded redacted `run.json`, `cases.jsonl`, and `aggregate.json` output with raw output disabled by default.
7. Implement path-confined retention, dry-run deletion, and artifact audit behavior for ignored local output.
8. Distinguish automated heuristics from human correctness in contracts and reports.
9. Preserve fake providers as runtime and CI defaults and preserve all frozen product contracts.

## 3. Purpose

Create an auditable, reproducible, fail-closed boundary for a future separately authorized real-provider evaluation. This task proves the boundary locally with fake providers, deterministic fixtures, no-network assertions, redaction, budgets, retention, and artifact controls.

## 4. Planned Execution

1. Add an isolated `backend/app/evaluation/provider_eval/` package for models, policy, adapters, runner, output, retention, and audit behavior.
2. Make only a fake adapter executable. Treat `provider=real` as preflight-plan-only and stop before credential access, provider construction, or network activity.
3. Add metadata-only fixtures and focused tests under `backend/tests/`.
4. Add run, cleanup, and audit CLIs under `scripts/eval/`.
5. Keep generated output below `.local_data/scientific_spaces/evaluation/real_provider/`, which is already ignored.
6. Create `docs/P3_004_REAL_PROVIDER_EVALUATION_DESIGN_REPORT.md` and update canonical task/project planning documentation according to the verified result.
7. Run focused tests, fake dry-run, compatibility regressions, full Backend tests, Frontend build, and artifact/secret/changed-path audits.
8. Create one status-appropriate local commit. Do not push, tag, create a Release, or make an external write.

Stop if implementation requires a real provider, credentials, private data, frozen-contract changes, new out-of-scope dependencies, or if tests/build/audits expose an unresolved blocker.

## 5. Selection Rationale

An isolated provider-evaluation package gives the strongest boundary and smallest regression surface. It avoids modifying existing deterministic evaluation behavior or wrapping existing network-capable providers. Fake-only adapter execution and real-mode preflight rejection make zero-network behavior directly testable.

## 6. Alternatives

| Option | Advantages | Disadvantages | Decision |
| --- | --- | --- | --- |
| A. Isolated `provider_eval` package | Clear risk boundary, small regression surface, direct no-network proof | More small modules | Selected |
| B. Extend existing evaluation runner | Fewer files | Couples safety controls to stable evaluation behavior | Rejected |
| C. Wrap existing network providers | Faster future provider integration | Risks credential/network construction and violates P3-004 | Prohibited |

## 7. Deliverables

- Provider evaluation contracts, policy, fake adapter, runner, redaction, retention, and audit modules.
- Fixed metadata-only provider evaluation cases.
- Focused deterministic safety and failure-taxonomy tests.
- `scripts/eval/run_real_provider_eval.py`.
- `scripts/eval/cleanup_real_provider_eval.py`.
- `scripts/eval/audit_real_provider_eval.py`.
- `docs/P3_004_REAL_PROVIDER_EVALUATION_DESIGN_REPORT.md`.
- Required updates to canonical task, project state, v1.2 roadmap, README planning links, and this alignment.
- One local status-appropriate commit; no push, tag, or Release.

## 8. Acceptance Criteria

- Consent and budget failures occur before adapter construction.
- Real-mode preflight requires explicit consent, positive caps, and known pricing, then stops without constructing a provider.
- Request envelopes contain only allowlisted fields and untrusted evidence cannot change the protocol.
- Request, cost, context, output, timeout, and retry bounds are deterministic and enforced.
- Terminal classes cover consent, budget, timeout, rate limit, auth, server, malformed-response, and validation failures.
- Output is redacted and bounded; raw output is absent by default.
- Cleanup defaults to dry-run and rejects path escape and symlink traversal.
- Unexpected network attempts equal zero; fake providers remain product and CI defaults.
- No secret, private data, local absolute path, runtime artifact, or generated evaluation output is tracked.
- Focused tests, fake dry-run, compatibility tests, full Backend pytest, and Frontend build pass.
- PASS commit: `feat: implement P3-004 provider evaluation design`.
- CONDITIONAL commit: `docs: record conditional P3-004 evaluation design`.
- BLOCKED commit: `docs: record P3-004 evaluation blockers`.
- Any future real request requires a separate task naming provider, model, cases, data categories, request/cost caps, currency, pricing source, retention, and operator consent.

## Execution Result

- Status: `PASS / CLOSED`.
- Focused P3-004 tests: 35 passed.
- Frozen evaluation/RAG/Tutor compatibility selection: 110 passed.
- Full Backend suite: 530 passed, 3 skipped.
- Frontend production build: PASS, static generation 8/8.
- Fake dry-run: 15 cases, 18 fake attempts, 0 external network requests, raw output disabled.
- Output audit: PASS, 0 findings.
- Real-provider request authorization remains `NOT GRANTED`.
- Push, tag, and Release were not authorized and were not performed.
