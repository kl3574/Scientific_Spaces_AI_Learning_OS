from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.graph.service import GraphService, ManagedGraphBuildError, NodeNotFoundError

router = APIRouter(prefix="/graph")


def get_graph_service() -> GraphService:
    return GraphService()


@router.post("/build")
def build_graph() -> dict[str, object]:
    try:
        graph = get_graph_service().build_graph()
    except ManagedGraphBuildError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "built_at": graph.built_at,
        "source_counts": graph.source_counts,
    }


@router.get("")
def get_graph() -> dict[str, object]:
    return get_graph_service().get_graph().to_dict()


@router.get("/summary")
def get_graph_summary() -> dict[str, object]:
    return get_graph_service().get_summary()


@router.get("/nodes")
def search_nodes(
    q: str = "",
    node_type: str | None = None,
    article_id: str | None = None,
    concept: str | None = None,
    sort: Literal["node_id_asc", "label_asc", "source_count_desc"] = "node_id_asc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    limit: int | None = Query(default=None, ge=1, le=100),
) -> dict[str, object]:
    result = get_graph_service().list_nodes(
        query=q,
        node_type=node_type,
        article_id=article_id,
        concept=concept,
        sort=sort,
        page=page,
        page_size=limit or page_size,
    )
    if limit is not None:
        result["matched_total"] = result["total"]
        result["total"] = len(result["items"])
        result["total_pages"] = 1 if result["items"] else 0
        result["pages"] = result["total_pages"]
        result["has_next"] = False
        result["has_previous"] = False
    return result


@router.get("/subgraph")
def query_subgraph(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    node_limit: int = Query(default=100, ge=1, le=500),
    edge_limit: int = Query(default=250, ge=1, le=1000),
    node_type: str | None = None,
) -> dict[str, object]:
    try:
        return get_graph_service().get_subgraph(
            node_id,
            depth=depth,
            node_limit=node_limit,
            edge_limit=edge_limit,
            node_type=node_type,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/nodes/{node_id:path}/neighbors")
def get_neighbors(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    node_limit: int = Query(default=50, ge=1, le=500),
    edge_limit: int = Query(default=250, ge=1, le=1000),
    node_type: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=500),
) -> dict[str, object]:
    try:
        return get_graph_service().get_neighbors(
            node_id,
            depth=depth,
            node_limit=limit or node_limit,
            edge_limit=edge_limit,
            node_type=node_type,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/nodes/{node_id:path}")
def get_node(node_id: str) -> dict[str, object]:
    try:
        return get_graph_service().get_node(node_id).to_dict()
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/subgraph/{node_id:path}")
def get_subgraph(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    limit: int = Query(default=100, ge=1, le=500),
    edge_limit: int = Query(default=250, ge=1, le=1000),
    node_type: str | None = None,
) -> dict[str, object]:
    try:
        return get_graph_service().get_subgraph(
            node_id,
            depth=depth,
            node_limit=limit,
            edge_limit=edge_limit,
            node_type=node_type,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
