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
  | "route"
  | "invalidate";

export type ShellPendingRouteLifecycleAction = "target" | "observe" | "wait" | "invalidate";

export type ShellHistoryNavigation = Readonly<{
  hash: string;
  pathname: string;
  search: string;
}>;

export type ShellRouteCommit = Readonly<{
  action: ShellRouteCommitAction;
  focusOperationVersion: number;
  identity: string;
}>;

export const SHELL_HISTORY_NAVIGATION_EVENT = "scientific-spaces:shell-history-navigation";
export const SHELL_FOCUS_OPERATION_EVENT = "scientific-spaces:shell-focus-operation";
export const SHELL_ROUTE_COMMIT_EVENT = "scientific-spaces:shell-route-commit";

let pendingShellHistoryNavigation: ShellHistoryNavigation | null = null;
let latestShellRouteCommit: ShellRouteCommit | null = null;
let shellFocusOperationVersion = 0;
const pendingShellDestinationFocusIntents = new Map<string, string>();

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

export function recordShellDestinationFocusIntent(href: string, baseHref: string): void {
  const targetIdentity = resolveShellNavigationTarget(href, baseHref);
  let sourceIdentity: string | null = null;
  try {
    const source = new URL(baseHref);
    if (source.protocol === "http:" || source.protocol === "https:") {
      sourceIdentity = createShellRouteIdentity(source.pathname, source.search);
    }
  } catch {
    sourceIdentity = null;
  }
  if (!targetIdentity || !sourceIdentity) {
    return;
  }
  pendingShellDestinationFocusIntents.delete(targetIdentity);
  pendingShellDestinationFocusIntents.set(targetIdentity, sourceIdentity);
  while (pendingShellDestinationFocusIntents.size > 8) {
    const oldest = pendingShellDestinationFocusIntents.keys().next().value;
    if (typeof oldest !== "string") {
      break;
    }
    pendingShellDestinationFocusIntents.delete(oldest);
  }
}

export function consumeShellDestinationFocusIntent(
  targetIdentity: string,
  sourceIdentity: string | null,
): boolean {
  const expectedSourceIdentity = pendingShellDestinationFocusIntents.get(targetIdentity);
  if (!expectedSourceIdentity) {
    return false;
  }
  pendingShellDestinationFocusIntents.delete(targetIdentity);
  return sourceIdentity === expectedSourceIdentity;
}

export function recordShellHistoryNavigation(
  pathname: string,
  search: string,
  hash: string,
): void {
  pendingShellHistoryNavigation = { pathname, search, hash };
}

export function consumeShellHistoryNavigation(
  pathname: string,
  search: string,
  hash: string,
): ShellHistoryNavigation | null {
  const pending = pendingShellHistoryNavigation;
  if (
    !pending
    || pending.pathname !== pathname
    || pending.search !== search
    || pending.hash !== hash
  ) {
    return null;
  }
  pendingShellHistoryNavigation = null;
  return pending;
}

export function hasPendingShellHistoryNavigation(
  pathname: string,
  search: string,
  hash: string,
): boolean {
  return pendingShellHistoryNavigation?.pathname === pathname
    && pendingShellHistoryNavigation.search === search
    && pendingShellHistoryNavigation.hash === hash;
}

export function recordShellRouteCommit(
  identity: string,
  action: ShellRouteCommitAction,
): void {
  if (
    pendingShellHistoryNavigation
    && createShellRouteIdentity(
      pendingShellHistoryNavigation.pathname,
      pendingShellHistoryNavigation.search,
    ) !== identity
  ) {
    pendingShellHistoryNavigation = null;
  }
  if (action !== "unchanged") {
    latestShellRouteCommit = {
      action,
      focusOperationVersion: shellFocusOperationVersion,
      identity,
    };
  }
}

export function recordShellFocusOperation(): number {
  shellFocusOperationVersion += 1;
  pendingShellDestinationFocusIntents.clear();
  return shellFocusOperationVersion;
}

export function getShellFocusOperationVersion(): number {
  return shellFocusOperationVersion;
}

export function getShellRouteCommitAction(identity: string): ShellRouteCommitAction | null {
  return latestShellRouteCommit?.identity === identity
    ? latestShellRouteCommit.action
    : null;
}

export function getShellRouteCommitFocusOperationVersion(identity: string): number | null {
  return latestShellRouteCommit?.identity === identity
    ? latestShellRouteCommit.focusOperationVersion
    : null;
}

export function isShellDestinationFocusAction(
  action: ShellRouteCommitAction | null,
): boolean {
  return action === "pending" || action === "modal" || action === "route";
}

export function shouldUseShellMainFocus(
  activeIsBody: boolean,
  activeIsConnected: boolean,
  activeIsShellOrigin: boolean,
  activeIsInsideMain: boolean,
): boolean {
  return activeIsBody || !activeIsConnected || activeIsShellOrigin || !activeIsInsideMain;
}

export function shouldScheduleShellHistoryMainFocus(
  previousIdentity: string | null,
  nextIdentity: string,
  previousHash: string | null,
  nextHash: string,
): boolean {
  return previousIdentity === nextIdentity
    && previousHash !== null
    && previousHash === nextHash;
}

export function shouldTransferDeferredReaderFragmentFocus(
  activeIsBody: boolean,
  activeIsConnected: boolean,
  activeIsMain: boolean,
  activeIsTarget: boolean,
  activeMatchesInitial: boolean,
): boolean {
  return activeIsBody
    || !activeIsConnected
    || activeIsMain
    || activeIsTarget
    || activeMatchesInitial;
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
  if (pendingSourceIdentity !== null || pendingTargetIdentity !== null) {
    return "invalidate";
  }
  if (previousIdentity === nextIdentity) {
    return "unchanged";
  }
  if (previousIdentity === null) {
    return pendingSourceIdentity !== null || pendingTargetIdentity !== null
      ? "invalidate"
      : "initialize";
  }
  if (modalOpen) {
    return "modal";
  }
  return "route";
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
