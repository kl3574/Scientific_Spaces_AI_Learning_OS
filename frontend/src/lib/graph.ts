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

export type GraphDocument = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  built_at: string | null;
  source_counts: Record<string, number>;
};

export type GraphBuildResponse = {
  node_count: number;
  edge_count: number;
  built_at: string | null;
  source_counts: Record<string, number>;
};

export type GraphSearchResponse = {
  items: GraphNode[];
  total: number;
  query: string;
  node_type: GraphNodeType | null;
};

export type GraphNeighborsResponse = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function buildGraph(): Promise<GraphBuildResponse> {
  return requestJson<GraphBuildResponse>("/graph/build", { method: "POST" });
}

export async function fetchGraph(): Promise<GraphDocument> {
  return requestJson<GraphDocument>("/graph");
}

export async function searchGraphNodes(query: string, nodeType?: GraphNodeType | ""): Promise<GraphSearchResponse> {
  const url = new URL("/graph/nodes", API_BASE_URL);
  if (query.trim()) {
    url.searchParams.set("q", query.trim());
  }
  if (nodeType) {
    url.searchParams.set("node_type", nodeType);
  }
  return requestJsonUrl<GraphSearchResponse>(url);
}

export async function fetchGraphNode(nodeId: string): Promise<GraphNode> {
  return requestJson<GraphNode>(`/graph/nodes/${encodeURIComponent(nodeId)}`);
}

export async function fetchGraphNeighbors(nodeId: string): Promise<GraphNeighborsResponse> {
  return requestJson<GraphNeighborsResponse>(`/graph/nodes/${encodeURIComponent(nodeId)}/neighbors`);
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
