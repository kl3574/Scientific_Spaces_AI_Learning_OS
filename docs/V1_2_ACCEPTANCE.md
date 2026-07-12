# v1.2 Acceptance Gates

Status: Approved planning gates

Scope Decision: **A**

Commands marked **planned** are contracts for future milestones and are not current implemented CLIs.

## Global Status Rules

### PASS

- Every mandatory entry condition and command passes.
- Required reports and manifests are complete and internally consistent.
- No unresolved Critical or Important finding, frozen-contract regression, secret, private/runtime artifact, silent drop, Article mutation, unexpected network call, or automatic Zotero write remains.
- The next dependent milestone may begin under a new confirmed task alignment.

### CONDITIONAL

- Core evidence is valid, but one or more explicit, bounded non-critical decisions or accepted limitations remain.
- Every condition has owner, remediation, expiry/decision gate, and affected milestone.
- No dependent implementation milestone may begin when its required predecessor is CONDITIONAL.
- CONDITIONAL cannot hide failed data integrity, compatibility, security, consent, artifact, or release identity checks.

### BLOCKED

- Required evidence is missing or failed; scope/data/security/compatibility cannot converge; or a prohibited action/artifact occurred.
- Stop dependent work. Preserve evidence, classify the blocker, and create a separately aligned revision task.

## Frozen Compatibility Matrix

| Surface | Frozen behavior | v1.2 rule | Verification |
| --- | --- | --- | --- |
| v1.0 Article list | `GET /articles`, only `q`, exact keys/order and unbounded legacy result semantics | No new parameters/keys/defaults; references use `/v1.2` | Existing Article API contract tests and OpenAPI snapshot |
| v1.0 Article detail | `GET /articles/{id}` returns `id,title,url,content,metadata` | No reference payload injection or Article mutation | Exact response fixture and corpus fingerprint |
| v1.0 Graph | Legacy `/graph`, nodes, neighbors/path/subgraph/build contracts | No storage/query semantic change | Existing legacy Graph tests |
| `/v1.1/articles` | Bounded page/filter/sort contract, max page size 100 | Unchanged | Existing versioned Article tests/OpenAPI |
| `/v1.1/graph/*` | Bounded summary/nodes/subgraph filters and response fields | Unchanged | Existing versioned Graph tests/OpenAPI |
| M3 RAG | Citation source identity and no-source refusal | Reference data is supplemental only; cannot replace Article grounding | RAG API/evaluation regressions |
| M4 Learning | Learning state/bookmark/note/session API and persistence behavior | No schema/API change | Learning JSON/SQLite tests |
| M5 Zotero | Provider reads metadata; local project links are explicit; unavailable provider is nonfatal | Matcher is read-only and never auto-writes provider, links, or review decisions | Zotero API/provider tests plus matcher write-denial test |
| M6 Graph | Provenance/evidence/source-count and bounded context contracts | References do not rewrite Graph or provenance | Graph integrity/provenance tests |
| M7 Tutor | Article-grounded citations, bounded evidence, `no_sources`/Derive refusal | Provider evaluation cannot change default fake provider or refusal behavior | Tutor/evaluation regressions |
| Persistence | JSON Learning default, SQLite opt-in | No default change; Reference Tier 2 JSONL and Tier 1 decisions are independent | Config/migration tests |
| Migration/rollback | Explicit JSON<->SQLite migration/export with atomic failure handling | Existing path unchanged; new stores use separate staged lifecycle | Existing migration plus future reference failure injection |
| Backup/restore/cleanup | Tier 1 protected, Tier 2 rebuildable, cleanup bounded/dry-run | Review decisions become Tier 1 before use; derived reference store Tier 2 | Operations inventory/backup/cleanup tests |

Any future write to `metadata.references` is outside this matrix and requires a separate M1.x governance task, Article-store backup, atomic migration, reverse rollback, and full compatibility audit.

## P3-002 Requirement Traceability

| # | Required decision | Approved evidence |
| ---: | --- | --- |
| 1 | Approve/reject all three themes | Scope Decision A in PRD and roadmap |
| 2 | Explicit non-goals | `docs/V1_2_PRD.md` Non-Goals and Deferred Scope |
| 3 | Complete `ReferenceRecord` | `docs/V1_2_DATA_MODEL.md` |
| 4 | Complete Reference Store lifecycle | Architecture plus ADR 0006 |
| 5 | Complete provenance/duplicate rules | Data model, architecture, and evaluation thresholds |
| 6 | No automatic Zotero write | PRD, architecture, threat model, ADR 0006 |
| 7 | Provider consent/data/cost boundary | Architecture, evaluation plan, ADR 0007 |
| 8 | Complete CI security policy | Architecture, acceptance, ADR 0008 |
| 9 | Complete scoped threat model | `docs/V1_2_THREAT_MODEL.md` |
| 10 | Complete compatibility matrix | Frozen Compatibility Matrix above |
| 11 | Migration/rollback | Architecture, data model, ADR 0006-0008 |
| 12 | Milestones/dependencies | Execution plan and dependency graph |
| 13 | PASS/CONDITIONAL/BLOCKED per milestone | P3-002 through P3-007 gates below |
| 14 | No unresolved critical ambiguity | P3-002 PASS gate and future approval list |
| 15 | No implementation/candidate declaration | Git diff/audit gate; formal version remains v1.1.0 |

## P3-002 Product Requirements and Architecture

### Entry Criteria

- Formal version is `v1.1.0`; candidate is not assigned.
- P3-001 is on `origin/main`; Backend/Frontend CI passed and Docker was correctly skipped for main push.
- `main == origin/main`, worktree initially clean, and `v1.1.0^{}` remains `3efbe2a792a9853f1bac456f0287c3b5b62713ce`.
- Required documents/code boundaries are read; `REWORK.md` and `.audit` have no open blocker.

### Required Commands

```bash
git fetch origin --tags
git status
git rev-parse HEAD
git rev-parse origin/main
git rev-parse v1.1.0^{}
uv run --project backend --extra dev pytest -q
cd frontend && npm run build
git diff --check
```

Also required: documentation path/schema/API/milestone/version consistency checks and tracked artifact/secret scans.

### PASS

- Scope Option A/B/C is explicit; every included theme has a complete product, data, security, lifecycle, and evaluation contract.
- All 15 P3-002 attachment criteria pass.
- No critical ambiguity, implementation, candidate declaration, external/private call, or forbidden artifact exists.
- Backend tests and Frontend build pass.

### CONDITIONAL

- Direction is bounded but a finite architecture decision remains and is listed with owner/decision deadline.
- P3-003 cannot begin.

### BLOCKED

- Scope cannot be selected; frozen compatibility, data identity, privacy, consent, or CI provenance is unresolved; or baseline tests/build/audit fail.

### Required Reports

- Seven v1.2 specifications, ADR 0006-0008, updated roadmap/state/README planning links, and approved `alignment.md`.

### Forbidden Artifacts/Actions

- Any product code, full reference output, provider/Zotero private data, candidate version, push, tag, Release, or external write.

### Regression Requirements

- Complete current Backend suite and Frontend production build.

## P3-003 Structured Reference Extraction Pilot

### Entry Criteria

- P3-002 PASS with Scope Decision including Structured References.
- Approved schemas, normalization/deduplication, trust boundaries, and Reference Store ADR remain current.
- Explicit local pilot Article store is available and backed up; no full-corpus run is authorized.

### Required Commands

Planned:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_reference_*.py
uv run --project backend python scripts/references/run_reference_pilot.py \
  --article-store <ignored-store> --sample-size 75 \
  --output-dir .local_data/scientific_spaces/references/pilot --no-network
uv run --project backend --extra dev pytest -q
cd frontend && npm run build
```

### PASS

- At least 60 fixtures and a deterministic 50-100 Article pilot complete.
- Normalization, required classification, expected deterministic deduplication, provenance, index integrity, no-network, no-mutation, no-silent-drop, idempotency, and failure rollback meet `docs/V1_2_EVALUATION_PLAN.md` thresholds.
- Fake/unavailable Zotero behavior passes and no write occurs.

### CONDITIONAL

- Deterministic integrity passes but human-reviewed strong-identifier precision is below 95% or bounded corpus syntax requires a finite rule review.
- P3-006 cannot begin; record exact cases and plan P3-003.x.

### BLOCKED

- Article mutation, wrong exact identity, false exact Zotero match, provenance loss, silent drop, network access, corrupt/partial install, frozen regression, or test/build failure.

### Required Report

- `docs/P3_003_STRUCTURED_REFERENCE_PILOT_REPORT.md` with fixture matrix, pilot IDs/strata, metrics, human review, resource usage, no-network evidence, fingerprints, and artifact audit.

### Forbidden Artifacts/Actions

- Full corpus build, Article body fixtures/exports, `metadata.references` write, private Zotero read/export, remote lookup, product default change.

### Regression Requirements

- Frozen Article/M1 checks, full Backend suite, Frontend build, existing RAG/Graph/Tutor/Zotero tests.

## P3-004 Real Provider Evaluation Design

### Entry Criteria

- P3-002 PASS with Real Provider Evaluation included.
- ADR 0007, schemas, case taxonomy, consent, redaction, retention, and budgets are accepted.
- No real credential or private user dataset is required.

### Required Commands

Planned:

```bash
uv run --project backend --extra dev pytest -q backend/tests/test_real_provider_evaluation_*.py
uv run --project backend python scripts/eval/run_real_provider_eval.py \
  --provider fake --case-set <planned-fixture> --dry-run \
  --output-dir .local_data/scientific_spaces/evaluation/real_provider/dry-run
uv run --project backend --extra dev pytest -q
cd frontend && npm run build
```

### PASS

- Fake/dry-run proves consent fail-closed, request/cost/context/output/retry bounds, request-envelope allowlist, prompt-injection treatment, redaction, retention/deletion, artifact scan, and zero network access.
- Fake providers remain default in runtime and CI.
- Reports distinguish heuristics from human correctness.

### CONDITIONAL

- Adapter/report design passes but a named provider lacks immutable version or usage metadata; limitation is explicit and does not enable a call.
- No real evaluation may run until separately approved.

### BLOCKED

- A real call occurs without new authorization; consent/budget can be bypassed; secrets/private data can be logged/sent; CI/default can select real; or regression fails.

### Required Report

- `docs/P3_004_REAL_PROVIDER_EVALUATION_DESIGN_REPORT.md` with dry-run matrix, request schema, consent/budget failures, redaction/retention, and zero-network evidence.

### Forbidden Artifacts/Actions

- API key, auth header, real/paid request, raw provider output by default, private Zotero/user data, CI provider call.

### Regression Requirements

- M3/M7 fake-provider, citation, grounding, refusal, and existing evaluation suites remain unchanged.

## P3-005 CI Security and Release Provenance

### Entry Criteria

- P3-002 PASS with CI Security included.
- Baseline backend/frontend main CI is green; current tag/manual Docker policy is known.
- ADR 0008, severity/suppression policy, SBOM format, and permission matrix are accepted.

### Required Commands

Implementation selects and pins exact tool versions. Gate commands must include:

```bash
uv run --project backend --extra dev pytest -q
cd frontend && npm ci && npm run build
docker compose up --build -d
# backend/frontend smoke, then docker compose down --volumes --remove-orphans
# planned immutable-pin, permission, suppression, dependency, secret, SBOM, and attestation policy checks
```

Tag/manual Docker may be evidenced by GitHub Actions when local Docker is unavailable.

### PASS

- Every third-party Action is pinned by full SHA; least permissions match ADR 0008.
- Python and npm plus independent lockfile scanning execute under the severity policy.
- Secret scan and suppression validator pass without printing secrets.
- CycloneDX SBOM is valid, <=5 MiB, covers both lockfiles, and contains no forbidden path/data.
- Test attestation binds an approved non-private subject to exact ref/SHA; release instructions are executable.
- Backend, Frontend, and required Docker jobs pass.

### CONDITIONAL

- GitHub-hosted feature availability prevents attestation publication in a non-release dry run, while local subject/digest/provenance validation passes and exact release gate is explicitly blocked pending availability.
- Candidate/release cannot proceed without final exact-tag evidence.

### BLOCKED

- Mutable Action remains; write permission is overbroad; unsuppressed Critical/High/secret finding remains; scanner fails open; suppression is invalid; SBOM/provenance mismatches or leaks private data; baseline CI regresses.

### Required Report

- `docs/P3_005_CI_SECURITY_PROVENANCE_REPORT.md` with pin map, permission matrix, scanner results, suppression audit, SBOM digest/content audit, attestation evidence, and branch-protection guidance.

### Forbidden Artifacts/Actions

- Runtime corpus/data in CI artifact, broad write token, package publication, untrusted PR attestation, secret value in logs, automatic repository-setting changes.

### Regression Requirements

- Existing backend/frontend jobs on PR/main and Docker on manual/tag remain functionally equivalent or stricter.

## P3-006 Structured Reference Full-Corpus Build and Zotero Matching

### Entry Criteria

- P3-003 PASS; no open reference integrity/precision blocker.
- Full-corpus run is separately authorized, Article store is validated/backed up, and sufficient capacity exists.
- P3-005 security policy should be merged before full integration; absence is recorded as a dependency blocker for P3-007.

### Required Commands

Planned:

```bash
uv run --project backend python scripts/references/build_full_corpus_references.py \
  --article-store <ignored-full-store> \
  --output-dir .local_data/scientific_spaces/references/full_corpus \
  --no-network --rebuild
# repeat unchanged command for validated no-op
uv run --project backend python scripts/references/audit_reference_store.py \
  --reference-store .local_data/scientific_spaces/references/full_corpus
uv run --project backend --extra dev pytest -q
cd frontend && npm run build
```

### PASS

- Every validated Article has a terminal processing status; all candidates reconcile.
- Provenance, identifiers, counts, indexes, checksums, fingerprints, no-network, no-mutation, and no-op integrity pass.
- Corruption and install failure recover the previous valid store.
- Fake/curated Zotero matching passes; an unavailable real local provider is nonfatal.
- No private library is required or exported.

### CONDITIONAL

- Extraction store passes, but optional private Zotero matching was not authorized/available. This is an accepted local integration limitation, not extraction failure; P3-007 must state whether fake matching is sufficient for release scope.

### BLOCKED

- Input Article unclassified, candidate silent drop, invalid exact identity, provenance loss, Article mutation, network access, corrupt install, non-idempotency, private data leak, or regression.

### Required Report

- `docs/P3_006_FULL_CORPUS_REFERENCE_REPORT.md` with input fingerprint/count, classifications, normalization/dedup/provenance metrics, store integrity/idempotency, matching state, resource usage, and artifact audit.

### Forbidden Artifacts/Actions

- Committed reference store/corpus, source fetch, automatic/manual-unapproved Zotero write, private library export, M1 change.

### Regression Requirements

- Full Backend/Frontend and frozen compatibility suites; operations inventory must classify Reference Store Tier 2 and decisions Tier 1.

## P3-007 v1.2 Integration and Release Readiness

### Entry Criteria

- P3-003, P3-004, P3-005, and P3-006 are PASS, or the release board explicitly resolves an allowed P3-006 optional-Zotero CONDITIONAL without weakening mandatory gates.
- All required reports, migrations, rollback evidence, and artifact policies are current.
- Candidate version remains unassigned until this gate passes and the user separately authorizes release metadata.

### Required Commands

- Full Backend suite and Frontend build/tests.
- Manual Docker compose smoke and later exact-tag Docker CI.
- Frozen compatibility, RAG/Tutor, Learning persistence/migration, backup/restore/cleanup, Reference Store/API/UI, fake/dry-run provider, scanner/SBOM/provenance, docs, Git, artifact, and secret checks.
- Exact commands must be recorded in `docs/P3_007_V1_2_RELEASE_READINESS_REPORT.md` and correspond to implemented CLIs at that time.

### PASS

- All mandatory workstreams and compatibility/security/data gates pass with no Critical/Important finding.
- SBOM/provenance is clean and exact-subject verification is ready.
- No runtime/private artifact is tracked or proposed for Release.
- The gate may recommend a candidate; candidate assignment/tag/Release still require separate authorization.

### CONDITIONAL

- Only an explicit non-critical external availability limitation remains, with release action blocked until exact evidence is obtained.

### BLOCKED

- Any mandatory predecessor/gate fails, compatibility changes, real-provider/default/privacy boundary weakens, release evidence is forged/mismatched, or artifact/secret policy fails.

### Required Report

- `docs/P3_007_V1_2_RELEASE_READINESS_REPORT.md` with requirement traceability, findings, exact commands/results, candidate recommendation, and release stop conditions.

### Forbidden Artifacts/Actions

- Tag/Release without separate authorization; moved prior tag; runtime/private artifact; silent gate waiver.

### Regression Requirements

- All released v1.0/v1.1 contracts and complete current CI matrix.

## Dependency Graph

```text
P3-002
  ├── P3-003 ──> P3-006 ──┐
  ├── P3-004 ──────────────┤
  └── P3-005 ──────────────┤
                            └──> P3-007
```

P3-003, P3-004, and P3-005 may proceed independently after P3-002 under separate task alignments. P3-006 requires P3-003. P3-007 requires all workstream evidence.

## Global Forbidden Artifact Pattern

Gates scan for tracked `.env`, keys, SQLite/database files, corpus/reference stores, PDF/HTML/images, archives/backups/restores, RAG/FAISS/Graph data, provider raw output, traces/profiles/caches, `.next`, `node_modules`, and local absolute paths. A real hit is BLOCKED; test fixture false positives require a narrow documented review, never silent exclusion.
