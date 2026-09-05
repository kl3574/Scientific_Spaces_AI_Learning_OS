import assert from "node:assert/strict";
import test from "node:test";

import {
  PRIMARY_NAVIGATION,
  createShellRouteIdentity,
  isNavigationItemActive,
  resolveShellPendingRouteLifecycleAction,
  resolveShellRouteCommitAction,
  resolveShellNavigationTarget,
  resolveWorkspaceLocation,
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

test("Shell main fallback only owns absent document focus", () => {
  assert.equal(shouldUseShellMainFocus(true, true, false), true);
  assert.equal(shouldUseShellMainFocus(false, false, false), true);
  assert.equal(shouldUseShellMainFocus(false, true, true), true);
  assert.equal(shouldUseShellMainFocus(false, true, false), false);
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
  assert.equal(resolveShellRouteCommitAction("/", "/session", null, null, false), "invalidate");
});

test("Shell pending route lifecycle preserves slow work and rejects completed cancellation", () => {
  assert.equal(resolveShellPendingRouteLifecycleAction("/session", "/session", false, true), "target");
  assert.equal(resolveShellPendingRouteLifecycleAction("/", "/session", true, false), "observe");
  assert.equal(resolveShellPendingRouteLifecycleAction("/", "/session", true, true), "observe");
  assert.equal(resolveShellPendingRouteLifecycleAction("/", "/session", false, false), "wait");
  assert.equal(resolveShellPendingRouteLifecycleAction("/", "/session", false, true), "invalidate");
});
