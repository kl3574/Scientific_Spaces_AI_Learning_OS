# P3-023 Concept Study Set and Learning Launch

## Status

APPROVED / IN PROGRESS

## Objective

Connect an existing Graph Concept to a bounded, provenance-derived Article
study set, Tutor Explain and Quiz launch points, Reader round trips, and the
existing Focused Session without changing Backend contracts or product data.

## Authoritative Alignment

`alignment.md`

## Entry State

- branch: `main`
- entry commit: `e5fd14d1292cb6142dca26d0bfdc6eb517d109bb`
- cached `origin/main`: exact match
- ahead / behind: `0 / 0`
- worktree, index, and untracked set: clean
- P3-022: PASS / CLOSED
- REWORK / `.audit`: absent
- independent revised-scope reviews: 2 PASS
- candidate version: not assigned

## In Scope

- source-ordered, deduplicated Concept provenance Article study set
- explicit truncation, omission, invalid, duplicate, and eligibility disclosure
- safe typed Concept Explain/Quiz launch and canonical Graph return context
- Graph -> Article -> Graph and Graph -> Tutor -> Graph continuity
- per-Article and one-write bounded bulk append to the existing Focused Session
- complete empty, unavailable, recovered, full, and write-failure states
- responsive, accessible Graph/Tutor presentation
- focused Frontend, Product E2E, and read-only local real-data validation
- governance, report, commits, non-force push, and exact-SHA CI closure

## Protected Boundaries

- no prerequisite, pedagogical-order, or completeness claim
- no new route, queue, persistent concept plan, Tutor mode, Paper entity, or
  Experiment entity
- no Backend, API, M1, source, Article, Graph builder, or derived-data changes
- no dependency, lockfile, or workflow changes
- no source network, external search, private Zotero, or real/paid Provider
- no candidate, tag, Release, attestation, force push, or history rewrite
- no committed runtime/private artifacts, corpus, HTML, PDF, image, trace,
  profile, cache, database, credential, or secret

## Product Contract

- Study Set membership comes only from provenance records returned for the
  selected Concept.
- Valid readable Articles are deduplicated by Article ID in returned order.
- Source count is evidence-record count, not unique-Article count.
- Explain may combine a primary source Article with supplemental Graph context.
- Quiz uses the primary Article and concept topic; Graph grounding is not
  promised.
- Tutor launch pre-fills but never auto-submits.
- Session bulk append preserves current order and active item, adds once in
  source order, caps at 20, saves once, and reports every outcome class.

## Deliverables

- Concept Study Set and launch implementation under `frontend/src/`
- focused tests and expanded `scripts/e2e/run_product_e2e.py`
- `docs/P3_023_CONCEPT_STUDY_SET_REPORT.md`
- synchronized task, state, roadmap, README, and alignment documents
- implementation and docs-only closure commits with exact-SHA CI evidence

## Acceptance

- selected Concept exposes accurate bounded study actions and disclosure
- other Graph node types and existing Article-origin workflows do not regress
- Explain/Quiz prefill and exact return paths are safe and deterministic
- no Tutor request precedes explicit user submission
- Article links and Tutor return to the exact selected Concept
- Session append/dedup/capacity/storage outcomes are deterministic and announced
- keyboard, focus, semantics, 200-percent zoom, desktop, and 390 px pass
- three isolated Product E2E runs and all repository gates pass
- protected implementation/data boundaries remain unchanged
- implementation and closure exact-SHA CI pass; final branch is synchronized

## Confirmed Test Seams

1. Pure Concept Study Set, launch URL, and Session mutation interfaces.
2. Browser Graph Concept -> Article/Tutor/Session workflow.

## Stop Rule

Stop without widening scope when completion requires a protected contract,
external/private side effect, new dependency, release action, or unresolved
critical regression.

## Completion Evidence

- implementation commit: pending
- implementation CI: pending
- report: `docs/P3_023_CONCEPT_STUDY_SET_REPORT.md` pending
- docs-only closure commit: pending
- closure CI: pending
