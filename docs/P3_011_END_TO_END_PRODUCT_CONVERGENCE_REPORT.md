# P3-011 End-to-End Product Convergence Report

Date: 2026-07-29

Status: **LOCAL PASS / EXACT-SHA CI PENDING**

## 1. Scope

P3-011 validates the complete local product journey over the exact current
Scientific Spaces corpus:

```text
Dashboard
  -> Article search
  -> Article reading
  -> Reading History and Learning state
  -> Structured References
  -> Knowledge Graph
  -> grounded Tutor modes
  -> persistence after Backend restart
```

The task uses local runtime assets and deterministic fake providers. It does
not contact Scientific Spaces, access or write private Zotero, call a real or
paid Provider, mutate Article records, modify frozen M1 modules, change
published API contracts, assign a candidate, or create a tag or Release.

## 2. Exact Runtime Baseline

- entry commit:
  `380f79804fbbde6795a7532f00a9be79b02b3bc0`
- Article count: 1,314
- Article Store SHA-256:
  `852ea18fd0f01781d0f8fdb7a4cf5d0ba5c4b9fb161e680a0f56455c03f11846`
- corpus fingerprint:
  `ff2824ca675ee0f7b6d82d8a3c63a08c5d3f6df99f5b79495c896367c8afbce6`
- RAG: 1,314 Articles / 5,570 chunks
- Graph: 1,314 Articles / 53,046 nodes / 82,584 edges
- Reference Store: 1,314 Articles / 12,904 records / 24,598 evidence rows
- RAG, Graph, and Reference corpus fingerprints: exact match

The Article Store byte SHA was rechecked after local implementation and
remained unchanged.

## 3. Defects Found and Fixed

### Duplicate Reader Session

React development Strict Mode invoked the Article Detail effect twice. Both
invocations created a Backend reading session, and concurrent JSON
read-modify-write operations could leave the UI holding a session ID that was
not present in the store. Ending that session returned HTTP 404.

`ArticleDetailView` now uses an Article-keyed synchronous `useRef` guard before
the first asynchronous request. A failed load releases the guard so a later
retry is possible. Real-corpus browser evidence changed from two session
creation requests to exactly one, and `End session` succeeded.

### Mobile Article List Overflow

At a 390 px viewport, the Article List document was 422 px wide. Min-content
width from nested flex/grid/card children escaped the content container.
Explicit `min-w-0`, `max-w-full`, and bounded card overflow now keep the
document at 390 px.

### Mobile Formula Overflow

At a 390 px viewport, an Article Detail document containing KaTeX was 988 px
wide. Hidden MathML/intrinsic formula layout expanded document width despite
the visible formula wrapper. The Reader now bounds KaTeX containers, preserves
local formula horizontal scrolling, and clips document-level overflow.
Article Detail now remains 390 px wide.

## 4. Automated E2E Design

`scripts/e2e/run_product_e2e.py`:

- derives a three-Article fixture runtime under a system temporary directory;
- builds temporary Graph and structured Reference stores using production
  builders;
- starts the real FastAPI application and the built Next.js application;
- launches real headless Chromium;
- permits only `localhost`, `127.0.0.1`, and `::1` requests;
- uses fake Tutor and Zotero providers;
- validates desktop and mobile flows;
- resets mutable fixture state between complete runs;
- restarts the Backend against the final store and rechecks persistence; and
- removes the entire fixture runtime automatically.

No screenshots, traces, videos, browser profiles, Article exports, indexes, or
runtime stores are written to the repository.

CI contains a dedicated `Product E2E` job. It installs Chromium, builds the
Frontend, and runs the complete suite three times. Manual/tag release-evidence
CI now also depends on this job.

## 5. E2E Acceptance Matrix

| Requirement | Browser/API evidence | Result |
| --- | --- | --- |
| Start complete local product | FastAPI health and built Next.js server reached through loopback | PASS |
| Dashboard | product title and fixture Article count rendered | PASS |
| Title/keyword search | `CRB` returned the expected Article | PASS |
| Empty search | impossible query rendered `No articles found.` | PASS |
| Article Detail | Chinese Markdown and Fisher content rendered | PASS |
| Formula fidelity | KaTeX rendered and display wrapper retained local x-scroll | PASS |
| Structured References | normalized DOI `10.1000/example` rendered | PASS |
| Reading History | opened Article appeared on Dashboard history | PASS |
| Learning state | completed state, bookmark, and note persisted | PASS |
| Reader session | exactly one session created; end request succeeded | PASS |
| Knowledge Graph | Attention concept, provenance, bounded context, and local Article link rendered | PASS |
| Tutor Explain | grounded answer and local Article source rendered | PASS |
| Tutor Derive | formula-backed grounded result rendered | PASS |
| Tutor Quiz | evidence-backed questions and answers rendered | PASS |
| Tutor Research | grounded answer or policy-compliant evidence-gap refusal plus local-only notice rendered | PASS |
| Deep links | Graph and Tutor Article hrefs resolved to bounded local `/articles/{id}` routes | PASS |
| Not found | unknown Article rendered controlled `Article not found` | PASS |
| Backend error | intentional Article-list HTTP 503 rendered controlled error | PASS |
| Mobile list | document width 390 px at a 390 px viewport | PASS |
| Mobile detail | document width 390 px at a 390 px viewport | PASS |
| Restart persistence | completed, bookmark, note, and ended sessions survived Backend restart | PASS |
| Isolation | mutable state reset before each run; temporary tree removed | PASS |
| Network boundary | external request count 0 | PASS |
| Browser errors | unexpected console errors 0; uncaught page errors 0 | PASS |

## 6. Three-Run Stability

Command:

```bash
uv run --project backend python scripts/e2e/run_product_e2e.py --repeat 3
```

Result:

- complete runs: 3
- successful runs: 3
- functional checks per run: 16
- failed checks: 0
- unexpected console errors: 0
- uncaught page errors: 0
- external network requests: 0
- mobile Article List widths: 390 / 390 / 390
- mobile Article Detail widths: 390 / 390 / 390
- Chromium: `149.0.7827.55`
- restart persistence: PASS

Each run started from an empty mutable learning/Tutor store. The final Backend
restart recovered one completed state, one bookmark, one note, and two ended
Reader sessions produced by the desktop and mobile contexts.

## 7. Exact-Corpus Browser Evidence

Before fixture automation, the real local 1,314-Article runtime was exercised
with isolated writable learning state:

- Dashboard: HTTP 200, 1,314 Articles
- search `Attention`: 128 Articles
- opened Archive 11823:
  `将Softmax Attention线性化为Gated DeltaNet`
- Article body and Chinese text: PASS
- rendered KaTeX nodes: 105
- Structured References: 25 records displayed
- Graph: full-corpus summary and bounded Attention context displayed
- Tutor Explain: grounded answer with two local Article chunks
- learning state, bookmark, note, reading history, and session end: PASS
- restart readback: completed 1 / bookmark 1 / note 1
- post-fix session delta per Article open: exactly 1
- mobile list/detail document widths after fix: 390 / 390

The browser did not open external source links.

## 8. Local Test Evidence

- Backend:
  `600 passed, 4 skipped in 38.76s`
- Frontend Article tests: 3 passed
- Frontend Reference tests: 3 passed
- Frontend Tutor tests: 13 passed
- Frontend Graph tests: 8 passed
- Frontend focused total: 27 passed
- Frontend production build: PASS, 8/8 pages generated
- Product E2E: 3/3 complete runs PASS
- workflow policy: PASS, 19 immutable Action uses, explicit permissions
- suppression policy: PASS, zero dependency/secret suppressions
- dependency audit: PASS, 40 PyPI and 219 npm packages, zero findings
- tracked/history secret audit: PASS, zero credible findings
- temporary SBOM build/validation: PASS, 261 combined components, zero
  forbidden values

The local host does not provide a Docker executable. Docker compose smoke is
therefore a required exact-implementation `workflow_dispatch` CI gate before
P3-011 can be closed.

## 9. Compatibility and Protected Boundaries

- Backend product/API implementation changes: 0
- frozen M1 module changes: 0
- legacy API contract changes: 0
- `/v1.1` contract changes: 0
- `/v1.2` contract changes: 0
- Article source mutations: 0
- source-site requests: 0
- private Zotero reads/writes: 0/0
- real or paid Provider calls: 0
- candidate/tag/Release actions: 0

The only product changes are Frontend session orchestration and responsive
layout. The E2E harness uses existing production APIs without adding or
changing a route.

## 10. CI Evidence

Implementation commit and exact-SHA CI evidence are pending at this report
stage. Closure requires:

1. push the implementation commit to `main`;
2. pass its normal main CI, including Backend, Frontend, Product E2E,
   workflow policy, dependency audit, secret audit, and SBOM validation;
3. run exact-implementation `workflow_dispatch`;
4. pass Docker compose smoke and no-publish release evidence;
5. create a docs-only closure commit; and
6. pass the closure commit's exact main CI.

No tag, Release, candidate, or attestation action is authorized.

## 11. Known Risks

- Browser automation depends on a compatible Chromium runtime. CI installs the
  pinned Python Playwright browser before E2E.
- The product remains a local single-user application. Concurrent independent
  writers are outside the current architecture contract.
- Fake providers prove deterministic grounding and refusal behavior, not
  real-model answer quality.
- Structured Reference extraction still includes inherited low-value page
  links in some real Articles. P3-011 does not alter the frozen Reference
  extraction output or claim improved scientific precision.
- External site changes remain relevant to future M1.x acquisition tasks but
  do not affect this offline product E2E gate.

## 12. Current Decision

Local implementation, exact-corpus runtime, three-run E2E, persistence,
Frontend, Backend, compatibility, network-boundary, dependency, secret, and
SBOM gates: **PASS**.

Docker and exact-SHA GitHub Actions evidence: **PENDING**.

Current P3-011 status: **LOCAL PASS / EXACT-SHA CI PENDING**.

P3-011 must not be marked `PASS / CLOSED` until both the implementation and
docs-only closure commits have successful exact main CI evidence and the
manual Docker compose smoke passes.
