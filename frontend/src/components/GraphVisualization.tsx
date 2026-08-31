"use client";

import { useMemo } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";

import type { GraphSubgraphResponse } from "@/lib/graph";
import {
  GRAPH_NODE_VISUALS,
  createGraphVisualizationModel,
  type GraphVisualNode,
} from "@/lib/graphVisualization";

type GraphVisualizationProps = {
  subgraph: GraphSubgraphResponse;
  selectedNodeId: string;
  onSelectNode: (nodeId: string) => void;
};

type KnowledgeNodeData = Record<string, unknown> & {
  visual: GraphVisualNode;
  onSelectNode: (nodeId: string) => void;
};

type KnowledgeFlowNode = Node<KnowledgeNodeData, "knowledge">;

const nodeTypes = { knowledge: KnowledgeNode };

export function GraphVisualization({
  subgraph,
  selectedNodeId,
  onSelectNode,
}: Readonly<GraphVisualizationProps>) {
  const model = useMemo(
    () => createGraphVisualizationModel(subgraph, selectedNodeId),
    [selectedNodeId, subgraph],
  );
  const nodes = useMemo<KnowledgeFlowNode[]>(
    () =>
      model.nodes.map((node) => ({
        id: node.id,
        type: "knowledge",
        position: node.position,
        data: { visual: node, onSelectNode },
        selected: node.selected,
        draggable: false,
        selectable: false,
        focusable: false,
        ariaLabel: node.ariaLabel,
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      })),
    [model.nodes, onSelectNode],
  );
  const edges = useMemo<Edge[]>(
    () =>
      model.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        label: edge.label,
        ariaLabel: `${edge.label}: ${edge.source} to ${edge.target}`,
        focusable: true,
        selectable: false,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: edge.connectedToCenter ? "#334155" : "#94a3b8",
          width: 16,
          height: 16,
        },
        style: {
          stroke: edge.connectedToCenter ? "#334155" : "#94a3b8",
          strokeWidth: edge.connectedToCenter ? 1.8 : 1.2,
        },
        labelStyle: {
          fill: "#475569",
          fontSize: 10,
          fontWeight: 600,
        },
        labelBgStyle: {
          fill: "#ffffff",
          fillOpacity: 0.92,
        },
        labelBgPadding: [4, 2],
        labelBgBorderRadius: 3,
      })),
    [model.edges],
  );

  return (
    <div className="min-w-0 space-y-3" data-testid="graph-visualization">
      <div className="flex flex-col gap-3 border-y border-slate-200 py-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-slate-600" data-testid="graph-map-counts">
          {model.nodes.length} nodes · {model.edges.length} relationships
        </p>
        <GraphLegend />
      </div>

      <div className="knowledge-graph-canvas min-w-0 overflow-hidden border border-slate-300 bg-white">
        <ReactFlow<KnowledgeFlowNode>
          key={`${model.centerNodeId}-${model.nodes.length}-${model.edges.length}`}
          aria-label="Knowledge relationship map"
          colorMode="light"
          deleteKeyCode={null}
          edges={edges}
          edgesFocusable
          edgesReconnectable={false}
          elementsSelectable
          fitView
          fitViewOptions={{ padding: 0.16, minZoom: 0.35, maxZoom: 1.25 }}
          maxZoom={1.8}
          minZoom={0.25}
          nodes={nodes}
          nodesConnectable={false}
          nodesDraggable={false}
          nodesFocusable
          panOnDrag
          preventScrolling={false}
          zoomOnDoubleClick
          zoomOnPinch
          zoomOnScroll={false}
          nodeTypes={nodeTypes}
        >
          <Background color="#cbd5e1" gap={22} size={1} variant={BackgroundVariant.Dots} />
          <MiniMap
            aria-label="Knowledge map overview"
            className="knowledge-graph-minimap"
            maskColor="rgba(248, 250, 252, 0.72)"
            nodeColor={(node) => (node.data as KnowledgeNodeData).visual.accent}
            nodeStrokeWidth={2}
            pannable
            zoomable
          />
          <Controls aria-label="Knowledge map viewport controls" position="bottom-left" showInteractive={false} />
        </ReactFlow>
      </div>

      <p className="text-xs leading-5 text-slate-500">
        Select a node to make it the center. Use the viewport controls to zoom or fit the complete bounded map.
      </p>
    </div>
  );
}

function KnowledgeNode({ data }: NodeProps<KnowledgeFlowNode>) {
  const visual = data.visual;
  const isSelected = visual.selected;

  return (
    <div className="min-w-0" data-node-type={visual.nodeType}>
      <Handle className="knowledge-graph-handle" position={Position.Left} type="target" />
      <button
        aria-label={visual.ariaLabel}
        aria-pressed={isSelected}
        className={`knowledge-graph-node min-w-0 text-left ${isSelected ? "knowledge-graph-node-selected" : ""}`}
        data-testid={`graph-map-node-${visual.id}`}
        style={{
          background: visual.background,
          borderColor: isSelected ? visual.accent : visual.border,
          boxShadow: isSelected ? `0 0 0 3px ${visual.background}, 0 0 0 5px ${visual.accent}` : undefined,
        }}
        type="button"
        onClick={() => data.onSelectNode(visual.id)}
      >
        <span className="flex min-w-0 items-center gap-2.5">
          <span
            aria-hidden="true"
            className="knowledge-graph-symbol"
            style={{ background: visual.accent }}
          >
            {visual.symbol}
          </span>
          <span className="min-w-0">
            <span className="block text-[10px] font-semibold uppercase text-slate-500">{visual.typeLabel}</span>
            <span className="mt-0.5 block truncate text-sm font-semibold text-slate-950" title={visual.label}>
              {visual.label}
            </span>
          </span>
        </span>
      </button>
      <Handle className="knowledge-graph-handle" position={Position.Right} type="source" />
    </div>
  );
}

function GraphLegend() {
  return (
    <ul aria-label="Node type legend" className="flex flex-wrap gap-x-3 gap-y-2 text-[11px] text-slate-600">
      {Object.entries(GRAPH_NODE_VISUALS).map(([nodeType, spec]) => (
        <li key={nodeType} className="flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-flex h-4 min-w-4 items-center justify-center rounded-sm px-0.5 text-[8px] font-bold text-white"
            style={{ background: spec.accent }}
          >
            {spec.symbol}
          </span>
          {spec.typeLabel}
        </li>
      ))}
    </ul>
  );
}
