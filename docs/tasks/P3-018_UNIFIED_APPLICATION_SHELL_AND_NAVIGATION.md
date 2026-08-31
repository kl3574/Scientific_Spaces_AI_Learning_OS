# P3-018 Unified Application Shell and Navigation

Status: **PASS / CLOSED**

## Objective

Unify the existing learning workspaces behind one responsive, accessible
Application Shell using only existing Frontend clients, route contracts, and
dependencies.

## Entry Evidence

- branch: `main`
- entry commit: `abadf6d03aa5f7632085bb2393dfbad35c1ea6ff`
- cached `origin/main`: `abadf6d03aa5f7632085bb2393dfbad35c1ea6ff`
- ahead / behind: `0 / 0`
- worktree and index: clean
- REWORK / `.audit`: absent
- predecessor: P3-017 PASS / CLOSED

## In Scope

- semantic global navigation for all primary learning workspaces
- responsive desktop and mobile application framing
- active-route and workspace indication
- evidence-based contextual return and breadcrumb affordances
- preservation of existing deep links and route-local state
- bounded shared loading, empty, error, and unavailable presentation
- keyboard, focus, reduced-motion, landmark, and responsive behavior
- focused Frontend tests, isolated Product E2E, and local Article browser probes
- governance, implementation evidence, commits, push, and exact-SHA CI closure

## Out of Scope

- Backend or published API changes
- frozen M1/source pipeline changes
- Article record or storage changes
- RAG, Graph, or Reference derived-asset rebuilds or mutations
- dependency, lockfile, or workflow changes
- private Zotero access
- source-site access
- real or paid Provider calls
- candidate, tag, Release, or attestation actions
- authentication, multi-user state, or hosted deployment

## Planned Changes

- shell and navigation components under `frontend/src/components/`
- pure route/navigation helpers under `frontend/src/lib/` if justified by the
  existing component structure
- existing Frontend layouts/pages only where required for shell integration
- focused tests under `frontend/tests/`
- shell regression coverage in `scripts/e2e/run_product_e2e.py`
- `alignment.md`, task/status/report/roadmap/README documentation

## Acceptance

1. Dashboard, Articles, References, Graph, and Tutor are directly reachable
   through one semantic global navigation model; the integrated learning
   Workflow remains available through its existing context-preserving actions.
2. Current route/workspace is visually and programmatically identifiable.
3. Existing deep-link and workflow context is preserved through valid
   contextual return/breadcrumb actions.
4. Desktop and 390 px mobile navigation are complete, stable, and free of
   overlap, clipped controls, or page overflow.
5. Mobile menu focus, Escape handling, route-selection closure, and focus
   return behave predictably.
6. Keyboard access, visible focus, landmarks, and reduced motion pass.
7. Shared system states are consistent and auxiliary failure does not destroy
   usable workspace content.
8. Representative real local Article workflows and three repeated isolated
   Product E2E runs pass with fake providers, isolated mutable state, zero
   external requests, and no console/page errors.
9. Full local quality, compatibility, security, artifact, and protected-path
   gates pass without Backend, dependency, lockfile, workflow, data, or API
   changes.
10. Implementation and docs-only closure commits each pass exact-SHA main CI;
    final `main` is clean and synchronized.

## Authorization

- local Article data read, local application runtime, and isolated browser
  validation: GRANTED FOR P3-018
- Frontend/tests/docs edits, local commits, push, and CI inspection: GRANTED
  FOR P3-018
- Backend/frozen M1/source records/derived assets: NOT GRANTED
- dependency/lockfile/workflow/published API changes: NOT GRANTED
- source network/private Zotero/real Provider: NOT GRANTED
- candidate/tag/Release/attestation: NOT GRANTED

## Stop Conditions

Stop if an unknown worktree change appears, an in-scope gate cannot be fixed
without widening scope, a protected path or artifact changes, external/private
access becomes necessary, or any release action becomes necessary.

## Local Evidence

- Backend: 600 passed / 4 skipped
- focused Frontend: 59 passed
- production build: PASS
- Product E2E: 10 of 10 stress runs plus 3 of 3 formal runs, 32 checks per run
- real local Article shell probe: 5 of 5 PASS at 1440 x 900 and 390 x 844
- external requests, unexpected console errors, and page errors: 0
- workflow, suppression, dependency, staged secret audit, security utility,
  and temporary SBOM gates: PASS
- initial implementation commit:
  `86ff3cf971acc73feb298918e89f4468e6814e3b`
- initial implementation CI run `33370930585`: Product E2E BLOCKED; all other
  required jobs PASS
- hydration/readiness repair commit:
  `8db53b06947f4438d179ca020a7a1496e5176de8`
- repair exact-SHA main CI run
  [`33373397693`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33373397693):
  Backend, Frontend, Product E2E, workflow, dependency, secret, and SBOM PASS;
  Docker and release evidence correctly skipped; uploaded artifacts 0
- docs-only closure commit: this commit; exact-SHA main CI required before
  final reporting
