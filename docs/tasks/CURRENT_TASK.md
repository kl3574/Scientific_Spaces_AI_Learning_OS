# Current Task

## Task

P3-005 CI Security and Release Provenance

## Canonical Specification

`docs/tasks/P3-005_CI_SECURITY_AND_RELEASE_PROVENANCE.md`

## Status

BLOCKED - IMPLEMENTATION COMPLETE; DOCKER SMOKE EVIDENCE UNAVAILABLE

## Formal Version

v1.1.0

## Candidate Version

Not assigned

## Previous Task

P3-004 Real Provider Evaluation Design: PASS / CLOSED

## Implementation Authorization

GRANTED UNDER CONFIRMED LOCAL-ONLY ALIGNMENT

## Real Provider Authorization

NOT GRANTED

## Allowed Current Action

Record the authorized local blocker commit. Further execution requires Docker-capable validation evidence or separate authorization for an exact-commit remote manual run.

## Prohibited Current Actions

- Push of the P3-005 completion commit
- Formal SBOM or provenance publication
- Real or paid Provider calls
- Private Zotero or user-data access/export
- Candidate assignment
- Tag or Release
- Push without separate authorization

## Next Required Decision

Obtain Docker compose smoke evidence, then close P3-005 and separately audit any push authorization.
