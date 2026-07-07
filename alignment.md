# Task Alignment - Bootstrap Project Specification

## 1. 背景

当前项目是 `Scientific_Spaces_AI_Learning_OS`，远端仓库为 `kl3574/Scientific_Spaces_AI_Learning_OS`。GitHub 仓库已创建并可访问，当前本地 `main` 跟踪 `origin/main`。

用户要求初始化 Scientific Spaces AI Learning OS 项目，只完成 Bootstrap，不实现任何业务代码。

已确认约束：

- 只建立目录和工程文档。
- 不实现 backend。
- 不实现 frontend。
- 不实现 crawler。
- 不实现 RAG。
- 不添加业务逻辑。

## 2. 需求

1. 检查环境：
   - `git`
   - GitHub authentication
   - 当前 repository 状态
2. 输出 Environment Report。
3. 创建目录：
   - `docs/`
   - `milestones/`
   - `ADR/`
   - `codex/`
   - `backend/`
   - `frontend/`
   - `tests/`
4. 创建 `README.md`。
5. 创建基础工程文档：
   - `docs/01_PRD.md`
   - `docs/02_TDD.md`
   - `docs/03_SOP.md`
   - `docs/04_DATA_MODEL.md`
   - `docs/05_AI_AGENT_SPEC.md`
   - `docs/06_TEST_PLAN.md`
   - `docs/07_ROADMAP.md`
   - `docs/08_KNOWLEDGE_PIPELINE.md`
   - `docs/09_LEARNING_MODEL.md`
   - `docs/10_UI_SPEC.md`
   - `docs/11_SOURCE_POLICY.md`
   - `docs/12_AGENT_WORKFLOW.md`
6. 创建 Milestone 文档：
   - `milestones/M0_FOUNDATION.md`
   - `milestones/M1_SOURCE_PIPELINE.md`
   - `milestones/M2_READER_SYSTEM.md`
   - `milestones/M3_RAG_SYSTEM.md`
   - `milestones/M4_LEARNING_SYSTEM.md`
   - `milestones/M5_ZOTERO.md`
   - `milestones/M6_KNOWLEDGE_GRAPH.md`
   - `milestones/M7_AI_TUTOR.md`
7. 创建 `docs/00_PROJECT_STATE.md`，内容包含：
   - Version: `v0.0.1`
   - Phase: `Bootstrap`
   - Status: `Documentation initialized`
8. 提交信息：`docs: initialize project specification`。
9. Push 到 `origin/main`。
10. 最终输出：
    - GitHub 状态
    - 创建文件列表
    - commit hash
    - 下一步建议

## 3. 目的

完成项目 Bootstrap，让仓库具备基础目录结构、工程规格文档、Milestone 路线文档和项目状态记录，作为后续实现工作的起点。

## 4. 计划执行方案

1. 读取当前 `alignment.md`、检查 `REWORK.md`、读取 `roadmap.md`，确认无返工阻塞。
2. 检查 `git`、`gh auth status`、当前分支、远端、工作区状态和 GitHub 仓库状态。
3. 将本次完整对齐内容覆盖写入 `alignment.md`。
4. 创建缺失目录；空目录使用 `.gitkeep` 保留。
5. 创建或补齐指定 README、docs、milestones、project state 文档。
6. 若文件已存在，保留有效内容，只做 Bootstrap 文档层面的补齐。
7. 验证所有目录和文件存在。
8. 验证没有新增业务实现文件。
9. 提交：`docs: initialize project specification`。
10. Push 到 `origin/main`。
11. 验证本地 `main` 与 `origin/main` 同步，并读取 GitHub 远端状态。

## 5. 方案选型理由

Bootstrap 应该只建立项目骨架和规格文档。先检查环境和仓库现状，再补齐缺失文档，可以避免覆盖已有有效内容，也能确保最终提交范围只包含工程文档和空目录占位。

## 6. 优缺点对比

方案 A：检查现状后补齐 Bootstrap 文档和目录。

优点：

- 安全、可验证。
- 不会误删已有文件。
- 符合不实现业务代码的约束。

缺点：

- 已有文件内容与新规范不一致时，需要逐项判断是否补齐。

推荐采用方案 A。

方案 B：强制重建全部文件。

优点：

- 输出统一。

缺点：

- 可能覆盖已有 Milestone 文档或历史内容。

不推荐方案 B。

## 7. 交付件

1. Environment Report。
2. `README.md`。
3. `docs/00_PROJECT_STATE.md` 到 `docs/12_AGENT_WORKFLOW.md`。
4. `milestones/M0_FOUNDATION.md` 到 `milestones/M7_AI_TUTOR.md`。
5. `ADR/`、`codex/`、`backend/`、`frontend/`、`tests/` 目录。
6. Git commit：`docs: initialize project specification`。
7. Push 到 `origin/main` 的同步结果。

## 8. 交付件验收指标

1. 所有指定目录存在。
2. 所有指定文档存在。
3. `docs/00_PROJECT_STATE.md` 精确包含 `v0.0.1`、`Bootstrap`、`Documentation initialized`。
4. 未实现 backend、frontend、crawler、RAG 或业务逻辑。
5. `git status` 最终干净。
6. 本地 `main` 与 `origin/main` 同步。
7. 最终输出包含 GitHub 状态、创建文件列表、commit hash、下一步建议。
