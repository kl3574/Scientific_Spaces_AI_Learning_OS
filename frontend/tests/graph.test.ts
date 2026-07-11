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
