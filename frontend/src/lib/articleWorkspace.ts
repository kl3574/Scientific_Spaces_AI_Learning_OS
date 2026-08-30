export type ArticleOutlineItem = {
  id: string;
  label: string;
  level: 2 | 3 | 4;
  line: number;
};

export type ReaderTextSize = "compact" | "comfortable" | "large";
export type ReaderWidth = "focused" | "wide";

export type ReaderPreferences = {
  textSize: ReaderTextSize;
  width: ReaderWidth;
};

export type ReaderProgressState = {
  article_id: string;
  section_id: string | null;
  section_title: string | null;
  progress: number;
  updated_at: string;
};

type ReaderProgressStore = {
  version: 1;
  items: ReaderProgressState[];
};

const READER_PROGRESS_STORAGE_KEY = "scientific-spaces-reader-progress-v1";
const READER_PREFERENCES_STORAGE_KEY = "scientific-spaces-reader-preferences-v1";
const MAX_PROGRESS_ITEMS = 50;

export const DEFAULT_READER_PREFERENCES: ReaderPreferences = {
  textSize: "comfortable",
  width: "focused",
};

export function prepareArticleMarkdown(content: string): string {
  return content
    .split(/(```[\s\S]*?```|~~~[\s\S]*?~~~)/g)
    .map((segment, index) => {
      if (index % 2 === 1) {
        return segment;
      }
      const normalizedCommands = segment
        .replace(
          /(\\newcommand\{([A-Za-z][A-Za-z0-9]*)\}[^\n$]*?\\\2)\$\1\$/g,
          (_match, formula: string) => `$${normalizeNewcommand(formula)}$`,
        )
        .replace(/\\newcommand\{([A-Za-z][A-Za-z0-9]*)\}/g, (_match, name: string) => `\\newcommand{\\${name}}`);

      const normalizedDisplayMath = normalizedCommands.replace(
        /\$\$([\s\S]*?)\$\$/g,
        (_match, formula: string) => `\n\n$$\n${formula.trim()}\n$$\n\n`,
      );

      return normalizedDisplayMath
        .replace(/(?<!\\)\\\[/g, () => "$$")
        .replace(/(?<!\\)\\\]/g, () => "$$")
        .replace(/(?<!\\)\\\(/g, () => "$")
        .replace(/(?<!\\)\\\)/g, () => "$")
        .replace(/^(#{2,4}\s+.*?)[ \t]+\[#\]\(#[^)]+\)[ \t]*$/gm, "$1")
        .replace(/(\*\*[^*\n]+?\*\*)(?=[\p{Letter}\p{Number}])/gu, "$1 ");
    })
    .join("");
}

export function extractArticleOutline(markdown: string): ArticleOutlineItem[] {
  const outline: ArticleOutlineItem[] = [];
  const slugCounts = new Map<string, number>();
  const usedIds = new Set<string>();
  let fence: { marker: "`" | "~"; length: number } | null = null;

  markdown.split("\n").forEach((line, index) => {
    const fenceMatch = line.match(/^\s*(`{3,}|~{3,})/);
    if (fenceMatch) {
      const marker = fenceMatch[1][0] as "`" | "~";
      if (!fence) {
        fence = { marker, length: fenceMatch[1].length };
      } else if (fence.marker === marker && fenceMatch[1].length >= fence.length) {
        fence = null;
      }
      return;
    }
    if (fence) {
      return;
    }

    const heading = line.match(/^ {0,3}(#{2,4})[ \t]+(.+?)[ \t]*#*[ \t]*$/);
    if (!heading) {
      return;
    }
    const label = cleanHeadingLabel(heading[2]);
    if (!label) {
      return;
    }
    const baseSlug = slugifyHeading(label) || `section-${index + 1}`;
    let occurrence = (slugCounts.get(baseSlug) ?? 0) + 1;
    let id = occurrence === 1 ? baseSlug : `${baseSlug}-${occurrence}`;
    while (usedIds.has(id)) {
      occurrence += 1;
      id = `${baseSlug}-${occurrence}`;
    }
    slugCounts.set(baseSlug, occurrence);
    usedIds.add(id);
    outline.push({
      id,
      label,
      level: heading[1].length as 2 | 3 | 4,
      line: index + 1,
    });
  });

  return outline;
}

export function clampReadingProgress(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }
  return Math.min(100, Math.max(0, Math.round(value)));
}

export function updateLastMeaningfulPosition(
  previous: ReaderProgressState,
  visibleSection: ArticleOutlineItem | null,
  progress: number,
  updatedAt: string,
): ReaderProgressState {
  return {
    article_id: previous.article_id,
    section_id: visibleSection?.id ?? previous.section_id,
    section_title: visibleSection?.label ?? previous.section_title,
    progress: clampReadingProgress(progress),
    updated_at: updatedAt,
  };
}

export function loadReaderProgress(articleId: string): ReaderProgressState | null {
  return loadReaderProgressItems().find((item) => item.article_id === articleId) ?? null;
}

export function loadReaderProgressItems(): ReaderProgressState[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    return parseReaderProgressStore(window.localStorage.getItem(READER_PROGRESS_STORAGE_KEY));
  } catch {
    return [];
  }
}

export function saveReaderProgress(state: ReaderProgressState): ReaderProgressState {
  const normalized = normalizeReaderProgressState(state);
  if (typeof window === "undefined") {
    return normalized;
  }
  try {
    const next = [
      normalized,
      ...loadReaderProgressItems().filter((item) => item.article_id !== normalized.article_id),
    ]
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
      .slice(0, MAX_PROGRESS_ITEMS);
    const store: ReaderProgressStore = { version: 1, items: next };
    window.localStorage.setItem(READER_PROGRESS_STORAGE_KEY, JSON.stringify(store));
  } catch {
    // Reading remains available when browser storage is unavailable.
  }
  return normalized;
}

export function parseReaderProgressStore(raw: string | null): ReaderProgressState[] {
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return [];
    }
    const store = parsed as Record<string, unknown>;
    if (store.version !== 1 || !Array.isArray(store.items)) {
      return [];
    }
    return store.items
      .filter(isReaderProgressState)
      .map(normalizeReaderProgressState)
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
      .slice(0, MAX_PROGRESS_ITEMS);
  } catch {
    return [];
  }
}

export function loadReaderPreferences(): ReaderPreferences {
  if (typeof window === "undefined") {
    return DEFAULT_READER_PREFERENCES;
  }
  try {
    return parseReaderPreferences(window.localStorage.getItem(READER_PREFERENCES_STORAGE_KEY));
  } catch {
    return DEFAULT_READER_PREFERENCES;
  }
}

export function saveReaderPreferences(preferences: ReaderPreferences): ReaderPreferences {
  const normalized = normalizeReaderPreferences(preferences);
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(READER_PREFERENCES_STORAGE_KEY, JSON.stringify(normalized));
    } catch {
      // Controls still work for the current page when browser storage is unavailable.
    }
  }
  return normalized;
}

export function parseReaderPreferences(raw: string | null): ReaderPreferences {
  if (!raw) {
    return DEFAULT_READER_PREFERENCES;
  }
  try {
    return normalizeReaderPreferences(JSON.parse(raw) as unknown);
  } catch {
    return DEFAULT_READER_PREFERENCES;
  }
}

export function createResumeHref(articleId: string, state: ReaderProgressState | null): string {
  const base = `/articles/${encodeURIComponent(articleId)}`;
  return state?.section_id && isSafeSectionId(state.section_id)
    ? `${base}#${encodeURIComponent(state.section_id)}`
    : base;
}

function cleanHeadingLabel(value: string): string {
  return value
    .replace(/[ \t]+\[#\]\(#[^)]+\)[ \t]*$/, "")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/<[^>]+>/g, "")
    .replace(/[~*_]/g, "")
    .replace(/\\([#`])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

function slugifyHeading(value: string): string {
  return value
    .normalize("NFKC")
    .toLocaleLowerCase("en-US")
    .replace(/[’']/g, "")
    .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
}

function normalizeNewcommand(value: string): string {
  return value.replace(/\\newcommand\{([A-Za-z][A-Za-z0-9]*)\}/g, (_match, name: string) => `\\newcommand{\\${name}}`);
}

function normalizeReaderProgressState(state: ReaderProgressState): ReaderProgressState {
  return {
    article_id: state.article_id,
    section_id: state.section_id && isSafeSectionId(state.section_id) ? state.section_id : null,
    section_title: state.section_title?.trim() || null,
    progress: clampReadingProgress(state.progress),
    updated_at: isValidDate(state.updated_at) ? state.updated_at : new Date(0).toISOString(),
  };
}

function isReaderProgressState(value: unknown): value is ReaderProgressState {
  if (!value || typeof value !== "object") {
    return false;
  }
  const item = value as Record<string, unknown>;
  return (
    typeof item.article_id === "string" &&
    (item.section_id === null || typeof item.section_id === "string") &&
    (item.section_title === null || typeof item.section_title === "string") &&
    typeof item.progress === "number" &&
    typeof item.updated_at === "string"
  );
}

function normalizeReaderPreferences(value: unknown): ReaderPreferences {
  if (!value || typeof value !== "object") {
    return DEFAULT_READER_PREFERENCES;
  }
  const preferences = value as Record<string, unknown>;
  return {
    textSize: isReaderTextSize(preferences.textSize) ? preferences.textSize : DEFAULT_READER_PREFERENCES.textSize,
    width: isReaderWidth(preferences.width) ? preferences.width : DEFAULT_READER_PREFERENCES.width,
  };
}

function isReaderTextSize(value: unknown): value is ReaderTextSize {
  return value === "compact" || value === "comfortable" || value === "large";
}

function isReaderWidth(value: unknown): value is ReaderWidth {
  return value === "focused" || value === "wide";
}

function isSafeSectionId(value: string): boolean {
  return /^[\p{Letter}\p{Number}](?:[\p{Letter}\p{Number}-]{0,199})$/u.test(value);
}

function isValidDate(value: string): boolean {
  return Number.isFinite(Date.parse(value));
}
