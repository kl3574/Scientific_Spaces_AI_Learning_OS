import assert from "node:assert/strict";
import test from "node:test";

import type { ArticleListResponse } from "../src/lib/articles";
import type { GraphNodeListResponse } from "../src/lib/graph";
import {
  GLOBAL_SEARCH_LIMIT,
  createGraphSearchHref,
  getWorkspaceQuickResults,
  normalizeGlobalSearchQuery,
  parseGraphSearchState,
  searchGlobalContent,
  type GlobalSearchProviders,
} from "../src/lib/globalSearch";
import type { ReferencePage } from "../src/lib/references";

test("global query normalization removes control whitespace and enforces its bound", () => {
  assert.equal(normalizeGlobalSearchQuery("  Fisher\n\t information  "), "Fisher information");
  assert.equal(normalizeGlobalSearchQuery(` ${"x".repeat(140)} `).length, 120);
  assert.equal(normalizeGlobalSearchQuery("\u0000CRB\u007f"), "CRB");
});

test("empty quick navigation covers every stable workspace and filters readably", () => {
  const all = getWorkspaceQuickResults("");

  assert.deepEqual(all.map((result) => result.title), [
    "Dashboard",
    "Saved",
    "Session",
    "Articles",
    "References",
    "Graph",
    "Tutor",
  ]);
  assert.deepEqual(
    getWorkspaceQuickResults("tut").map((result) => ({ title: result.title, href: result.href })),
    [{ title: "Tutor", href: "/tutor" }],
  );
  assert.equal(all.some((result) => result.title.includes("workspace:")), false);
});

test("global search aggregates bounded readable results through existing providers", async () => {
  const calls: Array<[string, string, number]> = [];
  const providers: GlobalSearchProviders = {
    articles: async (query, limit) => {
      calls.push(["articles", query, limit]);
      return articlePage();
    },
    references: async (query, limit) => {
      calls.push(["references", query, limit]);
      return referencePage();
    },
    graph: async (query, limit) => {
      calls.push(["graph", query, limit]);
      return graphPage();
    },
  };

  const response = await searchGlobalContent("  attention ", providers);

  assert.deepEqual(calls, [
    ["articles", "attention", GLOBAL_SEARCH_LIMIT],
    ["references", "attention", GLOBAL_SEARCH_LIMIT],
    ["graph", "attention", GLOBAL_SEARCH_LIMIT],
  ]);
  assert.equal(response.query, "attention");
  assert.deepEqual(response.groups.map((group) => [group.label, group.total]), [
    ["Articles", 14],
    ["References", 8],
    ["Knowledge Graph", 3],
  ]);
  assert.deepEqual(response.failures, []);

  const article = response.groups.find((group) => group.source === "articles")?.items[0];
  const references = response.groups.find((group) => group.source === "references")?.items ?? [];
  const reference = references[0];
  const internalReference = references[1];
  const citationReference = references[2];
  const graph = response.groups.find((group) => group.source === "graph")?.items[0];
  assert.ok(article);
  assert.ok(reference);
  assert.ok(internalReference);
  assert.ok(citationReference);
  assert.ok(graph);
  assert.equal(article.title, "Attention mechanisms");
  assert.equal(article.description.includes("#"), false);
  assert.match(article.href, /^\/articles\/article-attention\?/);
  assert.match(article.href, /from=%2Farticles%3Fq%3Dattention%26sort%3Drelevance/);
  assert.equal(reference.title, "DOI 10.1000/attention");
  assert.match(reference.description, /Attention mechanisms/);
  assert.match(reference.href, /^\/articles\/article-attention\?/);
  assert.equal(internalReference.title, "Related Article link");
  assert.equal(internalReference.title.includes("\\sqrt"), false);
  assert.equal(internalReference.description.includes("reference:private-id"), false);
  assert.equal(internalReference.description.includes("[#]"), false);
  assert.equal(citationReference.title, "Citation text");
  assert.match(citationReference.description, /Article root$/);
  assert.equal(graph.title, "Attention");
  assert.equal(graph.href, "/graph?node_id=concept%3Aattention&q=attention");

  const visibleText = response.groups
    .flatMap((group) => group.items)
    .map((result) => `${result.title} ${result.description}`)
    .join(" ");
  assert.equal(visibleText.includes("reference:private-id"), false);
  assert.equal(visibleText.includes("concept:attention"), false);
  assert.equal(
    response.groups.flatMap((group) => group.items).every((result) => result.description.length <= 180),
    true,
  );
});

test("one failed source retains healthy groups and reports the bounded failure", async () => {
  const providers: GlobalSearchProviders = {
    articles: async () => articlePage(),
    references: async () => {
      throw new Error("reference store unavailable");
    },
    graph: async () => graphPage(),
  };

  const response = await searchGlobalContent("attention", providers);

  assert.deepEqual(response.groups.map((group) => group.label), ["Articles", "Knowledge Graph"]);
  assert.deepEqual(response.failures, [
    { source: "references", label: "References", message: "References search is unavailable." },
  ]);
});

test("graph search routes are canonical and reject unsafe identifiers", () => {
  assert.equal(
    createGraphSearchHref("concept:attention", " Fisher  information "),
    "/graph?node_id=concept%3Aattention&q=Fisher+information",
  );
  assert.deepEqual(
    parseGraphSearchState(new URLSearchParams("node_id=concept%3Aattention&q=Fisher+information")),
    { nodeId: "concept:attention", query: "Fisher information" },
  );
  assert.deepEqual(
    parseGraphSearchState({ node_id: "../../private", q: " x\u0000 y " }),
    { nodeId: null, query: "x y" },
  );

  const unicodeNodeId = "section:attention-basics:0:Attention机制";
  const unicodeHref = createGraphSearchHref(unicodeNodeId, "Attention机制");
  const unicodeUrl = new URL(unicodeHref, "http://local");
  assert.equal(unicodeUrl.searchParams.get("node_id"), unicodeNodeId);
  assert.deepEqual(parseGraphSearchState(unicodeUrl.searchParams), {
    nodeId: unicodeNodeId,
    query: "Attention机制",
  });
});

function articlePage(): ArticleListResponse {
  return {
    items: [
      {
        id: "article-attention",
        title: "Attention mechanisms",
        url: "https://spaces.ac.cn/archives/1",
        metadata: { date: "2026-08-31", category: "机器学习".repeat(50) },
        content_preview: "# Attention\n\nA readable summary of attention.",
      },
    ],
    total: 14,
    query: "attention",
    category: null,
    sort: "relevance",
    page: 1,
    page_size: 5,
    total_pages: 3,
    has_next: true,
    has_previous: false,
  };
}

function referencePage(): ReferencePage {
  const doiReference: ReferencePage["items"][number] = {
    schema_version: "1",
    reference_id: "reference:private-id",
    reference_type: "doi",
    classification: "normalized",
    canonical_key: "doi:10.1000/attention",
    normalized_identifier: "10.1000/attention",
    normalized_url: "https://doi.org/10.1000/attention",
    doi: "10.1000/attention",
    arxiv_id: null,
    arxiv_version: null,
    source_article_id: "article-attention",
    source_article_title: "Attention mechanisms",
    source_article_url: "https://spaces.ac.cn/archives/1",
    source_section: `References ${"long section ".repeat(30)}`,
    source_span_start: 10,
    source_span_end: 40,
    evidence_text: "DOI: 10.1000/attention",
    source_count: 1,
    extraction_rule: "fixture",
    extraction_rule_version: "1",
    confidence: 1,
    duplicate_group_id: null,
    record_fingerprint: "fixture-fingerprint",
  };
  return {
    items: [
      doiReference,
      {
        ...doiReference,
        reference_id: "reference:internal-private-id",
        reference_type: "relative_or_internal_url",
        canonical_key: "url:https://spaces.ac.cn/archives/1#attention",
        normalized_identifier: "https://spaces.ac.cn/archives/1#attention",
        normalized_url: "https://spaces.ac.cn/archives/1#attention",
        doi: null,
        source_section: "## Attention [#](#Attention)",
        evidence_text: String.raw`\\sqrt{d} raw MathJax [Attention](/archives/1#attention)`,
        record_fingerprint: "internal-fixture-fingerprint",
      },
      {
        ...doiReference,
        reference_id: "reference:citation-private-id",
        reference_type: "citation_text",
        classification: "ambiguous",
        canonical_key: null,
        normalized_identifier: null,
        normalized_url: null,
        doi: null,
        source_section: "__article_root__",
        evidence_text: "A free-form citation that must not become the global result title",
        record_fingerprint: "citation-fixture-fingerprint",
      },
    ],
    total: 8,
    page: 1,
    page_size: 5,
    total_pages: 2,
    has_next: true,
    has_previous: false,
    query: "attention",
  };
}

function graphPage(): GraphNodeListResponse {
  return {
    items: [
      {
        node_id: "concept:attention",
        node_type: "concept",
        label: "Attention",
        source_id: null,
        source_url: null,
        metadata: {},
      },
    ],
    total: 3,
    page: 1,
    page_size: 5,
    pages: 1,
  };
}
