import assert from "node:assert/strict";
import test from "node:test";

import {
  createConceptTutorHref,
  getConceptTutorContextMessage,
  parseConceptTutorLaunch,
} from "../src/lib/conceptLearningLaunch";
import { createConceptStudySet } from "../src/lib/conceptStudySet";
import type { GraphNode } from "../src/lib/graph";

test("Concept Study Set preserves returned order and discloses bounded provenance", () => {
  const node = conceptNode({
    source_count: 9,
    truncated: true,
    sources: [
      source("article-b", "贝叶斯估计", "第二节"),
      source("article-a", "Attention 机制", "定义"),
      source("article-b", "重复来源不应重复文章", "公式"),
      source("unsafe/id", "不安全记录", "坏路径"),
      source("missing-title", null, "只有章节名"),
      source("article-c", "Cramer-Rao 下界", null),
    ],
  });

  const set = createConceptStudySet(node);

  assert.ok(set);
  assert.equal(set.conceptNodeId, "concept:注意力机制");
  assert.equal(set.conceptTitle, "注意力机制");
  assert.equal(set.sourceRecordCount, 9);
  assert.equal(set.returnedRecordCount, 6);
  assert.equal(set.omittedRecordCount, 3);
  assert.equal(set.duplicateRecordCount, 1);
  assert.equal(set.invalidRecordCount, 2);
  assert.equal(set.truncated, true);
  assert.deepEqual(set.articles, [
    { articleId: "article-b", title: "贝叶斯估计", sectionTitle: "第二节" },
    { articleId: "article-a", title: "Attention 机制", sectionTitle: "定义" },
    { articleId: "article-c", title: "Cramer-Rao 下界", sectionTitle: null },
  ]);
  assert.deepEqual(set.primaryArticle, set.articles[0]);
});

test("Concept Study Set rejects unsupported nodes and unsafe concept identity", () => {
  assert.equal(createConceptStudySet({ ...conceptNode(), node_type: "formula" }), null);
  assert.equal(createConceptStudySet({ ...conceptNode(), node_id: "concept:../secret" }), null);
  assert.equal(createConceptStudySet({ ...conceptNode(), node_id: "concept:" }), null);
  assert.equal(createConceptStudySet({ ...conceptNode(), label: "/home/private/topic" }), null);
});

test("Concept Study Set bounds long CJK display titles without changing identity", () => {
  const set = createConceptStudySet({ ...conceptNode(), label: "概".repeat(300) });

  assert.ok(set);
  assert.equal(set.conceptNodeId, "concept:注意力机制");
  assert.equal(set.conceptTitle.length, 160);
});

test("Concept Study Set eligibility matches Reader, Tutor, and Session Article IDs", () => {
  const set = createConceptStudySet(conceptNode({
    source_count: 3,
    truncated: false,
    sources: [
      source("article-safe", "Readable Article", null),
      source("article with space", "Whitespace ID", null),
      source("article?query", "Query ID", null),
    ],
  }));

  assert.ok(set);
  assert.deepEqual(set.articles, [
    { articleId: "article-safe", title: "Readable Article", sectionTitle: null },
  ]);
  assert.equal(set.invalidRecordCount, 2);
});

test("Concept Tutor Explain launch is typed, bounded, and returns to the exact Concept", () => {
  const set = createConceptStudySet(conceptNode({
    source_count: 1,
    truncated: false,
    sources: [source("article-a", "Attention 机制", "定义")],
  }));
  assert.ok(set);

  const href = createConceptTutorHref(set, "explain");
  const url = new URL(href, "http://scientific-spaces.local");
  const parsed = parseConceptTutorLaunch(url.searchParams);

  assert.equal(url.pathname, "/tutor");
  assert.deepEqual(parsed, {
    conceptNodeId: "concept:注意力机制",
    conceptTitle: "注意力机制",
    mode: "explain",
    prompt: "Explain 注意力机制 using intuition, mathematics, and cited local evidence.",
    returnTo: "/graph?node_id=concept%3A%E6%B3%A8%E6%84%8F%E5%8A%9B%E6%9C%BA%E5%88%B6",
    primaryArticle: { articleId: "article-a", title: "Attention 机制" },
  });
});

test("Concept Tutor Quiz launch uses Article evidence and never promises Graph grounding", () => {
  const set = createConceptStudySet(conceptNode({
    source_count: 1,
    truncated: false,
    sources: [source("article-a", "Attention 机制", "定义")],
  }));
  assert.ok(set);

  const parsed = parseConceptTutorLaunch(
    new URL(createConceptTutorHref(set, "quiz"), "http://scientific-spaces.local").searchParams,
  );

  assert.equal(parsed?.mode, "quiz");
  assert.equal(parsed?.prompt, "注意力机制");
  assert.deepEqual(parsed?.primaryArticle, { articleId: "article-a", title: "Attention 机制" });
});

test("Concept Tutor context wording follows the active mode and Article selection", () => {
  assert.equal(
    getConceptTutorContextMessage("explain", true),
    "Graph context supplements the selected local Article evidence.",
  );
  assert.equal(
    getConceptTutorContextMessage("quiz", true),
    "Quiz uses the selected local Article and concept topic.",
  );
  assert.equal(
    getConceptTutorContextMessage("explain", false),
    "Explain keeps the Concept as supplemental Graph context; no local Article is selected.",
  );
  assert.equal(
    getConceptTutorContextMessage("research", false),
    "Research keeps the Concept context; no local Article is selected.",
  );
});

test("Concept Tutor launch rejects identity tampering and canonicalizes return paths", () => {
  const tampered = new URLSearchParams({
    entry: "concept",
    node_id: "concept:注意力机制",
    concept_title: "注意力机制",
    mode: "explain",
    return_to: "https://example.com/graph?node_id=concept:secret",
    source_article_id: "../secret",
    source_article_title: "/home/private/article",
  });
  const parsed = parseConceptTutorLaunch(tampered);

  assert.ok(parsed);
  assert.equal(parsed.returnTo, "/graph?node_id=concept%3A%E6%B3%A8%E6%84%8F%E5%8A%9B%E6%9C%BA%E5%88%B6");
  assert.equal(parsed.primaryArticle, null);
  assert.equal(parseConceptTutorLaunch(new URLSearchParams({ ...Object.fromEntries(tampered), mode: "research" })), null);
  assert.equal(parseConceptTutorLaunch(new URLSearchParams({ ...Object.fromEntries(tampered), node_id: "formula:x" })), null);
});

function conceptNode(metadata: Record<string, unknown> = { source_count: 0, sources: [], truncated: false }): GraphNode {
  return {
    node_id: "concept:注意力机制",
    node_type: "concept",
    label: "注意力机制",
    source_id: "注意力机制",
    source_url: null,
    metadata,
  };
}

function source(articleId: string, articleTitle: string | null, sectionTitle: string | null) {
  return {
    article_id: articleId,
    article_title: articleTitle,
    article_url: `https://spaces.ac.cn/archives/${articleId}`,
    source_type: "section_content",
    section_title: sectionTitle,
    source_context: "Bounded context",
    evidence: "Evidence",
    chunk_index: 0,
  };
}
