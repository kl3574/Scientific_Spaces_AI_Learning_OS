from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

GraphNodeType = Literal["article", "section", "concept", "formula", "zotero_item"]
GraphEdgeType = Literal[
    "contains",
    "mentions",
    "has_section",
    "has_formula",
    "related_to",
    "related",
    "cites",
    "background",
    "same_category",
]


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: GraphNodeType
    label: str
    source_id: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphNode":
        return cls(
            node_id=str(data["node_id"]),
            node_type=data["node_type"],
            label=str(data["label"]),
            source_id=data.get("source_id"),
            source_url=data.get("source_url"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: GraphEdgeType
    weight: float = 1.0
    evidence: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "weight": self.weight,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphEdge":
        return cls(
            edge_id=str(data["edge_id"]),
            source_node_id=str(data["source_node_id"]),
            target_node_id=str(data["target_node_id"]),
            edge_type=data["edge_type"],
            weight=float(data.get("weight", 1.0)),
            evidence=dict(data.get("evidence") or {}),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class GraphDocument:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    built_at: str | None = None
    source_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "built_at": self.built_at,
            "source_counts": self.source_counts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphDocument":
        return cls(
            nodes=[GraphNode.from_dict(item) for item in data.get("nodes", [])],
            edges=[GraphEdge.from_dict(item) for item in data.get("edges", [])],
            built_at=data.get("built_at"),
            source_counts=dict(data.get("source_counts") or {}),
        )


def make_node_id(node_type: str, source: str) -> str:
    return f"{node_type}:{_stable_key(source)}"


def make_edge_id(source_node_id: str, target_node_id: str, edge_type: str, evidence_key: str = "") -> str:
    raw = "|".join([source_node_id, target_node_id, edge_type, evidence_key])
    return f"edge:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _stable_key(value: str) -> str:
    cleaned = value.strip().lower().replace(" ", "-")
    safe = "".join(ch for ch in cleaned if ch.isalnum() or ch in {"-", "_", ":", "."}).strip("-")
    if safe:
        return safe[:80]
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
