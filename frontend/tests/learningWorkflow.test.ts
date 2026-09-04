import assert from "node:assert/strict";
import test from "node:test";

import {
  createArticleDetailHref,
  createArticleListHref,
  createArticleReturnHref,
  createLearningToolHref,
  parseArticleListState,
  parseLearningWorkflowContext,
  sanitizeArticleEntryReturnPath,
  sanitizeArticleListReturnPath,
} from "../src/lib/learningWorkflow";

test("Article list state is canonical, bounded, and URL-addressable", () => {
  assert.deepEqual(
    parseArticleListState(new URLSearchParams("q= Attention &sort=relevance&page=3")),
    { q: "Attention", sort: "relevance", page: 3 },
  );
  assert.equal(
    createArticleListHref({ q: "Attention", sort: "relevance", page: 3 }),
    "/articles?q=Attention&sort=relevance&page=3",
  );
  assert.deepEqual(
    parseArticleListState({ q: "x", sort: "unsafe", page: "-4" }),
    { q: "x", sort: "date_desc", page: 1 },
  );
});

test("Article detail links retain only a safe canonical list return path", () => {
  const listPath = "/articles?q=CRB&sort=relevance&page=2";
  assert.equal(
    createArticleDetailHref("crb-formula", listPath),
    "/articles/crb-formula?from=%2Farticles%3Fq%3DCRB%26sort%3Drelevance%26page%3D2",
  );
  assert.equal(sanitizeArticleListReturnPath("https://example.com/articles?q=secret"), "/articles");
  assert.equal(sanitizeArticleListReturnPath("//example.com/articles"), "/articles");
  assert.equal(sanitizeArticleListReturnPath("/tutor?q=CRB"), "/articles");
});

test("Article detail accepts only canonical Saved Library return state", () => {
  const libraryPath = "/library?q=CRB&view=bookmarked&sort=progress";
  assert.equal(sanitizeArticleEntryReturnPath(libraryPath), libraryPath);
  assert.equal(
    createArticleDetailHref("crb-formula", libraryPath),
    "/articles/crb-formula?from=%2Flibrary%3Fq%3DCRB%26view%3Dbookmarked%26sort%3Dprogress",
  );
  assert.equal(
    sanitizeArticleEntryReturnPath("/library?q=x&view=unsafe&sort=unsafe&token=secret"),
    "/library?q=x",
  );
  assert.equal(sanitizeArticleEntryReturnPath("https://example.com/library"), "/articles");
});

test("Article detail accepts only the canonical local Study Session return path", () => {
  assert.equal(sanitizeArticleEntryReturnPath("/session"), "/session");
  assert.equal(sanitizeArticleEntryReturnPath("/session?token=secret"), "/session");
  assert.equal(sanitizeArticleEntryReturnPath("/session#unsafe"), "/articles");
  assert.equal(sanitizeArticleEntryReturnPath("https://example.com/session"), "/articles");
  assert.equal(
    createArticleDetailHref("crb-formula", "/session"),
    "/articles/crb-formula?from=%2Fsession",
  );
});

test("Article detail accepts only a canonical Graph Concept return path", () => {
  const graphPath = "/graph?node_id=concept%3A%E6%B3%A8%E6%84%8F%E5%8A%9B%E6%9C%BA%E5%88%B6";
  assert.equal(sanitizeArticleEntryReturnPath(graphPath), graphPath);
  assert.equal(
    sanitizeArticleEntryReturnPath(`${graphPath}&token=secret&q=private`),
    graphPath,
  );
  assert.equal(sanitizeArticleEntryReturnPath("/graph?node_id=formula%3Asecret"), "/articles");
  assert.equal(sanitizeArticleEntryReturnPath("https://example.com/graph?node_id=concept%3Ax"), "/articles");
  assert.equal(
    createArticleDetailHref("attention-basics", graphPath),
    `/articles/attention-basics?from=${encodeURIComponent(graphPath)}`,
  );
});

test("Tutor workflow context round-trips Article, list, title, and section", () => {
  const href = createLearningToolHref("tutor", {
    articleId: "crb-formula",
    articleTitle: "CRB 公式",
    listReturnTo: "/articles?q=CRB&sort=relevance&page=2",
    sectionId: "数值检查",
  });
  const context = parseLearningWorkflowContext(new URL(href, "http://local").searchParams);
  assert.deepEqual(context, {
    articleId: "crb-formula",
    articleTitle: "CRB 公式",
    returnTo:
      "/articles/crb-formula?from=%2Farticles%3Fq%3DCRB%26sort%3Drelevance%26page%3D2#%E6%95%B0%E5%80%BC%E6%A3%80%E6%9F%A5",
    nodeId: null,
  });
});

test("Graph context derives and validates the exact Article node", () => {
  const href = createLearningToolHref("graph", {
    articleId: "article-001",
    articleTitle: "Attention",
    sectionId: "formula",
  });
  const context = parseLearningWorkflowContext(new URL(href, "http://local").searchParams);
  assert.equal(context?.nodeId, "article:article-001");
  assert.equal(context?.returnTo, "/articles/article-001#formula");

  const tampered = new URLSearchParams(href.split("?")[1]);
  tampered.set("node_id", "article:different");
  assert.equal(parseLearningWorkflowContext(tampered)?.nodeId, null);
});

test("Tool context rejects cross-Article and external return paths", () => {
  const external = parseLearningWorkflowContext({
    article_id: "article-001",
    article_title: "Attention",
    return_to: "https://example.com/articles/article-001",
  });
  assert.equal(external?.returnTo, "/articles/article-001");

  const crossArticle = parseLearningWorkflowContext({
    article_id: "article-001",
    return_to: createArticleReturnHref("article-002", "/articles?q=private", "formula"),
  });
  assert.equal(crossArticle?.returnTo, "/articles/article-001");
});
