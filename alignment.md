# Task Alignment - Milestone 5 Zotero Integration Document

## 1. 背景

当前项目是 `Scientific_Spaces_AI_Learning_OS`，已同步到公开 GitHub 仓库 `kl3574/Scientific_Spaces_AI_Learning_OS`。项目已有 M0、M1、M2、M3 和 M4 里程碑文档。

本轮任务是创建 Milestone 5 文档，用于定义 Zotero Integration 能力。任务范围是规划文档，不实现 Zotero MCP、论文搜索、metadata 读取或引用同步功能。

已确认约束：

- 必须创建 `milestones/M5_ZOTERO.md`。
- 文档必须定义 Milestone 5 的目标、功能、支持能力、Article-Paper 关联和验收场景。
- 本轮不实现业务功能。

## 2. 需求

1. 创建文件：`milestones/M5_ZOTERO.md`。
2. 文档标题为：`Milestone 5 - Zotero Integration`。
3. 目标：建立论文知识体系。
4. 功能：
   - Zotero MCP
5. 支持：
   - 搜索论文
   - 读取metadata
   - 同步引用
6. Article 关联：
   - Paper
7. 写入 Acceptance：
   - 博客文章显示相关论文列表。
8. 本轮只创建 Milestone 文档，不实现业务功能。

## 3. 目的

形成 Milestone 5 的正式任务定义，为后续把博客文章与 Zotero 论文知识体系关联起来提供边界和验收标准。

## 4. 计划执行方案

1. 读取 `alignment.md`、检查 `REWORK.md`、读取 `roadmap.md`。
2. 将本次完整对齐内容覆盖写入 `alignment.md`。
3. 检查 `milestones/` 目录和现有 M0-M4 文档。
4. 创建 `milestones/M5_ZOTERO.md`。
5. 验证标题、目标、Zotero MCP、搜索论文、读取metadata、同步引用、Article-Paper 关联和 Acceptance 是否完整。
6. 确认没有新增 Zotero 集成实现代码。
7. 提交并同步本次文档变更。

## 5. 方案选型理由

这是一个里程碑规划任务，使用 Markdown 文档最直接。先定义 Zotero 集成的能力边界，可以避免在未单独对齐实现方案前引入 MCP 或数据模型实现。

## 6. 优缺点对比

方案 A：仅创建 M5 里程碑文档。

优点：

- 符合当前请求。
- 边界清晰。
- 保持 M0-M4 文档风格一致。
- 不提前实现业务功能。

缺点：

- 本轮不会让 Zotero 集成实际可运行。

推荐采用方案 A。

方案 B：创建文档并同时实现 Zotero MCP 集成。

优点：

- 推进更多功能。

缺点：

- 超出当前创建里程碑文档的任务边界。
- 会在未单独对齐实现方案前引入 MCP、数据模型和本地 Zotero 依赖处理。

不推荐方案 B。

## 7. 交付件

1. `alignment.md`：本轮 Milestone 5 文档任务的完整对齐文档。
2. `milestones/M5_ZOTERO.md`：Milestone 5 Zotero Integration 文档。
3. 包含该文档变更的提交与同步结果。

## 8. 交付件验收指标

1. `alignment.md` 已覆盖为本轮任务对齐内容。
2. `milestones/M5_ZOTERO.md` 存在。
3. 文件标题精确为 `Milestone 5 - Zotero Integration`。
4. 文件包含目标：建立论文知识体系。
5. 文件包含 Zotero MCP。
6. 文件包含搜索论文、读取metadata、同步引用。
7. 文件包含 Article 关联 Paper。
8. 文件包含 Acceptance：博客文章显示相关论文列表。
9. 本轮未新增 Zotero 集成业务实现代码。
10. `git status` 最终干净，本地 `main` 与 `origin/main` 同步。
