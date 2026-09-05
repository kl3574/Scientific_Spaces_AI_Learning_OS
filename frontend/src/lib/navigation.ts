export type WorkspaceId = "dashboard" | "library" | "session" | "articles" | "references" | "graph" | "tutor" | "unknown";

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

export type ShellNavigationEvent = {
  preventDefault: () => void;
};

export type ShellRouteCommitAction =
  | "initialize"
  | "unchanged"
  | "source"
  | "pending"
  | "modal"
  | "invalidate";

export type ShellPendingRouteLifecycleAction = "target" | "observe" | "wait" | "invalidate";

export const PRIMARY_NAVIGATION: readonly PrimaryNavigationItem[] = [
  { id: "dashboard", href: "/", label: "Dashboard" },
  { id: "library", href: "/library", label: "Saved" },
  { id: "session", href: "/session", label: "Session" },
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
  if (normalized === "/library" || normalized.startsWith("/library/")) {
    return { id: "library", label: "Saved", trail: ["Saved Learning"] };
  }
  if (normalized === "/session" || normalized.startsWith("/session/")) {
    return { id: "session", label: "Session", trail: ["Study Session"] };
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

export function createShellRouteIdentity(pathname: string, search: string): string {
  const normalizedPathname = normalizePathname(pathname);
  const parameters = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  parameters.sort();
  const normalizedSearch = parameters.toString();
  return normalizedSearch ? `${normalizedPathname}?${normalizedSearch}` : normalizedPathname;
}

export function resolveShellNavigationTarget(href: string, baseHref: string): string | null {
  let base: URL;
  let target: URL;
  try {
    base = new URL(baseHref);
    target = new URL(href, base);
  } catch {
    return null;
  }
  if ((target.protocol !== "http:" && target.protocol !== "https:") || target.origin !== base.origin) {
    return null;
  }
  return createShellRouteIdentity(target.pathname, target.search);
}

export function shouldUseShellMainFocus(
  activeIsBody: boolean,
  activeIsConnected: boolean,
  activeIsShellOrigin: boolean,
): boolean {
  return activeIsBody || !activeIsConnected || activeIsShellOrigin;
}

export function resolveShellRouteCommitAction(
  previousIdentity: string | null,
  nextIdentity: string,
  pendingSourceIdentity: string | null,
  pendingTargetIdentity: string | null,
  modalOpen: boolean,
): ShellRouteCommitAction {
  if (pendingTargetIdentity === nextIdentity) {
    return "pending";
  }
  if (pendingSourceIdentity === nextIdentity) {
    return "source";
  }
  if (previousIdentity === nextIdentity) {
    return "unchanged";
  }
  if (previousIdentity === null && pendingTargetIdentity === null) {
    return "initialize";
  }
  if (modalOpen) {
    return "modal";
  }
  return "invalidate";
}

export function resolveShellPendingRouteLifecycleAction(
  currentIdentity: string,
  targetIdentity: string,
  transitionPending: boolean,
  transitionPendingObserved: boolean,
): ShellPendingRouteLifecycleAction {
  if (currentIdentity === targetIdentity) {
    return "target";
  }
  if (transitionPending) {
    return "observe";
  }
  return transitionPendingObserved ? "invalidate" : "wait";
}

function normalizePathname(pathname: string): string {
  const value = pathname.trim();
  if (!value || value === "/") {
    return "/";
  }
  const withLeadingSlash = value.startsWith("/") ? value : `/${value}`;
  return withLeadingSlash.replace(/\/+$/, "") || "/";
}
