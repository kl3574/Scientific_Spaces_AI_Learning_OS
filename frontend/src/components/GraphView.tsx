"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  GraphDocument,
  GraphNeighborsResponse,
  GraphNode,
  GraphNodeType,
  buildGraph,
  fetchGraph,
  fetchGraphNeighbors,
  searchGraphNodes,
} from "@/lib/graph";

const nodeTypes: Array<GraphNodeType | ""> = ["", "article", "section", "concept", "formula", "zotero_item"];

export function GraphView() {
  const [graph, setGraph] = useState<GraphDocument | null>(null);
  const [query, setQuery] = useState("attention");
  const [nodeType, setNodeType] = useState<GraphNodeType | "">("");
  const [results, setResults] = useState<GraphNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [neighbors, setNeighbors] = useState<GraphNeighborsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void loadGraph();
  }, []);

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const node of graph?.nodes ?? []) {
      counts[node.node_type] = (counts[node.node_type] ?? 0) + 1;
    }
    return counts;
  }, [graph]);

  async function loadGraph() {
    setError(null);
    try {
      const nextGraph = await fetchGraph();
      setGraph(nextGraph);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph");
    }
  }

  async function handleBuild() {
    setLoading(true);
    setError(null);
    try {
      await buildGraph();
      await loadGraph();
      const response = await searchGraphNodes(query, nodeType);
      setResults(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to build graph");
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const response = await searchGraphNodes(query, nodeType);
      setResults(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search graph");
    }
  }

  async function handleSelect(node: GraphNode) {
    setSelectedNode(node);
    setError(null);
    try {
      setNeighbors(await fetchGraphNeighbors(node.node_id));
    } catch (err) {
      setNeighbors(null);
      setError(err instanceof Error ? err.message : "Failed to load neighbors");
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Knowledge Graph</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Explore deterministic links between articles, sections, concepts, formulas, and Zotero papers.
          </p>
        </div>
        <button
          className="rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={loading}
          type="button"
          onClick={() => void handleBuild()}
        >
          {loading ? "Building..." : "Build graph"}
        </button>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section className="grid gap-3 md:grid-cols-4">
        <SummaryItem label="Nodes" value={graph?.nodes.length ?? 0} />
        <SummaryItem label="Edges" value={graph?.edges.length ?? 0} />
        <SummaryItem label="Articles" value={graph?.source_counts.articles ?? 0} />
        <SummaryItem label="Built" value={graph?.built_at ? new Date(graph.built_at).toLocaleString() : "Not built"} />
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold">Node Types</h2>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          {Object.entries(typeCounts).length ? (
            Object.entries(typeCounts).map(([type, count]) => (
              <span key={type} className="rounded border border-slate-200 px-2 py-1 text-slate-600">
                {type}: {count}
              </span>
            ))
          ) : (
            <span className="text-slate-600">No graph data loaded.</span>
          )}
        </div>
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <form className="grid gap-2 md:grid-cols-[minmax(0,1fr)_180px_auto]" onSubmit={handleSearch}>
          <input
            className="min-w-0 rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950"
            placeholder="Search nodes"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <select
            className="rounded border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-950"
            value={nodeType}
            onChange={(event) => setNodeType(event.target.value as GraphNodeType | "")}
          >
            {nodeTypes.map((type) => (
              <option key={type || "all"} value={type}>
                {type || "all types"}
              </option>
            ))}
          </select>
          <button className="rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white" type="submit">
            Search
          </button>
        </form>
      </section>

      <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="grid gap-3">
          {results.length ? (
            results.map((node) => (
              <button
                key={node.node_id}
                className="rounded border border-slate-200 bg-white p-4 text-left hover:bg-slate-50"
                type="button"
                onClick={() => void handleSelect(node)}
              >
                <span className="block text-base font-semibold">{node.label}</span>
                <span className="mt-1 block text-xs text-slate-500">
                  {node.node_type} · {node.node_id}
                </span>
              </button>
            ))
          ) : (
            <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">
              Search nodes or build the graph to populate results.
            </p>
          )}
        </div>

        <aside className="space-y-4">
          <section className="rounded border border-slate-200 bg-white p-4">
            <h2 className="text-base font-semibold">Selected Node</h2>
            {selectedNode ? (
              <div className="mt-3 space-y-3 text-sm">
                <p className="font-medium">{selectedNode.label}</p>
                <p className="break-all text-xs text-slate-500">{selectedNode.node_id}</p>
                <p className="text-slate-600">{selectedNode.node_type}</p>
                <NodeLink node={selectedNode} />
                <pre className="max-h-56 overflow-auto rounded bg-slate-950 p-3 text-xs leading-5 text-white">
                  {JSON.stringify(selectedNode.metadata, null, 2)}
                </pre>
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-600">Select a node to inspect metadata and neighbors.</p>
            )}
          </section>

          <section className="rounded border border-slate-200 bg-white p-4">
            <h2 className="text-base font-semibold">Neighbors</h2>
            <div className="mt-3 grid gap-2">
              {neighbors?.nodes.length ? (
                neighbors.nodes.map((node) => (
                  <button
                    key={node.node_id}
                    className="rounded border border-slate-100 px-3 py-2 text-left text-sm hover:bg-slate-50"
                    type="button"
                    onClick={() => void handleSelect(node)}
                  >
                    <span className="block font-medium">{node.label}</span>
                    <span className="mt-1 block text-xs text-slate-500">{node.node_type}</span>
                  </button>
                ))
              ) : (
                <p className="text-sm text-slate-600">No neighbors loaded.</p>
              )}
            </div>
          </section>

          <section className="rounded border border-slate-200 bg-white p-4">
            <h2 className="text-base font-semibold">Evidence</h2>
            <div className="mt-3 grid gap-2">
              {neighbors?.edges.length ? (
                neighbors.edges.map((edge) => (
                  <article key={edge.edge_id} className="rounded border border-slate-100 p-3 text-sm">
                    <p className="font-medium">{edge.edge_type}</p>
                    <p className="mt-1 break-all text-xs text-slate-500">{edge.edge_id}</p>
                    <pre className="mt-2 max-h-36 overflow-auto rounded bg-slate-50 p-2 text-xs leading-5 text-slate-700">
                      {JSON.stringify(edge.evidence, null, 2)}
                    </pre>
                  </article>
                ))
              ) : (
                <p className="text-sm text-slate-600">No edge evidence loaded.</p>
              )}
            </div>
          </section>
        </aside>
      </section>
    </section>
  );
}

function SummaryItem({ label, value }: Readonly<{ label: string; value: number | string }>) {
  return (
    <section className="rounded border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </section>
  );
}

function NodeLink({ node }: Readonly<{ node: GraphNode }>) {
  if (node.node_type === "article" && node.source_id) {
    return (
      <Link className="inline-block text-sm text-slate-600 hover:text-slate-950" href={`/articles/${node.source_id}`}>
        Open article
      </Link>
    );
  }
  if (node.node_type === "zotero_item") {
    return (
      <Link className="inline-block text-sm text-slate-600 hover:text-slate-950" href="/zotero">
        Open Zotero
      </Link>
    );
  }
  if (node.source_url) {
    return (
      <a className="inline-block text-sm text-slate-600 hover:text-slate-950" href={node.source_url} rel="noreferrer" target="_blank">
        Source
      </a>
    );
  }
  return null;
}
