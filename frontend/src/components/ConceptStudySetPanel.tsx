"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { createConceptTutorHref, createConceptGraphHref } from "@/lib/conceptLearningLaunch";
import { createConceptStudySet, type ConceptStudyArticle } from "@/lib/conceptStudySet";
import type { GraphNode } from "@/lib/graph";
import { createArticleDetailHref } from "@/lib/learningWorkflow";
import {
  STUDY_SESSION_CHANGE_EVENT,
  STUDY_SESSION_ITEM_LIMIT,
  STUDY_SESSION_STORAGE_KEY,
  addStudySessionItems,
  loadStudySession,
  saveStudySession,
  type StudySessionLoadResult,
} from "@/lib/studySession";

export function ConceptStudySetPanel({ node }: Readonly<{ node: GraphNode }>) {
  const studySet = useMemo(() => createConceptStudySet(node), [node]);
  const [session, setSession] = useState<StudySessionLoadResult | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    function refresh() {
      setSession(loadStudySession());
    }
    function handleStorage(event: StorageEvent) {
      if (event.key === null || event.key === STUDY_SESSION_STORAGE_KEY) {
        refresh();
      }
    }
    refresh();
    window.addEventListener(STUDY_SESSION_CHANGE_EVENT, refresh);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener(STUDY_SESSION_CHANGE_EVENT, refresh);
      window.removeEventListener("storage", handleStorage);
    };
  }, [node.node_id]);

  if (!studySet) {
    return (
      <section className="border-t border-slate-200 pt-4" data-testid="concept-study-set-unavailable">
        <h3 className="text-sm font-semibold">Concept Study Set</h3>
        <p className="mt-2 text-sm leading-6 text-amber-800" role="alert">
          This Concept cannot be opened as a safe study set.
        </p>
      </section>
    );
  }

  const queuedIds = new Set(session?.state.items.map((item) => item.articleId) ?? []);
  const sessionCount = session?.state.items.length ?? 0;
  const sessionFull = sessionCount >= STUDY_SESSION_ITEM_LIMIT;
  const storageReady = session?.storageAvailable === true;
  const returnTo = createConceptGraphHref(studySet.conceptNodeId);

  function addArticles(articles: readonly ConceptStudyArticle[]) {
    if (!session?.storageAvailable) {
      setNotice("Browser-local storage is unavailable. No Articles were added.");
      return;
    }
    const mutation = addStudySessionItems(
      session.state,
      articles.map((article) => ({ articleId: article.articleId, title: article.title })),
      new Date().toISOString(),
    );
    if (!mutation.changed) {
      setNotice(formatSessionOutcomes(mutation.outcomes));
      return;
    }
    if (!saveStudySession(mutation.state)) {
      setNotice("Focused Session storage failed. No saved change is being reported.");
      return;
    }
    setSession((current) => current ? { ...current, state: mutation.state, recovered: false } : current);
    setNotice(formatSessionOutcomes(mutation.outcomes));
  }

  return (
    <section
      className="min-w-0 border-t border-slate-200 pt-4"
      data-state={studySet.articles.length ? "ready" : "empty"}
      data-testid="concept-study-set"
    >
      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase text-emerald-800">Study this concept</p>
          <h3 className="mt-1 break-words text-base font-semibold [overflow-wrap:anywhere]">Concept Study Set</h3>
        </div>
        <span className="w-fit shrink-0 rounded border border-slate-200 px-2 py-1 text-xs text-slate-600">
          {studySet.articles.length} eligible
        </span>
      </div>

      <p className="mt-2 text-xs leading-5 text-slate-500">
        Built from the returned local provenance in deterministic source order. It is not a complete or recommended learning sequence.
      </p>

      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
        <StudyFact label="Source records" value={studySet.sourceRecordCount} />
        <StudyFact label="Returned" value={studySet.returnedRecordCount} />
        <StudyFact label="Eligible" value={studySet.articles.length} />
        <StudyFact label="Duplicates" value={studySet.duplicateRecordCount} />
        <StudyFact label="Invalid" value={studySet.invalidRecordCount} />
        <StudyFact label="Omitted" value={studySet.omittedRecordCount} />
      </dl>

      {studySet.truncated ? (
        <p className="mt-3 border-l-2 border-amber-500 pl-3 text-xs leading-5 text-amber-900" role="status">
          The Graph response is truncated; additional provenance records are not represented in this study set.
        </p>
      ) : null}

      <ol className="mt-4 space-y-4" aria-label={`Study actions for ${studySet.conceptTitle}`}>
        <StudyStep index={1} title="Explain">
          <p className="text-xs leading-5 text-slate-600">Open Tutor with the Concept and optional primary Article prefilled.</p>
          <Link
            className="mt-2 inline-flex rounded bg-slate-950 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-800"
            href={createConceptTutorHref(studySet, "explain")}
          >
            Explain concept
          </Link>
        </StudyStep>

        <StudyStep index={2} title="Read returned Articles">
          {studySet.articles.length ? (
            <ul className="mt-2 divide-y divide-slate-100 border-y border-slate-100">
              {studySet.articles.map((article) => {
                const queued = queuedIds.has(article.articleId);
                const addDisabled = !storageReady || queued || sessionFull;
                return (
                  <li className="min-w-0 py-3" key={article.articleId} data-testid="concept-study-article">
                    <Link
                      className="break-words text-sm font-semibold text-slate-950 hover:underline [overflow-wrap:anywhere]"
                      href={createArticleDetailHref(article.articleId, returnTo)}
                    >
                      {article.title}
                    </Link>
                    {article.sectionTitle ? (
                      <p className="mt-1 break-words text-xs text-slate-500 [overflow-wrap:anywhere]">
                        Source section: {article.sectionTitle}
                      </p>
                    ) : null}
                    <button
                      aria-label={queued ? `${article.title} is in study session` : `Add ${article.title} to study session`}
                      className="mt-2 rounded border border-emerald-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-emerald-900 hover:border-emerald-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
                      disabled={addDisabled}
                      title={!storageReady ? "Browser-local storage is unavailable" : sessionFull && !queued ? "Focused Session is full" : undefined}
                      type="button"
                      onClick={() => addArticles([article])}
                    >
                      {queued ? "In session" : "Add to session"}
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="mt-2 text-xs leading-5 text-slate-600">No eligible local Articles were returned for this Concept.</p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              className="rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 hover:border-slate-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
              disabled={!storageReady || studySet.articles.length === 0}
              type="button"
              onClick={() => addArticles(studySet.articles)}
            >
              Add eligible Articles
            </button>
            <Link className="text-xs font-semibold text-slate-600 hover:text-slate-950 hover:underline" href="/session">
              Open Focused Session ({sessionCount}/{STUDY_SESSION_ITEM_LIMIT})
            </Link>
          </div>
          {session?.recovered ? (
            <p className="mt-2 text-xs leading-5 text-amber-900" role="status">
              Focused Session recovered valid entries from browser storage before this action.
            </p>
          ) : null}
          {!storageReady && session ? (
            <p className="mt-2 text-xs leading-5 text-amber-900" role="alert">
              Browser-local Focused Session storage is unavailable.
            </p>
          ) : null}
          {notice ? <p className="mt-2 text-xs leading-5 text-slate-700" role="status" aria-live="polite">{notice}</p> : null}
        </StudyStep>

        <StudyStep index={3} title="Inspect related evidence">
          <p className="text-xs leading-5 text-slate-600">Use the existing map or list to inspect returned Sections, Formulas, Articles, and Zotero items.</p>
          <a className="mt-2 inline-flex text-xs font-semibold text-slate-700 hover:text-slate-950 hover:underline" href="#graph-context-panel">
            Go to Knowledge Context
          </a>
        </StudyStep>

        <StudyStep index={4} title="Check understanding">
          {studySet.primaryArticle ? (
            <Link
              className="mt-1 inline-flex rounded border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900 hover:border-slate-600"
              href={createConceptTutorHref(studySet, "quiz")}
            >
              Open concept quiz
            </Link>
          ) : (
            <p className="text-xs leading-5 text-slate-600">Quiz requires an eligible primary Article from the returned provenance.</p>
          )}
        </StudyStep>
      </ol>
    </section>
  );
}

function StudyFact({ label, value }: Readonly<{ label: string; value: number }>) {
  return (
    <div className="min-w-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="mt-1 font-semibold text-slate-950">{value}</dd>
    </div>
  );
}

function StudyStep({ index, title, children }: Readonly<{ index: number; title: string; children: React.ReactNode }>) {
  return (
    <li className="grid min-w-0 grid-cols-[24px_minmax(0,1fr)] gap-3">
      <span aria-hidden="true" className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-900">
        {index}
      </span>
      <div className="min-w-0">
        <h4 className="text-sm font-semibold">{title}</h4>
        <div className="mt-1 min-w-0">{children}</div>
      </div>
    </li>
  );
}

function formatSessionOutcomes(outcomes: {
  added: number;
  alreadyPresent: number;
  invalid: number;
  capacityOmitted: number;
}): string {
  return [
    `${outcomes.added} added`,
    `${outcomes.alreadyPresent} already present`,
    `${outcomes.invalid} invalid`,
    `${outcomes.capacityOmitted} omitted by capacity`,
  ].join("; ") + ".";
}
