"use client";

import Link from "next/link";
import { FormEvent, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { fetchArticle } from "@/lib/articles";
import {
  getConceptTutorContextMessage,
  type ConceptTutorLaunch,
} from "@/lib/conceptLearningLaunch";
import type { LearningWorkflowContext } from "@/lib/learningWorkflow";
import {
  QuizQuestion,
  TutorMode,
  TutorResponse,
  TutorSessionsResponse,
  askTutor,
  createTutorSession,
  fetchTutorSessions,
  requestTutorQuiz,
} from "@/lib/tutor";
import {
  MAX_RENDERED_TUTOR_SOURCES,
  createTutorModeResetState,
  deriveRefusalLabel,
  formatSelectionSummaryLines,
  getTutorEvidenceScopeMessage,
  isResearchEvidenceGap,
  isResearchLocalOnly,
  normalizeTutorQuizTopic,
  type TutorSelectionLine,
} from "@/lib/tutorPresentation";
import {
  getTutorModeLabel,
  createTutorRequestContext,
  isTutorRequestContextCurrent,
  type TutorArticleSelection,
  type TutorQuizAnswers,
  type TutorRequestContext,
} from "@/lib/tutorWorkspace";

import { TutorActivity } from "./TutorActivity";
import { TutorArticlePicker } from "./TutorArticlePicker";
import { TutorMarkdown } from "./TutorMarkdown";
import { TutorQuizWorkspace } from "./TutorQuizWorkspace";
import { TutorSourceList } from "./TutorSourceList";

const modes: TutorMode[] = ["explain", "derive", "qa", "quiz", "research"];
const ACTIVITY_UPDATE_ERROR = "The answer is ready, but recent activity could not be updated.";

type TutorFlowStatus = "idle" | "loading" | "ready" | "error";
type SessionStatus = "idle" | "loading" | "loaded" | "error";

export function TutorView({
  initialConcept,
  initialContext,
}: Readonly<{
  initialConcept: ConceptTutorLaunch | null;
  initialContext: LearningWorkflowContext | null;
}>) {
  const [mode, setMode] = useState<TutorMode>(initialConcept?.mode ?? "explain");
  const [question, setQuestion] = useState(initialConcept?.prompt ?? "");
  const [selectedArticle, setSelectedArticle] = useState<TutorArticleSelection | null>(() =>
    initialContext
      ? {
          id: initialContext.articleId,
          title: initialContext.articleTitle ?? "Current article",
          metadata: {},
        }
      : initialConcept?.primaryArticle
        ? {
            id: initialConcept.primaryArticle.articleId,
            title: initialConcept.primaryArticle.title,
            metadata: {},
          }
      : null,
  );
  const [nodeId, setNodeId] = useState(initialConcept?.conceptNodeId ?? initialContext?.nodeId ?? "");
  const [response, setResponse] = useState<TutorResponse | null>(null);
  const [quiz, setQuiz] = useState<QuizQuestion[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<TutorQuizAnswers>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [sessions, setSessions] = useState<TutorSessionsResponse | null>(null);
  const [articleTitles, setArticleTitles] = useState<Record<string, string>>(() =>
    initialContext?.articleTitle
      ? { [initialContext.articleId]: initialContext.articleTitle }
      : initialConcept?.primaryArticle
        ? { [initialConcept.primaryArticle.articleId]: initialConcept.primaryArticle.title }
        : {},
  );

  const [status, setStatus] = useState<TutorFlowStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [sessionsStatus, setSessionsStatus] = useState<SessionStatus>("idle");
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const activeRequestId = useRef(0);
  const sessionsRequestId = useRef(0);
  const mountedRef = useRef(false);
  const questionRef = useRef<HTMLTextAreaElement>(null);
  const resultRegionRef = useRef<HTMLElement>(null);
  const errorRegionRef = useRef<HTMLDivElement>(null);
  const currentRequestContext = createTutorRequestContext({
    mode,
    question,
    articleId: selectedArticle?.id,
    nodeId,
  });
  const currentRequestContextRef = useRef<TutorRequestContext>(currentRequestContext);
  currentRequestContextRef.current = currentRequestContext;

  useLayoutEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      activeRequestId.current += 1;
      sessionsRequestId.current += 1;
    };
  }, []);

  useEffect(() => {
    void fetchSessions();
  }, []);

  useLayoutEffect(() => {
    invalidateTutorOutcome();
    let cancelled = false;

    if (initialConcept) {
      setMode(initialConcept.mode);
      setQuestion(initialConcept.prompt);
      setNodeId(initialConcept.conceptNodeId);
      setSelectedArticle(
        initialConcept.primaryArticle
          ? {
              id: initialConcept.primaryArticle.articleId,
              title: initialConcept.primaryArticle.title,
              metadata: {},
            }
          : null,
      );
      if (initialConcept.primaryArticle) {
        setArticleTitles((current) => ({
          ...current,
          [initialConcept.primaryArticle!.articleId]: initialConcept.primaryArticle!.title,
        }));
      }
      return () => {
        cancelled = true;
      };
    }

    setMode("explain");
    setQuestion("");
    if (!initialContext?.articleId) {
      setNodeId("");
      setSelectedArticle(null);
      return () => {
        cancelled = true;
      };
    }

    setSelectedArticle({
      id: initialContext.articleId,
      title: initialContext.articleTitle ?? "Current article",
      metadata: {},
    });
    setNodeId(initialContext.nodeId ?? "");
    if (initialContext.articleTitle) {
      setArticleTitles((current) => ({ ...current, [initialContext.articleId]: initialContext.articleTitle as string }));
      return;
    }

    void fetchArticle(initialContext.articleId)
      .then((article) => {
        if (cancelled) {
          return;
        }
        setSelectedArticle((current) =>
          current?.id === article.id
            ? { id: article.id, title: article.title, metadata: article.metadata }
            : current,
        );
        setArticleTitles((current) => ({ ...current, [article.id]: article.title }));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [initialConcept, initialContext]);

  useEffect(() => {
    if (status !== "ready" || (mode === "quiz" && quiz.length > 0)) {
      return;
    }
    const focusFrame = window.requestAnimationFrame(() => {
      resultRegionRef.current?.focus({ preventScroll: true });
      resultRegionRef.current?.scrollIntoView({ behavior: "auto", block: "nearest" });
    });
    return () => window.cancelAnimationFrame(focusFrame);
  }, [mode, quiz.length, response, status]);

  useEffect(() => {
    if (status !== "error") {
      return;
    }
    const focusFrame = window.requestAnimationFrame(() => {
      errorRegionRef.current?.focus({ preventScroll: true });
      errorRegionRef.current?.scrollIntoView({ behavior: "auto", block: "nearest" });
    });
    return () => window.cancelAnimationFrame(focusFrame);
  }, [status]);

  useEffect(() => {
    if (!sessions?.items.length) {
      return;
    }
    const missingIds = [...new Set(
      sessions.items
        .slice(0, 5)
        .map((session) => session.article_id)
        .filter((articleId): articleId is string => Boolean(articleId && !articleTitles[articleId])),
    )];
    if (!missingIds.length) {
      return;
    }
    let cancelled = false;
    void Promise.allSettled(missingIds.map((articleId) => fetchArticle(articleId))).then((results) => {
      if (cancelled) {
        return;
      }
      const resolved: Record<string, string> = {};
      results.forEach((result) => {
        if (result.status === "fulfilled") {
          resolved[result.value.id] = result.value.title;
        }
      });
      if (Object.keys(resolved).length) {
        setArticleTitles((current) => ({ ...current, ...resolved }));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [sessions, articleTitles]);

  async function fetchSessions(expectedTutorRequestId?: number) {
    const requestId = sessionsRequestId.current + 1;
    sessionsRequestId.current = requestId;
    if (expectedTutorRequestId === undefined) {
      setSessionsStatus("loading");
      setSessionsError(null);
    }
    try {
      const nextSessions = await fetchTutorSessions();
      if (
        sessionsRequestId.current !== requestId
        || (expectedTutorRequestId !== undefined
          && activeRequestId.current !== expectedTutorRequestId)
      ) {
        return;
      }
      setSessions(nextSessions);
      setSessionsStatus("loaded");
      setSessionsError(null);
    } catch {
      if (
        sessionsRequestId.current !== requestId
        || (expectedTutorRequestId !== undefined
          && activeRequestId.current !== expectedTutorRequestId)
      ) {
        return;
      }
      setSessionsStatus("error");
      setSessionsError("Failed to load recent tutor activity.");
    }
  }

  async function recordTutorActivity(context: TutorRequestContext, tutorRequestId: number) {
    try {
      await createTutorSession({
        mode: context.mode,
        article_id: context.articleId ?? undefined,
        node_id: context.nodeId || undefined,
      });
      if (!mountedRef.current || activeRequestId.current !== tutorRequestId) {
        return;
      }
      await fetchSessions(tutorRequestId);
    } catch {
      if (!mountedRef.current || activeRequestId.current !== tutorRequestId) {
        return;
      }
      sessionsRequestId.current += 1;
      setSessionsStatus("error");
      setSessionsError(ACTIVITY_UPDATE_ERROR);
    }
  }

  const selectionSummary = useMemo<TutorSelectionLine[]>(() => {
    if (!response) {
      return [];
    }
    return formatSelectionSummaryLines(response.selection_summary);
  }, [response]);

  const articleQuestionLabel = mode === "quiz" ? "Prompt" : "Question";

  function clearActivityUpdateError() {
    if (sessionsError !== ACTIVITY_UPDATE_ERROR) {
      return;
    }
    setSessionsStatus(sessions ? "loaded" : "idle");
    setSessionsError(null);
  }

  function invalidateTutorOutcome() {
    activeRequestId.current += 1;
    const reset = createTutorModeResetState();
    setStatus(reset.status);
    setError(reset.error);
    setResponse(reset.response);
    setQuiz(reset.quiz);
    setQuizAnswers({});
    setQuizSubmitted(false);
    clearActivityUpdateError();
  }

  function chooseArticle(article: TutorArticleSelection | null) {
    if (article?.id !== selectedArticle?.id) {
      invalidateTutorOutcome();
    }
    setSelectedArticle(article);
    if (article) {
      setArticleTitles((current) => ({ ...current, [article.id]: article.title }));
    }
  }

  function changeMode(nextMode: TutorMode) {
    if (nextMode === mode) {
      return;
    }
    invalidateTutorOutcome();
    setMode(nextMode);
    if (initialConcept && nextMode === "quiz") {
      setQuestion(initialConcept.conceptTitle);
    } else if (initialConcept && nextMode === "explain") {
      setQuestion(`Explain ${initialConcept.conceptTitle} using intuition, mathematics, and cited local evidence.`);
    }
  }

  function changeQuestion(nextQuestion: string) {
    if (nextQuestion !== question) {
      invalidateTutorOutcome();
    }
    setQuestion(nextQuestion);
  }

  function changeNodeId(nextNodeId: string) {
    if (nextNodeId !== nodeId) {
      invalidateTutorOutcome();
    }
    setNodeId(nextNodeId);
  }

  async function runTutorQuery(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    clearActivityUpdateError();
    const requestId = activeRequestId.current + 1;
    activeRequestId.current = requestId;
    const submittedContext = createTutorRequestContext({
      mode,
      question,
      articleId: selectedArticle?.id,
      nodeId,
    });
    setStatus("loading");
    setError(null);
    setResponse(null);
    setQuiz([]);
    setQuizAnswers({});
    setQuizSubmitted(false);

    const articleId = selectedArticle?.id;
    const graphNodeId = nodeId.trim() || undefined;

    try {
      if (mode === "quiz") {
        const quizResponse = await requestTutorQuiz({
          article_id: articleId,
          node_id: graphNodeId,
          num_questions: 3,
          topic: normalizeTutorQuizTopic(question),
        });
        if (
          activeRequestId.current !== requestId
          || !isTutorRequestContextCurrent(submittedContext, currentRequestContextRef.current)
        ) {
          return;
        }
        setQuiz(quizResponse.questions);
      } else {
        const tutorResponse = await askTutor({
          question,
          mode,
          article_id: articleId,
          node_id: graphNodeId,
          top_k: 5,
          include_graph_context: true,
          include_zotero_context: true,
        });
        if (
          activeRequestId.current !== requestId
          || !isTutorRequestContextCurrent(submittedContext, currentRequestContextRef.current)
        ) {
          return;
        }
        setResponse(tutorResponse);
      }
      setStatus("ready");
      void recordTutorActivity(submittedContext, requestId);
    } catch (reason) {
      if (
        activeRequestId.current !== requestId
        || !isTutorRequestContextCurrent(submittedContext, currentRequestContextRef.current)
      ) {
        return;
      }
      setError(reason instanceof Error ? reason.message : "Failed to run tutor request");
      setStatus("error");
    }
  }

  function useFollowUp(nextQuestion: string) {
    setQuestion(nextQuestion);
    requestAnimationFrame(() => questionRef.current?.focus());
  }

  const refusalMessage = response ? deriveRefusalLabel(response) : null;
  const hasRefusalState = Boolean(response && refusalMessage);
  const isResearchMode = response?.mode === "research";
  const researchLocalOnly = response ? isResearchLocalOnly(response) : false;
  const researchEvidenceGap = response ? isResearchEvidenceGap(response) : false;
  const statusAnnouncement = status === "loading"
    ? "Tutor request in progress."
    : status === "ready"
      ? mode === "quiz"
        ? quiz.length
          ? `Quiz ready with ${quiz.length} questions.`
          : "Quiz request completed without questions."
        : response
          ? `${hasRefusalState ? "Tutor refusal" : "Tutor answer"} ready.`
          : "Tutor request completed without a response."
      : "";

  return (
    <>
      <p aria-atomic="true" aria-live="polite" className="sr-only" data-testid="tutor-request-status" role="status">
        {statusAnnouncement}
      </p>
      <section aria-busy={status === "loading"} className="space-y-6" data-testid="guided-tutor-workspace">
      <div className="space-y-2 border-b border-slate-300 pb-5">
        <p className="text-xs font-semibold uppercase text-emerald-800">Guided study workspace</p>
        <h1 className="text-2xl font-semibold">AI Research Tutor</h1>
        <p className="max-w-3xl text-sm leading-6 text-slate-600">
          Select a local Article, choose a study mode, and work from cited evidence.
        </p>
      </div>

      {initialContext ? (
        <section data-testid="learning-workflow-context" className="flex flex-col gap-3 border-y border-emerald-200 bg-emerald-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase text-emerald-800">Opened from Article</p>
            <p className="mt-1 break-words text-sm font-medium text-emerald-950">
              {initialContext.articleTitle ?? selectedArticle?.title ?? "Current article"}
            </p>
          </div>
          <Link className="w-fit shrink-0 rounded border border-emerald-300 bg-white px-3 py-2 text-sm font-semibold text-emerald-900 hover:border-emerald-600" href={initialContext.returnTo}>
            Return to article
          </Link>
        </section>
      ) : null}

      {initialConcept ? (
        <section data-testid="concept-learning-context" className="flex flex-col gap-3 border-y border-emerald-200 bg-emerald-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase text-emerald-800">Opened from Concept</p>
            <p className="mt-1 break-words text-sm font-medium text-emerald-950 [overflow-wrap:anywhere]">
              {initialConcept.conceptTitle}
            </p>
            <p className="mt-1 text-xs leading-5 text-emerald-900">
              {getConceptTutorContextMessage(mode, Boolean(selectedArticle))}
            </p>
          </div>
          <Link className="w-fit shrink-0 rounded border border-emerald-300 bg-white px-3 py-2 text-sm font-semibold text-emerald-900 hover:border-emerald-600" href={initialConcept.returnTo}>
            Return to concept
          </Link>
        </section>
      ) : null}

      <TutorArticlePicker selected={selectedArticle} onSelect={chooseArticle} />

      <form className="grid gap-4 border-y border-slate-200 bg-white px-4 py-5" onSubmit={runTutorQuery}>
        <fieldset className="space-y-2" data-testid="tutor-mode-group">
          <legend className="text-sm font-medium">Study mode</legend>
          <div className="grid w-full grid-cols-2 gap-1 rounded border border-slate-300 p-1 sm:grid-cols-5">
            {modes.map((item) => {
              const active = mode === item;
              return (
                <button
                  key={item}
                  aria-pressed={active}
                  className={`min-w-0 rounded border px-2 py-2 text-sm transition ${active ? "border-emerald-700 bg-emerald-700 text-white" : "border-slate-200 bg-white text-slate-700 hover:border-slate-900"}`}
                  type="button"
                  onClick={() => changeMode(item)}
                >
                  {getTutorModeLabel(item)}
                </button>
              );
            })}
          </div>
        </fieldset>

        {initialConcept ? (
          <div className="border-y border-slate-200 py-3 text-sm">
            <span className="font-medium">{mode === "quiz" ? "Concept topic" : "Graph context"}</span>
            <p className="mt-1 break-words text-slate-600 [overflow-wrap:anywhere]">{initialConcept.conceptTitle}</p>
          </div>
        ) : (
          <details className="border-y border-slate-200 py-3">
            <summary className="cursor-pointer text-sm font-semibold text-slate-700">Advanced context</summary>
            <label className="mt-3 grid max-w-xl gap-1 text-sm">
              <span className="font-medium">Graph concept key</span>
              <input
                className="rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
                value={nodeId}
                onChange={(event) => changeNodeId(event.target.value)}
                placeholder="Optional, for example concept:attention"
              />
            </label>
          </details>
        )}

        <label className="grid gap-1 text-sm">
          <span className="font-medium">{articleQuestionLabel}</span>
          <textarea
            ref={questionRef}
            className="min-h-28 rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
            value={question}
            onChange={(event) => changeQuestion(event.target.value)}
            placeholder={mode === "quiz" ? "Optional topic for this knowledge check" : "Ask a grounded question"}
          />
        </label>

        <div className="flex flex-wrap items-center gap-3">
          <button
            className="w-fit rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={status === "loading" || (mode !== "quiz" && !question.trim())}
            type="submit"
          >
            {status === "loading" ? "Running..." : mode === "quiz" ? "Generate quiz" : "Ask tutor"}
          </button>
          <p className="text-xs text-slate-500">
            {getTutorEvidenceScopeMessage(Boolean(selectedArticle))}
          </p>
        </div>
      </form>

      {status === "loading" ? <div className="border-l-4 border-slate-300 bg-white px-4 py-3"><p className="text-sm text-slate-700">Running tutor request...</p></div> : null}

      {status === "error" ? (
        <div
          ref={errorRegionRef}
          className="scroll-mt-24 border-l-4 border-red-500 bg-red-50 px-4 py-3 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-red-700"
          data-testid="tutor-error"
          role="alert"
          tabIndex={-1}
        >
          <p className="text-sm text-red-700">{error ?? "Tutor request failed."}</p>
          <button className="mt-2 rounded bg-slate-900 px-3 py-2 text-xs font-medium text-white" onClick={() => void runTutorQuery()} type="button">Retry request</button>
        </div>
      ) : null}

      {status === "ready" && mode === "quiz" ? (
        quiz.length ? (
          <TutorQuizWorkspace
            answers={quizAnswers}
            onAnswer={(index, answer) => setQuizAnswers((current) => ({ ...current, [index]: answer }))}
            onReset={() => {
              setQuizAnswers({});
              setQuizSubmitted(false);
            }}
            onSubmit={() => setQuizSubmitted(true)}
            questions={quiz}
            submitted={quizSubmitted}
          />
        ) : (
          <div
            ref={(node) => {
              resultRegionRef.current = node;
            }}
            className="scroll-mt-24 border-y border-slate-200 bg-white py-4 text-sm text-slate-600 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
            data-testid="tutor-empty-result"
            tabIndex={-1}
          >
            No quiz questions returned. Choose an Article with answerable evidence and retry.
          </div>
        )
      ) : null}

      {status === "ready" && response ? (
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <article
            ref={(node) => {
              resultRegionRef.current = node;
            }}
            aria-labelledby="tutor-result-heading"
            className="min-w-0 scroll-mt-24 border-y border-slate-200 bg-white py-4 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
            data-testid="tutor-result"
            tabIndex={-1}
          >
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold" id="tutor-result-heading">{hasRefusalState ? "Refusal" : "Answer"}</h2>
              {hasRefusalState && refusalMessage ? <span className="rounded border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700">Refusal</span> : null}
            </div>
            <div className="mt-3">
              <TutorMarkdown content={response.answer || refusalMessage || "No answer returned."} />
            </div>
            {response.follow_up_questions.length ? (
              <div className="mt-5 border-t border-slate-200 pt-4">
                <h3 className="text-sm font-semibold">Continue learning</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  {response.follow_up_questions.map((item) => (
                    <button
                      key={item}
                      className="max-w-full rounded border border-emerald-300 bg-emerald-50 px-3 py-2 text-left text-sm text-emerald-950 hover:border-emerald-700"
                      onClick={() => useFollowUp(item)}
                      type="button"
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </article>
          <aside className="grid min-w-0 content-start gap-4">
            <TutorSourceList compact title="来源" sources={response.sources} maxSources={MAX_RENDERED_TUTOR_SOURCES} />
            <SelectionContextSummary lines={selectionSummary} />
            <ContextSummary graphNodes={response.graph_context.nodes?.length ?? 0} graphEdges={response.graph_context.edges?.length ?? 0} zoteroItems={response.zotero_context.length} />
            {isResearchMode ? <ResearchNotice localOnly={researchLocalOnly} evidenceGap={researchEvidenceGap} /> : null}
          </aside>
        </section>
      ) : null}

      {status === "ready" && mode !== "quiz" && !response ? (
        <div
          ref={(node) => {
            resultRegionRef.current = node;
          }}
          className="scroll-mt-24 border-y border-slate-200 bg-white py-4 text-sm text-slate-600 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
          data-testid="tutor-empty-result"
          tabIndex={-1}
        >
          No response for this request. Retry or adjust your inputs.
        </div>
      ) : null}

      <TutorActivity
        articleTitles={articleTitles}
        error={sessionsError}
        onRetry={() => void fetchSessions()}
        sessions={sessions?.items ?? []}
        status={sessionsStatus}
      />
      </section>
    </>
  );
}

function SelectionContextSummary({ lines }: Readonly<{ lines: TutorSelectionLine[] }>) {
  if (!lines.length) {
    return null;
  }
  return (
    <section className="border-y border-slate-200 bg-white py-4">
      <h2 className="text-base font-semibold">来源选择摘要</h2>
      <dl className="mt-3 grid gap-2 text-sm">
        {lines.map((item) => (
          <div key={item.label} className="grid gap-1 text-xs sm:grid-cols-[140px_1fr] sm:items-center sm:text-sm">
            <dt className="text-slate-500">{item.label}</dt>
            <dd className="break-words font-medium">{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ContextSummary({ graphNodes, graphEdges, zoteroItems }: Readonly<{ graphNodes: number; graphEdges: number; zoteroItems: number }>) {
  return (
    <section className="border-y border-slate-200 bg-white py-4">
      <h2 className="text-base font-semibold">Context</h2>
      <dl className="mt-3 grid gap-2 text-sm">
        <div className="grid gap-1 sm:grid-cols-[120px_1fr] sm:items-center"><dt className="text-slate-500">Graph nodes</dt><dd className="break-words font-medium">{graphNodes}</dd></div>
        <div className="grid gap-1 sm:grid-cols-[120px_1fr] sm:items-center"><dt className="text-slate-500">Graph edges</dt><dd className="break-words font-medium">{graphEdges}</dd></div>
        <div className="grid gap-1 sm:grid-cols-[120px_1fr] sm:items-center"><dt className="text-slate-500">Zotero items</dt><dd className="break-words font-medium">{zoteroItems}</dd></div>
      </dl>
    </section>
  );
}

function ResearchNotice({ localOnly, evidenceGap }: Readonly<{ localOnly: boolean; evidenceGap: boolean }>) {
  return (
    <section className="border-y border-indigo-200 bg-indigo-50 py-4">
      <h2 className="text-sm font-semibold text-indigo-900">Research 模式范围</h2>
      <p className="mt-2 text-xs text-indigo-900">
        {localOnly ? "Research 结果仅基于本地语料证据，不能据此推断外部文献覆盖情况。" : "Research 模式的资料范围受限。"}
      </p>
      {evidenceGap ? <p className="mt-2 text-xs text-indigo-900">检测到资料缺口：当前本地来源不足以形成完整综合。</p> : null}
    </section>
  );
}
