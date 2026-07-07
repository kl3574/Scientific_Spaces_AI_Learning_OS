# Task Alignment - Milestone 7 AI Tutor Document

## 1. 背景

当前项目是 `Scientific_Spaces_AI_Learning_OS`，已同步到公开 GitHub 仓库 `kl3574/Scientific_Spaces_AI_Learning_OS`。项目已有 M0、M1、M2、M3、M4、M5 和 M6 里程碑文档。

本轮任务是创建 Milestone 7 文档，用于定义 AI Research Tutor 能力。任务范围是规划文档，不实现 AI 导师、问答模式、数学推导、测验或论文探索功能。

已确认约束：

- 必须创建 `milestones/M7_AI_TUTOR.md`。
- 文档必须定义 Milestone 7 的目标、模式、模式说明和验收场景。
- 本轮不实现业务功能。

## 2. 需求

1. 创建文件：`milestones/M7_AI_TUTOR.md`。
2. 文档标题为：`Milestone 7 - AI Research Tutor`。
3. 目标：实现AI导师。
4. 模式：
   - Explain
   - Derive
   - Quiz
   - Research
5. Explain：
   - 概念解释。
6. Derive：
   - 数学推导。
7. Quiz：
   - 检查理解。
8. Research：
   - 探索论文。
9. 写入 Acceptance：
   - 用户输入：解释CRB
   - AI输出：直觉、数学、论文、检查问题。
10. 本轮只创建 Milestone 文档，不实现业务功能。

## 3. 目的

形成 Milestone 7 的正式任务定义，为后续实现 AI 导师的解释、推导、测验和论文探索能力提供清晰范围与验收标准。

## 4. 计划执行方案

1. 读取 `alignment.md`、检查 `REWORK.md`、读取 `roadmap.md`。
2. 将本次完整对齐内容覆盖写入 `alignment.md`。
3. 检查 `milestones/` 目录和现有 M0-M6 文档。
4. 创建 `milestones/M7_AI_TUTOR.md`。
5. 验证标题、目标、四种模式、各模式说明和 Acceptance 是否完整。
6. 确认没有新增 AI Tutor 实现代码。
7. 提交并同步本次文档变更。

## 5. 方案选型理由

这是一个里程碑规划任务，使用 Markdown 文档最直接。先定义 AI 导师模式和验收输出结构，可以避免在未单独对齐实现方案前引入 LLM 调用、prompt、测验逻辑或论文检索实现。

## 6. 优缺点对比

方案 A：仅创建 M7 里程碑文档。

优点：

- 符合当前请求。
- 边界清晰。
- 保持 M0-M6 文档风格一致。
- 不提前实现业务功能。

缺点：

- 本轮不会让 AI 导师实际可运行。

推荐采用方案 A。

方案 B：创建文档并同时实现 AI Tutor。

优点：

- 推进更多功能。

缺点：

- 超出当前创建里程碑文档的任务边界。
- 会在未单独对齐实现方案前引入 LLM 调用、prompt、测验逻辑或论文检索实现。

不推荐方案 B。

## 7. 交付件

1. `alignment.md`：本轮 Milestone 7 文档任务的完整对齐文档。
2. `milestones/M7_AI_TUTOR.md`：Milestone 7 AI Research Tutor 文档。
3. 包含该文档变更的提交与同步结果。

## 8. 交付件验收指标

1. `alignment.md` 已覆盖为本轮任务对齐内容。
2. `milestones/M7_AI_TUTOR.md` 存在。
3. 文件标题精确为 `Milestone 7 - AI Research Tutor`。
4. 文件包含目标：实现AI导师。
5. 文件包含 Explain、Derive、Quiz、Research 四种模式。
6. 文件包含各模式说明：概念解释、数学推导、检查理解、探索论文。
7. 文件包含 Acceptance：输入“解释CRB”，输出直觉、数学、论文、检查问题。
8. 本轮未新增 AI Tutor 业务实现代码。
9. `git status` 最终干净，本地 `main` 与 `origin/main` 同步。
