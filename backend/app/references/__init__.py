"""Deterministic, offline structured-reference extraction."""

from app.references.models import (
    ReferenceEvidence,
    ReferenceManifest,
    ReferenceRecord,
    ZoteroMatchCandidate,
)

__all__ = [
    "ReferenceEvidence",
    "ReferenceManifest",
    "ReferenceRecord",
    "ZoteroMatchCandidate",
]
