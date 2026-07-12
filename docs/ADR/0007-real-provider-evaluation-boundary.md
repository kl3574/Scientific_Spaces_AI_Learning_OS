# ADR 0007: Real Provider Evaluation Boundary

Status: Accepted

Date: 2026-07-12

## Context

The released system has deterministic fake embedding and generation providers. Existing evaluation proves response contracts, source grounding, refusal behavior, context bounds, and reproducibility, but does not establish real-model latency, usage, cost, provider failures, citation faithfulness, or language/mathematical quality.

A real provider crosses a network/privacy/cost boundary. Article snippets may leave the machine; provider logging and model identity can drift. Credentials, private Zotero data, Learning state, notes, and Tutor history must not be sent or retained accidentally.

## Options Considered

### 1. Make a Real Provider the Runtime Default

Rejected. It breaks offline/default behavior, introduces credentials/cost, and changes released product semantics.

### 2. Run Real Providers in Normal CI

Rejected. CI would require secrets, paid and variable requests, external availability, and potentially private/copyright-sensitive payloads. Results would be nondeterministic.

### 3. Ad Hoc Maintainer Script

Rejected. It lacks enforceable consent, budgets, request schemas, redaction, retention, reproducibility, and comparable metrics.

### 4. Explicit Operator-Only Evaluation Harness

Selected. Reuse evaluation contracts through embedding/chat adapters while keeping fake providers as default and mandatory CI evidence.

## Decision

Approve a real-provider evaluation harness for v1.2 with these hard boundaries:

- It is not product startup code and cannot be selected by default or normal CI.
- A real run requires explicit provider selection, data-sent acknowledgement, positive request cap, positive estimated-cost cap with dated pricing metadata, explicit case set, and ignored output directory.
- Preflight prints provider/model, endpoint category, cases, request/cost caps, sent data categories, snippet policy, and excluded user data before adapter construction.
- Request envelopes contain only fixed case instructions and bounded approved Article snippets.
- Keys, auth headers, secret environment values, user notes, Learning state, Tutor history, private Zotero metadata, complete corpus, and arbitrary files are prohibited.
- Article content is delimited as untrusted evidence and cannot alter the evaluation protocol.
- Fake/dry-run behavior, consent failures, budgets, redaction, retention, error taxonomy, and no-network checks are release gates. A real paid run is not required for v1.2.

## Output Policy

- Output root: `.local_data/scientific_spaces/evaluation/real_provider/`.
- Aggregate report may be retained locally.
- Redacted case output defaults to 30-day retention.
- Raw output is disabled. Any future enablement requires separate acknowledgement, Tier 3 handling, and 7-day default retention.
- Reports record provider/model/version/date/config fingerprint, case version, usage/cost assumptions, and human review status.
- Automated metrics are not labeled true answer correctness.

## Cost and Reliability Controls

- Request, retry, timeout, context, output, and estimated-cost caps are hard stops.
- Usage and estimated cost reconcile after every response before another request.
- Missing/unknown pricing blocks a cost-bounded real run rather than assuming zero cost.
- Timeout, rate limit, auth, server, malformed response, validation, and budget-stop outcomes are explicit terminal classes.

## Consequences

Positive:

- Real-provider evidence can be collected comparably without weakening safe defaults.
- Operators see data and cost boundaries before any request.
- Fake regressions remain deterministic and available to every contributor.

Costs and residual risks:

- Provider retention and immutable model versions may be unverifiable.
- Submitted public Article snippets still leave the local machine.
- Human quality review costs time and can disagree.
- Hard estimated-cost caps depend on current pricing and provider usage accuracy.

## Future Authorization

P3-004 PASS does not authorize a real request. Every real run needs a new task that names provider/model, case set, data categories, request cap, cost cap/currency/pricing source, output/retention policy, and operator acknowledgement. Private Zotero/user data remains prohibited unless a separate architecture decision changes this boundary.

## Acceptance

- Fake/dry-run tests prove fail-closed consent and budget logic before network adapter construction.
- Request-envelope snapshots contain only allowlisted fields.
- Redaction/deletion/artifact checks find no key, auth header, private user/Zotero data, local path, or full prompt/raw metadata.
- Existing fake-provider, M3 citation/no-source, and M7 grounding/refusal tests remain unchanged.
