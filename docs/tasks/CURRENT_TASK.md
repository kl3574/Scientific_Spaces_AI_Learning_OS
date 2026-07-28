# Current Task

## Task

P3-006-CI-001 Dependency Audit Repair

## Canonical Specification

`docs/tasks/P3-006_CI_001_DEPENDENCY_AUDIT_REPAIR.md`

## Status

IN PROGRESS

## Formal Version

v1.1.0

## Candidate Version

Not assigned

## Previous Task

P3-006 Structured Reference Full-Corpus Build: CONDITIONAL / CLOSED

## Implementation Authorization

GRANTED FOR THE EXACT DEPENDENCY-AUDIT FAILURE ONLY

## Dependency Update Authorization

GRANTED ONLY FOR THE MINIMUM OFFICIALLY FIXED VERSION

## Scanner/Parser Repair Authorization

GRANTED ONLY IF THE FAILURE IS CAUSED BY THE AUDIT TOOL

## Suppression Authorization

NOT GRANTED

## Full-Corpus Authorization

NOT GRANTED

## Private Zotero Authorization

NOT GRANTED

## Product/Source Network Authorization

NOT GRANTED

## Allowed Current Action

Diagnose GitHub Actions run `30320834573`, apply the minimum safe dependency
repair, validate it locally and through the required validation/main CI gates,
then record a docs-only closure.

## Prohibited Current Actions

- Full-corpus extraction, rebuild, resume, or Reference Store mutation
- Article Store mutation
- Reference semantics, product feature, or product API modification
- Dependency suppression, policy weakening, or scanner removal
- Source-site, Provider, paid-service, or private Zotero access
- P3-006.1 or P3-007 staging
- Candidate assignment, tag, Release, or attestation
- Force push, rebase, amend, or published-history rewrite

## Next Required Decision

Complete the exact dependency-audit repair and restore successful validation
and main CI. On closure, return this pointer to P3-006 `CONDITIONAL / CLOSED`.
