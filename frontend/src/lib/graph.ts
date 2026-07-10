export type GraphNodeType = "article" | "section" | "concept" | "formula" | "zotero_item";

export type GraphNode = {
  node_id: string;
  node_type: GraphNodeType;
  label: string;
  source_id: string | null;
  source_url: string | null;
  metadata: Record<string, unknown>;
};

export type GraphEdge = {
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  weight: number;
  evidence: Record<string, unknown>;
  metadata: Record<string, unknown>;
};

export type GraphSummary = {
  node_count: number;
  edge_count: number;
  built_at: string | null;
  source_counts: Record<string, number>;
  node_count_by_type: Partial<Record<GraphNodeType, number>>;
};

export type GraphNodeQuery = {
  q?: string;
  node_type?: GraphNodeType | "";
  page: number;
  page_size: number;
};

export type GraphNodeListResponse = {
  items: GraphNode[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type GraphSubgraphQuery = {
  node_id: string;
  depth: number;
  node_limit: number;
  edge_limit: number;
};

export type GraphSubgraphResponse = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchGraphSummary(signal?: AbortSignal): Promise<GraphSummary> {
  return requestJson<GraphSummary>("/graph/summary", { signal });
}

export async function fetchGraphNodes(
  query: GraphNodeQuery,
  signal?: AbortSignal,
): Promise<GraphNodeListResponse> {
  const url = new URL("/graph/nodes", API_BASE_URL);
  if (query.q?.trim()) {
    url.searchParams.set("q", query.q.trim());
  }
  if (query.node_type) {
    url.searchParams.set("node_type", query.node_type);
  }
  url.searchParams.set("page", String(query.page));
  url.searchParams.set("page_size", String(query.page_size));
  return requestJsonUrl<GraphNodeListResponse>(url, { signal });
}

export async function fetchGraphNode(nodeId: string, signal?: AbortSignal): Promise<GraphNode> {
  return requestJson<GraphNode>(`/graph/nodes/${encodeURIComponent(nodeId)}`, { signal });
}

export async function fetchGraphSubgraph(
  query: GraphSubgraphQuery,
  signal?: AbortSignal,
): Promise<GraphSubgraphResponse> {
  const url = new URL("/graph/subgraph", API_BASE_URL);
  url.searchParams.set("node_id", query.node_id);
  url.searchParams.set("depth", String(query.depth));
  url.searchParams.set("node_limit", String(query.node_limit));
  url.searchParams.set("edge_limit", String(query.edge_limit));
  return requestJsonUrl<GraphSubgraphResponse>(url, { signal });
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  return requestJsonUrl<T>(new URL(path, API_BASE_URL), init);
}

async function requestJsonUrl<T>(url: URL, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url.toString(), {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Graph request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
