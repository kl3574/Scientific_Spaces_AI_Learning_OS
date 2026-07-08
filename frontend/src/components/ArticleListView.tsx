"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { ArticleSummary, fetchArticles, formatMetadata } from "@/lib/articles";
import { Bookmark, LearningState, fetchBookmarks, fetchLearningStates } from "@/lib/learning";

type LoadState = "idle" | "loading" | "loaded" | "error";

export function ArticleListView() {
  const [query, setQuery] = useState("");
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [states, setStates] = useState<Record<string, LearningState>>({});
  const [bookmarks, setBookmarks] = useState<Record<string, Bookmark>>({});
  const [status, setStatus] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadArticles();
    void loadLearningBadges();
  }, []);

  async function loadArticles(nextQuery = query) {
    setStatus("loading");
    setError(null);
    try {
      const response = await fetchArticles(nextQuery);
      setArticles(response.items);
      setStatus("loaded");
    } catch (err) {
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
    void loadArticles(query);
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 border-b border-slate-200 pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Article List</h1>
          <p className="mt-1 text-sm text-slate-600">Search Scientific Spaces articles by title or keyword.</p>
        </div>
        <form className="flex w-full max-w-xl gap-2" onSubmit={handleSubmit}>
          <input
            className="min-w-0 flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-950"
            name="q"
            placeholder="Search title or keyword"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white" type="submit">
            Search
          </button>
        </form>
      </div>

      {status === "loading" ? <p className="text-sm text-slate-600">Loading articles...</p> : null}
      {status === "error" ? <p className="text-sm text-red-700">{error}</p> : null}
      {status === "loaded" && articles.length === 0 ? (
        <p className="text-sm text-slate-600">No articles found.</p>
      ) : null}

      <div className="grid gap-3">
        {articles.map((article) => (
          <article key={article.id} className="rounded border border-slate-200 bg-white p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <Link className="text-base font-semibold text-slate-950 hover:underline" href={`/articles/${article.id}`}>
                  {article.title}
                </Link>
                <p className="mt-1 text-xs text-slate-500">{formatMetadata(article.metadata)}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600">
                    {states[article.id]?.status ?? "unread"}
                  </span>
                  {bookmarks[article.id] ? (
                    <span className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                      Bookmarked
                    </span>
                  ) : null}
                </div>
              </div>
              <a
                className="text-xs text-slate-500 hover:text-slate-950"
                href={article.url}
                rel="noreferrer"
                target="_blank"
              >
                Source
              </a>
            </div>
            <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-700">{article.content_preview}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
