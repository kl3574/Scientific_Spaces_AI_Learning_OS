# Task Alignment - Implement M1 RSS Browser Source Strategy

## 1. 背景

项目 `kl3574/Scientific_Spaces_AI_Learning_OS` 当前 M1 Source Pipeline 已完成。新的策略评估已通过：

- RSS Discovery: PASS
- Browser Article Access: PASS

当前任务是实现新的 M1 Source Access Strategy，将 RSS Discovery 与 Playwright Browser Access 整合进入 M1 pipeline。本任务不实现 M2 Reader、M3 RAG、M4-M7，不修改 Verification 标准。最终仍需重新验证 M1。

## 2. 需求

1. 读取：
   - `docs/M1_SOURCE_ACCESS_STRATEGY_REVISION.md`
   - `docs/M1_ARTICLE_DISCOVERY_STRATEGY_EVALUATION.md`
   - `docs/M1_BROWSER_ARTICLE_ACCESS_STRATEGY.md`
   - `docs/M1_VERIFICATION_REPORT.md`
   - `ADR/0003-m1-live-source-access-blocker.md`
2. 实现 RSS Discovery Provider：
   - 输入：`https://spaces.ac.cn/feed`
   - 输出：Article URL list
3. 实现 Browser Access Provider：
   - 使用 Playwright Chromium
   - 支持 HTML 获取
   - 支持 title 获取
   - 支持 MathJax 等待
   - 支持 bounded retry
   - 失败时记录 URL 和失败原因
4. 保持 Existing Parser、Converter、Storage。
5. 更新 `python -m app.sync` 流程：
   - RSS
   - Article URLs
   - Browser Access
   - Parser
   - Markdown Converter
   - Storage
   - Validation
6. 禁止：
   - PDF 生成
   - 保存 raw HTML
   - 保存图片
   - 保存额外正文文件
   - 实现 M2-M7
7. 增加测试：
   - RSS discovery test
   - Browser provider test
   - Sync integration test
8. 保留 fixture 测试。
9. Live test 必须独立标记。
10. 验证：
    - `pytest`
    - `python -m app.sync`
    - 至少若干篇真实文章成功导入
    - 重复 sync 不重复
11. 只有真实 end-to-end sync 成功，才更新 `docs/00_PROJECT_STATE.md` 为 `M1 Verification Passed`。
12. Commit message：
    - 成功解除：`fix: implement RSS browser source strategy`
    - 如果只是实现但未解除：`feat: add RSS browser access strategy`

## 3. 目的

把已经评估通过的新 M1 source access strategy 工程化：用官方 RSS 获取文章 URL，用 Playwright Chromium 获取文章页面，再复用现有 parser/converter/storage/validation，完成真实端到端同步验证。

## 4. 计划执行方案

1. 覆盖写入本次 `alignment.md`。
2. 读取指定 5 个文档。
3. 检查当前 git 状态，识别已有未提交诊断文件和依赖变更，避免误提交无关内容。
4. 读取现有 M1 pipeline 代码：
   - crawler
   - parser
   - converter
   - storage
   - validation
   - sync
   - tests
5. 先写测试：
   - RSS fixture discovery 测试
   - Browser provider fake/page 测试
   - Sync fixture integration 测试
   - Live RSS/browser 测试独立 marker，默认不运行
6. 实现 RSS Discovery Provider：
   - 结构化解析 RSS XML
   - 提取 `item/link`
   - 校验 `https://spaces.ac.cn/archives/{id}`
   - 去重
   - bounded item limits
7. 实现 Browser Access Provider：
   - Playwright Chromium
   - 非持久 context
   - 禁止 downloads
   - bounded retry/timeout
   - 返回内存中的 HTML/title/metadata
   - 不把 raw HTML 写入文件
   - 记录失败 URL 和原因
8. 更新 sync：
   - 默认使用 RSS discovery + browser access
   - 保留 fixture/index/article-dir 测试入口兼容
   - 复用 parser/converter/storage/validation
9. 依赖处理：
   - 将 Playwright 作为 backend runtime dependency
   - 不提交浏览器缓存、trace、截图、profile
10. 运行测试：
    - `pytest`
11. 运行真实 sync：
    - `python -m app.sync`
    - 控制最大文章数，低频验证
12. 重复运行 sync，验证 idempotency。
13. 如果真实 end-to-end sync 成功：
    - 更新 `docs/00_PROJECT_STATE.md` 为 `M1 Verification Passed`
    - commit: `fix: implement RSS browser source strategy`
14. 如果真实 sync 失败：
    - 保持 `docs/00_PROJECT_STATE.md` blocked
    - commit: `feat: add RSS browser access strategy`

## 5. 方案选型理由

RSS 是官方可访问 discovery source，Playwright Chromium 已证明可访问部分 article URL。把二者作为 M1 source access layer，能替代失败的 homepage/archive discovery，同时复用已有 parser/converter/storage，避免引入 M2/M3 业务功能。

## 6. 优缺点对比

仅一个可行方案：实现 `RSS Discovery + Playwright Browser Access` 并接入现有 M1 sync。

优点：

- 使用官方 RSS discovery。
- 避开 homepage/archive 403。
- 复用现有 M1 parser/storage。
- 可通过 live sync 验证 M1 是否真正可用。

缺点：

- Playwright 增加运行时依赖和环境复杂度。
- RSS 可能只覆盖近期文章，不代表全量历史。
- Browser access 存在超时/403 波动，需要 bounded retry 和失败记录。

## 7. 交付件

1. `alignment.md`
2. RSS Discovery Provider 代码
3. Browser Access Provider 代码
4. 更新后的 `python -m app.sync`
5. RSS/browser/sync 测试
6. 独立 live test marker
7. 依赖配置更新
8. 若真实 sync 成功：更新 `docs/00_PROJECT_STATE.md`
9. Git commit：
   - 成功解除：`fix: implement RSS browser source strategy`
   - 未解除：`feat: add RSS browser access strategy`

## 8. 交付件验收指标

1. 已读取指定 5 个文档。
2. RSS provider 能从 `https://spaces.ac.cn/feed` 输出 article URL list。
3. Browser provider 使用 Playwright Chromium。
4. Browser provider 支持 HTML/title/MathJax/bounded retry/failure reason。
5. `python -m app.sync` 使用新流程。
6. Existing Parser/Converter/Storage 保持复用。
7. fixture 测试保留并通过。
8. 新增 RSS/browser/sync 测试通过。
9. live test 独立标记，默认不运行。
10. `pytest` 通过。
11. `python -m app.sync` 真实运行。
12. 重复 sync 不产生重复数据。
13. 不保存 raw HTML、PDF、图片、附件或额外正文文件。
14. 不实现 M2-M7。
15. 不修改 Verification 标准。
16. 只有真实 end-to-end sync 成功，才更新 `docs/00_PROJECT_STATE.md` 为 `M1 Verification Passed`。
17. commit message 与结果匹配。
