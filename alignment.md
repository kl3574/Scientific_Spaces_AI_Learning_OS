# Task Alignment - M1.1 Article Content Fidelity Revision

## 1. 背景

项目 `kl3574/Scientific_Spaces_AI_Learning_OS` 当前 M1 Final Freeze Gate 已执行，结果为 BLOCKED。

阻塞原因：

- fresh live sync 成功发现并导入文章。
- 但是 `Article.content` 质量不满足要求：
  - 抽样正文不可靠。
  - `formulas_valid=false`。

当前任务是 `M1.1 Article Content Fidelity Revision`。这是 M1 冻结后的 revision task，用于修复 M1 Source Pipeline 的内容保真问题。

禁止实现：

- M2 Reader
- Search
- RAG
- Learning System

## 2. 需求

1. 读取：
   - `docs/M1_FINAL_FREEZE_REPORT.md`
   - `docs/M1_VERIFICATION_REPORT.md`
   - `docs/M1_SOURCE_ACCESS_STRATEGY_REVISION.md`
   - `docs/04_DATA_MODEL.md`
   - `docs/08_KNOWLEDGE_PIPELINE.md`
2. 检查 `backend/app/`，包括：
   - crawler
   - browser
   - parser
   - converter
   - storage
   - validation
3. 针对一个真实文章 URL 诊断：
   - Browser HTML 是否包含 article body。
   - Parser 输出 `title`、`content`、`references`、`images`。
   - Converter 输出 Markdown 结构。
   - Formula 中 LaTeX、MathJax 和公式完整性。
4. 创建 `docs/M1_CONTENT_FIDELITY_REVISION.md`，包含：
   - Current Issue
   - Root Cause
   - Evidence
   - Fix Plan
   - Validation Result
5. 如果根因明确，允许修改：
   - `backend/app/parser/`
   - `backend/app/converter/`
   - `backend/app/validation/`
6. 禁止修改：
   - RSS discovery
   - Browser Access Strategy
   - M2-M7 相关功能
7. 增加 parser regression test，至少使用真实文章 fixture，验证：
   - title 正确
   - content 正文正确
   - formula 保留
   - references 保留
8. 运行 `pytest`。
9. Live 验证最多 5 篇真实文章，验证：
   - content quality
   - formula validity
10. 成功标准：
   - `formulas_valid=true`
   - 正文抽样正确
11. 如果修复成功，提交：
   - `fix: improve article content fidelity`
12. 如果只是诊断，提交：
   - `docs: analyze article content fidelity issue`

## 3. 目的

修复 M1 Source Pipeline 的文章内容保真问题，使 RSS + Playwright 获取的真实文章经过 parser/converter/storage/validation 后，`Article.content` 能可靠表示文章正文并保持公式结构，从而重新满足 M1 freeze handoff 的输入质量要求。

## 4. 计划执行方案

1. 覆盖写入本次 `alignment.md`。
2. 读取指定文档和当前 `backend/app/` 实现。
3. 用一个真实文章 URL 进行最小化诊断，定位 browser HTML、parser root selection、converter output、validation 之间的数据流断点。
4. 形成明确根因后，先写 parser regression test，使用真实文章 fixture，覆盖正文、标题、公式、引用。
5. 运行新增测试，确认失败。
6. 在允许范围内修改 parser/converter/validation 中必要文件，不改 crawler/RSS/browser access/sync。
7. 运行 targeted tests，使回归测试通过。
8. 运行普通 `pytest`。
9. 低频 live 验证最多 5 篇文章，确认 `formulas_valid=true` 且正文抽样正确。
10. 创建 `docs/M1_CONTENT_FIDELITY_REVISION.md`，记录根因、证据、修复方案和验证结果。
11. 检查 `git status`、`git diff --stat`，确认没有临时 HTML、PDF、图片、trace、profile、cache artifact。
12. 按结果提交。

## 5. 方案选型理由

当前问题表现为 Article 内容保真失败，最可能发生在 parser/converter/validation 之间。系统化诊断可以避免修改 RSS discovery 或 browser access strategy 这类已通过的上游能力。用真实文章 fixture 做回归测试可以把 live failure 固化为稳定测试，再通过最小实现修复根因。

## 6. 优缺点对比

仅一个可行方案：诊断真实 HTML 到 Article.content 的数据流，基于根因用 TDD 修复 parser/converter/validation。

优点：

- 聚焦 M1.1 内容保真，不扩大到 M2。
- 保持 RSS discovery 和 browser access strategy 稳定。
- 用回归测试防止再次把正文解析成评论/侧栏。
- live 验证直接覆盖 freeze blocker。

缺点：

- 真实站点 HTML 结构可能变化，selector 需要谨慎设计。
- live 验证依赖网络和 Playwright runtime。
- 如果根因不在允许修改范围内，只能形成诊断报告并保持 blocked。

## 7. 交付件

1. `alignment.md`
2. `docs/M1_CONTENT_FIDELITY_REVISION.md`
3. parser regression test
4. 必要的 parser/converter/validation 修复
5. pytest 和 live validation 证据
6. Git commit：
   - 成功修复：`fix: improve article content fidelity`
   - 仅诊断：`docs: analyze article content fidelity issue`

## 8. 交付件验收指标

1. 已读取指定文档。
2. 已检查 `backend/app/` 中 crawler/browser/parser/converter/storage/validation。
3. 已对真实文章 URL 完成 Browser HTML、Parser、Converter、Formula 诊断。
4. `docs/M1_CONTENT_FIDELITY_REVISION.md` 存在并包含 Current Issue、Root Cause、Evidence、Fix Plan、Validation Result。
5. 新增 parser regression test，使用真实文章 fixture，验证 title/content/formula/references。
6. 未修改 RSS discovery 或 Browser Access Strategy，除非诊断证明必要。
7. 未实现 M2 Reader、Search、RAG、Learning System。
8. 普通 `pytest` 通过。
9. live 验证最多 5 篇文章。
10. 如果成功修复，live validation 显示 `formulas_valid=true`，正文抽样正确。
11. 如果未成功修复，保持 M1 Freeze Blocked 并提交诊断报告。
12. 提交消息与结果匹配。
