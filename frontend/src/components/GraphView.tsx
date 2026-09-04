"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { GraphContextList, GraphLoadState, GraphNodeDetail } from "@/components/GraphNodeDetail";
import { GraphVisualization } from "@/components/GraphVisualization";
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
import type { GraphSearchState } from "@/lib/globalSearch";
import {
  normalizeGlobalSearchQuery,
  normalizeGraphNodeId,
  parseGraphSearchState,
} from "@/lib/globalSearch";
import { getSafeDisplayText } from "@/lib/graphPresentation";
import {
  createGraphWorkspaceHref,
  getGraphCanonicalizationAction,
  getGraphInitialPanel,
  getGraphSelectionHistoryAction,
  type GraphExplorePanel,
  type GraphWorkspaceMode,
} from "@/lib/graphWorkspace";
import {
  parseLearningWorkflowContext,
  type LearningWorkflowContext,
} from "@/lib/learningWorkflow";

const PAGE_SIZE = 20;
const SUBGRAPH_DEPTH = 1;
const SUBGRAPH_NODE_LIMIT = 25;
const SUBGRAPH_EDGE_LIMIT = 50;
const MAX_ANNOUNCEMENT_LABEL_LENGTH = 120;

const nodeTypes: Array<{ value: GraphNodeType | ""; label: string }> = [
  { value: "", label: "All types" },
  { value: "article", label: "Articles" },
  { value: "section", label: "Sections" },
  { value: "concept", label: "Concepts" },
  { value: "formula", label: "Formulas" },
  { value: "zotero_item", label: "Zotero items" },
];

export function GraphView({
  initialContext,
  initialSearch,
}: Readonly<{
  initialContext: LearningWorkflowContext | null;
  initialSearch: GraphSearchState;
}>) {
  const pathname = usePathname();
  const routeSearchParams = useSearchParams();
  const routeSearch = routeSearchParams.toString();
  const initialNodeId = initialContext?.nodeId ?? initialSearch.nodeId;
  const [workflowContext, setWorkflowContext] = useState(initialContext);
  const [workspaceMode, setWorkspaceMode] = useState<GraphWorkspaceMode>("explore");
  const [explorePanel, setExplorePanel] = useState<GraphExplorePanel>(() => getGraphInitialPanel(initialNodeId));
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [summaryStatus, setSummaryStatus] = useState<GraphLoadState>("idle");
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryRevision, setSummaryRevision] = useState(0);

  const [query, setQuery] = useState(initialSearch.query);
  const [nodeType, setNodeType] = useState<GraphNodeType | "">("");
  const [appliedQuery, setAppliedQuery] = useState(initialSearch.query);
  const [appliedNodeType, setAppliedNodeType] = useState<GraphNodeType | "">("");
  const [page, setPage] = useState(1);
  const [nodePage, setNodePage] = useState<GraphNodeListResponse | null>(null);
  const [nodeStatus, setNodeStatus] = useState<GraphLoadState>("idle");
  const [nodeError, setNodeError] = useState<string | null>(null);
  const [nodeRevision, setNodeRevision] = useState(0);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(initialNodeId);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [detailStatus, setDetailStatus] = useState<GraphLoadState>("idle");
  const [detailError, setDetailError] = useState<string | null>(null);
  const [subgraph, setSubgraph] = useState<GraphSubgraphResponse | null>(null);
  const [subgraphStatus, setSubgraphStatus] = useState<GraphLoadState>("idle");
  const [subgraphError, setSubgraphError] = useState<string | null>(null);
  const [selectionRevision, setSelectionRevision] = useState(0);
  const [selectionAnnouncement, setSelectionAnnouncement] = useState("");
  const [focusRevision, setFocusRevision] = useState(0);
  const routeNodeRef = useRef(initialNodeId);
  const routeQueryRef = useRef(initialSearch.query);
  const appliedQueryRef = useRef(initialSearch.query);
  const pendingFocusRef = useRef<"detail" | "results" | "context" | null>(null);
  const pendingDetailScrollRef = useRef(Boolean(initialNodeId));
  const pendingContextFocusRef = useRef(false);
  const selectionOriginRef = useRef<string | null>(null);
  const detailRegionRef = useRef<HTMLDivElement>(null);
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);
  const contextRegionRef = useRef<HTMLElement>(null);
  const resultButtonRefs = useRef(new Map<string, HTMLButtonElement>());

  useEffect(() => {
    if (pathname !== "/graph") {
      return;
    }
    const params = new URLSearchParams(routeSearch);
    const nextSearch = parseGraphSearchState(params);
    const nextContext = parseLearningWorkflowContext(params);
    const nextNodeId = nextContext?.nodeId ?? nextSearch.nodeId;
    const canonicalHref = createGraphWorkspaceHref({
      nodeId: nextNodeId,
      query: nextSearch.query,
      context: nextContext,
    });
    const currentHref = `${pathname}${window.location.search}${window.location.hash}`;

    if (getGraphCanonicalizationAction(currentHref, canonicalHref) === "replace") {
      window.history.replaceState(null, "", canonicalHref);
    }

    setWorkflowContext(nextContext);
    if (nextSearch.query !== routeQueryRef.current) {
      routeQueryRef.current = nextSearch.query;
      if (nextSearch.query !== appliedQueryRef.current) {
        appliedQueryRef.current = nextSearch.query;
        setQuery(nextSearch.query);
        setAppliedQuery(nextSearch.query);
        setNodeType("");
        setAppliedNodeType("");
        setPage(1);
        setNodeRevision((current) => current + 1);
      }
    }

    if (nextNodeId === routeNodeRef.current) {
      return;
    }
    routeNodeRef.current = nextNodeId;
    selectionOriginRef.current = null;
    pendingDetailScrollRef.current = Boolean(nextNodeId);
    setSelectedNodeId(nextNodeId);
    setSelectedNode(null);
    setDetailError(null);
    setSubgraph(null);
    setSubgraphError(null);
    if (nextNodeId) {
      setDetailStatus("loading");
      setSubgraphStatus("loading");
      setExplorePanel("selected");
      if (workspaceMode === "context") {
        pendingContextFocusRef.current = true;
        requestFocus("context");
      } else {
        requestFocus("detail");
      }
    } else {
      setExplorePanel("results");
      setDetailStatus("idle");
      setSubgraphStatus("idle");
      requestFocus(workspaceMode === "context" ? "context" : "results");
    }
  }, [pathname, routeSearch, workspaceMode]);

  useEffect(() => {
    if (!pendingFocusRef.current) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      const target = pendingFocusRef.current;
      pendingFocusRef.current = null;
      if (target === "detail") {
        detailRegionRef.current?.focus({ preventScroll: true });
        if (isNarrowLayout()) {
          pendingDetailScrollRef.current = !isGraphLayoutSettled(
            detailStatus,
            nodeStatus,
            summaryStatus,
          );
          detailRegionRef.current?.scrollIntoView({ block: "start", behavior: "auto" });
        }
        return;
      }
      if (target === "context") {
        contextRegionRef.current?.focus({ preventScroll: true });
        contextRegionRef.current?.scrollIntoView({ block: "start", behavior: "auto" });
        return;
      }
      const origin = selectionOriginRef.current;
      (origin ? resultButtonRefs.current.get(origin) : null)?.focus();
      if (!origin || document.activeElement !== resultButtonRefs.current.get(origin)) {
        resultsHeadingRef.current?.focus();
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [detailStatus, explorePanel, focusRevision, nodePage, nodeStatus, summaryStatus, workspaceMode]);

  useEffect(() => {
    if (
      !pendingDetailScrollRef.current
      || !selectedNodeId
      || !isNarrowLayout()
    ) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      detailRegionRef.current?.scrollIntoView({ block: "start", behavior: "auto" });
      if (isGraphLayoutSettled(detailStatus, nodeStatus, summaryStatus)) {
        pendingDetailScrollRef.current = false;
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [detailStatus, nodeStatus, selectedNodeId, summaryStatus]);

  useEffect(() => {
    if (!pendingContextFocusRef.current || workspaceMode !== "context") {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      const region = contextRegionRef.current;
      const activeElement = document.activeElement;
      if (
        region
        && (!activeElement || activeElement === document.body || region.contains(activeElement))
      ) {
        region.focus({ preventScroll: true });
      }
      if (subgraphStatus === "loaded" || subgraphStatus === "error") {
        pendingContextFocusRef.current = false;
      }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [selectedNodeId, subgraphStatus, workspaceMode]);

  useEffect(() => {
    if (!selectedNodeId) {
      setSelectionAnnouncement("No graph node is selected.");
      return;
    }
    if (detailStatus === "loading" || detailStatus === "idle") {
      setSelectionAnnouncement("Loading selected node details.");
      return;
    }
    if (detailStatus === "error") {
      setSelectionAnnouncement("Selected node details are unavailable.");
      return;
    }
    const label = getBoundedAnnouncementLabel(selectedNode?.label);
    setSelectionAnnouncement(`Selected ${selectedNode ? formatNodeType(selectedNode.node_type) : "node"}: ${label}. Details ready.`);
  }, [detailStatus, selectedNode, selectedNodeId]);

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
    const nextQuery = normalizeGlobalSearchQuery(query);
    setPage(1);
    setQuery(nextQuery);
    setAppliedQuery(nextQuery);
    appliedQueryRef.current = nextQuery;
    setAppliedNodeType(nodeType);
    setNodeRevision((current) => current + 1);
    replaceCanonicalRoute(nextQuery);
  }

  function clearFilters() {
    setQuery("");
    setNodeType("");
    setAppliedQuery("");
    appliedQueryRef.current = "";
    setAppliedNodeType("");
    setPage(1);
    setNodeRevision((current) => current + 1);
    replaceCanonicalRoute("");
  }

  function replaceCanonicalRoute(nextQuery: string) {
    const canonicalHref = createGraphWorkspaceHref({
      nodeId: selectedNodeId,
      query: nextQuery,
      context: workflowContext,
    });
    const currentHref = `${window.location.pathname}${window.location.search}`;
    routeQueryRef.current = nextQuery;
    if (getGraphCanonicalizationAction(currentHref, canonicalHref) === "replace") {
      window.history.replaceState(null, "", canonicalHref);
    }
  }

  function selectNode(
    nodeId: string,
    options: Readonly<{ source: "results" | "context"; focusDetail?: boolean }>,
  ) {
    const safeNodeId = normalizeGraphNodeId(nodeId);
    if (!safeNodeId) {
      return;
    }
    if (options.source === "results") {
      selectionOriginRef.current = safeNodeId;
      setWorkspaceMode("explore");
      setExplorePanel("selected");
      if (options.focusDetail || isNarrowLayout()) {
        requestFocus("detail");
      }
    }

    const historyAction = getGraphSelectionHistoryAction(selectedNodeId, safeNodeId);
    if (historyAction === "none") {
      return;
    }
    if (options.source === "context") {
      pendingContextFocusRef.current = true;
      contextRegionRef.current?.focus({ preventScroll: true });
      requestFocus("context");
    }

    routeNodeRef.current = safeNodeId;
    routeQueryRef.current = appliedQuery;
    setSelectedNode(null);
    setDetailError(null);
    setDetailStatus("loading");
    setSubgraph(null);
    setSubgraphError(null);
    setSubgraphStatus("loading");
    setSelectedNodeId(safeNodeId);
    window.history.pushState(
      null,
      "",
      createGraphWorkspaceHref({
        nodeId: safeNodeId,
        query: appliedQuery,
        context: workflowContext,
      }),
    );
  }

  function requestFocus(target: "detail" | "results" | "context") {
    pendingFocusRef.current = target;
    setFocusRevision((current) => current + 1);
  }

  function showResults() {
    setWorkspaceMode("explore");
    setExplorePanel("results");
    requestFocus("results");
  }

  function showSelected() {
    if (!selectedNodeId) {
      return;
    }
    setWorkspaceMode("explore");
    setExplorePanel("selected");
    requestFocus("detail");
  }

  function showContext() {
    setWorkspaceMode("context");
    requestFocus("context");
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

      {workflowContext ? (
        <section
          data-testid="learning-workflow-context"
          className="flex flex-col gap-3 border-y border-emerald-200 bg-emerald-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase text-emerald-800">Current article</p>
            <p className="mt-1 break-words text-sm font-medium text-emerald-950">
              {workflowContext.articleTitle ?? workflowContext.articleId}
            </p>
          </div>
          <Link
            className="w-fit shrink-0 rounded border border-emerald-300 bg-white px-3 py-2 text-sm font-semibold text-emerald-900 hover:border-emerald-600"
            href={workflowContext.returnTo}
          >
            Return to article
          </Link>
        </section>
      ) : null}

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

      <section className="flex flex-col gap-3 border-y border-slate-200 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">Graph workspace</h2>
          <p className="mt-1 text-xs text-slate-500">Browse nodes or inspect the bounded context.</p>
        </div>
        <div aria-label="Graph workspace view" className="inline-flex w-fit rounded border border-slate-300 bg-white p-1" role="group">
          <button
            aria-controls="graph-explore-workspace"
            aria-pressed={workspaceMode === "explore"}
            className={`rounded px-3 py-1.5 text-xs font-semibold ${
              workspaceMode === "explore" ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
            type="button"
            onClick={() => setWorkspaceMode("explore")}
          >
            Explore
          </button>
          <button
            aria-controls="graph-context-workspace"
            aria-pressed={workspaceMode === "context"}
            className={`rounded px-3 py-1.5 text-xs font-semibold ${
              workspaceMode === "context" ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
            type="button"
            onClick={showContext}
          >
            Knowledge context
          </button>
        </div>
      </section>

      <p className="sr-only" aria-atomic="true" aria-live="polite" data-testid="graph-selection-status">
        {selectionAnnouncement}
      </p>

      <section aria-label="Explore graph nodes" hidden={workspaceMode !== "explore"} id="graph-explore-workspace">
        <div aria-label="Explore panel" className="mb-4 inline-flex w-fit rounded border border-slate-300 bg-white p-1 lg:hidden" role="group">
          <button
            aria-controls="graph-results-panel"
            aria-pressed={explorePanel === "results"}
            className={`rounded px-3 py-1.5 text-xs font-semibold ${
              explorePanel === "results" ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
            type="button"
            onClick={showResults}
          >
            Results
          </button>
          <button
            aria-controls="graph-selected-panel"
            aria-pressed={explorePanel === "selected"}
            className={`rounded px-3 py-1.5 text-xs font-semibold ${
              explorePanel === "selected" ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100"
            }`}
            disabled={!selectedNodeId}
            type="button"
            onClick={showSelected}
          >
            Selected
          </button>
        </div>

        <section className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(300px,380px)] lg:items-start">
          <section
            aria-busy={nodeStatus === "loading"}
            className={`${explorePanel === "results" ? "block" : "hidden"} min-w-0 lg:block`}
            data-testid="graph-node-results"
            id="graph-results-panel"
          >
          <div className="flex flex-col gap-2 border-b border-slate-200 pb-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="scroll-mt-24 text-base font-semibold" ref={resultsHeadingRef} tabIndex={-1}>Nodes</h2>
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
                  data-testid={`graph-result-node-${node.node_id}`}
                  ref={(element) => {
                    if (element) {
                      resultButtonRefs.current.set(node.node_id, element);
                    } else {
                      resultButtonRefs.current.delete(node.node_id);
                    }
                  }}
                  type="button"
                  onClick={(event) => selectNode(node.node_id, { source: "results", focusDetail: event.detail === 0 })}
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

          <div
            aria-labelledby="graph-selected-node-heading"
            className={`${explorePanel === "selected" ? "block" : "hidden"} min-w-0 scroll-mt-24 focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700 lg:sticky lg:top-16 lg:block lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto lg:overscroll-contain lg:pr-1`}
            data-testid="graph-selected-region"
            id="graph-selected-panel"
            ref={detailRegionRef}
            role="region"
            tabIndex={-1}
          >
            <GraphNodeDetail
              detailError={detailError}
              detailStatus={detailStatus}
              node={selectedNode}
              onBackToResults={showResults}
              onRetry={() => {
                requestFocus("detail");
                setSelectionRevision((current) => current + 1);
              }}
              onShowContext={showContext}
            />
          </div>
        </section>
      </section>

      <section
        aria-labelledby="graph-context-heading"
        className="min-w-0 scroll-mt-24 focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
        hidden={workspaceMode !== "context"}
        id="graph-context-workspace"
        ref={contextRegionRef}
        role="region"
        tabIndex={-1}
      >
        {workspaceMode === "context" ? (
          <GraphContextExplorer
            node={selectedNode}
            selectedNodeId={selectedNodeId}
            subgraph={subgraph}
            subgraphError={subgraphError}
            subgraphStatus={subgraphStatus}
            onInspectSelected={showSelected}
            onRetry={() => {
              requestFocus("context");
              setSelectionRevision((current) => current + 1);
            }}
            onSelectNode={(nodeId) => selectNode(nodeId, { source: "context" })}
          />
        ) : null}
      </section>
    </section>
  );
}

function GraphContextExplorer({
  node,
  selectedNodeId,
  subgraph,
  subgraphStatus,
  subgraphError,
  onInspectSelected,
  onSelectNode,
  onRetry,
}: Readonly<{
  node: GraphNode | null;
  selectedNodeId: string | null;
  subgraph: GraphSubgraphResponse | null;
  subgraphStatus: GraphLoadState;
  subgraphError: string | null;
  onInspectSelected: () => void;
  onSelectNode: (nodeId: string) => void;
  onRetry: () => void;
}>) {
  const [viewMode, setViewMode] = useState<"map" | "list">("map");
  const bounds = {
    depth: SUBGRAPH_DEPTH,
    nodeLimit: SUBGRAPH_NODE_LIMIT,
    edgeLimit: SUBGRAPH_EDGE_LIMIT,
  };

  return (
    <section className="min-w-0" data-testid="graph-context-explorer">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-base font-semibold" id="graph-context-heading">Knowledge Context</h2>
          <p className="mt-1 text-xs text-slate-500">
            Explore the selected node as a visual map or an accessible relationship list.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            className="rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:border-slate-600 disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={!selectedNodeId}
            type="button"
            onClick={onInspectSelected}
          >
            Inspect selected
          </button>
          <div
            aria-label="Knowledge context view"
            className="inline-flex w-fit rounded border border-slate-300 bg-white p-1"
            role="group"
          >
            <button
              aria-controls="graph-context-panel"
              aria-pressed={viewMode === "map"}
              className={`rounded px-3 py-1.5 text-xs font-semibold ${
                viewMode === "map" ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
              data-testid="graph-view-map"
              type="button"
              onClick={() => setViewMode("map")}
            >
              Map
            </button>
            <button
              aria-controls="graph-context-panel"
              aria-pressed={viewMode === "list"}
              className={`rounded px-3 py-1.5 text-xs font-semibold ${
                viewMode === "list" ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
              data-testid="graph-view-list"
              type="button"
              onClick={() => setViewMode("list")}
            >
              List
            </button>
          </div>
        </div>
      </header>

      <div className="mt-4 min-w-0" id="graph-context-panel">
        {viewMode === "map" ? (
          <GraphMapState
            selectedNodeId={selectedNodeId}
            subgraph={subgraph}
            subgraphError={subgraphError}
            subgraphStatus={subgraphStatus}
            onRetry={onRetry}
            onSelectNode={onSelectNode}
          />
        ) : (
          <GraphContextList
            bounds={bounds}
            node={node}
            subgraph={subgraph}
            subgraphError={subgraphError}
            subgraphStatus={subgraphStatus}
            onRetry={onRetry}
            onSelectNode={onSelectNode}
          />
        )}
      </div>
    </section>
  );
}

function GraphMapState({
  selectedNodeId,
  subgraph,
  subgraphStatus,
  subgraphError,
  onSelectNode,
  onRetry,
}: Readonly<{
  selectedNodeId: string | null;
  subgraph: GraphSubgraphResponse | null;
  subgraphStatus: GraphLoadState;
  subgraphError: string | null;
  onSelectNode: (nodeId: string) => void;
  onRetry: () => void;
}>) {
  if (!selectedNodeId || subgraphStatus === "idle") {
    return <p className="border-y border-slate-200 py-5 text-sm text-slate-600">Select a node to build its visual context.</p>;
  }
  if (subgraphStatus === "loading") {
    return (
      <p className="border-y border-slate-200 py-5 text-sm text-slate-600" role="status">
        Loading visual context...
      </p>
    );
  }
  if (subgraphStatus === "error") {
    return (
      <div className="flex items-start justify-between gap-3 border border-red-200 bg-red-50 p-4" role="alert">
        <p className="min-w-0 break-words text-sm text-red-700">{subgraphError}</p>
        <button className="shrink-0 text-xs font-semibold text-red-700 hover:text-red-950" type="button" onClick={onRetry}>
          Retry
        </button>
      </div>
    );
  }
  if (!subgraph || !subgraph.nodes.length) {
    return <p className="border-y border-slate-200 py-5 text-sm text-slate-600">No visual context is available.</p>;
  }
  return (
    <GraphVisualization
      selectedNodeId={selectedNodeId}
      subgraph={subgraph}
      onSelectNode={onSelectNode}
    />
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
      <div className="grid grid-cols-2 gap-px overflow-hidden border border-slate-200 bg-slate-200 lg:grid-cols-4">
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
    <section className="min-w-0 bg-white p-3 sm:p-4">
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

function isNarrowLayout(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(max-width: 1023px)").matches;
}

function isGraphLayoutSettled(
  detailStatus: GraphLoadState,
  nodeStatus: GraphLoadState,
  summaryStatus: GraphLoadState,
): boolean {
  return [detailStatus, nodeStatus, summaryStatus].every(
    (status) => status === "loaded" || status === "error",
  );
}

function getBoundedAnnouncementLabel(value: unknown): string {
  const label = getSafeDisplayText(value) ?? "Untitled node";
  if (label.length <= MAX_ANNOUNCEMENT_LABEL_LENGTH) {
    return label;
  }
  return `${label.slice(0, MAX_ANNOUNCEMENT_LABEL_LENGTH - 3)}...`;
}
