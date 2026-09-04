import type { GraphNode } from "./graph";
import { getConceptProvenance, getSafeDisplayText } from "./graphPresentation";

export const CONCEPT_TITLE_LIMIT = 160;
const SAFE_ARTICLE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;

export type ConceptStudyArticle = {
  articleId: string;
  title: string;
  sectionTitle: string | null;
};

export type ConceptStudySet = {
  conceptNodeId: string;
  conceptTitle: string;
  sourceRecordCount: number;
  returnedRecordCount: number;
  omittedRecordCount: number;
  duplicateRecordCount: number;
  invalidRecordCount: number;
  truncated: boolean;
  articles: ConceptStudyArticle[];
  primaryArticle: ConceptStudyArticle | null;
};

export function createConceptStudySet(node: GraphNode): ConceptStudySet | null {
  if (node.node_type !== "concept") {
    return null;
  }
  const conceptNodeId = normalizeConceptNodeId(node.node_id);
  const conceptTitle = normalizeDisplayText(node.label, CONCEPT_TITLE_LIMIT);
  if (!conceptNodeId || !conceptTitle) {
    return null;
  }

  const provenance = getConceptProvenance(node);
  if (!provenance) {
    return null;
  }

  const articles: ConceptStudyArticle[] = [];
  const seenArticleIds = new Set<string>();
  let duplicateRecordCount = 0;
  let invalidRecordCount = 0;

  for (const source of provenance.sources) {
    const articleId = normalizeArticleId(source.articleId);
    if (articleId && seenArticleIds.has(articleId)) {
      duplicateRecordCount += 1;
      continue;
    }
    const title = normalizeDisplayText(source.articleTitle, 240);
    if (!articleId || !title || equivalentText(articleId, title)) {
      invalidRecordCount += 1;
      continue;
    }
    seenArticleIds.add(articleId);
    articles.push({
      articleId,
      title,
      sectionTitle: normalizeDisplayText(source.sectionTitle, 240),
    });
  }

  return {
    conceptNodeId,
    conceptTitle,
    sourceRecordCount: provenance.sourceCount,
    returnedRecordCount: provenance.sources.length,
    omittedRecordCount: provenance.omittedCount,
    duplicateRecordCount,
    invalidRecordCount,
    truncated: provenance.truncated,
    articles,
    primaryArticle: articles[0] ?? null,
  };
}

function normalizeArticleId(value: unknown): string | null {
  const clean = typeof value === "string" ? value.trim() : "";
  return SAFE_ARTICLE_ID.test(clean) ? clean : null;
}

export function normalizeConceptNodeId(value: unknown): string | null {
  const clean = typeof value === "string" ? value.trim() : "";
  if (
    !clean.startsWith("concept:")
    || clean.length > 200
    || clean.length === "concept:".length
    || /[\u0000-\u001f\u007f/\\?#]/u.test(clean)
  ) {
    return null;
  }
  return clean;
}

function normalizeDisplayText(value: unknown, limit: number): string | null {
  const safe = getSafeDisplayText(value);
  if (!safe) {
    return null;
  }
  const clean = safe.replace(/[\u0000-\u001f\u007f]+/g, " ").replace(/\s+/g, " ").trim();
  return clean ? clean.slice(0, limit) : null;
}

function equivalentText(left: string, right: string): boolean {
  return left.trim().toLocaleLowerCase("zh-CN") === right.trim().toLocaleLowerCase("zh-CN");
}
