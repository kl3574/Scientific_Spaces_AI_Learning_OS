import { strict as assert } from "node:assert";
import test from "node:test";

import { toPlainTextPreview } from "../src/lib/articlePresentation";

test("toPlainTextPreview removes Markdown structure while retaining readable content", () => {
  const source = [
    "## 模型回顾",
    "不知道大家是否留意 **Attention** 的 [长度外推](https://example.test/detail)。",
    "![结构图](https://example.test/image.png)",
    "这里有 $I(\\theta)$ 和 `inline code`。",
  ].join("\n\n");

  assert.equal(
    toPlainTextPreview(source),
    "模型回顾 不知道大家是否留意 Attention 的 长度外推。 结构图 这里有 I(theta) 和 inline code。",
  );
});

test("toPlainTextPreview removes headings and truncated links after API whitespace compaction", () => {
  const compacted = "正文段落。 ## 模型回顾 # 参考[《文章标题》](/archives/123 #";
  assert.equal(toPlainTextPreview(compacted), "正文段落。 模型回顾 参考《文章标题》");
});

test("toPlainTextPreview truncates deterministically without splitting the ellipsis budget", () => {
  assert.equal(toPlainTextPreview("1234567890", 6), "12345…");
});
