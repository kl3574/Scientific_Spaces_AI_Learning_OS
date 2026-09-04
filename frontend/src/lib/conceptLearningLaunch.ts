import type { ConceptStudySet } from "./conceptStudySet";
import { normalizeConceptNodeId } from "./conceptStudySet";
import { getSafeDisplayText } from "./graphPresentation";

export type ConceptTutorMode = "explain" | "quiz";
export type ConceptTutorDisplayMode = "explain" | "derive" | "qa" | "quiz" | "research";

export type ConceptTutorLaunch = {
  conceptNodeId: string;
  conceptTitle: string;
  mode: ConceptTutorMode;
  prompt: string;
  returnTo: string;
  primaryArticle: { articleId: string; title: string } | null;
};

type SearchParamInput = URLSearchParams | Record<string, string | string[] | undefined>;

const SAFE_ARTICLE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const TITLE_LIMIT = 160;
const ARTICLE_TITLE_LIMIT = 240;

export function createConceptTutorHref(
  studySet: ConceptStudySet,
  mode: ConceptTutorMode,
): string {
  const params = new URLSearchParams();
  params.set("entry", "concept");
  params.set("node_id", studySet.conceptNodeId);
  params.set("concept_title", studySet.conceptTitle);
  params.set("mode", mode);
  params.set("return_to", createConceptGraphHref(studySet.conceptNodeId));
  if (studySet.primaryArticle) {
    params.set("source_article_id", studySet.primaryArticle.articleId);
    params.set("source_article_title", studySet.primaryArticle.title);
  }
  return `/tutor?${params.toString()}`;
}

export function parseConceptTutorLaunch(input: SearchParamInput): ConceptTutorLaunch | null {
  if (readParam(input, "entry") !== "concept") {
    return null;
  }
  const conceptNodeId = normalizeConceptNodeId(readParam(input, "node_id"));
  const conceptTitle = normalizeDisplayText(readParam(input, "concept_title"), TITLE_LIMIT);
  const mode = readParam(input, "mode");
  if (!conceptNodeId || !conceptTitle || (mode !== "explain" && mode !== "quiz")) {
    return null;
  }

  const articleId = normalizeArticleId(readParam(input, "source_article_id"));
  const articleTitle = normalizeDisplayText(readParam(input, "source_article_title"), ARTICLE_TITLE_LIMIT);
  const primaryArticle = articleId && articleTitle && !equivalentText(articleId, articleTitle)
    ? { articleId, title: articleTitle }
    : null;

  return {
    conceptNodeId,
    conceptTitle,
    mode,
    prompt: mode === "quiz"
      ? conceptTitle
      : `Explain ${conceptTitle} using intuition, mathematics, and cited local evidence.`,
    returnTo: createConceptGraphHref(conceptNodeId),
    primaryArticle,
  };
}

export function createConceptGraphHref(conceptNodeId: string): string {
  const normalized = normalizeConceptNodeId(conceptNodeId);
  if (!normalized) {
    return "/graph";
  }
  const params = new URLSearchParams({ node_id: normalized });
  return `/graph?${params.toString()}`;
}

export function getConceptTutorContextMessage(
  mode: ConceptTutorDisplayMode,
  hasPrimaryArticle: boolean,
): string {
  if (mode === "quiz") {
    return hasPrimaryArticle
      ? "Quiz uses the selected local Article and concept topic."
      : "Quiz keeps the concept topic; no local Article is selected.";
  }
  if (mode === "explain") {
    return hasPrimaryArticle
      ? "Graph context supplements the selected local Article evidence."
      : "Explain keeps the Concept as supplemental Graph context; no local Article is selected.";
  }
  const label = mode === "qa" ? "Q&A" : `${mode[0].toUpperCase()}${mode.slice(1)}`;
  return hasPrimaryArticle
    ? `${label} keeps the selected local Article and Concept context.`
    : `${label} keeps the Concept context; no local Article is selected.`;
}

function readParam(input: SearchParamInput, key: string): string {
  const value = input instanceof URLSearchParams ? input.get(key) : input[key];
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function normalizeArticleId(value: string): string | null {
  const clean = value.trim();
  return SAFE_ARTICLE_ID.test(clean) ? clean : null;
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
