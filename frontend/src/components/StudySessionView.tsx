"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { WorkspaceState } from "@/components/WorkspaceState";
import { fetchLearningStates, type LearningState } from "@/lib/learning";
import {
  STUDY_SESSION_CHANGE_EVENT,
  activateStudySessionItem,
  clearStudySession,
  createStudySessionCompletionSummary,
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

type SessionFocusRequest = Readonly<{
  articleId?: string;
  origin: HTMLElement | null;
  target: "clear" | "completion" | "confirm" | "empty" | "item";
}>;

export function StudySessionView() {
  const [snapshot, setSnapshot] = useState<StudySessionLoadResult | null>(null);
  const [persistenceWarning, setPersistenceWarning] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [learningStates, setLearningStates] = useState<LearningState[] | null>(null);
  const [completionState, setCompletionState] = useState<"loading" | "loaded" | "error">("loading");
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [focusRequest, setFocusRequest] = useState<SessionFocusRequest | null>(null);
  const clearQueueButtonRef = useRef<HTMLButtonElement>(null);
  const completionStatusRef = useRef<HTMLElement>(null);
  const confirmClearButtonRef = useRef<HTMLButtonElement>(null);
  const emptyRecoveryRef = useRef<HTMLAnchorElement>(null);
  const itemLinkRefs = useRef(new Map<string, HTMLAnchorElement>());

  useEffect(() => {
    const refresh = () => setSnapshot(loadStudySession());
    refresh();
    window.addEventListener("storage", refresh);
    window.addEventListener(STUDY_SESSION_CHANGE_EVENT, refresh);
    void refreshCompletion();
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener(STUDY_SESSION_CHANGE_EVENT, refresh);
    };
  }, []);

  async function refreshCompletion(origin?: HTMLButtonElement) {
    if (origin) {
      setFocusRequest({ origin, target: "completion" });
    }
    setCompletionState("loading");
    setCompletionError(null);
    try {
      const response = await fetchLearningStates();
      setLearningStates(response.items);
      setCompletionState("loaded");
    } catch (error) {
      setLearningStates(null);
      setCompletionError(error instanceof Error ? error.message : "Learning states are unavailable");
      setCompletionState("error");
    }
  }

  const activePosition = useMemo(() => {
    const state = snapshot?.state;
    return state?.activeArticleId ? getStudySessionPosition(state, state.activeArticleId) : null;
  }, [snapshot?.state]);
  const completion = useMemo(
    () => snapshot ? createStudySessionCompletionSummary(snapshot.state, learningStates) : null,
    [learningStates, snapshot],
  );

  useLayoutEffect(() => {
    const request = focusRequest;
    if (!request) {
      return;
    }
    const target = request.target === "clear"
      ? clearQueueButtonRef.current
      : request.target === "completion"
        ? completionStatusRef.current
      : request.target === "confirm"
        ? confirmClearButtonRef.current
        : request.target === "empty"
          ? emptyRecoveryRef.current
          : request.articleId
            ? itemLinkRefs.current.get(request.articleId) ?? null
            : null;
    const activeElement = document.activeElement;
    if (
      target?.isConnected
      && (
        !activeElement
        || activeElement === document.body
        || !activeElement.isConnected
        || activeElement === request.origin
      )
    ) {
      target.scrollIntoView({ behavior: "auto", block: "nearest" });
      target.focus({ preventScroll: true });
    }
    setFocusRequest((current) => (current === request ? null : current));
  }, [focusRequest, snapshot]);

  function persist(nextState: StudySessionState) {
    setSnapshot((current) => current ? { ...current, state: nextState } : current);
    if (saveStudySession(nextState)) {
      setPersistenceWarning(null);
    } else {
      setPersistenceWarning("The queue changed on this page, but browser-local storage could not save it.");
    }
  }

  function moveItem(item: StudySessionItem, direction: -1 | 1, origin: HTMLButtonElement) {
    if (!snapshot) {
      return;
    }
    const nextState = moveStudySessionItem(
      snapshot.state,
      item.articleId,
      direction,
      new Date().toISOString(),
    );
    persist(nextState);
    const nextIndex = nextState.items.findIndex((candidate) => candidate.articleId === item.articleId);
    const movedIntoDisabledBoundary = direction === -1
      ? nextIndex === 0
      : nextIndex === nextState.items.length - 1;
    if (movedIntoDisabledBoundary) {
      setFocusRequest({ articleId: item.articleId, origin, target: "item" });
    }
  }

  function setCurrent(item: StudySessionItem, origin: HTMLButtonElement) {
    if (!snapshot) {
      return;
    }
    persist(activateStudySessionItem(snapshot.state, item.articleId, new Date().toISOString()));
    setFocusRequest({ articleId: item.articleId, origin, target: "item" });
  }

  function removeItem(item: StudySessionItem, origin: HTMLButtonElement) {
    if (!snapshot) {
      return;
    }
    const removedIndex = snapshot.state.items.findIndex(
      (candidate) => candidate.articleId === item.articleId,
    );
    const nextState = removeStudySessionItem(
      snapshot.state,
      item.articleId,
      new Date().toISOString(),
    );
    const survivingItem = nextState.items[Math.min(removedIndex, nextState.items.length - 1)];
    persist(nextState);
    setConfirmClear(false);
    setFocusRequest(
      survivingItem
        ? { articleId: survivingItem.articleId, origin, target: "item" }
        : { origin, target: "empty" },
    );
  }

  function clearQueue(origin: HTMLButtonElement) {
    if (!snapshot) {
      return;
    }
    persist(clearStudySession(snapshot.state, new Date().toISOString()));
    setConfirmClear(false);
    setFocusRequest({ origin, target: "empty" });
  }

  function requestClearQueue(origin: HTMLButtonElement) {
    setConfirmClear(true);
    setFocusRequest({ origin, target: "confirm" });
  }

  function cancelClearQueue(origin: HTMLButtonElement) {
    setConfirmClear(false);
    setFocusRequest({ origin, target: "clear" });
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

      {snapshot?.storageAvailable ? (
        <section
          ref={completionStatusRef}
          aria-atomic="true"
          aria-live="polite"
          className="outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2"
          data-testid="study-session-completion-status"
          tabIndex={-1}
        >
          {completionState === "error" ? (
            <div className="flex flex-col gap-3 border border-amber-300 bg-amber-50 p-3 sm:flex-row sm:items-center sm:justify-between" role="alert">
              <div>
                <p className="text-sm font-semibold text-amber-950">Completion status is unavailable.</p>
                <p className="mt-1 text-xs text-amber-900">{completionError}</p>
              </div>
              <button
                className="w-fit rounded border border-amber-700 bg-white px-3 py-2 text-sm font-semibold text-amber-950 hover:bg-amber-100"
                type="button"
                onClick={(event) => void refreshCompletion(event.currentTarget)}
              >
                Retry status
              </button>
            </div>
          ) : (
            <p className="border-y border-slate-200 py-3 text-sm text-slate-600" role="status">
              {completionState === "loading"
                ? "Refreshing canonical completion status..."
                : "Canonical completion status is available."}
            </p>
          )}
        </section>
      ) : null}

      {snapshot?.storageAvailable && snapshot.state.items.length === 0 ? (
        <WorkspaceState
          action={<Link ref={emptyRecoveryRef} className="text-sm font-semibold text-emerald-800 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700" href="/library">Browse saved learning</Link>}
          detail="Add readable Articles from Saved Learning to assemble a focused session."
          testId="study-session-empty"
          title="Your study queue is empty"
          tone="empty"
        />
      ) : null}

      {snapshot?.storageAvailable && snapshot.state.items.length > 0 ? (
        <>
          <section className="grid gap-px overflow-hidden border border-slate-200 bg-slate-200 sm:grid-cols-2 lg:grid-cols-4" data-testid="study-session-summary">
            <div className="bg-white p-4">
              <p className="text-xs font-medium text-slate-500">Queue</p>
              <p className="mt-1 text-2xl font-semibold text-slate-950">
                {snapshot.state.items.length} {snapshot.state.items.length === 1 ? "Article" : "Articles"}
              </p>
            </div>
            <div className="bg-white p-4">
              <p className="text-xs font-medium text-slate-500">Completed</p>
              <p className="mt-1 text-2xl font-semibold text-slate-950">
                {completion?.completedCount ?? "—"}
              </p>
            </div>
            <div className="bg-white p-4">
              <p className="text-xs font-medium text-slate-500">Remaining</p>
              <p className="mt-1 text-2xl font-semibold text-slate-950">
                {completion?.remainingCount ?? "—"}
              </p>
            </div>
            <div className="bg-white p-4">
              <p className="text-xs font-medium text-slate-500">Current position</p>
              <p className="mt-1 text-2xl font-semibold text-slate-950">
                {activePosition ? `${activePosition.index + 1} of ${activePosition.total}` : "Not set"}
              </p>
            </div>
          </section>

          {completion?.isComplete === true ? (
            <div className="border-l-4 border-emerald-700 bg-emerald-50 px-4 py-3" data-testid="study-session-complete" role="status">
              <p className="font-semibold text-emerald-950">Focused Session complete</p>
              <p className="mt-1 text-sm text-emerald-900">All queued Articles are complete. They remain available for review.</p>
            </div>
          ) : completion?.nextIncomplete ? (
            <p className="border-l-4 border-sky-700 bg-sky-50 px-4 py-3 text-sm text-sky-950" data-testid="study-session-next">
              Next unfinished: <span className="font-semibold">{completion.nextIncomplete.title}</span>
            </p>
          ) : null}

          {activePosition ? (
            <Link
              aria-label={`${completion?.current?.status === "completed" ? "Review" : "Continue"} current Article: ${activePosition.current.title}`}
              className="flex min-w-0 items-center justify-between gap-4 border-l-4 border-emerald-700 bg-emerald-50 px-4 py-3 text-emerald-950 hover:bg-emerald-100"
              href={createStudySessionReaderHref(activePosition.current)}
            >
              <span className="min-w-0">
                <span className="block text-xs font-semibold uppercase">
                  {completion?.current?.status === "completed" ? "Review current Article" : "Continue current Article"}
                </span>
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
                      ref={confirmClearButtonRef}
                      className="rounded border border-red-700 bg-red-700 px-3 py-2 text-sm font-semibold text-white hover:bg-red-800"
                      type="button"
                      onClick={(event) => clearQueue(event.currentTarget)}
                    >
                      Confirm clear queue
                    </button>
                    <button
                      className="rounded border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-slate-500"
                      type="button"
                      onClick={(event) => cancelClearQueue(event.currentTarget)}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    ref={clearQueueButtonRef}
                    className="rounded border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-800 hover:border-red-600"
                    type="button"
                    onClick={(event) => requestClearQueue(event.currentTarget)}
                  >
                    Clear queue
                  </button>
                )}
              </div>
            </div>

            <ol className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
              {snapshot.state.items.map((item, index) => {
                const isCurrent = item.articleId === snapshot.state.activeArticleId;
                const completionItem = completion?.items.find((entry) => entry.item.articleId === item.articleId);
                return (
                  <li className="min-w-0 py-4" data-testid="study-session-item" key={item.articleId}>
                    <div className="flex min-w-0 flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div className="flex min-w-0 items-start gap-3">
                        <span className="flex size-8 shrink-0 items-center justify-center rounded border border-slate-300 text-sm font-semibold text-slate-600">
                          {index + 1}
                        </span>
                        <div className="min-w-0">
                          <Link
                            ref={(node) => {
                              if (node) {
                                itemLinkRefs.current.set(item.articleId, node);
                              } else {
                                itemLinkRefs.current.delete(item.articleId);
                              }
                            }}
                            className="break-words text-base font-semibold text-slate-950 hover:underline focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
                            href={createStudySessionReaderHref(item)}
                          >
                            {item.title}
                          </Link>
                          <p className={`mt-1 text-xs font-semibold ${isCurrent ? "text-emerald-800" : "text-slate-500"}`}>
                            {isCurrent ? "Current" : "Queued"} · {completionLabel(completionItem?.status ?? "unknown")}
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
                          onClick={(event) => moveItem(item, -1, event.currentTarget)}
                        >
                          <span aria-hidden="true">&#8593;</span>
                        </button>
                        <button
                          aria-label={`Move ${item.title} down`}
                          className="flex size-10 items-center justify-center rounded border border-slate-300 bg-white text-lg text-slate-700 hover:border-slate-500 disabled:cursor-not-allowed disabled:text-slate-300"
                          disabled={index === snapshot.state.items.length - 1}
                          title="Move down"
                          type="button"
                          onClick={(event) => moveItem(item, 1, event.currentTarget)}
                        >
                          <span aria-hidden="true">&#8595;</span>
                        </button>
                        <button
                          aria-label={`Set ${item.title} as current`}
                          className="rounded border border-emerald-300 bg-white px-3 py-2 text-sm font-semibold text-emerald-900 hover:border-emerald-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
                          disabled={isCurrent}
                          type="button"
                          onClick={(event) => setCurrent(item, event.currentTarget)}
                        >
                          Set current
                        </button>
                        <button
                          aria-label={`Remove ${item.title} from session`}
                          className="rounded border border-red-300 bg-white px-3 py-2 text-sm font-semibold text-red-800 hover:border-red-600"
                          type="button"
                          onClick={(event) => removeItem(item, event.currentTarget)}
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

function completionLabel(status: "unread" | "reading" | "completed" | "unknown"): string {
  if (status === "completed") {
    return "Completed";
  }
  if (status === "reading") {
    return "Reading";
  }
  if (status === "unread") {
    return "Unread";
  }
  return "Status unavailable";
}
