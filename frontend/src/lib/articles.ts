export type ArticleMetadata = {
  date?: string | null;
  category?: string | null;
  references?: Array<string | Record<string, unknown>>;
  images?: Array<string | Record<string, unknown>>;
};

export type ArticleListSort = "date_desc" | "archive_desc" | "title_asc" | "relevance";

export type ArticleListRequest = {
  q?: string;
  page?: number;
  page_size?: number;
  category?: string;
  sort?: ArticleListSort;
};

export type ArticleSummary = {
  id: string;
  title: string;
  url: string;
  metadata: ArticleMetadata;
  content_preview: string;
};

export type ArticleDetail = {
  id: string;
  title: string;
  url: string;
  content: string;
  metadata: ArticleMetadata;
};

export type ArticleListResponse = {
  items: ArticleSummary[];
  total: number;
  query: string | null;
  category: string | null;
  sort: ArticleListSort;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchArticles(queryOrOptions?: string | ArticleListRequest): Promise<ArticleListResponse> {
  const url = new URL("/articles", API_BASE_URL);

  const options: ArticleListRequest = typeof queryOrOptions === "string" ? { q: queryOrOptions } : queryOrOptions ?? {};
  if (options.q?.trim()) {
    url.searchParams.set("q", options.q.trim());
  }
  if (Number.isFinite(options.page) && (options.page as number) > 0) {
    url.searchParams.set("page", String(options.page));
  }
  if (Number.isFinite(options.page_size) && (options.page_size as number) > 0) {
    url.searchParams.set("page_size", String(options.page_size));
  }
  if (options.category?.trim()) {
    url.searchParams.set("category", options.category.trim());
  }
  if (options.sort) {
    url.searchParams.set("sort", options.sort);
  }

  const response = await fetch(url.toString(), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load articles: ${response.status}`);
  }
  return response.json() as Promise<ArticleListResponse>;
}

export async function fetchArticle(articleId: string): Promise<ArticleDetail> {
  const response = await fetch(new URL(`/articles/${articleId}`, API_BASE_URL).toString(), {
    cache: "no-store",
  });
  if (response.status === 404) {
    throw new Error("Article not found");
  }
  if (!response.ok) {
    throw new Error(`Failed to load article: ${response.status}`);
  }
  return response.json() as Promise<ArticleDetail>;
}

export function formatMetadata(metadata: ArticleMetadata): string {
  const parts = [metadata.date, metadata.category].filter(Boolean);
  return parts.length ? parts.join(" · ") : "No metadata";
}
