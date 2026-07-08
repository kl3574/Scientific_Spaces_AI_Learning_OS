export type ZoteroStatus = {
  provider: string;
  available: boolean;
  read_only: boolean;
  base_url?: string | null;
  version?: string | null;
  error?: string | null;
};

export type ZoteroItem = {
  item_key: string;
  bibtex_key: string;
  title: string;
  creators: string[];
  year: string | null;
  item_type: string;
  publication_title: string | null;
  doi: string | null;
  url: string | null;
  abstract_note: string | null;
  tags: string[];
  collections: string[];
  updated_at: string | null;
};

export type ZoteroItemSearchResponse = {
  items: ZoteroItem[];
  total: number;
  query: string;
};

export type ZoteroRelationType = "related" | "cites" | "background";

export type ZoteroArticleLink = {
  article_id: string;
  zotero_item_key: string;
  relation_type: ZoteroRelationType;
  created_at: string;
  note: string | null;
};

export type ZoteroArticleLinkItem = {
  link: ZoteroArticleLink;
  item: ZoteroItem | null;
};

export type ZoteroArticleLinksResponse = {
  items: ZoteroArticleLinkItem[];
  total: number;
};

export type BibtexExportResponse = {
  bibtex: string;
  item_count: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchZoteroStatus(): Promise<ZoteroStatus> {
  return requestJson<ZoteroStatus>("/zotero/status");
}

export async function searchZoteroItems(query: string, limit = 20): Promise<ZoteroItemSearchResponse> {
  const url = new URL("/zotero/items", API_BASE_URL);
  url.searchParams.set("q", query.trim());
  url.searchParams.set("limit", String(limit));
  return requestJsonUrl<ZoteroItemSearchResponse>(url);
}

export async function fetchArticleZoteroLinks(articleId: string): Promise<ZoteroArticleLinksResponse> {
  return requestJson<ZoteroArticleLinksResponse>(`/zotero/links/${articleId}`);
}

export async function createArticleZoteroLink(
  articleId: string,
  itemKey: string,
  relationType: ZoteroRelationType,
  note: string | null,
): Promise<ZoteroArticleLink> {
  return requestJson<ZoteroArticleLink>(`/zotero/links/${articleId}`, {
    body: JSON.stringify({ item_key: itemKey, relation_type: relationType, note }),
    method: "POST",
  });
}

export async function deleteArticleZoteroLink(articleId: string, itemKey: string): Promise<void> {
  const response = await fetch(new URL(`/zotero/links/${articleId}/${itemKey}`, API_BASE_URL).toString(), {
    cache: "no-store",
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Zotero request failed: ${response.status}`);
  }
}

export async function exportZoteroBibtex(itemKeys: string[]): Promise<BibtexExportResponse> {
  return requestJson<BibtexExportResponse>("/zotero/export/bibtex", {
    body: JSON.stringify({ item_keys: itemKeys }),
    method: "POST",
  });
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  return requestJsonUrl<T>(new URL(path, API_BASE_URL), init);
}

async function requestJsonUrl<T>(url: URL, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url.toString(), {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Zotero request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
