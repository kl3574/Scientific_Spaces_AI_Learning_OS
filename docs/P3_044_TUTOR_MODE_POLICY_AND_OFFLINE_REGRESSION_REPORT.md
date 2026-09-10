# P3-044 Tutor 教学模式与离线产品回归实施报告

后续状态更新（2026-09-10）：[v3 准备与复核](P3_044_AFFINE_REVIEW_PREPARATION_REPORT.md)已完成，
用户对 12/12 项参考内容的“全部同意”已记录于[人工确认记录](reviews/P3_044_AFFINE_V3_HUMAN_DECISION.json)。
真实模型回答质量仍 NOT_RUN。后续用户已授权 GitHub 同步与冗余清理。
下文是原实现阶段的历史记录；PENDING、未提交 HEAD、无发布授权与 NEXT_TASK 均指当时状态。
当前进度和规划见[canonical task](tasks/P3-044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION.md)。
历史交付补丁的撤销说明仅适用于原始基线，不适用于后续已提交的同步改动。

状态：LOCAL COMPLETE / OFFLINE VERIFIED。代码、离线回归及独立代码审查完成；
人工数学/教学审核 PENDING，真实模型 NOT_RUN。仅本地交付，无发布授权。

日期：2026-09-10。

Canonical task：[P3-044](tasks/P3-044_TUTOR_MODE_POLICY_AND_OFFLINE_REGRESSION.md)。

## 1. 基线与实际范围

正式版本仍为 `v1.1.0`，candidate=None。起点及当前代码 HEAD 均为
`893197bf9ca8555078eddfc85225ff0428a436ad`；分支
`codex/p3-044-tutor-mode-policy`，工作树有本轮未提交改动。当前主工作区
存在 P3-043 Reader 草稿等用户修改，使用从 HEAD 新建的隔离 worktree，未复制、
覆盖或清理这些修改，未 stash/reset/commit/push。

已检查当前 README、project state、alignment/current canonical、v1.2 PRD、
architecture、evaluation plan、P3-004 report、ADR 0007，Tutor/LLM/RAG、既有评测、
测试入口和 CI。没有适用的 AGENTS.md，现有任务规范足够，未新增。

现有检索及 SourceSelector 已有模式差异，包括公式倾向和 research 来源多样性。
实测缺口仅在生成端：旧 `_mode_answer` 调用相同 `chat(question, contexts)`，
模式要求只在其返回后包装。固定仿射校准问题、两篇允许来源、相同顺序和原文，
五个模式各调用一次，旧请求变体数为 **1**。先运行真实链路回归测试，确实因
`1 != 5` 失败，再实现策略；没有回退旧代码来匹配报告。

另在新建临时目录用 `git archive HEAD backend` 取得未修改的原实现，复制相同
synthetic fixture，以现有 Python 环境重放基线捕获脚本。退出 0，五条请求/来源/
字段/拒答记录与首次捕获完全相等，旧请求变体仍为 1。原/现工作树均未回退。

## 2. 实现与接口

| 文件/函数 | 实际变化及目的 |
| --- | --- |
| `app/tutor/generation.py::build_generation_request` | 小型版本化任务策略；构建逐来源、可核查、有界请求 |
| `app/tutor/service.py::answer/_mode_answer` | 证据拒答之后构造任务，调用之前传递；上限拒答不会调用 provider |
| `app/llm/provider.py::ChatRequest/invoke_chat_request` | 可信 instruction、question、独立 contexts；显式结构接口及旧 chat 适配 |
| `app/llm/fake.py::chat_request` | 保留确定性 fake 和原 chat 行为；不把 fake 当真实教学模型 |
| `TutorService.quiz` | 保持 QuizQuestion 字段，去掉题干里的答案摘录，标注考点和证据辨认层次 |
| `app/evaluation/tutor_generation.py`、`scripts/eval/run_tutor_generation_eval.py` | 复用现有 fixtures、临时环境、原子输出和审计，直接观察产品服务 |
| 两个 `test_tutor_generation*.py` 与小型仿射 fixtures | 真实调用链正反例、脱敏输出与分母检查 |

策略版本为 `tutor-generation/v1`，评测策略为
`synthetic-product-observation/v1`。五模式调用前任务为：

| 模式 | 新生成请求的任务 |
| --- | --- |
| explain | 定义、直观解释、支持的简例、误解；类比不是证明 |
| derive | 假设/变量域、可核查逐步推导及来源/代数依据；缺条件或环节则停止并说明缺口 |
| qa | 先直接回答，再逐项对应证据，不扩张支持范围 |
| quiz | 考点/层次、围绕证据的问题及答案依据，题干不泄露答案 |
| research | 分开已有证据、推测、资料缺口和验证建议；不声称完整综述 |

通用规则要求相同符号在不同来源里的意义保持独立，没有明确支持的映射不能合并
推导。要求的是读者可核查的步骤和依据，不是模型私有思考过程。

内置结构请求把任务置于 system，用户问题及 evidence 置于 JSON user 数据。
来源正文、标题和伪造角色分隔符都保留为数据，不能改变真实 message 角色。
旧自定义 provider 无须新增方法：单次 `chat` 调用收到带可信任务和用户问题的
JSON question，以及包含来源 ID 的 JSON 证据；无 TypeError 回退或重试。
这种文本适配不保证第三方 provider 的最终系统角色安排或任务遵循。

输入上限仍取 SourceSelectionPolicy 的字符上限，默认 24,000。计入可信指令、
问题、来源 ID/标题、证据及嵌套 JSON 转义，按结构 messages 与 legacy arguments
的较大序列化字符数检查。它不是 token、UTF-8 字节或完整 HTTP 请求体上限；
model 名称和传输 envelope 不属于模型输入。已修正中文在传输层再次 ASCII
转义导致的计数不一致。不能完整装入时返回现有 `no_sources` 及清楚的上限说明，
保留真实 evidence/selection summary，生成器零调用。不会截断已经获准的证据，
以免切掉公式后仍沿用原有“证据足够”判断；这可能让原来接近上限的输入拒答。

`/tutor/ask` 的 quiz 模式经过生成策略；前端使用的 `/tutor/quiz` 继续采用
确定性的来源辨认题，以适配原有选项/精确答案评分，不冒充自由作答或应用能力测评。
原答案摘录上限保持不变，完整公式和资料仍应回到来源核查。

## 3. 离线评测及证据范围

输出明确分成四部分：

| 部分 | 当前观察范围 |
| --- | --- |
| `contract_results` | 实际产品策略传递、拒答、协议、异常和网络边界；未实现/不适用单独列出 |
| `fixture_results` | synthetic ID 成员关系、精确块内容匹配及一个限定算术对照，均带样本与分母 |
| `human_review` | PENDING，数学正确性/证据支持/教学清晰度均 null，完成 0/12 |
| `real_provider_results` | NOT_RUN，未授权；样本 0，质量/延迟/成本均 null |

开发集复用 Attention/CRB 两篇合成 Article；验收集另写两篇仿射校准 Article，
文章和主题均隔离。开发集保留现有 research 与其他模式不同的来源选择，不能用于
严格同证据比较。验收集五模式保持同问题、同来源顺序和同原文，修复后请求变体数
**5**。这是请求策略差异的证据，不是回答质量提高的证据。这些自写案例没有独立
人工金标准资格；待审核的验收集也不是盲测/真实模型泛化证据。

限定算术对照从实际产品返回文本提取 x，计算 fixture 的 `(7-1)/2=3`：
返回 `x=3` 与 `x=99` 都带合法来源，只有前者满足该合成算式。后者记录
contradicted，不能因为 ID 格式合法获得语义正确分；两者通用 semantic_correctness
均为 null。无法唯一解析、指数或分式表达为 unresolved，不通过标签预设评分。
该对照也揭示既有 grounding 只验证来源存在，无法自动拒绝错误主张。

回归覆盖实际 TutorService 与 ASGI：五任务差异、字段/来源顺序、无来源、低相关、
derive 缺公式、空 ID/非法来源 URL/缺章节、同符号分离、来源提示注入、超长问题和上下文、
精确上限边界、实际 OpenAI transport mock、旧 chat、自定义子类、超时/ValueError/
TypeError 等异常单次传播、原 HTTP 500，以及真实假索引陈旧指纹触发 503。
SourceSelector 本身未改。

必须保留的未实现项：通用必要数学条件识别、跨源符号语义协调、主张蕴含验证均
NOT_IMPLEMENTED；这轮只验证相应任务传达和既有公式拒答。公开 TutorSource 不提供
验证后的字符 span，span 评分 NOT_APPLICABLE，未编造定位。指令隔离测试不能证明
任意真实模型对提示注入免疫。

运行元数据保存 HEAD、工作树变更摘要哈希、策略版本、fixture 哈希、配置、分母、
失败/跳过和比较条件。原始基线及每次运行输出仅在受忽略的 `eval_outputs/` 和
`.local_data/p3-044/`；公开报告不复制完整 prompt、运行日志或本机绝对路径。
最终评测工作树标识在 ignored 输出中读取，报告不嵌入自身哈希，避免自引用循环。

Fixture 配置哈希：`91dfd006d0ad0fcf047791da3c6197097dd3196af41fd91820947ab69a17d309`。
原始基线规范化哈希：`e5c0874141db28fc9ad8161f0adee6371a4e98ada08440cc73d97bc2007689c3`。
本轮 10 个代码/测试/fixture 文件的候选标识：
`08f5b5d2a0ca9aba13affd44bf18ba3722d6bc95eaa75f6b433e4ae6dfe26a66`。
计算方法是对排序的相对路径→文件 SHA-256 映射作 compact、sort_keys JSON 后再取
SHA-256；映射留在 ignored `runtime-candidate.json`，不含后补文档。
当前 runner：32/32 已执行契约通过，0 失败，2 项分别为 NOT_IMPLEMENTED 和
NOT_APPLICABLE；不能计为 34/34。开发/验收集各有 5 个模式样本、2 篇 Article，
各自来源 ID 成员与精确块内容指标都是 10/10。输出审计为 3 文件、0 findings。

## 4. 验证记录

所有 uv 命令启用 `UV_OFFLINE=true`、`RUN_LIVE_TESTS=0`，使用隔离 fixture
环境。Backend 完整验证还附加只允许 loopback、拒绝私有 Zotero 端口的进程级
socket/DNS 守卫；各新测试/评测把所有 socket 尝试直接拒绝。无下载或真实请求。

| 实际命令/门禁 | 退出结果与计数 |
| --- | --- |
| `uv run --project backend --extra dev pytest -q backend/tests/test_tutor_generation.py backend/tests/test_tutor_generation_evaluation.py backend/tests/test_tutor.py backend/tests/test_tutor_api_selection.py backend/tests/test_tutor_source_selection.py backend/tests/test_llm_provider.py` | 0；153 passed，0 failed，0 skipped |
| `uv run --project backend --extra dev pytest -q` | 0；1244 passed，0 failed，4 skipped；592 条既有 E2E 脚本转义弃用 warning |
| `npm --prefix frontend run test:articles` | 0；98 passed |
| `npm --prefix frontend run test:references` | 0；23 passed |
| `npm --prefix frontend run test:tutor` | 0；24 passed |
| `npm --prefix frontend run test:graph` | 0；34 passed；四组共 179，0 failed/skip |
| `uv run --project backend python scripts/eval/run_tutor_generation_eval.py --baseline eval_outputs/tutor_generation_baseline/before.json --output-dir eval_outputs/tutor_generation/final` | 0；32/32 契约，synthetic fixture PASS，人工 PENDING，真实模型 NOT_RUN |
| `python3 scripts/security/check_workflow_policy.py` | 0；1 workflow、19 actions，pin/permission rate 1.0 |
| `python3 scripts/security/validate_suppressions.py` | 0；dependency=0、secret=0 |
| `python3 scripts/security/run_secret_audit.py` | 0；credible/reported/suppressed=0，范围为 tracked/history |
| `uv run --project backend python scripts/security/build_sbom.py --output-dir .local_data/p3-044/sbom` | 0；backend=40、frontend=244、combined=286 |
| `uv run --project backend python scripts/security/validate_sbom.py .local_data/p3-044/sbom --structural-only` | 0；覆盖/结构通过，forbidden=0；schema=NOT_RUN |
| `git diff --check` 与新增文件/新增行安全复核 | 0；16 个候选文件，新增真实密钥/本机绝对路径=0，受保护路径 diff=0 |
| 独立 reviewer 的两子类及 Quiz 回归 | 0；3 passed，44 deselected；后者不是 skipped |
| owned `npm run build` | 0；最终 E2E helper 的隔离生产构建完成，输入/依赖绑定及清理通过 |
| 原始 `scripts/e2e/run_product_e2e.py --repeat 3 --frontend-mode start` | 0；PASS，2563.8 秒；3×298=894 主检查通过、0 失败，附加门禁见下 |

4 个 skipped 已另用 `-rs` 核对：live source、browser live acquisition、live PDF
均需 RUN_LIVE_TESTS=1，本轮禁止；独立 local PDF integration 需额外的显式开关，
仍遵循现有 opt-in 默认，未启用。没有把这些项目写为通过。

完整依赖情报审计 `python scripts/security/run_dependency_audit.py` 会访问 OSV/
pip-audit/npm 服务；完整 `python scripts/security/validate_sbom.py <dir>` 会下载
schema/启动外部工具。均 NOT_RUN（本轮禁网），没有降级声称完整 CI PASS。
远程 CI、Docker 发布门禁、tag/Release 均未执行；没有本轮远程 SHA/CI 结论。

前端依赖由现有安装离线复制，非软链；原/副本完整树哈希同为
`bc742ff3249a71f08f150a9ca5b2e94896c6bf73e18a5519e04b814ed4a5ab49`。
首次 E2E 完成 owned production build，因独立审查已确认的两处本轮缺陷而有序
中止：INTERRUPTED_FOR_CONFIRMED_FIX，退出 1，630.78 秒，0 完整轮次。
只向经归属验证的任务 runner 发送 SIGINT；其五个任务进程消失，helper 的
bindings/cleanup 通过，任务端口释放。该次不计 PASS，不是观察超时后的重启。
修复并通过 focused 后才启动最终三轮，原脚本、断言、超时和顺序不变。

最终运行启动前绑定 331 个运行代码/测试/fixture 文件，清单哈希为
`46f4c2330c183624863a280dcac311758125fe86ddd207e2c9bcf727d5716020`；
原 E2E 脚本哈希为 `800dc6cb0cd553d26859c4263e42f32f39ef713c86ad8987fe42458e74d36edb`。
运行前后 331 个文件全部相同，HEAD、原脚本、原/副本依赖及主工作区 `.next`
均未变；文档补录单独处理。最终原始入口没有重启或修改脚本/断言：

```bash
SCIENTIFIC_SPACES_E2E_BACKEND_PORT=18000 RUN_LIVE_TESTS=0 \
uv run --offline --project backend python scripts/e2e/run_product_e2e.py \
  --repeat 3 --frontend-mode start \
  --output .local_data/p3-044/product-e2e-final.json
```

| 最终 E2E 范围 | 实际结果 |
| --- | --- |
| 主三轮 | 3/3 完整轮次，3×298=894 passed，0 failed |
| 重启持久化 | 4 passed，0 failed |
| Reader image | 3×8=24 passed，0 failed |
| Article navigation | 10 cases、36 checks 全通过，原 gate 再验为 true |
| Component contract | 6 cases 符合原 gate：3 现版 PASS、3 受控突变按预期 BLOCKED |

三个受控突变分别捕获 `stale_success_read`、`stale_failure_read`、
`replacement_fetch_missing`，是原门禁的有效反例，不能写成产品失败或六个正例。
主/image console、page、external 计数均为 0；navigation/component 清理前后
审计错误为 0。Chromium `149.0.7827.55`；owned runtime 全部清理，任务进程归零，
3000/18000 的 IPv4/IPv6 端口均空闲。结果文件 SHA-256：
`4bda478f3cbc7bc9ebd4b9bc31f1e3e8ccbb731e875de571754af81e1b35cba8`。
完整结果、before/after 绑定、命令/进度和精确摘要仅在 ignored
`.local_data/p3-044/product-e2e-final*`，没有写入公开日志。

首轮完整后端为 1228 passed / 10 failed / 4 skipped。原因是本任务测试启动环境
设置了高优先级 ARTICLES_FILE，遮住旧测试自己设置的 ARTICLE_STORE。移除冲突的
全局文件配置后，原 10 个失败项全部通过，随后全量 1242 passed / 4 skipped。
这是验证环境修复；未更改旧测试断言、产品检索或 health 检查。

## 5. 独立审查与修订

已实际调用无实现作者身份的独立 reviewer，审查 diff、调用接口、评测、数据边界
及前端 Quiz 评分。发现并处理的两项问题：

1. 内置 provider 继承新 ABC，会使旧子类意外加入结构调用，绕过原 chat 覆写，
   OpenAI 子类可能进入继承的联网实现；Fake 子类则丢失模式任务。
   两项真实服务反例先 RED。修正为内置确切类型的显式路由，第三方自行继承 ABC
   才 opt in；旧子类继续走带任务的 chat 适配。
2. 新开放式 Quiz 题干与现有精确选项评分不匹配。改成识记/理解/辨析的证据辨认题，
   保留响应和评分契约。自由作答评分未实现。

最终独立代码复核 PASS：两项问题已消除，未发现剩余生产/接口/数据安全阻塞；
独立 reviewer 实际重跑相应三项测试通过。人工数学/教学审核仍 PENDING；代码 reviewer 不是回答质量
审核者，不能替代第三部分 human_review。

## 6. 数据、兼容性与撤销

Article/M1、legacy、/v1.1、/v1.2 schema、SourceSelector/retrieval、RAG、P3-004
real planned gate、Reader/Shell/Graph、Zotero、学习持久化、数据库、备份恢复、
依赖锁和 CI 文件均不修改。fake 仍默认。只使用自写/既有 synthetic fixtures；
没有访问私有 Zotero/模型密钥/语料，没有外发、提交或发布。

接口另做动态核验：从 HEAD 归档启动独立的离线 schema 探针，与当前 `app.openapi()`
完整排序序列化比较，40 个 path 的公开 schema 完全相等，退出 0；共同 SHA-256 为
`339d3263820f7d25d84fb38cd3aea274abe64b7f331b583cc2d2f973a085058e`。
这证明声明的公开接口未改；行为兼容由上述实际服务/ASGI、原有全套和 E2E 分别验证。

Reader P3-042 保持 OPEN / CI BLOCKED；Graph P3-039 保持 OPEN / DEFERRED，历史
根因 UNKNOWN。任何本轮通过的 E2E 均不能证明这些历史故障已经修复。

撤销方式：主工作区无需操作。先保留需要的补丁/报告，再丢弃本轮专用 worktree 与
本地分支即可；也可仅在该专用 worktree 中恢复报告列出的 tracked 文件并删除本轮
新增代码/fixtures/文档。不要对主工作区执行 reset/clean/stash。本轮未自动执行撤销。

交付补丁位于该 worktree 的 ignored `.local_data/p3-044/delivery.patch`，包含全部
16 个候选文件，已做反向应用检查。需要撤销时，仅在该专用 worktree 中运行：

```bash
git apply --reverse --check .local_data/p3-044/delivery.patch
git apply --reverse .local_data/p3-044/delivery.patch
```

第二条会撤销代码和文档，因此先保留所需报告；不删除 ignored 验证输出和依赖，
不影响主工作区。这些是撤销说明，不是本轮已执行的写操作。

NEXT_TASK：独立人工核对两篇仿射验收 Article 及支持/反驳/缺条件预期，再冻结验收集。
后续仅记录：明确授权的真实模型小样本及检索比较；LearningAttempt/ReviewSchedule；
来源锚点笔记和可恢复导入/导出；人工审核先修关系及局部学习路径。
