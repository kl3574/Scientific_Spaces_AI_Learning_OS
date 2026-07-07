# Task Alignment - M1 Final Freeze & Handoff Gate

## 1. 背景

项目 `kl3574/Scientific_Spaces_AI_Learning_OS` 当前已完成：

- M0 Engineering Foundation: PASS
- M1 Source Pipeline: PASS
- M1 Verification: PASS
- M1 PDF Export Capability: PASS

当前任务是执行 M1 Final Freeze & Handoff Gate。该任务是验收冻结任务，不实现新功能，不进入 M2。

Freeze 完成后，任何 M1 实现变更必须新建 `M1.x revision task`，不得直接修改冻结代码。

## 2. 需求

1. 读取：
   - `docs/00_PROJECT_STATE.md`
   - `milestones/M1_SOURCE_PIPELINE.md`
   - `docs/M1_VERIFICATION_REPORT.md`
   - `docs/M1_SOURCE_ACCESS_STRATEGY_REVISION.md`
   - `docs/M1_PDF_EXPORT_EVALUATION.md`
   - `docs/04_DATA_MODEL.md`
   - `docs/08_KNOWLEDGE_PIPELINE.md`
   - `ADR/`
2. 检查当前 `git status`。
3. 创建 `docs/M1_FINAL_FREEZE_REPORT.md`。
4. 审计并冻结：
   - Source Discovery
   - Browser Access
   - Parser
   - Converter
   - Storage
   - Validation
   - PDF Export
5. 确认 Article 数据契约：
   - `id`
   - `title`
   - `url`
   - `content`
   - `metadata`
   - `metadata.date`
   - `metadata.category`
   - `metadata.references`
   - `metadata.images`
6. 记录接口冻结：
   - Discovery Interface
   - Browser Access Interface
   - Parser Interface
   - Storage Interface
   - Export Interface
7. 记录测试证据：
   - pytest 结果
   - M1 live sync 结果
   - PDF export 结果
   - article count
   - duplicate count
   - validation result
   - PDF success rate
8. 判断 `backend/tests/test_browser_access.py`：
   - 若是长期 regression probe，则保留并提交
   - 若只是临时诊断文件，则删除
   - 在报告中记录决定
9. 执行 `git status`、`git diff --stat`。
10. 确认无 PDF、HTML、图片、trace、profile、cache、临时 artifact 被提交。
11. 如果 M1 Freeze 通过，更新 `docs/00_PROJECT_STATE.md`，增加 `M1 Freeze Passed`。
12. 在 freeze 报告和项目状态中记录冻结规则：
   - Freeze 完成后，任何 M1 实现变更必须新建 `M1.x revision task`
   - 不得直接修改冻结代码
13. 提交：`docs: freeze M1 source pipeline handoff`。

## 3. 目的

冻结 M1 当前最终状态，明确 M1 输出是否稳定、接口是否清晰、数据契约是否可靠，并判断是否可以作为 M2 Scientific Reader 的输入。冻结后建立 M1 变更治理规则，防止后续任务直接修改已冻结的 M1 实现。

## 4. 计划执行方案

1. 覆盖写入本次 `alignment.md`。
2. 读取所有指定文档和 ADR。
3. 检查 git 状态、当前未跟踪文件和潜在 artifact。
4. 检查 M1 实现代码的结构和接口签名，但不修改实现代码。
5. 运行普通 `pytest` 获取 fresh test evidence。
6. 复用已有 live sync / PDF export 报告证据；如证据不足，再执行低频验证命令，但不生成可提交 artifact。
7. 判断 `backend/tests/test_browser_access.py` 的性质：
   - 如果仍测试已知 403 homepage 路径且与当前 RSS/browser article strategy 不匹配，则视为临时诊断文件并删除。
   - 如果能作为长期 regression probe 且默认跳过，不破坏测试体系，则保留并纳入报告。
8. 创建 `docs/M1_FINAL_FREEZE_REPORT.md`，包含冻结规则。
9. 若审计通过，更新 `docs/00_PROJECT_STATE.md` 添加 `M1 Freeze Passed` 和 M1 freeze 变更规则。
10. 再次检查 `git status`、`git diff --stat`、artifact 扫描。
11. 提交 `docs: freeze M1 source pipeline handoff`。
12. 输出最终摘要、冻结接口、数据契约、测试证据、M2 readiness 和 commit hash。

## 5. 方案选型理由

这是冻结/移交 gate，不应修改 M1 实现或引入新能力。以文档、测试和当前代码证据为基础做审计，只有状态文档和 freeze report 可以更新；任何实现问题只记录为风险，不在本任务中修复。新增 `M1.x revision task` 规则可以保护冻结后的 M1 基线，避免 M2 或后续任务隐式改动 M1。

## 6. 优缺点对比

仅一个可行方案：审计当前 M1 状态并生成冻结报告。

优点：

- 边界清晰，不改变已通过的 M1 实现。
- 能给 M2 提供明确输入契约。
- 降低后续 Reader 系统误用 M1 数据/接口的风险。
- 冻结后变更治理清晰。

缺点：

- 如果发现 M1 残留风险，本任务只记录，不修复。
- M2 是否开始仍依赖 freeze 结论。
- 未来若需改 M1，必须通过额外 revision task。

## 7. 交付件

1. `alignment.md`
2. `docs/M1_FINAL_FREEZE_REPORT.md`
3. 如 freeze 通过，更新 `docs/00_PROJECT_STATE.md`
4. 对 `backend/tests/test_browser_access.py` 的保留或删除决定
5. Freeze 后 M1 变更规则记录
6. Git commit：`docs: freeze M1 source pipeline handoff`

## 8. 交付件验收指标

1. `docs/M1_FINAL_FREEZE_REPORT.md` 存在。
2. 报告包含：
   - Current Status
   - Architecture Freeze
   - Data Contract Freeze
   - Interface Freeze
   - Test Evidence
   - Known Risks
   - M2 Readiness
   - Post-freeze Change Rule
3. 报告明确记录 M1 Source Pipeline、M1 Verification、M1 PDF Export 均为 PASS。
4. 报告明确冻结 RSS Discovery、Playwright Browser Access、Parser、Converter、Storage、Validation、PDF Export。
5. 报告明确 Article schema 和 metadata 字段。
6. 报告明确 M2 readiness，只能为 A/B/C 之一。
7. 报告和项目状态明确记录：Freeze 后任何 M1 实现变更必须新建 `M1.x revision task`，不得直接修改冻结代码。
8. 未修改 `backend/app/crawler/`、M1 implementation、Verification 标准。
9. 未实现 M2 Reader、Search、RAG 或 Learning System。
10. `docs/00_PROJECT_STATE.md` 仅在 freeze 通过时增加 `M1 Freeze Passed` 和 freeze 变更规则。
11. 提交前确认无 PDF、HTML、图片、trace、profile、cache、临时 artifact。
12. commit message 为 `docs: freeze M1 source pipeline handoff`。
