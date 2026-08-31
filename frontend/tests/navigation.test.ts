import assert from "node:assert/strict";
import test from "node:test";

import {
  PRIMARY_NAVIGATION,
  isNavigationItemActive,
  resolveWorkspaceLocation,
} from "../src/lib/navigation";

test("primary navigation exposes every stable workspace root once", () => {
  assert.deepEqual(
    PRIMARY_NAVIGATION.map(({ id, href, label }) => ({ id, href, label })),
    [
      { id: "dashboard", href: "/", label: "Dashboard" },
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
  const articles = PRIMARY_NAVIGATION[1];

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
  assert.equal(resolveWorkspaceLocation("/zotero").id, "references");
  assert.equal(resolveWorkspaceLocation("/graph/context").id, "graph");
  assert.equal(resolveWorkspaceLocation("tutor").id, "tutor");
  assert.deepEqual(resolveWorkspaceLocation("/missing"), {
    id: "unknown",
    label: "Page not found",
    trail: ["Page not found"],
  });
});
