import { strict as assert } from "node:assert";
import test from "node:test";

import {
  DEFAULT_READER_PREFERENCES,
  canResumeReaderProgress,
  canReaderToolsConsumeScroll,
  clampReadingProgress,
  createResumeHref,
  extractArticleOutline,
  hasReaderScrollMotion,
  hasSameReaderLayout,
  parseReaderPreferences,
  parseReaderProgressStore,
  prepareArticleMarkdown,
  updateLastMeaningfulPosition,
} from "../src/lib/articleWorkspace";

const toolPosition = {
  scrollY: 2397,
  articleTop: 85,
  articleHeight: 2382,
  articleWidth: 358,
  viewportHeight: 844,
  viewportWidth: 390,
};

test("tool scroll ownership is directional and only chains at an existing boundary", () => {
  const tools = { scrollTop: 300, scrollHeight: 2500, clientHeight: 900 };
  assert.equal(canReaderToolsConsumeScroll(tools, 5000), true);
  assert.equal(canReaderToolsConsumeScroll(tools, -5000), true);
  assert.equal(canReaderToolsConsumeScroll(tools, 0), false);
  assert.equal(canReaderToolsConsumeScroll({ ...tools, scrollTop: 0 }, -1), false);
  assert.equal(canReaderToolsConsumeScroll({ ...tools, scrollTop: 1600 }, 1), false);
  assert.equal(canReaderToolsConsumeScroll({ ...tools, scrollTop: 0 }, 1), true);
  assert.equal(canReaderToolsConsumeScroll({ ...tools, scrollTop: 1600 }, -1), true);
  assert.equal(canReaderToolsConsumeScroll({ ...tools, clientHeight: 2500 }, 1), false);
});

test("a user document gesture can reacquire reading without changing tool hash or focus", () => {
  assert.equal(canResumeReaderProgress(toolPosition, { ...toolPosition, scrollY: 1300 }), true);
  assert.equal(canResumeReaderProgress(toolPosition, { ...toolPosition, scrollY: 0 }), true);
  assert.equal(canResumeReaderProgress(toolPosition, toolPosition), false);
  assert.equal(canResumeReaderProgress(toolPosition, { ...toolPosition, scrollY: 2700 }), false);
});

test("layout and viewport changes cannot reuse an earlier reading gesture", () => {
  for (const key of ["articleTop", "articleHeight", "articleWidth", "viewportHeight", "viewportWidth"] as const) {
    const changed = { ...toolPosition, scrollY: 1300, [key]: toolPosition[key] + 10 };
    assert.equal(hasSameReaderLayout(toolPosition, changed), false, key);
    assert.equal(canResumeReaderProgress(toolPosition, changed), false, key);
  }
  assert.equal(hasSameReaderLayout(toolPosition, { ...toolPosition, scrollY: 1300 }), true);
  assert.equal(hasSameReaderLayout(toolPosition, { ...toolPosition, articleTop: 85.000001 }), true);
});

test("native motion can precede Article entry without admitting an idle or reflowed origin", () => {
  const origin = { ...toolPosition, scrollY: 2783 };
  const stillBelow = { ...origin, scrollY: 2673 };
  assert.equal(hasReaderScrollMotion(origin, stillBelow), true);
  assert.equal(canResumeReaderProgress(origin, stillBelow), false);
  assert.equal(canResumeReaderProgress(origin, { ...origin, scrollY: 2045 }), true);
  assert.equal(hasReaderScrollMotion(origin, origin), false);
  assert.equal(hasReaderScrollMotion(origin, { ...stillBelow, articleHeight: 2500 }), false);
  assert.equal(hasReaderScrollMotion(origin, { ...stillBelow, scrollY: Number.NaN }), false);
});

test("short Articles can resume and gestures can pass the real end in either direction", () => {
  const short = { ...toolPosition, articleHeight: 479, scrollY: 494 };
  assert.equal(canResumeReaderProgress(short, { ...short, scrollY: 100 }), true);
  assert.equal(canResumeReaderProgress(short, { ...short, scrollY: 600 }), false);
  assert.equal(canResumeReaderProgress({ ...toolPosition, scrollY: 500 }, { ...toolPosition, scrollY: 3000 }), true);
  assert.equal(canResumeReaderProgress({ ...toolPosition, scrollY: 3000 }, { ...toolPosition, scrollY: 500 }), true);
});

test("invalid scroll geometry fails closed", () => {
  for (const value of [Number.NaN, Number.POSITIVE_INFINITY]) {
    for (const key of Object.keys(toolPosition) as Array<keyof typeof toolPosition>) {
      assert.equal(canResumeReaderProgress(toolPosition, { ...toolPosition, scrollY: 1300, [key]: value }), false);
    }
  }
  assert.equal(canResumeReaderProgress({ ...toolPosition, articleHeight: 0 }, { ...toolPosition, articleHeight: 0, scrollY: 1300 }), false);
});

test("extractArticleOutline creates stable Unicode anchors and resolves duplicates", () => {
  const markdown = [
    "## 模型概览",
    "### 重复标题",
    "### 重复标题",
    "### 重复标题-2",
    "### 重复标题",
    "#### [公式推导](https://example.test) [#](#公式推导)",
    "```markdown",
    "## 代码中的伪标题",
    "```",
  ].join("\n");

  assert.deepEqual(extractArticleOutline(markdown), [
    { id: "模型概览", label: "模型概览", level: 2, line: 1 },
    { id: "重复标题", label: "重复标题", level: 3, line: 2 },
    { id: "重复标题-2", label: "重复标题", level: 3, line: 3 },
    { id: "重复标题-2-2", label: "重复标题-2", level: 3, line: 4 },
    { id: "重复标题-3", label: "重复标题", level: 3, line: 5 },
    { id: "公式推导", label: "公式推导", level: 4, line: 6 },
  ]);
  assert.deepEqual(extractArticleOutline(markdown), extractArticleOutline(markdown));
});

test("prepareArticleMarkdown repairs presentation markers without changing fenced code", () => {
  const source = [
    "## 数学形式 [#](#数学形式)",
    "**前言：**正文从这里开始。",
    "\\[x^2\\]",
    "```markdown",
    "**前言：**代码保持原样",
    "## 代码标题 [#](#代码标题)",
    "```",
  ].join("\n");
  const prepared = prepareArticleMarkdown(source);

  assert.match(prepared, /^## 数学形式$/m);
  assert.match(prepared, /\*\*前言：\*\* 正文/);
  assert.match(prepared, /\$\$x\^2\$\$/);
  assert.match(prepared, /\*\*前言：\*\*代码保持原样/);
  assert.match(prepared, /## 代码标题 \[#\]\(#代码标题\)/);
});

test("reading progress is integer bounded from zero through one hundred", () => {
  assert.equal(clampReadingProgress(Number.NaN), 0);
  assert.equal(clampReadingProgress(-12), 0);
  assert.equal(clampReadingProgress(42.6), 43);
  assert.equal(clampReadingProgress(140), 100);
});

test("last meaningful section survives a temporary scroll above the first heading", () => {
  const previous = {
    article_id: "article-1",
    section_id: "formula",
    section_title: "Formula",
    progress: 45,
    updated_at: "2026-08-31T08:00:00.000Z",
  };

  assert.deepEqual(
    updateLastMeaningfulPosition(previous, null, 0, "2026-08-31T08:01:00.000Z"),
    {
      ...previous,
      progress: 0,
      updated_at: "2026-08-31T08:01:00.000Z",
    },
  );
  assert.deepEqual(
    updateLastMeaningfulPosition(
      previous,
      { id: "references", label: "References", level: 2, line: 20 },
      72.4,
      "2026-08-31T08:02:00.000Z",
    ),
    {
      article_id: "article-1",
      section_id: "references",
      section_title: "References",
      progress: 72,
      updated_at: "2026-08-31T08:02:00.000Z",
    },
  );
});

test("reader progress parsing is fail-closed and normalizes unsafe fields", () => {
  const raw = JSON.stringify({
    version: 1,
    items: [
      {
        article_id: "article-1",
        section_id: "模型概览",
        section_title: "模型概览",
        progress: 120,
        updated_at: "2026-08-31T08:00:00.000Z",
      },
      {
        article_id: "article-2",
        section_id: "../unsafe",
        section_title: "Unsafe",
        progress: 25,
        updated_at: "2026-08-30T08:00:00.000Z",
      },
      { article_id: 3 },
    ],
  });

  const parsed = parseReaderProgressStore(raw);
  assert.equal(parsed.length, 2);
  assert.equal(parsed[0].progress, 100);
  assert.equal(parsed[1].section_id, null);
  assert.deepEqual(parseReaderProgressStore("not-json"), []);
});

test("reader preferences and resume links use bounded safe values", () => {
  assert.deepEqual(parseReaderPreferences(null), DEFAULT_READER_PREFERENCES);
  assert.deepEqual(parseReaderPreferences('{"textSize":"large","width":"wide"}'), {
    textSize: "large",
    width: "wide",
  });
  assert.deepEqual(parseReaderPreferences('{"textSize":"huge","width":"full"}'), DEFAULT_READER_PREFERENCES);

  const href = createResumeHref("article with space", {
    article_id: "article with space",
    section_id: "公式推导",
    section_title: "公式推导",
    progress: 50,
    updated_at: "2026-08-31T08:00:00.000Z",
  });
  assert.equal(href, "/articles/article%20with%20space#%E5%85%AC%E5%BC%8F%E6%8E%A8%E5%AF%BC");
});
