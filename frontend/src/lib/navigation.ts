export type WorkspaceId = "dashboard" | "articles" | "references" | "graph" | "tutor" | "unknown";

export type PrimaryNavigationItem = {
  id: Exclude<WorkspaceId, "unknown">;
  href: string;
  label: string;
};

export type WorkspaceLocation = {
  id: WorkspaceId;
  label: string;
  trail: string[];
};

export const PRIMARY_NAVIGATION: readonly PrimaryNavigationItem[] = [
  { id: "dashboard", href: "/", label: "Dashboard" },
  { id: "articles", href: "/articles", label: "Articles" },
  { id: "references", href: "/zotero", label: "References" },
  { id: "graph", href: "/graph", label: "Graph" },
  { id: "tutor", href: "/tutor", label: "Tutor" },
];

export function isNavigationItemActive(pathname: string, item: PrimaryNavigationItem): boolean {
  const normalized = normalizePathname(pathname);
  if (item.href === "/") {
    return normalized === "/";
  }
  return normalized === item.href || normalized.startsWith(`${item.href}/`);
}

export function resolveWorkspaceLocation(pathname: string): WorkspaceLocation {
  const normalized = normalizePathname(pathname);

  if (normalized === "/") {
    return { id: "dashboard", label: "Dashboard", trail: ["Dashboard"] };
  }
  if (normalized === "/articles") {
    return { id: "articles", label: "Articles", trail: ["Articles"] };
  }
  if (normalized.startsWith("/articles/")) {
    return { id: "articles", label: "Article", trail: ["Articles", "Article"] };
  }
  if (normalized === "/zotero" || normalized.startsWith("/zotero/")) {
    return { id: "references", label: "References", trail: ["References"] };
  }
  if (normalized === "/graph" || normalized.startsWith("/graph/")) {
    return { id: "graph", label: "Graph", trail: ["Graph"] };
  }
  if (normalized === "/tutor" || normalized.startsWith("/tutor/")) {
    return { id: "tutor", label: "Tutor", trail: ["Tutor"] };
  }

  return { id: "unknown", label: "Page not found", trail: ["Page not found"] };
}

function normalizePathname(pathname: string): string {
  const value = pathname.trim();
  if (!value || value === "/") {
    return "/";
  }
  const withLeadingSlash = value.startsWith("/") ? value : `/${value}`;
  return withLeadingSlash.replace(/\/+$/, "") || "/";
}
