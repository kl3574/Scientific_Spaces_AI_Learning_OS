import type { GraphNode } from "./graph";

export type ConceptSource = {
  articleId: string | null;
  articleTitle: string | null;
  articleUrl: string | null;
  sourceType: string | null;
  sectionTitle: string | null;
  sourceContext: string | null;
  evidence: string | null;
  chunkIndex: number | null;
};

export type ConceptProvenance = {
  sourceCount: number;
  sources: ConceptSource[];
  truncated: boolean;
  omittedCount: number;
};

const COLLAPSED_PROVENANCE_SOURCE_COUNT = 3;

export function getConceptProvenance(node: GraphNode): ConceptProvenance | null {
  if (node.node_type !== "concept") {
    return null;
  }

  const rawSources = Array.isArray(node.metadata.sources) ? node.metadata.sources : [];
  const sources = rawSources.filter(isRecord).map((source) => ({
    articleId: getSafeArticleId(source.article_id),
    articleTitle: getSafeDisplayText(source.article_title),
    articleUrl: getSafeExternalUrl(source.article_url),
    sourceType: getSafeDisplayText(source.source_type),
    sectionTitle: getSafeDisplayText(source.section_title),
    sourceContext: getSafeDisplayText(source.source_context),
    evidence: getSafeDisplayText(source.evidence),
    chunkIndex: getNonNegativeInteger(source.chunk_index),
  }));
  const recordedCount = getNonNegativeInteger(node.metadata.source_count);
  const sourceCount = Math.max(recordedCount ?? sources.length, sources.length);
  const omittedCount = Math.max(sourceCount - sources.length, 0);

  return {
    sourceCount,
    sources,
    truncated: node.metadata.truncated === true || omittedCount > 0,
    omittedCount,
  };
}

export function getProvenanceSourceView(
  sources: readonly ConceptSource[],
  expanded: boolean,
): { sources: ConceptSource[]; hiddenReturnedCount: number } {
  const visibleSources = expanded
    ? [...sources]
    : sources.slice(0, COLLAPSED_PROVENANCE_SOURCE_COUNT);
  return {
    sources: visibleSources,
    hiddenReturnedCount: Math.max(sources.length - visibleSources.length, 0),
  };
}

export function getSafeArticleId(value: unknown): string | null {
  const text = getSafeDisplayText(value);
  if (!text || text === "." || text === ".." || text.includes("/") || text.includes("\\")) {
    return null;
  }
  return text;
}

export function getSafeDisplayText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const text = value.trim();
  if (!text || containsLocalPath(text)) {
    return null;
  }
  return text;
}

export function getSafeExternalUrl(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const candidate = value.trim();
  if (!candidate) {
    return null;
  }
  try {
    const url = new URL(candidate);
    if ((url.protocol !== "http:" && url.protocol !== "https:") || url.username || url.password) {
      return null;
    }
    return candidate;
  } catch {
    return null;
  }
}

function containsLocalPath(value: string): boolean {
  return (
    /^file:/i.test(value) ||
    /(?:^|[\s"'(`=])\/(?!\/)\S+/.test(value) ||
    /^\/?(?:home|users|root|tmp|var|etc|opt|mnt|srv|data)\//i.test(value) ||
    /(?:^|[\s"'(])~\//.test(value) ||
    /(?:^|[\s"'(])\/(?:home|users|root|tmp|var|etc|opt|mnt|srv|data)\//i.test(value) ||
    /(?:^|[\s"'(])[a-z]:[\\/]/i.test(value) ||
    /(?:^|[\s"'(])\\\\/.test(value)
  );
}

function getNonNegativeInteger(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? Math.floor(value) : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
