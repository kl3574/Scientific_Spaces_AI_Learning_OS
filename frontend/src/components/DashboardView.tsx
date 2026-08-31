"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ArticleListResponse, ArticleSummary, fetchArticles, formatMetadata } from "@/lib/articles";
import { ReaderProgressState, loadReaderProgressItems } from "@/lib/articleWorkspace";
import {
  DashboardActivityItem,
  createArticleTitleIndex,
  createDashboardOverview,
  buildDashboardActivity,
  selectContinueLearning,
} from "@/lib/dashboard";
import { LearningStats, fetchLearningStats } from "@/lib/learning";
import { ReadingHistoryItem, loadReadingHistory } from "@/lib/readingHistory";

type DashboardRemoteState = "loading" | "loaded" | "partial" | "error";

const NEXT_ACTIONS = [
  {
    href: "/articles",
    label: "Browse library",
    detail: "Find an article by title, keyword, category, or date.",
  },
  {
    href: "/tutor",
    label: "Ask tutor",
    detail: "Explain, derive, quiz, or research from local evidence.",
  },
  {
    href: "/graph",
    label: "Explore graph",
    detail: "Follow Articles, Sections, Concepts, and Formulas.",
  },
  {
    href: "/zotero",
    label: "Review sources",
    detail: "Inspect linked papers and Zotero metadata.",
  },
] as const;

export function DashboardView() {
  const [articleQuery, setArticleQuery] = useState<ArticleListResponse | null>(null);
  const [stats, setStats] = useState<LearningStats | null>(null);
  const [history, setHistory] = useState<ReadingHistoryItem[]>([]);
  const [progressItems, setProgressItems] = useState<ReaderProgressState[]>([]);
  const [remoteState, setRemoteState] = useState<DashboardRemoteState>("loading");
  const [remoteErrors, setRemoteErrors] = useState<string[]>([]);

  useEffect(() => {
    setHistory(loadReadingHistory());
    setProgressItems(loadReaderProgressItems());
    void loadDashboard();
  }, []);

  async function loadDashboard() {
    setRemoteState("loading");
    setRemoteErrors([]);
    const [articleResult, statsResult] = await Promise.allSettled([
      fetchArticles({ page: 1, page_size: 5, sort: "date_desc" }),
      fetchLearningStats(),
    ]);
    const errors: string[] = [];

    if (articleResult.status === "fulfilled") {
      setArticleQuery(articleResult.value);
    } else {
      errors.push(errorMessage(articleResult.reason, "Article library is unavailable"));
    }
    if (statsResult.status === "fulfilled") {
      setStats(statsResult.value);
    } else {
      errors.push(errorMessage(statsResult.reason, "Learning statistics are unavailable"));
    }

    setRemoteErrors(errors);
    setRemoteState(errors.length === 0 ? "loaded" : errors.length === 2 ? "error" : "partial");
  }

  const articles = articleQuery?.items ?? [];
  const overview = useMemo(
    () => createDashboardOverview(articleQuery?.total ?? null, stats),
    [articleQuery?.total, stats],
  );
  const titles = useMemo(
    () => createArticleTitleIndex(articles, stats, history),
    [articles, history, stats],
  );
  const continueItem = useMemo(
    () => selectContinueLearning(history, progressItems, titles),
    [history, progressItems, titles],
  );
  const activity = useMemo(
    () => buildDashboardActivity(stats, history, titles),
    [history, stats, titles],
  );

  return (
    <section
      aria-busy={remoteState === "loading"}
      className="min-w-0 space-y-5 md:space-y-7"
      data-testid="dashboard-command-center"
    >
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-emerald-800">Learning command center</p>
          <h1 className="mt-1 text-3xl font-semibold">Scientific Spaces AI Learning OS</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Resume focused study, review recent work, and move into the next local learning tool.
          </p>
        </div>
        <Link
          className="w-fit rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800"
          href="/articles"
        >
          Browse articles
        </Link>
      </header>

      <RemoteStatus state={remoteState} errors={remoteErrors} onRetry={loadDashboard} />

      <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(19rem,0.85fr)] lg:gap-7">
        <LearningOverview overview={overview} />
        <ContinueLearning item={continueItem} />
      </div>

      <NextActions />

      <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(19rem,0.85fr)] lg:gap-7">
        <LearningActivity items={activity} />
        <LatestArticles articles={articles} total={articleQuery?.total ?? null} />
      </div>
    </section>
  );
}

function RemoteStatus({
  state,
  errors,
  onRetry,
}: Readonly<{
  state: DashboardRemoteState;
  errors: string[];
  onRetry: () => void;
}>) {
  if (state === "loaded") {
    return null;
  }
  if (state === "loading") {
    return (
      <p className="border-y border-slate-200 py-3 text-sm text-slate-600" role="status">
        Refreshing learning overview...
      </p>
    );
  }
  return (
    <div
      className="flex flex-col gap-3 border border-amber-300 bg-amber-50 p-3 sm:flex-row sm:items-center sm:justify-between"
      data-testid="dashboard-remote-state"
      data-state={state}
      role="alert"
    >
      <div className="min-w-0">
        <p className="text-sm font-semibold text-amber-950">
          {state === "partial" ? "Some dashboard data is unavailable." : "Remote dashboard data is unavailable."}
        </p>
        <p className="mt-1 break-words text-xs text-amber-900">{errors.slice(0, 2).join(" · ")}</p>
      </div>
      <button
        className="w-fit shrink-0 rounded border border-amber-700 bg-white px-3 py-1.5 text-xs font-semibold text-amber-950 hover:bg-amber-100"
        type="button"
        onClick={onRetry}
      >
        Retry
      </button>
    </div>
  );
}

function LearningOverview({ overview }: Readonly<{ overview: ReturnType<typeof createDashboardOverview> }>) {
  const completionText = overview.completionPercent === null ? "Unavailable" : `${overview.completionPercent}%`;
  const metrics = [
    { label: "Library", value: overview.articleTotal },
    { label: "In progress", value: overview.readingCount },
    { label: "Saved", value: overview.bookmarkCount },
    { label: "Notes", value: overview.noteCount },
  ];

  return (
    <section aria-labelledby="learning-overview-title" className="min-w-0 border-t-2 border-emerald-700 pt-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold" id="learning-overview-title">Learning Overview</h2>
          <p className="mt-1 text-xs text-slate-500">
            {displayCount(overview.completedCount)} completed · {displayCount(overview.unreadCount)} unread
          </p>
        </div>
        <p className="text-right">
          <span className="block text-2xl font-semibold text-slate-950">{completionText}</span>
          <span className="block text-[11px] text-slate-500">complete</span>
        </p>
      </div>

      <div
        aria-label="Collection completion"
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={overview.completionPercent ?? undefined}
        aria-valuetext={overview.completionPercent === null ? "Completion unavailable" : completionText}
        className="mt-4 h-2 overflow-hidden bg-slate-200"
        role="progressbar"
      >
        <span
          className="block h-full bg-emerald-700"
          style={{ width: `${overview.completionPercent ?? 0}%` }}
        />
      </div>

      <dl
        className="mt-4 grid grid-cols-2 gap-px overflow-hidden border border-slate-200 bg-slate-200 sm:grid-cols-4"
        data-testid="dashboard-stats"
      >
        {metrics.map((metric) => (
          <div className="min-w-0 bg-white px-3 py-3" key={metric.label}>
            <dt className="text-xs font-medium text-slate-500">{metric.label}</dt>
            <dd className="mt-1 break-words text-xl font-semibold text-slate-950">{displayCount(metric.value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ContinueLearning({
  item,
}: Readonly<{ item: ReturnType<typeof selectContinueLearning> }>) {
  return (
    <section className="min-w-0 border-t-2 border-amber-500 pt-4" data-testid="continue-reading">
      <h2 className="text-base font-semibold">Continue Learning</h2>
      {item ? (
        <div className="mt-3 min-w-0 border-y border-slate-200 py-4">
          <p className="break-words text-lg font-semibold text-slate-950">{item.title}</p>
          <p className="mt-1 break-words text-xs text-slate-500">
            {item.sectionTitle ?? "Article start"} · {item.progress}% read
          </p>
          <div
            aria-label={`Reading progress for ${item.title}`}
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={item.progress}
            className="mt-3 h-1.5 overflow-hidden bg-slate-200"
            role="progressbar"
          >
            <span className="block h-full bg-amber-500" style={{ width: `${item.progress}%` }} />
          </div>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <time className="text-xs text-slate-500" dateTime={item.updatedAt}>
              Updated {formatDate(item.updatedAt)}
            </time>
            <Link
              aria-label={`Continue learning ${item.title}`}
              className="w-fit rounded bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
              href={item.href}
            >
              Continue learning
            </Link>
          </div>
        </div>
      ) : (
        <div className="mt-3 border-y border-slate-200 py-4">
          <p className="text-sm text-slate-600">No article in progress.</p>
          <Link className="mt-3 inline-block text-sm font-semibold text-emerald-800 hover:text-emerald-950" href="/articles">
            Choose an article
          </Link>
        </div>
      )}
    </section>
  );
}

function NextActions() {
  return (
    <section aria-labelledby="next-actions-title" className="border-t border-slate-300 pt-4" data-testid="dashboard-next-actions">
      <div>
        <h2 className="text-base font-semibold" id="next-actions-title">Next Actions</h2>
        <p className="mt-1 text-xs text-slate-500">Move directly into an existing learning workflow.</p>
      </div>
      <div className="mt-3 grid gap-px overflow-hidden border border-slate-200 bg-slate-200 sm:grid-cols-2 lg:grid-cols-4">
        {NEXT_ACTIONS.map((action) => (
          <Link className="min-w-0 bg-white p-4 hover:bg-slate-50" href={action.href} key={action.href}>
            <span className="block text-sm font-semibold text-slate-950">{action.label}</span>
            <span className="mt-1 block text-xs leading-5 text-slate-500">{action.detail}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

function LearningActivity({ items }: Readonly<{ items: DashboardActivityItem[] }>) {
  return (
    <section aria-labelledby="learning-activity-title" className="min-w-0 border-t-2 border-blue-700 pt-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold" id="learning-activity-title">Learning Activity</h2>
          <p className="mt-1 text-xs text-slate-500">Recent Reader and research work in one timeline.</p>
        </div>
        <span className="text-xs text-slate-500">{items.length} events</span>
      </div>
      {items.length ? (
        <ol className="mt-3 divide-y divide-slate-200 border-y border-slate-200" data-testid="dashboard-activity">
          {items.map((item) => (
            <li className="grid min-w-0 grid-cols-[1.75rem_minmax(0,1fr)] gap-3 py-3" key={item.id}>
              <span
                aria-hidden="true"
                className={`mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-sm text-[10px] font-bold text-white ${activityColor(item.kind)}`}
              >
                {activitySymbol(item.kind)}
              </span>
              <div className="min-w-0">
                <Link className="block break-words text-sm font-medium text-slate-950 hover:text-emerald-800" href={item.href}>
                  {item.title}
                </Link>
                <p className="mt-1 text-xs text-slate-500">
                  {item.detail} · <time dateTime={item.timestamp}>{formatDate(item.timestamp)}</time>
                </p>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 border-y border-slate-200 py-4 text-sm text-slate-600">No learning activity yet.</p>
      )}
    </section>
  );
}

function LatestArticles({
  articles,
  total,
}: Readonly<{ articles: ArticleSummary[]; total: number | null }>) {
  return (
    <section aria-labelledby="latest-articles-title" className="min-w-0 border-t-2 border-slate-950 pt-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold" id="latest-articles-title">New in Library</h2>
          <p className="mt-1 text-xs text-slate-500">
            {total === null ? "Library count unavailable" : `Showing ${articles.length} of ${total}`}
          </p>
        </div>
        <Link className="text-sm font-medium text-emerald-800 hover:text-emerald-950" href="/articles">
          View all
        </Link>
      </div>
      <div className="mt-3 divide-y divide-slate-200 border-y border-slate-200">
        {articles.length ? (
          articles.map((article) => (
            <Link className="block px-1 py-3 text-sm hover:bg-white" href={`/articles/${article.id}`} key={article.id}>
              <span className="block break-words font-medium">{article.title}</span>
              <span className="mt-1 block text-xs text-slate-500">{formatMetadata(article.metadata)}</span>
            </Link>
          ))
        ) : (
          <p className="py-4 text-sm text-slate-600">No articles available.</p>
        )}
      </div>
    </section>
  );
}

function displayCount(value: number | null): string {
  return value === null ? "—" : value.toLocaleString();
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) ? parsed.toLocaleString() : "Unknown time";
}

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

function activitySymbol(kind: DashboardActivityItem["kind"]): string {
  if (kind === "session") {
    return "S";
  }
  if (kind === "history") {
    return "H";
  }
  return "L";
}

function activityColor(kind: DashboardActivityItem["kind"]): string {
  if (kind === "session") {
    return "bg-violet-700";
  }
  if (kind === "history") {
    return "bg-slate-600";
  }
  return "bg-blue-700";
}
