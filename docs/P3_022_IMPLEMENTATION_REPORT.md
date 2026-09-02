# P3-022 Session-Aware Learning Dashboard Report

Status: **PASS / CLOSED**

## 1. Baseline And Scope

- entry branch: `main`
- entry commit and cached `origin/main`:
  `4c9ade019692173a3884fa7c60860aff04307a38`
- entry worktree and index: clean
- P3-016 Learning Dashboard Command Center: PASS / CLOSED
- P3-021 Focused Study Session: PASS / CLOSED
- REWORK and `.audit`: absent
- Backend, data, dependency, lockfile, workflow, API, Provider, Zotero, and
  release changes: not authorized and not made

P3-016 predated P3-021. The existing Dashboard could resume one Reader
position but did not expose the newer Focused Session queue, so its primary
action always opened Saved Learning even when a current session existed.

## 2. Implemented Experience

The existing `/` Command Center now contains one Session-aware work band:

1. A non-empty queue shows its bounded Article count, safe current title,
   exact queue position, next title, latest Reader progress, and current
   section label when available.
2. The page-level primary action changes from `Open saved learning` to
   `Resume focused session` only when a healthy queue exists.
3. `Open session` preserves the queue-management workflow, while `Continue
   current Article` uses the canonical Reader destination with
   `from=/session` and the latest safe section fragment when available.
4. Empty state routes learners to Saved Learning without hiding the existing
   exact single-Article Continue Learning action.
5. Same-tab custom events, cross-tab `storage` events, and refresh all reload
   the existing versioned P3-021 store. No second queue or persistence model
   was added.

The work band follows the existing unframed Dashboard section pattern. It is
placed after the existing overview/Continue Learning row so the established
mobile Continue Learning action remains within the first 390 x 844 viewport.

## 3. Resilience And Accessibility

- initial loading: bounded status text
- empty queue: actionable Saved Learning destination
- recovered queue: invalid/duplicate-record notice plus healthy entries
- inaccessible localStorage: isolated warning; remote Dashboard content stays
  available
- unsafe ID-as-title records: excluded by the pure presentation model and the
  existing queue parser
- progress: semantic `progressbar` with numeric ARIA values
- actions: descriptive visible text and exact accessible names
- keyboard/focus/reduced-motion behavior: inherited shared Shell and link
  controls remain intact

Independent Article and Learning Stats partial-failure/Retry behavior remains
unchanged and passed Product E2E.

## 4. TDD Evidence

Pure-model red:

```text
TS2305: Module '../src/lib/dashboard' has no exported member
'createDashboardStudySession'.
```

Browser-workflow red:

```text
Focused Session heading: element(s) not found
```

After implementation:

- active/fallback position selection: PASS
- exact `/session` Reader return path: PASS
- latest progress and section selection: PASS
- next Article and empty behavior: PASS
- same-tab and cross-tab synchronization: PASS
- recovered and unavailable storage behavior: PASS

## 5. Real Local Data And Visual Evidence

A temporary local-only production probe read the installed Article Store and
used isolated mutable state plus fake Tutor/Zotero providers. Every
non-loopback browser request was blocked.

- Article count: 1,314
- Article Store bytes: 14,970,258
- Article Store SHA-256:
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`
- current Article: `用傅里叶级数拟合一维概率密度函数`
- next Article: `时空之章：将Attention视为平方复杂度的RNN`
- current Reader progress: 38 percent
- canonical Reader destination:
  `/articles/521a5341f8f043db?from=%2Fsession`
- desktop viewport/document width: 1,440 / 1,440 px
- mobile viewport/document width: 390 / 390 px
- desktop Session band: 1,152 px wide, 194 px high
- mobile Session band: 358 px wide, 344 px high
- overlap, clipped controls, unreadable title wrapping, or horizontal
  overflow: none
- external requests: 0
- unexpected console errors: 0
- page errors: 0

Desktop and mobile screenshots were visually inspected and deleted with the
temporary probe. No screenshot, Article body, HTML, image, trace, profile, or
runtime store was retained.

## 6. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 38.20s
```

### Frontend

- Article, Reader, Dashboard, workflow, and navigation: 32 passed
- structured References: 3 passed
- global search: 5 passed
- Saved Learning: 5 passed
- Focused Session: 6 passed
- Graph: 10 passed
- Tutor: 19 passed
- focused total: 80 passed
- Next.js 15.5.21 production build: PASS, 11 routes
- `/`: 5.9 kB route / 116 kB first load
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

- complete runs: 3
- successful runs: 3
- checks per run: 51
- Session-aware Dashboard and exact Reader route: PASS
- same-tab and cross-tab Session updates: PASS
- recovered/unavailable Session states: PASS
- existing partial Dashboard Retry: PASS
- mobile Dashboard/Session geometry: PASS
- Backend restart persistence: PASS
- state leakage between runs: none
- external requests: 0
- unexpected console errors: 0
- page errors: 0

The final E2E harness also passed three complete runs under a single-core UTC
constraint. That stress run retained all 51 checks per run, restart
persistence, zero external requests, and zero unexpected console/page errors.

## 7. Security And Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- explicit workflow permissions: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- security utility tests: 17 passed
- dependency audit: PASS, 40 PyPI / 239 npm / 0 findings
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- combined SBOM bytes: 241,026
- independent SBOM builds: byte-identical
- SBOM forbidden values: 0
- temporary SBOM cleanup: PASS

## 8. Artifact And Protected-Path Evidence

- Backend implementation changes: 0
- frozen M1 path changes: 0
- Article source-record changes: 0
- Article Store count/fingerprint changes: 0
- derived RAG, Graph, Reference, or PDF asset changes: 0
- dependency, lockfile, or workflow changes: 0
- published API contract changes: 0
- tracked runtime/private artifact additions: 0
- `.env.example`: retained allowed secret-free template
- source-site requests: 0
- private Zotero reads/writes: 0 / 0
- real or paid Provider calls: 0
- candidate, tag, Release, or attestation actions: 0

## 9. Exact-SHA CI And E2E Repair

Implementation commit
`13af4c0898bbea6a86172c924ad255702ebc8d06` triggered exact-SHA main CI run
[`33588352098`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33588352098).
Backend, Frontend, workflow, dependency, secret, and SBOM jobs passed, but
Product E2E reported React hydration error `#418`. A rerun of the same SHA
failed again; the captured URL moved from `/library` to `/articles`, so the
failure was not accepted as a page-specific product defect or a transient
runner pass.

Bounded diagnosis established:

- direct target-state hard loads: 210/210 without hydration failure
- direct `/articles` 503 state: 100/100 without hydration failure
- same-tab unrelated hard-navigation sequence under one CPU: reproduced in
  1/32 runs
- fixed delays and `networkidle`: reduced but did not eliminate the race
- independent page per unrelated hard-navigation scenario: 100/100 without
  hydration failure

The Product E2E harness now gives each independent 404/503/Dashboard/Library
hard-navigation scenario a new Playwright page while retaining its browser
context, localStorage, backend state, network guard, console capture, and
strict page-error rejection. It also checks page errors immediately after
each scenario. Product routes, implementation behavior, workflows, and test
acceptance thresholds were not changed.

Repair commit `eeef48fbd982621da1e02553f34edefe8f53f8c5` passed exact-SHA main CI
run [`33590335784`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33590335784):

- Backend pytest: PASS
- Frontend build: PASS
- Product E2E, three runs: PASS
- workflow, dependency, secret, and SBOM jobs: PASS
- normal-main Docker and release-evidence jobs: skipped as designed
- uploaded workflow artifacts: 0

## 10. Known Risks

1. Focused Session remains intentionally browser-local and is not shared
   between browsers or devices.
2. Cross-tab synchronization depends on the standard browser `storage` event;
   same-tab writes use the existing explicit custom event.
3. Reader progress and queue state are separate versioned stores. The
   Dashboard selects the newest matching Reader record at render time but does
   not rewrite either store.
4. Pinned GitHub Actions currently receive an upstream Node 20 deprecation
   annotation while the runner forces Node 24; workflow revision is outside
   this product task.
5. Reusing one Playwright tab for unrelated hard-navigation failure scenarios
   can surface a low-resource React/Chromium old-document hydration race. The
   harness now isolates those scenarios without relaxing page-error checks.

## 11. Decision

P3-022 local acceptance: **PASS**.

- implementation commit:
  `13af4c0898bbea6a86172c924ad255702ebc8d06`
- E2E isolation repair commit:
  `eeef48fbd982621da1e02553f34edefe8f53f8c5`
- repair exact-SHA main CI: PASS, run `33590335784`
- P3-022: **PASS / CLOSED**
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
- v1.2 candidate assignment: none
