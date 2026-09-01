"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { WorkspaceState } from "@/components/WorkspaceState";
import {
  STUDY_SESSION_CHANGE_EVENT,
  activateStudySessionItem,
  clearStudySession,
  createStudySessionReaderHref,
  getStudySessionPosition,
  loadStudySession,
  moveStudySessionItem,
  removeStudySessionItem,
  saveStudySession,
  type StudySessionItem,
  type StudySessionLoadResult,
  type StudySessionState,
} from "@/lib/studySession";

export function StudySessionView() {
  const [snapshot, setSnapshot] = useState<StudySessionLoadResult | null>(null);
  const [persistenceWarning, setPersistenceWarning] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);

  useEffect(() => {
    const refresh = () => setSnapshot(loadStudySession());
    refresh();
    window.addEventListener("storage", refresh);
    window.addEventListener(STUDY_SESSION_CHANGE_EVENT, refresh);
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener(STUDY_SESSION_CHANGE_EVENT, refresh);
    };
  }, []);

  const activePosition = useMemo(() => {
    const state = snapshot?.state;
    return state?.activeArticleId ? getStudySessionPosition(state, state.activeArticleId) : null;
  }, [snapshot?.state]);

  function persist(nextState: StudySessionState) {
    setSnapshot((current) => current ? { ...current, state: nextState } : current);
    if (saveStudySession(nextState)) {
      setPersistenceWarning(null);
    } else {
      setPersistenceWarning("The queue changed on this page, but browser-local storage could not save it.");
    }
  }

  function moveItem(item: StudySessionItem, direction: -1 | 1) {
    if (!snapshot) {
      return;
    }
    persist(moveStudySessionItem(snapshot.state, item.articleId, direction, new Date().toISOString()));
  }

  function setCurrent(item: StudySessionItem) {
    if (!snapshot) {
      return;
    }
    persist(activateStudySessionItem(snapshot.state, item.articleId, new Date().toISOString()));
  }

  function removeItem(item: StudySessionItem) {
    if (!snapshot) {
      return;
    }
    persist(removeStudySessionItem(snapshot.state, item.articleId, new Date().toISOString()));
    setConfirmClear(false);
  }

  function clearQueue() {
    if (!snapshot) {
      return;
    }
    persist(clearStudySession(snapshot.state, new Date().toISOString()));
    setConfirmClear(false);
  }

  return (
    <section className="min-w-0 space-y-5 md:space-y-7" data-testid="focused-study-session">
      <header className="border-b border-slate-200 pb-5">
        <p className="text-xs font-semibold uppercase text-emerald-800">Focused learning workflow</p>
        <div className="mt-1 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Focused Study Session</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Work through a bounded queue of saved Articles without losing your reading position.
            </p>
          </div>
          <Link className="w-fit text-sm font-semibold text-emerald-800 hover:text-emerald-950" href="/library">
            Open saved learning
          </Link>
        </div>
      </header>

      {!snapshot ? <WorkspaceState title="Loading study session" tone="loading" /> : null}

      {snapshot && !snapshot.storageAvailable ? (
        <WorkspaceState
          action={<Link className="text-sm font-semibold text-emerald-800" href="/library">Open saved learning</Link>}
          detail="Browser-local storage is unavailable, so a study queue cannot be recovered."
          testId="study-session-unavailable"
          title="Study session is unavailable"
          tone="unavailable"
        />
      ) : null}

      {snapshot?.storageAvailable && (snapshot.recovered || snapshot.droppedCount > 0 || snapshot.truncatedCount > 0) ? (
        <p className="border-l-2 border-amber-600 bg-amber-50 px-3 py-2 text-sm text-amber-950" role="status">
          The saved queue was recovered safely. {snapshot.droppedCount} invalid or duplicate record
          {snapshot.droppedCount === 1 ? " was" : "s were"} removed and {snapshot.truncatedCount} older record
          {snapshot.truncatedCount === 1 ? " was" : "s were"} omitted.
        </p>
      ) : null}

      {persistenceWarning ? (
        <p className="border-l-2 border-amber-600 bg-amber-50 px-3 py-2 text-sm text-amber-950" role="status">
          {persistenceWarning}
        </p>
      ) : null}

      {snapshot?.storageAvailable && snapshot.state.items.length === 0 ? (
        <WorkspaceState
          action={<Link className="text-sm font-semibold text-emerald-800" href="/library">Browse saved learning</Link>}
          detail="Add readable Articles from Saved Learning to assemble a focused session."
          testId="study-session-empty"
          title="Your study queue is empty"
          tone="empty"
        />
      ) : null}

      {snapshot?.storageAvailable && snapshot.state.items.length > 0 ? (
        <>
          <section className="grid gap-px overflow-hidden border border-slate-200 bg-slate-200 sm:grid-cols-2" data-testid="study-session-summary">
            <div className="bg-white p-4">
              <p className="text-xs font-medium text-slate-500">Queue</p>
              <p className="mt-1 text-2xl font-semibold text-slate-950">
                {snapshot.state.items.length} {snapshot.state.items.length === 1 ? "Article" : "Articles"}
              </p>
            </div>
            <div className="bg-white p-4">
              <p className="text-xs font-medium text-slate-500">Current position</p>
              <p className="mt-1 text-2xl font-semibold text-slate-950">
                {activePosition ? `${activePosition.index + 1} of ${activePosition.total}` : "Not set"}
              </p>
            </div>
          </section>

          {activePosition ? (
            <Link
              aria-label={`Continue current Article: ${activePosition.current.title}`}
              className="flex min-w-0 items-center justify-between gap-4 border-l-4 border-emerald-700 bg-emerald-50 px-4 py-3 text-emerald-950 hover:bg-emerald-100"
              href={createStudySessionReaderHref(activePosition.current)}
            >
              <span className="min-w-0">
                <span className="block text-xs font-semibold uppercase">Continue current Article</span>
                <span className="mt-1 block break-words text-base font-semibold">{activePosition.current.title}</span>
              </span>
              <span aria-hidden="true" className="shrink-0 text-xl">&#8594;</span>
            </Link>
          ) : null}

          <section aria-labelledby="study-session-queue-heading" className="border-t-2 border-emerald-700 pt-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold" id="study-session-queue-heading">Session queue</h2>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Reorder the queue or choose the Article that should open next.
                </p>
              </div>
              <div className="flex items-center gap-2">
                {confirmClear ? (
                  <>
                    <button
                      className="rounded border border-red-700 bg-red-700 px-3 py-2 text-sm font-semibold text-white hover:bg-red-800"
                      type="button"
                      onClick={clearQueue}
                    >
                      Confirm clear queue
                    </button>
                    <button
                      className="rounded border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-slate-500"
                      type="button"
                      onClick={() => setConfirmClear(false)}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    className="rounded border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-800 hover:border-red-600"
                    type="button"
                    onClick={() => setConfirmClear(true)}
                  >
                    Clear queue
                  </button>
                )}
              </div>
            </div>

            <ol className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
              {snapshot.state.items.map((item, index) => {
                const isCurrent = item.articleId === snapshot.state.activeArticleId;
                return (
                  <li className="min-w-0 py-4" data-testid="study-session-item" key={item.articleId}>
                    <div className="flex min-w-0 flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div className="flex min-w-0 items-start gap-3">
                        <span className="flex size-8 shrink-0 items-center justify-center rounded border border-slate-300 text-sm font-semibold text-slate-600">
                          {index + 1}
                        </span>
                        <div className="min-w-0">
                          <Link className="break-words text-base font-semibold text-slate-950 hover:underline" href={createStudySessionReaderHref(item)}>
                            {item.title}
                          </Link>
                          <p className={`mt-1 text-xs font-semibold ${isCurrent ? "text-emerald-800" : "text-slate-500"}`}>
                            {isCurrent ? "Current" : "Queued"}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 md:justify-end">
                        <button
                          aria-label={`Move ${item.title} up`}
                          className="flex size-10 items-center justify-center rounded border border-slate-300 bg-white text-lg text-slate-700 hover:border-slate-500 disabled:cursor-not-allowed disabled:text-slate-300"
                          disabled={index === 0}
                          title="Move up"
                          type="button"
                          onClick={() => moveItem(item, -1)}
                        >
                          <span aria-hidden="true">&#8593;</span>
                        </button>
                        <button
                          aria-label={`Move ${item.title} down`}
                          className="flex size-10 items-center justify-center rounded border border-slate-300 bg-white text-lg text-slate-700 hover:border-slate-500 disabled:cursor-not-allowed disabled:text-slate-300"
                          disabled={index === snapshot.state.items.length - 1}
                          title="Move down"
                          type="button"
                          onClick={() => moveItem(item, 1)}
                        >
                          <span aria-hidden="true">&#8595;</span>
                        </button>
                        <button
                          aria-label={`Set ${item.title} as current`}
                          className="rounded border border-emerald-300 bg-white px-3 py-2 text-sm font-semibold text-emerald-900 hover:border-emerald-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
                          disabled={isCurrent}
                          type="button"
                          onClick={() => setCurrent(item)}
                        >
                          Set current
                        </button>
                        <button
                          aria-label={`Remove ${item.title} from session`}
                          className="rounded border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-800 hover:border-red-600"
                          type="button"
                          onClick={() => removeItem(item)}
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>
        </>
      ) : null}
    </section>
  );
}
