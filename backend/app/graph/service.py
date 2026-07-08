from __future__ import annotations

from collections import deque

from app.graph.builder import KnowledgeGraphBuilder
from app.graph.models import GraphDocument, GraphEdge, GraphNode
from app.graph.store import GraphStore


class NodeNotFoundError(Exception):
    """Raised when a graph node is not present in the current graph."""


class GraphService:
    def __init__(
        self,
        *,
        builder: KnowledgeGraphBuilder | None = None,
        store: GraphStore | None = None,
    ) -> None:
        self.builder = builder or KnowledgeGraphBuilder()
        self.store = store or GraphStore()

    def build_graph(self) -> GraphDocument:
        return self.store.save(self.builder.build())

    def get_graph(self) -> GraphDocument:
        return self.store.load()

    def search_nodes(self, query: str, node_type: str | None = None, limit: int = 50) -> list[GraphNode]:
        graph = self.get_graph()
        normalized = query.strip().lower()
        capped_limit = max(1, min(limit, 100))
        results = []
        for node in graph.nodes:
            if node_type and node.node_type != node_type:
                continue
            haystack = " ".join([node.label, node.node_id, str(node.source_id or ""), str(node.metadata)]).lower()
            if not normalized or normalized in haystack:
                results.append(node)
            if len(results) >= capped_limit:
                break
        return results

    def get_node(self, node_id: str) -> GraphNode:
        graph = self.get_graph()
        for node in graph.nodes:
            if node.node_id == node_id:
                return node
        raise NodeNotFoundError(f"Graph node not found: {node_id}")

    def get_neighbors(self, node_id: str, depth: int = 1, limit: int = 50) -> dict[str, list[dict[str, object]]]:
        graph = self.get_graph()
        self.get_node(node_id)
        node_ids, edges = self._walk(graph, node_id, depth=depth, limit=limit)
        node_map = {node.node_id: node for node in graph.nodes}
        node_ids.discard(node_id)
        return {
            "nodes": [node_map[item].to_dict() for item in sorted(node_ids) if item in node_map],
            "edges": [edge.to_dict() for edge in edges],
        }

    def get_subgraph(self, node_id: str, depth: int = 1, limit: int = 100) -> dict[str, object]:
        graph = self.get_graph()
        root = self.get_node(node_id)
        node_ids, edges = self._walk(graph, node_id, depth=depth, limit=limit)
        node_ids.add(root.node_id)
        node_map = {node.node_id: node for node in graph.nodes}
        return {
            "nodes": [node_map[item].to_dict() for item in sorted(node_ids) if item in node_map],
            "edges": [edge.to_dict() for edge in edges],
            "built_at": graph.built_at,
            "source_counts": graph.source_counts,
        }

    def _walk(self, graph: GraphDocument, node_id: str, *, depth: int, limit: int) -> tuple[set[str], list[GraphEdge]]:
        capped_depth = max(1, min(depth, 3))
        capped_limit = max(1, min(limit, 200))
        adjacency: dict[str, list[tuple[str, GraphEdge]]] = {}
        for edge in graph.edges:
            adjacency.setdefault(edge.source_node_id, []).append((edge.target_node_id, edge))
            adjacency.setdefault(edge.target_node_id, []).append((edge.source_node_id, edge))

        seen_nodes = {node_id}
        seen_edges: dict[str, GraphEdge] = {}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue and len(seen_nodes) <= capped_limit:
            current, current_depth = queue.popleft()
            if current_depth >= capped_depth:
                continue
            for neighbor_id, edge in adjacency.get(current, []):
                seen_edges.setdefault(edge.edge_id, edge)
                if neighbor_id not in seen_nodes:
                    seen_nodes.add(neighbor_id)
                    queue.append((neighbor_id, current_depth + 1))
                    if len(seen_nodes) >= capped_limit:
                        break
        return seen_nodes, sorted(seen_edges.values(), key=lambda edge: edge.edge_id)
