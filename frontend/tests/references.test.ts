import { strict as assert } from "node:assert";
import test from "node:test";

import {
  ReferenceApiError,
  candidateHref,
  fetchArticleReferences,
  fetchReference,
  fetchReferences,
  fetchZoteroCandidates,
  referenceErrorMessage,
  referenceHref,
  type ReferenceRecord,
  type ZoteroMatchCandidate,
} from "../src/lib/references";

type FetchCall = {
  input: string;
  init?: RequestInit;
};

function installFetchStub(payload: unknown, status = 200): FetchCall[] {
  const calls: FetchCall[] = [];
  globalThis.fetch = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ input: input.toString(), init });
    return new Response(JSON.stringify(payload), {
      headers: { "Content-Type": "application/json" },
      status,
    });
  }) as typeof fetch;
  return calls;
}

test("reference clients use additive bounded v1.2 routes", async () => {
  const calls = installFetchStub({ items: [], total: 0 });

  await fetchReferences({
    page: 2,
    pageSize: 10,
    referenceType: "doi",
    classification: "normalized",
    articleId: " article-1 ",
    query: " 10.1000 ",
  });
  await fetchArticleReferences("article/with space", { page: 3, pageSize: 5 });
  await fetchReference("reference/one", 7);
  await fetchZoteroCandidates("reference/one", { limit: 12, decision: "ambiguous" });

  const list = new URL(calls[0].input);
  assert.equal(list.pathname, "/v1.2/references");
  assert.deepEqual(Object.fromEntries(list.searchParams), {
    page: "2",
    page_size: "10",
    reference_type: "doi",
    classification: "normalized",
    article_id: "article-1",
    q: "10.1000",
  });
  assert.equal(new URL(calls[1].input).pathname, "/v1.2/articles/article%2Fwith%20space/references");
  assert.equal(new URL(calls[2].input).pathname, "/v1.2/references/reference%2Fone");
  assert.equal(new URL(calls[2].input).searchParams.get("provenance_limit"), "7");
  assert.equal(
    new URL(calls[3].input).pathname,
    "/v1.2/references/reference%2Fone/zotero-candidates",
  );
  assert.deepEqual(Object.fromEntries(new URL(calls[3].input).searchParams), {
    limit: "12",
    decision: "ambiguous",
  });
  assert.equal(calls[0].init?.cache, "no-store");
});

test("reference client preserves bounded stale and corrupt error states", async () => {
  installFetchStub(
    {
      detail: {
        code: "reference_store_stale",
        state: "stale",
        message: "Reference Store is stale and must be rebuilt",
      },
    },
    503,
  );

  await assert.rejects(
    fetchReferences(),
    (error: unknown) => {
      assert.ok(error instanceof ReferenceApiError);
      assert.equal(error.status, 503);
      assert.equal(error.code, "reference_store_stale");
      assert.equal(error.state, "stale");
      assert.equal(referenceErrorMessage(error), "The reference index is stale and must be rebuilt.");
      return true;
    },
  );

  assert.equal(
    referenceErrorMessage(new ReferenceApiError("bad", 503, "reference_store_corrupt", "corrupt")),
    "The reference index failed integrity validation.",
  );
});

test("reference links allow only credential-free HTTP URLs or generated identifier URLs", () => {
  const record = {
    normalized_url: "https://example.org/paper",
    doi: null,
    arxiv_id: null,
    arxiv_version: null,
  } as ReferenceRecord;
  const unsafe = {
    ...record,
    normalized_url: "javascript:alert(1)",
  } as ReferenceRecord;
  const credentialed = {
    ...record,
    normalized_url: "https://user:secret@example.org/paper",
  } as ReferenceRecord;
  const doi = {
    ...record,
    normalized_url: null,
    doi: "10.1000/example",
  } as ReferenceRecord;
  const candidate = {
    url: null,
    doi: null,
    arxiv_id: "1706.03762",
    arxiv_version: 2,
  } as ZoteroMatchCandidate;

  assert.equal(referenceHref(record), "https://example.org/paper");
  assert.equal(referenceHref(unsafe), null);
  assert.equal(referenceHref(credentialed), null);
  assert.equal(referenceHref(doi), "https://doi.org/10.1000%2Fexample");
  assert.equal(candidateHref(candidate), "https://arxiv.org/abs/1706.03762v2");
});
