from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from app.graph.service import GraphService, NodeNotFoundError
from app.tutor.models import TutorSource
from app.tutor.source_selection import SourceSelectionPolicy, sanitize_graph_context


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
            depth=policy.max_graph_depth,
            node_limit=policy.max_graph_nodes,
            edge_limit=policy.max_graph_edges,
        )
        safe_context, _ = sanitize_graph_context(raw_context, policy)
    except NodeNotFoundError:
        return _unavailable_result(started, "graph_node_not_found")
    except (OSError, json.JSONDecodeError):
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
    ]
