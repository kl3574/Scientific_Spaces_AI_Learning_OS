import type { ReaderProgressState } from "./articleWorkspace";
import type { Bookmark, LearningState, LearningStatus, RecentLearningArticle } from "./learning";
import { createArticleReturnHref, type SearchParamInput } from "./learningWorkflow";
import type { ReadingHistoryItem } from "./readingHistory";

export const SAVED_LIBRARY_ITEM_LIMIT = 100;
export type SavedLibraryView = "all" | "continue" | "bookmarked" | "recent";
export type SavedLibrarySort = "recent" | "title" | "progress";

export type SavedLibraryState = {
  q: string;
  view: SavedLibraryView;
  sort: SavedLibrarySort;
};

export type SavedLibraryItem = {
  articleId: string;
  title: string;
  href: string;
  status: LearningStatus;
  isBookmarked: boolean;
  progress: number;
  sectionId: string | null;
  sectionTitle: string | null;
  lastReadAt: string | null;
  savedAt: string | null;
  readCount: number;
};

export type SavedLibraryModel = {
  items: SavedLibraryItem[];
  counts: Record<SavedLibraryView, number>;
  unavailableCount: number;
  truncatedCount: number;
};

export type SavedLibraryInput = {
  states: LearningState[];
  bookmarks: Bookmark[];
  history: ReadingHistoryItem[];
  progressItems: ReaderProgressState[];
  recentArticles: RecentLearningArticle[];
};

type MutableLibraryItem = {
  articleId: string;
  title: string | null;
  status: LearningStatus;
  isBookmarked: boolean;
  progress: number;
  sectionId: string | null;
  sectionTitle: string | null;
  lastReadAt: string | null;
  savedAt: string | null;
  readCount: number;
};

const DEFAULT_STATE: SavedLibraryState = { q: "", view: "all", sort: "recent" };
const SAFE_ARTICLE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const SAFE_SECTION_ID = /^[\p{Letter}\p{Number}](?:[\p{Letter}\p{Number}-]{0,199})$/u;
const VALID_VIEWS = new Set<SavedLibraryView>(["all", "continue", "bookmarked", "recent"]);
const VALID_SORTS = new Set<SavedLibrarySort>(["recent", "title", "progress"]);

export function buildSavedLibrary(input: SavedLibraryInput): SavedLibraryModel {
  const records = new Map<string, MutableLibraryItem>();
  const unavailableIds = new Set<string>();

  function recordFor(articleId: string): MutableLibraryItem | null {
    const cleanId = articleId.trim();
    if (!SAFE_ARTICLE_ID.test(cleanId)) {
      if (cleanId) {
        unavailableIds.add(cleanId);
      }
      return null;
    }
    const current = records.get(cleanId);
    if (current) {
      return current;
    }
    const created: MutableLibraryItem = {
      articleId: cleanId,
      title: null,
      status: "unread",
      isBookmarked: false,
      progress: 0,
      sectionId: null,
      sectionTitle: null,
      lastReadAt: null,
      savedAt: null,
      readCount: 0,
    };
    records.set(cleanId, created);
    return created;
  }

  for (const progress of input.progressItems) {
    const record = recordFor(progress.article_id);
    if (!record) {
      continue;
    }
    record.progress = clampProgress(progress.progress);
    record.sectionId = normalizeSectionId(progress.section_id);
    record.sectionTitle = normalizeTitle(progress.section_title);
    record.lastReadAt = latestTimestamp(record.lastReadAt, progress.updated_at);
  }

  for (const recent of input.recentArticles) {
    const record = recordFor(recent.article_id);
    if (!record) {
      continue;
    }
    record.title = record.title ?? normalizeTitle(recent.title);
    record.status = recent.status;
    record.lastReadAt = latestTimestamp(record.lastReadAt, recent.last_read_at, recent.updated_at);
  }

  for (const state of input.states) {
    const record = recordFor(state.article_id);
    if (!record) {
      continue;
    }
    record.status = state.status;
    record.readCount = normalizeCount(state.read_count);
    record.lastReadAt = latestTimestamp(record.lastReadAt, state.last_read_at);
  }

  for (const historyItem of input.history) {
    const record = recordFor(historyItem.id);
    if (!record) {
      continue;
    }
    record.title = normalizeTitle(historyItem.title) ?? record.title;
    record.lastReadAt = latestTimestamp(record.lastReadAt, historyItem.last_read_at);
  }

  for (const bookmark of input.bookmarks) {
    const record = recordFor(bookmark.article_id);
    if (!record) {
      continue;
    }
    record.title = normalizeTitle(bookmark.title) ?? record.title;
    record.isBookmarked = true;
    record.savedAt = normalizeTimestamp(bookmark.created_at);
  }

  const available: SavedLibraryItem[] = [];
  for (const record of records.values()) {
    if (!record.title) {
      unavailableIds.add(record.articleId);
      continue;
    }
    available.push({
      articleId: record.articleId,
      title: record.title,
      href: createArticleReturnHref(record.articleId, "/library", record.sectionId),
      status: record.status,
      isBookmarked: record.isBookmarked,
      progress: record.progress,
      sectionId: record.sectionId,
      sectionTitle: record.sectionTitle,
      lastReadAt: record.lastReadAt,
      savedAt: record.savedAt,
      readCount: record.readCount,
    });
  }

  const ordered = sortSavedLibraryItems(available, "recent");
  const items = ordered.slice(0, SAVED_LIBRARY_ITEM_LIMIT);
  return {
    items,
    counts: {
      all: items.length,
      continue: items.filter(isContinueItem).length,
      bookmarked: items.filter((item) => item.isBookmarked).length,
      recent: items.filter((item) => item.lastReadAt !== null).length,
    },
    unavailableCount: unavailableIds.size,
    truncatedCount: Math.max(0, ordered.length - items.length),
  };
}

export function parseSavedLibraryState(input: SearchParamInput): SavedLibraryState {
  const view = readParam(input, "view");
  const sort = readParam(input, "sort");
  return {
    q: normalizeQuery(readParam(input, "q")),
    view: VALID_VIEWS.has(view as SavedLibraryView) ? (view as SavedLibraryView) : DEFAULT_STATE.view,
    sort: VALID_SORTS.has(sort as SavedLibrarySort) ? (sort as SavedLibrarySort) : DEFAULT_STATE.sort,
  };
}

export function createSavedLibraryHref(state: SavedLibraryState): string {
  const normalized = parseSavedLibraryState(state);
  const params = new URLSearchParams();
  if (normalized.q) {
    params.set("q", normalized.q);
  }
  if (normalized.view !== DEFAULT_STATE.view) {
    params.set("view", normalized.view);
  }
  if (normalized.sort !== DEFAULT_STATE.sort) {
    params.set("sort", normalized.sort);
  }
  const suffix = params.toString();
  return suffix ? `/library?${suffix}` : "/library";
}

export function selectSavedLibraryItems(
  items: SavedLibraryItem[],
  state: SavedLibraryState,
): SavedLibraryItem[] {
  const normalized = parseSavedLibraryState(state);
  const query = normalizeQuery(normalized.q).toLocaleLowerCase();
  const filtered = items.filter((item) => {
    if (normalized.view === "continue" && !isContinueItem(item)) {
      return false;
    }
    if (normalized.view === "bookmarked" && !item.isBookmarked) {
      return false;
    }
    if (normalized.view === "recent" && !item.lastReadAt) {
      return false;
    }
    if (!query) {
      return true;
    }
    return `${item.title} ${item.sectionTitle ?? ""} ${item.status}`.toLocaleLowerCase().includes(query);
  });
  return sortSavedLibraryItems(filtered, normalized.sort);
}

export function createSavedLibraryReaderHref(articleId: string, state: SavedLibraryState, sectionId?: string | null): string {
  return createArticleReturnHref(articleId, createSavedLibraryHref(state), sectionId);
}

function sortSavedLibraryItems(items: SavedLibraryItem[], sort: SavedLibrarySort): SavedLibraryItem[] {
  return [...items].sort((left, right) => {
    if (sort === "title") {
      const titleOrder = compareText(left.title, right.title);
      return titleOrder !== 0 ? titleOrder : compareText(left.articleId, right.articleId);
    }
    if (sort === "progress") {
      const progressOrder = right.progress - left.progress;
      return progressOrder !== 0 ? progressOrder : compareText(left.title, right.title);
    }
    const timeOrder = timestampValue(activityTimestamp(right)) - timestampValue(activityTimestamp(left));
    return timeOrder !== 0 ? timeOrder : compareText(left.title, right.title);
  });
}

function isContinueItem(item: SavedLibraryItem): boolean {
  return item.status !== "completed" && (item.status === "reading" || item.progress > 0);
}

function normalizeQuery(value: string): string {
  return value.replace(/[\u0000-\u001f\u007f]+/g, " ").replace(/\s+/g, " ").trim().slice(0, 120);
}

function normalizeSectionId(value: string | null | undefined): string | null {
  const normalized = value?.trim() ?? "";
  return SAFE_SECTION_ID.test(normalized) ? normalized : null;
}

function normalizeTitle(value: string | null | undefined): string | null {
  const normalized = (value ?? "")
    .replace(/[\u0000-\u001f\u007f]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 240);
  return normalized || null;
}

function normalizeCount(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.trunc(value)) : 0;
}

function clampProgress(value: number): number {
  return Number.isFinite(value) ? Math.min(100, Math.max(0, Math.round(value))) : 0;
}

function latestTimestamp(...values: Array<string | null | undefined>): string | null {
  return values
    .map(normalizeTimestamp)
    .filter((value): value is string => value !== null)
    .sort((left, right) => timestampValue(right) - timestampValue(left))[0] ?? null;
}

function normalizeTimestamp(value: string | null | undefined): string | null {
  return typeof value === "string" && Number.isFinite(Date.parse(value)) ? value : null;
}

function activityTimestamp(item: SavedLibraryItem): string | null {
  return latestTimestamp(item.lastReadAt, item.savedAt);
}

function timestampValue(value: string | null): number {
  const parsed = value ? Date.parse(value) : 0;
  return Number.isFinite(parsed) ? parsed : 0;
}

function compareText(left: string, right: string): number {
  const normalizedLeft = left.normalize("NFKC").toLocaleLowerCase();
  const normalizedRight = right.normalize("NFKC").toLocaleLowerCase();
  return normalizedLeft < normalizedRight ? -1 : normalizedLeft > normalizedRight ? 1 : 0;
}

function readParam(input: SearchParamInput, key: string): string {
  const value = input instanceof URLSearchParams ? input.get(key) : input[key];
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}
