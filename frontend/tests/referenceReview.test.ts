import { strict as assert } from "node:assert";
import test from "node:test";

import {
  createArticleReferenceReturnPath,
  createReferenceReviewHref,
  createReferenceRequestOwner,
  consumeCandidateFilterFocus,
  consumeReferenceDetailFocus,
  consumeReferenceResultsFocus,
  isCanonicalReferenceReviewSearchParams,
  ownsReferenceCandidatePage,
  ownsReferenceRequest,
  parseArticleReferenceReturnTarget,
  parseReferenceReviewState,
  rememberCandidateFilterFocus,
  rememberReferenceDetailFocus,
  rememberReferenceResultsFocus,
  referenceRowId,
  resolveAvailableReferencePage,
  resolveOwnedReferenceReturnPath,
} from "../src/lib/referenceReview";

test("reference review state parses bounded canonical URL values", () => {
  const state = parseReferenceReviewState({
    q: "  Fisher\u0000 information  ",
    reference_type: "doi",
    classification: "normalized",
    page: "7",
    reference_id: "ref:doi:123",
    candidate: "ambiguous",
    return_to: "/articles/article-1?from=%2Flibrary%3Fview%3Dbookmarked&reference_page=3#structured-reference-ref:doi:123",
  });

  assert.deepEqual(state, {
    q: "Fisher information",
    referenceType: "doi",
    classification: "normalized",
    page: 7,
    referenceId: "ref:doi:123",
    candidateFilter: "ambiguous",
    returnTo: "/articles/article-1?from=%2Flibrary%3Fview%3Dbookmarked&reference_page=3#structured-reference-ref:doi:123",
  });
  assert.equal(
    createReferenceReviewHref(state),
    "/zotero?q=Fisher+information&reference_type=doi&classification=normalized&page=7&reference_id=ref%3Adoi%3A123&candidate=ambiguous&return_to=%2Farticles%2Farticle-1%3Ffrom%3D%252Flibrary%253Fview%253Dbookmarked%26reference_page%3D3%23structured-reference-ref%3Adoi%3A123",
  );
});

test("reference review state rejects unsafe or unbounded values", () => {
  const state = parseReferenceReviewState({
    q: "x".repeat(240),
    reference_type: "paper",
    classification: "trusted",
    page: "-2",
    reference_id: "../unsafe",
    candidate: "exact",
    return_to: "https://evil.example/articles/article-1#structured-reference-ref-1",
  });

  assert.equal(state.q.length, 200);
  assert.equal(state.referenceType, null);
  assert.equal(state.classification, null);
  assert.equal(state.page, 1);
  assert.equal(state.referenceId, null);
  assert.equal(state.candidateFilter, "all");
  assert.equal(state.returnTo, null);
  assert.equal(createReferenceReviewHref(state).startsWith("/zotero?q="), true);
});

test("reference review URL recognizes only its exact canonical query", () => {
  const canonical = new URLSearchParams("q=Fisher+information&reference_type=doi&page=2");
  assert.equal(isCanonicalReferenceReviewSearchParams(canonical), true);
  assert.equal(
    isCanonicalReferenceReviewSearchParams(
      new URLSearchParams("page=2&reference_type=doi&q=Fisher%20information"),
    ),
    false,
  );
  assert.equal(isCanonicalReferenceReviewSearchParams(new URLSearchParams("page=1")), false);
  assert.equal(isCanonicalReferenceReviewSearchParams(new URLSearchParams("unknown=value")), false);
  assert.equal(isCanonicalReferenceReviewSearchParams(new URLSearchParams("q=one&q=two")), false);
});

test("Article reference return path preserves safe Reader context and exact row", () => {
  const path = createArticleReferenceReturnPath({
    articleId: "article-1",
    referenceId: "ref:doi:123",
    referencePage: 3,
    currentArticlePath: "/articles/article-1?from=%2Flibrary%3Fview%3Dbookmarked",
  });

  assert.equal(
    path,
    "/articles/article-1?from=%2Flibrary%3Fview%3Dbookmarked&reference_page=3#structured-reference-ref:doi:123",
  );
  assert.equal(referenceRowId("ref:doi:123"), "structured-reference-ref:doi:123");
});

test("Article reference return ignores a mismatched current Reader route", () => {
  assert.equal(
    createArticleReferenceReturnPath({
      articleId: "article-1",
      referenceId: "ref-1",
      referencePage: 1,
      currentArticlePath: "/articles/article-2?from=https%3A%2F%2Fevil.example",
    }),
    "/articles/article-1#structured-reference-ref-1",
  );
});

test("owned Article return requires exact source Article, reference, and safe route", () => {
  const path = "/articles/article-1?reference_page=3#structured-reference-ref:doi:123";
  assert.equal(
    resolveOwnedReferenceReturnPath(path, "article-1", "ref:doi:123"),
    path,
  );
  assert.equal(resolveOwnedReferenceReturnPath(path, "article-2", "ref:doi:123"), null);
  assert.equal(
    resolveOwnedReferenceReturnPath(path, ["article-2", "article-1"], "ref:doi:123"),
    path,
  );
  assert.equal(resolveOwnedReferenceReturnPath(path, "article-1", "ref:doi:999"), null);
  assert.equal(
    resolveOwnedReferenceReturnPath(
      "https://evil.example/articles/article-1#structured-reference-ref:doi:123",
      "article-1",
      "ref:doi:123",
    ),
    null,
  );
});

test("Article return target exposes only a canonical local membership probe", () => {
  assert.deepEqual(
    parseArticleReferenceReturnTarget(
      "/articles/article-2?reference_page=4#structured-reference-ref:doi:123",
      "ref:doi:123",
    ),
    {
      articleId: "article-2",
      referencePage: 4,
      path: "/articles/article-2?reference_page=4#structured-reference-ref:doi:123",
    },
  );
  assert.equal(
    parseArticleReferenceReturnTarget(
      "/articles/article-2#structured-reference-ref:doi:other",
      "ref:doi:123",
    ),
    null,
  );
});

test("result pages canonicalize to the last available page", () => {
  assert.equal(resolveAvailableReferencePage(100_000, 7), 7);
  assert.equal(resolveAvailableReferencePage(2, 7), 2);
  assert.equal(resolveAvailableReferencePage(9, 0), 1);
  assert.equal(resolveAvailableReferencePage(-4, 7), 1);
});

test("reference request ownership requires current generation and exact key", () => {
  const owner = createReferenceRequestOwner(4, "detail:ref-a");
  assert.equal(ownsReferenceRequest(owner, 4, "detail:ref-a"), true);
  assert.equal(ownsReferenceRequest(owner, 5, "detail:ref-a"), false);
  assert.equal(ownsReferenceRequest(owner, 4, "detail:ref-b"), false);
});

test("candidate response renders only for the currently selected reference", () => {
  assert.equal(
    ownsReferenceCandidatePage({ reference_id: "ref-a" }, "ref-a"),
    true,
  );
  assert.equal(
    ownsReferenceCandidatePage({ reference_id: "ref-a" }, "ref-b"),
    false,
  );
  assert.equal(ownsReferenceCandidatePage(null, "ref-a"), false);
});

test("route focus intents are exact and consumed once", () => {
  rememberReferenceDetailFocus("ref-a");
  assert.equal(consumeReferenceDetailFocus("ref-b"), false);
  assert.equal(consumeReferenceDetailFocus("ref-a"), true);
  assert.equal(consumeReferenceDetailFocus("ref-a"), false);

  rememberReferenceResultsFocus();
  assert.equal(consumeReferenceDetailFocus("ref-a"), false);
  assert.equal(consumeReferenceResultsFocus(), true);
  assert.equal(consumeReferenceResultsFocus(), false);

  rememberCandidateFilterFocus("ambiguous");
  assert.equal(consumeCandidateFilterFocus("matched"), false);
  assert.equal(consumeCandidateFilterFocus("ambiguous"), true);
  assert.equal(consumeCandidateFilterFocus("ambiguous"), false);
});
