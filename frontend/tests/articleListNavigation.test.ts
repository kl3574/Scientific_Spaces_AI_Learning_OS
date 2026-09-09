import assert from "node:assert/strict";
import test from "node:test";

import { getArticleListRoutePlan } from "../src/lib/articleListNavigation";

function observe(search: string, knownHref = "/articles", browserSearch = search) {
  return getArticleListRoutePlan({
    pathname: "/articles", browserPathname: "/articles", search, browserSearch, knownHref,
  });
}

test("external navigation adopts query, sort and page together", () => {
  assert.deepEqual(observe("q=Attention&sort=relevance&page=2"), {
    action: "navigate", href: "/articles?q=Attention&sort=relevance&page=2",
    state: { q: "Attention", sort: "relevance", page: 2 },
  });
});

test("bare navigation resets a known local filter even after a bare entry", () => {
  assert.equal(observe("")?.action, "echo");
  const localHref = "/articles?q=Attention&sort=relevance";
  assert.equal(observe("q=Attention&sort=relevance", localHref)?.action, "echo");
  assert.deepEqual(observe("", localHref), {
    action: "navigate", href: "/articles", state: { q: "", sort: "date_desc", page: 1 },
  });
});

test("local URL echoes do not request external draft reconciliation", () => {
  for (const [search, href] of [
    ["q=Attention", "/articles?q=Attention"],
    ["q=Attention&sort=title_asc", "/articles?q=Attention&sort=title_asc"],
    ["q=Attention&sort=title_asc&page=2", "/articles?q=Attention&sort=title_asc&page=2"],
  ]) {
    assert.equal(observe(search, href)?.action, "echo");
  }
});

test("history transitions restore complete tuples including A to B to A", () => {
  const entries = [
    ["q=Attention&sort=relevance&page=2", "/articles?q=Attention&sort=relevance&page=2"],
    ["q=CRB&sort=title_asc", "/articles?q=CRB&sort=title_asc"],
    ["q=Attention&sort=relevance&page=2", "/articles?q=Attention&sort=relevance&page=2"],
  ];
  let known = "/articles";
  for (const [search, href] of entries) {
    const plan = observe(search, known);
    assert.equal(plan?.action, "navigate");
    assert.equal(plan.href, href);
    known = plan.href;
  }
});

test("sort-only and page-only navigation are meaningful transitions", () => {
  assert.equal(observe("sort=title_asc")?.action, "navigate");
  assert.equal(observe("page=2")?.action, "navigate");
});

test("canonical equivalence is an echo rather than a second result generation", () => {
  for (const search of ["", "page=1", "sort=date_desc", "unused=value&page=1"]) {
    assert.equal(observe(search)?.action, "echo");
  }
  assert.equal(observe("sort=relevance&q=Attention&page=1", "/articles?q=Attention&sort=relevance")?.action, "echo");
});

test("normalization uses existing list rules rather than a separate parser", () => {
  assert.deepEqual(observe("q=%20Attention%20%20test%20&sort=invalid&page=-1")?.state, {
    q: "Attention test", sort: "date_desc", page: 1,
  });
  assert.equal(observe("page=999999")?.state.page, 100000);
  assert.equal(observe("q=" + "x".repeat(250))?.state.q.length, 200);
});

test("superseded hook snapshots cannot reconcile or rewrite a newer browser URL", () => {
  assert.equal(observe("q=Attention", "/articles", "q=CRB"), null);
  assert.equal(observe("", "/articles?q=Attention", "q=Attention"), null);
  assert.equal(observe("page=2", "/articles", "page=3"), null);
});

test("route ownership excludes a departed or unrelated pathname", () => {
  for (const [pathname, browserPathname] of [
    ["/articles", "/graph"], ["/graph", "/graph"], ["/articles/attention-basics", "/articles/attention-basics"],
  ]) {
    assert.equal(getArticleListRoutePlan({ pathname, browserPathname, search: "", browserSearch: "", knownHref: "/articles" }), null);
  }
});

test("browser leading question mark and standard query encoding are equivalent snapshots", () => {
  assert.equal(observe("q=Attention+test", "/articles", "?q=Attention%20test")?.action, "navigate");
});
