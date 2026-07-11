from __future__ import annotations

import json
import math
from collections import Counter, deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import Literal

from app.graph.builder import KnowledgeGraphBuilder
from app.graph.models import GraphDocument, GraphEdge, GraphNode
from app.graph.store import GraphStore

GraphNodeSort = Literal["node_id_asc", "label_asc", "source_count_desc"]


class NodeNotFoundError(Exception):
    """Raised when a graph node is not present in the current graph."""


class ManagedGraphBuildError(Exception):
    """Raised when the legacy builder targets a managed full-corpus graph."""


@dataclass(frozen=True)
class _GraphIndex:
    graph: GraphDocument
    node_map: dict[str, GraphNode]
    adjacency: dict[str, tuple[tuple[str, GraphEdge], ...]]
    article_node_ids: dict[str, frozenset[str]]


_INDEX_STATE_LOCK = Lock()
_INDEX_LOAD_LOCKS: dict[tuple[str, tuple[int, int] | None], Lock] = {}
_INDEX_LOAD_VALUES: dict[tuple[str, tuple[int, int] | None], _GraphIndex] = {}


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
        if _is_managed_full_corpus_store(self.store.path):
            raise ManagedGraphBuildError(
                "Refusing to overwrite a managed full-corpus graph; use the full-corpus graph CLI"
            )
        graph = self.store.save(self.builder.build())
        _clear_index_cache()
        return graph

    def get_graph(self) -> GraphDocument:
        return self._index().graph

    def get_summary(self) -> dict[str, object]:
        graph = self.get_graph()
        node_counts = Counter(node.node_type for node in graph.nodes)
        edge_counts = Counter(edge.edge_type for edge in graph.edges)
        manifest = _safe_manifest(self.store.path)
        return {
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "node_count_by_type": dict(sorted(node_counts.items())),
            "edge_count_by_type": dict(sorted(edge_counts.items())),
            "built_at": graph.built_at,
            "source_counts": graph.source_counts,
            "graph_fingerprint": manifest.get("graph_fingerprint"),
            "schema_version": manifest.get("schema_version"),
            "graph_contract_version": manifest.get("graph_contract_version", "m6.1"),
            "extraction_rule_version": manifest.get("extraction_rule_version"),
            "graph_fingerprint_version": manifest.get("graph_fingerprint_version"),
        }

    def list_nodes(
        self,
        *,
        query: str = "",
        node_type: str | None = None,
        article_id: str | None = None,
        concept: str | None = None,
        sort: GraphNodeSort = "node_id_asc",
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, object]:
        normalized_query = query.strip().casefold()
        normalized_concept = (concept or "").strip().casefold()
        normalized_article_id = (article_id or "").strip()
        article_node_ids = (
            self._index().article_node_ids.get(normalized_article_id, frozenset())
            if normalized_article_id
            else None
        )
        matches: list[GraphNode] = []
        for node in self.get_graph().nodes:
            if node_type and node.node_type != node_type:
                continue
            if article_node_ids is not None and node.node_id not in article_node_ids:
                continue
            if normalized_concept:
                if node.node_type != "concept":
                    continue
                aliases = node.metadata.get("aliases")
                alias_text = " ".join(str(alias) for alias in aliases) if isinstance(aliases, list) else ""
                concept_text = f"{node.label} {node.metadata.get('normalized') or ''} {alias_text}".casefold()
                if normalized_concept not in concept_text:
                    continue
            if normalized_query:
                haystack = " ".join(
                    [node.label, node.node_id, str(node.source_id or ""), _metadata_search_text(node.metadata)]
                ).casefold()
                if normalized_query not in haystack:
                    continue
            matches.append(node)

        if sort == "label_asc":
            matches.sort(key=lambda node: (node.label.casefold(), node.node_id))
        elif sort == "source_count_desc":
            matches.sort(
                key=lambda node: (-int(node.metadata.get("source_count") or 0), node.label.casefold(), node.node_id)
            )
        else:
            matches.sort(key=lambda node: node.node_id)

        total = len(matches)
        total_pages = math.ceil(total / page_size) if total else 0
        offset = (page - 1) * page_size
        items = matches[offset : offset + page_size]
        return {
            "items": [node.to_dict() for node in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1 and total_pages > 0,
            "query": query,
            "node_type": node_type,
            "article_id": article_id,
            "concept": concept,
            "sort": sort,
        }

    def search_nodes(self, query: str, node_type: str | None = None, limit: int = 50) -> list[GraphNode]:
        normalized = query.strip().lower()
        capped_limit = max(1, min(limit, 100))
        results: list[GraphNode] = []
        for node in self.get_graph().nodes:
            if node_type and node.node_type != node_type:
                continue
            haystack = " ".join(
                [node.label, node.node_id, str(node.source_id or ""), _metadata_search_text(node.metadata)]
            ).lower()
            if not normalized or normalized in haystack:
                results.append(node)
            if len(results) >= capped_limit:
                break
        return results

    def get_node(self, node_id: str) -> GraphNode:
        node = self._index().node_map.get(node_id)
        if node is None:
            raise NodeNotFoundError(f"Graph node not found: {node_id}")
        return node

    def get_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        limit: int | None = None,
        *,
        node_limit: int | None = None,
        edge_limit: int = 1000,
        node_type: str | None = None,
    ) -> dict[str, list[dict[str, object]]]:
        effective_node_limit = node_limit if node_limit is not None else (limit if limit is not None else 50)
        node_ids, edges = self._walk(
            node_id,
            depth=depth,
            node_limit=effective_node_limit,
            edge_limit=edge_limit,
        )
        result = self._serialize_walk(node_ids, edges, root_id=node_id, node_type=node_type)
        result["nodes"] = [item for item in result["nodes"] if item["node_id"] != node_id]
        return result

    def get_subgraph(
        self,
        node_id: str,
        depth: int = 1,
        limit: int | None = None,
        *,
        node_limit: int | None = None,
        edge_limit: int = 1000,
        node_type: str | None = None,
    ) -> dict[str, object]:
        effective_node_limit = node_limit if node_limit is not None else (limit if limit is not None else 100)
        node_ids, edges = self._walk(
            node_id,
            depth=depth,
            node_limit=effective_node_limit,
            edge_limit=edge_limit,
        )
        node_ids.add(node_id)
        result = self._serialize_walk(node_ids, edges, root_id=node_id, node_type=node_type)
        result["built_at"] = self.get_graph().built_at
        result["source_counts"] = self.get_graph().source_counts
        result["limits"] = {
            "depth": depth,
            "node_limit": effective_node_limit,
            "edge_limit": edge_limit,
        }
        return result

    def _walk(
        self,
        node_id: str,
        *,
        depth: int,
        node_limit: int,
        edge_limit: int,
    ) -> tuple[set[str], list[GraphEdge]]:
        index = self._index()
        if node_id not in index.node_map:
            raise NodeNotFoundError(f"Graph node not found: {node_id}")
        seen_nodes = {node_id}
        seen_edges: dict[str, GraphEdge] = {}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        stop = False
        while queue and not stop:
            current, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            for neighbor_id, edge in index.adjacency.get(current, ()):
                if edge.edge_id not in seen_edges:
                    if len(seen_edges) >= edge_limit:
                        stop = True
                        break
                    seen_edges[edge.edge_id] = edge
                if neighbor_id not in seen_nodes:
                    if len(seen_nodes) >= node_limit:
                        continue
                    seen_nodes.add(neighbor_id)
                    queue.append((neighbor_id, current_depth + 1))
        valid_edges = [
            edge
            for edge in seen_edges.values()
            if edge.source_node_id in seen_nodes and edge.target_node_id in seen_nodes
        ]
        return seen_nodes, sorted(valid_edges, key=lambda edge: edge.edge_id)

    def _serialize_walk(
        self,
        node_ids: set[str],
        edges: list[GraphEdge],
        *,
        root_id: str | None,
        node_type: str | None,
    ) -> dict[str, list[dict[str, object]]]:
        index = self._index()
        selected_ids = {
            node_id
            for node_id in node_ids
            if node_id in index.node_map
            and (not node_type or index.node_map[node_id].node_type == node_type or node_id == root_id)
        }
        selected_edges = [
            edge
            for edge in edges
            if edge.source_node_id in selected_ids and edge.target_node_id in selected_ids
        ]
        return {
            "nodes": [index.node_map[item].to_dict() for item in sorted(selected_ids)],
            "edges": [edge.to_dict() for edge in selected_edges],
        }

    def _index(self) -> _GraphIndex:
        path = self.store.path.resolve()
        try:
            stat = path.stat()
            signature: tuple[int, int] | None = (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            signature = None
        return _load_index(str(path), signature)


@lru_cache(maxsize=8)
def _load_index(path: str, signature: tuple[int, int] | None) -> _GraphIndex:
    key = (path, signature)
    with _INDEX_STATE_LOCK:
        existing = _INDEX_LOAD_VALUES.get(key)
        if existing is not None:
            return existing
        load_lock = _INDEX_LOAD_LOCKS.setdefault(key, Lock())
    with load_lock:
        with _INDEX_STATE_LOCK:
            existing = _INDEX_LOAD_VALUES.get(key)
            if existing is not None:
                return existing
        result = _load_index_uncached(path)
        with _INDEX_STATE_LOCK:
            _INDEX_LOAD_VALUES[key] = result
            _INDEX_LOAD_LOCKS.pop(key, None)
            while len(_INDEX_LOAD_VALUES) > 8:
                oldest_key = next(iter(_INDEX_LOAD_VALUES))
                _INDEX_LOAD_VALUES.pop(oldest_key, None)
        return result


def _load_index_uncached(path: str) -> _GraphIndex:
    graph = GraphStore(Path(path)).load()
    node_map = {node.node_id: node for node in graph.nodes}
    adjacency_lists: dict[str, list[tuple[str, GraphEdge]]] = {}
    article_node_sets: dict[str, set[str]] = {}
    for node in graph.nodes:
        for article_id in _node_article_ids(node):
            article_node_sets.setdefault(article_id, set()).add(node.node_id)
    for edge in graph.edges:
        adjacency_lists.setdefault(edge.source_node_id, []).append((edge.target_node_id, edge))
        adjacency_lists.setdefault(edge.target_node_id, []).append((edge.source_node_id, edge))
        article_id = str(edge.evidence.get("article_id") or "")
        if article_id:
            article_node_sets.setdefault(article_id, set()).update(
                (edge.source_node_id, edge.target_node_id)
            )
    adjacency = {
        node_id: tuple(sorted(items, key=lambda item: (item[1].edge_id, item[0])))
        for node_id, items in adjacency_lists.items()
    }
    article_node_ids = {
        article_id: frozenset(node_ids)
        for article_id, node_ids in article_node_sets.items()
    }
    return _GraphIndex(
        graph=graph,
        node_map=node_map,
        adjacency=adjacency,
        article_node_ids=article_node_ids,
    )


def _clear_index_cache() -> None:
    _load_index.cache_clear()
    with _INDEX_STATE_LOCK:
        _INDEX_LOAD_VALUES.clear()


def _safe_manifest(graph_path: Path) -> dict[str, object]:
    payload = _read_graph_manifest(graph_path)
    if not payload:
        return {}
    allowed = {
        "graph_fingerprint",
        "schema_version",
        "graph_contract_version",
        "extraction_rule_version",
        "graph_fingerprint_version",
    }
    return {key: payload.get(key) for key in allowed if key in payload}


def _is_managed_full_corpus_store(graph_path: Path) -> bool:
    payload = _read_graph_manifest(graph_path)
    required = {
        "schema_version",
        "graph_contract_version",
        "audit_rule_version",
        "article_count",
        "corpus_fingerprint",
        "graph_fingerprint",
    }
    return bool(payload) and required.issubset(payload)


def _read_graph_manifest(graph_path: Path) -> dict[str, object]:
    manifest_path = graph_path.parent / "manifest.json"
    if graph_path.name != "graph.json" or not manifest_path.is_file():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("graph_file") != graph_path.name:
        return {}
    return payload


def _node_article_ids(node: GraphNode) -> set[str]:
    result: set[str] = set()
    direct = node.metadata.get("article_id") or (node.source_id if node.node_type == "article" else None)
    if direct:
        result.add(str(direct))
    if node.node_type == "concept":
        for source in node.metadata.get("sources") or []:
            if isinstance(source, dict) and source.get("article_id"):
                result.add(str(source["article_id"]))
    return result


def _metadata_search_text(metadata: dict[str, object]) -> str:
    searchable_metadata = {key: value for key, value in metadata.items() if key != "sources"}
    return str(searchable_metadata)
