from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from app.graph.service import GraphService, NodeNotFoundError
from app.tutor.models import TutorSource
from app.tutor.source_selection import (
    MAX_TUTOR_GRAPH_DEPTH,
    MAX_TUTOR_GRAPH_EDGES,
    MAX_TUTOR_GRAPH_NODES,
    GraphContextDataError,
    SourceSelectionPolicy,
    sanitize_graph_context,
)


@dataclass(frozen=True)
class GraphContextResult:
    context: dict[str, list[dict[str, Any]]]
    supplemental_sources: tuple[TutorSource, ...]
    latency_ms: float
    error_code: str | None = None


def collect_graph_context(
    graph_service: GraphService,
    node_id: str | None,
    policy: SourceSelectionPolicy,
) -> GraphContextResult:
    """Collect supplemental Graph evidence only for an explicitly requested node."""
    if not node_id or not node_id.strip():
        return GraphContextResult(context=_empty_context(), supplemental_sources=(), latency_ms=0.0)

    started = time.perf_counter()
    try:
        raw_context = graph_service.get_subgraph(
            node_id.strip(),
            depth=min(policy.max_graph_depth, MAX_TUTOR_GRAPH_DEPTH),
            node_limit=min(policy.max_graph_nodes, MAX_TUTOR_GRAPH_NODES),
            edge_limit=min(policy.max_graph_edges, MAX_TUTOR_GRAPH_EDGES),
        )
        safe_context, _ = sanitize_graph_context(raw_context, policy)
    except NodeNotFoundError:
        return _unavailable_result(started, "graph_node_not_found")
    except (OSError, json.JSONDecodeError, GraphContextDataError):
        return _unavailable_result(started, "graph_unavailable")
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        if not _is_graph_model_data_error(error):
            raise
        return _unavailable_result(started, "graph_unavailable")

    nodes = [dict(node) for node in safe_context["nodes"]]
    edges = [dict(edge) for edge in safe_context["edges"]]
    _place_root_first(nodes, node_id.strip())
    context = {"nodes": nodes, "edges": edges}
    return GraphContextResult(
        context=context,
        supplemental_sources=tuple(_node_sources(nodes) + _edge_sources(edges)),
        latency_ms=(time.perf_counter() - started) * 1000,
    )


def _empty_context() -> dict[str, list[dict[str, Any]]]:
    return {"nodes": [], "edges": []}


def _unavailable_result(started: float, error_code: str) -> GraphContextResult:
    return GraphContextResult(
        context=_empty_context(),
        supplemental_sources=(),
        latency_ms=(time.perf_counter() - started) * 1000,
        error_code=error_code,
    )


def _place_root_first(nodes: list[dict[str, Any]], node_id: str) -> None:
    for index, node in enumerate(nodes):
        if node.get("node_id") == node_id:
            nodes.insert(0, nodes.pop(index))
            return


def _is_graph_model_data_error(error: Exception) -> bool:
    """Recognize only persisted Graph deserialization failures, not caller bugs."""
    traceback = error.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        if frame.f_globals.get("__name__") == "app.graph.models" and frame.f_code.co_name == "from_dict":
            return True
        traceback = traceback.tb_next
    return False


def _node_sources(nodes: list[dict[str, Any]]) -> list[TutorSource]:
    return [
        TutorSource(
            source_type="graph_node",
            source_id=str(node["node_id"]),
            title=str(node["label"]),
            url=node.get("source_url"),
            evidence=node.get("evidence") or node.get("metadata"),
            metadata={
                key: value
                for key, value in {
                    "node_type": node.get("node_type"),
                    "source_id": node.get("source_id"),
                }.items()
                if value is not None
            },
        )
        for node in nodes
        if str(node.get("node_id") or "").strip() and str(node.get("label") or "").strip()
    ]


def _edge_sources(edges: list[dict[str, Any]]) -> list[TutorSource]:
    return [
        TutorSource(
            source_type="graph_edge",
            source_id=str(edge["edge_id"]),
            title=str(edge["edge_type"]),
            evidence=edge.get("evidence"),
            metadata={
                "source_node_id": edge["source_node_id"],
                "target_node_id": edge["target_node_id"],
            },
        )
        for edge in edges
        if str(edge.get("edge_id") or "").strip() and str(edge.get("edge_type") or "").strip()
    ]
