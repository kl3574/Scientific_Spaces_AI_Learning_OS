"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  ArticleListRequest,
  ArticleMetadata,
  ArticleSummary,
  fetchArticles,
  formatMetadata,
} from "@/lib/articles";
import { toPlainTextPreview } from "@/lib/articlePresentation";
import { Bookmark, LearningState, fetchBookmarks, fetchLearningStates } from "@/lib/learning";
import {
  ArticleListSort,
  ArticleListState,
  createArticleDetailHref,
  createArticleListHref,
} from "@/lib/learningWorkflow";
import { WorkspaceState } from "@/components/WorkspaceState";

type LoadState = "idle" | "loading" | "loaded" | "error";

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
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [totalPages, setTotalPages] = useState(0);
  const [states, setStates] = useState<Record<string, LearningState>>({});
  const [bookmarks, setBookmarks] = useState<Record<string, Bookmark>>({});
  const [status, setStatus] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadArticles();
  }, [appliedQuery, page, sort]);

  useEffect(() => {
    const href = createArticleListHref({ q: appliedQuery, sort, page });
    window.history.replaceState(null, "", href);
  }, [appliedQuery, page, sort]);

  useEffect(() => {
    void loadLearningBadges();
  }, []);

  async function loadArticles() {
    setStatus("loading");
    setError(null);
    try {
      const request: ArticleListRequest = {
        q: appliedQuery,
        page,
        page_size: PAGE_SIZE,
        sort,
      };
      const response = await fetchArticles(request);
      setArticles(response.items);
      setTotal(response.total);
      setHasNext(response.has_next);
      setHasPrevious(response.has_previous);
      setTotalPages(response.total_pages);
      setStatus("loaded");
    } catch (err) {
      setArticles([]);
      setTotal(0);
      setHasNext(false);
      setHasPrevious(false);
      setTotalPages(0);
      setError(err instanceof Error ? err.message : "Failed to load articles");
      setStatus("error");
    }
  }

  async function loadLearningBadges() {
    try {
      const [stateResponse, bookmarkResponse] = await Promise.all([fetchLearningStates(), fetchBookmarks()]);
      setStates(Object.fromEntries(stateResponse.items.map((item) => [item.article_id, item])));
      setBookmarks(Object.fromEntries(bookmarkResponse.items.map((item) => [item.article_id, item])));
    } catch {
      setStates({});
      setBookmarks({});
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setAppliedQuery(query.trim());
  }

  function clearSearch() {
    setQuery("");
    setAppliedQuery("");
    setPage(1);
  }

  function getSummaryLabel(metadata: ArticleMetadata) {
    const refs = metadata.references?.length ?? 0;
    const imgs = metadata.images?.length ?? 0;
    const pieces = [formatMetadata(metadata), `${refs} references`, `${imgs} images`].filter((part) => Boolean(part));
    return pieces.join(" · ");
  }

  function getRangeLabel() {
    if (!total) {
      return "No results";
    }
    const from = (page - 1) * PAGE_SIZE + 1;
    const to = Math.min(page * PAGE_SIZE, total);
    return `Showing ${from}-${to} of ${total}`;
  }

  const listHref = createArticleListHref({ q: appliedQuery, sort, page });

  return (
    <section className="min-w-0 max-w-full space-y-5">
      <header className="border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-semibold">Article List</h1>
          <p className="mt-1 text-sm text-slate-600">Search Scientific Spaces articles by title or keyword.</p>
          <p className="mt-2 text-xs text-slate-500">{status === "loaded" ? getRangeLabel() : ""}</p>
        </div>
        <form className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_180px_auto_auto] sm:items-end" onSubmit={handleSubmit}>
          <label className="grid min-w-0 gap-1 text-xs font-medium text-slate-600">
            Search
            <input
              className="min-w-0 rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none"
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
              className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none"
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
          <button className="rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800" type="submit">
            Search
          </button>
          <button
            className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:border-slate-500 disabled:cursor-not-allowed disabled:text-slate-300"
            disabled={!query && !appliedQuery}
            type="button"
            onClick={clearSearch}
          >
            Clear
          </button>
        </form>
      </header>

      {status === "loading" ? (
        <WorkspaceState title="Loading articles" tone="loading" />
      ) : null}
      {status === "error" ? (
        <WorkspaceState detail={error} title="Article library unavailable" tone="error" />
      ) : null}
      {status === "loaded" ? (
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm text-slate-600">
            Page {page} / {Math.max(totalPages, 1)}
          </p>
          <div className="flex gap-2">
            <button
              className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
              disabled={!hasPrevious}
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              Previous
            </button>
            <button
              className="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
              disabled={!hasNext}
              type="button"
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </div>
        </div>
      ) : null}

      {status === "loaded" && total === 0 ? (
        <WorkspaceState title="No articles found." tone="empty" />
      ) : null}

      <div className="min-w-0 max-w-full divide-y divide-slate-200 border-y border-slate-200">
        {articles.map((article) => (
          <article key={article.id} className="min-w-0 max-w-full overflow-hidden py-4">
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
                    {states[article.id]?.status ?? "unread"}
                  </span>
                  {bookmarks[article.id] ? (
                    <span className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">Bookmarked</span>
                  ) : null}
                </div>
              </div>
              <a
                className="shrink-0 text-xs font-medium text-emerald-800 hover:text-emerald-950"
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
          </article>
        ))}
      </div>
    </section>
  );
}
