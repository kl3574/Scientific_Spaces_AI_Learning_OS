import type { ArticleSummary } from "./articles";
import { createResumeHref, type ReaderProgressState } from "./articleWorkspace";
import type { LearningStats, LearningStatus } from "./learning";
import { createArticleReturnHref } from "./learningWorkflow";
import type { ReadingHistoryItem } from "./readingHistory";
import type { StudySessionState } from "./studySession";

export const DASHBOARD_ACTIVITY_LIMIT = 8;

export type DashboardOverview = {
  articleTotal: number | null;
  readingCount: number | null;
  completedCount: number | null;
  unreadCount: number | null;
  bookmarkCount: number | null;
  noteCount: number | null;
  completionPercent: number | null;
};

export type DashboardContinueItem = {
  articleId: string;
  title: string;
  href: string;
  sectionTitle: string | null;
  progress: number;
  updatedAt: string;
};

export type DashboardStudySession = {
  count: number;
  position: number;
  currentTitle: string;
  currentHref: string;
  nextTitle: string | null;
  progress: number | null;
  sectionTitle: string | null;
  updatedAt: string;
};

export type DashboardActivityKind = "learning" | "session" | "history";

export type DashboardActivityItem = {
  id: string;
  articleId: string;
  title: string;
  href: string;
  kind: DashboardActivityKind;
  detail: string;
  timestamp: string;
};

export function createDashboardOverview(
  articleTotal: number | null,
  stats: LearningStats | null,
): DashboardOverview {
  const total = normalizeOptionalCount(articleTotal ?? stats?.total_articles ?? null);
  const completed = normalizeOptionalCount(stats?.completed_count ?? null);
  return {
    articleTotal: total,
    readingCount: normalizeOptionalCount(stats?.reading_count ?? null),
    completedCount: completed,
    unreadCount: normalizeOptionalCount(stats?.unread_count ?? null),
    bookmarkCount: normalizeOptionalCount(stats?.bookmark_count ?? null),
    noteCount: normalizeOptionalCount(stats?.note_count ?? null),
    completionPercent:
      total !== null && completed !== null && total > 0
        ? Math.min(100, Math.round((completed / total) * 100))
        : total === 0 && completed !== null
          ? 0
          : null,
  };
}

export function createArticleTitleIndex(
  articles: ArticleSummary[],
  stats: LearningStats | null,
  history: ReadingHistoryItem[],
): Map<string, string> {
  const titles = new Map<string, string>();
  for (const item of history) {
    setTitle(titles, item.id, item.title);
  }
  for (const item of stats?.recent_articles ?? []) {
    setTitle(titles, item.article_id, item.title);
  }
  for (const article of articles) {
    setTitle(titles, article.id, article.title);
  }
  return titles;
}

export function selectContinueLearning(
  history: ReadingHistoryItem[],
  progressItems: ReaderProgressState[],
  titles: ReadonlyMap<string, string>,
): DashboardContinueItem | null {
  const historyById = new Map(history.map((item) => [item.id, item]));
  const progressById = new Map(progressItems.map((item) => [item.article_id, item]));
  const articleIds = new Set([...historyById.keys(), ...progressById.keys()]);
  const candidates: DashboardContinueItem[] = [];

  for (const articleId of articleIds) {
    const historyItem = historyById.get(articleId) ?? null;
    const progress = progressById.get(articleId) ?? null;
    const updatedAt = latestValidTimestamp(progress?.updated_at, historyItem?.last_read_at);
    if (!updatedAt) {
      continue;
    }
    const title = cleanTitle(titles.get(articleId)) ?? cleanTitle(historyItem?.title);
    if (!title) {
      continue;
    }
    candidates.push({
      articleId,
      title,
      href: createResumeHref(articleId, progress),
      sectionTitle: cleanTitle(progress?.section_title),
      progress: clampPercent(progress?.progress ?? 0),
      updatedAt,
    });
  }

  return candidates.sort((left, right) => {
    const timeDifference = timestampValue(right.updatedAt) - timestampValue(left.updatedAt);
    return timeDifference !== 0 ? timeDifference : left.articleId.localeCompare(right.articleId);
  })[0] ?? null;
}

export function createDashboardStudySession(
  state: StudySessionState,
  progressItems: ReaderProgressState[],
): DashboardStudySession | null {
  const items = state.items.flatMap((item) => {
    const title = safeDisplayTitle(item.articleId, item.title);
    return title ? [{ ...item, title }] : [];
  });
  if (!items.length) {
    return null;
  }

  const activeIndex = Math.max(0, items.findIndex((item) => item.articleId === state.activeArticleId));
  const current = items[activeIndex];
  const progress = progressItems
    .filter((item) => item.article_id === current.articleId)
    .sort((left, right) => timestampValue(right.updated_at) - timestampValue(left.updated_at))[0] ?? null;
  const sectionId = progress?.section_id ?? current.sectionId;

  return {
    count: items.length,
    position: activeIndex + 1,
    currentTitle: current.title,
    currentHref: createArticleReturnHref(current.articleId, "/session", sectionId),
    nextTitle: cleanTitle(items[activeIndex + 1]?.title),
    progress: progress ? clampPercent(progress.progress) : null,
    sectionTitle: cleanTitle(progress?.section_title),
    updatedAt: state.updatedAt,
  };
}

export function buildDashboardActivity(
  stats: LearningStats | null,
  history: ReadingHistoryItem[],
  titles: ReadonlyMap<string, string>,
  limit = DASHBOARD_ACTIVITY_LIMIT,
): DashboardActivityItem[] {
  const events: DashboardActivityItem[] = [];
  const learningArticleIds = new Set<string>();

  for (const item of stats?.recent_articles ?? []) {
    const timestamp = latestValidTimestamp(item.last_read_at, item.updated_at);
    if (!timestamp) {
      continue;
    }
    learningArticleIds.add(item.article_id);
    events.push({
      id: `learning:${item.article_id}`,
      articleId: item.article_id,
      title: resolveTitle(item.article_id, item.title, titles),
      href: articleHref(item.article_id),
      kind: "learning",
      detail: learningStatusLabel(item.status),
      timestamp,
    });
  }

  for (const item of stats?.recent_sessions ?? []) {
    const timestamp = latestValidTimestamp(item.ended_at, item.started_at);
    if (!timestamp) {
      continue;
    }
    events.push({
      id: `session:${item.session_id}`,
      articleId: item.article_id,
      title: resolveTitle(item.article_id, null, titles),
      href: articleHref(item.article_id),
      kind: "session",
      detail: sessionLabel(item.source, item.duration_seconds),
      timestamp,
    });
  }

  for (const item of history) {
    if (learningArticleIds.has(item.id) || !isValidTimestamp(item.last_read_at)) {
      continue;
    }
    events.push({
      id: `history:${item.id}`,
      articleId: item.id,
      title: resolveTitle(item.id, item.title, titles),
      href: articleHref(item.id),
      kind: "history",
      detail: "Opened in Reader",
      timestamp: item.last_read_at,
    });
  }

  const boundedLimit = Math.min(12, Math.max(1, Math.trunc(limit) || DASHBOARD_ACTIVITY_LIMIT));
  return events
    .sort((left, right) => {
      const timeDifference = timestampValue(right.timestamp) - timestampValue(left.timestamp);
      return timeDifference !== 0 ? timeDifference : left.id.localeCompare(right.id);
    })
    .slice(0, boundedLimit);
}

function normalizeOptionalCount(value: number | null): number | null {
  if (value === null || !Number.isFinite(value)) {
    return null;
  }
  return Math.max(0, Math.trunc(value));
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.min(100, Math.max(0, Math.round(value)));
}

function setTitle(titles: Map<string, string>, articleId: string, value: string | null | undefined) {
  const title = cleanTitle(value);
  if (articleId && title) {
    titles.set(articleId, title);
  }
}

function cleanTitle(value: string | null | undefined): string | null {
  const normalized = value?.replace(/\s+/g, " ").trim();
  return normalized || null;
}

function safeDisplayTitle(articleId: string, title: string): string | null {
  const normalizedTitle = cleanTitle(title);
  const normalizedId = articleId.trim();
  if (
    !normalizedTitle
    || !normalizedId
    || normalizedTitle.normalize("NFKC").toLocaleLowerCase()
      === normalizedId.normalize("NFKC").toLocaleLowerCase()
  ) {
    return null;
  }
  return normalizedTitle;
}

function latestValidTimestamp(...values: Array<string | null | undefined>): string | null {
  return values
    .filter((value): value is string => isValidTimestamp(value))
    .sort((left, right) => timestampValue(right) - timestampValue(left))[0] ?? null;
}

function isValidTimestamp(value: string | null | undefined): value is string {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function timestampValue(value: string): number {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function resolveTitle(
  articleId: string,
  preferred: string | null | undefined,
  titles: ReadonlyMap<string, string>,
): string {
  return cleanTitle(titles.get(articleId)) ?? cleanTitle(preferred) ?? "Untitled article";
}

function articleHref(articleId: string): string {
  return `/articles/${encodeURIComponent(articleId)}`;
}

function learningStatusLabel(status: LearningStatus): string {
  if (status === "completed") {
    return "Completed";
  }
  if (status === "reading") {
    return "Reading in progress";
  }
  return "Added to learning";
}

function sessionLabel(source: "reader" | "rag", durationSeconds: number | null): string {
  const sourceLabel = source === "reader" ? "Reader session" : "Research session";
  return durationSeconds === null ? sourceLabel : `${sourceLabel} · ${formatDuration(durationSeconds)}`;
}

function formatDuration(seconds: number): string {
  const normalized = Math.max(0, Math.round(seconds));
  if (normalized < 60) {
    return `${normalized}s`;
  }
  const minutes = Math.floor(normalized / 60);
  const remainder = normalized % 60;
  return remainder ? `${minutes}m ${remainder}s` : `${minutes}m`;
}
