import { strict as assert } from "node:assert";
import test from "node:test";

import { fetchArticle, fetchArticles, type ArticleListResponse } from "../src/lib/articles";

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

test("fetchArticles uses paged v1.1 endpoint and trims q", async () => {
  const calls = installFetchStub({
    items: [],
    total: 0,
    query: "transformer",
    category: null,
    sort: "date_desc",
    page: 2,
    page_size: 10,
    total_pages: 1,
    has_next: false,
    has_previous: true,
  } satisfies ArticleListResponse);

  await fetchArticles({
    q: "  transformer  ",
    page: 2,
    page_size: 10,
    sort: "date_desc",
  });

  const url = new URL(calls[0].input);
  assert.equal(url.pathname, "/v1.1/articles");
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    q: "transformer",
    page: "2",
    page_size: "10",
    sort: "date_desc",
  });
});

test("fetchArticles string overload maps to v1.1 articles with q", async () => {
  const calls = installFetchStub({
    items: [],
    total: 0,
    query: "attention",
    category: null,
    sort: "date_desc",
    page: 1,
    page_size: 20,
    total_pages: 1,
    has_next: false,
    has_previous: false,
  } satisfies ArticleListResponse);

  await fetchArticles(" attention ");

  const url = new URL(calls[0].input);
  assert.equal(url.pathname, "/v1.1/articles");
  assert.deepEqual(Object.fromEntries(url.searchParams), {
    q: "attention",
  });
});

test("fetchArticle continues to use legacy detail endpoint", async () => {
  const calls = installFetchStub({
    id: "article-1",
    title: "Article",
    url: "https://example.com/article-1",
    content: "Hello",
    metadata: {},
  });

  await fetchArticle("article-1");

  const url = new URL(calls[0].input);
  assert.equal(url.pathname, "/articles/article-1");
});
