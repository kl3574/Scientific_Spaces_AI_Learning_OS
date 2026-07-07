# Task Alignment - M1 PDF Export Capability Evaluation

## 1. 背景

项目 `kl3574/Scientific_Spaces_AI_Learning_OS` 已完成 M0/M1。RSS Discovery、Browser Article Access、Article Sync 均已验证通过。

本任务属于 M1 Export Capability Evaluation，只评估 Scientific Spaces Article PDF Export 工程可行性，不属于 M2 Reader、M3 RAG、AI Tutor 或 M4-M7。

## 2. 需求

1. 读取：
   - `docs/00_PROJECT_STATE.md`
   - `docs/M1_SOURCE_ACCESS_STRATEGY_REVISION.md`
   - `docs/M1_BROWSER_ARTICLE_ACCESS_STRATEGY.md`
   - `docs/M1_VERIFICATION_REPORT.md`
2. 检查 `kexue_downloader.py` 作为设计参考。
3. 创建 `docs/M1_PDF_EXPORT_EVALUATION.md`。
4. 新建独立 PDF Export 模块：`backend/app/export/pdf.py`。
5. PDF Export 必须支持：
   - Playwright Chromium
   - 等待 MathJax v2/v3
   - A4 页面打印
   - 中文
   - 数学公式
   - bounded retry
   - failure logging
6. 增加 fixture PDF export test。
7. 增加独立 marker 的 live PDF test，例如 `pdf_live`，默认不运行。
8. Live PDF test 必须使用临时目录。
9. 生成 PDF 后必须验证：
   - 文件存在
   - 文件大小大于 0
   - PDF 格式有效
10. 测试结束必须删除所有 PDF artifact。
11. 真实测试最多 5 篇文章，例如 `/archives/6508` 以及 RSS 获取的少量 URL。
12. 运行普通 `pytest`。
13. 禁止提交 PDF、HTML、图片、正文、缓存、browser profile、trace、截图。
14. 不修改：
   - `backend/app/crawler/`
   - RSS discovery
   - sync 主流程
   - Verification 标准
   - Project State
15. 不实现 M2 Reader、M3 RAG、M4-M7。
16. Commit message：`feat: add article pdf export capability`。

## 3. 目的

验证 Scientific Spaces Article -> PDF Export 是否具备工程可行性，并沉淀一个独立、可测试、可扩展但不接入主同步流程的 export capability。

## 4. 计划执行方案

1. 覆盖写入本次 `alignment.md`。
2. 读取指定 M1 文档和 `kexue_downloader.py`。
3. 检查当前 git 状态，避免误提交已有无关文件。
4. 先写 PDF export 测试：
   - fixture/fake exporter 测试 retry、failure logging、PDF 输出验证
   - live PDF test 使用 `@pytest.mark.pdf_live`，默认跳过
5. 运行新增测试，确认缺失实现导致失败。
6. 创建 `backend/app/export/pdf.py`，实现独立 Article PDF Export 能力。
7. 运行 targeted tests 使其通过。
8. 运行普通 `pytest`。
9. 使用最多 5 篇真实文章运行 live PDF export 验证，记录每篇：
   - URL
   - PDF status
   - 生成时间
   - 文件大小
   - MathJax status
   - 失败原因
10. 测试结束清理所有 PDF artifact。
11. 创建 `docs/M1_PDF_EXPORT_EVALUATION.md`，记录环境、设计、测试结果、成功率、Recommendation 和 Conclusion。
12. 检查 `git status` 和 `git diff --stat`，确认未提交禁止 artifact，未修改禁止文件。
13. 提交：`feat: add article pdf export capability`。

## 5. 方案选型理由

独立 export 模块可以验证 PDF 能力，同时不污染 M1 sync 主流程，也不提前进入 M2/M3。Playwright 是现有 Browser Article Access 已验证的技术路径，适合复用浏览器渲染、MathJax 等待和 `page.pdf()` 能力。临时目录和 PDF 格式校验能保证验证可信且不污染仓库。

## 6. 优缺点对比

仅一个可行方案：独立 PDF Export 模块 + 独立测试 + 独立报告。

优点：

- 边界清晰，不改变 crawler/sync/verification。
- 可验证真实 PDF 生成。
- 生成物受临时目录隔离。
- 后续可扩展为 batch export。

缺点：

- Playwright runtime 成本较高。
- live PDF 测试依赖网络和站点可访问性。
- PDF 质量可能需要后续排版优化。

## 7. 交付件

1. `alignment.md`
2. `docs/M1_PDF_EXPORT_EVALUATION.md`
3. `backend/app/export/pdf.py`
4. PDF export fixture 测试文件
5. live PDF test，独立 marker `pdf_live`
6. Git commit：`feat: add article pdf export capability`

## 8. 交付件验收指标

1. 报告存在，并包含 Current Status、Export Strategy、Test Results、PDF success rate、Recommendation、Conclusion。
2. `backend/app/export/pdf.py` 存在，并支持 Playwright Chromium、MathJax wait、A4 PDF、retry、failure logging。
3. 普通 `pytest` 通过。
4. live PDF test 默认跳过，可通过显式 marker/env 运行。
5. 至少 5 篇真实文章 PDF 生成结果被记录到报告中。
6. live PDF test 使用临时目录。
7. 每个 PDF artifact 验证：文件存在、文件大小大于 0、PDF 格式有效。
8. 测试结束后删除所有 PDF artifact。
9. 仓库内无 PDF、HTML、图片、正文、browser profile、trace、截图 artifact。
10. 未修改 `backend/app/crawler/`、RSS discovery、sync 主流程、M1 Verification 标准、Project State。
11. commit message 为 `feat: add article pdf export capability`。
