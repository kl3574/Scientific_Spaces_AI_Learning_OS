from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.graph.service import GraphService, NodeNotFoundError

router = APIRouter(prefix="/graph")


def get_graph_service() -> GraphService:
    return GraphService()


@router.post("/build")
def build_graph() -> dict[str, object]:
    graph = get_graph_service().build_graph()
    return {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "built_at": graph.built_at,
        "source_counts": graph.source_counts,
    }


@router.get("")
def get_graph() -> dict[str, object]:
    return get_graph_service().get_graph().to_dict()


@router.get("/nodes")
def search_nodes(q: str = "", node_type: str | None = None, limit: int = 50) -> dict[str, object]:
    nodes = [node.to_dict() for node in get_graph_service().search_nodes(q, node_type=node_type, limit=limit)]
    return {"items": nodes, "total": len(nodes), "query": q, "node_type": node_type}


@router.get("/nodes/{node_id:path}/neighbors")
def get_neighbors(node_id: str, depth: int = 1, limit: int = 50) -> dict[str, object]:
    try:
        return get_graph_service().get_neighbors(node_id, depth=depth, limit=limit)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/nodes/{node_id:path}")
def get_node(node_id: str) -> dict[str, object]:
    try:
        return get_graph_service().get_node(node_id).to_dict()
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/subgraph/{node_id:path}")
def get_subgraph(node_id: str, depth: int = 1, limit: int = 100) -> dict[str, object]:
    try:
        return get_graph_service().get_subgraph(node_id, depth=depth, limit=limit)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
