export type ArticleMetadata = {
  date?: string | null;
  category?: string | null;
  references?: Array<Record<string, string>>;
  images?: string[];
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
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchArticles(query?: string): Promise<ArticleListResponse> {
  const url = new URL("/articles", API_BASE_URL);
  if (query?.trim()) {
    url.searchParams.set("q", query.trim());
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
