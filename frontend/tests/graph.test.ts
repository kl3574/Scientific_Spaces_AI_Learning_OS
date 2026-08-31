import { strict as assert } from "node:assert";
import test from "node:test";

import {
  fetchGraphNodes,
  fetchGraphSubgraph,
  fetchGraphSummary,
  fetchGraphNode,
} from "../src/lib/graph";
import {
  getConceptProvenance,
  getProvenanceSourceView,
  getSafeDisplayText,
  getSafeExternalUrl,
} from "../src/lib/graphPresentation";
import {
  GRAPH_VISUAL_EDGE_LIMIT,
  GRAPH_VISUAL_NODE_LIMIT,
  createGraphVisualizationModel,
} from "../src/lib/graphVisualization";

type FetchCall = {
  input: string;
  init?: RequestInit;
};

function installFetchStub(payload: unknown): FetchCall[] {
  const calls: FetchCall[] = [];
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ input: input.toString(), init });
    return new Response(JSON.stringify(payload), {
      headers: { "Content-Type": "application/json" },
      status: 200,
    });
  }) as typeof fetch;
  return calls;
}

test("fetchGraphSummary requests only the graph summary endpoint", async () => {
  const calls = installFetchStub({
    node_count: 120,
    edge_count: 240,
    built_at: "2026-07-10T00:00:00Z",
    source_counts: { articles: 20 },
    node_count_by_type: { article: 20, concept: 100 },
  });

  const summary = await fetchGraphSummary();

  assert.equal(calls.length, 1);
  assert.equal(new URL(calls[0].input).pathname, "/graph/summary");
  assert.equal(new URL(calls[0].input).search, "");
  assert.deepEqual(summary.node_count_by_type, { article: 20, concept: 100 });
});

test("fetchGraphNodes sends trimmed filters and pagination", async () => {
  const calls = installFetchStub({
    items: [],
    total: 0,
    page: 3,
    page_size: 20,
    pages: 0,
  });

  await fetchGraphNodes({
    q: "  attention  ",
    node_type: "concept",
    page: 3,
    page_size: 20,
  });

  const url = new URL(calls[0].input);
  assert.equal(url.pathname, "/v1.1/graph/nodes");
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    q: "attention",
    node_type: "concept",
    page: "3",
    page_size: "20",
  });
});

test("fetchGraphSubgraph always sends explicit traversal bounds", async () => {
  const calls = installFetchStub({ nodes: [], edges: [] });

  await fetchGraphSubgraph({
    node_id: "concept:scaled attention",
    depth: 1,
    node_limit: 25,
    edge_limit: 50,
  });

  const url = new URL(calls[0].input);
  assert.equal(url.pathname, "/v1.1/graph/subgraph");
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    node_id: "concept:scaled attention",
    depth: "1",
    node_limit: "25",
    edge_limit: "50",
  });
});

test("fetchGraphNode continues to use legacy detail endpoint", async () => {
  const calls = installFetchStub({
    node_id: "concept:attention",
    node_type: "concept",
    label: "Attention",
    source_id: null,
    source_url: null,
    metadata: {},
  });

  await fetchGraphNode("concept:attention");

  const url = new URL(calls[0].input);
  assert.equal(url.pathname, "/graph/nodes/concept%3Aattention");
});

test("getConceptProvenance reports source and omitted counts", () => {
  const provenance = getConceptProvenance({
    node_id: "concept:attention",
    node_type: "concept",
    label: "Attention",
    source_id: "attention",
    source_url: null,
    metadata: {
      source_count: 4,
      truncated: true,
      sources: [
        {
          article_id: "article-1",
          article_title: "A very long article title",
          article_url: "https://example.com/article-1",
          source_type: "section_content",
          section_title: "Background",
          source_context: "Attention is used here.",
          evidence: "attention",
          local_path: "/home/private/corpus/article.md",
        },
      ],
    },
  });

  assert.ok(provenance);
  assert.equal(provenance.sourceCount, 4);
  assert.equal(provenance.sources.length, 1);
  assert.equal(provenance.omittedCount, 3);
  assert.equal(provenance.truncated, true);
  assert.equal("local_path" in provenance.sources[0], false);
});

test("getProvenanceSourceView collapses returned sources and supports expansion", () => {
  const sources = Array.from({ length: 5 }, (_, index) => ({
    articleId: `article-${index}`,
    articleTitle: `Article ${index}`,
    articleUrl: `https://example.com/${index}`,
    sourceType: "section_content",
    sectionTitle: "Section",
    sourceContext: "Context",
    evidence: "Evidence",
    chunkIndex: index,
  }));

  const collapsed = getProvenanceSourceView(sources, false);
  const expanded = getProvenanceSourceView(sources, true);

  assert.equal(collapsed.sources.length, 3);
  assert.equal(collapsed.hiddenReturnedCount, 2);
  assert.equal(expanded.sources.length, 5);
  assert.equal(expanded.hiddenReturnedCount, 0);
});

test("getSafeExternalUrl permits web URLs and rejects local paths", () => {
  assert.equal(getSafeExternalUrl("https://spaces.ac.cn/archives/6508"), "https://spaces.ac.cn/archives/6508");
  assert.equal(getSafeExternalUrl("file:///home/private/article.md"), null);
  assert.equal(getSafeExternalUrl("/home/private/article.md"), null);
  assert.equal(getSafeExternalUrl("C:\\Users\\private\\article.md"), null);
});

test("getSafeDisplayText rejects arbitrary absolute paths embedded in metadata", () => {
  assert.equal(getSafeDisplayText("Loaded from /workspace/private/article.md"), null);
});

test("createGraphVisualizationModel centers the selected node with typed deterministic positions", () => {
  const subgraph = {
    nodes: [
      graphNode("formula:fisher", "formula", "Fisher information"),
      graphNode("concept:attention", "concept", "Attention"),
      graphNode("article:a", "article", "Article A"),
      graphNode("section:background", "section", "Background"),
      graphNode("zotero:z", "zotero_item", "Paper Z"),
    ],
    edges: [
      graphEdge("edge:2", "concept:attention", "section:background", "explained_by"),
      graphEdge("edge:1", "article:a", "concept:attention", "mentions"),
    ],
  };

  const first = createGraphVisualizationModel(subgraph, "concept:attention");
  const second = createGraphVisualizationModel(
    { nodes: [...subgraph.nodes].reverse(), edges: [...subgraph.edges].reverse() },
    "concept:attention",
  );

  assert.deepEqual(first, second);
  assert.equal(first.centerNodeId, "concept:attention");
  assert.deepEqual(first.nodes.map((node) => node.id), [
    "concept:attention",
    "article:a",
    "section:background",
    "formula:fisher",
    "zotero:z",
  ]);
  assert.deepEqual(first.nodes[0].position, { x: 0, y: 0 });
  assert.deepEqual(first.nodes[1].position, { x: 0, y: -180 });
  assert.equal(first.nodes[0].selected, true);
  assert.equal(first.nodes[0].symbol, "C");
  assert.equal(first.nodes[0].typeLabel, "Concept");
  assert.equal(first.nodes[0].ariaLabel, "Selected Concept: Attention");
  assert.equal(first.edges[0].label, "mentions");
  assert.equal(first.edges[1].label, "explained by");
});

test("createGraphVisualizationModel enforces bounds and removes invalid relationships", () => {
  const center = graphNode("concept:center", "concept", "Center");
  const neighbors = Array.from({ length: 30 }, (_, index) =>
    graphNode(`section:${String(index).padStart(2, "0")}`, "section", `Section ${index}`),
  );
  const edges = [
    ...neighbors.map((node, index) =>
      graphEdge(`edge:${String(index).padStart(2, "0")}`, center.node_id, node.node_id, "has_section"),
    ),
    graphEdge("edge:invalid", center.node_id, "section:missing", "related_to"),
  ];

  const model = createGraphVisualizationModel(
    { nodes: [...neighbors, center, center], edges: [...edges, ...edges] },
    center.node_id,
  );

  assert.equal(model.nodes.length, GRAPH_VISUAL_NODE_LIMIT);
  assert.equal(model.edges.length, GRAPH_VISUAL_NODE_LIMIT - 1);
  assert.ok(model.edges.length <= GRAPH_VISUAL_EDGE_LIMIT);
  assert.equal(new Set(model.nodes.map((node) => node.id)).size, model.nodes.length);
  assert.equal(new Set(model.edges.map((edge) => edge.id)).size, model.edges.length);
  assert.ok(model.edges.every((edge) => model.nodes.some((node) => node.id === edge.source)));
  assert.ok(model.edges.every((edge) => model.nodes.some((node) => node.id === edge.target)));
});

function graphNode(
  nodeId: string,
  nodeType: "article" | "section" | "concept" | "formula" | "zotero_item",
  label: string,
) {
  return {
    node_id: nodeId,
    node_type: nodeType,
    label,
    source_id: null,
    source_url: null,
    metadata: {},
  };
}

function graphEdge(edgeId: string, source: string, target: string, edgeType: string) {
  return {
    edge_id: edgeId,
    source_node_id: source,
    target_node_id: target,
    edge_type: edgeType,
    weight: 1,
    evidence: {},
    metadata: {},
  };
}
