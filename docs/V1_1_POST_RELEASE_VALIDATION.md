# v1.1.0 Post-Release Validation

Validation date: 2026-07-12

## Current Status

- Release: `v1.1.0`
- Tag validation: **PASS**
- Fresh clone validation: **PASS**
- Release installation and default startup: **PASS**
- Recommendation: **A: No v1.1.1 required**

The published tag installs and runs without the developer workspace, a local corpus, an API key, or pre-existing runtime data. No Critical or Important post-release finding was found.

## Release Identity

| Evidence | Value |
|---|---|
| Annotated tag | `v1.1.0` |
| Tag object type | `tag` |
| Tag object SHA | `d136eb1de7217a014913f83cf6b08344a5f0d61d` |
| Peeled release commit | `3efbe2a792a9853f1bac456f0287c3b5b62713ce` |
| Post-release evidence commit | `6f887fb780cfac7916e341eb92eb9a400d4bf6df` |
| `v1.0.0` peeled target | `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6` |
| GitHub Release | <https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/releases/tag/v1.1.0> |
| Exact-tag CI | <https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/29158711141> |

Local and remote tag object/peeled references matched. The GitHub Release is neither draft nor prerelease and has no attached runtime assets. No tag or release was modified during this validation.

## Fresh Clone Environment

The repository was cloned from GitHub to `/tmp/scientific-spaces-v1.1.0-validation` and checked out with detached `HEAD` at the exact tag.

| Item | Result |
|---|---|
| OS | Ubuntu Linux, kernel `7.0.0-27-generic` |
| Architecture | `x86_64` |
| System Python | `3.10.20` |
| Project Python selected by uv | `3.11.15` |
| uv | `0.11.21` |
| Node.js | `22.22.1` |
| npm | `11.4.2` |
| Docker CLI | Not installed in the local validation environment |
| Initial worktree | Clean, detached at `v1.1.0` |

The initial clone contained no `.local_data`, `.env`, `node_modules`, `.next`, virtual environment, database, PDF, corpus, RAG index, Graph, or browser artifact. Dependencies were installed only inside the disposable clone.

## Backend Installation

Command:

```bash
uv run --project backend --extra dev pytest -q
```

uv selected CPython 3.11.15, created an isolated `backend/.venv`, built the local package, and installed 40 packages. The hardlink-to-copy uv warning was an environment/filesystem optimization warning and did not affect correctness.

## Backend Tests

- Full suite: **469 passed, 3 skipped, 0 failed** in 42.09 seconds.
- Current-main pre-commit rerun: **469 passed, 3 skipped, 0 failed** in 41.96 seconds.
- Article API focused suite: **18 passed**.
- Graph focused suite: **11 passed**.
- Learning migration and SQLite store suites: **12 passed**.
- Operations inventory/health/backup/restore/cleanup suites: **38 passed**.
- Live source, browser-live, and PDF-live tests remained skipped by their explicit markers; this task did not access Scientific Spaces.

## Frontend Installation

`npm ci` installed 217 packages from the release lockfile in 24.59 seconds. npm reported zero vulnerabilities. No pre-existing `node_modules` was used.

## Frontend Build

Next.js `15.5.20` production build: **PASS** in 10.74 seconds. Static/dynamic output covered `/`, `/_not-found`, `/articles`, `/articles/[id]`, `/graph`, `/tutor`, and `/zotero`.

The current-main pre-commit production build also passed after the documentation updates.

Additional frontend evidence:

- Article client tests: 3/3 PASS.
- Graph client/presentation tests: 8/8 PASS.
- Tutor client/presentation tests: 13/13 PASS.
- Production routes `/`, `/articles`, `/graph`, `/tutor`, and `/zotero`: HTTP 200.
- Unknown route: HTTP 404.
- Article Chromium fixture smoke: 20 + 17 pagination, content search, detail navigation, and no horizontal overflow PASS.
- Graph Chromium fixture smoke: 17/17 checks PASS; no external requests or unexpected console errors.
- Tutor Chromium fixture smoke: 20/20 checks PASS; loading/retry and empty states PASS; no external requests.
- With the API stopped, Articles, Graph, and Tutor displayed explicit error/retry states rather than crashing.

## Default Runtime

The backend ran with an isolated `SCIENTIFIC_SPACES_DATA_DIR`, JSON Learning persistence, and explicit fake Zotero/Tutor providers.

| Check | Result |
|---|---|
| `GET /health` | 200, `{"status":"ok"}` |
| `GET /articles` | 200, exact empty legacy response |
| `GET /v1.1/articles` | 200, understandable empty paginated response |
| `GET /graph` | 200, empty Graph document |
| `POST /tutor/ask` | 200, grounded no-source refusal |
| API key required | No |
| External source/provider request | None observed; browser fixture probes reported zero external requests |
| Automatic article download | None |
| Runtime files created by read-only smoke | None |
| SQLite created in JSON mode | No |

The default startup does not require or silently generate the 1,311-Article corpus. Full-corpus capabilities remain explicit local configuration choices.

## Docker Runtime

Local Docker execution was unavailable because the host has no `docker` command. This is an environment limitation, not a hidden PASS.

The same exact release commit was independently checked out by tag CI run `29158711141`. Its Docker job completed successfully in approximately 67 seconds and passed:

- Compose build and detached startup.
- Backend health response.
- Frontend homepage response.
- Compose shutdown with volumes and orphans removed.

Docker release path result: **PASS from exact-tag CI; local rerun NOT AVAILABLE**.

## Article API Compatibility

A deterministic 37-Article runtime fixture verified:

- Legacy `GET /articles` returned all 37 records in store order.
- Legacy top-level fields were exactly `items`, `total`, and `query`.
- List items excluded full content and retained the summary contract.
- `GET /articles/{id}` returned `id`, `title`, `url`, `content`, and `metadata`.
- `/v1.1/articles` defaulted to 20 records; page 2 returned 17.
- `page_size=100` returned all 37; values above 100 are covered by the 422 regression.
- Title/content search, category filter, empty result, and deterministic sorting passed.

## Graph API Compatibility

A deterministic 37-Article Graph fixture produced 235 nodes and 640 edges.

- Legacy `GET /graph` retained `nodes`, `edges`, `built_at`, and `source_counts`.
- Legacy node search retained `items`, `total`, `query`, and `node_type`.
- Legacy node detail and path-subgraph routes remained available.
- `/v1.1/graph/nodes` returned 20 of 235 nodes by default rather than the full Graph.
- `/v1.1/graph/subgraph` enforced the requested 25-node and 50-edge bounds; the probe returned 25 nodes and 24 edges.
- Search, pagination, provenance, empty, failure/retry, mobile, and safe-link browser checks passed.

## Learning Migration and Rollback

The deterministic Learning fixture contained two states, one bookmark, two notes, and one session with stable IDs and timestamps.

- JSON to SQLite: PASS with counts `2/1/2/1`.
- Repeated JSON to SQLite: same counts; no growth.
- SQLite to JSON: PASS with the same counts and identities.
- Repeated export: byte-identical output.
- Source and restored JSON SHA-256 both equaled `4640a20c3167681131a121b117da548c0ae953820ed06303e4db7bbbcaba7f43`.
- No staging file remained.
- Injected replacement failures preserve source and existing target in the focused regression suite.
- Selecting a backend is separate from explicit migration, as documented; startup performs no automatic migration.

## Backup and Restore

The operations drill used a small deterministic fixture, not the user's local corpus.

- Inventory: PASS with deterministic manifest and capacity result.
- Health: PASS with zero issues across Article, classification, Learning, Markdown, PDF, RAG, Graph, Tutor, Zotero, manifest, and capacity checks.
- Essential backup: PASS; 6 data files plus manifest; 8,300 bytes; mode `0600`.
- PDF included: false.
- `.env`, credential, profile, trace, cache, RAG, Graph, Markdown, and PDF entries: absent.
- Independent verification: PASS with zero issues.
- Isolated restore: PASS; all six Tier 1 file hashes matched the source.
- Cleanup default: dry-run; cache remained present and Tier 1 files were unchanged.
- `all-derived --execute` without confirmation was refused and deleted nothing.

## Documentation Validation

### Tag-contained documentation

The tag contains the install commands, `.env.example`, compatibility/migration revision, deployment profile, persistence plan, pre-release checklist, changelog, and draft release notes. Backend setup, frontend setup, migration, backup, verification, restore, health, and cleanup commands were exercised successfully.

The tag necessarily predates post-release evidence and still identifies the release as a candidate in README/changelog/draft notes. This was distinguished from corruption: the immutable tag is unchanged, while formal post-release records live on main and in the GitHub Release.

### Post-release documentation

Main contains the formal release notes, release CI evidence, published project state, dated changelog, and release checklist completion evidence. Claims correctly state the local-first, single-user, fake-provider, partial SQLite, remote-image, and 1,311-of-1,326 corpus boundaries.

The README's bare RAG/Graph rebuild examples omitted required path arguments. This task corrected those examples on main. The release checklist's heading and two documentation bullets still describe the pre-release state despite completed release actions; this is recorded as a non-blocking hygiene finding.

## Artifact and Secret Audit

- No tracked runtime/private artifact matched the final anchored artifact scan.
- The only tracked HTML files are the three bounded parser regression fixtures.
- The release has no uploaded binary/runtime assets.
- Tracked secret-pattern scan returned no private key, OpenAI-style key, GitHub token, AWS access key, Google API key, or Slack token match.
- No `.env`, database, PDF, archive, corpus, FAISS, Graph runtime, backup, restore, profile, trace, cache, `node_modules`, or `.next` output was copied into main.

## Findings

### Critical

None.

### Important

None.

### Minor

#### P3-001-MIN-001 - Incomplete README derived rebuild examples

- Severity: Minor, resolved on main in this task.
- Affected component: README local-data operations.
- Reproduction: run the published bare RAG or Graph rebuild command.
- Expected: a copy/paste command supplies the required input and output paths.
- Actual: argparse requires `--article-store` and `--output-dir`.
- Evidence: both CLI `--help` outputs and clean-clone execution review.
- User impact: an optional derived rebuild stops before modifying data.
- Recommended version: main documentation update; no patch release.
- Recommended action: keep full explicit commands and add command tests if the README becomes generated documentation.

#### P3-001-MIN-002 - Post-release checklist retains pre-release header text

- Severity: Minor.
- Affected component: `docs/V1_1_RELEASE_CHECKLIST.md`.
- Reproduction: compare its header/documentation bullets with the checked release-action section.
- Expected: the completed checklist identifies v1.1.0 as published.
- Actual: the header still says formal version v1.0.0/ready to tag, and two bullets still describe draft/unreleased files.
- Evidence: main checklist lines 7-9 and 80-81 versus its completed release-action section.
- User impact: maintainer confusion only; runtime and release identity are unaffected.
- Recommended version: P3-002 documentation hygiene.
- Recommended action: make future release checklists immutable snapshots or add a separate completion record.

#### P3-001-MIN-003 - Cleanup safety rejection prints a Python traceback

- Severity: Minor.
- Affected component: cleanup CLI error presentation.
- Reproduction: run `cleanup_local_data.py --category all-derived --execute` without `--confirm-derived-delete`.
- Expected: concise nonzero CLI error explaining the required confirmation.
- Actual: the correct `CleanupSafetyError` is shown through a full traceback.
- Evidence: fresh-clone operations drill; no files were deleted.
- User impact: noisy operator experience, with safety behavior intact.
- Recommended version: v1.2.
- Recommended action: catch domain safety errors at the CLI boundary and print a concise stderr message.

### Accepted Limitations

- Local Docker was unavailable; exact-tag CI supplies the Docker evidence.
- Published tag contents cannot include the subsequent evidence commit without moving the tag, which is prohibited.
- Real provider cost, latency, error rate, privacy, and answer quality remain unevaluated.
- The default clone intentionally contains no full corpus or derived data.
- Structured `metadata.references` is empty across the completed corpus.
- Remote images are placeholders, and the Graph remains a large local JSON baseline.
- Authentication, authorization, and multi-user isolation are outside v1.1 scope.

## Patch Release Decision

**A: No v1.1.1 required.**

Critical findings: 0. Important findings: 0. Installation, default startup, API compatibility, exact-tag Docker, migration, backup, verification, and isolated restore all passed. The README issue is fixed on main; the remaining Minor findings do not break a declared v1.1 capability or create data/security risk.

## Cleanup Evidence

- `/tmp/scientific-spaces-v1.1.0-validation`: removed.
- `/tmp/scientific-spaces-v1.1.0-runtime`: removed.
- `/tmp/scientific-spaces-v1.1.0-backup`: removed.
- `/tmp/scientific-spaces-v1.1.0-restore`: removed.
- Migration/API fixture directories and temporary smoke JSON: removed.
- Ports 3000 and 8000: no listener after validation.
- Uvicorn/Next validation processes: stopped.
- Local Docker resources: none created because the CLI is unavailable; exact-tag CI's teardown step passed.

## Final Recommendation

Status: **PASS**.

Proceed to `P3-002 v1.2 Product Requirements and Architecture`. Do not create a v1.2 candidate version until that scope is reviewed and approved.
