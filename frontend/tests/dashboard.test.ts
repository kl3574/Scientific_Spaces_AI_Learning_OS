import assert from "node:assert/strict";
import test from "node:test";

import type { ArticleSummary } from "../src/lib/articles";
import type { ReaderProgressState } from "../src/lib/articleWorkspace";
import {
  DASHBOARD_ACTIVITY_LIMIT,
  buildDashboardActivity,
  createArticleTitleIndex,
  createDashboardOverview,
  selectContinueLearning,
} from "../src/lib/dashboard";
import type { LearningStats } from "../src/lib/learning";
import type { ReadingHistoryItem } from "../src/lib/readingHistory";

test("createDashboardOverview keeps unavailable values explicit and bounds completion", () => {
  assert.deepEqual(createDashboardOverview(1314, null), {
    articleTotal: 1314,
    readingCount: null,
    completedCount: null,
    unreadCount: null,
    bookmarkCount: null,
    noteCount: null,
    completionPercent: null,
  });

  const overview = createDashboardOverview(null, learningStats({ total_articles: 3, completed_count: 8 }));
  assert.equal(overview.articleTotal, 3);
  assert.equal(overview.completedCount, 8);
  assert.equal(overview.completionPercent, 100);
});

test("createArticleTitleIndex prefers current Article data over stale local history", () => {
  const titles = createArticleTitleIndex(
    [article("article-a", "Current source title")],
    learningStats({
      recent_articles: [recentArticle("article-a", "Learning title", "2026-08-31T08:00:00Z")],
    }),
    [historyItem("article-a", "Stale history title", "2026-08-31T09:00:00Z")],
  );
  assert.equal(titles.get("article-a"), "Current source title");
});

test("selectContinueLearning chooses the newest exact Reader position", () => {
  const history = [
    historyItem("article-a", "Article A", "2026-08-30T08:00:00Z"),
    historyItem("article-b", "Article B", "2026-08-30T09:00:00Z"),
  ];
  const progress = [
    readerProgress("article-a", "proof", "Proof", 43, "2026-08-31T10:00:00Z"),
    readerProgress("article-b", null, null, 12, "2026-08-30T10:00:00Z"),
  ];
  const selected = selectContinueLearning(history, progress, new Map(history.map((item) => [item.id, item.title])));

  assert.deepEqual(selected, {
    articleId: "article-a",
    title: "Article A",
    href: "/articles/article-a#proof",
    sectionTitle: "Proof",
    progress: 43,
    updatedAt: "2026-08-31T10:00:00Z",
  });
});

test("buildDashboardActivity merges title-resolved events and suppresses duplicate history", () => {
  const stats = learningStats({
    recent_articles: [recentArticle("article-a", "Stale Article A", "2026-08-31T10:00:00Z")],
    recent_sessions: [
      {
        session_id: "session-1",
        article_id: "article-b",
        started_at: "2026-08-31T11:00:00Z",
        ended_at: "2026-08-31T11:02:05Z",
        duration_seconds: 125,
        source: "reader",
      },
    ],
  });
  const history = [
    historyItem("article-a", "Duplicate Article A", "2026-08-31T10:01:00Z"),
    historyItem("article-c", "Article C", "2026-08-31T09:00:00Z"),
    historyItem("invalid", "Invalid timestamp", "not-a-date"),
  ];
  const titles = new Map([
    ["article-a", "Article A"],
    ["article-b", "Resolved Article B"],
    ["article-c", "Article C"],
  ]);
  const activity = buildDashboardActivity(stats, history, titles);

  assert.deepEqual(activity.map((item) => item.id), [
    "session:session-1",
    "learning:article-a",
    "history:article-c",
  ]);
  assert.equal(activity[0].title, "Resolved Article B");
  assert.equal(activity[0].detail, "Reader session · 2m 5s");
  assert.equal(activity[1].title, "Article A");
  assert.equal(activity.some((item) => item.id === "history:article-a"), false);
});

test("buildDashboardActivity never exposes a raw Article ID as a title", () => {
  const activity = buildDashboardActivity(
    learningStats({
      recent_sessions: [
        {
          session_id: "session-unknown",
          article_id: "internal-raw-id",
          started_at: "2026-08-31T11:00:00Z",
          ended_at: null,
          duration_seconds: null,
          source: "rag",
        },
      ],
    }),
    [],
    new Map(),
  );

  assert.equal(activity[0].title, "Untitled article");
  assert.equal(activity[0].title.includes("internal-raw-id"), false);
});

test("buildDashboardActivity enforces the public activity ceiling", () => {
  const recent = Array.from({ length: 20 }, (_, index) =>
    recentArticle(
      `article-${index}`,
      `Article ${index}`,
      new Date(Date.UTC(2026, 7, 31, 12, index)).toISOString(),
    ),
  );
  const activity = buildDashboardActivity(
    learningStats({ recent_articles: recent }),
    [],
    new Map(),
    100,
  );
  assert.equal(activity.length, 12);
  assert.equal(buildDashboardActivity(learningStats({ recent_articles: recent }), [], new Map()).length, DASHBOARD_ACTIVITY_LIMIT);
});

function article(id: string, title: string): ArticleSummary {
  return {
    id,
    title,
    url: `https://example.test/${id}`,
    content_preview: "Preview",
    metadata: {},
  };
}

function historyItem(id: string, title: string, lastReadAt: string): ReadingHistoryItem {
  return {
    id,
    title,
    url: `https://example.test/${id}`,
    last_read_at: lastReadAt,
  };
}

function readerProgress(
  articleId: string,
  sectionId: string | null,
  sectionTitle: string | null,
  progress: number,
  updatedAt: string,
): ReaderProgressState {
  return {
    article_id: articleId,
    section_id: sectionId,
    section_title: sectionTitle,
    progress,
    updated_at: updatedAt,
  };
}

function recentArticle(articleId: string, title: string, timestamp: string) {
  return {
    article_id: articleId,
    title,
    url: `https://example.test/${articleId}`,
    status: "reading" as const,
    last_read_at: timestamp,
    updated_at: timestamp,
  };
}

function learningStats(overrides: Partial<LearningStats> = {}): LearningStats {
  return {
    total_articles: 3,
    unread_count: 2,
    reading_count: 1,
    completed_count: 0,
    bookmark_count: 0,
    note_count: 0,
    recent_articles: [],
    recent_sessions: [],
    ...overrides,
  };
}
