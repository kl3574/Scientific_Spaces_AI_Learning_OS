"use client";

import { FormEvent, useEffect, useState } from "react";

import { GraphLoadState, GraphNodeDetail } from "@/components/GraphNodeDetail";
import {
  GraphNode,
  GraphNodeListResponse,
  GraphNodeType,
  GraphSubgraphResponse,
  GraphSummary,
  fetchGraphNode,
  fetchGraphNodes,
  fetchGraphSubgraph,
  fetchGraphSummary,
} from "@/lib/graph";
import { getSafeDisplayText } from "@/lib/graphPresentation";

const PAGE_SIZE = 20;
const SUBGRAPH_DEPTH = 1;
const SUBGRAPH_NODE_LIMIT = 25;
const SUBGRAPH_EDGE_LIMIT = 50;

const nodeTypes: Array<{ value: GraphNodeType | ""; label: string }> = [
  { value: "", label: "All types" },
  { value: "article", label: "Articles" },
  { value: "section", label: "Sections" },
  { value: "concept", label: "Concepts" },
  { value: "formula", label: "Formulas" },
  { value: "zotero_item", label: "Zotero items" },
];

export function GraphView() {
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [summaryStatus, setSummaryStatus] = useState<GraphLoadState>("idle");
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryRevision, setSummaryRevision] = useState(0);

  const [query, setQuery] = useState("");
  const [nodeType, setNodeType] = useState<GraphNodeType | "">("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [appliedNodeType, setAppliedNodeType] = useState<GraphNodeType | "">("");
  const [page, setPage] = useState(1);
  const [nodePage, setNodePage] = useState<GraphNodeListResponse | null>(null);
  const [nodeStatus, setNodeStatus] = useState<GraphLoadState>("idle");
  const [nodeError, setNodeError] = useState<string | null>(null);
  const [nodeRevision, setNodeRevision] = useState(0);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [detailStatus, setDetailStatus] = useState<GraphLoadState>("idle");
  const [detailError, setDetailError] = useState<string | null>(null);
  const [subgraph, setSubgraph] = useState<GraphSubgraphResponse | null>(null);
  const [subgraphStatus, setSubgraphStatus] = useState<GraphLoadState>("idle");
  const [subgraphError, setSubgraphError] = useState<string | null>(null);
  const [selectionRevision, setSelectionRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadSummary() {
      setSummaryStatus("loading");
      setSummaryError(null);
      try {
        const response = await fetchGraphSummary(controller.signal);
        setSummary(response);
        setSummaryStatus("loaded");
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        setSummary(null);
        setSummaryError(getErrorMessage(error, "Failed to load graph summary"));
        setSummaryStatus("error");
      }
    }

    void loadSummary();
    return () => controller.abort();
  }, [summaryRevision]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadNodes() {
      setNodeStatus("loading");
      setNodeError(null);
      try {
        const response = await fetchGraphNodes(
          {
            q: appliedQuery,
            node_type: appliedNodeType,
            page,
            page_size: PAGE_SIZE,
          },
          controller.signal,
        );
        setNodePage(response);
        setNodeStatus("loaded");
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        setNodePage(null);
        setNodeError(getErrorMessage(error, "Failed to load graph nodes"));
        setNodeStatus("error");
      }
    }

    void loadNodes();
    return () => controller.abort();
  }, [appliedNodeType, appliedQuery, nodeRevision, page]);

  useEffect(() => {
    if (!selectedNodeId) {
      return;
    }
    const controller = new AbortController();

    setSelectedNode(null);
    setDetailStatus("loading");
    setDetailError(null);
    setSubgraph(null);
    setSubgraphStatus("loading");
    setSubgraphError(null);

    async function loadNodeDetail() {
      try {
        const response = await fetchGraphNode(selectedNodeId as string, controller.signal);
        setSelectedNode(response);
        setDetailStatus("loaded");
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        setDetailError(getErrorMessage(error, "Failed to load node details"));
        setDetailStatus("error");
      }
    }

    async function loadSubgraph() {
      try {
        const response = await fetchGraphSubgraph(
          {
            node_id: selectedNodeId as string,
            depth: SUBGRAPH_DEPTH,
            node_limit: SUBGRAPH_NODE_LIMIT,
            edge_limit: SUBGRAPH_EDGE_LIMIT,
          },
          controller.signal,
        );
        setSubgraph(response);
        setSubgraphStatus("loaded");
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        setSubgraphError(getErrorMessage(error, "Failed to load bounded context"));
        setSubgraphStatus("error");
      }
    }

    void loadNodeDetail();
    void loadSubgraph();
    return () => controller.abort();
  }, [selectedNodeId, selectionRevision]);

  function handleFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setAppliedQuery(query.trim());
    setAppliedNodeType(nodeType);
    setNodeRevision((current) => current + 1);
  }

  function clearFilters() {
    setQuery("");
    setNodeType("");
    setAppliedQuery("");
    setAppliedNodeType("");
    setPage(1);
    setNodeRevision((current) => current + 1);
  }

  function selectNode(nodeId: string) {
    setSelectedNodeId(nodeId);
    setSelectionRevision((current) => current + 1);
  }

  const responsePage = nodePage?.page ?? page;
  const responsePages = nodePage?.pages ?? 0;
  const hasFilters = Boolean(query || nodeType || appliedQuery || appliedNodeType);

  return (
    <section className="min-w-0 space-y-6">
      <header className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-semibold">Knowledge Graph</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Explore links between articles, sections, concepts, formulas, and Zotero papers.
        </p>
      </header>

      <SummaryPanel
        summary={summary}
        status={summaryStatus}
        error={summaryError}
        onRetry={() => setSummaryRevision((current) => current + 1)}
      />

      <section className="rounded border border-slate-200 bg-white p-4">
        <form className="grid min-w-0 gap-3 md:grid-cols-[minmax(0,1fr)_180px_auto] md:items-end" onSubmit={handleFilters}>
          <label className="min-w-0 text-xs font-medium text-slate-600">
            Search
            <input
              className="mt-1 block w-full min-w-0 rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none focus:border-slate-950"
              name="q"
              placeholder="Title, concept, or formula"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label className="text-xs font-medium text-slate-600">
            Type
            <select
              className="mt-1 block w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none focus:border-slate-950"
              name="node_type"
              value={nodeType}
              onChange={(event) => setNodeType(event.target.value as GraphNodeType | "")}
            >
              {nodeTypes.map((type) => (
                <option key={type.value || "all"} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={nodeStatus === "loading"}
              type="submit"
            >
              Apply
            </button>
            {hasFilters ? (
              <button
                className="rounded border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
                type="button"
                onClick={clearFilters}
              >
                Clear
              </button>
            ) : null}
          </div>
        </form>
      </section>

      <section className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(300px,380px)] lg:items-start">
        <section className="min-w-0" aria-busy={nodeStatus === "loading"}>
          <div className="flex flex-col gap-2 border-b border-slate-200 pb-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-base font-semibold">Nodes</h2>
              <p className="mt-1 text-xs text-slate-500">{nodeStatus === "loaded" ? getResultRange(nodePage) : ""}</p>
            </div>
            {nodeStatus === "loaded" ? (
              <Pagination
                page={responsePage}
                pages={responsePages}
                onPrevious={() => setPage(Math.max(1, responsePage - 1))}
                onNext={() => setPage(responsePage + 1)}
              />
            ) : null}
          </div>

          {nodeStatus === "loading" ? (
            <p className="py-5 text-sm text-slate-600" role="status">
              Loading nodes...
            </p>
          ) : null}
          {nodeStatus === "error" ? (
            <div className="flex items-start justify-between gap-3 py-5" role="alert">
              <p className="min-w-0 break-words text-sm text-red-700">{nodeError}</p>
              <button
                className="shrink-0 text-xs font-medium text-slate-600 hover:text-slate-950"
                type="button"
                onClick={() => setNodeRevision((current) => current + 1)}
              >
                Retry
              </button>
            </div>
          ) : null}
          {nodeStatus === "loaded" && nodePage?.items.length === 0 ? (
            <p className="py-5 text-sm text-slate-600">
              {appliedQuery || appliedNodeType ? "No nodes match the current filters." : "No graph nodes are available."}
            </p>
          ) : null}
          {nodeStatus === "loaded" && nodePage?.items.length ? (
            <div className="grid min-w-0 gap-3 pt-4">
              {nodePage.items.map((node) => (
                <button
                  key={node.node_id}
                  aria-pressed={selectedNodeId === node.node_id}
                  className={`min-w-0 rounded border bg-white p-4 text-left hover:bg-slate-50 ${
                    selectedNodeId === node.node_id ? "border-slate-950" : "border-slate-200"
                  }`}
                  type="button"
                  onClick={() => selectNode(node.node_id)}
                >
                  <span className="block min-w-0 break-words text-base font-semibold leading-6 [overflow-wrap:anywhere]">
                    {getSafeDisplayText(node.label) ?? "Untitled node"}
                  </span>
                  <span className="mt-2 inline-block rounded border border-slate-200 px-2 py-1 text-xs text-slate-500">
                    {formatNodeType(node.node_type)}
                  </span>
                </button>
              ))}
            </div>
          ) : null}
        </section>

        <GraphNodeDetail
          bounds={{ depth: SUBGRAPH_DEPTH, nodeLimit: SUBGRAPH_NODE_LIMIT, edgeLimit: SUBGRAPH_EDGE_LIMIT }}
          detailError={detailError}
          detailStatus={detailStatus}
          node={selectedNode}
          subgraph={subgraph}
          subgraphError={subgraphError}
          subgraphStatus={subgraphStatus}
          onRetry={() => setSelectionRevision((current) => current + 1)}
          onSelectNode={selectNode}
        />
      </section>
    </section>
  );
}

function SummaryPanel({
  summary,
  status,
  error,
  onRetry,
}: Readonly<{
  summary: GraphSummary | null;
  status: GraphLoadState;
  error: string | null;
  onRetry: () => void;
}>) {
  if (status === "loading" || status === "idle") {
    return (
      <section aria-busy="true">
        <h2 className="sr-only">Graph Summary</h2>
        <p className="text-sm text-slate-600" role="status">
          Loading graph summary...
        </p>
      </section>
    );
  }

  if (status === "error") {
    return (
      <section className="flex items-start justify-between gap-3 border border-red-200 bg-red-50 p-3" role="alert">
        <p className="min-w-0 break-words text-sm text-red-700">{error}</p>
        <button className="shrink-0 text-xs font-medium text-red-700 hover:text-red-950" type="button" onClick={onRetry}>
          Retry
        </button>
      </section>
    );
  }

  if (!summary) {
    return null;
  }

  const typeCounts = Object.entries(summary.node_count_by_type).filter((entry): entry is [string, number] => {
    return typeof entry[1] === "number";
  });

  return (
    <section className="space-y-3">
      <h2 className="sr-only">Graph Summary</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryItem label="Nodes" value={formatCount(summary.node_count)} />
        <SummaryItem label="Edges" value={formatCount(summary.edge_count)} />
        <SummaryItem label="Articles" value={formatCount(summary.source_counts.articles ?? 0)} />
        <SummaryItem label="Built" value={formatBuiltAt(summary.built_at)} compact />
      </div>
      {summary.node_count === 0 ? <p className="text-sm text-slate-600">The graph summary is empty.</p> : null}
      {typeCounts.length ? (
        <div className="flex flex-wrap gap-2 text-xs text-slate-600">
          {typeCounts.map(([type, count]) => (
            <span key={type} className="rounded border border-slate-200 bg-white px-2 py-1">
              {formatNodeType(type as GraphNodeType)}: {formatCount(count)}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function SummaryItem({ label, value, compact = false }: Readonly<{ label: string; value: string; compact?: boolean }>) {
  return (
    <section className="min-w-0 rounded border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-2 min-w-0 break-words font-semibold [overflow-wrap:anywhere] ${compact ? "text-sm leading-6" : "text-2xl"}`}>
        {value}
      </p>
    </section>
  );
}

function Pagination({
  page,
  pages,
  onPrevious,
  onNext,
}: Readonly<{ page: number; pages: number; onPrevious: () => void; onNext: () => void }>) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-slate-500">
        Page {page} of {Math.max(pages, 1)}
      </span>
      <button
        className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
        disabled={page <= 1}
        type="button"
        onClick={onPrevious}
      >
        Previous
      </button>
      <button
        className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
        disabled={pages === 0 || page >= pages}
        type="button"
        onClick={onNext}
      >
        Next
      </button>
    </div>
  );
}

function getResultRange(response: GraphNodeListResponse | null): string {
  if (!response || response.total === 0) {
    return "No results";
  }
  const first = (response.page - 1) * response.page_size + 1;
  const last = Math.min(response.page * response.page_size, response.total);
  return `Showing ${first}-${last} of ${formatCount(response.total)}`;
}

function formatBuiltAt(value: string | null): string {
  if (!value) {
    return "Not built";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unknown" : date.toLocaleString();
}

function formatCount(value: number): string {
  return new Intl.NumberFormat().format(value);
}

function formatNodeType(nodeType: GraphNodeType): string {
  return nodeTypes.find((type) => type.value === nodeType)?.label.replace(/s$/, "") ?? "Node";
}

function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
