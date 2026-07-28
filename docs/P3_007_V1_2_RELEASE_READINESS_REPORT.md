# P3-007 v1.2 Integration and Release Readiness Report

## Status

- P3-007: **CONDITIONAL / RISK ACCEPTED / CLOSED**
- Formal version: `v1.1.0`
- Candidate version: Not assigned
- Product integration: Complete and pushed
- GitHub Actions validation: Complete
- Tag, Release, or attestation publication: Not performed

The highest permitted result is conditional because the product owner reviewed
three pilot cases and explicitly waived the remaining 61 formal review cases.
This report does not claim 64/64 review completion or measured precision
greater than or equal to 0.95.

## Baseline

- Branch: `main`
- Baseline HEAD and local tracking `origin/main`:
  `d6f6f3eefdf5d54bae93727647cab51a4236a3fb`
- Baseline ahead / behind: `0 / 0`
- REWORK / FAIL audit: absent
- Baseline CI:
  [`30337284957`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30337284957),
  SUCCESS

The baseline CI passed Backend pytest, Frontend build, dependency audit,
secret audit, workflow policy, and SBOM validation. Docker and release
evidence were correctly skipped for that normal `main` push.

## Remote CI Closure Evidence

Implementation commit:
`a88e27e65b1a244f6ca038e1b358ed50b348be17`.

| Run | Trigger | Exact SHA | Result |
| --- | --- | --- | --- |
| [`30341443480`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30341443480) | `push` on `main` | `a88e27e65b1a244f6ca038e1b358ed50b348be17` | SUCCESS |
| [`30341652046`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/30341652046) | `workflow_dispatch` on `main` | `a88e27e65b1a244f6ca038e1b358ed50b348be17` | SUCCESS |

The normal push run passed Backend pytest, Frontend build, workflow policy,
dependency audit, secret audit, and SBOM validation. Docker compose smoke and
release-evidence dry-run were skipped by the intended push policy.

The manual run passed all of those checks plus Docker compose build/start,
Backend health, Frontend home-page smoke, service cleanup, and the no-publish
release-evidence dry-run. It produced zero workflow artifacts.

GitHub Actions emitted a non-blocking maintenance warning that selected pinned
versions of `actions/checkout` and `actions/setup-python` target Node.js 20 and
are currently forced to Node.js 24. The actions remained immutable-pinned and
all jobs passed.

Remote tag evidence remained unchanged:

- `v1.0.0` peeled target:
  `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6`
- `v1.1.0` peeled target:
  `3efbe2a792a9853f1bac456f0287c3b5b62713ce`

## Risk Decision

ADR 0009 records the repository product owner's decision:

- reviewed and approved cases: exactly 3;
- formal review cases waived: exactly 61;
- measured strong-identifier precision: unavailable;
- P3-006 status: `CONDITIONAL / RISK ACCEPTED / CLOSED`;
- P3-007 maximum status: `CONDITIONAL / RISK ACCEPTED`; and
- Scientific Spaces Zotero full-text children must be browser-printed PDFs,
  not HTML snapshots.

Any future candidate decision must carry this limitation explicitly. Completing
P3-006.1 remains the remediation path if statistical human-review evidence is
later required.

## Integration Delivered

### Backend

A read-only Reference Store adapter:

- validates manifest, checksums, schema, corpus freshness, and optional
  configuration fingerprint before serving;
- caches only a validated immutable snapshot;
- returns bounded missing, stale, and corrupt states;
- allowlists public record, evidence, candidate, provenance, and summary
  fields; and
- never rebuilds or writes during an API request.

The following additive endpoints are implemented:

| Endpoint | Bounds and behavior |
| --- | --- |
| `GET /v1.2/references` | page >= 1, page size 1-100, bounded query and filters |
| `GET /v1.2/references/{reference_id}` | 200-character ID cap, provenance 1-20 |
| `GET /v1.2/articles/{article_id}/references` | 200-character ID cap, paginated |
| `GET /v1.2/references/{reference_id}/zotero-candidates` | limit 1-20, read-only decision filter |
| `GET /v1.2/reference-summary` | numeric count tree only, no paths or rebuild command |

Unknown IDs return 404. Missing, stale, or corrupt stores fail closed with a
bounded 503 response.

### Frontend

- Article Detail renders Structured References with loading, empty, error,
  stale/corrupt, safe-link, source-count, and pagination states.
- The Zotero view renders read-only exact/probable, ambiguous/rejected, and
  unmatched candidate filters without writing Zotero or review decisions.
- HTTP links reject credentials and non-HTTP schemes; DOI and arXiv links are
  generated from normalized identifiers.
- Desktop and 390 px mobile Playwright checks found no incoherent overlap.

### Operations

- `references/full-corpus/current` is classified as rebuildable Tier 2.
- `references/reviewed/decisions.json` is classified as private essential
  Tier 1.
- Inventory, essential/complete backup, restore verification, health, capacity,
  and cleanup policies cover both assets.
- Missing/stale/corrupt derived stores are rebuildable warnings.
- Malformed review decisions are blocking essential-data failures.
- Cleanup protects review decisions and may select only the derived Reference
  Store for stale-data cleanup.

## Compatibility and Scope

- Legacy `/articles` and `/v1.1/articles` OpenAPI parameters are unchanged.
- M1, Article Store payload/schema, Reference Store payload/schema, Graph
  storage, provider defaults, and M3-M7 contracts are unchanged.
- No real Provider, paid request, source-site request, private Zotero
  read/write, or full-corpus build/rebuild occurred.
- The fake provider remained the default and its dry-run recorded zero external
  network requests.

## Test Evidence

| Gate | Result |
| --- | --- |
| Focused Reference API | PASS, 10 tests |
| Focused operations | PASS, 35 tests |
| Full Backend | PASS, 573 passed and 3 skipped |
| Frontend Article client | PASS, 3 tests |
| Frontend Reference client | PASS, 3 tests |
| Frontend Graph client | PASS, 8 tests |
| Frontend Tutor client | PASS, 13 tests |
| Frontend production build | PASS, Next.js 15.5.21, 8 pages |
| Browser Article reference API | PASS, HTTP 200 |
| Browser Zotero candidate API | PASS, HTTP 200 |
| Fake-provider dry-run | PASS, 15 cases, 0 external network requests |
| Fake-provider output audit | PASS, 0 findings |
| Workflow policy | PASS, 16/16 immutable pins and permission checks |
| Suppression policy | PASS, 0 dependency and 0 secret suppressions |
| Dependency audit | PASS, 40 Python and 219 npm components, 0 findings |
| Secret audit | PASS, 0 credible findings |
| SBOM build/validation | PASS, 40 Backend, 219 Frontend, 261 combined |
| SBOM forbidden-artifact scan | PASS, 0 findings |
| No-publish release-evidence dry-run | PASS |
| Offline release-evidence verification | PASS |
| Local Docker compose smoke | NOT RUN, `docker` is unavailable |
| Implementation main-push CI | PASS, run `30341443480` |
| Exact-SHA manual CI | PASS, run `30341652046` |
| Remote Docker compose smoke | PASS |
| Remote no-publish release-evidence dry-run | PASS |
| Workflow artifact count | PASS, 0 |

Commands:

```bash
uv run --project backend --extra dev pytest -q
uv run --project backend --extra dev pytest -q backend/tests/test_reference_api.py
cd frontend && npm run test:articles
cd frontend && npm run test:references
cd frontend && npm run test:graph
cd frontend && npm run test:tutor
cd frontend && npm run build
docker compose up --build -d
python scripts/security/check_workflow_policy.py
python scripts/security/validate_suppressions.py
python scripts/security/run_dependency_audit.py
python scripts/security/run_secret_audit.py
python scripts/security/build_sbom.py \
  --output-dir /tmp/scientific-spaces-p3-007-sbom.XgS5Rv
python scripts/security/validate_sbom.py \
  /tmp/scientific-spaces-p3-007-sbom.XgS5Rv
python scripts/release/build_release_evidence.py \
  --tag v1.1.0 \
  --sbom-dir /tmp/scientific-spaces-p3-007-sbom.XgS5Rv \
  --dry-run \
  --no-publish
python scripts/release/verify_release_evidence.py \
  --evidence /tmp/scientific-spaces-p3-007-sbom.XgS5Rv/release-evidence.json \
  --no-network
uv run --project backend python scripts/eval/run_real_provider_eval.py \
  --provider fake \
  --case-set backend/tests/fixtures/evaluation/provider_cases.json \
  --dry-run \
  --output-dir .local_data/scientific_spaces/evaluation/real_provider/dry-run
uv run --project backend python scripts/eval/audit_real_provider_eval.py
```

The local Docker limitation was closed by exact-implementation remote CI.
Current-change GitHub Actions and Docker evidence are now available. The
closure documentation commit still requires its normal post-push CI
confirmation.

## Artifact and Privacy Evidence

- Temporary Playwright snapshots, fake-provider output, UI fixture data, SBOMs,
  and release-evidence files were removed after validation.
- No PDF, HTML dump, image, trace, profile, cache, runtime store, database,
  private Zotero export, full Reference Store, or secret is intended for the
  commit.
- The literal `/home/private/library` exists only as a negative API allowlist
  test sentinel; the test proves it is absent from the public response.
- The Zotero PDF-only policy is governance evidence only; this task did not
  access or modify the private Zotero library.

## Known Limitations

- Only 3 of 64 formal human-review cases were reviewed; 61 were explicitly
  waived.
- Human-review precision is not measured.
- Exact full-corpus quality remains machine-verified but not statistically
  human-verified.
- The derived Reference Store must be rebuilt when its corpus or configuration
  fingerprint changes.
- Local Docker remains unavailable; exact-implementation Docker evidence comes
  from the successful manual GitHub Actions run.
- Pinned third-party Actions currently produce a Node.js 20 deprecation
  warning while GitHub forces execution on Node.js 24.

## Candidate Recommendation

**CONDITIONAL - no candidate is assigned.**

The push and current-commit CI prerequisites are complete. Candidate selection
remains a separate P3-008 decision and must explicitly carry ADR 0009's
accepted review limitation.

## Final Decision

P3-007 implementation, remote synchronization, exact-commit CI, and Docker
evidence are complete.

Status: **CONDITIONAL / RISK ACCEPTED / CLOSED**

Next recommended task:
`P3-008 v1.2 Candidate Decision`
with `ALIGNMENT REQUIRED / NOT GRANTED`.
