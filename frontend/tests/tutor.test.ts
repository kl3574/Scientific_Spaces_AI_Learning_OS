import { strict as assert } from "node:assert";
import test from "node:test";

import {
  MAX_RENDERED_TUTOR_SOURCES,
  createTutorModeResetState,
  dedupeTutorSources,
  deriveRefusalLabel,
  formatSelectionSummaryLines,
  getBoundedSourceRows,
  getSafeDisplayText,
  getSafeExternalUrl,
  getSourceDisclosure,
  isResearchEvidenceGap,
  isResearchLocalOnly,
  normalizeTutorQuizTopic,
  resolveSourceArticleId,
} from "../src/lib/tutorPresentation";
import type {
  TutorEvidenceSummary,
  TutorResponse,
  TutorSelectionSummary,
  TutorSource,
} from "../src/lib/tutor";

function sourceFactory(overrides: Partial<TutorSource> = {}): TutorSource {
  return {
    source_type: "article_chunk",
    source_id: "attention-001:0",
    title: "Attention",
    url: "https://spaces.ac.cn/archives/6508",
    section_title: "Introduction",
    chunk_index: 0,
    evidence: null,
    metadata: {},
    ...overrides,
  };
}

function evidenceFactory(overrides: Partial<TutorEvidenceSummary> = {}): TutorEvidenceSummary {
  return {
    source_count: 2,
    article_count: 2,
    has_formula_evidence: false,
    has_definition_evidence: true,
    has_answerable_evidence: true,
    source_schema_valid: true,
    unsupported_or_out_of_scope: false,
    refusal_reason: null,
    ...overrides,
  };
}

function responseFactory(overrides: Partial<TutorResponse> = {}): TutorResponse {
  return {
    answer: "ok",
    mode: "explain",
    sources: [],
    graph_context: { nodes: [], edges: [] },
    zotero_context: [],
    follow_up_questions: [],
    refusal_reason: null,
    selection_summary: null,
    evidence_summary: evidenceFactory(),
    ...overrides,
  };
}

test("Tutor summary types match the backend additive schema exactly", () => {
  const summary = {
    candidate_count: 12,
    selected_article_count: 4,
    selected_chunk_count: 8,
    graph_node_count: 20,
    graph_edge_count: 30,
    graph_latency_ms: 12.5,
    graph_error_code: null,
    context_character_count: 1200,
    estimated_token_count: 300,
    truncated: true,
    supplement_omitted_count: 7,
  } satisfies TutorSelectionSummary;
  const evidence = evidenceFactory();

  assert.equal(summary.context_character_count, 1200);
  assert.equal(summary.supplement_omitted_count, 7);
  assert.equal(evidence.article_count, 2);

  const obsoleteSummary = {
    ...summary,
    // @ts-expect-error The backend does not expose this legacy presentation field.
    context_characters: 1200,
  } satisfies TutorSelectionSummary;
  const obsoleteEvidence = {
    ...evidence,
    // @ts-expect-error Evidence gaps are derived from real sufficiency fields.
    has_evidence_gaps: true,
  } satisfies TutorEvidenceSummary;
  void obsoleteSummary;
  void obsoleteEvidence;
});

test("dedupeTutorSources removes duplicate source_type+source_id entries and enforces cap", () => {
  const sources = [
    sourceFactory({ source_id: "article-1:0", title: "One" }),
    sourceFactory({ source_id: "article-1:0", title: "One duplicate" }),
    sourceFactory({ source_id: "article-2:0", title: "Two" }),
  ];

  const result = dedupeTutorSources(sources, 2);
  assert.equal(result.sources.length, 2);
  assert.equal(result.sources[0]?.title, "One");
  assert.equal(result.sources[1]?.title, "Two");
  assert.equal(result.hiddenReturnedCount, 0);
});

test("whole-response source ceiling preserves bounded Article, Graph, and Zotero supplements", () => {
  const articleSources = Array.from({ length: 10 }, (_, index) =>
    sourceFactory({ source_id: `article-${index}:0` }),
  );
  const graphNodeSources = Array.from({ length: 20 }, (_, index) =>
    sourceFactory({ source_type: "graph_node", source_id: `node-${index}` }),
  );
  const graphEdgeSources = Array.from({ length: 30 }, (_, index) =>
    sourceFactory({ source_type: "graph_edge", source_id: `edge-${index}` }),
  );
  const zoteroSources = Array.from({ length: 12 }, (_, index) =>
    sourceFactory({ source_type: "zotero_item", source_id: `zotero-${index}` }),
  );
  const boundedBackendSources = [
    ...articleSources,
    ...graphNodeSources,
    ...graphEdgeSources,
    ...zoteroSources,
  ];

  assert.equal(boundedBackendSources.length, 72);
  assert.ok(MAX_RENDERED_TUTOR_SOURCES >= boundedBackendSources.length);
  assert.ok(MAX_RENDERED_TUTOR_SOURCES <= 100);

  const result = dedupeTutorSources(boundedBackendSources, MAX_RENDERED_TUTOR_SOURCES);
  assert.equal(result.sources.length, boundedBackendSources.length);
  assert.equal(result.sources.filter((source) => source.source_type === "zotero_item").length, 12);
});

test("source disclosure remains collapsible after expansion and reports UI-ceiling omissions", () => {
  const sources = Array.from({ length: MAX_RENDERED_TUTOR_SOURCES + 2 }, (_, index) =>
    sourceFactory({ source_id: `article-${index}:0` }),
  );
  const collapsed = getBoundedSourceRows(sources, {
    maxSources: MAX_RENDERED_TUTOR_SOURCES,
    maxVisible: 3,
    expanded: false,
  });
  const expanded = getBoundedSourceRows(sources, {
    maxSources: MAX_RENDERED_TUTOR_SOURCES,
    maxVisible: 3,
    expanded: true,
  });
  const collapsedDisclosure = getSourceDisclosure(collapsed, { expanded: false, maxVisible: 3 });
  const expandedDisclosure = getSourceDisclosure(expanded, { expanded: true, maxVisible: 3 });

  assert.equal(collapsed.visibleSources.length, 3);
  assert.equal(collapsed.hiddenReturnedCount, MAX_RENDERED_TUTOR_SOURCES - 3);
  assert.equal(collapsed.omittedReturnedCount, 2);
  assert.equal(collapsedDisclosure.canToggle, true);
  assert.match(collapsedDisclosure.toggleLabel ?? "", /展开另外 69 条/);
  assert.match(collapsedDisclosure.omittedLabel ?? "", /另有 2 条/);

  assert.equal(expanded.visibleSources.length, MAX_RENDERED_TUTOR_SOURCES);
  assert.equal(expanded.hiddenReturnedCount, 0);
  assert.equal(expandedDisclosure.canToggle, true);
  assert.match(expandedDisclosure.toggleLabel ?? "", /收起来源/);
  assert.match(expandedDisclosure.omittedLabel ?? "", /另有 2 条/);
});

test("resolveSourceArticleId prefers safe metadata article_id and parses chunked article ids", () => {
  const withMetadata = sourceFactory({
    metadata: { article_id: "attention-001" },
    source_id: "ignored:1",
  });
  assert.equal(resolveSourceArticleId(withMetadata), "attention-001");

  const withChunkId = sourceFactory({
    source_id: "attention-001:12",
    metadata: {},
  });
  assert.equal(resolveSourceArticleId(withChunkId), "attention-001");
});

test("resolveSourceArticleId rejects paths, traversal, schemes, and unsafe identifiers", () => {
  const unsafeIds = [
    "/tmp/secret/article.json",
    "C:\\Users\\alice\\article.json",
    "\\\\server\\share\\article.json",
    "../secret/article",
    "article/../../secret",
    "file:///tmp/article",
    "data:text/plain,article",
    "javascript:alert(1)",
    "article id with spaces",
    "article%2F..%2Fsecret",
  ];

  for (const sourceId of unsafeIds) {
    const source = sourceFactory({ source_id: sourceId, metadata: {} });
    assert.equal(resolveSourceArticleId(source), null, sourceId);
  }

  const safeFallback = sourceFactory({
    metadata: { article_id: "/tmp/secret/article.json" },
    source_id: "attention-001:2",
  });
  assert.equal(resolveSourceArticleId(safeFallback), "attention-001");

  const invalidGraphSource = sourceFactory({
    source_type: "graph_node",
    source_id: "graph-1",
    metadata: { article_id: "../secret/article.json" },
  });
  assert.equal(resolveSourceArticleId(invalidGraphSource), null);
});

test("getSafeDisplayText rejects embedded local paths, traversal, and executable schemes", () => {
  const unsafeText = [
    "Loaded from /home/alice/private/article.md",
    "Cache at C:\\Users\\alice\\article.md",
    "Mirror \\\\server\\share\\article.md",
    "Read ../private/article.md next",
    "Open file:///tmp/article.md",
    "Payload data:text/plain,secret",
    "Run javascript:alert(1)",
  ];

  assert.equal(getSafeDisplayText("Attention and transformer"), "Attention and transformer");
  for (const value of unsafeText) {
    assert.equal(getSafeDisplayText(value), null, value);
  }
});

test("getSafeExternalUrl allows clean HTTP(S) and rejects local, embedded, or traversal payloads", () => {
  assert.equal(getSafeExternalUrl("https://spaces.ac.cn/archives/6508"), "https://spaces.ac.cn/archives/6508");
  assert.equal(getSafeExternalUrl("http://spaces.ac.cn/archives/6508"), "http://spaces.ac.cn/archives/6508");

  const unsafeUrls = [
    "file:///tmp/article.md",
    "/tmp/article.md",
    "https://example.com/?next=file:///tmp/article.md",
    "https://example.com/?next=javascript:alert(1)",
    "https://example.com/?payload=data:text/plain,secret",
    "https://example.com/a/../private",
    "https://example.com/?path=/home/alice/private.md",
    "https://example.com/?path=C%3A%5CUsers%5Calice%5Cprivate.md",
    "https://example.com/?path=%5C%5Cserver%5Cshare%5Cprivate.md",
    "javascript:alert(1)",
    "data:text/html,secret",
  ];
  for (const value of unsafeUrls) {
    assert.equal(getSafeExternalUrl(value), null, value);
  }
});

test("research notices derive from mode and real evidence sufficiency fields", () => {
  const adequateResearch = responseFactory({
    mode: "research",
    sources: [
      sourceFactory({ source_id: "article-a:0" }),
      sourceFactory({ source_id: "article-b:0" }),
    ],
    evidence_summary: evidenceFactory(),
  });
  const researchGap = responseFactory({
    mode: "research",
    sources: [sourceFactory({ source_id: "article-a:0" })],
    evidence_summary: evidenceFactory({
      source_count: 1,
      article_count: 1,
      has_answerable_evidence: false,
      refusal_reason: "insufficient_local_corpus_evidence",
    }),
    refusal_reason: "no_sources",
  });

  assert.equal(isResearchLocalOnly(adequateResearch), true);
  assert.equal(isResearchEvidenceGap(adequateResearch), false);
  assert.equal(isResearchEvidenceGap(researchGap), true);
  assert.equal(isResearchLocalOnly(responseFactory({ mode: "qa" })), false);
});

test("mode-change reset clears response, error, quiz, and loading presentation state", () => {
  const reset = createTutorModeResetState();

  assert.deepEqual(reset, {
    status: "idle",
    error: null,
    response: null,
    quiz: [],
  });
});

test("normalizeTutorQuizTopic maps the single visible Quiz prompt to the request topic", () => {
  assert.equal(normalizeTutorQuizTopic("  Attention mechanisms  "), "Attention mechanisms");
  assert.equal(normalizeTutorQuizTopic(" \n "), undefined);
});

test("deriveRefusalLabel maps derive insufficiency to explicit refusal text", () => {
  const responses: TutorResponse[] = [
    responseFactory({
      answer: "",
      mode: "derive",
      refusal_reason: "insufficient_formula_sources",
      evidence_summary: evidenceFactory({ refusal_reason: null }),
    }),
    responseFactory({
      answer: "",
      mode: "derive",
      refusal_reason: "no_sources",
      evidence_summary: evidenceFactory({ refusal_reason: null }),
    }),
  ];

  assert.equal(deriveRefusalLabel(responses[0]), "当前资料不足以完整推导。");
  assert.equal(deriveRefusalLabel(responses[1]), "无法基于当前资料回答。");
});

test("formatSelectionSummaryLines renders every real backend summary field", () => {
  const summary: TutorSelectionSummary = {
    candidate_count: 12,
    selected_article_count: 4,
    selected_chunk_count: 8,
    graph_node_count: 20,
    graph_edge_count: 30,
    graph_latency_ms: 12.5,
    graph_error_code: "graph_unavailable",
    context_character_count: 1200,
    estimated_token_count: 300,
    truncated: true,
    supplement_omitted_count: 7,
  };

  const lines = formatSelectionSummaryLines(summary);
  const byLabel = new Map(lines.map((line) => [line.label, line.value]));

  assert.equal(byLabel.get("候选片段"), "12");
  assert.equal(byLabel.get("已选来源"), "4 篇文章 / 8 个片段");
  assert.equal(byLabel.get("上下文字符"), "1200");
  assert.equal(byLabel.get("估算 Token"), "300");
  assert.equal(byLabel.get("Graph"), "20 个节点 / 30 条边");
  assert.equal(byLabel.get("Graph 延迟"), "12.5 ms");
  assert.equal(byLabel.get("Graph 状态"), "graph_unavailable");
  assert.equal(byLabel.get("已截断"), "是");
  assert.equal(byLabel.get("已省略补充来源"), "7");
  assert.deepEqual(formatSelectionSummaryLines(null), []);
});
