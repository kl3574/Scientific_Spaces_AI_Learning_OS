import {
  normalizeGlobalSearchQuery,
  normalizeGraphNodeId,
} from "./globalSearch";
import {
  parseLearningWorkflowContext,
  sanitizeArticleEntryReturnPath,
  type LearningWorkflowContext,
} from "./learningWorkflow";

export type GraphWorkspaceMode = "explore" | "context";
export type GraphExplorePanel = "results" | "selected";
export type GraphHistoryAction = "none" | "push" | "replace";

type GraphReturnFocusStorage = Pick<Storage, "getItem" | "removeItem" | "setItem">;

export type GraphArticleReturnFocusResult =
  | { status: "found"; articleId: string; focusTarget: string | null }
  | { status: "missing" }
  | { status: "unavailable" };

export type NavigationActivation = {
  altKey: boolean;
  button: number;
  ctrlKey: boolean;
  currentTarget: { target: string };
  metaKey: boolean;
  shiftKey: boolean;
};

type GraphWorkspaceHrefInput = {
  nodeId: string | null;
  query: string;
  context: LearningWorkflowContext | null;
};

const GRAPH_ARTICLE_RETURN_FOCUS_KEY = "scientific-spaces:graph-article-return-focus:v1";
const GRAPH_ARTICLE_RETURN_ORIGIN_KEY = "scientific-spaces:graph-article-return-origin:v1";
const GRAPH_ARTICLE_RETURN_PROBE_KEY = "scientific-spaces:graph-article-return-probe:v1";
const SAFE_ARTICLE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const SAFE_FOCUS_TARGET = /^[a-z][a-z0-9-]{0,39}$/;

export function createGraphWorkspaceHref({
  nodeId,
  query,
  context,
}: Readonly<GraphWorkspaceHrefInput>): string {
  const params = new URLSearchParams();
  const safeNodeId = normalizeGraphNodeId(nodeId);
  const safeQuery = normalizeGlobalSearchQuery(query);
  const safeContext = normalizeWorkflowContext(context);

  if (safeNodeId) {
    params.set("node_id", safeNodeId);
  }
  if (safeQuery) {
    params.set("q", safeQuery);
  }
  if (safeContext) {
    params.set("article_id", safeContext.articleId);
    if (safeContext.articleTitle) {
      params.set("article_title", safeContext.articleTitle);
    }
    params.set("return_to", safeContext.returnTo);
  }

  const suffix = params.toString();
  return suffix ? `/graph?${suffix}` : "/graph";
}

export function getGraphSelectionHistoryAction(
  currentNodeId: string | null,
  nextNodeId: string | null,
): GraphHistoryAction {
  const next = normalizeGraphNodeId(nextNodeId);
  if (!next || next === normalizeGraphNodeId(currentNodeId)) {
    return "none";
  }
  return "push";
}

export function getGraphCanonicalizationAction(
  currentHref: string,
  canonicalHref: string,
): GraphHistoryAction {
  return currentHref === canonicalHref ? "none" : "replace";
}

export function getGraphInitialPanel(nodeId: string | null): GraphExplorePanel {
  return normalizeGraphNodeId(nodeId) ? "selected" : "results";
}

export function rememberGraphArticleReturnFocus(
  storage: GraphReturnFocusStorage | null,
  graphHref: string,
  articleId: string,
  focusTarget: string | null = null,
): void {
  const returnTo = sanitizeArticleEntryReturnPath(graphHref);
  const safeArticleId = normalizeArticleId(articleId);
  const safeFocusTarget = normalizeFocusTarget(focusTarget);
  if (
    !returnTo.startsWith("/graph")
    || !safeArticleId
    || (focusTarget !== null && !safeFocusTarget)
  ) {
    return;
  }
  if (!storage) {
    return;
  }
  try {
    const existingOrigin = parseFocusMarker(storage.getItem(GRAPH_ARTICLE_RETURN_ORIGIN_KEY));
    const resolvedFocusTarget = safeFocusTarget ?? (
      existingOrigin?.articleId === safeArticleId
      && existingOrigin.returnTo === returnTo
        ? existingOrigin.focusTarget
        : null
    );
    const marker = JSON.stringify({
      articleId: safeArticleId,
      focusTarget: resolvedFocusTarget,
      returnTo,
    });
    if (safeFocusTarget) {
      storage.setItem(GRAPH_ARTICLE_RETURN_ORIGIN_KEY, marker);
    }
    storage.setItem(
      GRAPH_ARTICLE_RETURN_FOCUS_KEY,
      marker,
    );
  } catch {
    // Navigation remains usable when session storage is unavailable.
  }
}

export function consumeGraphArticleReturnFocus(
  storage: GraphReturnFocusStorage | null,
  graphHref: string,
): GraphArticleReturnFocusResult {
  if (!storage) {
    return { status: "unavailable" };
  }
  let raw: string | null = null;
  try {
    raw = storage.getItem(GRAPH_ARTICLE_RETURN_FOCUS_KEY);
    storage.removeItem(GRAPH_ARTICLE_RETURN_FOCUS_KEY);
  } catch {
    return { status: "unavailable" };
  }
  if (!raw) {
    try {
      storage.setItem(GRAPH_ARTICLE_RETURN_PROBE_KEY, "1");
      storage.removeItem(GRAPH_ARTICLE_RETURN_PROBE_KEY);
    } catch {
      return { status: "unavailable" };
    }
    return { status: "missing" };
  }
  const marker = parseFocusMarker(raw);
  const currentReturnTo = sanitizeArticleEntryReturnPath(graphHref);
  if (
    !marker
    || !currentReturnTo.startsWith("/graph")
    || marker.returnTo !== currentReturnTo
  ) {
    return { status: "missing" };
  }
  return {
    status: "found",
    articleId: marker.articleId,
    focusTarget: marker.focusTarget,
  };
}

export function getGraphSessionStorage(
  target: { readonly sessionStorage: GraphReturnFocusStorage } | null | undefined,
): GraphReturnFocusStorage | null {
  try {
    return target?.sessionStorage ?? null;
  } catch {
    return null;
  }
}

export function isSameTabNavigation(event: NavigationActivation): boolean {
  return event.button === 0
    && !event.altKey
    && !event.ctrlKey
    && !event.metaKey
    && !event.shiftKey
    && event.currentTarget.target !== "_blank";
}

function normalizeWorkflowContext(
  context: LearningWorkflowContext | null,
): LearningWorkflowContext | null {
  if (!context) {
    return null;
  }
  return parseLearningWorkflowContext({
    article_id: context.articleId,
    article_title: context.articleTitle ?? undefined,
    return_to: context.returnTo,
    node_id: `article:${context.articleId}`,
  });
}

function normalizeArticleId(value: string): string | null {
  const clean = value.trim();
  return SAFE_ARTICLE_ID.test(clean) ? clean : null;
}

function normalizeFocusTarget(value: string | null | undefined): string | null {
  const clean = value?.trim() ?? "";
  return SAFE_FOCUS_TARGET.test(clean) ? clean : null;
}

function parseFocusMarker(raw: string | null): {
  articleId: string;
  focusTarget: string | null;
  returnTo: string;
} | null {
  if (!raw) {
    return null;
  }
  try {
    const marker = JSON.parse(raw) as {
      articleId?: unknown;
      focusTarget?: unknown;
      returnTo?: unknown;
    };
    const articleId = typeof marker.articleId === "string"
      ? normalizeArticleId(marker.articleId)
      : null;
    const returnTo = typeof marker.returnTo === "string"
      ? sanitizeArticleEntryReturnPath(marker.returnTo)
      : "/articles";
    const focusTarget = typeof marker.focusTarget === "string"
      ? normalizeFocusTarget(marker.focusTarget)
      : null;
    if (marker.focusTarget !== undefined && marker.focusTarget !== null && !focusTarget) {
      return null;
    }
    return articleId && returnTo.startsWith("/graph")
      ? { articleId, focusTarget, returnTo }
      : null;
  } catch {
    return null;
  }
}
