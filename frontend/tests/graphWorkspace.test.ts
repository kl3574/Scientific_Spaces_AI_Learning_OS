import assert from "node:assert/strict";
import test from "node:test";

import {
  consumeGraphArticleReturnFocus,
  createGraphWorkspaceHref,
  getGraphCanonicalizationAction,
  getGraphInitialPanel,
  getGraphSessionStorage,
  getGraphSelectionHistoryAction,
  isSameTabNavigation,
  rememberGraphArticleReturnFocus,
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

test("Graph Article return focus is exact, one-shot, and fail-closed", () => {
  const values = new Map<string, string>();
  const storage = {
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
  };

  rememberGraphArticleReturnFocus(
    storage,
    "/graph?node_id=article%3Acrb-formula&q=CRB",
    "crb-formula",
    "provenance-2",
  );
  assert.deepEqual(
    consumeGraphArticleReturnFocus(storage, "/graph?node_id=article%3Acrb-formula&q=CRB"),
    { status: "found", articleId: "crb-formula", focusTarget: "provenance-2" },
  );
  assert.deepEqual(
    consumeGraphArticleReturnFocus(storage, "/graph?node_id=article%3Acrb-formula&q=CRB"),
    { status: "missing" },
  );
  rememberGraphArticleReturnFocus(
    storage,
    "/graph?node_id=article%3Acrb-formula&q=CRB",
    "crb-formula",
  );
  assert.deepEqual(
    consumeGraphArticleReturnFocus(storage, "/graph?node_id=article%3Acrb-formula&q=CRB"),
    { status: "found", articleId: "crb-formula", focusTarget: "provenance-2" },
  );

  rememberGraphArticleReturnFocus(storage, "https://example.com/graph?node_id=article%3Ax", "x");
  assert.deepEqual(
    consumeGraphArticleReturnFocus(storage, "/graph?node_id=article%3Ax"),
    { status: "missing" },
  );

  rememberGraphArticleReturnFocus(storage, "/graph?node_id=article%3Ax", "../private");
  assert.deepEqual(
    consumeGraphArticleReturnFocus(storage, "/graph?node_id=article%3Ax"),
    { status: "missing" },
  );

  values.set("scientific-spaces:graph-article-return-focus:v1", "not-json");
  assert.deepEqual(
    consumeGraphArticleReturnFocus(storage, "/graph?node_id=article%3Ax"),
    { status: "missing" },
  );

  rememberGraphArticleReturnFocus(storage, "/graph?node_id=article%3Ax", "x", "selected-node");
  rememberGraphArticleReturnFocus(storage, "/graph?node_id=article%3Ax", "x");
  assert.deepEqual(
    consumeGraphArticleReturnFocus(storage, "/graph?node_id=article%3Ax"),
    { status: "found", articleId: "x", focusTarget: "selected-node" },
  );
});

test("Graph session storage access and navigation activation fail closed", () => {
  const values = new Map<string, string>();
  const storage = {
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
  };
  assert.equal(getGraphSessionStorage({ sessionStorage: storage }), storage);

  const denied = Object.defineProperty({}, "sessionStorage", {
    get() {
      throw new Error("storage denied");
    },
  }) as { readonly sessionStorage: Storage };
  assert.equal(getGraphSessionStorage(denied), null);

  rememberGraphArticleReturnFocus(null, "/graph?node_id=article%3Ax", "x", "selected-node");
  assert.deepEqual(
    consumeGraphArticleReturnFocus(null, "/graph?node_id=article%3Ax"),
    { status: "unavailable" },
  );

  const methodDenied = {
    getItem() {
      throw new Error("storage method denied");
    },
    removeItem() {},
    setItem() {},
  };
  assert.deepEqual(
    consumeGraphArticleReturnFocus(methodDenied, "/graph?node_id=article%3Ax"),
    { status: "unavailable" },
  );

  const writeDenied = {
    getItem() {
      return null;
    },
    removeItem() {},
    setItem() {
      throw new Error("storage write denied");
    },
  };
  assert.deepEqual(
    consumeGraphArticleReturnFocus(writeDenied, "/graph?node_id=article%3Ax"),
    { status: "unavailable" },
  );

  const activation = {
    altKey: false,
    button: 0,
    ctrlKey: false,
    currentTarget: { target: "" },
    metaKey: false,
    shiftKey: false,
  };
  assert.equal(isSameTabNavigation(activation), true);
  assert.equal(isSameTabNavigation({ ...activation, ctrlKey: true }), false);
  assert.equal(isSameTabNavigation({ ...activation, metaKey: true }), false);
  assert.equal(isSameTabNavigation({ ...activation, shiftKey: true }), false);
  assert.equal(isSameTabNavigation({ ...activation, button: 1 }), false);
  assert.equal(
    isSameTabNavigation({ ...activation, currentTarget: { target: "_blank" } }),
    false,
  );
});
