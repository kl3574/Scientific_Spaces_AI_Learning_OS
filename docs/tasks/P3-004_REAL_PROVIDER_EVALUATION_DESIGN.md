# P3-004 Real Provider Evaluation Design

## Status

PASS / CLOSED

IMPLEMENTATION AUTHORIZATION: COMPLETED UNDER CONFIRMED FAKE/DRY-RUN ALIGNMENT

REAL PROVIDER AUTHORIZATION: NOT GRANTED

## Task Identity

P3-004 Real Provider Evaluation Design

## Authoritative Baseline

- Repository baseline: P3-003 implementation commit `fb5419fc31222be738178a3ed65cf11dfb9192fe`
- Previous task: P3-003 Structured Reference Extraction Pilot, PASS / CLOSED
- Architecture baseline: `edc6e4a4f619c8b7bc0cd3de480fbd64a463aabf`
- Formal version: `v1.1.0`
- Candidate version: Not assigned
- Applicable ADR: `docs/ADR/0007-real-provider-evaluation-boundary.md`
- Applicable governance: root `AGENTS.md`, `docs/tasks/README.md`, and a separately confirmed `alignment.md`

## Background

The released system uses deterministic fake embedding and generation providers. Existing evaluation covers response contracts, grounding, refusal, context bounds, and reproducibility, but it does not establish real-provider latency, usage, cost, failure behavior, citation faithfulness, or model quality. A real provider crosses network, privacy, retention, and cost boundaries.

P3-002 approved an operator-only evaluation architecture. P3-004 is limited to implementing and verifying that architecture with fake providers and dry-run behavior. P3-004 PASS does not authorize a real request.

## Goals

- Define unified embedding/chat evaluation adapter metadata and run/case contracts.
- Fail closed on missing consent, invalid budgets, unknown pricing, or disallowed data before adapter construction.
- Restrict request envelopes to fixed case instructions and bounded approved public-corpus snippets.
- Enforce request, cost, context, output, retry, and timeout bounds.
- Produce aggregate and bounded redacted output with raw output disabled.
- Verify retention/deletion, error taxonomy, artifact safety, fake-provider defaults, and zero network access.

## Non-Goals

- No real or paid provider request.
- No real credential, API key, auth header, or provider secret.
- No private Zotero library, Learning state, notes, Tutor history, or other private user data.
- No product runtime default, startup, API, or UI change.
- No full prompt or raw provider output by default.
- No P3-005 CI security implementation, P3-006 full-corpus reference build, candidate assignment, tag, or Release.

## Implemented Scope

- `ProviderEvaluationRun` and `ProviderEvaluationCaseResult` contracts consistent with `docs/V1_2_DATA_MODEL.md`.
- Evaluation-owned embedding/chat adapter metadata without changing provider defaults.
- Consent and budget preflight with deterministic fake/dry-run behavior.
- Request-envelope allowlist and prompt-injection treatment for untrusted Article evidence.
- Fixed metadata-only cases and deterministic fake responses/errors.
- Aggregate/redacted output, raw-off behavior, retention/deletion, and artifact audit tooling.
- A focused design report and deterministic tests proving zero real requests.

## Out of Scope

- Real-provider quality measurement or comparative paid evidence.
- Credentials or operator-specific provider configuration.
- Product feature integration or default-provider selection.
- Private user/Zotero data, complete corpus transfer, arbitrary file input, or remote source access.
- Article, M1, P3-003, legacy API, `/v1.1` API, Graph storage, image archive, authentication, or multi-user changes.

## Allowed Changes

The confirmed execution alignment authorized only:

- evaluation/provider-owned modules under `backend/app/evaluation/`;
- focused fake/dry-run tests and bounded metadata-only fixtures under `backend/tests/`;
- evaluation CLI and audit tooling under `scripts/eval/`;
- `.gitignore`, only if the approved ignored output root is not already covered;
- `docs/P3_004_REAL_PROVIDER_EVALUATION_DESIGN_REPORT.md`;
- task, project-state, README command, and alignment documentation required by the confirmed task.

The implementation remained within this allowlist. `.gitignore` did not require a change because `.local_data/` was already ignored.

## Prohibited Actions

- Construct or call a network-capable provider in tests, dry-run, default startup, or CI.
- Send data externally or use a paid request.
- Read, send, log, serialize, or retain a key, auth header, secret environment value, private Zotero metadata, private user state, full corpus, arbitrary file, or local absolute path.
- Permit consent or budget checks to occur after adapter construction.
- Treat missing pricing as zero cost or allow unbounded requests/retries/context/output.
- Persist raw provider metadata or full prompts by default.
- Label automated heuristics as human correctness.
- Modify frozen product contracts or select a real provider by default.

## Inputs

- Approved v1.2 architecture, data model, threat model, evaluation plan, acceptance criteria, and execution plan.
- ADR 0007.
- Existing evaluation modules and deterministic fake providers.
- Fixed synthetic or bounded metadata-only cases.
- Optional bounded public Article snippets only in tests that remain fully local and no-network.

## Data Contracts

### ProviderEvaluationRun

A versioned aggregate record for provider/model identity, explicit consent state, case-set/config identity, request/cost/context/output/retry limits, aggregate usage/cost assumptions, result counts, status, and output policy. It must contain no secret or full sensitive prompt.

### ProviderEvaluationCaseResult

A bounded, redacted case result containing fixed case identity, task/source expectations, safe data classification, request index, terminal status, bounded latency/retry/usage/cost metadata, returned source IDs, heuristic metrics, sanitized error class, response digest, optional bounded redacted response, and explicit human-review fields.

### Request Envelope

An allowlisted in-memory structure containing only fixed case instructions and bounded approved public-corpus evidence. Article content is delimited as untrusted evidence and cannot alter the protocol.

## Deliverables

- Evaluation contracts and adapter metadata.
- Fail-closed consent and hard budget controls.
- Request-envelope allowlist and deterministic fake/dry-run runner.
- Redaction, raw-off, retention/deletion, and artifact audit behavior.
- Focused deterministic tests covering success and terminal failure taxonomy.
- `docs/P3_004_REAL_PROVIDER_EVALUATION_DESIGN_REPORT.md`.
- Status-appropriate commit and CI evidence only if separately authorized by the execution alignment.

## Acceptance Criteria

### PASS

- Fake/dry-run proves consent fails before adapter construction.
- Positive request and estimated-cost caps are mandatory for any real-mode preflight.
- Request, cost, context, output, timeout, and retry limits are enforced deterministically.
- Request-envelope snapshots contain only allowlisted fields.
- Prompt-injection content remains untrusted evidence and cannot change the protocol.
- Redaction, raw-off, retention/deletion, artifact, and secret checks pass.
- External network requests and unexpected network attempts equal zero.
- Fake providers remain the default in runtime and CI.
- Reports distinguish automated heuristics from human correctness.
- Existing Backend regressions and Frontend build pass.

### CONDITIONAL

The deterministic adapter/report design passes, but a documented named-provider limitation such as immutable version or usage metadata remains. No real evaluation becomes authorized.

### BLOCKED

- A real call occurs or a network-capable adapter is constructed without a separately authorized real-run task.
- Consent, budget, request-envelope, redaction, retention, or zero-network controls can be bypassed.
- A secret, auth header, private user/Zotero data, raw output, full prompt, local path, or runtime artifact is exposed or tracked.
- CI/default startup can select a real provider.
- A frozen contract, test, or build regresses.

## Verification Commands

Planned commands, not authorized until a complete execution alignment is confirmed:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_real_provider_evaluation_*.py
uv run --project backend python scripts/eval/run_real_provider_eval.py \
  --provider fake --case-set <planned-fixture> --dry-run \
  --output-dir .local_data/scientific_spaces/evaluation/real_provider/dry-run
uv run --project backend --extra dev pytest -q
npm --prefix frontend run build
```

The future task must also run bounded request-envelope, no-network, retention/deletion, artifact, secret, changed-path, and frozen-compatibility audits.

## Artifact and Secret Policy

Runtime output belongs below `.local_data/scientific_spaces/evaluation/real_provider/` and must remain ignored. Never commit or attach API keys, auth headers, provider raw output, complete prompts, Article/corpus exports, private Zotero/user data, databases, PDFs, HTML/images, archives, Graph/RAG data, traces, profiles, caches, local absolute paths, or generated evaluation output.

## Git Plan

- Current staging commit: docs-only P3-003 closure and P3-004 canonical specification
- Implementation commit: `0bf90e518549bea7549409cde72a3befda0c340d`
- The original implementation alignment did not authorize push; the commit was subsequently pushed under separate authorization.
- Main CI: PASS, run `29627617727`
- Main CI URL: https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29627617727
- Tag: prohibited
- Release: prohibited

## Stop Conditions

- A real/network/paid request, credential, private Zotero/user data, or nonlocal data transfer is required.
- Work requires product defaults, startup, Article, M1, P3-003, legacy API, or `/v1.1` API changes.
- Consent, budgets, allowlisting, zero-network, redaction, retention, or artifact controls remain ambiguous.
- Test/build failure, unknown worktree drift, REWORK/FAIL audit, or credible artifact/secret finding appears.
- Required changes fall outside the future confirmed allowlist.

## Completion Evidence

- Focused tests: 35 passed
- Frozen compatibility selection: 110 passed
- Full Backend suite: 530 passed, 3 skipped
- Frontend production build: PASS, static generation 8/8
- Fake dry-run: 15 cases, 18 fake attempts, 0 external network requests, raw output disabled
- Artifact audit: PASS, 0 findings
- Implementation commit: `0bf90e518549bea7549409cde72a3befda0c340d`
- Main CI run: `29627617727`
- Main CI URL: https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29627617727
- Backend pytest: PASS
- Frontend build: PASS
- Docker compose smoke: SKIPPED by normal main-push policy
- Report: `docs/P3_004_REAL_PROVIDER_EVALUATION_DESIGN_REPORT.md`
- Real-provider authorization: NOT GRANTED

## Next Task

P3-005 CI Security and Release Provenance is canonically staged with implementation authorization NOT GRANTED. The next decision is confirmation or revision of its execution alignment. P3-004 PASS grants no real-provider request authority.
