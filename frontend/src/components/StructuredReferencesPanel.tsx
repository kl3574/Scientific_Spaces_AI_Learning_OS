"use client";

import { useEffect, useState } from "react";

import {
  ReferencePage,
  ReferenceRecord,
  fetchArticleReferences,
  referenceErrorMessage,
  referenceHref,
} from "@/lib/references";

const PAGE_SIZE = 20;

export function StructuredReferencesPanel({ articleId }: Readonly<{ articleId: string }>) {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ReferencePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    fetchArticleReferences(articleId, { page, pageSize: PAGE_SIZE })
      .then((response) => {
        if (active) {
          setData(response);
        }
      })
      .catch((reason) => {
        if (active) {
          setError(referenceErrorMessage(reason));
          setData(null);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [articleId, page]);

  return (
    <section className="mt-8 border-t border-slate-200 pt-6" aria-labelledby="structured-references-heading">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="structured-references-heading" className="text-lg font-semibold">
          Structured References
        </h2>
        {data ? <span className="text-xs text-slate-500">{data.total} records</span> : null}
      </div>

      {loading ? <p className="mt-4 text-sm text-slate-600">Loading references...</p> : null}
      {error ? (
        <p className="mt-4 border-l-2 border-amber-500 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {error}
        </p>
      ) : null}
      {!loading && !error && data?.items.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">No structured references for this article.</p>
      ) : null}

      {data?.items.length ? (
        <ul className="mt-4 divide-y divide-slate-200 border-y border-slate-200">
          {data.items.map((record) => (
            <li key={record.reference_id} className="py-4">
              <ReferenceRow record={record} />
            </li>
          ))}
        </ul>
      ) : null}

      {data && data.total_pages > 1 ? (
        <nav className="mt-4 flex items-center justify-between gap-3" aria-label="Reference pages">
          <button
            className="border border-slate-300 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={!data.has_previous}
            type="button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            Previous
          </button>
          <span className="text-xs text-slate-500">
            Page {data.page} of {data.total_pages}
          </span>
          <button
            className="border border-slate-300 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={!data.has_next}
            type="button"
            onClick={() => setPage((current) => current + 1)}
          >
            Next
          </button>
        </nav>
      ) : null}
    </section>
  );
}

function ReferenceRow({ record }: Readonly<{ record: ReferenceRecord }>) {
  const href = referenceHref(record);
  const identity = record.normalized_identifier ?? record.normalized_url ?? record.evidence_text;

  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="border border-slate-300 px-2 py-1 font-medium uppercase text-slate-700">
          {record.reference_type.replaceAll("_", " ")}
        </span>
        <span className="text-slate-500">{record.classification}</span>
        {record.source_count > 1 ? <span className="text-slate-500">{record.source_count} sources</span> : null}
      </div>
      <p className="mt-2 break-words text-sm font-medium text-slate-900">
        {href ? (
          <a className="underline underline-offset-2 hover:text-sky-700" href={href} rel="noopener noreferrer" target="_blank">
            {identity}
          </a>
        ) : (
          identity
        )}
      </p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{record.evidence_text}</p>
      <p className="mt-2 text-xs text-slate-500">
        Section: {record.source_section || "Article root"}
      </p>
    </div>
  );
}
