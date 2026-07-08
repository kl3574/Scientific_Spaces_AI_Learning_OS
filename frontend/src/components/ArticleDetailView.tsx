"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import { ArticleDetail, fetchArticle, formatMetadata } from "@/lib/articles";
import { ReadingHistoryItem, loadReadingHistory, recordReading } from "@/lib/readingHistory";

export function ArticleDetailView({ articleId }: Readonly<{ articleId: string }>) {
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [history, setHistory] = useState<ReadingHistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setHistory(loadReadingHistory());
    fetchArticle(articleId)
      .then((loadedArticle) => {
        setArticle(loadedArticle);
        setHistory(recordReading(loadedArticle));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load article"));
  }, [articleId]);

  if (error) {
    return (
      <section className="space-y-4">
        <Link className="text-sm text-slate-600 hover:text-slate-950" href="/articles">
          Back to articles
        </Link>
        <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>
      </section>
    );
  }

  if (!article) {
    return <p className="text-sm text-slate-600">Loading article...</p>;
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <article className="min-w-0 rounded border border-slate-200 bg-white p-5">
        <Link className="text-sm text-slate-600 hover:text-slate-950" href="/articles">
          Back to articles
        </Link>
        <h1 className="mt-4 text-2xl font-semibold leading-tight">{article.title}</h1>
        <p className="mt-2 text-sm text-slate-500">{formatMetadata(article.metadata)}</p>
        <a
          className="mt-2 inline-block text-sm text-slate-600 hover:text-slate-950"
          href={article.url}
          rel="noreferrer"
          target="_blank"
        >
          Source article
        </a>
        <div className="reader-markdown mt-6">
          <ReactMarkdown>{article.content}</ReactMarkdown>
        </div>
      </article>

      <aside className="space-y-4">
        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold">Metadata</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div>
              <dt className="text-slate-500">Date</dt>
              <dd>{article.metadata.date ?? "Unknown"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Category</dt>
              <dd>{article.metadata.category ?? "Unknown"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Images</dt>
              <dd>{article.metadata.images?.length ?? 0}</dd>
            </div>
            <div>
              <dt className="text-slate-500">References</dt>
              <dd>{article.metadata.references?.length ?? 0}</dd>
            </div>
          </dl>
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold">Recent Reading</h2>
          <div className="mt-3 grid gap-2">
            {history.length ? (
              history.slice(0, 5).map((item) => (
                <Link
                  key={`${item.id}-${item.last_read_at}`}
                  className="rounded border border-slate-100 px-3 py-2 text-sm hover:bg-slate-50"
                  href={`/articles/${item.id}`}
                >
                  <span className="block font-medium">{item.title}</span>
                  <span className="mt-1 block text-xs text-slate-500">
                    {new Date(item.last_read_at).toLocaleString()}
                  </span>
                </Link>
              ))
            ) : (
              <p className="text-sm text-slate-600">No reading history yet.</p>
            )}
          </div>
        </section>
      </aside>
    </section>
  );
}
