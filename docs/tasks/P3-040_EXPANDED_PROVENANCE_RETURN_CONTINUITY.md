# P3-040 Expanded Provenance Return Continuity

Status: PASS / CLOSED

## Closure Receipt

Replacement integration [0a203bae2f99e3c2b3223823e7d91437bc27e96a](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/commit/0a203bae2f99e3c2b3223823e7d91437bc27e96a)
passes exact-SHA [main CI 34314910981](https://github.com/kl3574/Scientific_Spaces_AI_Learning_OS/actions/runs/34314910981),
completed SUCCESS at 2026-09-09T06:14:45Z. All seven required jobs pass.
Product E2E: three runs of 298 checks, no failed checks, restart persistence
four checks true, zero unexpected console/page errors or external requests.
Uploaded artifacts: 0. Docker/release jobs are policy-skipped, not PASS.
The prior local gates and independent final reviews remain recorded below.

Current task: [P3-041 Reader Inline Image Rendering](P3-041_READER_INLINE_IMAGE_RENDERING.md),
OPEN / IMPLEMENTATION, not completed by this prior CI. P3-039 remains
OPEN / DEFERRED, historical cause UNKNOWN. Formal version v1.1.0; candidate None.

Historical record follows: earlier pending/open gate statements describe their
pre-closure checkpoints, not current status. Original failures, requirements,
thresholds and scope are retained unchanged.

## Objective

After opening an Article from an expanded Concept Provenance list, returning to
the exact concept must reveal and focus the originating source, including sources
beyond the first three. Preserve default collapsed lists, explicit manual collapse,
native links, keyboard navigation, exact query context and one-shot return markers.

## Entry Evidence

Unchanged production build at d25113d, one owned temporary four-source concept:
keyboard expand, open provenance-3, Reader, Back to concept. Returned URL is
correct but source-3 is absent, the list is collapsed and focus falls back to the
detail region. Strict external/console/page/context-page counts are all zero.
Product/build bindings and the temporary fixture were unchanged; runtime removed.

This is separate from P3-039's historical map-rendering incident. That incident
remains OPEN / UNKNOWN. Its successful diagnostic CI is not a product repair.

## Independently Reviewed Scope

- frontend/src/components/GraphView.tsx
- frontend/src/components/GraphNodeDetail.tsx
- frontend/src/lib/graphPresentation.ts
- frontend/tests/graph.test.ts
- scripts/e2e/check_graph_provenance_return.py
- backend/tests/test_graph_provenance_return.py
- This task, docs/P3_040_EXPANDED_PROVENANCE_RETURN_CONTINUITY_REPORT.md,
  alignment.md, docs/tasks/CURRENT_TASK.md, docs/00_PROJECT_STATE.md,
  roadmap.md, docs/V1_2_ROADMAP.md and README.md.
- P3-039 task/report: diagnostic receipt and explicit deferral only.

Independent concrete design review passed before product edits. Independent final
review and verification precede publication. The owner authorizes automatic
execution within reviewed scope, not recurring generic plan confirmation.

## Acceptance

1. The original fourth-source journey has recorded browser RED evidence.
2. Desktop and narrow-mobile returns reveal and visibly focus the exact source
   without an extra click. Article identity and provenance index must both match.
3. Cold visits and already-visible source returns retain the three-source default.
   Manual collapse after a restored return remains effective.
4. Missing, malformed, unreturned or mismatched origins never reveal unrelated
   sources; preserve the existing safe region fallback and user-focus ownership.
5. Pending return work cannot act on a later route or selected node; one-shot
   markers retain their existing schema and consumption semantics.
   A late detail response must also respect already-completed newer Results /
   Selected intent; prerequisite failures do not qualify as product RED.
6. Graph unit tests, all existing Frontend test commands, production build,
   ordinary Backend tests and the bounded real-browser regression pass.
7. Before closure, the unchanged full Product E2E and exact-SHA CI pass; all
   assertions and strict network/error policy remain intact.
8. No runtime/private artifact, secret or forbidden application change is included.

## Boundaries

No Backend implementation, M1, API, storage schema, canonical data, acquisition,
PDF, private Zotero, real/paid Provider, dependency or workflow changes. No map
callback/rendering patch, Reader image-policy change, tag, Release, force push or
history rewrite. Preserve the known untracked frame-oracle draft without running
or publishing it; do not silently remove or include unrelated work.

## Delivery

Implementation commit: `fix: restore expanded provenance return focus`.
Non-force main publication requires independent review, safety checks and the
local gates above. Verify exact-SHA CI; do not claim closure from focused tests
or create receipt-only commits. Any failure returns to the affected diagnosis.
