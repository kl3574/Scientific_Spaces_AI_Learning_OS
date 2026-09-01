import { createArticleReturnHref } from "./learningWorkflow";

export const STUDY_SESSION_ITEM_LIMIT = 20;
export const STUDY_SESSION_STORAGE_KEY = "scientific-spaces-study-session-v1";
export const STUDY_SESSION_CHANGE_EVENT = "scientific-spaces-study-session-change";

export type StudySessionItem = {
  articleId: string;
  title: string;
  sectionId: string | null;
  addedAt: string;
};

export type StudySessionState = {
  version: 1;
  items: StudySessionItem[];
  activeArticleId: string | null;
  updatedAt: string;
};

export type StudySessionParseResult = {
  state: StudySessionState;
  recovered: boolean;
  droppedCount: number;
  truncatedCount: number;
};

export type StudySessionLoadResult = StudySessionParseResult & {
  storageAvailable: boolean;
};

export type StudySessionAddOutcome = "added" | "already-present" | "full" | "invalid";

export type StudySessionMutation = {
  state: StudySessionState;
  outcome: StudySessionAddOutcome;
};

export type StudySessionPosition = {
  index: number;
  total: number;
  previous: StudySessionItem | null;
  current: StudySessionItem;
  next: StudySessionItem | null;
};

type PersistedStudySessionItem = {
  article_id: string;
  title: string;
  section_id: string | null;
  added_at: string;
};

type PersistedStudySession = {
  version: 1;
  items: PersistedStudySessionItem[];
  active_article_id: string | null;
  updated_at: string;
};

const EPOCH = new Date(0).toISOString();
const SAFE_ARTICLE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const SAFE_SECTION_ID = /^[\p{Letter}\p{Number}](?:[\p{Letter}\p{Number}-]{0,199})$/u;

export function createEmptyStudySession(updatedAt = EPOCH): StudySessionState {
  return {
    version: 1,
    items: [],
    activeArticleId: null,
    updatedAt: normalizeTimestamp(updatedAt),
  };
}

export function parseStudySessionStore(raw: string | null): StudySessionParseResult {
  if (!raw) {
    return cleanParseResult(createEmptyStudySession());
  }

  let value: unknown;
  try {
    value = JSON.parse(raw) as unknown;
  } catch {
    return { ...cleanParseResult(createEmptyStudySession()), recovered: true };
  }
  if (!value || typeof value !== "object") {
    return { ...cleanParseResult(createEmptyStudySession()), recovered: true };
  }

  const store = value as Record<string, unknown>;
  if (store.version !== 1 || !Array.isArray(store.items)) {
    return { ...cleanParseResult(createEmptyStudySession()), recovered: true };
  }

  const unique = new Map<string, StudySessionItem>();
  let droppedCount = 0;
  let normalizedItemCount = 0;
  for (const candidate of store.items) {
    const item = normalizePersistedItem(candidate);
    if (!item || unique.has(item.articleId)) {
      droppedCount += 1;
      continue;
    }
    if (!isCanonicalPersistedItem(candidate, item)) {
      normalizedItemCount += 1;
    }
    unique.set(item.articleId, item);
  }

  const allItems = [...unique.values()];
  const truncatedCount = Math.max(0, allItems.length - STUDY_SESSION_ITEM_LIMIT);
  const items = allItems.slice(0, STUDY_SESSION_ITEM_LIMIT);
  const requestedActive = normalizeArticleId(store.active_article_id);
  const activeArticleId = requestedActive && items.some((item) => item.articleId === requestedActive)
    ? requestedActive
    : items[0]?.articleId ?? null;
  const requestedUpdatedAt = typeof store.updated_at === "string" ? store.updated_at : "";
  const updatedAt = normalizeTimestamp(requestedUpdatedAt);
  const recovered =
    droppedCount > 0 ||
    normalizedItemCount > 0 ||
    truncatedCount > 0 ||
    requestedActive !== activeArticleId ||
    requestedUpdatedAt !== updatedAt;

  return {
    state: { version: 1, items, activeArticleId, updatedAt },
    recovered,
    droppedCount,
    truncatedCount,
  };
}

export function serializeStudySession(state: StudySessionState): string {
  const persisted: PersistedStudySession = {
    version: 1,
    items: state.items.slice(0, STUDY_SESSION_ITEM_LIMIT).map((item) => ({
      article_id: item.articleId,
      title: item.title,
      section_id: item.sectionId,
      added_at: item.addedAt,
    })),
    active_article_id: state.activeArticleId,
    updated_at: state.updatedAt,
  };
  return JSON.stringify(persisted);
}

export function addStudySessionItem(
  state: StudySessionState,
  input: { articleId: string; title: string; sectionId?: string | null },
  updatedAt: string,
): StudySessionMutation {
  const item = normalizeInputItem(input, updatedAt);
  if (!item) {
    return { state, outcome: "invalid" };
  }
  if (state.items.some((candidate) => candidate.articleId === item.articleId)) {
    return { state, outcome: "already-present" };
  }
  if (state.items.length >= STUDY_SESSION_ITEM_LIMIT) {
    return { state, outcome: "full" };
  }
  return {
    outcome: "added",
    state: {
      version: 1,
      items: [...state.items, item],
      activeArticleId: state.activeArticleId ?? item.articleId,
      updatedAt: normalizeTimestamp(updatedAt),
    },
  };
}

export function activateStudySessionItem(
  state: StudySessionState,
  articleId: string,
  updatedAt: string,
): StudySessionState {
  if (state.activeArticleId === articleId || !state.items.some((item) => item.articleId === articleId)) {
    return state;
  }
  return { ...state, activeArticleId: articleId, updatedAt: normalizeTimestamp(updatedAt) };
}

export function moveStudySessionItem(
  state: StudySessionState,
  articleId: string,
  direction: -1 | 1,
  updatedAt: string,
): StudySessionState {
  const currentIndex = state.items.findIndex((item) => item.articleId === articleId);
  const nextIndex = currentIndex + direction;
  if (currentIndex < 0 || nextIndex < 0 || nextIndex >= state.items.length) {
    return state;
  }
  const items = [...state.items];
  [items[currentIndex], items[nextIndex]] = [items[nextIndex], items[currentIndex]];
  return { ...state, items, updatedAt: normalizeTimestamp(updatedAt) };
}

export function removeStudySessionItem(
  state: StudySessionState,
  articleId: string,
  updatedAt: string,
): StudySessionState {
  const removedIndex = state.items.findIndex((item) => item.articleId === articleId);
  if (removedIndex < 0) {
    return state;
  }
  const items = state.items.filter((item) => item.articleId !== articleId);
  const activeArticleId = state.activeArticleId === articleId
    ? items[Math.min(removedIndex, items.length - 1)]?.articleId ?? null
    : state.activeArticleId && items.some((item) => item.articleId === state.activeArticleId)
      ? state.activeArticleId
      : items[0]?.articleId ?? null;
  return {
    version: 1,
    items,
    activeArticleId,
    updatedAt: normalizeTimestamp(updatedAt),
  };
}

export function clearStudySession(_state: StudySessionState, updatedAt: string): StudySessionState {
  return createEmptyStudySession(updatedAt);
}

export function getStudySessionPosition(
  state: StudySessionState,
  articleId: string,
): StudySessionPosition | null {
  const index = state.items.findIndex((item) => item.articleId === articleId);
  if (index < 0) {
    return null;
  }
  return {
    index,
    total: state.items.length,
    previous: state.items[index - 1] ?? null,
    current: state.items[index],
    next: state.items[index + 1] ?? null,
  };
}

export function createStudySessionReaderHref(item: StudySessionItem): string {
  return createArticleReturnHref(item.articleId, "/session", item.sectionId);
}

export function loadStudySession(): StudySessionLoadResult {
  if (typeof window === "undefined") {
    return { ...cleanParseResult(createEmptyStudySession()), storageAvailable: false };
  }
  try {
    return {
      ...parseStudySessionStore(window.localStorage.getItem(STUDY_SESSION_STORAGE_KEY)),
      storageAvailable: true,
    };
  } catch {
    return { ...cleanParseResult(createEmptyStudySession()), storageAvailable: false };
  }
}

export function saveStudySession(state: StudySessionState): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  try {
    window.localStorage.setItem(STUDY_SESSION_STORAGE_KEY, serializeStudySession(state));
    window.dispatchEvent(new Event(STUDY_SESSION_CHANGE_EVENT));
    return true;
  } catch {
    return false;
  }
}

function cleanParseResult(state: StudySessionState): StudySessionParseResult {
  return { state, recovered: false, droppedCount: 0, truncatedCount: 0 };
}

function normalizePersistedItem(value: unknown): StudySessionItem | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const record = value as Record<string, unknown>;
  return normalizeInputItem(
    {
      articleId: typeof record.article_id === "string" ? record.article_id : "",
      title: typeof record.title === "string" ? record.title : "",
      sectionId: typeof record.section_id === "string" ? record.section_id : null,
    },
    typeof record.added_at === "string" ? record.added_at : EPOCH,
  );
}

function isCanonicalPersistedItem(value: unknown, item: StudySessionItem): boolean {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return record.article_id === item.articleId
    && record.title === item.title
    && record.section_id === item.sectionId
    && record.added_at === item.addedAt;
}

function normalizeInputItem(
  input: { articleId: string; title: string; sectionId?: string | null },
  addedAt: string,
): StudySessionItem | null {
  const articleId = normalizeArticleId(input.articleId);
  const title = normalizeTitle(input.title);
  if (!articleId || !title || equivalentText(articleId, title)) {
    return null;
  }
  const section = input.sectionId?.trim() ?? "";
  return {
    articleId,
    title,
    sectionId: SAFE_SECTION_ID.test(section) ? section : null,
    addedAt: normalizeTimestamp(addedAt),
  };
}

function normalizeArticleId(value: unknown): string | null {
  const normalized = typeof value === "string" ? value.trim() : "";
  return SAFE_ARTICLE_ID.test(normalized) ? normalized : null;
}

function normalizeTitle(value: string): string | null {
  const normalized = value
    .replace(/[\u0000-\u001f\u007f]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 240);
  return normalized || null;
}

function normalizeTimestamp(value: string): string {
  return Number.isFinite(Date.parse(value)) ? value : EPOCH;
}

function equivalentText(left: string, right: string): boolean {
  return left.normalize("NFKC").toLocaleLowerCase() === right.normalize("NFKC").toLocaleLowerCase();
}
