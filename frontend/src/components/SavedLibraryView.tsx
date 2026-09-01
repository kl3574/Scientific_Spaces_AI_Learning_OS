"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { WorkspaceState } from "@/components/WorkspaceState";
import { loadReaderProgressItems } from "@/lib/articleWorkspace";
import {
  fetchBookmarks,
  fetchLearningStates,
  fetchLearningStats,
  type Bookmark,
  type LearningState,
  type RecentLearningArticle,
} from "@/lib/learning";
import { loadReadingHistory, type ReadingHistoryItem } from "@/lib/readingHistory";
import {
  buildSavedLibrary,
  createSavedLibraryHref,
  createSavedLibraryReaderHref,
  selectSavedLibraryItems,
  type SavedLibraryItem,
  type SavedLibrarySort,
  type SavedLibraryState,
  type SavedLibraryView as SavedLibraryViewId,
} from "@/lib/savedLibrary";

type RemoteState = "loading" | "loaded" | "partial" | "error";

const VIEW_OPTIONS: ReadonlyArray<{ id: SavedLibraryViewId; label: string }> = [
  { id: "all", label: "All" },
  { id: "continue", label: "Continue" },
  { id: "bookmarked", label: "Saved" },
  { id: "recent", label: "Recent" },
];

export function SavedLibraryView({ initialState }: Readonly<{ initialState: SavedLibraryState }>) {
  const [state, setState] = useState(initialState);
  const [queryDraft, setQueryDraft] = useState(initialState.q);
  const [states, setStates] = useState<LearningState[]>([]);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [history, setHistory] = useState<ReadingHistoryItem[]>([]);
  const [progressItems, setProgressItems] = useState(() => [] as ReturnType<typeof loadReaderProgressItems>);
  const [recentArticles, setRecentArticles] = useState<RecentLearningArticle[]>([]);
  const [remoteState, setRemoteState] = useState<RemoteState>("loading");
  const [remoteErrors, setRemoteErrors] = useState<string[]>([]);

  useEffect(() => {
    setHistory(loadReadingHistory());
    setProgressItems(loadReaderProgressItems());
    void loadRemoteRecords();
  }, []);

  useEffect(() => {
    window.history.replaceState(null, "", createSavedLibraryHref(state));
  }, [state]);

  async function loadRemoteRecords() {
    setRemoteState("loading");
    setRemoteErrors([]);
    const results = await Promise.allSettled([
      fetchLearningStates(),
      fetchBookmarks(),
      fetchLearningStats(),
    ]);
    const errors: string[] = [];

    if (results[0].status === "fulfilled") {
      setStates(results[0].value.items);
    } else {
      errors.push(errorMessage(results[0].reason, "Learning states are unavailable"));
    }
    if (results[1].status === "fulfilled") {
      setBookmarks(results[1].value.items);
    } else {
      errors.push(errorMessage(results[1].reason, "Bookmarks are unavailable"));
    }
    if (results[2].status === "fulfilled") {
      setRecentArticles(results[2].value.recent_articles);
    } else {
      errors.push(errorMessage(results[2].reason, "Recent learning activity is unavailable"));
    }

    setRemoteErrors(errors);
    setRemoteState(errors.length === 0 ? "loaded" : errors.length === results.length ? "error" : "partial");
  }

  const model = useMemo(
    () => buildSavedLibrary({ states, bookmarks, history, progressItems, recentArticles }),
    [bookmarks, history, progressItems, recentArticles, states],
  );
  const visibleItems = useMemo(() => selectSavedLibraryItems(model.items, state), [model.items, state]);
  const sections = useMemo(() => createSections(model.items, visibleItems, state), [model.items, state, visibleItems]);
  const hasVisibleItems = sections.some((section) => section.items.length > 0);

  function applyQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState((current) => ({ ...current, q: queryDraft }));
  }

  function clearQuery() {
    setQueryDraft("");
    setState((current) => ({ ...current, q: "" }));
  }

  return (
    <section
      aria-busy={remoteState === "loading"}
      className="min-w-0 space-y-5 md:space-y-7"
      data-testid="saved-library-workspace"
    >
      <header className="border-b border-slate-200 pb-5">
        <p className="text-xs font-semibold uppercase text-emerald-800">Personal learning workspace</p>
        <div className="mt-1 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Saved Learning Library</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Resume active reading, revisit saved Articles, and recover recent study positions.
            </p>
          </div>
          <Link className="w-fit text-sm font-semibold text-emerald-800 hover:text-emerald-950" href="/articles">
            Browse all articles
          </Link>
        </div>
      </header>

      <LibrarySummary model={model} />

      <RemoteStatus
        errors={remoteErrors}
        hasLocalResults={model.items.length > 0}
        state={remoteState}
        onRetry={loadRemoteRecords}
      />

      <section aria-label="Library controls" className="space-y-4 border-y border-slate-200 py-4">
        <div aria-label="Saved learning view" className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap" role="group">
          {VIEW_OPTIONS.map((option) => (
            <button
              aria-pressed={state.view === option.id}
              className={`min-h-10 rounded border px-3 py-2 text-sm font-semibold ${
                state.view === option.id
                  ? "border-slate-950 bg-slate-950 text-white"
                  : "border-slate-300 bg-white text-slate-700 hover:border-slate-500"
              }`}
              key={option.id}
              type="button"
              onClick={() => setState((current) => ({ ...current, view: option.id }))}
            >
              {option.label} ({model.counts[option.id]})
            </button>
          ))}
        </div>

        <form className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem_auto_auto] sm:items-end" onSubmit={applyQuery}>
          <label className="grid min-w-0 gap-1 text-xs font-medium text-slate-600">
            Filter saved learning
            <input
              className="min-w-0 rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none"
              maxLength={120}
              placeholder="Title, section, or status"
              type="search"
              value={queryDraft}
              onChange={(event) => setQueryDraft(event.target.value)}
            />
          </label>
          <label className="grid gap-1 text-xs font-medium text-slate-600">
            Sort
            <select
              aria-label="Sort saved learning"
              className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none"
              value={state.sort}
              onChange={(event) => setState((current) => ({ ...current, sort: event.target.value as SavedLibrarySort }))}
            >
              <option value="recent">Recent activity</option>
              <option value="title">Title</option>
              <option value="progress">Progress</option>
            </select>
          </label>
          <button className="rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800" type="submit">
            Filter
          </button>
          <button
            className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-slate-500 disabled:cursor-not-allowed disabled:text-slate-300"
            disabled={!queryDraft && !state.q}
            type="button"
            onClick={clearQuery}
          >
            Clear
          </button>
        </form>
      </section>

      {remoteState === "error" && model.items.length === 0 ? (
        <WorkspaceState
          action={<RetryButton onRetry={loadRemoteRecords} />}
          detail={remoteErrors.slice(0, 3).join(" · ")}
          testId="saved-library-unavailable"
          title="Saved learning is unavailable"
          tone="unavailable"
        />
      ) : null}

      {remoteState !== "loading" && model.items.length === 0 && remoteState !== "error" ? (
        <WorkspaceState
          action={
            <Link className="text-sm font-semibold text-emerald-800 hover:text-emerald-950" href="/articles">
              Browse articles
            </Link>
          }
          detail="Open or save an Article to begin building this workspace."
          testId="saved-library-empty"
          title="No saved learning yet"
          tone="empty"
        />
      ) : null}

      {model.items.length > 0 && !hasVisibleItems ? (
        <WorkspaceState
          action={state.q ? <button className="text-sm font-semibold text-emerald-800" type="button" onClick={clearQuery}>Clear filter</button> : null}
          detail="Try another view or a shorter title, section, or status filter."
          testId="saved-library-no-results"
          title="No matching saved learning"
          tone="empty"
        />
      ) : null}

      {hasVisibleItems ? (
        <div className="space-y-7" data-testid="saved-library-sections">
          {sections.map((section) => (
            <LibrarySection key={section.id} section={section} state={state} />
          ))}
        </div>
      ) : null}

      {model.unavailableCount > 0 || model.truncatedCount > 0 ? (
        <aside className="border-t border-slate-200 pt-4 text-xs leading-5 text-slate-500" data-testid="saved-library-bounds">
          {model.unavailableCount > 0 ? (
            <p>{model.unavailableCount} record{model.unavailableCount === 1 ? "" : "s"} could not be shown because no readable Article title was available.</p>
          ) : null}
          {model.truncatedCount > 0 ? (
            <p>{model.truncatedCount} older record{model.truncatedCount === 1 ? "" : "s"} were omitted by the 100-item workspace limit.</p>
          ) : null}
        </aside>
      ) : null}
    </section>
  );
}

function LibrarySummary({ model }: Readonly<{ model: ReturnType<typeof buildSavedLibrary> }>) {
  const metrics = [
    { label: "Readable", value: model.counts.all },
    { label: "In progress", value: model.counts.continue },
    { label: "Saved", value: model.counts.bookmarked },
    { label: "Recent", value: model.counts.recent },
  ];
  return (
    <dl className="grid grid-cols-2 gap-px overflow-hidden border border-slate-200 bg-slate-200 sm:grid-cols-4" data-testid="saved-library-summary">
      {metrics.map((metric) => (
        <div className="min-w-0 bg-white p-4" key={metric.label}>
          <dt className="text-xs font-medium text-slate-500">{metric.label}</dt>
          <dd className="mt-1 text-2xl font-semibold text-slate-950">{metric.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function RemoteStatus({
  errors,
  hasLocalResults,
  state,
  onRetry,
}: Readonly<{
  errors: string[];
  hasLocalResults: boolean;
  state: RemoteState;
  onRetry: () => void;
}>) {
  if (state === "loaded") {
    return null;
  }
  if (state === "loading") {
    return <WorkspaceState title="Refreshing saved learning" tone="loading" />;
  }
  if (state === "error" && !hasLocalResults) {
    return null;
  }
  return (
    <WorkspaceState
      action={<RetryButton onRetry={onRetry} />}
      detail={errors.slice(0, 3).join(" · ")}
      testId="saved-library-remote-state"
      title={state === "partial" ? "Some saved-learning data is unavailable" : "Remote saved-learning data is unavailable"}
      tone="unavailable"
    />
  );
}

function RetryButton({ onRetry }: Readonly<{ onRetry: () => void }>) {
  return (
    <button className="rounded border border-amber-700 bg-white px-3 py-2 text-sm font-semibold text-amber-950 hover:bg-amber-100" type="button" onClick={onRetry}>
      Retry
    </button>
  );
}

type LibrarySectionModel = {
  id: SavedLibraryViewId;
  title: string;
  detail: string;
  items: SavedLibraryItem[];
};

function createSections(
  allItems: SavedLibraryItem[],
  visibleItems: SavedLibraryItem[],
  state: SavedLibraryState,
): LibrarySectionModel[] {
  const definitions: Array<Omit<LibrarySectionModel, "items">> = [
    { id: "continue", title: "Continue Learning", detail: "Return to active Articles and the last meaningful section." },
    { id: "bookmarked", title: "Bookmarked", detail: "Articles deliberately saved for another study session." },
    { id: "recent", title: "Recently Read", detail: "Recent Article activity recovered from local and learning history." },
  ];
  if (state.view === "all") {
    return definitions.map((definition) => ({
      ...definition,
      items: selectSavedLibraryItems(allItems, { ...state, view: definition.id }),
    }));
  }
  const definition = definitions.find((candidate) => candidate.id === state.view);
  if (!definition) {
    return [{ id: "all", title: "Saved Learning", detail: "All readable saved-learning records.", items: visibleItems }];
  }
  return [{ ...definition, items: visibleItems }];
}

function LibrarySection({ section, state }: Readonly<{ section: LibrarySectionModel; state: SavedLibraryState }>) {
  if (section.items.length === 0) {
    return null;
  }
  return (
    <section aria-labelledby={`saved-library-${section.id}`} className="min-w-0 border-t-2 border-emerald-700 pt-4" data-testid={`saved-library-section-${section.id}`}>
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold" id={`saved-library-${section.id}`}>{section.title}</h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">{section.detail}</p>
        </div>
        <span className="shrink-0 text-xs font-semibold text-slate-500">{section.items.length}</span>
      </div>
      <div className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
        {section.items.map((item) => <LibraryItem item={item} key={item.articleId} state={state} />)}
      </div>
    </section>
  );
}

function LibraryItem({ item, state }: Readonly<{ item: SavedLibraryItem; state: SavedLibraryState }>) {
  const href = createSavedLibraryReaderHref(item.articleId, state, item.sectionId);
  const progressLabel = item.progress > 0 ? `${item.progress}% read` : "Ready to read";
  return (
    <article className="min-w-0 py-4" data-article-id={item.articleId} data-testid="saved-library-item">
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <Link className="break-words text-base font-semibold text-slate-950 hover:underline" href={href}>
            {item.title}
          </Link>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <span className="rounded border border-slate-200 px-2 py-1 text-slate-600">{statusLabel(item.status)}</span>
            {item.isBookmarked ? <span className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-amber-900">Saved</span> : null}
            {item.sectionTitle ? <span className="max-w-full truncate rounded border border-slate-200 px-2 py-1 text-slate-600">{item.sectionTitle}</span> : null}
          </div>
        </div>
        <div className="flex shrink-0 items-center justify-between gap-4 sm:block sm:text-right">
          <p className="text-sm font-semibold text-slate-800">{progressLabel}</p>
          <p className="mt-1 text-xs text-slate-500">{formatActivity(item)}</p>
        </div>
      </div>
      <div aria-label={`${item.title} progress`} aria-valuemax={100} aria-valuemin={0} aria-valuenow={item.progress} className="mt-3 h-1.5 overflow-hidden bg-slate-200" role="progressbar">
        <span className="block h-full bg-emerald-700" style={{ width: `${item.progress}%` }} />
      </div>
    </article>
  );
}

function statusLabel(status: SavedLibraryItem["status"]): string {
  return status === "completed" ? "Completed" : status === "reading" ? "Reading" : "Unread";
}

function formatActivity(item: SavedLibraryItem): string {
  const value = item.lastReadAt ?? item.savedAt;
  if (!value) {
    return "No recent activity";
  }
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}
