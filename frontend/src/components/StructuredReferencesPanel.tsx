"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState, type MouseEvent as ReactMouseEvent } from "react";

import { toPlainTextPreview } from "@/lib/articlePresentation";
import { recordShellDestinationFocusIntent } from "@/lib/navigation";
import {
  ReferencePage,
  ReferenceRecord,
  fetchArticleReferences,
  referenceErrorMessage,
  referenceHref,
} from "@/lib/references";
import {
  DEFAULT_REFERENCE_REVIEW_STATE,
  createArticleReferenceReturnPath,
  createReferenceReviewHref,
  rememberReferenceDetailFocus,
  referenceRowId,
} from "@/lib/referenceReview";

const PAGE_SIZE = 20;

export function StructuredReferencesPanel({ articleId }: Readonly<{ articleId: string }>) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const routePage = parseReferencePage(searchParams.get("reference_page"));
  const [page, setPage] = useState(routePage);
  const [data, setData] = useState<ReferencePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestKey, setRequestKey] = useState<string | null>(null);
  const currentRequestKey = `${articleId}:${page}`;

  useEffect(() => {
    setPage(routePage);
    setData(null);
  }, [articleId, routePage]);

  useEffect(() => {
    let active = true;
    const nextRequestKey = `${articleId}:${page}`;
    setRequestKey(nextRequestKey);
    setLoading(true);
    setError(null);
    setData(null);
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

  const requestIsCurrent = requestKey === currentRequestKey;
  const visibleData = requestIsCurrent ? data : null;
  const visibleError = requestIsCurrent ? error : null;
  const visibleLoading = !requestIsCurrent || loading;
  const loadState = visibleLoading
    ? "loading"
    : visibleError
      ? "error"
      : visibleData?.items.length
        ? "ready"
        : "empty";

  return (
    <section
      className="mt-8 border-t border-slate-200 pt-6"
      aria-busy={visibleLoading}
      aria-labelledby="structured-references-heading"
      data-structured-references-article-id={articleId}
      data-structured-references-page={page}
      data-structured-references-state={loadState}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="structured-references-heading" className="text-lg font-semibold">
          Structured References
        </h2>
        {visibleData ? <span className="text-xs text-slate-500">{visibleData.total} records</span> : null}
      </div>

      {visibleLoading ? <p className="mt-4 text-sm text-slate-600">Loading references...</p> : null}
      {visibleError ? (
        <p className="mt-4 border-l-2 border-amber-500 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {visibleError}
        </p>
      ) : null}
      {!visibleLoading && !visibleError && visibleData?.items.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">No structured references for this article.</p>
      ) : null}

      {visibleData?.items.length ? (
        <ul className="mt-4 divide-y divide-slate-200 border-y border-slate-200">
          {visibleData.items.map((record) => (
            <li
              key={record.reference_id}
              id={referenceRowId(record.reference_id)}
              className="scroll-mt-24 py-4 outline-none focus:ring-2 focus:ring-sky-600 focus:ring-offset-4"
              data-reference-id={record.reference_id}
              tabIndex={-1}
            >
              <ReferenceRow
                record={record}
                reviewHref={createReferenceReviewHref({
                  ...DEFAULT_REFERENCE_REVIEW_STATE,
                  referenceId: record.reference_id,
                  returnTo: createArticleReferenceReturnPath({
                    articleId,
                    referenceId: record.reference_id,
                    referencePage: page,
                    currentArticlePath: `${pathname}${searchParams.size ? `?${searchParams.toString()}` : ""}`,
                  }),
                })}
              />
            </li>
          ))}
        </ul>
      ) : null}

      {visibleData && visibleData.total_pages > 1 ? (
        <nav className="mt-4 flex items-center justify-between gap-3" aria-label="Reference pages">
          <button
            className="border border-slate-300 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={!visibleData.has_previous}
            type="button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            Previous
          </button>
          <span className="text-xs text-slate-500">
            Page {visibleData.page} of {visibleData.total_pages}
          </span>
          <button
            className="border border-slate-300 px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-slate-400"
            disabled={!visibleData.has_next}
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

function ReferenceRow({
  record,
  reviewHref,
}: Readonly<{
  record: ReferenceRecord;
  reviewHref: string;
}>) {
  const href = referenceHref(record);
  const identity = record.normalized_identifier ?? record.normalized_url ?? record.evidence_text;
  const reviewLabel = toPlainTextPreview(identity, 120) || "unidentified reference";

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
      <p className="mt-2 break-words text-sm leading-6 text-slate-600 [overflow-wrap:anywhere]">
        {record.evidence_text}
      </p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-slate-500">
          Section: {record.source_section || "Article root"}
        </p>
        <Link
          className="border border-slate-300 px-3 py-2 text-xs font-medium text-slate-800 hover:border-slate-950 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
          href={reviewHref}
          aria-label={`Review Zotero candidates for ${reviewLabel}`}
          onClick={(event) => rememberReviewFocus(event, record.reference_id)}
        >
          Review candidates
        </Link>
      </div>
    </div>
  );
}

function parseReferencePage(value: string | null): number {
  const page = Number.parseInt(value ?? "", 10);
  return Number.isSafeInteger(page) && page > 0 ? Math.min(page, 100_000) : 1;
}

function rememberReviewFocus(event: ReactMouseEvent<HTMLAnchorElement>, referenceId: string): void {
  if (
    event.button === 0
    && !event.altKey
    && !event.ctrlKey
    && !event.metaKey
    && !event.shiftKey
    && event.currentTarget.target !== "_blank"
  ) {
    recordShellDestinationFocusIntent(event.currentTarget.href, window.location.href);
    rememberReferenceDetailFocus(referenceId);
  }
}
