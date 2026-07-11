from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.graph.service import GraphService, ManagedGraphBuildError, NodeNotFoundError

router = APIRouter()


def get_graph_service() -> GraphService:
    return GraphService()


@router.post("/graph/build")
def build_graph() -> dict[str, object]:
    service = get_graph_service()
    try:
        graph = service.build_graph()
    except ManagedGraphBuildError:
        graph = service.get_graph()
    return {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "built_at": graph.built_at,
        "source_counts": graph.source_counts,
    }


@router.get("/graph")
def get_graph() -> dict[str, object]:
    return get_graph_service().get_graph().to_dict()


@router.get("/graph/summary")
def get_graph_summary() -> dict[str, object]:
    return get_graph_service().get_summary()


@router.get("/graph/nodes")
def search_nodes(
    q: str = "",
    node_type: str | None = None,
    limit: int = 50,
) -> dict[str, object]:
    nodes = [
        node.to_dict()
        for node in get_graph_service().search_nodes(q, node_type=node_type, limit=limit)
    ]
    return {
        "items": nodes,
        "total": len(nodes),
        "query": q,
        "node_type": node_type,
    }


@router.get("/v1.1/graph/nodes")
def search_nodes_v11(
    q: str = "",
    node_type: str | None = None,
    article_id: str | None = None,
    concept: str | None = None,
    sort: Literal["node_id_asc", "label_asc", "source_count_desc"] = "node_id_asc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict[str, object]:
    return get_graph_service().list_nodes(
        query=q,
        node_type=node_type,
        article_id=article_id,
        concept=concept,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/graph/nodes/{node_id:path}/neighbors")
def get_neighbors(
    node_id: str,
    depth: int = 1,
    limit: int = 50,
) -> dict[str, object]:
    try:
        return get_graph_service().get_neighbors(
            node_id,
            depth=max(1, min(depth, 3)),
            limit=max(1, min(limit, 200)),
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/v1.1/graph/nodes/{node_id:path}/neighbors")
def get_neighbors_v11(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    node_limit: int = Query(default=50, ge=1, le=500),
    edge_limit: int = Query(default=250, ge=1, le=1000),
    node_type: str | None = None,
) -> dict[str, object]:
    try:
        return get_graph_service().get_neighbors(
            node_id,
            depth=depth,
            node_limit=node_limit,
            edge_limit=edge_limit,
            node_type=node_type,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/graph/nodes/{node_id:path}")
def get_node(node_id: str) -> dict[str, object]:
    try:
        return get_graph_service().get_node(node_id).to_dict()
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/graph/subgraph/{node_id:path}")
def get_subgraph(
    node_id: str,
    depth: int = 1,
    limit: int = 100,
) -> dict[str, object]:
    try:
        result = get_graph_service().get_subgraph(
            node_id,
            depth=max(1, min(depth, 3)),
            limit=max(1, min(limit, 200)),
        )
        result.pop("limits", None)
        return result
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/v1.1/graph/subgraph")
def get_subgraph_v11(
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
