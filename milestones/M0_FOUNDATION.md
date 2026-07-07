# Milestone 0 - Engineering Foundation

## Goal

建立可运行的软件工程基础。

## Scope

包含：

- GitHub 仓库
- Backend
- Frontend
- Docker
- CI

## Tasks

### TASK-M0-001 Initialize repository

要求：

- 创建 `backend/`
- 创建 `frontend/`
- 创建 `docs/`
- 创建 `tests/`

### TASK-M0-002 Backend skeleton

要求：

- FastAPI 启动。
- Health API：
  - `GET /health`
- 返回：

```json
{
  "status": "ok"
}
```

### TASK-M0-003 Frontend skeleton

要求：

- Next.js 启动。
- 首页显示：

```text
Scientific Spaces AI Learning OS
```

### TASK-M0-004 Docker

要求：

- `docker compose up` 成功启动。

### TASK-M0-005 CI

要求：

- 创建 GitHub Actions。
- 运行：
  - `test`
  - `build`

## Acceptance

新机器：

1. `clone`
2. `docker compose up`
3. 网页可访问。

## Forbidden

禁止实现业务功能。
