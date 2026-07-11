# P2-005 Optional Local PDF Export Workflow Alignment

## 1. 背景

- P2-004 Tutor Source Selection over Full Corpus 已完成并提交。
- 当前任务是 P2-005，为 1,311 篇本地 Article/Markdown 生成可选 PDF 副本。
- PDF 仅是本地派生阅读格式，不替代 Article.content、RAG、Graph 或 Tutor 数据源。
- 用户已确认本执行方案。

## 2. 需求

1. 开始前 push P2-004 并确认 GitHub Actions、分支同步和干净工作区。
2. 实现默认离线 Mode A，支持单篇、范围、全量、resume、rebuild 和 1-4 workers。
3. Mode B 明确为默认关闭的 source print-parity probe；只允许显式 opt-in、小样本、单并发和低频访问。
4. 使用本地 HTML、Playwright Chromium 和本地 KaTeX 或等价能力渲染 PDF。
5. 远程图片显示占位符；仅嵌入受控根目录中已存在的本地图片，禁止隐式下载。
6. 生成原子 JSON/CSV manifest、summary、validation 和 failure registry。
7. 执行 20 篇代表性 pilot、1,311 篇全量导出及幂等复跑。
8. 所有 PDF、HTML、manifest、cache、profile 和日志保持 Git ignored。
9. 不修改 Article.content、Markdown library、RAG、Graph、Tutor 或 source pipeline。

## 3. 目的

建立可恢复、可验证、严格离线的本地 PDF 派生资料库，并以全量数据证明完整性、公式保真、零网络访问和幂等性。

## 4. 计划执行方案

1. 检查 Git；临时 stash 本 alignment，并在 `.git/info/exclude` 本地排除 hook 生成的 `AGENTS.md` 与 `roadmap.md`，完成 clean pre-sync。
2. Push 当前 P2-004 提交到 `origin/main`，等待 backend pytest 和 frontend build CI。
3. 恢复 alignment，读取所有指定文档及 export/corpus/frontend 现状。
4. 并发审计本地依赖、输入数据、现有 PDF 能力和测试边界。
5. 先补失败测试，再实现输入模型、HTML 模板、公式、图片、文件名、manifest、验证、resume 和并发协调器。
6. 实现 CLI；Mode A 默认离线，Mode B 必须显式授权并强制 `limit<=10`、`workers=1`、`delay>=8`。
7. 运行 20 篇代表性 pilot，生成临时视觉检查材料，审计后删除。
8. Pilot 通过后按用户追加要求用 `workers=4` 导出 1,311 篇，并执行 resume 幂等复跑。
9. 并行运行后端测试、前端 build、RAG/Graph/Tutor 回归；更新报告和状态。
10. 执行 artifact/privacy 审计并提交。除非另有要求，不 push P2-005 最终提交。

## 5. 方案选型理由

- Playwright 复用现有 Chromium 能力，可稳定输出 A4 PDF。
- 本地 KaTeX 资源避免 CDN 和公式静默丢失。
- 图片采用 A+B：远程占位符，仅嵌入已存在且位于受控根目录的本地图片。
- 默认两个持久 worker 各自拥有独立 browser context/page；主线程串行原子写 manifest。
- Reader PDF endpoint 非 PASS 必需，本轮优先保持产品接口不变。

## 6. 优缺点对比

### 本地 HTML + KaTeX + Chromium（选定）

- 优点：打印效果稳定、公式可审计、完全离线、可执行视觉检查。
- 缺点：依赖本地 Chromium/KaTeX 版本，首次全量导出耗时较长。

### 仅保留 LaTeX 原文（未选）

- 优点：实现简单。
- 缺点：只能标记 CONDITIONAL，不满足公式渲染 PASS。

### 源站打印（仅可选 probe）

- 优点：接近官网版式。
- 缺点：依赖外部站点，不适合作为 1,311 篇默认流程。

## 7. 交付件

- `backend/app/export/local_pdf.py`
- `scripts/export/export_local_corpus_pdfs.py`
- backend tests 与小型非运行时 fixtures
- `docs/LOCAL_PDF_EXPORT_REPORT.md`
- 更新 `docs/00_PROJECT_STATE.md`、`README.md`、`.env.example`、`.gitignore`
- ignored runtime PDF library、manifest 和验证报告
- Git commit：`feat: add offline local PDF export workflow`

## 8. 交付件验收指标

- 输入为 1,311 Articles、1,311 unique URLs、missing content 0、duplicates 0。
- Pilot 20 篇覆盖公式、长短文、图片、代码、表格和 legacy，并通过结构及视觉审计。
- 全量覆盖 1,311，validation/formula/empty/corrupt failures 均为 0。
- 第二次运行：unchanged 1,311、exported 0、regenerated 0、failed 0。
- external network requests 为 0。
- Backend tests、frontend build、RAG/Graph/Tutor 回归全部通过。
- Git 中无 PDF、runtime manifest、HTML、语料、索引、Graph、cache 或本地路径泄露。
- Mode B 默认关闭且未用于全量导出。
