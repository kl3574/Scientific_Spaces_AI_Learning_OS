"use client";

import Link from "next/link";
import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";

import { WorkspaceState } from "@/components/WorkspaceState";
import { toPlainTextPreview } from "@/lib/articlePresentation";
import {
  createArticleSessionCapturePlan,
  formatArticleSessionCaptureOutcome,
  getArticleLearningStatusLabel,
  ownsArticleResultGeneration,
  reconcileArticleSelection,
  updateArticleSelection,
} from "@/lib/articleSessionPlanning";
import {
  ArticleListRequest,
  ArticleMetadata,
  ArticleSummary,
  fetchArticles,
  formatMetadata,
} from "@/lib/articles";
import { Bookmark, LearningState, fetchBookmarks, fetchLearningStates } from "@/lib/learning";
import {
  ArticleListSort,
  ArticleListState,
  createArticleDetailHref,
  createArticleListHref,
} from "@/lib/learningWorkflow";
import {
  STUDY_SESSION_CHANGE_EVENT,
  STUDY_SESSION_ITEM_LIMIT,
  STUDY_SESSION_STORAGE_KEY,
  loadStudySession,
  saveStudySession,
  type StudySessionLoadResult,
} from "@/lib/studySession";

type LoadState = "idle" | "loading" | "loaded" | "error";

type ArticlePageSnapshot = {
  requestKey: string;
  status: LoadState;
  articles: ArticleSummary[];
  total: number;
  hasNext: boolean;
  hasPrevious: boolean;
  totalPages: number;
  error: string | null;
};

type LearningBadgeSnapshot = {
  status: LoadState;
  records: Record<string, LearningState>;
};

type BookmarkBadgeSnapshot = {
  status: LoadState;
  records: Record<string, Bookmark>;
};

type CaptureFeedback = {
  sequence: number;
  message: string;
  tone: "success" | "warning" | "error";
};

type BadgeRetryPhase = "idle" | "retrying" | "succeeded" | "failed";

const PAGE_SIZE = 20;

export function ArticleListView({
  initialState,
}: Readonly<{
  initialState: ArticleListState;
}>) {
  const [query, setQuery] = useState(initialState.q);
  const [appliedQuery, setAppliedQuery] = useState(initialState.q);
  const [sort, setSort] = useState<ArticleListSort>(initialState.sort);
  const [page, setPage] = useState(initialState.page);
  const [articlePage, setArticlePage] = useState<ArticlePageSnapshot>(() =>
    emptyArticlePage("", "idle"),
  );
  const [learningBadges, setLearningBadges] = useState<LearningBadgeSnapshot>({
    status: "idle",
    records: {},
  });
  const [bookmarkBadges, setBookmarkBadges] = useState<BookmarkBadgeSnapshot>({
    status: "idle",
    records: {},
  });
  const [learningRetryPhase, setLearningRetryPhase] = useState<BadgeRetryPhase>("idle");
  const [bookmarkRetryPhase, setBookmarkRetryPhase] = useState<BadgeRetryPhase>("idle");
  const [selectedArticleIds, setSelectedArticleIds] = useState<string[]>([]);
  const [studySession, setStudySession] = useState<StudySessionLoadResult | null>(null);
  const [captureFeedback, setCaptureFeedback] = useState<CaptureFeedback | null>(null);

  const articleRequestId = useRef(0);
  const learningRequestId = useRef(0);
  const bookmarkRequestId = useRef(0);
  const feedbackSequence = useRef(0);
  const badgeAvailabilityRef = useRef<HTMLElement>(null);
  const badgeFocusFrame = useRef<number | null>(null);
  const captureRegionRef = useRef<HTMLElement>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const feedbackFocusFrame = useRef<number | null>(null);

  const requestKey = useMemo(
    () => JSON.stringify([appliedQuery, sort, page]),
    [appliedQuery, page, sort],
  );

  const clearCaptureFeedback = useCallback(() => {
    const feedbackWasFocused =
      typeof document !== "undefined" && document.activeElement === feedbackRef.current;
    if (feedbackFocusFrame.current !== null) {
      window.cancelAnimationFrame(feedbackFocusFrame.current);
      feedbackFocusFrame.current = null;
    }
    setCaptureFeedback(null);
    if (feedbackWasFocused) {
      feedbackFocusFrame.current = window.requestAnimationFrame(() => {
        feedbackFocusFrame.current = null;
        captureRegionRef.current?.focus({ preventScroll: true });
      });
    }
  }, []);

  const focusBadgeAvailability = useCallback((onlyIfOwned = false) => {
    if (badgeFocusFrame.current !== null) {
      window.cancelAnimationFrame(badgeFocusFrame.current);
    }
    badgeFocusFrame.current = window.requestAnimationFrame(() => {
      badgeFocusFrame.current = null;
      const region = badgeAvailabilityRef.current;
      const active = document.activeElement;
      if (
        region
        && (!onlyIfOwned || active === region || active === document.body)
      ) {
        region.focus({ preventScroll: true });
      }
    });
  }, []);

  const loadArticles = useCallback(async () => {
    const requestId = articleRequestId.current + 1;
    articleRequestId.current = requestId;
    setSelectedArticleIds([]);
    clearCaptureFeedback();
    setArticlePage(emptyArticlePage(requestKey, "loading"));

    try {
      const request: ArticleListRequest = {
        q: appliedQuery,
        page,
        page_size: PAGE_SIZE,
        sort,
      };
      const response = await fetchArticles(request);
      if (!ownsArticleResultGeneration(requestId, articleRequestId.current)) {
        return;
      }
      setArticlePage({
        requestKey,
        status: "loaded",
        articles: response.items,
        total: response.total,
        hasNext: response.has_next,
        hasPrevious: response.has_previous,
        totalPages: response.total_pages,
        error: null,
      });
    } catch (reason) {
      if (!ownsArticleResultGeneration(requestId, articleRequestId.current)) {
        return;
      }
      setArticlePage({
        ...emptyArticlePage(requestKey, "error"),
        error: reason instanceof Error ? reason.message : "Failed to load articles",
      });
    }
  }, [appliedQuery, clearCaptureFeedback, page, requestKey, sort]);

  const loadLearningBadges = useCallback(async (isRetry = false) => {
    const requestId = learningRequestId.current + 1;
    learningRequestId.current = requestId;
    if (isRetry) {
      setLearningRetryPhase("retrying");
      focusBadgeAvailability();
    } else {
      setLearningRetryPhase("idle");
      setLearningBadges((current) => ({ ...current, status: "loading" }));
    }
    try {
      const response = await fetchLearningStates();
      if (requestId !== learningRequestId.current) {
        return;
      }
      setLearningBadges({
        status: "loaded",
        records: Object.fromEntries(response.items.map((item) => [item.article_id, item])),
      });
      if (isRetry) {
        setLearningRetryPhase("succeeded");
        focusBadgeAvailability(true);
      }
    } catch {
      if (requestId !== learningRequestId.current) {
        return;
      }
      setLearningBadges((current) => ({ ...current, status: "error" }));
      if (isRetry) {
        setLearningRetryPhase("failed");
        focusBadgeAvailability(true);
      }
    }
  }, [focusBadgeAvailability]);

  const loadBookmarkBadges = useCallback(async (isRetry = false) => {
    const requestId = bookmarkRequestId.current + 1;
    bookmarkRequestId.current = requestId;
    if (isRetry) {
      setBookmarkRetryPhase("retrying");
      focusBadgeAvailability();
    } else {
      setBookmarkRetryPhase("idle");
      setBookmarkBadges((current) => ({ ...current, status: "loading" }));
    }
    try {
      const response = await fetchBookmarks();
      if (requestId !== bookmarkRequestId.current) {
        return;
      }
      setBookmarkBadges({
        status: "loaded",
        records: Object.fromEntries(response.items.map((item) => [item.article_id, item])),
      });
      if (isRetry) {
        setBookmarkRetryPhase("succeeded");
        focusBadgeAvailability(true);
      }
    } catch {
      if (requestId !== bookmarkRequestId.current) {
        return;
      }
      setBookmarkBadges((current) => ({ ...current, status: "error" }));
      if (isRetry) {
        setBookmarkRetryPhase("failed");
        focusBadgeAvailability(true);
      }
    }
  }, [focusBadgeAvailability]);

  useEffect(() => {
    void loadArticles();
  }, [loadArticles]);

  useEffect(() => {
    const href = createArticleListHref({ q: appliedQuery, sort, page });
    window.history.replaceState(null, "", href);
  }, [appliedQuery, page, sort]);

  useEffect(() => {
    void loadLearningBadges();
    void loadBookmarkBadges();
  }, [loadBookmarkBadges, loadLearningBadges]);

  useEffect(() => {
    function refreshStudySession() {
      clearCaptureFeedback();
      setStudySession(loadStudySession());
    }
    function handleStorage(event: StorageEvent) {
      if (event.key === null || event.key === STUDY_SESSION_STORAGE_KEY) {
        refreshStudySession();
      }
    }

    refreshStudySession();
    window.addEventListener(STUDY_SESSION_CHANGE_EVENT, refreshStudySession);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener(STUDY_SESSION_CHANGE_EVENT, refreshStudySession);
      window.removeEventListener("storage", handleStorage);
    };
  }, [clearCaptureFeedback]);

  useEffect(() => {
    return () => {
      articleRequestId.current += 1;
      learningRequestId.current += 1;
      bookmarkRequestId.current += 1;
      if (badgeFocusFrame.current !== null) {
        window.cancelAnimationFrame(badgeFocusFrame.current);
      }
      if (feedbackFocusFrame.current !== null) {
        window.cancelAnimationFrame(feedbackFocusFrame.current);
      }
    };
  }, []);

  const effectiveStatus = articlePage.requestKey === requestKey ? articlePage.status : "loading";
  const visibleArticles = effectiveStatus === "loaded" ? articlePage.articles : [];
  const selectedVisibleIds = useMemo(
    () => reconcileArticleSelection(visibleArticles, selectedArticleIds),
    [selectedArticleIds, visibleArticles],
  );
  const queuedArticleIds = useMemo(
    () => new Set(
      studySession?.storageAvailable
        ? studySession.state.items.map((item) => item.articleId)
        : [],
    ),
    [studySession],
  );
  const listHref = createArticleListHref({ q: appliedQuery, sort, page });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuery = query.trim();
    if (nextQuery === appliedQuery && page === 1) {
      void loadArticles();
      return;
    }
    setPage(1);
    setAppliedQuery(nextQuery);
  }

  function clearSearch() {
    setQuery("");
    if (!appliedQuery && page === 1) {
      void loadArticles();
      return;
    }
    setAppliedQuery("");
    setPage(1);
  }

  function announceCapture(message: string, tone: CaptureFeedback["tone"]) {
    feedbackSequence.current += 1;
    setCaptureFeedback({ sequence: feedbackSequence.current, message, tone });
    if (feedbackFocusFrame.current !== null) {
      window.cancelAnimationFrame(feedbackFocusFrame.current);
    }
    feedbackFocusFrame.current = window.requestAnimationFrame(() => {
      feedbackFocusFrame.current = null;
      feedbackRef.current?.focus({ preventScroll: true });
      feedbackRef.current?.scrollIntoView({ block: "nearest" });
    });
  }

  function captureSelectedArticles() {
    const selected = reconcileArticleSelection(visibleArticles, selectedArticleIds);
    if (!selected.length) {
      announceCapture("Select at least one Article from the current results.", "warning");
      return;
    }

    const reloaded = loadStudySession();
    setStudySession(reloaded);
    if (!reloaded.storageAvailable) {
      announceCapture("Browser-local storage is unavailable. No Articles were added.", "error");
      return;
    }

    const plan = createArticleSessionCapturePlan(
      visibleArticles,
      selected,
      reloaded.state,
      new Date().toISOString(),
    );
    const outcome = formatArticleSessionCaptureOutcome(plan.mutation.outcomes);

    if (plan.requiresSave && !saveStudySession(plan.mutation.state)) {
      setStudySession(reloaded);
      announceCapture(
        "Focused Session storage failed. No changes were saved. Selection is ready to retry.",
        "error",
      );
      return;
    }

    setStudySession(plan.requiresSave ? {
      ...reloaded,
      state: plan.mutation.state,
      recovered: false,
      droppedCount: 0,
      truncatedCount: 0,
    } : reloaded);
    setSelectedArticleIds(plan.remainingSelectionIds);
    const queueCount = plan.mutation.state.items.length;
    const hasUnresolved = plan.remainingSelectionIds.length > 0;
    announceCapture(
      `${outcome} Focused Session contains ${queueCount} of ${STUDY_SESSION_ITEM_LIMIT} Articles.`,
      hasUnresolved || plan.mutation.outcomes.added === 0 ? "warning" : "success",
    );
  }

  function retryStudySessionStatus() {
    const refreshed = loadStudySession();
    setStudySession(refreshed);
    if (!refreshed.storageAvailable) {
      announceCapture("Browser-local Focused Session storage remains unavailable.", "error");
      return;
    }
    announceCapture(
      `Focused Session status is available with ${refreshed.state.items.length} of ${STUDY_SESSION_ITEM_LIMIT} Articles.`,
      refreshed.recovered ? "warning" : "success",
    );
  }

  function selectVisiblePage() {
    setSelectedArticleIds(reconcileArticleSelection(
      visibleArticles,
      visibleArticles.map((article) => article.id),
    ));
  }

  function getSummaryLabel(metadata: ArticleMetadata) {
    const refs = metadata.references?.length ?? 0;
    const imgs = metadata.images?.length ?? 0;
    return [formatMetadata(metadata), `${refs} references`, `${imgs} images`]
      .filter(Boolean)
      .join(" · ");
  }

  function getRangeLabel() {
    if (!articlePage.total) {
      return "No results";
    }
    const from = (page - 1) * PAGE_SIZE + 1;
    const to = Math.min(page * PAGE_SIZE, articlePage.total);
    return `Showing ${from}-${to} of ${articlePage.total}`;
  }

  return (
    <section className="min-w-0 max-w-full space-y-5" data-testid="article-discovery-workspace">
      <header className="border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-semibold">Article List</h1>
          <p className="mt-1 text-sm text-slate-600">Search Scientific Spaces articles by title or keyword.</p>
          <p className="mt-2 text-xs text-slate-500">
            {effectiveStatus === "loaded" ? getRangeLabel() : ""}
          </p>
        </div>
        <form className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px_auto_auto] sm:items-end" onSubmit={handleSubmit}>
          <label className="grid min-w-0 gap-1 text-xs font-medium text-slate-600">
            Search
            <input
              className="min-w-0 rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none focus:border-slate-950"
              name="q"
              placeholder="Search title or keyword"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label className="grid gap-1 text-xs font-medium text-slate-600">
            Sort
            <select
              className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none focus:border-slate-950"
              value={sort}
              onChange={(event) => {
                setSort(event.target.value as ArticleListSort);
                setPage(1);
              }}
            >
              <option value="date_desc">Newest date</option>
              <option value="archive_desc">Newest archive</option>
              <option value="title_asc">Title A-Z</option>
              <option value="relevance">Relevance</option>
            </select>
          </label>
          <button className="min-h-10 rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800" type="submit">
            Search
          </button>
          <button
            className="min-h-10 rounded border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:border-slate-500 disabled:cursor-not-allowed disabled:text-slate-300"
            disabled={!query && !appliedQuery}
            type="button"
            onClick={clearSearch}
          >
            Clear
          </button>
        </form>
      </header>

      <BadgeAvailability
        availabilityRef={badgeAvailabilityRef}
        bookmarkRetryPhase={bookmarkRetryPhase}
        bookmarkStatus={bookmarkBadges.status}
        learningRetryPhase={learningRetryPhase}
        learningStatus={learningBadges.status}
        onRetryBookmarks={() => void loadBookmarkBadges(true)}
        onRetryLearning={() => void loadLearningBadges(true)}
      />

      {effectiveStatus === "loading" ? <WorkspaceState title="Loading articles" tone="loading" /> : null}
      {effectiveStatus === "error" ? (
        <WorkspaceState
          action={<RetryButton label="Retry articles" onRetry={() => void loadArticles()} />}
          detail={articlePage.error}
          title="Article library unavailable"
          tone="error"
        />
      ) : null}

      {effectiveStatus === "loaded" ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-slate-600">
            Page {page} / {Math.max(articlePage.totalPages, 1)}
          </p>
          <div className="flex gap-2">
            <button
              className="min-h-10 rounded border border-slate-300 px-3 py-1.5 text-xs font-medium disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
              disabled={!articlePage.hasPrevious}
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              Previous
            </button>
            <button
              className="min-h-10 rounded border border-slate-300 px-3 py-1.5 text-xs font-medium disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
              disabled={!articlePage.hasNext}
              type="button"
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </div>
        </div>
      ) : null}

      {effectiveStatus === "loaded" && articlePage.total === 0 ? (
        <WorkspaceState title="No articles found." tone="empty" />
      ) : null}

      <section
        ref={captureRegionRef}
        aria-label="Focused Session capture"
        aria-busy={studySession === null}
        className="min-w-0 border-y border-slate-200 bg-white py-4 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-700"
        data-testid="article-session-capture"
        tabIndex={-1}
      >
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold">Build a Focused Session</h2>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              {selectedVisibleIds.length} selected on this page · {formatStudySessionAvailability(studySession)}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="min-h-10 rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 hover:border-slate-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
              disabled={!visibleArticles.length}
              type="button"
              onClick={selectVisiblePage}
            >
              Select page
            </button>
            <button
              className="min-h-10 rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 hover:border-slate-600 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
              disabled={!selectedVisibleIds.length}
              type="button"
              onClick={() => setSelectedArticleIds([])}
            >
              Clear selection
            </button>
            <button
              className="min-h-10 rounded bg-slate-950 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={!selectedVisibleIds.length}
              type="button"
              onClick={captureSelectedArticles}
            >
              Add selected to session
            </button>
            <Link className="min-h-10 py-2 text-xs font-semibold text-emerald-800 hover:text-emerald-950 hover:underline" href="/session">
              Open Focused Session
            </Link>
            {studySession && !studySession.storageAvailable ? (
              <button
                className="min-h-10 rounded border border-amber-400 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-950 hover:border-amber-700"
                type="button"
                onClick={retryStudySessionStatus}
              >
                Retry session status
              </button>
            ) : null}
          </div>
        </div>
        {studySession?.recovered ? (
          <p className="mt-3 text-xs leading-5 text-amber-900">
            Focused Session recovered valid entries from browser storage.
          </p>
        ) : null}
        <div
          ref={feedbackRef}
          aria-atomic="true"
          aria-live="polite"
          className={captureFeedback ? captureFeedbackClass(captureFeedback.tone) : "sr-only"}
          data-testid="article-session-capture-feedback"
          tabIndex={-1}
        >
          <p key={captureFeedback?.sequence}>{captureFeedback?.message ?? ""}</p>
        </div>
      </section>

      <div className="min-w-0 max-w-full divide-y divide-slate-200 border-y border-slate-200">
        {visibleArticles.map((article) => {
          const selected = selectedVisibleIds.includes(article.id);
          const queued = queuedArticleIds.has(article.id);
          return (
            <article key={article.id} className="grid min-w-0 max-w-full grid-cols-[auto_minmax(0,1fr)] gap-3 overflow-hidden py-4">
              <label className="flex min-h-11 items-start pt-0.5">
                <input
                  aria-label={`Select ${article.title} for focused session`}
                  checked={selected}
                  className="h-5 w-5"
                  type="checkbox"
                  onChange={(event) => setSelectedArticleIds((current) =>
                    updateArticleSelection(visibleArticles, current, article.id, event.target.checked),
                  )}
                />
              </label>
              <div className="min-w-0">
                <div className="flex min-w-0 flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <Link
                      className="break-words text-base font-semibold text-slate-950 hover:underline"
                      href={createArticleDetailHref(article.id, listHref)}
                    >
                      {article.title}
                    </Link>
                    <p className="mt-1 break-words text-xs text-slate-500">{getSummaryLabel(article.metadata)}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <span className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600">
                        {getArticleLearningStatusLabel(learningBadgeAvailability(learningBadges.status), learningBadges.records, article.id)}
                      </span>
                      {bookmarkBadges.status === "loaded" && bookmarkBadges.records[article.id] ? (
                        <span className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">Bookmarked</span>
                      ) : null}
                      {queued ? (
                        <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-900">In session</span>
                      ) : null}
                    </div>
                  </div>
                  <a
                    className="w-fit shrink-0 text-xs font-medium text-emerald-800 hover:text-emerald-950"
                    href={article.url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Open source
                  </a>
                </div>
                <p data-testid="article-preview" className="mt-3 line-clamp-3 break-words text-sm leading-6 text-slate-700">
                  {toPlainTextPreview(article.content_preview)}
                </p>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function emptyArticlePage(requestKey: string, status: LoadState): ArticlePageSnapshot {
  return {
    requestKey,
    status,
    articles: [],
    total: 0,
    hasNext: false,
    hasPrevious: false,
    totalPages: 0,
    error: null,
  };
}

function learningBadgeAvailability(status: LoadState): "loading" | "loaded" | "error" {
  return status === "loaded" ? "loaded" : status === "error" ? "error" : "loading";
}

function formatStudySessionAvailability(session: StudySessionLoadResult | null): string {
  if (session === null) {
    return "Focused Session status loading";
  }
  if (!session.storageAvailable) {
    return "Focused Session unavailable";
  }
  return `${session.state.items.length}/${STUDY_SESSION_ITEM_LIMIT} in session`;
}

function captureFeedbackClass(tone: CaptureFeedback["tone"]): string {
  if (tone === "error") {
    return "mt-3 border-l-2 border-red-600 bg-red-50 px-3 py-2 text-sm leading-6 text-red-900 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-red-600";
  }
  if (tone === "warning") {
    return "mt-3 border-l-2 border-amber-600 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-950 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-amber-600";
  }
  return "mt-3 border-l-2 border-emerald-600 bg-emerald-50 px-3 py-2 text-sm leading-6 text-emerald-950 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-emerald-600";
}

function BadgeAvailability({
  availabilityRef,
  learningStatus,
  bookmarkStatus,
  learningRetryPhase,
  bookmarkRetryPhase,
  onRetryLearning,
  onRetryBookmarks,
}: Readonly<{
  availabilityRef: RefObject<HTMLElement | null>;
  learningStatus: LoadState;
  bookmarkStatus: LoadState;
  learningRetryPhase: BadgeRetryPhase;
  bookmarkRetryPhase: BadgeRetryPhase;
  onRetryLearning: () => void;
  onRetryBookmarks: () => void;
}>) {
  const showLearning = learningStatus === "error" || learningRetryPhase !== "idle";
  const showBookmark = bookmarkStatus === "error" || bookmarkRetryPhase !== "idle";
  if (!showLearning && !showBookmark) {
    return null;
  }

  return (
    <section
      ref={availabilityRef}
      aria-atomic="true"
      aria-busy={learningRetryPhase === "retrying" || bookmarkRetryPhase === "retrying"}
      aria-label="Article badge availability"
      className="grid gap-2 border-y border-amber-200 bg-amber-50 py-3 focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-amber-700"
      data-testid="article-badge-availability"
      role="status"
      tabIndex={-1}
    >
      {showLearning ? (
        <div className="flex flex-wrap items-center justify-between gap-2 px-3">
          <p className="text-sm text-amber-950">
            {badgeRetryMessage("Learning", learningRetryPhase)}
          </p>
          {learningStatus === "error" ? (
            <RetryButton
              disabled={learningRetryPhase === "retrying"}
              label="Retry learning status"
              onRetry={onRetryLearning}
            />
          ) : null}
        </div>
      ) : null}
      {showBookmark ? (
        <div className="flex flex-wrap items-center justify-between gap-2 px-3">
          <p className="text-sm text-amber-950">
            {badgeRetryMessage("Saved", bookmarkRetryPhase)}
          </p>
          {bookmarkStatus === "error" ? (
            <RetryButton
              disabled={bookmarkRetryPhase === "retrying"}
              label="Retry saved status"
              onRetry={onRetryBookmarks}
            />
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function badgeRetryMessage(
  subject: "Learning" | "Saved",
  phase: BadgeRetryPhase,
): string {
  if (phase === "retrying") {
    return `${subject} status retry in progress. Article rows remain unavailable.`;
  }
  if (phase === "succeeded") {
    return `${subject} status is available.`;
  }
  if (phase === "failed") {
    return `${subject} status remains unavailable. Retry is available.`;
  }
  return subject === "Learning"
    ? "Learning status is unavailable. Article rows do not assume unread."
    : "Saved status is unavailable. Learning status remains independent.";
}

function RetryButton({
  disabled = false,
  label,
  onRetry,
}: Readonly<{ disabled?: boolean; label: string; onRetry: () => void }>) {
  return (
    <button
      aria-busy={disabled}
      className="min-h-10 rounded border border-slate-400 bg-white px-3 py-2 text-xs font-semibold text-slate-800 hover:border-slate-700 disabled:cursor-wait disabled:border-slate-300 disabled:text-slate-500"
      disabled={disabled}
      type="button"
      onClick={onRetry}
    >
      {label}
    </button>
  );
}
