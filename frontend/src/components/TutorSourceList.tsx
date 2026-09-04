"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import type { TutorSource } from "@/lib/tutor";
import {
  MAX_RENDERED_TUTOR_SOURCES,
  getBoundedSourceRows,
  getSafeDisplayText,
  getSafeExternalUrl,
  getSourceDisclosure,
  resolveSourceArticleId,
} from "@/lib/tutorPresentation";

const DEFAULT_SOURCE_PREVIEW = 3;

export function TutorSourceList({
  sources,
  compact = false,
  title = "来源",
  maxSources = MAX_RENDERED_TUTOR_SOURCES,
  maxVisible = DEFAULT_SOURCE_PREVIEW,
}: Readonly<{
  sources: TutorSource[];
  compact?: boolean;
  title?: string;
  maxSources?: number;
  maxVisible?: number;
}>) {
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    setExpanded(false);
  }, [sources]);

  const bounded = useMemo(
    () => getBoundedSourceRows(sources, { maxSources, maxVisible, expanded }),
    [sources, expanded, maxSources, maxVisible],
  );
  const disclosure = getSourceDisclosure(bounded, { expanded, maxVisible });

  return (
    <section className={compact ? "mt-3 min-w-0" : "min-w-0 border-y border-slate-200 bg-white py-4"}>
      <h2 className="text-base font-semibold">{title}</h2>
      <div className="mt-3 grid min-w-0 gap-2">
        {!sources.length ? <p className="text-sm text-slate-600">未返回来源。</p> : null}
        {bounded.visibleSources.map((source) => {
          const safeTitle = getSafeDisplayText(source.title) ?? "未命名来源";
          const safeSourceType = getSafeDisplayText(source.source_type) ?? "source";
          const safeSectionTitle = getSafeDisplayText(source.section_title);
          const articleId = resolveSourceArticleId(source);
          const externalUrl = getSafeExternalUrl(source.url);
          return (
            <article key={`${source.source_type}-${source.source_id}`} className="min-w-0 max-w-full rounded border border-slate-200 bg-white p-3 text-xs sm:text-sm">
              <p className="break-words font-medium [overflow-wrap:anywhere]">{safeTitle}</p>
              <p className="mt-1 break-words text-[11px] text-slate-500 [overflow-wrap:anywhere]">
                {safeSourceType}
                {safeSectionTitle ? ` · ${safeSectionTitle}` : ""}
                {typeof source.chunk_index === "number" ? ` · chunk ${source.chunk_index}` : ""}
              </p>
              <div className="mt-2 flex min-w-0 flex-wrap gap-2">
                {articleId ? (
                  <Link className="inline-block max-w-full whitespace-normal break-words rounded border border-slate-200 px-2 py-1 text-xs text-slate-700 hover:border-slate-900" href={`/articles/${encodeURIComponent(articleId)}`}>
                    Open local article
                  </Link>
                ) : null}
                {externalUrl ? (
                  <a className="inline-block max-w-full whitespace-normal break-words rounded border border-slate-200 px-2 py-1 text-xs text-slate-700 hover:border-slate-900" href={externalUrl} rel="noreferrer" target="_blank">
                    Open original source
                  </a>
                ) : null}
              </div>
            </article>
          );
        })}
        {disclosure.omittedLabel ? <p className="text-xs leading-5 text-slate-500">{disclosure.omittedLabel}</p> : null}
        {disclosure.canToggle && disclosure.toggleLabel ? (
          <button className="w-fit rounded border border-slate-200 px-2 py-1 text-xs text-slate-700" onClick={() => setExpanded((current) => !current)} type="button">
            {disclosure.toggleLabel}
          </button>
        ) : null}
      </div>
    </section>
  );
}
