"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ArticleListResponse, ArticleSummary, fetchArticles } from "@/lib/articles";
import { LearningStats, fetchLearningStats } from "@/lib/learning";
import { ReadingHistoryItem, loadReadingHistory } from "@/lib/readingHistory";

export function DashboardView() {
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [articleQuery, setArticleQuery] = useState<ArticleListResponse | null>(null);
  const [stats, setStats] = useState<LearningStats | null>(null);
  const [history, setHistory] = useState<ReadingHistoryItem[]>([]);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setHistory(loadReadingHistory());
    void loadDashboard();
  }, []);

  async function loadDashboard() {
    setStatus("loading");
    setError(null);
    try {
      const [articleResponse, learningStats] = await Promise.all([
        fetchArticles({ page: 1, page_size: 5, sort: "date_desc" }),
        fetchLearningStats(),
      ]);
      setArticleQuery(articleResponse);
      setArticles(articleResponse.items);
      setStats(learningStats);
      setStatus("loaded");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
      setStatus("error");
    }
  }

  if (status === "loading") {
    return <p className="text-sm text-slate-600">Loading dashboard...</p>;
  }

  if (status === "error") {
    return <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>;
  }

  const articleTotal = articleQuery?.total ?? 0;
  const metrics = [
    { label: "Articles", value: articleTotal },
    { label: "Reading", value: stats?.reading_count ?? 0 },
    { label: "Completed", value: stats?.completed_count ?? 0 },
    { label: "Bookmarks", value: stats?.bookmark_count ?? 0 },
    { label: "Notes", value: stats?.note_count ?? 0 },
    { label: "Unread", value: stats?.unread_count ?? 0 },
  ];

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold">Scientific Spaces AI Learning OS</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Read the local Scientific Spaces collection and continue your grounded learning workflow.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800" href="/articles">
            Browse articles
          </Link>
          <Link className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-slate-500" href="/tutor">
            Open tutor
          </Link>
        </div>
      </header>

      <dl data-testid="dashboard-stats" className="grid grid-cols-2 gap-px overflow-hidden border border-slate-200 bg-slate-200 sm:grid-cols-3 lg:grid-cols-6">
        {metrics.map((metric) => (
          <div key={metric.label} className="min-w-0 bg-white px-3 py-3">
            <dt className="text-xs font-medium text-slate-500">{metric.label}</dt>
            <dd className="mt-1 break-words text-2xl font-semibold text-slate-950">{metric.value}</dd>
          </div>
        ))}
      </dl>

      <section className="border-t-2 border-emerald-700 pt-4">
        <div className="flex items-end justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">Recent Articles</h2>
            <p className="mt-1 text-xs text-slate-500">
              {articleQuery ? `Showing ${articleQuery.items.length} of ${articleQuery.total}` : `Showing 0 of ${articleTotal}`}
            </p>
          </div>
          <Link className="text-sm font-medium text-emerald-800 hover:text-emerald-950" href="/articles">
            View all
          </Link>
        </div>
        <div className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
          {articles.length ? (
            articles.map((article) => (
              <Link key={article.id} className="block px-1 py-3 text-sm hover:bg-white" href={`/articles/${article.id}`}>
                <span className="block break-words font-medium">{article.title}</span>
                <span className="mt-1 block text-xs text-slate-500">{formatMetadata(article.metadata)}</span>
              </Link>
            ))
          ) : (
            <p className="py-3 text-sm text-slate-600">No articles available.</p>
          )}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="border-t border-slate-300 pt-4">
          <h2 className="text-base font-semibold">Recent Learning</h2>
          <div className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
          {stats?.recent_articles.length ? (
            stats.recent_articles.map((item) => (
              <Link
                key={`${item.article_id}-${item.updated_at ?? item.last_read_at}`}
                className="block py-3 text-sm hover:bg-white"
                href={`/articles/${item.article_id}`}
              >
                <span className="block font-medium">{item.title}</span>
                <span className="mt-1 block text-xs text-slate-500">
                  {item.status} · {formatDate(item.last_read_at ?? item.updated_at)}
                </span>
              </Link>
            ))
          ) : (
            <p className="text-sm text-slate-600">No learning activity yet.</p>
          )}
          </div>
        </section>

        <section className="border-t border-slate-300 pt-4">
          <h2 className="text-base font-semibold">Recent Sessions</h2>
          <div className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
          {stats?.recent_sessions.length ? (
            stats.recent_sessions.map((session) => (
              <Link
                key={session.session_id}
                className="block py-3 text-sm hover:bg-white"
                href={`/articles/${session.article_id}`}
              >
                <span className="block font-medium">{session.article_id}</span>
                <span className="mt-1 block text-xs text-slate-500">
                  {session.source} · {formatDate(session.started_at)}
                  {session.duration_seconds !== null ? ` · ${session.duration_seconds}s` : ""}
                </span>
              </Link>
            ))
          ) : (
            <p className="text-sm text-slate-600">No sessions yet.</p>
          )}
          </div>
        </section>

        <section className="border-t border-slate-300 pt-4">
          <h2 className="text-base font-semibold">Reading History</h2>
          <div className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
          {history.length ? (
            history.map((item) => (
              <Link
                key={`${item.id}-${item.last_read_at}`}
                className="block py-3 text-sm hover:bg-white"
                href={`/articles/${item.id}`}
              >
                <span className="block font-medium">{item.title}</span>
                <span className="mt-1 block text-xs text-slate-500">Last read at {new Date(item.last_read_at).toLocaleString()}</span>
              </Link>
            ))
          ) : (
            <p className="text-sm text-slate-600">No reading history yet.</p>
          )}
          </div>
        </section>
      </div>
    </section>
  );
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "No timestamp";
  }
  return new Date(value).toLocaleString();
}

function formatMetadataFromDate(value: string | null | undefined, category: string | null | undefined) {
  const parts = [value, category].filter(Boolean);
  return parts.length ? parts.join(" · ") : "No metadata";
}

function formatMetadata(metadata: { date?: string | null; category?: string | null }) {
  return formatMetadataFromDate(metadata.date, metadata.category);
}
