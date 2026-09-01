import assert from "node:assert/strict";
import test from "node:test";

import {
  SAVED_LIBRARY_ITEM_LIMIT,
  buildSavedLibrary,
  createSavedLibraryHref,
  createSavedLibraryReaderHref,
  parseSavedLibraryState,
  selectSavedLibraryItems,
} from "../src/lib/savedLibrary";

test("saved library joins existing learning records into readable actionable sections", () => {
  const model = buildSavedLibrary({
    bookmarks: [
      {
        article_id: "attention-001",
        title: "Attention Is All You Need",
        url: "https://spaces.ac.cn/archives/attention-001",
        created_at: "2026-08-30T09:00:00Z",
      },
    ],
    history: [
      {
        id: "attention-001",
        title: "Attention Is All You Need",
        url: "https://spaces.ac.cn/archives/attention-001",
        last_read_at: "2026-08-31T10:00:00Z",
      },
    ],
    progressItems: [
      {
        article_id: "attention-001",
        section_id: "scaled-dot-product",
        section_title: "Scaled dot-product attention",
        progress: 42,
        updated_at: "2026-08-31T10:05:00Z",
      },
    ],
    recentArticles: [],
    states: [
      {
        article_id: "attention-001",
        status: "reading",
        last_read_at: "2026-08-31T10:00:00Z",
        completed_at: null,
        read_count: 2,
        updated_at: "2026-08-31T10:00:00Z",
      },
      {
        article_id: "orphan-internal-id",
        status: "reading",
        last_read_at: null,
        completed_at: null,
        read_count: 1,
        updated_at: "2026-08-30T10:00:00Z",
      },
    ],
  });

  assert.equal(model.items.length, 1);
  assert.equal(model.unavailableCount, 1);
  assert.deepEqual(model.counts, { all: 1, continue: 1, bookmarked: 1, recent: 1 });
  assert.deepEqual(
    model.items[0],
    {
      articleId: "attention-001",
      title: "Attention Is All You Need",
      href: "/articles/attention-001?from=%2Flibrary#scaled-dot-product",
      status: "reading",
      isBookmarked: true,
      progress: 42,
      sectionId: "scaled-dot-product",
      sectionTitle: "Scaled dot-product attention",
      lastReadAt: "2026-08-31T10:05:00Z",
      savedAt: "2026-08-30T09:00:00Z",
      readCount: 2,
    },
  );
});

test("canonical learning state wins over a stale recent summary", () => {
  const model = buildSavedLibrary({
    bookmarks: [],
    history: [
      {
        id: "completed-001",
        title: "Completed Article",
        url: "https://spaces.ac.cn/archives/completed-001",
        last_read_at: "2026-08-31T09:00:00Z",
      },
    ],
    progressItems: [
      {
        article_id: "completed-001",
        section_id: "conclusion",
        section_title: "Conclusion",
        progress: 100,
        updated_at: "2026-08-31T09:05:00Z",
      },
    ],
    recentArticles: [
      {
        article_id: "completed-001",
        title: "Completed Article",
        url: "https://spaces.ac.cn/archives/completed-001",
        status: "reading",
        last_read_at: "2026-08-31T09:00:00Z",
        updated_at: "2026-08-31T09:00:00Z",
      },
    ],
    states: [
      {
        article_id: "completed-001",
        status: "completed",
        last_read_at: "2026-08-31T09:00:00Z",
        completed_at: "2026-08-31T09:10:00Z",
        read_count: 3,
        updated_at: "2026-08-31T09:10:00Z",
      },
    ],
  });

  assert.equal(model.items[0].status, "completed");
  assert.equal(model.counts.continue, 0);
});

test("library URL state is bounded and produces a canonical Reader return path", () => {
  assert.deepEqual(
    parseSavedLibraryState({ q: "  attention\u0000 score  ", view: "bookmarked", sort: "progress" }),
    { q: "attention score", view: "bookmarked", sort: "progress" },
  );
  assert.deepEqual(
    parseSavedLibraryState({ q: "", view: "unknown", sort: "unknown" }),
    { q: "", view: "all", sort: "recent" },
  );
  assert.equal(
    createSavedLibraryHref({ q: "attention score", view: "bookmarked", sort: "progress" }),
    "/library?q=attention+score&view=bookmarked&sort=progress",
  );
  assert.equal(
    createSavedLibraryReaderHref(
      "attention-001",
      { q: "attention score", view: "bookmarked", sort: "progress" },
      "scaled-dot-product",
    ),
    "/articles/attention-001?from=%2Flibrary%3Fq%3Dattention%2Bscore%26view%3Dbookmarked%26sort%3Dprogress#scaled-dot-product",
  );
});

test("local filter and sort remain deterministic", () => {
  const model = buildSavedLibrary({
    bookmarks: [
      { article_id: "b", title: "Beta", url: "https://spaces.ac.cn/archives/b", created_at: "2026-08-30T09:00:00Z" },
      { article_id: "a", title: "Alpha Attention", url: "https://spaces.ac.cn/archives/a", created_at: "2026-08-31T09:00:00Z" },
    ],
    history: [],
    progressItems: [
      { article_id: "a", section_id: "attention", section_title: "Attention score", progress: 30, updated_at: "2026-08-31T10:00:00Z" },
      { article_id: "b", section_id: null, section_title: null, progress: 80, updated_at: "2026-08-30T10:00:00Z" },
    ],
    recentArticles: [],
    states: [],
  });

  assert.deepEqual(
    selectSavedLibraryItems(model.items, { q: "attention", view: "all", sort: "progress" }).map((item) => item.articleId),
    ["a"],
  );
  assert.deepEqual(
    selectSavedLibraryItems(model.items, { q: "", view: "bookmarked", sort: "progress" }).map((item) => item.articleId),
    ["b", "a"],
  );
  assert.deepEqual(
    selectSavedLibraryItems(model.items, { q: "", view: "all", sort: "title" }).map((item) => item.articleId),
    ["a", "b"],
  );
});

test("library output is capped without truncating readable titles", () => {
  const longTitle = `Long ${"scientific ".repeat(18)}title`;
  const history = Array.from({ length: SAVED_LIBRARY_ITEM_LIMIT + 5 }, (_, index) => ({
    id: `article-${String(index).padStart(3, "0")}`,
    title: index === 0 ? longTitle : `Article ${index}`,
    url: `https://spaces.ac.cn/archives/${index}`,
    last_read_at: new Date(Date.UTC(2026, 7, 1, 0, SAVED_LIBRARY_ITEM_LIMIT + 5 - index)).toISOString(),
  }));
  const model = buildSavedLibrary({ bookmarks: [], history, progressItems: [], recentArticles: [], states: [] });

  assert.equal(model.items.length, SAVED_LIBRARY_ITEM_LIMIT);
  assert.equal(model.truncatedCount, 5);
  assert.equal(model.items.find((item) => item.articleId === "article-000")?.title, longTitle);
});
