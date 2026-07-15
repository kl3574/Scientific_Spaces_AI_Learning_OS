from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


REFERENCE_RECORD_SCHEMA = "reference-record/v1"
REFERENCE_EVIDENCE_SCHEMA = "reference-evidence/v1"
REFERENCE_MANIFEST_SCHEMA = "reference-manifest/v1"
ZOTERO_CANDIDATE_SCHEMA = "zotero-match-candidate/v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def stable_id(prefix: str, version: str, identity: str) -> str:
    digest = sha256_text(f"{version}\0{identity}")
    return f"{prefix}_{digest[:32]}"


@dataclass(frozen=True)
class ReferenceEvidence:
    evidence_id: str
    reference_id: str
    source_article_id: str
    source_article_title: str
    source_article_url: str
    source_section: str
    source_span_start: int | None
    source_span_end: int | None
    evidence_text: str
    raw_reference: str
    raw_reference_hash: str
    candidate_ordinal: int
    extraction_rule: str
    extraction_rule_version: str
    classification: str
    corpus_fingerprint: str
    schema_version: str = REFERENCE_EVIDENCE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceRecord:
    reference_id: str
    reference_type: str
    classification: str
    canonical_key: str | None
    normalized_identifier: str | None
    normalized_url: str | None
    doi: str | None
    arxiv_id: str | None
    arxiv_version: int | None
    source_article_id: str
    source_article_title: str
    source_article_url: str
    source_section: str
    source_span_start: int | None
    source_span_end: int | None
    evidence_text: str
    raw_reference: str
    evidence_ids: list[str]
    source_count: int
    extraction_rule: str
    extraction_rule_version: str
    confidence: float
    duplicate_group_id: str | None
    corpus_fingerprint: str
    build_id: str
    record_fingerprint: str
    schema_version: str = REFERENCE_RECORD_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ZoteroMatchCandidate:
    candidate_id: str
    reference_id: str
    zotero_item_key: str | None
    item_type: str | None
    title: str | None
    doi: str | None
    url: str | None
    arxiv_id: str | None
    arxiv_version: int | None
    match_method: str
    match_score: float
    matched_fields: list[str]
    conflicting_fields: list[str]
    provenance: dict[str, Any]
    decision: str
    matcher_version: str
    zotero_snapshot_fingerprint: str | None
    schema_version: str = ZOTERO_CANDIDATE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceManifest:
    corpus_fingerprint: str
    configuration_fingerprint: str
    build_fingerprint: str
    generated_at: str
    counts: dict[str, Any]
    files: list[dict[str, Any]]
    source_asset_id: str
    rebuild_command: str
    network_request_count: int
    schema_version: str = REFERENCE_MANIFEST_SCHEMA
    record_schema_version: str = REFERENCE_RECORD_SCHEMA
    evidence_schema_version: str = REFERENCE_EVIDENCE_SCHEMA
    candidate_schema_version: str = ZOTERO_CANDIDATE_SCHEMA
    corpus_fingerprint_version: int = 1
    extractor_version: str = "p3-003-extractor/v2"
    normalization_version: str = "p3-003-normalization/v3"
    matcher_version: str | None = "p3-003-matcher/v1"
    status: str = "complete"
    integrity_rule_version: str = "p3-003-integrity/v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ReferenceManifest:
        return cls(**value)


def record_fingerprint_payload(value: dict[str, Any]) -> dict[str, Any]:
    excluded = {"record_fingerprint", "build_id", "schema_version"}
    return {key: item for key, item in value.items() if key not in excluded}
