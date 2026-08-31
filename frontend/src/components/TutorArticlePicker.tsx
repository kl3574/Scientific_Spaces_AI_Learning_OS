"use client";

import { FormEvent, useRef, useState } from "react";

import { fetchArticles, formatMetadata, type ArticleSummary } from "@/lib/articles";
import {
  MAX_TUTOR_ARTICLE_RESULTS,
  createTutorArticleSelection,
  type TutorArticleSelection,
} from "@/lib/tutorWorkspace";

type SearchStatus = "idle" | "loading" | "ready" | "error";

export function TutorArticlePicker({
  selected,
  onSelect,
}: Readonly<{
  selected: TutorArticleSelection | null;
  onSelect: (article: TutorArticleSelection | null) => void;
}>) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ArticleSummary[]>([]);
  const [status, setStatus] = useState<SearchStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  async function search(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const currentRequest = requestId.current + 1;
    requestId.current = currentRequest;
    setStatus("loading");
    setError(null);
    try {
      const response = await fetchArticles({
        q: query.trim() || undefined,
        page: 1,
        page_size: MAX_TUTOR_ARTICLE_RESULTS,
        sort: query.trim() ? "relevance" : "date_desc",
      });
      if (requestId.current !== currentRequest) {
        return;
      }
      setResults(response.items.slice(0, MAX_TUTOR_ARTICLE_RESULTS));
      setStatus("ready");
    } catch (reason) {
      if (requestId.current !== currentRequest) {
        return;
      }
      setStatus("error");
      setError(reason instanceof Error ? reason.message : "Article search failed.");
    }
  }

  return (
    <section className="border-y border-slate-200 bg-white px-4 py-4" aria-labelledby="tutor-article-context">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-base font-semibold" id="tutor-article-context">Article context</h2>
          <p className="mt-1 text-sm text-slate-600">Choose a local Article by title or keyword.</p>
        </div>
        {selected ? (
          <button
            className="w-fit text-sm font-medium text-slate-600 underline underline-offset-4 hover:text-slate-950"
            onClick={() => onSelect(null)}
            type="button"
          >
            Clear article context
          </button>
        ) : null}
      </div>

      {selected ? (
        <div className="mt-3 border-l-4 border-emerald-600 bg-emerald-50 px-3 py-2" data-testid="tutor-selected-article">
          <p className="break-words text-sm font-semibold text-emerald-950">{selected.title}</p>
          <p className="mt-1 text-xs text-emerald-800">{formatMetadata(selected.metadata)}</p>
        </div>
      ) : null}

      <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={search}>
        <label className="min-w-0 flex-1 text-sm">
          <span className="sr-only">Search articles</span>
          <input
            className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-950"
            aria-label="Search articles"
            placeholder="Search Article title or keyword"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <button
          className="shrink-0 rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={status === "loading"}
          type="submit"
        >
          {status === "loading" ? "Searching..." : "Search library"}
        </button>
      </form>

      {status === "error" ? (
        <div className="mt-3 flex flex-wrap items-center gap-3" role="alert">
          <p className="text-sm text-red-700">{error ?? "Article search failed."}</p>
          <button className="text-sm font-semibold text-red-800 underline" onClick={() => void search()} type="button">
            Retry search
          </button>
        </div>
      ) : null}

      {status === "ready" ? (
        <div className="mt-3" data-testid="tutor-article-results">
          {results.length ? (
            <ul className="grid gap-2 sm:grid-cols-2" aria-label="Article search results">
              {results.map((article) => (
                <li key={article.id}>
                  <button
                    className="h-full w-full rounded border border-slate-200 px-3 py-3 text-left hover:border-emerald-700 hover:bg-emerald-50"
                    aria-label={`Select ${article.title}`}
                    onClick={() => onSelect(createTutorArticleSelection(article))}
                    type="button"
                  >
                    <span className="block break-words text-sm font-semibold text-slate-900">{article.title}</span>
                    <span className="mt-1 block text-xs text-slate-500">{formatMetadata(article.metadata)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-600">No matching Articles.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}
