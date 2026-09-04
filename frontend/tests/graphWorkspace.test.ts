import assert from "node:assert/strict";
import test from "node:test";

import {
  createGraphWorkspaceHref,
  getGraphCanonicalizationAction,
  getGraphInitialPanel,
  getGraphSelectionHistoryAction,
} from "../src/lib/graphWorkspace";

test("Graph workspace href emits only canonical validated state", () => {
  assert.equal(
    createGraphWorkspaceHref({
      nodeId: "concept:attention",
      query: "  Attention\u0000  model  ",
      context: {
        articleId: "attention-basics",
        articleTitle: "Attention 机制",
        returnTo: "/articles/attention-basics?from=%2Farticles%3Fq%3DAttention#definition",
        nodeId: null,
      },
    }),
    "/graph?node_id=concept%3Aattention&q=Attention+model&article_id=attention-basics&article_title=Attention+%E6%9C%BA%E5%88%B6&return_to=%2Farticles%2Fattention-basics%3Ffrom%3D%252Farticles%253Fq%253DAttention%23definition",
  );
});

test("Graph workspace href rejects unsafe identity and sanitizes Article workflow context", () => {
  assert.equal(
    createGraphWorkspaceHref({
      nodeId: "concept:../private",
      query: "\u0000  ",
      context: {
        articleId: "../private",
        articleTitle: "/home/private/article.md",
        returnTo: "https://example.com/article",
        nodeId: null,
      },
    }),
    "/graph",
  );

  assert.equal(
    createGraphWorkspaceHref({
      nodeId: "concept:attention",
      query: "attention",
      context: {
        articleId: "attention-basics",
        articleTitle: "Attention",
        returnTo: "https://example.com/article",
        nodeId: null,
      },
    }),
    "/graph?node_id=concept%3Aattention&q=attention&article_id=attention-basics&article_title=Attention&return_to=%2Farticles%2Fattention-basics",
  );
});

test("Graph selection history pushes only a different safe node", () => {
  assert.equal(getGraphSelectionHistoryAction("concept:attention", "concept:attention"), "none");
  assert.equal(getGraphSelectionHistoryAction("concept:attention", "concept:transformer"), "push");
  assert.equal(getGraphSelectionHistoryAction("concept:attention", "../private"), "none");
});

test("Graph canonicalization replaces noncanonical URLs without adding history", () => {
  assert.equal(
    getGraphCanonicalizationAction(
      "/graph?unknown=1&node_id=concept%3Aattention",
      "/graph?node_id=concept%3Aattention",
    ),
    "replace",
  );
  assert.equal(
    getGraphCanonicalizationAction(
      "/graph?node_id=concept%3Aattention",
      "/graph?node_id=concept%3Aattention",
    ),
    "none",
  );
  assert.equal(
    getGraphCanonicalizationAction(
      "/graph?node_id=concept%3Aattention#unknown",
      "/graph?node_id=concept%3Aattention",
    ),
    "replace",
  );
});

test("Graph deep links open Selected while an empty route opens Results", () => {
  assert.equal(getGraphInitialPanel("concept:attention"), "selected");
  assert.equal(getGraphInitialPanel("concept:../private"), "results");
  assert.equal(getGraphInitialPanel(null), "results");
});
