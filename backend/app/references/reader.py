from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from app.persistence.config import data_dir
from app.rag.full_corpus import compute_corpus_fingerprint, load_full_corpus_articles
from app.references.models import ReferenceManifest
from app.references.store import CORE_FILES, ReferenceStoreError, audit_reference_store
from app.services.article_reader import article_store_path

REFERENCE_STORE_ENV = "SCIENTIFIC_SPACES_REFERENCE_STORE"
REFERENCE_CONFIGURATION_ENV = "SCIENTIFIC_SPACES_REFERENCE_CONFIGURATION_FINGERPRINT"
DEFAULT_REFERENCE_STORE_RELATIVE_PATH = Path("references/full-corpus/current")

PUBLIC_RECORD_FIELDS = (
    "schema_version",
    "reference_id",
    "reference_type",
    "classification",
    "canonical_key",
    "normalized_identifier",
    "normalized_url",
    "doi",
    "arxiv_id",
    "arxiv_version",
    "source_article_id",
    "source_article_title",
    "source_article_url",
    "source_section",
    "source_span_start",
    "source_span_end",
    "evidence_text",
    "source_count",
    "extraction_rule",
    "extraction_rule_version",
    "confidence",
    "duplicate_group_id",
    "record_fingerprint",
)

PUBLIC_EVIDENCE_FIELDS = (
    "schema_version",
    "evidence_id",
    "reference_id",
    "source_article_id",
    "source_article_title",
    "source_article_url",
    "source_section",
    "source_span_start",
    "source_span_end",
    "evidence_text",
    "candidate_ordinal",
    "extraction_rule",
    "extraction_rule_version",
    "classification",
)

PUBLIC_CANDIDATE_FIELDS = (
    "schema_version",
    "candidate_id",
    "reference_id",
    "zotero_item_key",
    "item_type",
    "title",
    "doi",
    "url",
    "arxiv_id",
    "arxiv_version",
    "match_method",
    "match_score",
    "matched_fields",
    "conflicting_fields",
    "decision",
    "matcher_version",
    "zotero_snapshot_fingerprint",
)


class ReferenceReadError(RuntimeError):
    def __init__(self, *, code: str, state: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.state = state
        self.message = message


@dataclass(frozen=True)
class ReferenceSnapshot:
    manifest: ReferenceManifest
    records: tuple[dict[str, Any], ...]
    record_by_id: dict[str, dict[str, Any]]
    evidence_by_reference: dict[str, tuple[dict[str, Any], ...]]
    candidates_by_reference: dict[str, tuple[dict[str, Any], ...]]
    article_index: dict[str, dict[str, list[str]]]


def reference_store_path() -> Path:
    configured = os.getenv(REFERENCE_STORE_ENV)
    return Path(configured) if configured else data_dir() / DEFAULT_REFERENCE_STORE_RELATIVE_PATH


def load_reference_snapshot() -> ReferenceSnapshot:
    path = reference_store_path()
    signature = _store_signature(path)
    expected_corpus = _expected_corpus_fingerprint()
    expected_configuration = os.getenv(REFERENCE_CONFIGURATION_ENV) or None
    return _cached_snapshot(
        str(path.expanduser().resolve()),
        signature,
        expected_corpus,
        expected_configuration,
    )


def clear_reference_reader_cache() -> None:
    _cached_snapshot.cache_clear()
    _cached_article_fingerprint.cache_clear()


def public_record(record: dict[str, Any]) -> dict[str, Any]:
    return _allowlisted(record, PUBLIC_RECORD_FIELDS)


def public_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    return _allowlisted(evidence, PUBLIC_EVIDENCE_FIELDS)


def public_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    result = _allowlisted(candidate, PUBLIC_CANDIDATE_FIELDS)
    provenance = candidate.get("provenance")
    result["provenance"] = {
        "evidence_ids": _bounded_string_list(
            provenance.get("evidence_ids") if isinstance(provenance, dict) else None,
            limit=20,
            max_length=200,
        ),
        "matcher_version": _bounded_string(
            provenance.get("matcher_version") if isinstance(provenance, dict) else None,
            max_length=100,
        ),
    }
    return result


def filter_records(
    snapshot: ReferenceSnapshot,
    *,
    reference_type: str | None = None,
    classification: str | None = None,
    article_id: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    article_reference_ids: set[str] | None = None
    if article_id is not None:
        bucket = snapshot.article_index.get(article_id)
        article_reference_ids = set(bucket.get("reference_ids", [])) if bucket else set()
    normalized_query = query.strip().casefold() if query else ""
    selected: list[dict[str, Any]] = []
    for record in snapshot.records:
        if reference_type is not None and record.get("reference_type") != reference_type:
            continue
        if classification is not None and record.get("classification") != classification:
            continue
        if article_reference_ids is not None and record.get("reference_id") not in article_reference_ids:
            continue
        if normalized_query and not _record_matches_query(record, normalized_query):
            continue
        selected.append(record)
    return selected


def reference_summary(snapshot: ReferenceSnapshot) -> dict[str, Any]:
    manifest = snapshot.manifest
    return {
        "status": "valid",
        "schema_version": manifest.schema_version,
        "record_schema_version": manifest.record_schema_version,
        "evidence_schema_version": manifest.evidence_schema_version,
        "candidate_schema_version": manifest.candidate_schema_version,
        "corpus_fingerprint": manifest.corpus_fingerprint,
        "configuration_fingerprint": manifest.configuration_fingerprint,
        "build_fingerprint": manifest.build_fingerprint,
        "extractor_version": manifest.extractor_version,
        "normalization_version": manifest.normalization_version,
        "matcher_version": manifest.matcher_version,
        "generated_at": manifest.generated_at,
        "counts": _public_counts(manifest.counts),
        "network_request_count": manifest.network_request_count,
    }


def _store_signature(path: Path) -> tuple[tuple[str, int, int], ...]:
    if not path.is_dir() or path.is_symlink():
        raise ReferenceReadError(
            code="reference_store_missing",
            state="missing",
            message="Reference Store is not configured or is unavailable",
        )
    names = ("manifest.json", *CORE_FILES)
    signature: list[tuple[str, int, int]] = []
    try:
        for name in names:
            item = path / name
            stat = item.stat()
            signature.append((name, stat.st_mtime_ns, stat.st_size))
    except OSError as exc:
        raise ReferenceReadError(
            code="reference_store_corrupt",
            state="corrupt",
            message="Reference Store failed integrity validation",
        ) from exc
    return tuple(signature)


def _expected_corpus_fingerprint() -> str | None:
    path = article_store_path()
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ReferenceReadError(
            code="article_store_unavailable",
            state="stale",
            message="Article Store cannot be compared with the Reference Store",
        ) from exc
    try:
        return _cached_article_fingerprint(str(path.expanduser().resolve()), stat.st_mtime_ns, stat.st_size)
    except Exception as exc:
        raise ReferenceReadError(
            code="article_store_invalid",
            state="stale",
            message="Article Store cannot be compared with the Reference Store",
        ) from exc


@lru_cache(maxsize=8)
def _cached_article_fingerprint(path: str, modified_ns: int, size_bytes: int) -> str:
    del modified_ns, size_bytes
    return compute_corpus_fingerprint(load_full_corpus_articles(Path(path)))


@lru_cache(maxsize=8)
def _cached_snapshot(
    path: str,
    signature: tuple[tuple[str, int, int], ...],
    expected_corpus: str | None,
    expected_configuration: str | None,
) -> ReferenceSnapshot:
    del signature
    root = Path(path)
    try:
        manifest = audit_reference_store(
            root,
            expected_corpus_fingerprint=expected_corpus,
            expected_configuration_fingerprint=expected_configuration,
        )
    except ReferenceStoreError as exc:
        stale = "stale:" in str(exc)
        raise ReferenceReadError(
            code="reference_store_stale" if stale else "reference_store_corrupt",
            state="stale" if stale else "corrupt",
            message=(
                "Reference Store is stale and must be rebuilt"
                if stale
                else "Reference Store failed integrity validation"
            ),
        ) from exc

    try:
        records = tuple(_read_jsonl(root / "records.jsonl"))
        evidence = _read_jsonl(root / "evidence.jsonl")
        candidates = _read_jsonl(root / "zotero_candidates.jsonl")
        article_index = _read_json_object(root / "article_index.json")
        evidence_by_reference = _group_rows(evidence, "reference_id")
        candidates_by_reference = _group_rows(candidates, "reference_id")
        return ReferenceSnapshot(
            manifest=manifest,
            records=records,
            record_by_id={str(item["reference_id"]): item for item in records},
            evidence_by_reference=evidence_by_reference,
            candidates_by_reference=candidates_by_reference,
            article_index=article_index,
        )
    except (AttributeError, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ReferenceReadError(
            code="reference_store_corrupt",
            state="corrupt",
            message="Reference Store failed integrity validation",
        ) from exc


def _group_rows(rows: Iterable[dict[str, Any]], key: str) -> dict[str, tuple[dict[str, Any], ...]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row[key]), []).append(row)
    return {
        group_key: tuple(
            sorted(
                values,
                key=lambda item: str(
                    item.get("evidence_id")
                    or item.get("candidate_id")
                    or item.get("reference_id")
                    or ""
                ),
            )
        )
        for group_key, values in grouped.items()
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReferenceReadError(
            code="reference_store_corrupt",
            state="corrupt",
            message="Reference Store failed integrity validation",
        )
    return payload


def _allowlisted(value: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: value.get(field) for field in fields}


def _public_counts(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or isinstance(item, bool):
            continue
        if isinstance(item, int):
            result[key] = item
        elif isinstance(item, float) and math.isfinite(item):
            result[key] = item
        elif isinstance(item, dict):
            nested = _public_counts(item)
            if nested:
                result[key] = nested
    return result


def _bounded_string(value: object, *, max_length: int) -> str | None:
    return value[:max_length] if isinstance(value, str) else None


def _bounded_string_list(
    value: object,
    *,
    limit: int,
    max_length: int,
) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        item[:max_length]
        for item in value[:limit]
        if isinstance(item, str)
    ]


def _record_matches_query(record: dict[str, Any], query: str) -> bool:
    fields = (
        "reference_id",
        "canonical_key",
        "normalized_identifier",
        "normalized_url",
        "doi",
        "arxiv_id",
    )
    return any(query in str(record.get(field) or "").casefold() for field in fields)
