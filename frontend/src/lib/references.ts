export type ReferenceType =
  | "doi"
  | "arxiv"
  | "http_url"
  | "relative_or_internal_url"
  | "citation_text"
  | "unsupported"
  | "malformed";

export type ReferenceClassification =
  | "extracted"
  | "normalized"
  | "duplicate"
  | "ambiguous"
  | "unsupported"
  | "malformed"
  | "rejected";

export type CandidateDecision = "exact" | "probable" | "ambiguous" | "unmatched" | "rejected";

export type ReferenceRecord = {
  schema_version: string;
  reference_id: string;
  reference_type: ReferenceType;
  classification: ReferenceClassification;
  canonical_key: string | null;
  normalized_identifier: string | null;
  normalized_url: string | null;
  doi: string | null;
  arxiv_id: string | null;
  arxiv_version: number | null;
  source_article_id: string;
  source_article_title: string;
  source_article_url: string;
  source_section: string;
  source_span_start: number | null;
  source_span_end: number | null;
  evidence_text: string;
  source_count: number;
  extraction_rule: string;
  extraction_rule_version: string;
  confidence: number;
  duplicate_group_id: string | null;
  record_fingerprint: string;
};

export type ReferenceEvidence = {
  schema_version: string;
  evidence_id: string;
  reference_id: string;
  source_article_id: string;
  source_article_title: string;
  source_article_url: string;
  source_section: string;
  source_span_start: number | null;
  source_span_end: number | null;
  evidence_text: string;
  candidate_ordinal: number;
  extraction_rule: string;
  extraction_rule_version: string;
  classification: ReferenceClassification;
};

export type ReferencePage = {
  items: ReferenceRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  article_id?: string | null;
  reference_type?: ReferenceType | null;
  classification?: ReferenceClassification | null;
  query?: string | null;
};

export type ReferenceDetail = {
  record: ReferenceRecord;
  evidence: ReferenceEvidence[];
  evidence_total: number;
  provenance_limit: number;
  provenance_truncated: boolean;
};

export type ZoteroMatchCandidate = {
  schema_version: string;
  candidate_id: string;
  reference_id: string;
  zotero_item_key: string | null;
  item_type: string | null;
  title: string | null;
  doi: string | null;
  url: string | null;
  arxiv_id: string | null;
  arxiv_version: number | null;
  match_method: string;
  match_score: number;
  matched_fields: string[];
  conflicting_fields: string[];
  provenance: {
    evidence_ids: string[];
    matcher_version: string | null;
  };
  decision: CandidateDecision;
  matcher_version: string;
  zotero_snapshot_fingerprint: string | null;
};

export type ZoteroCandidatePage = {
  items: ZoteroMatchCandidate[];
  total: number;
  limit: number;
  truncated: boolean;
  reference_id: string;
  decision: CandidateDecision | null;
};

export type ReferenceSummary = {
  status: "valid";
  schema_version: string;
  record_schema_version: string;
  evidence_schema_version: string;
  candidate_schema_version: string;
  corpus_fingerprint: string;
  configuration_fingerprint: string;
  build_fingerprint: string;
  extractor_version: string;
  normalization_version: string;
  matcher_version: string | null;
  generated_at: string;
  counts: Record<string, unknown>;
  network_request_count: number;
};

export class ReferenceApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly state: string | null;

  constructor(message: string, status: number, code: string | null = null, state: string | null = null) {
    super(message);
    this.name = "ReferenceApiError";
    this.status = status;
    this.code = code;
    this.state = state;
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchReferenceSummary(): Promise<ReferenceSummary> {
  return requestJson<ReferenceSummary>(new URL("/v1.2/reference-summary", API_BASE_URL));
}

export async function fetchReferences(options: {
  page?: number;
  pageSize?: number;
  referenceType?: ReferenceType;
  classification?: ReferenceClassification;
  articleId?: string;
  query?: string;
} = {}): Promise<ReferencePage> {
  const url = new URL("/v1.2/references", API_BASE_URL);
  setPageOptions(url, options.page, options.pageSize);
  if (options.referenceType) {
    url.searchParams.set("reference_type", options.referenceType);
  }
  if (options.classification) {
    url.searchParams.set("classification", options.classification);
  }
  if (options.articleId?.trim()) {
    url.searchParams.set("article_id", options.articleId.trim());
  }
  if (options.query?.trim()) {
    url.searchParams.set("q", options.query.trim());
  }
  return requestJson<ReferencePage>(url);
}

export async function fetchArticleReferences(
  articleId: string,
  options: {
    page?: number;
    pageSize?: number;
    referenceType?: ReferenceType;
    classification?: ReferenceClassification;
  } = {},
): Promise<ReferencePage> {
  const url = new URL(`/v1.2/articles/${encodeURIComponent(articleId)}/references`, API_BASE_URL);
  setPageOptions(url, options.page, options.pageSize);
  if (options.referenceType) {
    url.searchParams.set("reference_type", options.referenceType);
  }
  if (options.classification) {
    url.searchParams.set("classification", options.classification);
  }
  return requestJson<ReferencePage>(url);
}

export async function fetchReference(referenceId: string, provenanceLimit = 5): Promise<ReferenceDetail> {
  const url = new URL(`/v1.2/references/${encodeURIComponent(referenceId)}`, API_BASE_URL);
  url.searchParams.set("provenance_limit", String(provenanceLimit));
  return requestJson<ReferenceDetail>(url);
}

export async function fetchZoteroCandidates(
  referenceId: string,
  options: {
    limit?: number;
    decision?: CandidateDecision;
  } = {},
): Promise<ZoteroCandidatePage> {
  const url = new URL(
    `/v1.2/references/${encodeURIComponent(referenceId)}/zotero-candidates`,
    API_BASE_URL,
  );
  url.searchParams.set("limit", String(options.limit ?? 20));
  if (options.decision) {
    url.searchParams.set("decision", options.decision);
  }
  return requestJson<ZoteroCandidatePage>(url);
}

export function referenceHref(record: ReferenceRecord): string | null {
  if (isSafeHttpUrl(record.normalized_url)) {
    return record.normalized_url;
  }
  if (record.doi) {
    return `https://doi.org/${encodeURIComponent(record.doi)}`;
  }
  if (record.arxiv_id) {
    const version = record.arxiv_version ? `v${record.arxiv_version}` : "";
    return `https://arxiv.org/abs/${encodeURIComponent(record.arxiv_id)}${version}`;
  }
  return null;
}

export function candidateHref(candidate: ZoteroMatchCandidate): string | null {
  if (isSafeHttpUrl(candidate.url)) {
    return candidate.url;
  }
  if (candidate.doi) {
    return `https://doi.org/${encodeURIComponent(candidate.doi)}`;
  }
  if (candidate.arxiv_id) {
    const version = candidate.arxiv_version ? `v${candidate.arxiv_version}` : "";
    return `https://arxiv.org/abs/${encodeURIComponent(candidate.arxiv_id)}${version}`;
  }
  return null;
}

export function referenceErrorMessage(error: unknown): string {
  if (!(error instanceof ReferenceApiError)) {
    return error instanceof Error ? error.message : "Failed to load structured references";
  }
  if (error.state === "stale") {
    return "The reference index is stale and must be rebuilt.";
  }
  if (error.state === "corrupt") {
    return "The reference index failed integrity validation.";
  }
  if (error.state === "missing") {
    return "The reference index is not available.";
  }
  return error.message;
}

function setPageOptions(url: URL, page?: number, pageSize?: number): void {
  if (Number.isFinite(page) && (page as number) > 0) {
    url.searchParams.set("page", String(page));
  }
  if (Number.isFinite(pageSize) && (pageSize as number) > 0) {
    url.searchParams.set("page_size", String(pageSize));
  }
}

function isSafeHttpUrl(value: string | null | undefined): value is string {
  if (!value) {
    return false;
  }
  try {
    const parsed = new URL(value);
    return (parsed.protocol === "http:" || parsed.protocol === "https:") && !parsed.username && !parsed.password;
  } catch {
    return false;
  }
}

async function requestJson<T>(url: URL): Promise<T> {
  const response = await fetch(url.toString(), { cache: "no-store" });
  if (response.ok) {
    return response.json() as Promise<T>;
  }

  let code: string | null = null;
  let state: string | null = null;
  let message = `Reference request failed: ${response.status}`;
  try {
    const payload = (await response.json()) as {
      detail?: string | { code?: string; state?: string; message?: string };
    };
    if (typeof payload.detail === "string") {
      message = payload.detail;
    } else if (payload.detail) {
      code = payload.detail.code ?? null;
      state = payload.detail.state ?? null;
      message = payload.detail.message ?? message;
    }
  } catch {
    // Keep the bounded status-only fallback.
  }
  throw new ReferenceApiError(message, response.status, code, state);
}
