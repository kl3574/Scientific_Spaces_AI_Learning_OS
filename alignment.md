# Task Alignment - Resolve or Confirm M1 Live Source Access Blocker

## 1. 背景

当前任务是解除或确认延续 `M1 Verification Blocked` 状态。当前阻塞来自 M1 Verification Gate：默认线上 `python -m app.sync` 访问 `https://spaces.ac.cn/` 时返回 HTTP 403。

本任务首先诊断 403，不保证一定能通过代码修复。如果真实 source 仍不可访问，则保持 blocked，不修改 verification 标准，不用 fixture 替代 live 验证。若 `ADR/0003` 已覆盖当前 403 问题，则不重复创建 ADR，优先更新已有阻塞记录。真实站点诊断必须低频、最小请求量、合理 User-Agent，且不得尝试绕过访问控制。如果 live integration check 已确认同一 URL、同一访问路径稳定返回 403，则不重复高频尝试，只记录证据并保持 blocked。

## 2. 需求

1. 读取：
   - `docs/M1_VERIFICATION_REPORT.md`
   - `ADR/0003-m1-live-source-access-blocker.md`
   - `docs/00_PROJECT_STATE.md`
2. 分析 HTTP 403 原因：
   - User-Agent
   - headers
   - robots
   - timeout
   - retry
3. 创建访问策略报告：`docs/M1_LIVE_ACCESS_STRATEGY.md`。
4. 报告必须记录：
   - OS
   - Python version
   - requests version
   - network environment summary
5. 如需修改 crawler，只允许修改 `backend/app/crawler/`。
6. 保持 fixture 测试。
7. 增加 live access integration check，且必须独立标记，不影响普通 pytest。
8. 运行 `pytest`。
9. 运行默认真实 `python -m app.sync`，但如果 live integration check 已确认同一 URL、同一路径稳定 403，则不重复高频尝试，只记录已有证据。
10. 仅当真实 source sync 成功时，将 `docs/00_PROJECT_STATE.md` 从 `M1 Verification Blocked` 更新为 `M1 Verification Passed`。
11. 如果真实 source 仍不可访问：
    - 保持 `M1 Verification Blocked`
    - 更新 `docs/M1_LIVE_ACCESS_STRATEGY.md`
    - 优先更新已有 `ADR/0003-m1-live-source-access-blocker.md`
    - 不重复创建 ADR，除非发现新的架构决策或不同根因
    - 不修改 Verification 标准
12. 诊断真实站点时：
    - 不进行高频批量抓取
    - 使用合理 User-Agent 和访问频率
    - 诊断请求数量保持最小化
    - 不尝试绕过访问控制
13. 禁止：
    - 使用 fixture 替代 live 验证
    - 提交人工下载数据
    - 绕过站点访问策略
    - 实现 M2-M7
14. Commit rule：
    - 如果真实 sync 成功并解除 Blocked，commit message 使用 `fix: resolve M1 live source access`
    - 如果真实 sync 失败并保持 Blocked，commit message 使用 `docs: update M1 live source access blocker`

## 3. 目的

通过合规、低频、证据化诊断确认 403 的根因和可行访问策略；只有在真实 Scientific Spaces source sync 成功时，才解除 M1 Verification Blocked。若无法合规访问，则把阻塞状态、环境信息和后续建议更新到现有阻塞记录中，避免伪造 M2 readiness、重复请求站点或制造重复 ADR。

## 4. 计划执行方案

1. 将本次完整对齐内容写入 `alignment.md`。
2. 读取指定报告、ADR 和项目状态。
3. 检查当前已有 live 403 证据，避免无意义重复请求。
4. 采集环境信息：
   - OS
   - Python version
   - requests version
   - network environment summary
5. 以最小请求量复现或确认当前 live sync 403。
6. 分析访问策略：
   - 当前 downloader 的 User-Agent。
   - 少量合理 headers 组合。
   - robots.txt 可访问性和规则。
   - timeout 设置。
   - retry 行为。
   - 官方域名/备用域名响应情况。
   - 是否为当前网络环境被站点策略拒绝。
7. 创建或更新 `docs/M1_LIVE_ACCESS_STRATEGY.md`，记录诊断命令、请求数量、结果、环境信息、结论和建议。
8. 若有明确、合规、最小的 crawler 修复，只修改 `backend/app/crawler/`。
9. 增加独立标记的 live integration check，默认普通 `pytest` 不运行 live check。
10. 运行普通 `pytest`，确认 fixture 测试仍通过。
11. 以最小请求量运行 live integration check。
12. 对默认真实 `python -m app.sync`：
    - 若 live integration check 已确认同一 URL、同一访问路径一致 403，则不重复高频尝试，只在报告中记录该证据。
    - 若未确认，则运行一次默认真实 sync 并记录结果。
13. 如果真实 sync 成功：更新 `docs/00_PROJECT_STATE.md` 为 `M1 Verification Passed`，commit 使用 `fix: resolve M1 live source access`。
14. 如果真实 sync 仍失败：保持 `M1 Verification Blocked`，更新访问策略报告和现有 ADR/0003 阻塞记录，commit 使用 `docs: update M1 live source access blocker`。
15. 提交前检查 diff，确认没有人工下载数据、没有 fixture 替代 live 验证、没有 M2-M7。
16. commit 并 push 到 `origin/main`。
17. 输出最终报告。

## 5. 方案选型理由

该任务的核心是 live source access 诊断。站点 403 可能来自请求头、robots、反爬策略、网络环境或访问策略；不能用 fixture、人工下载数据或绕过站点策略来伪造通过。独立 live integration check 可以保留普通测试稳定性，同时让 live source readiness 有明确证据。若根因仍是现有 403 阻塞，则更新 ADR/0003 比新增重复 ADR 更清晰。低频最小请求量符合 source access 约束。记录 OS/Python/requests/network summary 有助于判断问题是否与运行环境相关。

## 6. 优缺点对比

方案 A：低频诊断并尝试合规 crawler 请求层修复；真实 sync 成功才解除 blocked。

优点：

- 满足真实 source 验证要求。
- 边界清晰。
- 尊重站点访问策略。
- 环境证据完整。

缺点：

- 如果站点策略拒绝当前环境，可能无法在代码层解除 blocked。

方案 B：用 fixture 或本地数据替代 live 验证。

优点：稳定。

缺点：明确违反约束。不采用。

方案 C：人工下载数据并提交。

优点：短期有数据。

缺点：违反约束，也不可复现。不采用。

方案 D：绕过站点访问策略。

优点：可能临时成功。

缺点：违反约束和 source policy。不采用。

方案 E：重复创建新的 403 ADR。

优点：简单。

缺点：违反用户新增约束，造成重复记录。不采用，除非发现新的架构决策或不同根因。

## 7. 交付件

1. `alignment.md`
2. `docs/M1_LIVE_ACCESS_STRATEGY.md`
3. 独立标记的 live access integration check
4. 如需且合规：`backend/app/crawler/` 内最小修复
5. 如果仍失败：更新 `ADR/0003-m1-live-source-access-blocker.md`，不重复创建 ADR
6. 如果真实 sync 成功：`docs/00_PROJECT_STATE.md` 更新为 `M1 Verification Passed`
7. Git commit：
   - 成功解除 blocked：`fix: resolve M1 live source access`
   - 仍 blocked：`docs: update M1 live source access blocker`

## 8. 交付件验收指标

1. 已读取指定 3 个文件。
2. 策略报告包含 User-Agent、headers、robots、timeout、retry 分析。
3. 策略报告记录 OS、Python version、requests version、network environment summary。
4. 策略报告记录诊断请求数量和频率控制。
5. live integration test 独立标记，普通 `pytest` 不依赖真实网络。
6. fixture 测试仍保留并通过。
7. 没有使用 fixture 替代 live 验证。
8. 没有提交人工下载数据。
9. 没有绕过站点访问策略。
10. 未进行高频批量抓取。
11. 若有代码变更，只发生在 `backend/app/crawler/`。
12. `pytest` 通过。
13. 默认真实 `python -m app.sync` 已执行并记录结果，或在 live integration check 已确认同一 URL、同一访问路径一致 403 时记录该证据并避免重复高频尝试。
14. 只有真实 source sync 成功时，`docs/00_PROJECT_STATE.md` 才改为 `M1 Verification Passed`。
15. 如果真实 source 仍不可访问，`docs/00_PROJECT_STATE.md` 保持 `M1 Verification Blocked`，并更新现有 `ADR/0003-m1-live-source-access-blocker.md`。
16. 不重复创建 ADR，除非发现新的架构决策或不同根因。
17. 未修改 M1 Verification 标准。
18. 未实现 M2-M7。
19. commit message 与结果匹配：
    - 成功解除 blocked：`fix: resolve M1 live source access`
    - 仍 blocked：`docs: update M1 live source access blocker`
