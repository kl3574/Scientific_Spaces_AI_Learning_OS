# Task Alignment - Milestone 6 Knowledge Graph Document

## 1. 背景

当前项目是 `Scientific_Spaces_AI_Learning_OS`，已同步到公开 GitHub 仓库 `kl3574/Scientific_Spaces_AI_Learning_OS`。项目已有 M0、M1、M2、M3、M4 和 M5 里程碑文档。

本轮任务是创建 Milestone 6 文档，用于定义 Knowledge Graph 能力。任务范围是规划文档，不实现知识图谱、实体模型或关系查询功能。

已确认约束：

- 必须创建 `milestones/M6_KNOWLEDGE_GRAPH.md`。
- 文档必须定义 Milestone 6 的目标、实体、关系和验收场景。
- 本轮不实现业务功能。

## 2. 需求

1. 创建文件：`milestones/M6_KNOWLEDGE_GRAPH.md`。
2. 文档标题为：`Milestone 6 - Knowledge Graph`。
3. 目标：建立概念-论文-文章-实验关系。
4. 实体：
   - `Concept`
   - `Theory`
   - `Paper`
   - `Experiment`
5. 关系：
   - `explained_by`
   - `supported_by`
   - `verified_by`
6. 写入 Acceptance：
   - 用户点击：Attention
   - 看到：相关文章、论文、实验、学习路径。
7. 本轮只创建 Milestone 文档，不实现业务功能。

## 3. 目的

形成 Milestone 6 的正式任务定义，为后续构建知识图谱、实体关系和学习路径展示提供清晰范围与验收标准。

## 4. 计划执行方案

1. 读取 `alignment.md`、检查 `REWORK.md`、读取 `roadmap.md`。
2. 将本次完整对齐内容覆盖写入 `alignment.md`。
3. 检查 `milestones/` 目录和现有 M0-M5 文档。
4. 创建 `milestones/M6_KNOWLEDGE_GRAPH.md`。
5. 验证标题、目标、实体、关系和 Acceptance 是否完整。
6. 确认没有新增知识图谱实现代码。
7. 提交并同步本次文档变更。

## 5. 方案选型理由

这是一个里程碑规划任务，使用 Markdown 文档最直接。先定义实体、关系和用户验收场景，可以避免在未单独对齐实现方案前引入图数据库、数据模型或查询逻辑。

## 6. 优缺点对比

方案 A：仅创建 M6 里程碑文档。

优点：

- 符合当前请求。
- 边界清晰。
- 保持 M0-M5 文档风格一致。
- 不提前实现业务功能。

缺点：

- 本轮不会让知识图谱实际可运行。

推荐采用方案 A。

方案 B：创建文档并同时实现知识图谱。

优点：

- 推进更多功能。

缺点：

- 超出当前创建里程碑文档的任务边界。
- 会在未单独对齐实现方案前引入图数据库、实体模型或查询逻辑。

不推荐方案 B。

## 7. 交付件

1. `alignment.md`：本轮 Milestone 6 文档任务的完整对齐文档。
2. `milestones/M6_KNOWLEDGE_GRAPH.md`：Milestone 6 Knowledge Graph 文档。
3. 包含该文档变更的提交与同步结果。

## 8. 交付件验收指标

1. `alignment.md` 已覆盖为本轮任务对齐内容。
2. `milestones/M6_KNOWLEDGE_GRAPH.md` 存在。
3. 文件标题精确为 `Milestone 6 - Knowledge Graph`。
4. 文件包含目标：建立概念-论文-文章-实验关系。
5. 文件包含实体：`Concept`、`Theory`、`Paper`、`Experiment`。
6. 文件包含关系：`explained_by`、`supported_by`、`verified_by`。
7. 文件包含 Acceptance：点击 Attention 后看到相关文章、论文、实验、学习路径。
8. 本轮未新增知识图谱业务实现代码。
9. `git status` 最终干净，本地 `main` 与 `origin/main` 同步。
