# Task Alignment - Milestone 0 Engineering Foundation

## 1. 背景

当前任务是执行 `kl3574/Scientific_Spaces_AI_Learning_OS` 的 `Milestone 0 - Engineering Foundation`。

仓库已有 Bootstrap 文档和空工程目录，当前只允许建立工程骨架，不允许实现 M1-M7 的业务功能。

用户补充的工程约束：

- 不直接修改已有设计文档和 Milestone 文档内容。
- 如发现设计问题或规范缺口，创建 ADR，不直接改变规范。
- Backend 必须使用 `pyproject.toml` 管理依赖。
- Frontend 必须提交 `package.json` 和 `package-lock.json`。
- Git commit 前必须检查 `git status` 和 `git diff --stat`。
- 禁止提交 `.env`、`node_modules`、缓存文件、大规模生成文件。
- 保持未来 M1-M7 扩展兼容。

## 2. 需求

1. 读取指定文档：
   - `docs/00_PROJECT_STATE.md`
   - `docs/02_TDD.md`
   - `docs/03_SOP.md`
   - `milestones/M0_FOUNDATION.md`
   - `docs/15_ACCEPTANCE.md`
   - `docs/31_MVP_BOUNDARY.md`
2. 输出 `Environment Report`，检查：
   - `git`
   - `gh auth`
   - `python`
   - `node`
   - `docker`
3. 保持已有文件，建立并完善：
   - `backend/`
   - `frontend/`
   - `tests/`
   - `docs/`
4. Backend 技术冻结：
   - Python 3.11
   - FastAPI
   - `backend/pyproject.toml` 管理依赖
5. Backend 结构：
   - `backend/app/main.py`
   - `backend/app/api/`
   - `backend/app/core/`
   - `backend/app/models/`
   - `backend/app/services/`
   - `backend/tests/`
6. Backend 实现：
   - `GET /health`
   - 返回 `{"status":"ok"}`
   - 增加 pytest 测试
7. Frontend 技术冻结：
   - Next.js 15
   - TypeScript
   - App Router
   - TailwindCSS
8. Frontend 首页显示：
   - `Scientific Spaces AI Learning OS`
9. Frontend 必须提交：
   - `frontend/package.json`
   - `frontend/package-lock.json`
10. Docker Compose 启动：
    - backend
    - frontend
11. Docker 验证：
    - `localhost:8000/health`
    - `localhost:3000`
12. CI：
    - `.github/workflows/`
    - PR 触发
    - backend pytest
    - frontend build
13. Validation：
    - `pytest`
    - `npm run build`
    - `docker compose up`
14. 更新 `docs/00_PROJECT_STATE.md`：
    - Version: `v0.1.0`
    - Phase: `M0 Completed`
    - Status: `Engineering foundation implemented`
15. Commit:
    - `feat: implement M0 engineering foundation`
16. Push:
    - `origin/main`

## 3. 目的

完成 M0 工程基础，使新机器 clone 后可以通过 Docker 启动基础 backend/frontend，并通过 CI 验证测试和构建，同时保持后续 M1-M7 扩展空间。

## 4. 计划执行方案

1. 写入本次完整对齐内容到 `alignment.md`。
2. 按要求读取项目状态、TDD、SOP、M0、验收与 MVP 边界文件；若缺少 `docs/15_ACCEPTANCE.md` 或 `docs/31_MVP_BOUNDARY.md`，不直接补写规范正文，改为创建 ADR 记录缺口与 M0 执行假设。
3. 检查 `git`、`gh auth`、Python、Node、Docker 环境和仓库状态。
4. 补齐 M0 工程目录和基础配置，保留已有文件。
5. 创建 FastAPI backend skeleton：
   - `backend/pyproject.toml`
   - `backend/app/main.py`
   - `backend/app/api/`
   - `backend/app/core/`
   - `backend/app/models/`
   - `backend/app/services/`
   - `backend/tests/`
6. 为 `/health` 编写 pytest 测试。
7. 创建 Next.js 15 frontend skeleton：
   - TypeScript
   - App Router
   - TailwindCSS
   - 首页标题
   - `package.json`
   - `package-lock.json`
8. 创建 backend/frontend Dockerfile 与根目录 `docker-compose.yml`。
9. 创建 `.github/workflows/ci.yml`，PR 触发 backend pytest 和 frontend build。
10. 配置 `.gitignore`，排除 `.env`、`node_modules`、缓存和构建产物。
11. 运行本地验证：
    - `pytest`
    - `npm run build`
    - `docker compose up`
    - 检查 `localhost:8000/health`
    - 检查 `localhost:3000`
12. 仅更新允许更新的 `docs/00_PROJECT_STATE.md`，不改其他已有设计或 milestone 文档。
13. 提交前执行 `git status` 与 `git diff --stat`，确认无禁止提交内容。
14. 提交并推送到 `origin/main`。
15. 输出最终报告。

## 5. 方案选型理由

该方案严格限定在 M0 工程骨架范围内，建立运行、测试、构建、容器和 CI 基础；依赖管理、锁文件、Docker 与 CI 都可复现；通过 ADR 处理规范缺口，避免擅自修改已有设计文档或 milestone 规范。

## 6. 优缺点对比

仅一个可行方案：按 M0 要求直接实现工程骨架，并加入补充工程约束。

优点：

- 范围清晰、可验证。
- 符合 M0 milestone 边界。
- 对未来 M1-M7 保持兼容。
- 避免擅自改动既有设计文档和 milestone 规范。

缺点：

- 不会提前提供任何业务能力。
- 若现有规范文件缺失，只能通过 ADR 记录假设，不能直接完善原规范文档。

## 7. 交付件

1. `alignment.md`
2. `backend/pyproject.toml`
3. `backend/app/main.py`
4. `backend/app/api/`
5. `backend/app/core/`
6. `backend/app/models/`
7. `backend/app/services/`
8. `backend/tests/`
9. `frontend/package.json`
10. `frontend/package-lock.json`
11. `frontend/` Next.js 15 TypeScript App Router TailwindCSS 工程
12. `docker-compose.yml`
13. `backend/Dockerfile`
14. `frontend/Dockerfile`
15. `.github/workflows/ci.yml`
16. `.gitignore`
17. `docs/00_PROJECT_STATE.md` 更新
18. 如发现规范缺口：`ADR/` 下新增 ADR 文件
19. Git commit 和 push 到 `origin/main`

## 8. 交付件验收指标

1. `GET /health` 返回 `{"status":"ok"}`。
2. `backend/pyproject.toml` 管理 backend 依赖。
3. `pytest` 成功通过。
4. `frontend/package.json` 和 `frontend/package-lock.json` 已提交。
5. `npm run build` 成功通过。
6. `docker compose up` 能启动 backend 和 frontend。
7. `localhost:8000/health` 可访问。
8. `localhost:3000` 可访问并显示 `Scientific Spaces AI Learning OS`。
9. CI 在 PR 触发时运行 backend pytest 和 frontend build。
10. `docs/00_PROJECT_STATE.md` 更新为 `v0.1.0 / M0 Completed / Engineering foundation implemented`。
11. 提交前已检查 `git status` 和 `git diff --stat`。
12. 提交内容不包含 `.env`、`node_modules`、缓存文件或大规模生成文件。
13. 提交信息为 `feat: implement M0 engineering foundation`，并推送到 `origin/main`。
14. 不修改已有设计文档和 Milestone 文档内容，除允许更新的 `docs/00_PROJECT_STATE.md`。
15. 不包含 M1 crawler/parser/storage、M2 reader/search、M3 RAG/embedding/FAISS/LLM 或任何业务代码。
