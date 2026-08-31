"use client";

import type { TutorSession } from "@/lib/tutor";
import { buildTutorActivity } from "@/lib/tutorWorkspace";

export function TutorActivity({
  sessions,
  articleTitles,
  status,
  error,
  onRetry,
}: Readonly<{
  sessions: TutorSession[];
  articleTitles: Readonly<Record<string, string>>;
  status: "idle" | "loading" | "loaded" | "error";
  error: string | null;
  onRetry: () => void;
}>) {
  const activity = buildTutorActivity(sessions, articleTitles);
  return (
    <section className="border-t border-slate-300 pt-5" data-testid="tutor-activity">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold">Recent tutor activity</h2>
          <p className="mt-1 text-sm text-slate-600">Latest local study modes and Article context.</p>
        </div>
        {status === "loading" ? <span className="text-xs text-slate-500">Loading...</span> : null}
      </div>
      {status === "error" ? (
        <div className="mt-3 flex flex-wrap items-center gap-3" role="alert">
          <p className="text-sm text-red-700">{error ?? "Failed to load tutor activity."}</p>
          <button className="text-sm font-semibold text-red-800 underline" onClick={onRetry} type="button">Retry activity</button>
        </div>
      ) : null}
      {activity.length ? (
        <ol className="mt-4 grid gap-3 sm:grid-cols-2">
          {activity.map((item) => (
            <li key={item.key} className="border-l-4 border-slate-300 bg-white px-3 py-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase text-emerald-800">{item.modeLabel}</span>
                <time className="text-xs text-slate-500">{item.updatedAt}</time>
              </div>
              <p className="mt-2 break-words text-sm font-semibold text-slate-900">{item.articleTitle}</p>
              <p className="mt-1 break-words text-xs leading-5 text-slate-600">{item.prompt}</p>
            </li>
          ))}
        </ol>
      ) : status === "loaded" ? <p className="mt-3 text-sm text-slate-600">No tutor activity yet.</p> : null}
    </section>
  );
}
