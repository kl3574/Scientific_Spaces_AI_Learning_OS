# P3-044 Tutor Mode Policy and Offline Product Regression

## Status

LOCAL COMPLETE / OFFLINE VERIFIED. The user approved all 12 v3 reference-content
cases after reviewing them in the current conversation. The version/digest-bound
[human decision record](../reviews/P3_044_AFFINE_V3_HUMAN_DECISION.json) is authoritative
for that subsequent decision; actual model-answer quality remains NOT_RUN.
Latest focused local verification: 202 passed. Earlier implementation verification:
backend 1244 passed / 4 skipped; frontend 179 passed.
Owned production build and original repeat-three E2E passed, including the original
restart, image, navigation and component gates. Independent code review passed.
Those counts are historical local evidence, not checks of a newly published commit.
Remote publication checks are reported by GitHub Actions for the relevant commit.

## Authoritative Baseline

- Formal version: v1.1.0; candidate: None.
- Starting HEAD: `893197bf9ca8555078eddfc85225ff0428a436ad`.
- Branch: `codex/p3-044-tutor-mode-policy`, separate worktree from the dirty main checkout.
- Prior task: P3-034.1 diagnostic evidence; Reader P3-042 remains OPEN / CI BLOCKED,
  Graph P3-039 remains OPEN / DEFERRED with historical cause UNKNOWN.
- Inputs: current Tutor/LLM/RAG implementation, v1.2 PRD/architecture/evaluation plan,
  P3-004 report, ADR 0007, existing fixtures and original compatibility/E2E gates.
- The implementation and review-preparation phases were originally local only.
  The subsequent user instruction authorizes GitHub synchronization and redundant
  content cleanup for progress alignment and planning. No applicable AGENTS.md exists.

## Goal and Scope

Make explain/derive/qa/quiz/research tasks reach the generator before generation.
First capture the actual same-question/same-evidence five-mode baseline. Preserve
existing mode-sensitive retrieval and SourceSelector rules. Reuse the existing
offline evaluation facilities to observe the product TutorService, with clearly
separated contract, synthetic fixture, pending human and unrun real-provider results.

Implementation-phase production paths: `backend/app/tutor/generation.py`, Tutor service, LLM
provider/fake. Additional paths: one module under existing `app/evaluation`, one
CLI under `scripts/eval`, focused tests and self-authored synthetic fixtures,
this task/report, and minimal current-entry links in CURRENT_TASK, alignment,
project state and README. No new external dependencies or product agents.

The subsequent review-preparation phase added the static review validator,
request-observation module and CLIs, their tests and the v3 review packet, as
recorded in the [preparation report](../P3_044_AFFINE_REVIEW_PREPARATION_REPORT.md).
The present synchronization adds the separate human decision and consolidates
current entry documents/roadmaps without extending those product changes.

## Required Contracts

1. Explain requests definitions, intuition, supported examples, misconceptions,
   and analogy-versus-proof distinction. Derive requests assumptions/domains,
   reader-verifiable steps with grounds, and explicit unsupported gaps/refusal.
   QA answers directly then pairs evidence. Quiz specifies objective/level and
   separates questions from answer rationales. Research separates evidence,
   conjecture, gaps and validation, with no completeness claim.
2. Preserve legacy `chat(question, contexts)` callers and custom providers using
   an explicit adapter, with no interface guessing or exception-driven retries.
3. Separate trusted task, question and untrusted evidence. Preserve source IDs,
   selection order/limits and refusal branches. Count instructions, data and
   serialized escaping against the existing character cap; fail closed if the
   full admitted evidence cannot fit. Do not fabricate spans or semantic proofs.
4. Test mode differences on identical evidence, public fields, source refusal,
   symbol conflicts, injection, valid-ID/wrong-claim contrasts, oversized input,
   malformed/missing source location, stale index and provider errors. Capabilities
   absent from the product must be NOT_IMPLEMENTED or NOT_APPLICABLE.
5. Four separate results: `contract_results`, synthetic `fixture_results`,
   `human_review` PENDING/null, `real_provider_results` NOT_RUN/null (unauthorized).
   Record HEAD/change and fixture fingerprints, policy/config versions, samples,
   denominators, failures/skips and comparison conditions. Development/acceptance
   Articles and topics are disjoint; these authored fixtures are not a gold standard.
6. Run focused then full compatible backend gates, all existing frontend test
   scripts, an owned production build and original repeat-three Product E2E.
   Run available offline safety gates and review the real diff/interfaces/data.
   An independent review claim requires an actual independent reviewer.

## Boundaries

- Preserve the original dirty checkout: no stash/reset or user-process termination.
  GitHub commit/push and the existing CI are now authorized for this synchronization;
  no release/tag or repository permission change is part of it.
- No private Zotero, real/paid model, blog/source fetching, model-weight download,
  automatic private-corpus ingestion or unrelated external network requests.
- Preserve Article/M1, legacy, /v1.1 and /v1.2 fields, fake defaults, P3-004's real
  planned gate, Reader/Shell/Graph/Zotero/persistence/storage and privacy boundaries.
- No weakened tests, sleeps/retries hiding failures, historical-fault closure or
  unrelated product work. Complete independent safe work when a gate is blocked;
  record the exact blocked command and reason instead of widening scope.
- Raw captures and runtime output stay ignored. Public deliverables contain only
  code, synthetic fixtures and sanitized summaries, with no local absolute paths.

## Verification and Delivery

Use `UV_OFFLINE=true`, fake providers and isolated synthetic stores. Commands:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_tutor_generation.py backend/tests/test_tutor_generation_evaluation.py
uv run --project backend --extra dev pytest -q
npm --prefix frontend run test:articles
npm --prefix frontend run test:references
npm --prefix frontend run test:tutor
npm --prefix frontend run test:graph
SCIENTIFIC_SPACES_E2E_BACKEND_PORT=18000 RUN_LIVE_TESTS=0 uv run --offline --project backend python scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start --output .local_data/p3-044/product-e2e-final.json
```

The existing E2E helper owns a temporary production build at a nondefault backend
port and cleans its services. Dependency/browser absence blocks that gate rather
than authorizing downloads. Full dependency intelligence/schema-network gates
cannot be represented by their offline substitutes.

Report: [implementation and verification](../P3_044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION_REPORT.md).
The immutable v3 preparation snapshot retains its original PENDING fields. The
separate human decision above records the later approval without changing its digest.
These exposed, authored cases are development/regression data, not an unseen holdout.
This is not release qualification or real-model quality certification.

## Next Task

NEXT_TASK (planning only): Use the approved v3 references for controlled-response,
claim-level offline regression. First specify the claim-to-evidence observations and
failure criteria, preserving separate contract, reference-content and actual-answer
results. That next evaluation is not implemented by this synchronization.

Deferred only: explicitly authorized real-model sampling/retrieval comparison;
LearningAttempt/ReviewSchedule loop; source-anchor notes with recoverable export/import;
human-reviewed prerequisites and local learning paths. None is implemented here.
