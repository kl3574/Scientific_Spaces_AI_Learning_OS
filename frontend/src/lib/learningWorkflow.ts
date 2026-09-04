import type { ArticleListSort } from "./articles";

export type { ArticleListSort } from "./articles";

export type ArticleListState = {
  q: string;
  sort: ArticleListSort;
  page: number;
};

export type LearningWorkflowContext = {
  articleId: string;
  articleTitle: string | null;
  returnTo: string;
  nodeId: string | null;
};

export type SearchParamInput = URLSearchParams | Record<string, string | string[] | undefined>;

const DEFAULT_LIST_STATE: ArticleListState = { q: "", sort: "date_desc", page: 1 };
const VALID_SORTS = new Set<ArticleListSort>(["date_desc", "archive_desc", "title_asc", "relevance"]);
const LOCAL_ORIGIN = "http://scientific-spaces.local";
const MAX_QUERY_LENGTH = 200;
const MAX_TITLE_LENGTH = 240;
const MAX_PATH_LENGTH = 1200;
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const SAFE_SECTION = /^[^\u0000-\u001f\u007f?#]{1,240}$/;
const LIBRARY_VIEWS = new Set(["all", "continue", "bookmarked", "recent"]);
const LIBRARY_SORTS = new Set(["recent", "title", "progress"]);

export function parseArticleListState(input: SearchParamInput): ArticleListState {
  const q = normalizeText(readParam(input, "q"), MAX_QUERY_LENGTH);
  const rawSort = readParam(input, "sort");
  const sort = VALID_SORTS.has(rawSort as ArticleListSort) ? (rawSort as ArticleListSort) : DEFAULT_LIST_STATE.sort;
  const rawPage = Number.parseInt(readParam(input, "page"), 10);
  const page = Number.isSafeInteger(rawPage) && rawPage > 0 ? Math.min(rawPage, 100_000) : DEFAULT_LIST_STATE.page;
  return { q, sort, page };
}

export function createArticleListHref(state: ArticleListState): string {
  const normalized = parseArticleListState({
    q: state.q,
    sort: state.sort,
    page: String(state.page),
  });
  const params = new URLSearchParams();
  if (normalized.q) {
    params.set("q", normalized.q);
  }
  if (normalized.sort !== DEFAULT_LIST_STATE.sort) {
    params.set("sort", normalized.sort);
  }
  if (normalized.page > 1) {
    params.set("page", String(normalized.page));
  }
  const query = params.toString();
  return query ? `/articles?${query}` : "/articles";
}

export function sanitizeArticleListReturnPath(value: string | null | undefined): string {
  if (!value || value.length > MAX_PATH_LENGTH) {
    return "/articles";
  }
  const parsed = parseLocalUrl(value);
  if (!parsed || parsed.pathname !== "/articles" || parsed.hash) {
    return "/articles";
  }
  return createArticleListHref(parseArticleListState(parsed.searchParams));
}

export function sanitizeArticleEntryReturnPath(value: string | null | undefined): string {
  if (!value || value.length > MAX_PATH_LENGTH) {
    return "/articles";
  }
  const parsed = parseLocalUrl(value);
  if (!parsed || parsed.hash) {
    return "/articles";
  }
  if (parsed.pathname === "/articles") {
    return createArticleListHref(parseArticleListState(parsed.searchParams));
  }
  if (parsed.pathname === "/library") {
    return createLibraryReturnPath(parsed.searchParams);
  }
  if (parsed.pathname === "/session") {
    return "/session";
  }
  if (parsed.pathname === "/graph") {
    return createGraphConceptReturnPath(parsed.searchParams.get("node_id"));
  }
  return "/articles";
}

export function createArticleDetailHref(articleId: string, listReturnTo = "/articles"): string {
  const cleanArticleId = normalizeId(articleId);
  if (!cleanArticleId) {
    return "/articles";
  }
  const safeListPath = sanitizeArticleEntryReturnPath(listReturnTo);
  const params = new URLSearchParams();
  if (safeListPath !== "/articles") {
    params.set("from", safeListPath);
  }
  const query = params.toString();
  return `/articles/${encodeURIComponent(cleanArticleId)}${query ? `?${query}` : ""}`;
}

export function createArticleReturnHref(
  articleId: string,
  listReturnTo = "/articles",
  sectionId?: string | null,
): string {
  const base = createArticleDetailHref(articleId, listReturnTo);
  if (base === "/articles") {
    return base;
  }
  const cleanSection = normalizeSection(sectionId);
  return cleanSection ? `${base}#${encodeURIComponent(cleanSection)}` : base;
}

export function createLearningToolHref(
  tool: "tutor" | "graph",
  context: {
    articleId: string;
    articleTitle?: string | null;
    listReturnTo?: string;
    sectionId?: string | null;
  },
): string {
  const articleId = normalizeId(context.articleId);
  if (!articleId) {
    return `/${tool}`;
  }
  const params = new URLSearchParams();
  params.set("article_id", articleId);
  const title = normalizeText(context.articleTitle ?? "", MAX_TITLE_LENGTH);
  if (title) {
    params.set("article_title", title);
  }
  params.set(
    "return_to",
    createArticleReturnHref(articleId, context.listReturnTo, context.sectionId),
  );
  if (tool === "graph") {
    params.set("node_id", `article:${articleId}`);
  }
  return `/${tool}?${params.toString()}`;
}

export function parseLearningWorkflowContext(input: SearchParamInput): LearningWorkflowContext | null {
  const articleId = normalizeId(readParam(input, "article_id"));
  if (!articleId) {
    return null;
  }
  const articleTitle = normalizeText(readParam(input, "article_title"), MAX_TITLE_LENGTH) || null;
  const returnTo = sanitizeArticleReturnPath(readParam(input, "return_to"), articleId);
  const nodeId = normalizeId(readParam(input, "node_id"));
  return {
    articleId,
    articleTitle,
    returnTo,
    nodeId: nodeId === `article:${articleId}` ? nodeId : null,
  };
}

function sanitizeArticleReturnPath(value: string, articleId: string): string {
  const fallback = createArticleReturnHref(articleId);
  if (!value || value.length > MAX_PATH_LENGTH) {
    return fallback;
  }
  const parsed = parseLocalUrl(value);
  if (!parsed) {
    return fallback;
  }
  const match = parsed.pathname.match(/^\/articles\/([^/]+)$/);
  if (!match) {
    return fallback;
  }
  let pathArticleId: string;
  try {
    pathArticleId = decodeURIComponent(match[1]);
  } catch {
    return fallback;
  }
  if (pathArticleId !== articleId) {
    return fallback;
  }
  const listReturnTo = sanitizeArticleEntryReturnPath(parsed.searchParams.get("from"));
  const section = normalizeSection(parsed.hash ? decodeHash(parsed.hash) : null);
  return createArticleReturnHref(articleId, listReturnTo, section);
}

function parseLocalUrl(value: string): URL | null {
  try {
    const parsed = new URL(value, LOCAL_ORIGIN);
    return parsed.origin === LOCAL_ORIGIN ? parsed : null;
  } catch {
    return null;
  }
}

function readParam(input: SearchParamInput, key: string): string {
  const value = input instanceof URLSearchParams ? input.get(key) : input[key];
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function normalizeText(value: string, maxLength: number): string {
  return value.replace(/[\u0000-\u001f\u007f]+/g, " ").replace(/\s+/g, " ").trim().slice(0, maxLength);
}

function normalizeId(value: string | null | undefined): string | null {
  const clean = value?.trim() ?? "";
  return SAFE_ID.test(clean) ? clean : null;
}

function normalizeSection(value: string | null | undefined): string | null {
  const clean = value?.trim() ?? "";
  return SAFE_SECTION.test(clean) ? clean : null;
}

function decodeHash(hash: string): string {
  try {
    return decodeURIComponent(hash.replace(/^#/, ""));
  } catch {
    return "";
  }
}

function createLibraryReturnPath(input: URLSearchParams): string {
  const params = new URLSearchParams();
  const query = normalizeText(input.get("q") ?? "", 120);
  const view = input.get("view") ?? "";
  const sort = input.get("sort") ?? "";
  if (query) {
    params.set("q", query);
  }
  if (LIBRARY_VIEWS.has(view) && view !== "all") {
    params.set("view", view);
  }
  if (LIBRARY_SORTS.has(sort) && sort !== "recent") {
    params.set("sort", sort);
  }
  const suffix = params.toString();
  return suffix ? `/library?${suffix}` : "/library";
}

function createGraphConceptReturnPath(value: string | null): string {
  const nodeId = value?.trim() ?? "";
  if (
    !nodeId.startsWith("concept:")
    || nodeId.length === "concept:".length
    || nodeId.length > 200
    || /[\u0000-\u001f\u007f/\\?#]/u.test(nodeId)
  ) {
    return "/articles";
  }
  return `/graph?${new URLSearchParams({ node_id: nodeId }).toString()}`;
}
