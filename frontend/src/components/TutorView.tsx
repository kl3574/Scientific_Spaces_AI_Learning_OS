"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

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

const modes: TutorMode[] = ["explain", "derive", "qa", "quiz", "research"];

export function TutorView() {
  const [mode, setMode] = useState<TutorMode>("explain");
  const [question, setQuestion] = useState("什么是Attention？");
  const [articleId, setArticleId] = useState("attention-001");
  const [nodeId, setNodeId] = useState("concept:attention");
  const [response, setResponse] = useState<TutorResponse | null>(null);
  const [quiz, setQuiz] = useState<QuizQuestion[]>([]);
  const [sessions, setSessions] = useState<TutorSessionsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTutorSessions()
      .then(setSessions)
      .catch(() => setSessions(null));
  }, []);

  const graphCounts = useMemo(() => {
    const nodes = response?.graph_context.nodes?.length ?? 0;
    const edges = response?.graph_context.edges?.length ?? 0;
    return { nodes, edges };
  }, [response]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);
    setQuiz([]);
    try {
      const cleanArticleId = articleId.trim() || undefined;
      const cleanNodeId = nodeId.trim() || undefined;
      if (mode === "quiz") {
        const quizResponse = await requestTutorQuiz({
          article_id: cleanArticleId,
          node_id: cleanNodeId,
          num_questions: 3,
        });
        setQuiz(quizResponse.questions);
      } else {
        setResponse(
          await askTutor({
            question,
            mode,
            article_id: cleanArticleId,
            node_id: cleanNodeId,
            top_k: 5,
            include_graph_context: true,
            include_zotero_context: true,
          }),
        );
      }
      setSessions(await fetchTutorSessions().catch(() => null));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run tutor request");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-6">
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-semibold">AI Research Tutor</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Grounded tutor responses over articles, graph evidence, Zotero metadata, and local learning state.
        </p>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <form className="grid gap-4 rounded border border-slate-200 bg-white p-4" onSubmit={handleSubmit}>
        <div className="grid gap-3 md:grid-cols-[180px_minmax(0,1fr)_minmax(0,1fr)]">
          <label className="grid gap-1 text-sm">
            <span className="font-medium">Mode</span>
            <select
              className="rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
              value={mode}
              onChange={(event) => setMode(event.target.value as TutorMode)}
            >
              {modes.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-sm">
            <span className="font-medium">Article ID</span>
            <input
              className="rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
              value={articleId}
              onChange={(event) => setArticleId(event.target.value)}
            />
          </label>
          <label className="grid gap-1 text-sm">
            <span className="font-medium">Graph Node</span>
            <input
              className="rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
              value={nodeId}
              onChange={(event) => setNodeId(event.target.value)}
            />
          </label>
        </div>

        <label className="grid gap-1 text-sm">
          <span className="font-medium">Question</span>
          <textarea
            className="min-h-24 rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />
        </label>

        <button
          className="w-fit rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={loading}
          type="submit"
        >
          {loading ? "Running..." : mode === "quiz" ? "Generate quiz" : "Ask tutor"}
        </button>
      </form>

      {response ? (
        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <article className="rounded border border-slate-200 bg-white p-4">
            <h2 className="text-base font-semibold">{response.refusal_reason ? "Refusal" : "Answer"}</h2>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">{response.answer}</p>
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
          <aside className="space-y-4">
            <SourceList sources={response.sources} />
            <ContextSummary graphNodes={graphCounts.nodes} graphEdges={graphCounts.edges} zoteroItems={response.zotero_context.length} />
          </aside>
        </section>
      ) : null}

      {quiz.length ? (
        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold">Quiz</h2>
          <div className="mt-3 grid gap-3">
            {quiz.map((item, index) => (
              <article key={`${item.question}-${index}`} className="rounded border border-slate-100 p-3 text-sm">
                <p className="font-medium">{item.question}</p>
                <p className="mt-2 text-slate-700">Answer: {item.correct_answer}</p>
                <p className="mt-2 text-slate-600">{item.explanation}</p>
                <SourceList sources={item.sources} compact />
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold">Tutor Sessions</h2>
        <p className="mt-2 text-sm text-slate-600">{sessions?.total ?? 0} local session summaries</p>
      </section>
    </section>
  );
}

function SourceList({ sources, compact = false }: Readonly<{ sources: TutorSource[]; compact?: boolean }>) {
  return (
    <section className={compact ? "mt-3" : "rounded border border-slate-200 bg-white p-4"}>
      <h2 className="text-base font-semibold">Sources</h2>
      <div className="mt-3 grid gap-2">
        {sources.length ? (
          sources.map((source) => (
            <article key={`${source.source_type}-${source.source_id}`} className="rounded border border-slate-100 p-3 text-sm">
              <p className="font-medium">{source.title}</p>
              <p className="mt-1 text-xs text-slate-500">
                {source.source_type}
                {source.section_title ? ` · ${source.section_title}` : ""}
                {typeof source.chunk_index === "number" ? ` · chunk ${source.chunk_index}` : ""}
              </p>
              {source.url ? (
                <a className="mt-2 inline-block text-xs text-slate-600 hover:text-slate-950" href={source.url} rel="noreferrer" target="_blank">
                  Open source
                </a>
              ) : null}
            </article>
          ))
        ) : (
          <p className="text-sm text-slate-600">No sources returned.</p>
        )}
      </div>
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
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">Graph nodes</dt>
          <dd className="font-medium">{graphNodes}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">Graph edges</dt>
          <dd className="font-medium">{graphEdges}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">Zotero items</dt>
          <dd className="font-medium">{zoteroItems}</dd>
        </div>
      </dl>
    </section>
  );
}
