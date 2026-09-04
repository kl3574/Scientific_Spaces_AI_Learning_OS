import {
  normalizeGlobalSearchQuery,
  normalizeGraphNodeId,
} from "./globalSearch";
import {
  parseLearningWorkflowContext,
  type LearningWorkflowContext,
} from "./learningWorkflow";

export type GraphWorkspaceMode = "explore" | "context";
export type GraphExplorePanel = "results" | "selected";
export type GraphHistoryAction = "none" | "push" | "replace";

type GraphWorkspaceHrefInput = {
  nodeId: string | null;
  query: string;
  context: LearningWorkflowContext | null;
};

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
