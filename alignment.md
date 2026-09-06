# P3-034 Ordinary Route and Reader Hash Focus Continuity Alignment

Canonical task:
`docs/tasks/P3-034_ORDINARY_ROUTE_AND_HASH_FOCUS_CONTINUITY.md`

Status: **PASS / CLOSED**

BOUNDED SHELL/READER FRONTEND, PURE TESTS, PRODUCT E2E, GOVERNANCE
DOCUMENTATION, ISOLATED LOCAL FAKE-RUNTIME VALIDATION, LOCAL COMMITS, NON-FORCE
PUSH TO `main`, AND EXACT-SHA CI READBACK: **CONSUMED / CLOSED AFTER THIS
DOCS-ONLY CLOSURE COMMIT**

BACKEND, API, PROVIDER, PERSISTENCE, STORAGE SCHEMA, FROZEN M1, SOURCE OR ARTICLE
RECORDS, CORPUS, GRAPH OR REFERENCE DATA, MATCHING, DERIVED ASSETS, DEPENDENCIES,
LOCKFILES, WORKFLOWS, CANDIDATE, VERSION, TAG, RELEASE, AND ATTESTATION CHANGES:
**NOT GRANTED**

SOURCE NETWORK, EXTERNAL SEARCH, PRIVATE ZOTERO, REAL OR PAID PROVIDERS,
DESTRUCTIVE GIT ACTIONS, AND HISTORY REWRITING: **NOT GRANTED**

## Objective

Make ordinary same-tab navigation announce its committed destination through
visible keyboard focus, while preserving all destination-owned focus contracts
and repairing the Reader's explicit Outline, Reading tools, and Back to article
fragment destinations.

## Binding Contract

- Initial hydration never moves focus.
- Pathname and normalized query form Shell route identity; hash-only changes do
  not trigger Shell fallback.
- Search and mobile Drawer navigation retain their pending-route ownership and
  stale-operation cancellation.
- A changed route without pending modal ownership is an ordinary committed
  route. It schedules a main fallback instead of being discarded as stale.
- A connected focused element inside `main#main-content` owns focus. Otherwise
  Shell focuses main without scrolling after the route commits.
- Mismatched pending routes remain invalid and cannot claim focus.
- Desktop rail and brand use the existing accepted Next.js navigation event.
  Same-route activation adds no history entry and focuses current main;
  modified and new-tab activation stays native.
- Reader fragment links focus their exact target with visible focus treatment.
- New route, modal, or focus operations invalidate older deferred callbacks.

## Allowed Changes

- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/PrimaryNav.tsx`
- `frontend/src/components/ArticleDetailView.tsx`
- `frontend/src/components/StructuredReferencesPanel.tsx`
- `frontend/src/lib/navigation.ts`
- `frontend/tests/navigation.test.ts`
- `frontend/scripts/test-articles.sh`
- `scripts/e2e/run_product_e2e.py`
- `docs/tasks/P3-034_ORDINARY_ROUTE_AND_HASH_FOCUS_CONTINUITY.md`
- `docs/P3_034_ORDINARY_ROUTE_AND_HASH_FOCUS_CONTINUITY_REPORT.md`
- `alignment.md`
- `docs/tasks/CURRENT_TASK.md`
- `docs/00_PROJECT_STATE.md`
- `roadmap.md`
- `docs/V1_2_ROADMAP.md`
- `README.md`

## Acceptance

- Each desktop primary workspace, ordinary local content route, and browser
  Back/Forward commit lands on a destination-owned target or visible Shell main,
  never `BODY` or a persistent source-route link.
- Different-route activation creates exactly one history entry. Same-route rail
  or brand activation creates none and preserves URL and scroll.
- Delayed, superseded, and mismatched route operations cannot move focus early
  or overwrite a newer destination-owned target.
- Search, Drawer, Graph, Reader, and Reference focus ownership remains intact.
- Reader Outline, Reading tools, and Back to article links focus their exact
  visible targets; managed outline entries continue to focus their heading.
- Modified/new-tab and external links remain native.
- Desktop, `390x844`, `320x844`, and `720x450` coverage records no page-level
  overflow, focus loss, external request, or unexpected console/page error.
- Focused Frontend suites, production build, full Backend regression, three
  Product E2E runs, repository safety gates, and two independent final reviews
  pass.
- Implementation and docs-only closure commits each pass exact-SHA main CI;
  final `main` is clean and synchronized.

## Authorization Basis

The product owner explicitly directed the agent to continue bounded platform
and GUI improvements after independent sub-agent review without recurring plan
confirmation. Two independent reviewers reproduced this Important accessibility
gap and found no Critical issue. Both reviewers also identified the
structured-reference panel's independent autofocus as an Important ownership
conflict, so the exact scope above includes that single bounded repair. This
standing direction authorizes only the exact scope above.

## Stop Conditions

Stop rather than widen scope if correct behavior requires Backend, API,
provider, persistence, dependency, workflow, external/private, or release
changes, or if an unknown worktree change, forbidden artifact, unrepairable
gate, or exact-SHA CI failure appears.

No v1.2 candidate is assigned.

## Git Plan

- Implementation commit: `fix: preserve ordinary route focus continuity`
- Non-force push to `main`, followed by exact-SHA implementation CI readback
- Docs-only closure commit: `docs: close P3-034 route focus continuity`
- Non-force push to `main`, followed by exact-SHA closure CI readback
- Tag and Release operations are not authorized

## Local Gate Result

All required local implementation, focused Frontend, production build, full
Backend, three-run Product E2E, two-reviewer, security, SBOM, artifact, and
protected-path gates pass. Implementation commit
`05d18ffc9c359446d264bf8baa79785420af7769` passed exact-SHA main CI run
[`34005666793`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34005666793)
with every required job passing and zero uploaded artifacts. This docs-only
closure commit consumes the remaining P3-034 authorization; no later task is
staged or authorized.
