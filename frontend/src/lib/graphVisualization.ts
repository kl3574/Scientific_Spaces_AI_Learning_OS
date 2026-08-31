import type { GraphEdge, GraphNode, GraphNodeType, GraphSubgraphResponse } from "./graph";
import { getSafeDisplayText } from "./graphPresentation";

export const GRAPH_VISUAL_NODE_LIMIT = 25;
export const GRAPH_VISUAL_EDGE_LIMIT = 50;

export type GraphNodeVisualSpec = {
  typeLabel: string;
  symbol: string;
  accent: string;
  background: string;
  border: string;
};

export type GraphVisualNode = {
  id: string;
  source: GraphNode;
  position: { x: number; y: number };
  label: string;
  nodeType: GraphNodeType;
  typeLabel: string;
  symbol: string;
  selected: boolean;
  ariaLabel: string;
  accent: string;
  background: string;
  border: string;
};

export type GraphVisualEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  weight: number;
  connectedToCenter: boolean;
};

export type GraphVisualizationModel = {
  centerNodeId: string | null;
  nodes: GraphVisualNode[];
  edges: GraphVisualEdge[];
};

const NODE_TYPE_ORDER: Record<GraphNodeType, number> = {
  article: 0,
  section: 1,
  concept: 2,
  formula: 3,
  zotero_item: 4,
};

export const GRAPH_NODE_VISUALS: Record<GraphNodeType, GraphNodeVisualSpec> = {
  article: {
    typeLabel: "Article",
    symbol: "A",
    accent: "#047857",
    background: "#ecfdf5",
    border: "#6ee7b7",
  },
  section: {
    typeLabel: "Section",
    symbol: "S",
    accent: "#1d4ed8",
    background: "#eff6ff",
    border: "#93c5fd",
  },
  concept: {
    typeLabel: "Concept",
    symbol: "C",
    accent: "#b45309",
    background: "#fffbeb",
    border: "#fcd34d",
  },
  formula: {
    typeLabel: "Formula",
    symbol: "fx",
    accent: "#be123c",
    background: "#fff1f2",
    border: "#fda4af",
  },
  zotero_item: {
    typeLabel: "Zotero",
    symbol: "Z",
    accent: "#6d28d9",
    background: "#f5f3ff",
    border: "#c4b5fd",
  },
};

const RINGS = [
  { capacity: 8, radiusX: 260, radiusY: 180 },
  { capacity: 16, radiusX: 500, radiusY: 340 },
] as const;

export function createGraphVisualizationModel(
  subgraph: GraphSubgraphResponse,
  selectedNodeId: string | null,
): GraphVisualizationModel {
  const uniqueNodes = deduplicateNodes(subgraph.nodes);
  if (!uniqueNodes.length) {
    return { centerNodeId: null, nodes: [], edges: [] };
  }

  const requestedCenter = uniqueNodes.find((node) => node.node_id === selectedNodeId) ?? null;
  const sortedNodes = [...uniqueNodes].sort(compareNodes);
  const center = requestedCenter ?? sortedNodes[0];
  const neighbors = sortedNodes.filter((node) => node.node_id !== center.node_id);
  const boundedNodes = [center, ...neighbors].slice(0, GRAPH_VISUAL_NODE_LIMIT);
  const visualNodes = boundedNodes.map((node, index) => toVisualNode(node, center.node_id, index));
  const includedNodeIds = new Set(visualNodes.map((node) => node.id));
  const visualEdges = deduplicateEdges(subgraph.edges)
    .filter((edge) => includedNodeIds.has(edge.source_node_id) && includedNodeIds.has(edge.target_node_id))
    .sort((left, right) => compareStrings(left.edge_id, right.edge_id))
    .slice(0, GRAPH_VISUAL_EDGE_LIMIT)
    .map((edge) => toVisualEdge(edge, center.node_id));

  return {
    centerNodeId: center.node_id,
    nodes: visualNodes,
    edges: visualEdges,
  };
}

function deduplicateNodes(nodes: GraphNode[]): GraphNode[] {
  const unique = new Map<string, GraphNode>();
  for (const node of nodes) {
    if (!unique.has(node.node_id)) {
      unique.set(node.node_id, node);
    }
  }
  return [...unique.values()];
}

function deduplicateEdges(edges: GraphEdge[]): GraphEdge[] {
  const unique = new Map<string, GraphEdge>();
  for (const edge of edges) {
    if (!unique.has(edge.edge_id)) {
      unique.set(edge.edge_id, edge);
    }
  }
  return [...unique.values()];
}

function compareNodes(left: GraphNode, right: GraphNode): number {
  const typeDifference = NODE_TYPE_ORDER[left.node_type] - NODE_TYPE_ORDER[right.node_type];
  if (typeDifference !== 0) {
    return typeDifference;
  }
  const labelDifference = compareStrings(left.label, right.label);
  return labelDifference !== 0 ? labelDifference : compareStrings(left.node_id, right.node_id);
}

function compareStrings(left: string, right: string): number {
  if (left === right) {
    return 0;
  }
  return left < right ? -1 : 1;
}

function toVisualNode(node: GraphNode, centerNodeId: string, index: number): GraphVisualNode {
  const selected = node.node_id === centerNodeId;
  const spec = GRAPH_NODE_VISUALS[node.node_type];
  const label = getSafeDisplayText(node.label) ?? "Untitled node";
  return {
    id: node.node_id,
    source: node,
    position: selected ? { x: 0, y: 0 } : getRingPosition(index - 1),
    label,
    nodeType: node.node_type,
    typeLabel: spec.typeLabel,
    symbol: spec.symbol,
    selected,
    ariaLabel: `${selected ? "Selected " : ""}${spec.typeLabel}: ${label}`,
    accent: spec.accent,
    background: spec.background,
    border: spec.border,
  };
}

function getRingPosition(neighborIndex: number): { x: number; y: number } {
  let remaining = neighborIndex;
  for (let ringIndex = 0; ringIndex < RINGS.length; ringIndex += 1) {
    const ring = RINGS[ringIndex];
    if (remaining < ring.capacity) {
      const angle = -Math.PI / 2 + (2 * Math.PI * remaining) / ring.capacity;
      return {
        x: Math.round(Math.cos(angle) * ring.radiusX),
        y: Math.round(Math.sin(angle) * ring.radiusY),
      };
    }
    remaining -= ring.capacity;
  }
  return { x: 0, y: 0 };
}

function toVisualEdge(edge: GraphEdge, centerNodeId: string): GraphVisualEdge {
  const safeType = getSafeDisplayText(edge.edge_type);
  return {
    id: edge.edge_id,
    source: edge.source_node_id,
    target: edge.target_node_id,
    label: safeType?.replaceAll("_", " ") ?? "related",
    weight: Number.isFinite(edge.weight) ? edge.weight : 1,
    connectedToCenter: edge.source_node_id === centerNodeId || edge.target_node_id === centerNodeId,
  };
}
