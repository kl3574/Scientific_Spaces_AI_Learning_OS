# Task Alignment - Milestone 1 Scientific Spaces Source Pipeline

## 1. 背景

当前任务是执行 `kl3574/Scientific_Spaces_AI_Learning_OS` 的 `Milestone 1 - Scientific Spaces Source Pipeline`。

M0 工程基础已完成，M1 目标是建立 Scientific Spaces 数据来源管线。当前只允许实现 M1 crawler/parser/markdown converter/storage/validation，不允许实现 M2-M7 功能。

## 2. 需求

1. 执行前读取指定文档：
   - `docs/00_PROJECT_STATE.md`
   - `docs/02_TDD.md`
   - `docs/03_SOP.md`
   - `milestones/M1_SOURCE_PIPELINE.md`
   - `docs/08_KNOWLEDGE_PIPELINE.md`
   - `docs/11_SOURCE_POLICY.md`
   - `docs/15_ACCEPTANCE.md`
   - `docs/31_MVP_BOUNDARY.md`
2. 检查环境并输出 `Environment Report`：
   - `git status`
   - `git branch`
   - `git remote -v`
   - `python --version`
   - `docker --version`
3. 实现 M1 Source Pipeline：
   - crawler
   - parser
   - markdown converter
   - storage
   - validation
4. 创建统一同步入口，例如 `python -m app.sync`。
5. 添加 pytest 测试：
   - Crawler Test
   - Parser Test
   - Storage Test
   - Validation Test
6. 更新 `docs/00_PROJECT_STATE.md`：
   - Version: `v0.2.0`
   - Phase: `M1 Completed`
   - Status: `Scientific Spaces source pipeline implemented`
7. 提交前执行：
   - `git status`
   - `git diff --stat`
8. 提交并推送：
   - commit: `feat: implement M1 scientific spaces source pipeline`
   - push: `origin/main`
9. 禁止修改 PRD/TDD/SOP/Milestone 文档。
10. 禁止实现 M2 Reader/Search、M3 RAG/Embedding/FAISS/LLM、M4-M7 全部功能。
11. 不提交 `.env`、cache、临时文件或下载的大量原始数据。

## 3. 目的

建立可靠、可重复执行、可测试的 Scientific Spaces 文章来源管线：发现文章 URL，下载 HTML，解析文章结构，转换 Markdown，保存 Article 数据，并生成数据质量验证报告，为后续 M2 Reader 和 M3 RAG 提供干净输入，但不提前实现这些后续功能。

## 4. 计划执行方案

1. 将本次完整对齐内容覆盖写入 `alignment.md`。
2. 执行项目启动检查：
   - 读取 `alignment.md`
   - 检查 `REWORK.md`
   - 读取 `roadmap.md`
3. 读取用户指定的 M1 文档；若 `docs/15_ACCEPTANCE.md` 或 `docs/31_MVP_BOUNDARY.md` 缺失，不直接创建或修改规范文档，改为创建 ADR 记录规范缺口与 M1 执行假设。
4. 执行环境检查并整理 `Environment Report`。
5. 以 TDD 顺序先补测试，再实现代码。
6. 在 `backend/app/crawler/` 实现模块化 crawler：
   - `discovery.py`：文章列表发现、分页支持、URL 提取。
   - `downloader.py`：请求异常处理、重试机制。
   - `cache.py`：基础缓存，避免重复下载。
7. 在 `backend/app/parser/` 实现 parser：
   - 提取 `title`、`url`、`date`、`category`、`content`、`images`、`references`。
   - 保留数学公式、图片链接、引用信息，不修改原文含义。
8. 在 `backend/app/converter/` 实现 HTML to Markdown：
   - 保持标题层级、LaTeX 公式、图片引用、代码块。
   - 禁止简单纯文本转换。
9. 在 `backend/app/storage/` 实现 Article 保存：
   - 至少包含 `id`、`title`、`url`、`content`、`metadata`。
   - metadata 包含 `date`、`category`、`references`、`images`。
   - 不引入 Knowledge Graph、Paper Entity、Embedding。
10. 在 `backend/app/validation/` 实现数据质量检查：
    - Title 100% 存在。
    - Content 95% 以上正文完整。
    - Images 路径有效。
    - Formula 未明显损坏。
    - 生成验证报告，但不提交大规模下载数据。
11. 创建同步入口 `backend/app/sync.py`，支持 `python -m app.sync`，按 crawler -> parser -> converter -> storage -> validation 执行，重复运行不产生大量重复数据。
12. 运行 `pytest`，必要时运行 Docker/CI 相关检查。
13. 只更新允许修改的 `docs/00_PROJECT_STATE.md`。
14. 提交前检查 `git status`、`git diff --stat`、禁止提交项。
15. commit 并 push 到 `origin/main`。
16. 输出最终报告。

## 5. 方案选型理由

M1 是数据来源管线，不是 reader、search 或 RAG。因此实现应集中在 backend 内部的可测试模块和 CLI 同步入口，避免任何 frontend 页面、Article API、搜索 UI、embedding、FAISS 或 LLM 依赖。使用本地结构化存储和小规模 fixture 测试可以保证可重复验证，同时避免提交大量抓取数据。

## 6. 优缺点对比

方案 A：实现模块化 backend pipeline，并用 fixture/小规模测试验证。

优点：

- 边界清晰、可测试、可重复执行。
- 对 M2-M7 兼容。
- 不提交大规模原始抓取数据。

缺点：

- 不会提供用户可见 reader/search 功能。

方案 B：直接抓取并提交一批真实文章数据。

优点：

- 短期看起来更接近完整数据集。

缺点：

- 容易提交大量原始数据和缓存。
- 复现性差。
- 不利于 source policy 控制。

不推荐方案 B。

方案 C：提前实现 Article API 或前端 Reader 验证数据。

优点：

- 可视化验证更直观。

缺点：

- 违反 M2 禁止范围。

不采用方案 C。

推荐采用方案 A。

## 7. 交付件

1. `alignment.md`
2. 如发现规范缺口：`ADR/` 下新增 ADR
3. `backend/app/crawler/discovery.py`
4. `backend/app/crawler/downloader.py`
5. `backend/app/crawler/cache.py`
6. `backend/app/parser/`
7. `backend/app/converter/`
8. `backend/app/storage/`
9. `backend/app/validation/`
10. `backend/app/sync.py`
11. backend 测试文件：crawler/parser/storage/validation/sync 相关 pytest
12. 必要的 fixture 测试数据
13. 轻量验证报告输出路径或生成逻辑
14. `docs/00_PROJECT_STATE.md` 更新
15. Git commit 和 push 到 `origin/main`

## 8. 交付件验收指标

1. `python -m app.sync` 可执行完整 M1 管线。
2. Crawler 能输出文章 URL 列表，支持分页、异常处理、重试、基础缓存。
3. Parser 能提取 `title`、`url`、`date`、`category`、`content`、`images`、`references`。
4. Markdown converter 保留标题层级、LaTeX 公式、图片引用、代码块。
5. Storage 保存 Article：`id`、`title`、`url`、`content`、`metadata`。
6. 重复执行 sync 不产生大量重复 Article 数据。
7. Validation 能对样本文章生成质量报告。
8. `pytest` 通过。
9. `docs/00_PROJECT_STATE.md` 更新为 `v0.2.0 / M1 Completed / Scientific Spaces source pipeline implemented`。
10. 提交前已执行 `git status` 和 `git diff --stat`。
11. 提交内容不包含 `.env`、cache、临时文件、下载的大量原始数据。
12. 不修改 PRD/TDD/SOP/Milestone 文档，除允许更新 `docs/00_PROJECT_STATE.md`。
13. 不包含 M2 Article API、Frontend Reader、Search UI。
14. 不包含 M3 RAG、Embedding、FAISS、LLM。
15. 不包含 M4-M7 功能。
16. commit 信息为 `feat: implement M1 scientific spaces source pipeline`，并推送到 `origin/main`。
