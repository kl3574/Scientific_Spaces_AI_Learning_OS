# P2-004 Tutor Source Selection over Full Corpus Alignment

## 1. 背景

- Scientific Spaces AI Learning OS 已完成 MVP，并进入 Post-MVP 全语料处理阶段。
- 全语料 RAG index、Knowledge Graph 与 Tutor 基础能力已存在；当前工作是让 Tutor 在全语料规模下稳定、可解释且有界地选择来源。
- 用户已确认采用方案 A。
- Graph 上下文只能在请求显式提供 `node_id` 时扩展；禁止根据问题文本自动推断或自动扩展 Graph。
- 当前 worktree 含 P2-004 的分阶段实现和待集成修改，必须保留已有用户修改并基于当前状态继续。

## 2. 需求

1. Tutor 复用全语料 RAG index，一次请求只执行一次 Article retrieval。
2. Explain、Derive、Quiz、Research 保持既有契约和拒答兼容性。
3. Research 至少需要两个独立 Article 来源；Derive 必须有公式证据；Quiz 必须基于可回答证据并避免重复问题。
4. 来源、chunk、context、Graph node/edge 都必须有硬上限和明确截断信息。
5. Graph 仅在请求显式提供 `node_id` 时读取，最多 20 nodes、30 edges；Graph 故障降级为元数据，不改变 Article grounding 主路径。
6. Zotero 和 Graph 仅作为补充来源，不得替代 Article 支撑；所有补充 payload 必须清洗、限长且不得泄露本地路径。
7. 提供严格的 42-case 全语料 Tutor 评估，覆盖质量阈值、拒答、来源预算、高度节点和延迟。
8. 前端显示 selection summary、来源折叠、Research 资料缺口，并提供可运行的 fixture/live smoke。
9. 保留现有 M1-M7 边界，不抓取新文章、不修改冻结的 source pipeline、不提交 runtime corpus/index/Graph/artifacts。
10. 使用并发代理处理互不重叠的后端、评估和前端域，再统一验证。

## 3. 目的

使 Tutor 在完整本地语料库上使用可追踪、可预算、可降级的来源选择策略，同时保持 Graph 扩展显式可控，为后续真实 provider 质量评估提供稳定工程基线。

## 4. 计划执行方案

1. 复核当前 worktree、P2-004 设计报告、既有提交和未提交修改。
2. 并发完成三个独立域：后端 Tutor 编排契约、42-case 评估工具、前端来源呈现与 smoke。
3. 对每个域先补失败回归测试，再实施最小修复，并进行独立代码审查。
4. 集成后运行后端定向及全量测试、前端测试与 build、CLI 参数检查、42-case 全语料评估、原有 RAG/Tutor 回归和前端 smoke。
5. 更新最终 P2-004 报告；只有全部硬门槛通过时才更新项目状态为 PASS。
6. 执行 artifact/privacy 检查、最终整体验证和代码审查，然后创建一个范围明确的提交。

## 5. 方案选型理由

方案 A 复用现有 RAG/Graph/Zotero 接口，在 Tutor 编排层增加确定性的来源预算和质量门禁，改动范围最小且与已冻结能力兼容。显式 `node_id` 保证 Graph 成本、语义和来源可审计，避免隐式实体识别造成不可预测扩展。

## 6. 优缺点对比

### 方案 A：有界 Article retrieval + 显式 Graph 扩展（已选）

- 优点：行为确定、成本可控、可测试、兼容既有 API、不会因自动实体识别误扩展 Graph。
- 缺点：调用方若不提供 `node_id`，即使问题涉及已知概念也不会获得 Graph 补充。

### 方案 B：根据问题自动识别概念并扩展 Graph（未选）

- 优点：用户无需显式传递 Graph 节点。
- 缺点：引入实体消歧、误匹配、额外延迟和不可预测上下文，不符合当前明确边界。

### 方案 C：预先合并 RAG 与 Graph 为统一检索层（未选）

- 优点：检索接口统一。
- 缺点：改变 M3/M6 已冻结接口和索引生命周期，工程风险与迁移成本明显超出 P2-004。

## 7. 交付件

- 后端 Tutor source selection、orchestration、Graph/Zotero supplement 边界和对应测试。
- `backend/app/evaluation/tutor_full_corpus.py`
- `backend/tests/fixtures/evaluation/full_corpus_tutor_cases.json`
- `backend/tests/test_full_corpus_tutor_evaluation.py`
- `scripts/eval/run_full_corpus_tutor_eval.py`
- 前端 Tutor selection summary/source presentation、单元测试和 smoke 脚本。
- `docs/FULL_CORPUS_TUTOR_SOURCE_SELECTION_REPORT.md`
- 必要时更新 `docs/00_PROJECT_STATE.md`。
- 本对齐文件 `alignment.md`。

## 8. 交付件验收指标

- Graph 读取只在非空显式 `node_id` 下发生，测试证明无 `node_id` 时零 Graph 调用。
- 单次 Tutor 请求最多一次 Article retrieval；Research 至少两个 Article，Derive/Quiz 拒答与证据门禁通过回归测试。
- Article、chunk、context、Graph、Zotero 来源均满足硬预算，截断和降级信息出现在 additive selection summary 中。
- 42-case fixture 严格为元数据且包含规定模式/拒答分布；评估 CLI 接受 `--rag-index-dir` 与 `--graph-dir`，门槛决定 PASS/CONDITIONAL/BLOCKED。
- 评估覆盖真实持久化 tiny index/Graph、显式高度 Graph node、全部 42 cases，并报告 expected-article miss 而不将其误作硬失败。
- 前端类型与后端 schema 一致，来源可展开/收起，路径不泄露，切换模式清理旧状态；fixture 和 live smoke 均可运行。
- 后端全量 pytest、前端 Tutor/Graph tests 与 production build 通过；原有 RAG/Tutor/Graph 评估无回归。
- 最终报告记录实测指标；只有所有硬阈值通过才标记 `P2-004 Tutor Source Selection over Full Corpus: PASS`。
- `git status` 与 artifact 扫描确认未提交 `.env`、runtime corpus/index/Graph、PDF、HTML dump、图片、trace/profile/cache 或 `node_modules`。
