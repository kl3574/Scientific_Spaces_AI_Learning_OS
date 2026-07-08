"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ArticleSummary, fetchArticles, formatMetadata } from "@/lib/articles";
import { LearningStats, fetchLearningStats } from "@/lib/learning";
import { ReadingHistoryItem, loadReadingHistory } from "@/lib/readingHistory";

export function DashboardView() {
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [stats, setStats] = useState<LearningStats | null>(null);
  const [history, setHistory] = useState<ReadingHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setHistory(loadReadingHistory());
    Promise.all([fetchArticles(), fetchLearningStats()])
      .then(([articleResponse, learningStats]) => {
        setArticles(articleResponse.items);
        setStats(learningStats);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load articles"));
  }, []);

  const recentArticles = useMemo(
    () =>
      [...articles]
        .sort((left, right) => String(right.metadata.date ?? "").localeCompare(String(left.metadata.date ?? "")))
        .slice(0, 5),
    [articles],
  );

  return (
    <section className="space-y-6">
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-3xl font-semibold">Scientific Spaces AI Learning OS</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Browse, search, and read the frozen M1 Scientific Spaces article collection.
        </p>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <div className="grid gap-4 md:grid-cols-3">
        <section className="rounded border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Articles</p>
          <p className="mt-2 text-3xl font-semibold">{stats?.total_articles ?? articles.length}</p>
        </section>
        <section className="rounded border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Reading</p>
          <p className="mt-2 text-3xl font-semibold">{stats?.reading_count ?? 0}</p>
        </section>
        <section className="rounded border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Completed</p>
          <p className="mt-2 text-3xl font-semibold">{stats?.completed_count ?? 0}</p>
        </section>
        <section className="rounded border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Bookmarks</p>
          <p className="mt-2 text-3xl font-semibold">{stats?.bookmark_count ?? 0}</p>
        </section>
        <section className="rounded border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Notes</p>
          <p className="mt-2 text-3xl font-semibold">{stats?.note_count ?? 0}</p>
        </section>
        <section className="rounded border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Unread</p>
          <p className="mt-2 text-3xl font-semibold">{stats?.unread_count ?? articles.length}</p>
        </section>
        <section className="rounded border border-slate-200 bg-white p-4 md:col-span-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold">Recent Articles</h2>
            <Link className="text-sm text-slate-600 hover:text-slate-950" href="/articles">
              View all
            </Link>
          </div>
          <div className="mt-3 grid gap-2">
            {recentArticles.length ? (
              recentArticles.map((article) => (
                <Link
                  key={article.id}
                  className="rounded border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50"
                  href={`/articles/${article.id}`}
                >
                  <span className="block font-medium">{article.title}</span>
                  <span className="mt-1 block text-xs text-slate-500">{formatMetadata(article.metadata)}</span>
                </Link>
              ))
            ) : (
              <p className="text-sm text-slate-600">No articles available.</p>
            )}
          </div>
        </section>
      </div>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold">Recent Learning</h2>
        <div className="mt-3 grid gap-2">
          {stats?.recent_articles.length ? (
            stats.recent_articles.map((item) => (
              <Link
                key={`${item.article_id}-${item.updated_at ?? item.last_read_at}`}
                className="rounded border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50"
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

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold">Recent Sessions</h2>
        <div className="mt-3 grid gap-2">
          {stats?.recent_sessions.length ? (
            stats.recent_sessions.map((session) => (
              <Link
                key={session.session_id}
                className="rounded border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50"
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

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold">Reading History</h2>
        <div className="mt-3 grid gap-2">
          {history.length ? (
            history.map((item) => (
              <Link
                key={`${item.id}-${item.last_read_at}`}
                className="rounded border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50"
                href={`/articles/${item.id}`}
              >
                <span className="block font-medium">{item.title}</span>
                <span className="mt-1 block text-xs text-slate-500">
                  Last read at {new Date(item.last_read_at).toLocaleString()}
                </span>
              </Link>
            ))
          ) : (
            <p className="text-sm text-slate-600">No reading history yet.</p>
          )}
        </div>
      </section>
    </section>
  );
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "No timestamp";
  }
  return new Date(value).toLocaleString();
}
