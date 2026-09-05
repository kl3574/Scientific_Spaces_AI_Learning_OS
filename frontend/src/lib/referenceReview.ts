import type {
  ReferenceClassification,
  ReferenceType,
  ZoteroCandidatePage,
} from "./references";
import {
  createArticleDetailHref,
  sanitizeArticleEntryReturnPath,
} from "./learningWorkflow";

export type CandidateFilter = "all" | "matched" | "ambiguous" | "unmatched";

export type ReferenceReviewState = {
  q: string;
  referenceType: ReferenceType | null;
  classification: ReferenceClassification | null;
  page: number;
  referenceId: string | null;
  candidateFilter: CandidateFilter;
  returnTo: string | null;
};

export type ReferenceRequestOwner = {
  generation: number;
  requestKey: string;
};

export type ArticleReferenceReturnTarget = {
  articleId: string;
  referencePage: number;
  path: string;
};

type ReferenceReviewFocusIntent =
  | { target: "results" }
  | { target: "detail"; referenceId: string }
  | { target: "candidate-filter"; filter: CandidateFilter };

let pendingFocusIntent: ReferenceReviewFocusIntent | null = null;

export type SearchParamInput = URLSearchParams | Record<string, string | string[] | undefined>;

const LOCAL_ORIGIN = "http://scientific-spaces.local";
const MAX_QUERY_LENGTH = 200;
const MAX_RETURN_LENGTH = 1_200;
const MAX_PAGE = 100_000;
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;
const REFERENCE_TYPES = new Set<ReferenceType>([
  "doi",
  "arxiv",
  "http_url",
  "relative_or_internal_url",
  "citation_text",
  "unsupported",
  "malformed",
]);
const REFERENCE_CLASSIFICATIONS = new Set<ReferenceClassification>([
  "extracted",
  "normalized",
  "duplicate",
  "ambiguous",
  "unsupported",
  "malformed",
  "rejected",
]);
const CANDIDATE_FILTERS = new Set<CandidateFilter>([
  "all",
  "matched",
  "ambiguous",
  "unmatched",
]);

export const DEFAULT_REFERENCE_REVIEW_STATE: ReferenceReviewState = {
  q: "",
  referenceType: null,
  classification: null,
  page: 1,
  referenceId: null,
  candidateFilter: "all",
  returnTo: null,
};

export function parseReferenceReviewState(input: SearchParamInput): ReferenceReviewState {
  const q = normalizeText(readParam(input, "q"), MAX_QUERY_LENGTH);
  const referenceType = readEnum(readParam(input, "reference_type"), REFERENCE_TYPES);
  const classification = readEnum(
    readParam(input, "classification"),
    REFERENCE_CLASSIFICATIONS,
  );
  const rawPage = Number.parseInt(readParam(input, "page"), 10);
  const page = Number.isSafeInteger(rawPage) && rawPage > 0
    ? Math.min(rawPage, MAX_PAGE)
    : 1;
  const referenceId = normalizeId(readParam(input, "reference_id"));
  const candidateFilter = readEnum(
    readParam(input, "candidate"),
    CANDIDATE_FILTERS,
  ) ?? "all";
  const returnTo = referenceId
    ? canonicalArticleReferenceReturn(
        readParam(input, "return_to"),
        referenceId,
        null,
      )
    : null;

  return {
    q,
    referenceType,
    classification,
    page,
    referenceId,
    candidateFilter,
    returnTo,
  };
}

export function createReferenceReviewHref(state: ReferenceReviewState): string {
  const normalized = parseReferenceReviewState({
    q: state.q,
    reference_type: state.referenceType ?? "",
    classification: state.classification ?? "",
    page: String(state.page),
    reference_id: state.referenceId ?? "",
    candidate: state.candidateFilter,
    return_to: state.returnTo ?? "",
  });
  const params = new URLSearchParams();
  if (normalized.q) {
    params.set("q", normalized.q);
  }
  if (normalized.referenceType) {
    params.set("reference_type", normalized.referenceType);
  }
  if (normalized.classification) {
    params.set("classification", normalized.classification);
  }
  if (normalized.page > 1) {
    params.set("page", String(normalized.page));
  }
  if (normalized.referenceId) {
    params.set("reference_id", normalized.referenceId);
  }
  if (normalized.candidateFilter !== "all") {
    params.set("candidate", normalized.candidateFilter);
  }
  if (normalized.returnTo) {
    params.set("return_to", normalized.returnTo);
  }
  const query = params.toString();
  return query ? `/zotero?${query}` : "/zotero";
}

export function isCanonicalReferenceReviewSearchParams(
  input: SearchParamInput,
  state = parseReferenceReviewState(input),
): boolean {
  const expected = createReferenceReviewHref(state).split("?", 2)[1] ?? "";
  return serializeSearchParams(input) === expected;
}

export function createArticleReferenceReturnPath(input: {
  articleId: string;
  referenceId: string;
  referencePage: number;
  currentArticlePath: string;
}): string | null {
  const articleId = normalizeId(input.articleId);
  const referenceId = normalizeId(input.referenceId);
  if (!articleId || !referenceId) {
    return null;
  }

  const current = parseLocalUrl(input.currentArticlePath);
  const currentArticleId = current ? readArticleId(current.pathname) : null;
  const listReturnTo = current && currentArticleId === articleId
    ? sanitizeArticleEntryReturnPath(current.searchParams.get("from"))
    : "/articles";
  const target = new URL(createArticleDetailHref(articleId, listReturnTo), LOCAL_ORIGIN);
  const page = normalizePage(input.referencePage);
  if (page > 1) {
    target.searchParams.set("reference_page", String(page));
  }
  target.hash = referenceRowId(referenceId);
  return localPath(target);
}

export function resolveOwnedReferenceReturnPath(
  value: string | null | undefined,
  sourceArticleIds: string | readonly string[],
  referenceId: string,
): string | null {
  const target = parseArticleReferenceReturnTarget(value, referenceId);
  if (!target) {
    return null;
  }
  const allowedArticleIds = (Array.isArray(sourceArticleIds) ? sourceArticleIds : [sourceArticleIds])
    .map((articleId) => normalizeId(articleId))
    .filter((articleId): articleId is string => Boolean(articleId));
  return allowedArticleIds.includes(target.articleId) ? target.path : null;
}

export function parseArticleReferenceReturnTarget(
  value: string | null | undefined,
  referenceId: string,
): ArticleReferenceReturnTarget | null {
  const cleanReferenceId = normalizeId(referenceId);
  if (!cleanReferenceId) {
    return null;
  }
  const path = canonicalArticleReferenceReturn(value ?? "", cleanReferenceId, null);
  const parsed = path ? parseLocalUrl(path) : null;
  const articleId = parsed ? readArticleId(parsed.pathname) : null;
  if (!path || !parsed || !articleId) {
    return null;
  }
  return {
    articleId,
    referencePage: normalizePage(
      Number.parseInt(parsed.searchParams.get("reference_page") ?? "", 10),
    ),
    path,
  };
}

export function resolveAvailableReferencePage(
  requestedPage: number,
  totalPages: number,
): number {
  const requested = normalizePage(requestedPage);
  const available = Number.isSafeInteger(totalPages) && totalPages > 0
    ? Math.min(totalPages, MAX_PAGE)
    : 1;
  return Math.min(requested, available);
}

export function referenceRowId(referenceId: string): string {
  const normalized = normalizeId(referenceId);
  return `structured-reference-${normalized ?? "invalid"}`;
}

export function createReferenceRequestOwner(
  generation: number,
  requestKey: string,
): ReferenceRequestOwner {
  return { generation, requestKey };
}

export function ownsReferenceRequest(
  owner: ReferenceRequestOwner | null,
  currentGeneration: number,
  currentRequestKey: string,
): boolean {
  return owner?.generation === currentGeneration
    && owner.requestKey === currentRequestKey;
}

export function ownsReferenceCandidatePage(
  page: Pick<ZoteroCandidatePage, "reference_id"> | null,
  selectedReferenceId: string | null,
): boolean {
  return Boolean(
    page
    && selectedReferenceId
    && page.reference_id === selectedReferenceId,
  );
}

export function rememberReferenceResultsFocus(): void {
  pendingFocusIntent = { target: "results" };
}

export function rememberReferenceDetailFocus(referenceId: string): void {
  const normalized = normalizeId(referenceId);
  pendingFocusIntent = normalized
    ? { target: "detail", referenceId: normalized }
    : null;
}

export function consumeReferenceResultsFocus(): boolean {
  if (pendingFocusIntent?.target !== "results") {
    return false;
  }
  pendingFocusIntent = null;
  return true;
}

export function consumeReferenceDetailFocus(referenceId: string): boolean {
  if (
    pendingFocusIntent?.target !== "detail"
    || pendingFocusIntent.referenceId !== normalizeId(referenceId)
  ) {
    return false;
  }
  pendingFocusIntent = null;
  return true;
}

export function rememberCandidateFilterFocus(filter: CandidateFilter): void {
  pendingFocusIntent = { target: "candidate-filter", filter };
}

export function consumeCandidateFilterFocus(filter: CandidateFilter): boolean {
  if (
    pendingFocusIntent?.target !== "candidate-filter"
    || pendingFocusIntent.filter !== filter
  ) {
    return false;
  }
  pendingFocusIntent = null;
  return true;
}

function canonicalArticleReferenceReturn(
  value: string,
  referenceId: string,
  expectedArticleId: string | null,
): string | null {
  if (!value || value.length > MAX_RETURN_LENGTH) {
    return null;
  }
  const parsed = parseLocalUrl(value);
  if (!parsed || parsed.username || parsed.password) {
    return null;
  }
  const articleId = readArticleId(parsed.pathname);
  if (!articleId || (expectedArticleId && articleId !== expectedArticleId)) {
    return null;
  }
  if (decodeHash(parsed.hash) !== referenceRowId(referenceId)) {
    return null;
  }
  const allowedParams = new Set(["from", "reference_page"]);
  if ([...parsed.searchParams.keys()].some((key) => !allowedParams.has(key))) {
    return null;
  }
  const listReturnTo = sanitizeArticleEntryReturnPath(parsed.searchParams.get("from"));
  const target = new URL(createArticleDetailHref(articleId, listReturnTo), LOCAL_ORIGIN);
  const page = normalizePage(Number.parseInt(parsed.searchParams.get("reference_page") ?? "", 10));
  if (page > 1) {
    target.searchParams.set("reference_page", String(page));
  }
  target.hash = referenceRowId(referenceId);
  return localPath(target);
}

function parseLocalUrl(value: string): URL | null {
  try {
    const parsed = new URL(value, LOCAL_ORIGIN);
    return parsed.origin === LOCAL_ORIGIN ? parsed : null;
  } catch {
    return null;
  }
}

function readArticleId(pathname: string): string | null {
  const match = pathname.match(/^\/articles\/([^/]+)$/);
  if (!match) {
    return null;
  }
  try {
    return normalizeId(decodeURIComponent(match[1]));
  } catch {
    return null;
  }
}

function localPath(url: URL): string {
  return `${url.pathname}${url.search}${url.hash}`;
}

function decodeHash(hash: string): string {
  try {
    return decodeURIComponent(hash.replace(/^#/, ""));
  } catch {
    return "";
  }
}

function readParam(input: SearchParamInput, key: string): string {
  const value = input instanceof URLSearchParams ? input.get(key) : input[key];
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function serializeSearchParams(input: SearchParamInput): string {
  if (input instanceof URLSearchParams) {
    return input.toString();
  }
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(input)) {
    if (Array.isArray(value)) {
      value.forEach((item) => params.append(key, item));
    } else if (value !== undefined) {
      params.append(key, value);
    }
  }
  return params.toString();
}

function readEnum<T extends string>(value: string, allowed: Set<T>): T | null {
  return allowed.has(value as T) ? (value as T) : null;
}

function normalizeText(value: string, maxLength: number): string {
  return value
    .replace(/[\u0000-\u001f\u007f]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, maxLength);
}

function normalizeId(value: string | null | undefined): string | null {
  const clean = value?.trim() ?? "";
  return SAFE_ID.test(clean) ? clean : null;
}

function normalizePage(value: number): number {
  return Number.isSafeInteger(value) && value > 0 ? Math.min(value, MAX_PAGE) : 1;
}
