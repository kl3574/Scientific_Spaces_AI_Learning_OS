# Task Alignment - M1 Freeze Re-run

## 1. 背景

项目 `kl3574/Scientific_Spaces_AI_Learning_OS` 已完成 M1.1 Content Fidelity Revision，commit 为 `d446142c32ca9e6d12977703d5515aa9195a8354`。

本次任务是重新执行 M1 Final Freeze & Handoff Gate，重点验证 M1.1 是否解决 content fidelity 和 formula validity 阻塞问题，并判断 browser transient failure 是否只是风险而非阻塞。

## 2. 需求

1. 重新执行 M1 Freeze Gate。
2. 重点验证真实 live sync 的 `Article.content`：
   - 来自正文容器
   - 包含文章主体
   - 排除 sidebar、comments、share script、navigation
3. 抽样 3-5 篇真实文章，检查：
   - title 正确
   - content 开头为正文
   - content 长度合理
   - metadata 存在
   - references/images 保留
4. 验证 formula validity：
   - `formulas_valid=true`
   - inline `$...$` 平衡
   - block `$$...$$` 平衡
   - MathJax 转换未丢失
5. 将单篇 timeout / 单次 403 波动记录为 non-blocking risk，前提是 retry/failure logging 存在且 pipeline 仍可完成验证。
6. 明确 blocker 条件：
   - 数据质量失败：content 错误、formula 错误、metadata 丢失
   - pipeline 失败：RSS 无法发现、Browser 无法获取有效页面、Storage 无法保存
7. 如果通过，更新 `docs/00_PROJECT_STATE.md`：
   - `M1 Freeze Passed`
8. 检查并处理 `backend/tests/test_browser_access.py`：
   - 删除临时 homepage 403 probe，或
   - 保留为长期 regression test
   - 决定写入 Freeze Report
9. 不实现 M2 Reader、Search、RAG、Learning System。

## 3. 目的

确认 M1 当前输出已经稳定，可以作为 M2 Scientific Reader 的输入，并把 M1 Final Freeze 状态从之前的 BLOCKED 重新评估为 PASS 或继续 BLOCKED。

## 4. 计划执行方案

1. 写入本次 `alignment.md`。
2. 读取 M1 freeze、M1.1 revision、project state、data model、pipeline、PDF export、verification 等文档。
3. 检查 git 状态和未跟踪文件。
4. 运行普通 `pytest` 获取 fresh evidence。
5. 执行低频 live sync，最多 5 篇真实文章。
6. 读取 live sync 结果，统计：
   - article count
   - success/failure count
   - duplicate count
   - validation report
   - metadata keys
   - content heads/lengths
   - sidebar/comment/share script/navigation 排除情况
   - formula delimiter balance
7. 判断 browser transient failure：
   - 若只是单篇 timeout/403，且其余样本足以验证内容质量，则记录为风险，不阻塞。
8. 重新创建或更新 `docs/M1_FINAL_FREEZE_REPORT.md`，记录本次 re-run 证据。
9. 如果通过，更新 `docs/00_PROJECT_STATE.md` 增加 `M1 Freeze Passed` 和 M2 readiness。
10. 检查 artifact：无 PDF、HTML 下载件、图片、trace、profile、cache。
11. 提交 freeze re-run 结果。

## 5. 方案选型理由

本任务是 freeze gate re-run，不应修改 M1 实现。M1.1 已修复 parser/converter，本次只用 live evidence 验证修复结果，并把偶发 browser 失败与数据质量失败分开处理，避免把外部站点瞬时波动误判为 M1 数据契约失败。

## 6. 优缺点对比

仅一个可行方案：基于 M1.1 后的当前代码执行 freeze re-run 审计。

优点：

- 边界清晰。
- 不引入新功能。
- 直接验证真实 source pipeline 输出质量。
- 能明确 M2 是否可启动。

缺点：

- live 验证仍依赖外部站点和 Playwright 环境。
- 如果真实站点短时波动较大，可能需要记录为风险或重新运行 gate。

## 7. 交付件

1. `alignment.md`
2. 更新后的 `docs/M1_FINAL_FREEZE_REPORT.md`
3. 如通过，更新 `docs/00_PROJECT_STATE.md`
4. `backend/tests/test_browser_access.py` 的处理决定
5. Git commit：
   - 若通过：`docs: pass M1 final freeze handoff`
   - 若仍阻塞：`docs: rerun M1 final freeze gate`

## 8. 交付件验收指标

1. Freeze Report 明确记录：
   - M1 Source Pipeline: PASS
   - M1 Verification: PASS
   - M1 PDF Export: PASS
   - M1 Final Freeze: PASS/BLOCKED
   - M2 Readiness: A/B/C
2. Content Fidelity 记录为 PASS 时，必须有 3-5 篇真实文章证据。
3. Formula validation 记录：
   - `formulas_valid=true`
   - MathJax source preserved: true
   - Delimiter balanced: true
4. Browser transient failure 若存在，必须记录为 risk，并说明 mitigation：bounded retry + failure logging。
5. 如果通过，`docs/00_PROJECT_STATE.md` 包含 `M1 Freeze Passed`。
6. 未修改 M1 实现代码。
7. 未实现 M2/M3/M4-M7 功能。
8. 提交前无 PDF、临时 HTML、图片、trace、profile、cache artifact。
