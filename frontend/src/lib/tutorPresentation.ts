import type {
  QuizQuestion,
  TutorEvidenceSummary,
  TutorResponse,
  TutorSelectionSummary,
  TutorSource,
} from "./tutor";

export type BoundedSourceRows = {
  sources: TutorSource[];
  hiddenReturnedCount: number;
  omittedReturnedCount: number;
};

export type TutorSelectionLine = {
  label: string;
  value: string;
};

export type SourceDisclosure = {
  canToggle: boolean;
  toggleLabel: string | null;
  omittedLabel: string | null;
};

export type TutorModeResetState = {
  status: "idle";
  error: null;
  response: null;
  quiz: QuizQuestion[];
};

export const MAX_RENDERED_TUTOR_SOURCES = 72;

const DEFAULT_COLLAPSED_SOURCE_ROWS = 3;
const UNSAFE_URI = /(?:^|[\s"'(<>=])(?:data|file|ftp|javascript|mailto|sftp|ssh|vbscript):/i;
const ABSOLUTE_POSIX_PATH = /(?:^|[\s"'(<>=:])\/(?!\/)(?:[^/\\\s"'<>]+\/)+[^/\\\s"'<>]*/i;
const WINDOWS_PATH = /(?:^|[\s"'(<>=:])[A-Za-z]:[\\/][^\s"'<>]*/;
const UNC_PATH = /(?:^|[\s"'(<>=])(?:\\\\|\/\/)[^\\/\s"'<>]+[\\/][^\s"'<>]*/;
const PATH_TRAVERSAL = /(?:^|[\s"'(<>=:\\/])\.{1,2}(?:[\\/]|$)/;
const HOME_RELATIVE_PATH = /(?:^|[\s"'(<>=:])~[\\/]/;
const CONTROL_CHARACTERS = /[\u0000-\u001f\u007f]/;
const SAFE_ARTICLE_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;

export function createTutorModeResetState(): TutorModeResetState {
  return {
    status: "idle",
    error: null,
    response: null,
    quiz: [],
  };
}

export function normalizeTutorQuizTopic(prompt: string): string | undefined {
  return prompt.trim() || undefined;
}

export function dedupeTutorSources(
  sources: readonly TutorSource[],
  maxSources = MAX_RENDERED_TUTOR_SOURCES,
): BoundedSourceRows {
  const seen = new Set<string>();
  const deduped: TutorSource[] = [];

  for (const source of sources) {
    if (!source || typeof source.source_type !== "string" || typeof source.source_id !== "string") {
      continue;
    }
    const key = `${source.source_type}:${source.source_id}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(source);
  }

  const sourceLimit = normalizeLimit(maxSources, MAX_RENDERED_TUTOR_SOURCES, 0);
  const bounded = deduped.slice(0, sourceLimit);
  const omittedReturnedCount = Math.max(deduped.length - bounded.length, 0);
  return {
    sources: bounded,
    hiddenReturnedCount: omittedReturnedCount,
    omittedReturnedCount,
  };
}

export function getBoundedSourceRows(
  sources: readonly TutorSource[],
  options: {
    maxSources?: number;
    maxVisible?: number;
    expanded?: boolean;
  } = {},
): BoundedSourceRows & {
  visibleSources: TutorSource[];
} {
  const maxSources = normalizeLimit(options.maxSources, MAX_RENDERED_TUTOR_SOURCES, 0);
  const maxVisible = normalizeLimit(options.maxVisible, DEFAULT_COLLAPSED_SOURCE_ROWS, 1);
  const deduped = dedupeTutorSources(sources, maxSources);
  const visibleSources = options.expanded
    ? deduped.sources
    : deduped.sources.slice(0, Math.min(maxVisible, deduped.sources.length));

  return {
    sources: deduped.sources,
    hiddenReturnedCount: Math.max(deduped.sources.length - visibleSources.length, 0),
    omittedReturnedCount: deduped.omittedReturnedCount,
    visibleSources,
  };
}

export function getSourceDisclosure(
  rows: BoundedSourceRows,
  options: {
    expanded: boolean;
    maxVisible?: number;
  },
): SourceDisclosure {
  const maxVisible = normalizeLimit(options.maxVisible, DEFAULT_COLLAPSED_SOURCE_ROWS, 1);
  const collapsedVisibleCount = Math.min(maxVisible, rows.sources.length);
  const expandableCount = Math.max(rows.sources.length - collapsedVisibleCount, 0);
  const canToggle = expandableCount > 0;

  return {
    canToggle,
    toggleLabel: canToggle
      ? options.expanded
        ? `收起来源（保留前 ${collapsedVisibleCount} 条预览）`
        : `展开另外 ${expandableCount} 条已返回来源`
      : null,
    omittedLabel:
      rows.omittedReturnedCount > 0
        ? `已达到界面显示上限，另有 ${rows.omittedReturnedCount} 条返回来源未显示。`
        : null,
  };
}

export function resolveSourceArticleId(source: TutorSource): string | null {
  const metadataArticleId = source.metadata?.article_id;
  if (typeof metadataArticleId === "string") {
    const direct = safeArticleId(metadataArticleId);
    if (direct) {
      return direct;
    }
  }

  if (source.source_type !== "article_chunk" && source.source_type !== "article_metadata") {
    return null;
  }

  if (typeof source.source_id !== "string") {
    return null;
  }
  const sourceId = source.source_id.trim();
  if (!sourceId || hasUnsafeLocalReference(sourceId)) {
    return null;
  }

  const lastSegmentIndex = sourceId.lastIndexOf(":");
  if (lastSegmentIndex <= 0) {
    return safeArticleId(sourceId);
  }

  const articleId = sourceId.slice(0, lastSegmentIndex).trim();
  const chunkIndex = sourceId.slice(lastSegmentIndex + 1).trim();
  if (!/^\d+$/.test(chunkIndex)) {
    return null;
  }
  return safeArticleId(articleId);
}

export function getSafeExternalUrl(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed || hasUnsafeLocalReference(trimmed)) {
    return null;
  }

  let url: URL;
  try {
    url = new URL(trimmed);
  } catch {
    return null;
  }

  if (
    (url.protocol !== "http:" && url.protocol !== "https:")
    || !url.hostname
    || url.username
    || url.password
  ) {
    return null;
  }

  return trimmed;
}

export function getSafeDisplayText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const text = value.trim();
  if (!text || hasUnsafeLocalReference(text)) {
    return null;
  }
  return text;
}

export function formatSelectionSummary(summary: TutorSelectionSummary | null | undefined): string {
  return formatSelectionSummaryLines(summary)
    .map((line) => `${line.label}: ${line.value}`)
    .join(" · ");
}

export function formatSelectionSummaryLines(
  summary: TutorSelectionSummary | null | undefined,
): TutorSelectionLine[] {
  if (!summary) {
    return [];
  }

  const graphError = summary.graph_error_code === null
    ? null
    : getSafeDisplayText(summary.graph_error_code);
  return [
    {
      label: "候选片段",
      value: toDisplayNumber(summary.candidate_count),
    },
    {
      label: "已选来源",
      value: `${toDisplayNumber(summary.selected_article_count)} 篇文章 / ${toDisplayNumber(summary.selected_chunk_count)} 个片段`,
    },
    {
      label: "上下文字符",
      value: toDisplayNumber(summary.context_character_count),
    },
    {
      label: "估算 Token",
      value: toDisplayNumber(summary.estimated_token_count),
    },
    {
      label: "Graph",
      value: `${toDisplayNumber(summary.graph_node_count)} 个节点 / ${toDisplayNumber(summary.graph_edge_count)} 条边`,
    },
    {
      label: "Graph 延迟",
      value: summary.graph_latency_ms === null ? "未读取" : `${toDisplayDecimal(summary.graph_latency_ms)} ms`,
    },
    {
      label: "Graph 状态",
      value: graphError ?? (summary.graph_error_code === null ? "正常" : "无效错误码"),
    },
    {
      label: "已截断",
      value: summary.truncated ? "是" : "否",
    },
    {
      label: "已省略补充来源",
      value: toDisplayNumber(summary.supplement_omitted_count),
    },
  ];
}

export function isResearchLocalOnly(response: TutorResponse): boolean {
  return response.mode === "research";
}

export function isResearchEvidenceGap(response: TutorResponse): boolean {
  if (response.mode !== "research") {
    return false;
  }

  const evidence = response.evidence_summary;
  const articleCount = toInt(evidence?.article_count) ?? countDistinctArticleSources(response.sources);
  return Boolean(
    response.refusal_reason
    || evidence?.refusal_reason
    || evidence?.unsupported_or_out_of_scope === true
    || evidence?.source_schema_valid === false
    || evidence?.has_answerable_evidence === false
    || articleCount < 2
  );
}

export function deriveRefusalLabel(response: TutorResponse): string | null {
  const refusal = response.evidence_summary?.refusal_reason ?? response.refusal_reason;
  if (!refusal) {
    return null;
  }

  if (response.mode === "derive") {
    if (refusal === "insufficient_formula_evidence" || refusal === "insufficient_formula_sources") {
      return "当前资料不足以完整推导。";
    }
  }

  if (refusal === "no_relevant_source" || refusal === "no_sources") {
    return "无法基于当前资料回答。";
  }

  if (refusal === "insufficient_local_corpus_evidence") {
    return "无法基于当前资料形成可靠研究建议。";
  }

  if (refusal === "unsupported_query") {
    return "当前问题不在支持范围内。";
  }

  return "无可引用回答，请重新提问。";
}

export function isResponseRefusal(
  response: TutorResponse,
  evidence?: TutorEvidenceSummary | null,
): boolean {
  return Boolean(response.refusal_reason ?? evidence?.refusal_reason);
}

function safeArticleId(value: string): string | null {
  const articleId = value.trim();
  if (!articleId || hasUnsafeLocalReference(articleId) || !SAFE_ARTICLE_ID.test(articleId)) {
    return null;
  }
  return articleId;
}

function hasUnsafeLocalReference(value: string): boolean {
  const decoded = decodeForSafety(value);
  return [value, decoded].some((candidate) =>
    CONTROL_CHARACTERS.test(candidate)
    || UNSAFE_URI.test(candidate)
    || ABSOLUTE_POSIX_PATH.test(candidate)
    || WINDOWS_PATH.test(candidate)
    || UNC_PATH.test(candidate)
    || PATH_TRAVERSAL.test(candidate)
    || HOME_RELATIVE_PATH.test(candidate)
  );
}

function decodeForSafety(value: string): string {
  let decoded = value;
  for (let index = 0; index < 2; index += 1) {
    try {
      const next = decodeURIComponent(decoded);
      if (next === decoded) {
        break;
      }
      decoded = next;
    } catch {
      break;
    }
  }
  return decoded;
}

function countDistinctArticleSources(sources: readonly TutorSource[]): number {
  return new Set(
    sources
      .filter((source) => source.source_type === "article_chunk" || source.source_type === "article_metadata")
      .map(resolveSourceArticleId)
      .filter((articleId): articleId is string => articleId !== null),
  ).size;
}

function normalizeLimit(value: unknown, fallback: number, minimum: number): number {
  const parsed = toInt(value);
  return parsed === null ? fallback : Math.max(minimum, parsed);
}

function toInt(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }
  const normalized = Math.floor(value);
  return normalized >= 0 ? normalized : null;
}

function toDisplayNumber(value: unknown): string {
  const parsed = toInt(value);
  return parsed === null ? "-" : String(parsed);
}

function toDisplayDecimal(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    return "-";
  }
  return String(Number(value.toFixed(1)));
}
