# P3-044 仿射候选内容人工审核准备报告

后续状态更新（2026-09-10）：用户阅读 v3 后回复“全部同意”，12/12 项参考内容审核通过。
决定绑定见[人工确认记录](reviews/P3_044_AFFINE_V3_HUMAN_DECISION.json)。v3 文件逐字冻结，
其中 PENDING 表示准备时状态；模型回答质量仍 NOT_RUN，资料用途仍为 development/regression。
后续用户已授权 GitHub 同步与冗余清理。下文保留准备阶段的验证与授权事实，
其中“本轮”、未提交 HEAD、0/12 和 NEXT_TASK 均指当时阶段，不是当前进度。
当前范围与下一步见[canonical task](tasks/P3-044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION.md)。
历史增量补丁的撤销命令仅适用于其原始基线，不能用于撤销后续已提交的同步改动。

日期：2026-09-10。状态：**PREPARED_PENDING_HUMAN_REVIEW**。

本轮自动核对、必要修订、审核包和静态候选快照已完成。
`human_review=PENDING`，`reviewer=null`，`approved_at=null`；0/12 题获真人确认。
模型自审和实际调用的独立 reviewer 均仅为非盲 `model_review`。
没有真实/付费模型评测、人工批准或发布。

直接阅读：[完整中文人工审核包](../backend/tests/fixtures/evaluation/tutor_generation/review_candidate_v3/review_package.md)。
候选摘要：[manifest.json](../backend/tests/fixtures/evaluation/tutor_generation/review_candidate_v3/manifest.json)。
两篇原文、每题问题和允许证据、原预期与修订、推导、禁止结论、等价答案和空白人工决定
都在同一个审核包中，无须从运行日志拼题。

## 基线与保护范围

当前分支 `codex/p3-044-tutor-mode-policy`，HEAD
`893197bf9ca8555078eddfc85225ff0428a436ad`。原 P3-044 未提交，HEAD 不是其完整实现快照。
本轮读取了适用入口、[原 canonical task](tasks/P3-044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION.md)、
[原实施报告](P3_044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION_REPORT.md)、原两篇 Article、
`arithmetic_truth.json`、实际 evaluator、测试和 CI 命令。没有适用的 AGENTS.md。
原任务记录继续作为历史记录，不改写其通过计数或据此授权发布。

编辑前绑定 619 个现有非忽略文件，其中包括原 P3-044 的 16 个已修改/未跟踪文件；
指纹及精确原文件副本位于 ignored `.local_data/p3-044-review-prep/baseline.json` 和
`original-files/`。完成时 617 个旧文件逐字不变，只有以下两处授权的评测变更：

- `backend/app/evaluation/tutor_generation.py`：添加真实用途
  `data_role=development/regression`、`unseen_holdout=false` 及相应比较说明。
- `backend/tests/test_tutor_generation_evaluation.py`：增加用途元数据断言。

保留历史 `acceptance` split ID，以便原基线比较继续可重放；它已经不是未见验收集。
原 16 文件中另 14 个逐字不变。生产代码、API、SourceSelector、拒答规则、原 Article、
Reader/Shell/Graph、前端、依赖锁和工作流全部保持原指纹，没有接管或终止用户服务。

原 `.local_data/p3-044/delivery.patch` 未写入、未执行，SHA-256 保持：
`ea4fbb8f637bb82cf6d56f017427f4ddd50d7348e1d0a4ffee763298dc4e9b23`。
没有 reset/stash/clean/commit/push/tag/Release，没有访问私有 Zotero、博客或下载依赖。

## 原资料与真实结论

两篇 Article 为原有 `synthetic-affine-inverse` 和 `synthetic-affine-validation`，
快照 `articles.json` 与原 `acceptance_articles.json` **字节相同**，没有另写文章替代。
它们明确使用实数、已知非零 a、已知 b 和精确关系 y=ax+b；该条件下的逆式、数值例和
两篇之间的内容均正确一致。a=0 或参数未知的题目明确替换相关前提，不能冒充原定理的反例。

材料已用于此前开发、调试和实现选择。旧五模式案例仅有请求传递/字段契约，没有数学
gold 或已审核参考答案；原问题 `Affine calibration inverse conditions and example`
缺少用于单项真值判断的精确目标。本轮明确化题目并补充必要边界，未将旧契约 PASS
转换为数学通过。原支持/反驳算术标签没有错误，保持不变。

| Case | 当前明确目标与结论 | 证据关系 | 期望行为 |
| --- | --- | --- | --- |
| AFF-01 explain | 原已知非零条件下逆关系、例子与类比说明正确 | SUPPORTED | ANSWER |
| AFF-02 derive | 逆式的存在和唯一性正确；逐步给等式依据 | SUPPORTED | ANSWER |
| AFF-03 qa | 固定 a=2,b=1,y=7，x=3 正确 | SUPPORTED | ANSWER |
| AFF-04 quiz | 固定例子的选择题知识与答案正确；教学格式另审 | SUPPORTED | ANSWER |
| AFF-05 research | 显式新增 Y=2x+1+ε、真实 x=3、ε 未知；本次误差是否≤1缺条件 | INSUFFICIENT | CONDITIONAL_ANSWER |
| AFF-06 | 原正例 x=3 正确，反代为7 | SUPPORTED | ANSWER |
| AFF-07 | 原错误主张 x=99 不成立，反代199≠7 | CONTRADICTED | CORRECT_PREMISE |
| AFF-08 | 改为 a=0,y=b，声称有唯一逆错误；所有实数都是解 | CONTRADICTED | CORRECT_PREMISE |
| AFF-09 | 改为 a=0,y≠b，声称存在解错误；无解 | CONTRADICTED | CORRECT_PREMISE |
| AFF-10 | a≠0 但未知，b=1,y=7；实际 x=3 与否缺条件，可答 x=6/a | INSUFFICIENT | CONDITIONAL_ANSWER |
| AFF-11 | a=2,y=7，b未知；实际 x=3 与否缺条件，可答 x=(7-b)/2 | INSUFFICIENT | CONDITIONAL_ANSWER |
| AFF-12 | 声称两篇已建立噪声精度/综述完整性，与原文明示否认冲突 | CONTRADICTED | CORRECT_PREMISE |

12 个候选标签为 SUPPORTED 5、CONTRADICTED 4、INSUFFICIENT 3，均待人工裁决。
“错误”在 AFF-07 等处指待反驳主张，不是说其 CONTRADICTED 标签错误。
旧主题任务的含混与新反事实题的缺条件，在各 case 的 `finding`、原值及修订建议中另列。
模型没有发现原两篇之间的冲突或原文错误，真人仍可提出异议。

一般结论由论证支持：减 b、除非零 a、反代与两解之差证明唯一性；a=0 时按 y=b/≠b
穷尽分支；未知 a/b 时构造满足新前提的一真一假实例。AFF-05 的扰动方程是题目新增假设，
不是来源事实。由该题设得到误差 |ε|/2，因此本次界限成立当且仅当 |ε|≤2；实际 ε 未知。
ε=0 与4给出一真一假实例，±2是闭区间边界。它不是“对所有 ε 都成立”的保证命题。
Python `fractions.Fraction` 独立核对 14 项有限算术；一般结论不以有限实验代替证明。

## 旧契约与内容修订

旧 `derive-no-formula` 在代码中受控替换第一篇正文，却保留原 Article ID。
原两篇实际均有公式，所以该程序门禁不能成为“原资料缺公式”的 oracle。
本包记录已有派生输入的完整正文、`legacy-affine-no-formula/v1` 标识与正文哈希，
不把它作第三篇替代 Article。其主题式问题含混，且“scale and shift mapping”仍有数学信息，
暂不强塞三分类或全面 ABSTAIN。`no-source`、`low-relevance` 等也保留其契约用途。

`legacy_contract_inventory` 共 12 项：11 项在本次数学题用途下 NOT_APPLICABLE，
1 项自动必要条件验证保持 NOT_IMPLEMENTED；本轮没有 pytest skip/xfail。
这些不是12个遗漏的数学题，也不是产品能力已实现。公开字符 span 仍不适用；
本包字符定位只对应固定源文件，不扩展产品接口。

准备过程保留了实际失败及修订，而非只保留最后通过结果：

| 版本 | 实际结果与修订 |
| --- | --- |
| v1 草稿 | 静态校验退出1：manifest 多出 scope 字段、case 缺少 candidate_version；没有被记为有效审核包 |
| v2 | 静态校验、202项测试及48次请求观察通过，但独立 model_review 发现噪声题目标/标签与若干量词不一致；不能据程序通过冻结错误语义 |
| v3 | 修改为本次实际误差目标，行为改为 CONDITIONAL_ANSWER；数值题和固定文档题量词逐项限定。独立复核与相关校验通过，仍 PENDING |

v1、v2 的五文件快照分别原样保存在 ignored
`.local_data/p3-044-review-prep/superseded/review_candidate_v1/` 与
`review_candidate_v2/`，旧运行输出同样保留；没有覆盖旧版本。v2 的原值与修订理由也直接
列入 v3 审核包。原实现的数学标签未为匹配当前输出而降低。

## 快照、身份与输入隔离

最终版本 `p3-044-affine-review/v3`。四个审核内容文件由 manifest 绑定：
原 Articles、cases、rubric 和完整中文 Markdown；manifest 不哈希自身。
候选摘要为：

`52656b4933d23dd1aa20c575a77c5ab318116720e60e995661264e51fd69295e`

JSON 规范化使用 UTF-8、排序对象键、紧凑分隔符、保留非 ASCII，拒绝 NaN/Infinity；
数组顺序和字符串内容不变，不做 Unicode/空白归一。另记录每个文件的原始字节哈希。
Markdown 按 UTF-8/LF 字节哈希；候选摘要哈希输入为
`{candidate_version, content_sha256:{文件名:规范化哈希}}`。
审核内容变化会得到不同候选摘要，旧确认变为 STALE，须保留旧版并重新 PENDING。

校验器强制当前 manifest/逐题人工字段未签署，拒绝伪已审核状态。
`confirmation_binding_status` 只检查内容绑定：即使字符串身份和摘要匹配，也只返回
UNVERIFIED，绝不认证人为真人或将模型决定升级为人工批准。没有通用审批系统或数据库。

观察器使用实际 TutorService、ConfiguredTutorRetriever、SourceSelector 和两种 spy 接口。
只将 `question`、`mode` 和允许的 Article 知识投影到产品输入。
对标签、参考答案、must_include、must_not_claim 和 rubric 注入专用唯一 nonce 后，
相同产品输入的实际生成请求必须不变；不会用普通词或数字是否出现判断泄漏。
对故意引入 oracle 泄漏的测试反例，验证能失败。

12题×legacy/structured两路，各执行原始/变形，共48次真实产品调用。
24/24路径都召回并选中各自要求的两条来源，24/24差分隔离通过，无拒答、无外部请求。
比较对象是 spy 捕获参数/messages 的规范化 UTF-8 JSON，不是未执行的 HTTP wire bytes。
检索失败反例会单列 FAIL、保留原 oracle；未触达生成器则隔离验证 NOT_RUN，不能算通过。

所有 spy 返回固定观察标记，回答质量一律 NOT_RUN/null。
旧 evaluator 的受控 x=99 响应仍显示合法来源且未被语义纠错，算术对照仍判 contradicted；
这记录现有主张核验缺口，没有被32项契约 PASS 掩盖，也不被当作真实模型质量实验。
本轮没有顺便修复该生产能力。

## 实际验证

全部相关 uv 调用使用 `UV_OFFLINE=true RUN_LIVE_TESTS=0`；真实服务观察复用隔离临时
synthetic 数据和 socket/DNS 禁网守卫。以下命令从本隔离工作区运行：

```bash
UV_OFFLINE=true RUN_LIVE_TESTS=0 uv run --project backend --extra dev pytest -q backend/tests/test_tutor_generation.py backend/tests/test_tutor_generation_evaluation.py backend/tests/test_tutor.py backend/tests/test_tutor_api_selection.py backend/tests/test_tutor_source_selection.py backend/tests/test_llm_provider.py backend/tests/test_tutor_review.py backend/tests/test_tutor_review_observation.py
UV_OFFLINE=true RUN_LIVE_TESTS=0 uv run --project backend python scripts/eval/validate_tutor_review.py
UV_OFFLINE=true RUN_LIVE_TESTS=0 uv run --project backend python scripts/eval/observe_tutor_review.py --output-dir eval_outputs/tutor_generation/review-observation-v3
UV_OFFLINE=true RUN_LIVE_TESTS=0 uv run --project backend python scripts/eval/run_tutor_generation_eval.py --baseline eval_outputs/tutor_generation_baseline/before.json --output-dir eval_outputs/tutor_generation/review-prep-final
python3 .local_data/p3-044-review-prep/check_arithmetic.py
git diff --check
```

输出目录要求新建且不覆盖；重放时使用新的目录名。

| 检查 | 实际结果 |
| --- | --- |
| P3-044 focused + 本轮校验/观察测试 | 退出0；202 passed、0 failed、0 skipped（原153＋新增49） |
| v3 静态校验 | 退出0；2篇、12题、四内容文件绑定有效；人工状态仍PENDING |
| v3 实际产品请求观察 | 退出0；48调用、检索24/24、隔离24/24，0失败、0请求隔离NOT_RUN、0跳过；回答质量NOT_RUN |
| 受影响的原离线评测 | 退出0；32/32契约；另1 NOT_IMPLEMENTED、1 NOT_APPLICABLE；两split各两项10/10定位指标；同证据请求仍1→5 |
| 独立有限算术 | 退出0；14 passed、0 failed；一般证明另见审核包 |
| 输出审计 | 原runner及新观察各3文件、0 findings；原始请求只留ignored目录 |
| 独立非盲model_review | 实际调用 reviewer，v3内容和代码无剩余必须修复项；不计人工审核 |
| 指纹/差异/增量补丁复核 | 617旧文件及旧P3-044补丁不变，仅两处授权评测差异；新增路径在本轮范围；反向应用检查通过 |

前端 build、全量 backend、原始 repeat-three E2E 本轮 **NOT_RUN**：只有评测资料/工具及
相关测试变化，当前用户明确要求不主动重复无关浏览器诊断。原 CI 门禁及断言未改弱。
原报告中的 backend 1244/4 skipped、frontend179、E2E894及附加门禁，仅为上轮历史证据，
不写作本次重跑。需联网的安全情报/远程CI、真实模型、私有来源、发布同样未运行，
原因是本轮授权边界。历史 Reader/Graph 故障保持原状态，未推断关闭。

原始验证证据留在 `.local_data/p3-044-review-prep/` 和
`eval_outputs/tutor_generation/review-observation-v3/`、`review-prep-final/`。
最终运行的代码HEAD/工作树变更标识读取 ignored 输出元数据，不在报告中嵌入自身哈希。

## 本轮增量与撤销

本轮共14个增量文件：修改上述2个既有评测文件；新增以下12个文件：

- `backend/app/evaluation/tutor_review.py`、`tutor_review_observation.py`。
- `backend/tests/test_tutor_review.py`、`test_tutor_review_observation.py`。
- `scripts/eval/validate_tutor_review.py`、`observe_tutor_review.py`。
- `backend/tests/fixtures/evaluation/tutor_generation/review_candidate_v3/` 下的
  `articles.json`、`cases.json`、`rubric.json`、`review_package.md`、`manifest.json`。
- 本准备报告。

本轮专用增量补丁为 ignored `.local_data/p3-044-review-prep/review-preparation.patch`，
其基线是本轮开始时的未提交 P3-044 内容。已执行的只是反向检查；若需要撤销本轮准备，
先保留需要的审核包，再**仅在此隔离 worktree**中运行：

```bash
git apply --reverse --check .local_data/p3-044-review-prep/review-preparation.patch
git apply --reverse .local_data/p3-044-review-prep/review-preparation.patch
```

这样恢复两个评测文件的本轮前内容、删除本轮新增公开文件，保留整个既有P3-044、
其旧补丁、原工作区修改和ignored运行证据。不要执行原P3-044撤销补丁。
本轮未实际执行撤销。

NEXT_TASK：由真实审核者逐项确认本批候选内容，并将决定绑定到相应版本。
