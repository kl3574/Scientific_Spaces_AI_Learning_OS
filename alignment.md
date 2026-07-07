# Task Alignment - M1 Article Discovery Strategy Evaluation

## 1. 背景

项目 `kl3574/Scientific_Spaces_AI_Learning_OS` 当前 M1 Source Pipeline 实现已完成，fixture pipeline 已通过，但 M1 Verification 仍为 `BLOCKED`。

现有证据显示：

- homepage `https://spaces.ac.cn/`: `403`
- archive discovery `https://spaces.ac.cn/content.html`: `403`
- Playwright homepage: `403`
- Playwright known article URL: `PASS`

当前剩余问题是 Article URL Discovery。本任务不是实现 M1，不修改 crawler 主流程，不解除 Verification Blocked，只评估是否存在合规 Article URL discovery strategy。

## 2. 需求

1. 读取：
   - `docs/M1_VERIFICATION_REPORT.md`
   - `docs/M1_LIVE_ACCESS_STRATEGY.md`
   - `docs/M1_BROWSER_ACCESS_EVALUATION.md`
   - `docs/M1_ALTERNATIVE_DISCOVERY_EVALUATION.md`
   - `docs/M1_ARTICLE_BROWSER_ACCESS_EVALUATION.md`
   - `docs/M1_BROWSER_ARTICLE_ACCESS_STRATEGY.md`
   - `ADR/0003-m1-live-source-access-blocker.md`
2. 创建：
   - `docs/M1_ARTICLE_DISCOVERY_STRATEGY_EVALUATION.md`
3. 报告必须包含 Current Status：
   - M1 Implementation: PASS
   - M1 Verification: BLOCKED
   - Remaining blocker: Article URL Discovery
4. 评估候选：
   - Candidate A: Official sitemap
   - Candidate B: RSS/feed
   - Candidate C: Official archive/index
   - Candidate D: Search engine discovery
   - Candidate E: Manual seed URL
5. 每个候选必须记录：
   - URL
   - HTTP status
   - title（如果有）
   - 是否发现 article URL
   - 是否合规
   - 是否推荐
6. 访问约束：
   - 低频
   - 少量请求
   - 不批量抓取
7. 禁止：
   - 全站扫描
   - 分页遍历
   - 大规模搜索
   - 保存文章数据
8. 不修改：
   - `backend/app/crawler/`
   - `docs/00_PROJECT_STATE.md`
   - `milestones/M1_SOURCE_PIPELINE.md`
   - Verification 标准
9. 不实现 M2-M7。
10. 不保存：
    - HTML 全文
    - 文章正文
    - PDF
    - 图片
    - 附件
    - cache
11. 只保存诊断元数据。
12. 报告最后必须包含：
    - `Discovery feasibility: PASS/FAIL`
    - `Recommended Strategy`
    - `Recommendation`
13. Recommended Strategy 只能选择：
    - A: Official discovery available
    - B: Approved alternative discovery required
    - C: Manual seed strategy required
    - D: No viable discovery strategy found
14. 如果只是增加报告，commit message 使用：
    - `docs: evaluate article discovery strategy`

## 3. 目的

判断 Scientific Spaces article URL 列表是否能通过合规 discovery strategy 获得，并决定是否值得进入后续 `M1 Source Access Strategy Revision`。

## 4. 计划执行方案

1. 覆盖写入本次 `alignment.md`。
2. 读取所有指定文档。
3. 检查当前 git 状态，识别已有未提交变更，避免提交无关内容。
4. 对 discovery 候选做少量诊断：
   - robots/sitemap 相关公开入口
   - 常见 RSS/Atom/feed 路径
   - 已知 archive/index 路径与少量公开索引入口
   - 搜索发现只做少量验证，不批量抓取
   - Manual seed URL 只基于已有已知 URL 评估
5. 只保存诊断元数据，不保存网页内容。
6. 创建 `docs/M1_ARTICLE_DISCOVERY_STRATEGY_EVALUATION.md`。
7. 验证未修改禁止路径、未新增内容 artifact。
8. 如本轮只新增报告，按规则提交：
   - `docs: evaluate article discovery strategy`
9. 输出最终结论和 commit hash。

## 5. 方案选型理由

该任务的核心是策略评估，不是 pipeline 实现。把候选 discovery source 分开评估，可以避免把已知 URL browser access 误认为 discovery 已解决；同时低频、元数据化诊断符合 source policy 和当前 blocker 的约束。

## 6. 优缺点对比

仅一个可行方案：低频诊断并生成 discovery strategy evaluation。

优点：

- 范围清晰。
- 证据可追溯。
- 不改变 M1 状态。
- 不保存内容。
- 可以明确区分 discovery 和 article access。

缺点：

- 若官方 discovery 入口不可用，结论可能仍需要人工批准替代策略。
- 搜索引擎发现只能少量验证，不能证明完整覆盖。

不可采用方案：

- 全站扫描或分页遍历：违反访问约束。
- 大规模搜索：违反访问约束。
- 保存 HTML/正文/附件：违反数据最小化约束。
- 修改 crawler/verification/project state：用户明确禁止。
- 实现 M2-M7：用户明确禁止。

## 7. 交付件

1. `alignment.md`
2. `docs/M1_ARTICLE_DISCOVERY_STRATEGY_EVALUATION.md`
3. Git commit：
   - `docs: evaluate article discovery strategy`
4. 最终输出：
   - `Discovery feasibility`
   - `Recommended Strategy`
   - `Recommendation`
   - commit hash

## 8. 交付件验收指标

1. 已读取全部 7 个指定文档。
2. 报告包含 Current Status。
3. 报告评估 sitemap、RSS/feed、archive/index、search discovery、manual seed URL。
4. 每个候选包含 URL、HTTP status、title、是否发现 article URL、是否合规、是否推荐。
5. 请求数量低频、少量。
6. 未修改 `backend/app/crawler/`。
7. 未修改 `docs/00_PROJECT_STATE.md`。
8. 未修改 `milestones/M1_SOURCE_PIPELINE.md`。
9. 未修改 Verification 标准。
10. 未实现 M2-M7。
11. 未保存 HTML 全文、正文、PDF、图片、附件、cache。
12. 报告明确输出 `Discovery feasibility`、`Recommended Strategy`、`Recommendation`。
13. 如提交，commit message 为 `docs: evaluate article discovery strategy`，不用 `fix:`。
