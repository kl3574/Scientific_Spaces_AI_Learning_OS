# Post-MVP Roadmap

## Current Baseline

Scientific Spaces AI Learning OS v1.0.0 MVP is complete.

- Release: Scientific Spaces AI Learning OS v1.0.0 MVP
- Tag: `v1.0.0`
- Tag target commit: `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6`
- Release URL: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/releases/tag/v1.0.0`
- MVP milestones: M0 through M7 completed and verified
- Release readiness: PASS
- Release CI evidence: PASS

Test and build evidence:

- Backend pytest: `63 passed, 2 skipped`
- Frontend build: PASS
- Runtime smoke: backend and frontend PASS
- Release CI workflow: `CI`, manual `workflow_dispatch` on `v1.0.0`
- Release CI run: `https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/28928542749`
- Release CI covered backend pytest, frontend build, and Docker compose smoke

Current known limitations:

- CI is PR/manual triggered; push and tag automation need hardening.
- Local JSON stores are suitable for MVP, but not production multi-user persistence.
- Fake providers are the default for tests; real OpenAI-compatible and Zotero providers require explicit environment configuration.
- Full Scientific Spaces corpus processing is not yet a managed production workflow.
- RAG and tutor quality have functional verification, but not a sustained evaluation benchmark.
- Knowledge graph extraction is deterministic and source-grounded, but conservative and not yet scaled for large graphs.
- Zotero integration is read-only and depends on local Zotero Desktop/API availability.
- Research mode is local-only and not an exhaustive literature review.
- Local Docker was unavailable in prior local audits, although Docker compose smoke passed in GitHub Actions.
- `docs/15_ACCEPTANCE.md` and `docs/31_MVP_BOUNDARY.md` are absent and remain documentation hygiene gaps.

## v1.1 Candidate Themes

1. Deployment hardening.
2. Persistence upgrade.
3. Real provider configuration.
4. Full Scientific Spaces corpus processing.
5. RAG evaluation.
6. Tutor quality evaluation.
7. Knowledge Graph scaling.
8. Zotero real-library integration hardening.
9. CI / release automation.
10. UI / UX polish.
11. Security / privacy hardening.
12. Documentation and onboarding.

## Prioritized Backlog

### P0

#### P0-001 Production Deployment Profile

- Title: Production deployment profile.
- Motivation: The MVP runs locally and in CI, but a clean deployment profile is needed before broader use.
- Scope: Define production and local environment profiles, document required variables, validate startup configuration, preserve fake-provider defaults for tests, and keep Docker compose usable for smoke checks.
- Acceptance criteria: A clean machine can follow documented deployment steps; backend `/health` and frontend `/` pass smoke checks; missing required production variables fail with clear messages; no secrets are committed.
- Risks: Environment drift, provider secret handling, Docker/runtime differences, and accidental coupling to local `.local_data`.
- Dependencies: Current Docker files, `.env.example`, README setup instructions, GitHub Actions Docker compose smoke.

#### P0-002 Persistence Upgrade Decision and First Migration

- Title: Move MVP JSON persistence toward a database-backed storage layer.
- Motivation: Article, learning, Zotero, graph, and tutor stores are local JSON files; this is not durable enough for production or multi-user usage.
- Scope: Create an ADR choosing SQLite or Postgres for the first post-MVP persistence target, define migration boundaries, add isolated test database setup, and migrate one high-value store first without changing public API contracts.
- Acceptance criteria: ADR exists; selected store has automated tests against an isolated database; JSON-to-database migration path is documented; existing APIs remain backward compatible; rollback or backup guidance exists.
- Risks: Schema drift, migration data loss, concurrent-write assumptions, and premature multi-user commitments.
- Dependencies: M1-M7 storage adapters, `docs/04_DATA_MODEL.md`, current environment variable policy.

#### P0-003 CI and Release Automation Hardening

- Title: Automate release evidence and reduce manual CI steps.
- Motivation: v1.0.0 evidence is complete, but tag-level CI was manually triggered.
- Scope: Add push and tag CI triggers where appropriate, keep PR gates, preserve manual release-evidence runs, document release checklist, and add a lightweight changelog discipline.
- Acceptance criteria: PR, main push, and release tag workflows run the required backend pytest and frontend build checks; release evidence can be reproduced for a tag; Docker compose smoke remains covered where runner support exists; README and release docs describe the process.
- Risks: Longer CI runtime, Docker runner flakiness, duplicate workflows, and accidental release automation without evidence review.
- Dependencies: `.github/workflows/ci.yml`, `docs/RELEASE_CI_EVIDENCE_v1.0.0.md`, release notes process.

#### P0-004 Security and Privacy Baseline

- Title: Establish a security and privacy hardening baseline.
- Motivation: The MVP handles local learning data, Zotero metadata, provider credentials, and AI interactions; production hardening requires explicit controls.
- Scope: Add a threat model, secret-handling checklist, privacy/data-retention policy, CORS and host configuration review, dependency audit process, and artifact scanning guidance.
- Acceptance criteria: Security/privacy docs exist; no tracked `.env`, runtime data, Zotero exports, PDF/HTML dumps, FAISS caches, or embedding caches are found; dependency and secret scans are documented; production launch remains blocked until auth/privacy requirements are met.
- Risks: Over-scoping into full auth, missing local privacy paths, and treating fake-provider safety as production security.
- Dependencies: `.gitignore`, `.env.example`, README provider boundaries, release artifact audit.

#### P0-005 RAG and Tutor Evaluation Harness

- Title: Create a repeatable grounded-answer evaluation harness.
- Motivation: M3 and M7 verification proves contracts work, but v1.1 needs measurable answer quality and citation quality.
- Scope: Build a small curated evaluation set from existing article fixtures and verified local articles; measure citation presence, source relevance, no-source refusal, formula handling, and tutor mode behavior.
- Acceptance criteria: Evaluation command runs without real API keys by default; report includes pass/fail thresholds; no-source cases refuse; cited answers include article title, URL, and section; tutor explain/derive/quiz/research modes are covered.
- Risks: Evaluation overfitting, fake-provider limitations, unstable live articles, and unclear subjective quality thresholds.
- Dependencies: M3 RAG service, M7 tutor service, article fixtures, source citation policy.

### P1

#### P1-001 Full Scientific Spaces Corpus Processing Plan

- Title: Controlled full-corpus processing.
- Motivation: The MVP validates RSS discovery and article access on bounded samples, but v1.1 should define how to process more of the corpus safely.
- Scope: Define bounded RSS/backfill strategy, respectful request limits, checkpointing, duplicate handling, content-fidelity reporting, and validation summaries.
- Acceptance criteria: A dry-run mode reports discovered/importable article counts; repeated runs remain idempotent; validation reports summarize content completeness, formulas, images, and references; no uncontrolled crawl is introduced.
- Risks: Source site changes, access limits, RSS coverage gaps, browser runtime instability, and storing excessive raw content.
- Dependencies: M1 source pipeline, browser acquisition quality gate, validation reports, source access policy.

#### P1-002 Real Provider Configuration Hardening

- Title: Harden OpenAI-compatible and Zotero provider configuration.
- Motivation: Real providers are optional today; users need clear diagnostics, cost/rate guardrails, and graceful failure behavior.
- Scope: Add provider configuration checks, runtime status diagnostics, retry/rate-limit policy, cost-control documentation, and clearer fallback paths.
- Acceptance criteria: Misconfigured provider states return actionable errors; tests still run with fake providers; real-provider paths are opt-in; no API keys are logged or committed.
- Risks: Provider API drift, accidental real-provider usage in CI, and leaking sensitive configuration.
- Dependencies: M3 provider interfaces, M7 tutor provider selection, M5 local Zotero provider.

#### P1-003 Knowledge Graph Scaling and Provenance UX

- Title: Scale graph output and make provenance easier to inspect.
- Motivation: M6 graph provenance is stable, but larger corpora will require filtering, pagination, clustering, and clearer source trails.
- Scope: Add graph pagination/filtering plans, concept provenance browsing improvements, large-graph performance checks, and graph store corruption/concurrency handling.
- Acceptance criteria: Large fixture graph remains responsive; concept nodes expose provenance without full article bodies; UI can filter by node type and inspect evidence; graph output stays deterministic.
- Risks: Graph visualization performance, provenance truncation confusion, storage concurrency, and over-eager concept extraction.
- Dependencies: M6 graph model, M6.1 provenance metadata, frontend graph view.

#### P1-004 Zotero Real-Library Integration Hardening

- Title: Improve read-only Zotero real-library reliability.
- Motivation: M5 supports optional local Zotero access, but real-library workflows need stronger diagnostics and safer export behavior.
- Scope: Add local API availability diagnostics, collection/tag browsing hardening, BibTeX export result clarity, link-store backup guidance, and documentation for read-only boundaries.
- Acceptance criteria: Zotero unavailable state is clear; missing export entries report exported count or explicit errors; no Zotero writes are added; user setup docs cover Desktop/API prerequisites.
- Risks: Local Zotero profile differences, connector availability, metadata privacy, and accidental write expectations.
- Dependencies: M5 provider protocol, local API helper, Zotero link store.

#### P1-005 UI / UX Polish

- Title: Improve reader, graph, Zotero, and tutor usability without expanding scope.
- Motivation: The MVP is usable, but repeated learning workflows need better loading, empty, error, and source-inspection states.
- Scope: Polish responsive layouts, loading/error states, citation panels, article/tutor navigation, graph provenance display, and dashboard summaries.
- Acceptance criteria: Core routes remain responsive on desktop and mobile; long titles/content do not break layout; source/citation affordances are consistent; frontend build and smoke tests pass.
- Risks: UI churn, accidental scope expansion into new learning algorithms, and regressions in existing route behavior.
- Dependencies: `docs/10_UI_SPEC.md`, existing Next.js routes and shared components.

#### P1-006 Documentation and Onboarding Cleanup

- Title: Make onboarding and project boundaries easier to follow.
- Motivation: Release audit found missing acceptance/boundary docs, and new contributors need a clear entry path.
- Scope: Add or restore acceptance and MVP boundary docs, write troubleshooting notes, add architecture map, and document local data cleanup.
- Acceptance criteria: Setup, test, provider, Docker, live-source, and release workflows are discoverable from README; missing-doc gaps are resolved; docs do not contradict verification reports.
- Risks: Documentation drift and accidental changes to milestone requirements after release.
- Dependencies: README, release audit, milestone reports, verification reports.

### P2

#### P2-001 Advanced Tutor Evaluation and Mode Refinement

- Title: Deepen tutor quality after the evaluation harness exists.
- Motivation: Tutor modes need quality iteration, but only after baseline evaluation can detect regressions.
- Scope: Add larger curated question sets, stricter derivation checks, richer quiz grading criteria, and research-mode source-gap summaries.
- Acceptance criteria: Evaluation reports mode-specific scores; unsupported derivations refuse; quiz questions remain source-tied; research answers state evidence gaps.
- Risks: Subjective scoring, provider variability, and moving beyond grounded local sources.
- Dependencies: P0-005 RAG and tutor evaluation harness.

#### P2-002 Multi-User Readiness Planning

- Title: Plan auth and multi-user separation after security and persistence baselines.
- Motivation: Multi-user launch should not happen until storage, privacy, and auth boundaries are explicit.
- Scope: Define user identity, per-user data isolation, auth provider options, authorization checks, and migration implications.
- Acceptance criteria: Auth/storage ADR exists; no production multi-user deployment proceeds without data isolation tests.
- Risks: Privacy leaks, overbuilding auth too early, and breaking local-first usage.
- Dependencies: P0-002 persistence upgrade and P0-004 security/privacy baseline.

#### P2-003 Observability and Diagnostics

- Title: Add local-first operational diagnostics.
- Motivation: Browser acquisition, providers, graph builds, and tutor evaluation need clear operational visibility.
- Scope: Add structured logs, diagnostic endpoints or commands, run summaries, and failure-reason reporting.
- Acceptance criteria: A failed sync, provider call, graph build, or tutor request produces a useful diagnostic without exposing secrets or private data.
- Risks: Logging sensitive data and adding production monitoring before deployment shape is stable.
- Dependencies: Deployment profile, provider hardening, source pipeline reports.

#### P2-004 Export and Sharing Improvements

- Title: Improve safe export paths for study artifacts.
- Motivation: Users may want notes, citations, PDFs, or graph summaries, but exports must preserve privacy and source integrity.
- Scope: Define safe export formats, citation metadata, optional PDF generation workflow, and cleanup rules.
- Acceptance criteria: Exports exclude secrets/runtime-private data; generated artifacts are ignored by git; citations remain attached to exported learning material.
- Risks: Accidental artifact commits, copyrighted content handling, and privacy leakage.
- Dependencies: M1 PDF export capability, M4 learning state, M5 Zotero links.

#### P2-005 Performance Benchmarking

- Title: Benchmark larger data sets before broad corpus or graph expansion.
- Motivation: Larger article sets may stress storage, graph rendering, FAISS indexing, and browser processing.
- Scope: Add benchmark fixtures, measure sync/import/search/RAG/graph/tutor response times, and define acceptable thresholds.
- Acceptance criteria: Benchmark command runs locally with generated fixtures; report identifies bottlenecks and recommended limits.
- Risks: Synthetic benchmarks not matching real corpus behavior and premature optimization.
- Dependencies: Persistence upgrade, corpus-processing plan, graph scaling work.

## Recommended First Post-MVP Sprint

Timebox: 1 to 2 weeks.

Sprint goal: make v1.1 foundations safer and more repeatable without expanding product scope.

Recommended work:

1. CI and release automation hardening.
   - Add push/tag CI coverage where appropriate.
   - Keep manual release evidence available.
   - Document release checklist and changelog rules.
2. Persistence upgrade ADR.
   - Choose SQLite or Postgres as the first durable store target.
   - Define migration and backup strategy.
   - Select one store for a small first migration.
3. RAG and tutor evaluation harness.
   - Create a curated evaluation set.
   - Track citation quality, no-source refusal, formula handling, and tutor mode behavior.
4. Security and privacy baseline.
   - Write threat model and data-handling rules.
   - Define production blockers for auth, secrets, and runtime data.
5. Documentation cleanup.
   - Resolve missing acceptance and MVP-boundary documentation gaps.
   - Make setup, provider, release, and troubleshooting paths easier to follow.

Sprint deliverables:

- CI/release automation revision or ADR.
- Persistence ADR and first migration plan.
- Initial RAG/tutor evaluation report.
- Security/privacy baseline document.
- Updated onboarding and missing-boundary documentation.

## Do Not Do Yet

- Do not perform uncontrolled web-scale crawling.
- Do not launch production multi-user access before auth, privacy, and persistence boundaries are implemented.
- Do not add an ungrounded autonomous AI research agent.
- Do not allow automatic Zotero library writes.
- Do not extract graph facts through hallucination-prone methods without source evidence and provenance.
- Do not make real paid AI providers the default in tests or CI.
- Do not run full-corpus processing without rate limits, checkpoints, and content-quality reports.
- Do not perform destructive JSON-to-database migration without backup and rollback guidance.
- Do not move the `v1.0.0` tag or rewrite the GitHub Release for roadmap work.

## Release Strategy

v1.1.0 should focus on operational maturity rather than new headline features:

- Deployment hardening.
- Persistence upgrade.
- CI/release automation.
- Security/privacy baseline.
- RAG and tutor evaluation.
- Corpus-processing plan.
- Documentation cleanup.

Patch releases:

- Use `v1.0.x` for urgent documentation, CI, packaging, security, or compatibility fixes.
- Avoid schema or user-visible feature changes in patch releases unless they are required to fix a critical issue.

CI gating:

- PR gates should include backend pytest and frontend build.
- Main and release-tag gates should include backend pytest, frontend build, and Docker compose smoke when runner support is available.
- Release evidence should record workflow run URL, ref/tag, conclusion, and checks covered.
- Evaluation smoke should become a release gate once the P0 evaluation harness is stable.

Changelog discipline:

- Each release should link to release notes, release CI evidence, and verification or audit reports.
- Each release should summarize added capabilities, changed contracts, known limitations, and migration steps.
- Tags should be treated as immutable. Use fix-forward releases instead of moving tags.

