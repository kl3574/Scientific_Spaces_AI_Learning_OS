# ADR 0009: P3-007 Review Risk and Zotero PDF Policy

Status: Accepted

Date: 2026-07-28

## Context

P3-006 completed deterministic full-corpus extraction, provenance, store
integrity, idempotency, recovery, and fake/unavailable Zotero matching. Its
formal 64-case human-review packet was not completed, so no measured
strong-identifier precision exists.

P3-006.2 exposed three complete pilot Articles for human review. The product
owner reviewed and approved those three cases in Zotero on 2026-07-28 and
explicitly chose to skip the remaining 61 cases. P3-006.3 separately proved
that the useful full-text representation is a browser-printed PDF rather than
an HTML snapshot.

The project needs a transparent decision about whether P3-007 may proceed and
which Zotero full-text representation is authoritative.

## Decision Drivers

- Preserve truthful evidence and never equate three reviewed cases with 64.
- Respect the product owner's explicit decision to avoid further manual
  review.
- Keep machine integrity gates unchanged.
- Preserve local-first, no-automatic-write Zotero boundaries.
- Provide a stable, readable, math-capable Article attachment representation.

## Options Considered

### 1. Complete All 64 Cases

Statistically stronger, but explicitly declined because of review cost.

### 2. Treat Three Cases as the Original Gate

Rejected. Three cases cannot prove 64/64 completeness or precision >=0.95.

### 3. Keep P3-007 Blocked

Rejected after the product owner explicitly accepted the bounded quality risk.

### 4. Record a Controlled Risk Exception

Selected.

## Decision

### Human-Review Risk

- Record exactly three user-reviewed and approved pilot cases.
- Record 61 formal cases as waived, not reviewed.
- Do not publish a measured strong-identifier precision value.
- Keep P3-006 as `CONDITIONAL / RISK ACCEPTED`.
- Permit P3-007 implementation and release-readiness validation to proceed.
- The highest successful P3-007 status is
  `CONDITIONAL / RISK ACCEPTED`.
- A future candidate task must carry this risk explicitly. It may complete
  P3-006.1 for stronger evidence, but this ADR does not require repeated review
  unless the product owner changes the decision or extraction/matching
  semantics change.

Risk owner: repository product owner.

Decision gate: v1.2 candidate assignment.

Optional remediation: complete all P3-006.1 decisions and recompute the
original metrics.

### Zotero Full-Text Representation

For Scientific Spaces Article synchronization into `苏剑林博客`:

- the metadata-complete parent remains a Zotero Web Page item;
- the accepted full-text child is a browser-printed A4 PDF;
- the PDF must pass format, nonzero-size, readable text, title, Chinese,
  content, MathJax, and Zotero byte-readback checks;
- HTML snapshots are not an accepted final live full-text child;
- replacement deletes/moves HTML only after every intended PDF passes
  readback;
- PDFs and private Zotero identifiers remain runtime/private data and are
  never committed.

This policy does not authorize additional Zotero access or synchronization in
P3-007.

## Consequences

Positive:

- P3-007 can proceed without false statistical claims.
- The remaining uncertainty is visible to future candidate decisions.
- Zotero full text has one stable, printable, math-preserving representation.

Costs and residual risks:

- Extraction/matching errors outside the three reviewed cases may remain.
- The three-case evidence is not a precision estimate.
- Browser PDF output depends on Playwright/Chromium and source-page stability.
- PDF rendering can preserve visual content while reducing semantic HTML
  structure.

## Verification

- Governance documents report 3 reviewed and 61 waived cases.
- No report claims 64/64 completion or precision >=0.95.
- P3-006.3 evidence remains 3/3 PDF, zero live HTML children, and zero
  temporary repository artifacts.
- P3-007 tests prove read-only API/UI behavior and cannot write Zotero or
  review decisions.
- Artifact and secret audits reject PDF, HTML, private identifiers, and local
  paths.

## Reversal

The review exception can be superseded by completing P3-006.1 under a new
confirmed task. The PDF policy can be changed only by a new ADR with format,
migration, rollback, private-data, and attachment-readback evidence.
