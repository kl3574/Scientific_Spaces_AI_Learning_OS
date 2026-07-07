# Task Alignment - Milestone 4 Learning System Document

## 1. 背景

当前项目是 `Scientific_Spaces_AI_Learning_OS`，已同步到公开 GitHub 仓库 `kl3574/Scientific_Spaces_AI_Learning_OS`。项目已有 M0、M1、M2 和 M3 里程碑文档。

本轮任务是创建 Milestone 4 文档，用于定义 Learning Management 能力。任务范围是规划文档，不实现学习状态、收藏、会话历史或 Dashboard 业务功能。

已确认约束：

- 必须创建 `milestones/M4_LEARNING_SYSTEM.md`。
- 文档必须定义 Milestone 4 的目标、任务和验收场景。
- 本轮不实现业务功能。

## 2. 需求

1. 创建文件：`milestones/M4_LEARNING_SYSTEM.md`。
2. 文档标题为：`Milestone 4 - Learning Management`。
3. 目标：从阅读系统升级为学习系统。
4. 写入 4 个任务：
   - `TASK-M4-001 Learning State`
   - `TASK-M4-002 Bookmark`
   - `TASK-M4-003 Conversation History`
   - `TASK-M4-004 Dashboard`
5. `TASK-M4-001 Learning State` 要求记录：
   - `article`
   - `progress`
   - `status`
6. `TASK-M4-002 Bookmark` 要求：
   - 用户收藏内容。
7. `TASK-M4-003 Conversation History` 要求保存：
   - 问题
   - 回答
   - 来源
8. `TASK-M4-004 Dashboard` 要求显示：
   - 学习统计。
9. 写入 Acceptance：
   - 用户：学习一个章节。
   - 系统：记录状态。
10. 本轮只创建 Milestone 文档，不实现业务功能。

## 3. 目的

形成 Milestone 4 的正式任务定义，为后续将阅读系统升级为学习系统提供清晰范围和验收标准。

## 4. 计划执行方案

1. 读取 `alignment.md`、检查 `REWORK.md`、读取 `roadmap.md`。
2. 将本次完整对齐内容覆盖写入 `alignment.md`。
3. 检查 `milestones/` 目录和现有 M0-M3 文档。
4. 创建 `milestones/M4_LEARNING_SYSTEM.md`。
5. 验证标题、目标、任务编号、字段、收藏、会话历史、Dashboard 和 Acceptance 是否完整。
6. 确认没有新增学习系统实现代码。
7. 提交并同步本次文档变更。

## 5. 方案选型理由

这是一个里程碑规划任务，使用 Markdown 文档最直接。先定义学习状态、收藏、问答历史和学习统计的边界，可以避免在未单独对齐实现方案前引入业务代码。

## 6. 优缺点对比

方案 A：仅创建 M4 里程碑文档。

优点：

- 符合当前请求。
- 边界清晰。
- 保持 M0-M3 文档风格一致。
- 不提前实现业务功能。

缺点：

- 本轮不会让学习系统实际可运行。

推荐采用方案 A。

方案 B：创建文档并同时实现学习状态、收藏、会话历史和 Dashboard。

优点：

- 推进更多功能。

缺点：

- 超出当前创建里程碑文档的任务边界。
- 会在未单独对齐实现方案前引入业务代码。

不推荐方案 B。

## 7. 交付件

1. `alignment.md`：本轮 Milestone 4 文档任务的完整对齐文档。
2. `milestones/M4_LEARNING_SYSTEM.md`：Milestone 4 Learning Management 文档。
3. 包含该文档变更的提交与同步结果。

## 8. 交付件验收指标

1. `alignment.md` 已覆盖为本轮任务对齐内容。
2. `milestones/M4_LEARNING_SYSTEM.md` 存在。
3. 文件标题精确为 `Milestone 4 - Learning Management`。
4. 文件包含目标：从阅读系统升级为学习系统。
5. 文件包含 `TASK-M4-001` 到 `TASK-M4-004`。
6. 文件包含 `article`、`progress`、`status`。
7. 文件包含用户收藏内容、问题、回答、来源、学习统计。
8. 文件包含 Acceptance：用户学习一个章节，系统记录状态。
9. 本轮未新增学习系统业务实现代码。
10. `git status` 最终干净，本地 `main` 与 `origin/main` 同步。
