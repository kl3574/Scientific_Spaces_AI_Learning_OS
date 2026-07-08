import type { ArticleDetail } from "./articles";

export type ReadingHistoryItem = {
  id: string;
  title: string;
  url: string;
  last_read_at: string;
};

const STORAGE_KEY = "scientific-spaces-reading-history-v1";
const MAX_HISTORY_ITEMS = 8;

export function loadReadingHistory(): ReadingHistoryItem[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as ReadingHistoryItem[];
    return Array.isArray(parsed) ? parsed.filter(isHistoryItem) : [];
  } catch {
    return [];
  }
}

export function recordReading(article: ArticleDetail): ReadingHistoryItem[] {
  if (typeof window === "undefined") {
    return [];
  }

  const item: ReadingHistoryItem = {
    id: article.id,
    title: article.title,
    url: article.url,
    last_read_at: new Date().toISOString(),
  };
  const next = [item, ...loadReadingHistory().filter((entry) => entry.id !== article.id)].slice(
    0,
    MAX_HISTORY_ITEMS,
  );
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

function isHistoryItem(value: unknown): value is ReadingHistoryItem {
  if (!value || typeof value !== "object") {
    return false;
  }
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "string" &&
    typeof item.title === "string" &&
    typeof item.url === "string" &&
    typeof item.last_read_at === "string"
  );
}
