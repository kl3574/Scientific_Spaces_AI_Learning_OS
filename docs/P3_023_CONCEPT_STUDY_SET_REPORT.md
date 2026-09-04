# P3-023 Concept Study Set and Learning Launch Report

Status: **PASS / CLOSED**

## 1. Scope And Boundaries

P3-023 connects an existing Graph Concept to a bounded Article study set,
Reader round trips, Tutor Explain and Quiz launch points, and the existing
browser-local Focused Session. The implementation is Frontend-only apart from
tests and governance documentation.

Backend code, frozen M1 modules, source and Article records, Graph builders and
derived assets, dependencies, lockfiles, workflows, published APIs, private
Zotero data, Provider defaults, and release state remained unchanged. No
source request, external search, private Zotero action, real Provider call,
candidate, tag, Release, attestation, force push, or history rewrite occurred.

## 2. Study Set Contract

The pure Concept Study Set model:

- accepts only an existing `concept` node with a safe bounded identity and
  readable title;
- derives membership only from provenance records already returned with that
  Concept;
- preserves returned source order and deduplicates by safe Article ID;
- rejects malformed, unreadable, and ID-only records;
- identifies the first eligible Article as the optional primary Article;
- reports source, returned, eligible, duplicate, invalid, omitted, and
  truncated facts separately; and
- explicitly states that the result is neither complete nor a recommended or
  prerequisite learning sequence.

Other Graph node types retain their existing detail and context behavior.
Section provenance stays descriptive and is not converted into an unverified
Reader anchor.

## 3. Reader And Tutor Continuity

Each eligible Article links to the existing Reader with the exact canonical
`/graph?node_id=...` return path. Reader labels that destination `Back to
concept` and rejects non-canonical Graph return values.

Explain and Quiz use a typed, bounded launch contract. Both preserve the exact
Concept return path and prefill the existing Tutor without submitting a
request. Explain describes Graph context as supplemental to the selected local
Article. Quiz uses the primary Article and Concept topic without claiming Graph
grounding. Mode changes update the visible evidence statement, including the
case where no Article is selected.

## 4. Focused Session Integration

The existing 20-Article browser-local queue now supports one pure bulk append
operation. It preserves existing order and active Article, appends valid new
Articles once in source order, enforces capacity, and classifies added,
already-present, invalid, and capacity-omitted outcomes.

The Concept panel performs one persistence write for a changed bulk action.
Per-Article and bulk controls handle duplicate, full, unavailable, recovered,
and write-failure states without navigation or false success feedback.

## 5. Failure And Recovery Evidence

- non-Concept or unsafe Concept input: bounded unavailable state, PASS
- empty eligible set: explicit empty state, PASS
- truncated provenance: explicit disclosure, PASS
- malformed, duplicate, and unreadable sources: classified, PASS
- unavailable browser storage: writes disabled with alert, PASS
- recovered browser storage: healthy entries retained and disclosed, PASS
- failed persistence write: no success claim or navigation, PASS
- 19/20 and 20/20 queue capacity: deterministic outcomes, PASS
- Graph, Article, Tutor, and existing partial-backend failures: controlled,
  PASS

No failure state exposes a raw internal identifier, exception payload, Article
content, or private local path.

## 6. Accessibility And Responsive Behavior

- semantic heading, ordered-list, status, and alert structure: PASS
- actual keyboard Tab reachability and Enter activation: PASS
- `:focus-visible` with a nonzero visible outline: PASS
- live bulk-operation feedback: PASS
- long CJK title wrapping: PASS
- desktop 1,440 x 900: PASS
- mobile 390 x 844 with no horizontal overflow: PASS
- 200-percent zoom equivalent, 1,440 x 900 screen and 720 x 450 CSS
  viewport with both axes verified at 2:1: PASS
- Study Set and controls remain within the active CSS viewport: PASS

## 7. Real Local Data Evidence

The read-only local probe used the installed Article and Graph stores without
changing either one:

- Article count: 1,314
- Article Store SHA-256:
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`
- Graph Store SHA-256:
  `b39efa24e5ab5b4b625114542fd29aa087e504f578fd899c110a3fe5041cb473`
- `concept:attention`: 261 source records, 10 returned, 4 eligible, 6
  duplicates, 251 omitted, truncated
- `concept:transformer`: 155 source records, 10 returned, 5 eligible, 5
  duplicates, 145 omitted, truncated
- `concept:扩散模型`: 2 source records, 2 returned, 2 eligible, 0 omitted,
  not truncated

Every returned eligible Article resolved in the local Article Store. A
temporary local-only browser probe rendered all three Concepts and their typed
Tutor destinations with zero external requests, console errors, or page
errors. Temporary mutable state was isolated and removed.

## 8. Automated Evidence

### Backend

```text
uv run --project backend --extra dev pytest -q
600 passed, 4 skipped in 39.91s
```

### Frontend

- Article, Reader, workflow, and navigation: 33 passed
- structured References: 3 passed
- Tutor: 20 passed
- Graph and Concept Study Set: 18 passed
- global search: 5 passed
- Saved Learning Library: 5 passed
- Focused Session: 8 passed
- focused total: 92 passed
- Next.js 15.5.21 production build: PASS, 11 routes
- `/graph`: 67.3 kB route / 176 kB first load
- `/tutor`: 11 kB route / 241 kB first load
- shared first load: 103 kB

### Product E2E

```text
uv run --project backend --extra dev python \
  scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start
```

- formal complete runs: 3
- formal successful runs: 3
- checks per run: 63
- Concept -> Reader -> Concept: PASS
- Concept -> Tutor Explain/Quiz -> Concept: PASS
- Tutor request before explicit submission: 0
- one-write Session append, idempotence, recovery, failure, and capacity:
  PASS
- keyboard, focus, 200-percent zoom, desktop, and mobile: PASS
- restart persistence: PASS
- Chromium: 149.0.7827.55
- external requests: 0
- unexpected console errors: 0
- page errors: 0

## 9. Security And Supply Chain

- workflow policy: PASS, 1 workflow / 19 immutable Action uses
- explicit workflow permissions: 100 percent
- suppression policy: PASS, 0 dependency / 0 secret suppressions
- secret audit: PASS, 0 credible / 0 reported / 0 suppressed findings
- temporary CycloneDX 1.6 SBOM: PASS
- SBOM components: 40 Backend / 239 Frontend / 281 combined
- SBOM schema, dependency coverage, and forbidden-value checks: PASS
- temporary SBOM cleanup: PASS

The local dependency audit could not parse a timed-out npm audit response and
reported `npm audit JSON is missing vulnerabilities`. The exact implementation
SHA's independent GitHub Actions Dependency audit passed, so this local network
limitation is not an unresolved acceptance failure.

## 10. Artifact And Protected Paths

- Backend implementation changes: 0
- frozen M1 changes: 0
- source or Article record changes: 0
- Graph builder or derived-asset changes: 0
- dependency, lockfile, or workflow changes: 0
- published API changes: 0
- tracked runtime/private artifacts: 0
- uploaded workflow artifacts: 0
- `.env`, credential, PDF, HTML dump, image, trace, profile, cache, mutable
  store, corpus, generated SBOM, or local E2E result additions: 0

## 11. Review And Known Risks

Two independent final code reviews returned PASS after Article-ID validation,
mode-sensitive Tutor wording, outcome disclosure, keyboard focus evidence, and
two-axis 200-percent zoom evidence were corrected.

One local full-suite run observed a Next production hydration error on the
intentional route-not-found case. The minimal route probe then passed 5/5,
the next complete run passed, two separate three-run suites passed, and the
exact-SHA CI Product E2E job passed. It is recorded as a transient framework
risk rather than an active blocker. The existing CI also emits an upstream
Node 20 deprecation annotation for pinned Actions running in Node 24
compatibility mode; required jobs are unaffected.

The Study Set remains limited to bounded returned provenance, and Focused
Session persistence remains browser-local and single-profile. External Graph
shape changes can alter returned membership, which is why all counts and
truncation remain visible.

## 12. Exact-SHA Main CI

Implementation commit:
`fceadc512c266de2670d5c426dc201b9e580924b`.

Exact-SHA main CI:
[`33834027640`](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/33834027640),
`success` for the exact implementation SHA.

- Backend pytest: PASS
- Frontend build: PASS
- Product E2E, including three repeated runs: PASS
- workflow and suppression policy: PASS
- dependency audit: PASS
- secret audit: PASS
- SBOM validation: PASS
- Docker compose smoke: skipped as designed for a normal `main` push
- release-evidence dry-run: skipped as designed
- uploaded workflow artifacts: 0

## 13. Closure

P3-023 is `PASS / CLOSED`. Local acceptance, two independent final reviews,
and the implementation commit's exact-SHA main CI passed without widening the
authorized boundary. This docs-only closure commit must pass its own exact-SHA
main CI before final reporting. No new task or v1.2 candidate is assigned.
