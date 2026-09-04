import type { ArticleSummary } from "./articles";
import type { LearningState } from "./learning";
import {
  addStudySessionItems,
  addStudySessionItem,
  type StudySessionBulkMutation,
  type StudySessionState,
} from "./studySession";

export type ArticleSessionCandidate = Pick<ArticleSummary, "id" | "title">;
export type ArticleBadgeAvailability = "loading" | "loaded" | "error";

export type ArticleSessionCapturePlan = {
  selectedArticles: ArticleSessionCandidate[];
  mutation: StudySessionBulkMutation;
  remainingSelectionIds: string[];
  requiresSave: boolean;
};

export function ownsArticleResultGeneration(candidate: number, active: number): boolean {
  return Number.isSafeInteger(candidate) && candidate > 0 && candidate === active;
}

export function reconcileArticleSelection(
  visibleArticles: readonly ArticleSessionCandidate[],
  selectedIds: readonly string[],
): string[] {
  const selected = new Set(selectedIds);
  const emitted = new Set<string>();
  const reconciled: string[] = [];

  for (const article of visibleArticles) {
    if (!selected.has(article.id) || emitted.has(article.id)) {
      continue;
    }
    emitted.add(article.id);
    reconciled.push(article.id);
  }
  return reconciled;
}

export function updateArticleSelection(
  visibleArticles: readonly ArticleSessionCandidate[],
  selectedIds: readonly string[],
  articleId: string,
  selected: boolean,
): string[] {
  const visibleIds = new Set(visibleArticles.map((article) => article.id));
  if (!visibleIds.has(articleId)) {
    return reconcileArticleSelection(visibleArticles, selectedIds);
  }

  const next = new Set(reconcileArticleSelection(visibleArticles, selectedIds));
  if (selected) {
    next.add(articleId);
  } else {
    next.delete(articleId);
  }
  return reconcileArticleSelection(visibleArticles, [...next]);
}

export function getArticleLearningStatusLabel(
  availability: ArticleBadgeAvailability,
  states: Readonly<Record<string, Pick<LearningState, "article_id" | "status">>>,
  articleId: string,
): LearningState["status"] | "Status loading" | "Status unavailable" {
  if (availability === "loading") {
    return "Status loading";
  }
  if (availability === "error") {
    return "Status unavailable";
  }
  return states[articleId]?.status ?? "unread";
}

export function createArticleSessionCapturePlan(
  visibleArticles: readonly ArticleSessionCandidate[],
  selectedIds: readonly string[],
  reloadedSession: StudySessionState,
  updatedAt: string,
): ArticleSessionCapturePlan {
  const reconciledIds = reconcileArticleSelection(visibleArticles, selectedIds);
  const selected = new Set(reconciledIds);
  const selectedArticles = visibleArticles.filter((article, index, all) =>
    selected.has(article.id) && all.findIndex((candidate) => candidate.id === article.id) === index,
  );
  const mutation = addStudySessionItems(
    reloadedSession,
    selectedArticles.map((article) => ({ articleId: article.id, title: article.title })),
    updatedAt,
  );
  const resolvedIds = new Set<string>();
  let classificationState = reloadedSession;
  for (const article of selectedArticles) {
    const itemMutation = addStudySessionItem(
      classificationState,
      { articleId: article.id, title: article.title },
      updatedAt,
    );
    if (itemMutation.outcome === "added") {
      classificationState = itemMutation.state;
      resolvedIds.add(article.id);
    } else if (itemMutation.outcome === "already-present") {
      resolvedIds.add(article.id);
    }
  }

  return {
    selectedArticles,
    mutation,
    remainingSelectionIds: reconciledIds.filter((articleId) => !resolvedIds.has(articleId)),
    requiresSave: mutation.changed,
  };
}

export function formatArticleSessionCaptureOutcome(
  outcomes: StudySessionBulkMutation["outcomes"],
): string {
  return [
    `${outcomes.added} added`,
    `${outcomes.alreadyPresent} already present`,
    `${outcomes.invalid} invalid`,
    `${outcomes.capacityOmitted} omitted by capacity`,
  ].join("; ") + ".";
}
