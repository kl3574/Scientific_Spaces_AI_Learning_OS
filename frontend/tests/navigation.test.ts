import assert from "node:assert/strict";
import test from "node:test";

import {
  PRIMARY_NAVIGATION,
  consumeShellDestinationFocusIntent,
  consumeShellHistoryNavigation,
  createShellRouteIdentity,
  getShellFocusOperationVersion,
  getShellRouteCommitAction,
  getShellRouteCommitFocusOperationVersion,
  hasPendingShellHistoryNavigation,
  isNavigationItemActive,
  isShellDestinationFocusAction,
  recordShellFocusOperation,
  recordShellDestinationFocusIntent,
  recordShellHistoryNavigation,
  recordShellRouteCommit,
  resolveShellPendingRouteLifecycleAction,
  resolveShellRouteCommitAction,
  resolveShellNavigationTarget,
  resolveWorkspaceLocation,
  shouldTransferDeferredReaderFragmentFocus,
  shouldScheduleShellHistoryMainFocus,
  shouldUseShellMainFocus,
} from "../src/lib/navigation";

test("primary navigation exposes every stable workspace root once", () => {
  assert.deepEqual(
    PRIMARY_NAVIGATION.map(({ id, href, label }) => ({ id, href, label })),
    [
      { id: "dashboard", href: "/", label: "Dashboard" },
      { id: "library", href: "/library", label: "Saved" },
      { id: "session", href: "/session", label: "Session" },
      { id: "articles", href: "/articles", label: "Articles" },
      { id: "references", href: "/zotero", label: "References" },
      { id: "graph", href: "/graph", label: "Graph" },
      { id: "tutor", href: "/tutor", label: "Tutor" },
    ],
  );
  assert.equal(new Set(PRIMARY_NAVIGATION.map((item) => item.href)).size, PRIMARY_NAVIGATION.length);
});

test("active workspace matching respects route boundaries", () => {
  const dashboard = PRIMARY_NAVIGATION[0];
  const articles = PRIMARY_NAVIGATION[3];

  assert.equal(isNavigationItemActive("/", dashboard), true);
  assert.equal(isNavigationItemActive("/articles", dashboard), false);
  assert.equal(isNavigationItemActive("/articles", articles), true);
  assert.equal(isNavigationItemActive("/articles/crb-formula", articles), true);
  assert.equal(isNavigationItemActive("/articleship", articles), false);
});

test("workspace location describes Article detail without exposing its identifier", () => {
  const location = resolveWorkspaceLocation("/articles/private-runtime-id/");

  assert.deepEqual(location, {
    id: "articles",
    label: "Article",
    trail: ["Articles", "Article"],
  });
  assert.equal(location.trail.join(" ").includes("private-runtime-id"), false);
});

test("workspace location handles each root and an unknown route", () => {
  assert.equal(resolveWorkspaceLocation("/library").id, "library");
  assert.equal(resolveWorkspaceLocation("/session").id, "session");
  assert.equal(resolveWorkspaceLocation("/zotero").id, "references");
  assert.equal(resolveWorkspaceLocation("/graph/context").id, "graph");
  assert.equal(resolveWorkspaceLocation("tutor").id, "tutor");
  assert.deepEqual(resolveWorkspaceLocation("/missing"), {
    id: "unknown",
    label: "Page not found",
    trail: ["Page not found"],
  });
});

test("Shell route identity includes canonical pathname and query but excludes hash", () => {
  assert.equal(createShellRouteIdentity("/graph/", "?q=CRB&node_id=concept%3Acrb"), "/graph?node_id=concept%3Acrb&q=CRB");
  assert.equal(createShellRouteIdentity("articles", ""), "/articles");
  assert.equal(
    resolveShellNavigationTarget(
      "/graph/?q=CRB&node_id=concept%3Acrb#selected",
      "http://localhost:3000/articles?q=attention",
    ),
    "/graph?node_id=concept%3Acrb&q=CRB",
  );
});

test("Shell navigation target rejects non-local or non-HTTP destinations", () => {
  assert.equal(
    resolveShellNavigationTarget("https://example.com/graph", "http://localhost:3000/"),
    null,
  );
  assert.equal(resolveShellNavigationTarget("mailto:reader@example.com", "http://localhost:3000/"), null);
});

test("Shell destination focus intent is bounded to an exact local route and consumed once", () => {
  const graphIdentity = "/graph?node_id=article%3Aattention-basics";
  const articleIdentity = "/articles/attention-basics";
  recordShellDestinationFocusIntent(
    graphIdentity,
    "http://localhost:3000/articles/attention-basics",
  );
  recordShellDestinationFocusIntent(
    "https://example.com/graph",
    "http://localhost:3000/articles/attention-basics",
  );

  assert.equal(consumeShellDestinationFocusIntent("/graph", articleIdentity), false);
  assert.equal(consumeShellDestinationFocusIntent(graphIdentity, "/articles/other"), false);
  assert.equal(consumeShellDestinationFocusIntent(graphIdentity, articleIdentity), false);

  recordShellDestinationFocusIntent(
    graphIdentity,
    "http://localhost:3000/articles/attention-basics",
  );
  assert.equal(consumeShellDestinationFocusIntent(graphIdentity, articleIdentity), true);
  assert.equal(consumeShellDestinationFocusIntent(graphIdentity, articleIdentity), false);
});

test("a newer Shell focus operation invalidates an unconsumed destination intent", () => {
  const graphIdentity = "/graph?node_id=article%3Aattention-basics";
  const articleIdentity = "/articles/attention-basics";
  recordShellDestinationFocusIntent(
    graphIdentity,
    "http://localhost:3000/articles/attention-basics",
  );

  recordShellFocusOperation();

  assert.equal(consumeShellDestinationFocusIntent(graphIdentity, articleIdentity), false);
});

test("Shell history navigation is consumed only by its exact destination", () => {
  recordShellHistoryNavigation("/articles/crb-formula", "?from=%2Fsession", "#article-outline");
  assert.equal(
    hasPendingShellHistoryNavigation(
      "/articles/crb-formula",
      "?from=%2Fsession",
      "#article-outline",
    ),
    true,
  );
  assert.equal(
    consumeShellHistoryNavigation("/articles/attention-basics", "", "#article-outline"),
    null,
  );
  assert.deepEqual(
    consumeShellHistoryNavigation(
      "/articles/crb-formula",
      "?from=%2Fsession",
      "#article-outline",
    ),
    {
      pathname: "/articles/crb-formula",
      search: "?from=%2Fsession",
      hash: "#article-outline",
    },
  );
  assert.equal(
    consumeShellHistoryNavigation(
      "/articles/crb-formula",
      "?from=%2Fsession",
      "#article-outline",
    ),
    null,
  );
  assert.equal(
    hasPendingShellHistoryNavigation(
      "/articles/crb-formula",
      "?from=%2Fsession",
      "#article-outline",
    ),
    false,
  );
});

test("Shell route commits expose destination focus only for client-side commits", () => {
  const routeOperationVersion = recordShellFocusOperation();
  recordShellRouteCommit("/articles/crb-formula", "initialize");
  assert.equal(getShellRouteCommitAction("/articles/crb-formula"), "initialize");
  assert.equal(
    getShellRouteCommitFocusOperationVersion("/articles/crb-formula"),
    routeOperationVersion,
  );
  assert.equal(isShellDestinationFocusAction("initialize"), false);

  recordShellRouteCommit("/articles/crb-formula", "unchanged");
  assert.equal(getShellRouteCommitAction("/articles/crb-formula"), "initialize");

  recordShellRouteCommit("/articles/crb-formula?from=%2Fsession", "route");
  assert.equal(
    getShellRouteCommitAction("/articles/crb-formula?from=%2Fsession"),
    "route",
  );
  assert.equal(isShellDestinationFocusAction("route"), true);
  assert.equal(isShellDestinationFocusAction("pending"), true);
  assert.equal(isShellDestinationFocusAction("modal"), true);
  assert.equal(isShellDestinationFocusAction("source"), false);
  assert.equal(getShellRouteCommitAction("/articles/crb-formula"), null);
});

test("a newer Shell focus operation supersedes an older route focus claim", () => {
  const routeOperationVersion = recordShellFocusOperation();
  recordShellRouteCommit("/articles/crb-formula?from=%2Fsession", "pending");
  assert.equal(
    getShellRouteCommitFocusOperationVersion("/articles/crb-formula?from=%2Fsession"),
    routeOperationVersion,
  );

  const newerOperationVersion = recordShellFocusOperation();
  assert.equal(getShellFocusOperationVersion(), newerOperationVersion);
  assert.notEqual(routeOperationVersion, newerOperationVersion);
  assert.notEqual(
    getShellRouteCommitFocusOperationVersion("/articles/crb-formula?from=%2Fsession"),
    getShellFocusOperationVersion(),
  );
});

test("a different route commit invalidates stale history focus ownership", () => {
  recordShellHistoryNavigation("/articles/crb-formula", "", "#article-outline");
  recordShellRouteCommit("/session", "route");
  assert.equal(
    hasPendingShellHistoryNavigation("/articles/crb-formula", "", "#article-outline"),
    false,
  );
});

test("Shell main fallback preserves only connected destination focus inside main", () => {
  assert.equal(shouldUseShellMainFocus(true, true, false, false), true);
  assert.equal(shouldUseShellMainFocus(false, false, false, false), true);
  assert.equal(shouldUseShellMainFocus(false, true, true, false), true);
  assert.equal(shouldUseShellMainFocus(false, true, false, false), true);
  assert.equal(shouldUseShellMainFocus(false, true, false, true), false);
});

test("Shell history fallback excludes hash-only changes but retains identical-location state", () => {
  assert.equal(
    shouldScheduleShellHistoryMainFocus("/articles/crb-formula", "/articles/crb-formula", "", "#article-outline"),
    false,
  );
  assert.equal(
    shouldScheduleShellHistoryMainFocus("/", "/", "", ""),
    true,
  );
  assert.equal(
    shouldScheduleShellHistoryMainFocus("/session", "/", "", ""),
    false,
  );
});

test("deferred Reader fragments can replace an unchanged route-origin focus", () => {
  assert.equal(
    shouldTransferDeferredReaderFragmentFocus(false, true, false, false, true),
    true,
  );
  assert.equal(
    shouldTransferDeferredReaderFragmentFocus(false, true, false, false, false),
    false,
  );
  assert.equal(
    shouldTransferDeferredReaderFragmentFocus(true, true, false, false, false),
    true,
  );
  assert.equal(
    shouldTransferDeferredReaderFragmentFocus(false, false, false, false, false),
    true,
  );
  assert.equal(
    shouldTransferDeferredReaderFragmentFocus(false, true, true, false, false),
    true,
  );
  assert.equal(
    shouldTransferDeferredReaderFragmentFocus(false, true, false, true, false),
    true,
  );
});

test("Shell route commits distinguish pending ownership, modal history, and invalidation", () => {
  assert.equal(resolveShellRouteCommitAction(null, "/", null, null, false), "initialize");
  assert.equal(resolveShellRouteCommitAction("/", "/", null, null, false), "unchanged");
  assert.equal(resolveShellRouteCommitAction("/", "/session", "/", "/session", false), "pending");
  assert.equal(resolveShellRouteCommitAction("/", "/session", "/session", "/", false), "source");
  assert.equal(resolveShellRouteCommitAction("/", "/", "/session", "/", false), "pending");
  assert.equal(
    resolveShellRouteCommitAction("/graph?q=CRB", "/graph?q=Attention", null, null, true),
    "modal",
  );
  assert.equal(resolveShellRouteCommitAction("/", "/session", "/", "/library", false), "invalidate");
  assert.equal(resolveShellRouteCommitAction("/", "/session", "/", "/library", true), "invalidate");
  assert.equal(resolveShellRouteCommitAction(null, "/", "/stale", null, false), "invalidate");
  assert.equal(resolveShellRouteCommitAction("/", "/session", null, null, false), "route");
});

test("Shell pending route lifecycle preserves slow work and rejects completed cancellation", () => {
  assert.equal(resolveShellPendingRouteLifecycleAction("/session", "/session", false, true), "target");
  assert.equal(resolveShellPendingRouteLifecycleAction("/", "/session", true, false), "observe");
  assert.equal(resolveShellPendingRouteLifecycleAction("/", "/session", true, true), "observe");
  assert.equal(resolveShellPendingRouteLifecycleAction("/", "/session", false, false), "wait");
  assert.equal(resolveShellPendingRouteLifecycleAction("/", "/session", false, true), "invalidate");
});
