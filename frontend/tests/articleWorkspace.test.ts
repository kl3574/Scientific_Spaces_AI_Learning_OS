import { strict as assert } from "node:assert";
import test from "node:test";

import {
  DEFAULT_READER_PREFERENCES,
  clampReadingProgress,
  createResumeHref,
  extractArticleOutline,
  parseReaderPreferences,
  parseReaderProgressStore,
  prepareArticleMarkdown,
} from "../src/lib/articleWorkspace";

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
