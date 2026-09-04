import { fetchArticles, formatMetadata, type ArticleListResponse, type ArticleSummary } from "./articles";
import { toPlainTextPreview } from "./articlePresentation";
import { fetchGraphNodes, type GraphNode, type GraphNodeListResponse } from "./graph";
import { getSafeDisplayText } from "./graphPresentation";
import { createArticleDetailHref, createArticleListHref, type SearchParamInput } from "./learningWorkflow";
import { PRIMARY_NAVIGATION } from "./navigation";
import { fetchReferences, type ReferencePage, type ReferenceRecord } from "./references";

export const GLOBAL_SEARCH_LIMIT = 5;
export const MIN_GLOBAL_SEARCH_LENGTH = 2;
const MAX_GLOBAL_SEARCH_LENGTH = 120;
const MAX_RESULT_TEXT_LENGTH = 180;
const MAX_GRAPH_NODE_ID_LENGTH = 200;

export type GlobalSearchSource = "articles" | "references" | "graph";
export type GlobalSearchResultKind = "workspace" | "article" | "reference" | "graph";

export type GlobalSearchResult = {
  key: string;
  kind: GlobalSearchResultKind;
  title: string;
  description: string;
  href: string;
};

export type GlobalSearchGroup = {
  source: GlobalSearchSource;
  label: string;
  total: number;
  items: GlobalSearchResult[];
};

export type GlobalSearchFailure = {
  source: GlobalSearchSource;
  label: string;
  message: string;
};

export type GlobalSearchResponse = {
  query: string;
  groups: GlobalSearchGroup[];
  failures: GlobalSearchFailure[];
};

export type GlobalSearchProviders = {
  articles: (query: string, limit: number) => Promise<ArticleListResponse>;
  references: (query: string, limit: number) => Promise<ReferencePage>;
  graph: (query: string, limit: number) => Promise<GraphNodeListResponse>;
};

export type GraphSearchState = {
  nodeId: string | null;
  query: string;
};

const SOURCE_LABELS: Record<GlobalSearchSource, string> = {
  articles: "Articles",
  references: "References",
  graph: "Knowledge Graph",
};

const WORKSPACE_DESCRIPTIONS: Record<(typeof PRIMARY_NAVIGATION)[number]["id"], string> = {
  dashboard: "Learning overview and next actions",
  library: "Resume reading and revisit saved Articles",
  session: "Continue a focused multi-Article study queue",
  articles: "Browse and read the Article library",
  references: "Review papers and structured References",
  graph: "Explore concepts, formulas, and relationships",
  tutor: "Explain, derive, quiz, and research",
};

const DEFAULT_PROVIDERS: GlobalSearchProviders = {
  articles: (query, limit) =>
    fetchArticles({ q: query, page: 1, page_size: limit, sort: "relevance" }),
  references: (query, limit) => fetchReferences({ query, page: 1, pageSize: limit }),
  graph: (query, limit) => fetchGraphNodes({ q: query, page: 1, page_size: limit }),
};

export function normalizeGlobalSearchQuery(value: string): string {
  return value
    .replace(/[\u0000-\u001f\u007f]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_GLOBAL_SEARCH_LENGTH);
}

export function getWorkspaceQuickResults(rawQuery: string): GlobalSearchResult[] {
  const query = normalizeGlobalSearchQuery(rawQuery).toLocaleLowerCase();
  return PRIMARY_NAVIGATION.filter((item) => {
    if (!query) {
      return true;
    }
    return `${item.label} ${WORKSPACE_DESCRIPTIONS[item.id]}`.toLocaleLowerCase().includes(query);
  }).map((item) => ({
    key: `workspace:${item.id}`,
    kind: "workspace",
    title: item.label,
    description: WORKSPACE_DESCRIPTIONS[item.id],
    href: item.href,
  }));
}

export async function searchGlobalContent(
  rawQuery: string,
  providers: GlobalSearchProviders = DEFAULT_PROVIDERS,
): Promise<GlobalSearchResponse> {
  const query = normalizeGlobalSearchQuery(rawQuery);
  if (query.length < MIN_GLOBAL_SEARCH_LENGTH) {
    return { query, groups: [], failures: [] };
  }

  const sources: Array<{
    source: GlobalSearchSource;
    request: Promise<ArticleListResponse | ReferencePage | GraphNodeListResponse>;
  }> = [
    { source: "articles", request: providers.articles(query, GLOBAL_SEARCH_LIMIT) },
    { source: "references", request: providers.references(query, GLOBAL_SEARCH_LIMIT) },
    { source: "graph", request: providers.graph(query, GLOBAL_SEARCH_LIMIT) },
  ];
  const settled = await Promise.allSettled(sources.map((entry) => entry.request));
  const groups: GlobalSearchGroup[] = [];
  const failures: GlobalSearchFailure[] = [];

  settled.forEach((result, index) => {
    const source = sources[index].source;
    const label = SOURCE_LABELS[source];
    if (result.status === "rejected") {
      failures.push({ source, label, message: `${label} search is unavailable.` });
      return;
    }

    const group = mapSourceResponse(source, result.value, query);
    if (group.items.length > 0) {
      groups.push(group);
    }
  });

  return { query, groups, failures };
}

export function createGraphSearchHref(nodeId: string, rawQuery = ""): string {
  const params = new URLSearchParams();
  const cleanNodeId = normalizeGraphNodeId(nodeId);
  const query = normalizeGlobalSearchQuery(rawQuery);
  if (cleanNodeId) {
    params.set("node_id", cleanNodeId);
  }
  if (query) {
    params.set("q", query);
  }
  const suffix = params.toString();
  return suffix ? `/graph?${suffix}` : "/graph";
}

export function parseGraphSearchState(input: SearchParamInput): GraphSearchState {
  return {
    nodeId: normalizeGraphNodeId(readParam(input, "node_id")),
    query: normalizeGlobalSearchQuery(readParam(input, "q")),
  };
}

function mapSourceResponse(
  source: GlobalSearchSource,
  response: ArticleListResponse | ReferencePage | GraphNodeListResponse,
  query: string,
): GlobalSearchGroup {
  if (source === "articles") {
    const page = response as ArticleListResponse;
    return {
      source,
      label: SOURCE_LABELS[source],
      total: page.total,
      items: page.items.slice(0, GLOBAL_SEARCH_LIMIT).map((article) => mapArticle(article, query)),
    };
  }
  if (source === "references") {
    const page = response as ReferencePage;
    return {
      source,
      label: SOURCE_LABELS[source],
      total: page.total,
      items: page.items.slice(0, GLOBAL_SEARCH_LIMIT).map(mapReference),
    };
  }
  const page = response as GraphNodeListResponse;
  return {
    source,
    label: SOURCE_LABELS[source],
    total: page.total,
    items: page.items.slice(0, GLOBAL_SEARCH_LIMIT).map((node) => mapGraphNode(node, query)),
  };
}

function mapArticle(article: ArticleSummary, query: string): GlobalSearchResult {
  const listHref = createArticleListHref({ q: query, sort: "relevance", page: 1 });
  const metadata = formatMetadata(article.metadata);
  const metadataSummary =
    metadata === "No metadata" ? "" : boundedDisplayText(metadata, "", 56);
  const preview = boundedDisplayText(
    toPlainTextPreview(article.content_preview, MAX_GLOBAL_SEARCH_LENGTH),
    "Open the Article in Reader.",
    MAX_GLOBAL_SEARCH_LENGTH,
  );
  return {
    key: `article:${article.id}`,
    kind: "article",
    title: boundedDisplayText(article.title, "Untitled Article"),
    description: boundedDisplayText(
      [metadataSummary, preview].filter(Boolean).join(" · "),
      "Open the Article in Reader.",
    ),
    href: createArticleDetailHref(article.id, listHref),
  };
}

function mapReference(reference: ReferenceRecord): GlobalSearchResult {
  const sourceTitle = boundedDisplayText(reference.source_article_title, "Source Article", 112);
  const sourceSection = getReferenceSectionLabel(reference.source_section);
  const sourceList = createArticleListHref({ q: sourceTitle, sort: "relevance", page: 1 });
  return {
    key: `reference:${reference.reference_id}`,
    kind: "reference",
    title: getReferenceTitle(reference),
    description: boundedDisplayText(
      `From ${sourceTitle} · ${sourceSection}`,
      `From ${sourceTitle}`,
    ),
    href: createArticleDetailHref(reference.source_article_id, sourceList),
  };
}

function getReferenceSectionLabel(value: string): string {
  if (!value.trim() || value.trim() === "__article_root__") {
    return "Article root";
  }
  return boundedDisplayText(toPlainTextPreview(value, 48), "Article root", 48);
}

function mapGraphNode(node: GraphNode, query: string): GlobalSearchResult {
  return {
    key: `graph:${node.node_id}`,
    kind: "graph",
    title: boundedDisplayText(getSafeDisplayText(node.label), "Untitled graph node"),
    description: `${formatGraphNodeType(node.node_type)} · Knowledge Graph`,
    href: createGraphSearchHref(node.node_id, query),
  };
}

function getReferenceTitle(reference: ReferenceRecord): string {
  if (reference.doi) {
    return boundedDisplayText(`DOI ${reference.doi}`, "DOI Reference");
  }
  if (reference.arxiv_id) {
    const version = reference.arxiv_version ? `v${reference.arxiv_version}` : "";
    return boundedDisplayText(`arXiv ${reference.arxiv_id}${version}`, "arXiv Reference");
  }
  const labels: Record<ReferenceRecord["reference_type"], string> = {
    doi: "DOI reference",
    arxiv: "arXiv reference",
    http_url: "Web reference",
    relative_or_internal_url: "Related Article link",
    citation_text: "Citation text",
    unsupported: "Unsupported reference",
    malformed: "Malformed reference",
  };
  return labels[reference.reference_type];
}

function formatGraphNodeType(nodeType: GraphNode["node_type"]): string {
  const labels: Record<GraphNode["node_type"], string> = {
    article: "Article",
    section: "Section",
    concept: "Concept",
    formula: "Formula",
    zotero_item: "Paper",
  };
  return labels[nodeType];
}

function boundedDisplayText(
  value: string | null | undefined,
  fallback: string,
  maxLength = MAX_RESULT_TEXT_LENGTH,
): string {
  const clean = normalizeGlobalSearchQuery(value ?? "");
  return (clean || fallback).slice(0, maxLength);
}

export function normalizeGraphNodeId(value: string | null | undefined): string | null {
  const clean = value?.trim() ?? "";
  if (
    !clean ||
    clean.length > MAX_GRAPH_NODE_ID_LENGTH ||
    clean === "." ||
    clean === ".." ||
    /[\u0000-\u001f\u007f/\\?#]/u.test(clean)
  ) {
    return null;
  }
  return clean;
}

function readParam(input: SearchParamInput, key: string): string {
  const value = input instanceof URLSearchParams ? input.get(key) : input[key];
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}
