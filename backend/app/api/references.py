from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query

from app.references.reader import (
    ReferenceReadError,
    ReferenceSnapshot,
    filter_records,
    load_reference_snapshot,
    public_candidate,
    public_evidence,
    public_record,
    reference_summary,
)

ReferenceType = Literal[
    "doi",
    "arxiv",
    "http_url",
    "relative_or_internal_url",
    "citation_text",
    "unsupported",
    "malformed",
]
ReferenceClassification = Literal[
    "extracted",
    "normalized",
    "duplicate",
    "ambiguous",
    "unsupported",
    "malformed",
    "rejected",
]
CandidateDecision = Literal["exact", "probable", "ambiguous", "unmatched", "rejected"]
PathIdentifier = Annotated[str, Path(min_length=1, max_length=200)]

router = APIRouter(prefix="/v1.2", tags=["references"])


@router.get("/reference-summary")
def get_reference_summary() -> dict[str, object]:
    return reference_summary(_snapshot())


@router.get("/references")
def list_references(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    reference_type: Annotated[ReferenceType | None, Query()] = None,
    classification: Annotated[ReferenceClassification | None, Query()] = None,
    article_id: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> dict[str, object]:
    snapshot = _snapshot()
    normalized_query = q.strip() if q and q.strip() else None
    records = filter_records(
        snapshot,
        reference_type=reference_type,
        classification=classification,
        article_id=article_id,
        query=normalized_query,
    )
    return _page(
        [public_record(record) for record in records],
        page=page,
        page_size=page_size,
        extra={
            "reference_type": reference_type,
            "classification": classification,
            "article_id": article_id,
            "query": normalized_query,
        },
    )


@router.get("/articles/{article_id}/references")
def list_article_references(
    article_id: PathIdentifier,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    reference_type: Annotated[ReferenceType | None, Query()] = None,
    classification: Annotated[ReferenceClassification | None, Query()] = None,
) -> dict[str, object]:
    snapshot = _snapshot()
    if article_id not in snapshot.article_index:
        raise HTTPException(status_code=404, detail="Article not found in Reference Store")
    records = filter_records(
        snapshot,
        reference_type=reference_type,
        classification=classification,
        article_id=article_id,
    )
    return _page(
        [public_record(record) for record in records],
        page=page,
        page_size=page_size,
        extra={
            "article_id": article_id,
            "reference_type": reference_type,
            "classification": classification,
        },
    )


@router.get("/references/{reference_id}/zotero-candidates")
def list_reference_zotero_candidates(
    reference_id: PathIdentifier,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    decision: Annotated[CandidateDecision | None, Query()] = None,
) -> dict[str, object]:
    snapshot = _snapshot()
    if reference_id not in snapshot.record_by_id:
        raise HTTPException(status_code=404, detail="Reference not found")
    candidates = list(snapshot.candidates_by_reference.get(reference_id, ()))
    if decision is not None:
        candidates = [item for item in candidates if item.get("decision") == decision]
    total = len(candidates)
    return {
        "items": [public_candidate(item) for item in candidates[:limit]],
        "total": total,
        "limit": limit,
        "truncated": total > limit,
        "reference_id": reference_id,
        "decision": decision,
    }


@router.get("/references/{reference_id}")
def get_reference(
    reference_id: PathIdentifier,
    provenance_limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> dict[str, object]:
    snapshot = _snapshot()
    record = snapshot.record_by_id.get(reference_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Reference not found")
    evidence = list(snapshot.evidence_by_reference.get(reference_id, ()))
    return {
        "record": public_record(record),
        "evidence": [public_evidence(item) for item in evidence[:provenance_limit]],
        "evidence_total": len(evidence),
        "provenance_limit": provenance_limit,
        "provenance_truncated": len(evidence) > provenance_limit,
    }


def _snapshot() -> ReferenceSnapshot:
    try:
        return load_reference_snapshot()
    except ReferenceReadError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": exc.code,
                "state": exc.state,
                "message": exc.message,
            },
        ) from exc


def _page(
    items: list[dict[str, object]],
    *,
    page: int,
    page_size: int,
    extra: dict[str, object],
) -> dict[str, object]:
    total = len(items)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": total_pages > 0 and page > 1,
        **extra,
    }
