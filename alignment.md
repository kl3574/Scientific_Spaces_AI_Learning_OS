# Task Alignment - Milestone 3 RAG System Document

## 1. 背景

当前项目是 `Scientific_Spaces_AI_Learning_OS`，已同步到公开 GitHub 仓库 `kl3574/Scientific_Spaces_AI_Learning_OS`。项目已有 M0、M1 和 M2 里程碑文档。

本轮任务是创建 Milestone 3 文档，用于定义基于文章的 Grounded RAG Assistant。任务范围是规划文档，不实现 RAG、embedding、FAISS、LLM provider 或 citation 业务代码。

已确认约束：

- 必须创建 `milestones/M3_RAG_SYSTEM.md`。
- 文档必须定义 Milestone 3 的目标、任务和验收问题。
- 本轮不实现业务功能。

## 2. 需求

1. 创建文件：`milestones/M3_RAG_SYSTEM.md`。
2. 文档标题为：`Milestone 3 - Grounded RAG Assistant`。
3. 目标：实现基于文章的AI问答。
4. 写入 5 个任务：
   - `TASK-M3-001 Document Chunking`
   - `TASK-M3-002 Embedding`
   - `TASK-M3-003 Vector Search`
   - `TASK-M3-004 LLM Provider`
   - `TASK-M3-005 Citation`
5. `TASK-M3-001 Document Chunking` 要求：
   - Markdown 结构切分。
   - 不能固定字符切割。
6. `TASK-M3-002 Embedding` 要求：
   - 实现 embedding pipeline。
7. `TASK-M3-003 Vector Search` 要求：
   - 实现 FAISS。
8. `TASK-M3-004 LLM Provider` 要求实现接口：
   - `chat()`
   - `embedding()`
9. `TASK-M3-005 Citation` 要求回答必须包含：
   - 文章标题
   - URL
   - 章节
10. 写入 Acceptance：
    - 问题：什么是Attention？
    - 回答必须引用来源。
11. 本轮只创建 Milestone 文档，不实现业务功能。

## 3. 目的

形成 Milestone 3 的正式任务定义，为后续实现结构化文档切分、embedding 管线、FAISS 向量检索、LLM provider 抽象和可溯源回答提供明确边界与验收标准。

## 4. 计划执行方案

1. 读取 `alignment.md`、检查 `REWORK.md`、读取 `roadmap.md`。
2. 将本次完整对齐内容覆盖写入 `alignment.md`。
3. 检查 `milestones/` 目录和现有 M0/M1/M2 文档。
4. 创建 `milestones/M3_RAG_SYSTEM.md`。
5. 验证标题、目标、任务编号、Markdown 结构切分限制、embedding pipeline、FAISS、`chat()`、`embedding()`、citation 字段和 Acceptance 是否完整。
6. 确认没有新增 RAG、embedding、FAISS、LLM provider 或 citation 的实现代码。
7. 提交并同步本次文档变更。

## 5. 方案选型理由

这是一个里程碑规划任务，使用 Markdown 文档最直接。先定义 RAG 系统的关键工程边界，尤其是按 Markdown 结构切分而不是固定字符切割，以及回答必须引用来源，可以避免后续实现时偏离 grounded RAG 的核心要求。

## 6. 优缺点对比

方案 A：仅创建 M3 里程碑文档。

优点：

- 符合当前请求。
- 边界清晰。
- 保持 M0/M1/M2 文档风格一致。
- 不提前实现业务功能。

缺点：

- 本轮不会让 RAG 问答实际可运行。

推荐采用方案 A。

方案 B：创建文档并同时实现 chunking、embedding、FAISS、LLM provider 和 citation。

优点：

- 推进更多功能。

缺点：

- 超出当前创建里程碑文档的任务边界。
- 需要额外技术选型和 API key/模型配置对齐。

不推荐方案 B。

## 7. 交付件

1. `alignment.md`：本轮 Milestone 3 文档任务的完整对齐文档。
2. `milestones/M3_RAG_SYSTEM.md`：Milestone 3 Grounded RAG Assistant 文档。
3. 包含该文档变更的提交与同步结果。

## 8. 交付件验收指标

1. `alignment.md` 已覆盖为本轮任务对齐内容。
2. `milestones/M3_RAG_SYSTEM.md` 存在。
3. 文件标题精确为 `Milestone 3 - Grounded RAG Assistant`。
4. 文件包含目标：实现基于文章的AI问答。
5. 文件包含 `TASK-M3-001` 到 `TASK-M3-005`。
6. 文件包含 Markdown 结构切分要求，并明确不能固定字符切割。
7. 文件包含 embedding pipeline、FAISS、`chat()`、`embedding()`。
8. 文件包含 Citation 要求：文章标题、URL、章节。
9. 文件包含 Acceptance：问题“什么是Attention？”回答必须引用来源。
10. 本轮未新增 RAG、embedding、FAISS、LLM provider 或 citation 的业务实现代码。
11. `git status` 最终干净，本地 `main` 与 `origin/main` 同步。
