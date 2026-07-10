"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

import {
  QuizQuestion,
  TutorMode,
  TutorResponse,
  TutorSessionsResponse,
  TutorSource,
  askTutor,
  fetchTutorSessions,
  requestTutorQuiz,
} from "@/lib/tutor";
import {
  MAX_RENDERED_TUTOR_SOURCES,
  createTutorModeResetState,
  getBoundedSourceRows,
  getSafeDisplayText,
  getSafeExternalUrl,
  getSourceDisclosure,
  deriveRefusalLabel,
  formatSelectionSummaryLines,
  isResearchEvidenceGap,
  isResearchLocalOnly,
  normalizeTutorQuizTopic,
  resolveSourceArticleId,
  type TutorSelectionLine,
} from "@/lib/tutorPresentation";

const modes: TutorMode[] = ["explain", "derive", "qa", "quiz", "research"];
const DEFAULT_SOURCE_PREVIEW = 3;

type TutorFlowStatus = "idle" | "loading" | "ready" | "error";
type SessionStatus = "idle" | "loading" | "loaded" | "error";

export function TutorView() {
  const [mode, setMode] = useState<TutorMode>("explain");
  const [question, setQuestion] = useState("");
  const [articleId, setArticleId] = useState("");
  const [nodeId, setNodeId] = useState("");
  const [response, setResponse] = useState<TutorResponse | null>(null);
  const [quiz, setQuiz] = useState<QuizQuestion[]>([]);
  const [sessions, setSessions] = useState<TutorSessionsResponse | null>(null);

  const [status, setStatus] = useState<TutorFlowStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [sessionsStatus, setSessionsStatus] = useState<SessionStatus>("idle");
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const activeRequestId = useRef(0);

  useEffect(() => {
    void fetchSessions();
  }, []);

  async function fetchSessions() {
    setSessionsStatus("loading");
    setSessionsError(null);
    try {
      setSessions(await fetchTutorSessions());
      setSessionsStatus("loaded");
    } catch {
      setSessions(null);
      setSessionsStatus("error");
      setSessionsError("Failed to load tutor sessions.");
    }
  }

  const selectionSummary = useMemo<TutorSelectionLine[]>(() => {
    if (!response) {
      return [];
    }
    return formatSelectionSummaryLines(response.selection_summary);
  }, [response]);

  const articleQuestionLabel = mode === "quiz" ? "Prompt" : "Question";

  function changeMode(nextMode: TutorMode) {
    if (nextMode === mode) {
      return;
    }

    activeRequestId.current += 1;
    const reset = createTutorModeResetState();
    setMode(nextMode);
    setStatus(reset.status);
    setError(reset.error);
    setResponse(reset.response);
    setQuiz(reset.quiz);
  }

  async function runTutorQuery(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const requestId = activeRequestId.current + 1;
    activeRequestId.current = requestId;
    setStatus("loading");
    setError(null);
    setResponse(null);
    setQuiz([]);

    const cleanArticleId = articleId.trim() || undefined;
    const cleanNodeId = nodeId.trim() || undefined;

    try {
      if (mode === "quiz") {
        const quizResponse = await requestTutorQuiz({
          article_id: cleanArticleId,
          node_id: cleanNodeId,
          num_questions: 3,
          topic: normalizeTutorQuizTopic(question),
        });
        if (activeRequestId.current !== requestId) {
          return;
        }
        setQuiz(quizResponse.questions);
        setStatus("ready");
      } else {
        const tutorResponse = await askTutor({
          question,
          mode,
          article_id: cleanArticleId,
          node_id: cleanNodeId,
          top_k: 5,
          include_graph_context: true,
          include_zotero_context: true,
        });
        if (activeRequestId.current !== requestId) {
          return;
        }
        setResponse(tutorResponse);
        setStatus("ready");
      }
      await fetchSessions();
    } catch (err) {
      if (activeRequestId.current !== requestId) {
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to run tutor request");
      setStatus("error");
    }
  }

  const refusalMessage = response ? deriveRefusalLabel(response) : null;
  const hasRefusalState = Boolean(response && refusalMessage);
  const isResearchMode = response?.mode === "research";
  const researchLocalOnly = response ? isResearchLocalOnly(response) : false;
  const researchEvidenceGap = response ? isResearchEvidenceGap(response) : false;

  return (
    <section className="space-y-6">
      <div className="space-y-2 border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-semibold">AI Research Tutor</h1>
        <p className="max-w-3xl text-sm leading-6 text-slate-600">
          Grounded tutor responses are bounded by mode, bounded evidence budgets, and local source safety.
        </p>
      </div>

      <form className="grid gap-4 rounded border border-slate-200 bg-white p-4" onSubmit={runTutorQuery}>
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Mode</legend>
          <div className="inline-flex w-full flex-wrap gap-2 rounded border border-slate-300 p-1" role="tablist" aria-label="Tutor mode">
            {modes.map((item) => {
              const active = mode === item;
              return (
                <button
                  key={item}
                  className={`rounded border px-3 py-2 text-sm capitalize transition ${
                    active
                      ? "border-slate-900 bg-slate-950 text-white"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-900"
                  }`}
                  type="button"
                  onClick={() => changeMode(item)}
                >
                  {item}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-1 text-sm">
            <span className="font-medium">Article ID</span>
            <input
              className="rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
              value={articleId}
              onChange={(event) => setArticleId(event.target.value)}
              placeholder="Optional Article ID"
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="font-medium">Graph Node</span>
            <input
              className="rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
              value={nodeId}
              onChange={(event) => setNodeId(event.target.value)}
              placeholder="Optional concept:attention"
            />
          </label>
        </div>

        <label className="grid gap-1 text-sm">
          <span className="font-medium">{articleQuestionLabel}</span>
          <textarea
            className="min-h-24 rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={mode === "quiz" ? "Prompt for quiz topic" : "Ask a question"}
          />
        </label>

        <button
          className="w-fit rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={status === "loading"}
          type="submit"
        >
          {status === "loading" ? "Running..." : mode === "quiz" ? "Generate quiz" : "Ask tutor"}
        </button>
      </form>

      {status === "loading" ? (
        <div className="rounded border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-700">Running tutor request...</p>
        </div>
      ) : null}

      {status === "error" ? (
        <div className="rounded border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-700">{error ?? "Tutor request failed."}</p>
          <button
            className="mt-2 rounded bg-slate-900 px-3 py-2 text-xs font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
            onClick={() => void runTutorQuery()}
            type="button"
          >
            Retry
          </button>
        </div>
      ) : null}

      {status === "ready" && mode === "quiz" ? (
        <section className="grid gap-4">
          <h2 className="text-base font-semibold">Quiz</h2>
          {quiz.length === 0 ? (
            <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">No quiz questions returned.</div>
          ) : (
            <div className="grid gap-3">
              {quiz.map((item, index) => (
                <article key={`${item.question}-${index}`} className="rounded border border-slate-200 bg-white p-4 text-sm">
                  <p className="font-medium">{item.question}</p>
                  <p className="mt-2 text-slate-700">Answer: {item.correct_answer}</p>
                  <p className="mt-2 text-slate-600">{item.explanation}</p>
                  <SourceList sources={item.sources} compact title="题目来源" />
                  {item.options?.length ? (
                    <div className="mt-3">
                      <p className="mb-1 text-xs font-semibold text-slate-500">Options</p>
                      <ul className="grid gap-1 text-xs text-slate-700">
                        {item.options.map((option) => (
                          <li key={option} className="rounded border border-slate-100 px-2 py-1">
                            {option}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {status === "ready" && response ? (
        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <article className="min-w-0 rounded border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold">{hasRefusalState ? "Refusal" : "Answer"}</h2>
              {hasRefusalState && refusalMessage ? <span className="rounded border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700">Refusal</span> : null}
            </div>
            <p className="mt-3 break-words whitespace-pre-wrap text-sm leading-6 text-slate-700">
              {response.answer || refusalMessage || "No answer returned."}
            </p>
            {response.follow_up_questions.length ? (
              <div className="mt-4">
                <h3 className="text-sm font-semibold">Follow-up Questions</h3>
                <ul className="mt-2 grid gap-2 text-sm text-slate-700">
                  {response.follow_up_questions.map((item) => (
                    <li key={item} className="rounded border border-slate-100 px-3 py-2">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </article>
          <aside className="grid min-w-0 gap-4">
            <SourceList
              compact
              title="来源"
              sources={response.sources}
              maxSources={MAX_RENDERED_TUTOR_SOURCES}
              maxVisible={DEFAULT_SOURCE_PREVIEW}
            />
            <SelectionContextSummary lines={selectionSummary} />
            <ContextSummary graphNodes={response.graph_context.nodes?.length ?? 0} graphEdges={response.graph_context.edges?.length ?? 0} zoteroItems={response.zotero_context.length} />
            {isResearchMode ? <ResearchNotice localOnly={researchLocalOnly} evidenceGap={researchEvidenceGap} /> : null}
          </aside>
        </section>
      ) : null}

      {status === "ready" && mode !== "quiz" && !response ? (
        <div className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">No response for this request. Retry or adjust your inputs.</div>
      ) : null}

      <section className="rounded border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-base font-semibold">Tutor Sessions</h2>
          {sessionsStatus === "loading" ? <span className="text-xs text-slate-500">Loading...</span> : null}
        </div>
        {sessionsStatus === "error" ? (
          <div className="mt-2 space-y-2">
            <p className="text-sm text-red-700">{sessionsError ?? "Failed to load tutor sessions."}</p>
            <button
              className="rounded bg-slate-900 px-3 py-2 text-xs font-medium text-white"
              onClick={() => void fetchSessions()}
              type="button"
            >
              Retry
            </button>
          </div>
        ) : null}
        {sessionsStatus === "loaded" ? (
          <p className="mt-2 text-sm text-slate-600">{sessions?.total ?? 0} local session summaries</p>
        ) : null}
      </section>
    </section>
  );
}

function SourceList({
  sources,
  compact = false,
  title = "来源",
  maxSources = MAX_RENDERED_TUTOR_SOURCES,
  maxVisible = DEFAULT_SOURCE_PREVIEW,
}: Readonly<{
  sources: TutorSource[];
  compact?: boolean;
  title?: string;
  maxSources?: number;
  maxVisible?: number;
}>) {
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    setExpanded(false);
  }, [sources]);

  const bounded = useMemo(
    () =>
      getBoundedSourceRows(sources, {
        maxSources,
        maxVisible,
        expanded,
      }),
    [sources, expanded, maxSources, maxVisible],
  );
  const disclosure = getSourceDisclosure(bounded, { expanded, maxVisible });

  return (
    <section className={compact ? "mt-3 min-w-0" : "min-w-0 rounded border border-slate-200 bg-white p-4"}>
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="mt-3 grid gap-2">
        {!sources.length ? <p className="text-sm text-slate-600">未返回来源。</p> : null}
        {bounded.visibleSources.map((source) => {
          const safeTitle = getSafeDisplayText(source.title) ?? "未命名来源";
          const safeSourceType = getSafeDisplayText(source.source_type) ?? "source";
          const safeSectionTitle = getSafeDisplayText(source.section_title);
          const articleId = resolveSourceArticleId(source);
          const externalUrl = getSafeExternalUrl(source.url);
          return (
            <article
              key={`${source.source_type}-${source.source_id}`}
              className="rounded border border-slate-100 bg-white p-3 text-xs sm:text-sm"
            >
              <p className="font-medium break-words">{safeTitle}</p>
              <p className="mt-1 break-words text-[11px] text-slate-500">
                {safeSourceType}
                {safeSectionTitle ? ` · ${safeSectionTitle}` : ""}
                {typeof source.chunk_index === "number" ? ` · chunk ${source.chunk_index}` : ""}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {articleId ? (
                  <Link
                    className="inline-block rounded border border-slate-200 px-2 py-1 text-xs text-slate-700 hover:border-slate-900"
                    href={`/articles/${encodeURIComponent(articleId)}`}
                  >
                    Open local article
                  </Link>
                ) : null}
                {externalUrl ? (
                  <a
                    className="inline-block rounded border border-slate-200 px-2 py-1 text-xs text-slate-700 hover:border-slate-900"
                    href={externalUrl}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Open original source
                  </a>
                ) : null}
              </div>
            </article>
          );
        })}
        {disclosure.omittedLabel ? (
          <p className="text-xs leading-5 text-slate-500">{disclosure.omittedLabel}</p>
        ) : null}
        {disclosure.canToggle && disclosure.toggleLabel ? (
          <button
            className="w-fit rounded border border-slate-200 px-2 py-1 text-xs text-slate-700"
            onClick={() => setExpanded((current) => !current)}
            type="button"
          >
            {disclosure.toggleLabel}
          </button>
        ) : null}
      </div>
    </section>
  );
}

function SelectionContextSummary({ lines }: Readonly<{ lines: TutorSelectionLine[] }>) {
  if (!lines.length) {
    return null;
  }

  return (
    <section className="rounded border border-slate-200 bg-white p-4">
      <h2 className="text-base font-semibold">来源选择摘要</h2>
      <dl className="mt-3 grid gap-2 text-sm">
        {lines.map((item) => (
          <div key={item.label} className="grid gap-1 text-xs sm:grid-cols-[140px_1fr] sm:items-center sm:text-sm">
            <dt className="text-slate-500">{item.label}</dt>
            <dd className="font-medium break-words">{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ContextSummary({
  graphNodes,
  graphEdges,
  zoteroItems,
}: Readonly<{ graphNodes: number; graphEdges: number; zoteroItems: number }>) {
  return (
    <section className="rounded border border-slate-200 bg-white p-4">
      <h2 className="text-base font-semibold">Context</h2>
      <dl className="mt-3 grid gap-2 text-sm">
        <div className="grid gap-1 sm:grid-cols-[120px_1fr] sm:items-center">
          <dt className="text-slate-500">Graph nodes</dt>
          <dd className="font-medium break-words">{graphNodes}</dd>
        </div>
        <div className="grid gap-1 sm:grid-cols-[120px_1fr] sm:items-center">
          <dt className="text-slate-500">Graph edges</dt>
          <dd className="font-medium break-words">{graphEdges}</dd>
        </div>
        <div className="grid gap-1 sm:grid-cols-[120px_1fr] sm:items-center">
          <dt className="text-slate-500">Zotero items</dt>
          <dd className="font-medium break-words">{zoteroItems}</dd>
        </div>
      </dl>
    </section>
  );
}

function ResearchNotice({ localOnly, evidenceGap }: Readonly<{ localOnly: boolean; evidenceGap: boolean }>) {
  return (
    <section className="rounded border border-indigo-200 bg-indigo-50 p-4">
      <h2 className="text-sm font-semibold text-indigo-900">Research 模式范围</h2>
      <p className="mt-2 text-xs text-indigo-900">
        {localOnly
          ? "Research 结果仅基于本地语料证据，不能据此推断外部文献覆盖情况。"
          : "Research 模式的资料范围受限。"}
      </p>
      {evidenceGap ? (
        <p className="mt-2 text-xs text-indigo-900">
          检测到资料缺口：当前本地来源不足以形成完整综合。
        </p>
      ) : null}
    </section>
  );
}
