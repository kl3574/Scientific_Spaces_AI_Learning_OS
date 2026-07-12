# P3-001 v1.1.0 Post-Release Validation and v1.2 Planning

## 1. 背景

Scientific Spaces AI Learning OS `v1.1.0` 已发布。发布 tag 为 annotated tag，预期 peeled target 为 `3efbe2a792a9853f1bac456f0287c3b5b62713ce`；`v1.0.0` 必须保持在 `8e1e5bbbdebb8835c7e1b05a42f69093d43ddee6`。本任务验证发布 tag 的真实用户路径并制定 v1.2 路线，不修改已发布版本或实现新功能。

## 2. 需求

1. 核验当前仓库、tag、GitHub Release 和发布不可变性。
2. 从远端 fresh clone 并 detached checkout exact `v1.1.0`。
3. 严格按 tag README 验证 Backend、Frontend、默认运行和 Docker。
4. 验证 legacy 与 `/v1.1` Article/Graph API 兼容性。
5. 验证默认 JSON persistence、SQLite migration 和 rollback export。
6. 使用小型 deterministic fixture 验证 inventory、health、backup、verify、isolated restore 和 cleanup。
7. 区分 tag-contained 与 post-release 文档并审计声明准确性。
8. 按 Critical、Important、Minor、Accepted Limitation 分类 findings。
9. 选择 A/B/C patch release 决策并制定证据驱动的 v1.2 路线图。
10. 清理临时目录、Docker 资源和后台进程，不提交 runtime/private artifact。

## 3. 目的

证明 `v1.1.0` 不依赖开发工作区、私有数据或完整 corpus 即可安装、启动、迁移、备份和恢复，并据实决定是否需要 `v1.1.1` 以及 v1.2 的受限范围。

## 4. 计划执行方案

1. 核验主仓库、远端、tag、Release、工作区和 tracked artifact。
2. 在 `/tmp/scientific-spaces-v1.1.0-validation` fresh clone exact tag，核验隔离性。
3. 按 tag README 安装依赖，运行 Backend tests 和 Frontend build。
4. 在隔离 runtime 启动 Backend/Frontend，验证默认离线配置、API 和页面状态。
5. 在 exact tag 上执行 Docker config/build/up/smoke/log/down。
6. 使用至少 37 篇 deterministic fixture 验证 Article/Graph legacy 与 versioned API。
7. 验证 Learning JSON/SQLite migration、rollback、幂等及失败原子性。
8. 使用小型 fixture 验证运维脚本、权限、hash、隔离恢复及 cleanup 安全边界。
9. 审计 tag 文档和 main 上的 post-release 文档。
10. 分类 findings、作出 v1.1.1 决策，按统一公式评分 v1.2 候选并限定范围。
11. 创建验证报告和路线图；仅在 PASS 且无需 hotfix 时更新项目状态。
12. 清理全部临时资源，执行最终测试、artifact 审计和 requirement-by-requirement 复核后提交。

## 5. 方案选型理由

远端 exact-tag 隔离 clone 能排除 main 后续提交、缓存和本地 corpus 干扰。小型 deterministic fixture 可验证冻结契约、迁移和运维行为，同时避免复制真实私有数据。

## 6. 优缺点对比

- 完整 exact-tag 隔离验证（采用）：证据最强，覆盖真实安装、运行、迁移、恢复；代价是耗时较长且依赖 Docker。
- 仅复用 CI：更快，但无法证明 README、fresh clone 和运维路径，不满足验收。
- 在当前 main 验证：容易执行，但混入 tag 后提交，不能作为 `v1.1.0` 发布证据。

只有完整 exact-tag 隔离验证符合任务要求。

## 7. 交付件

- `alignment.md`
- `docs/V1_1_POST_RELEASE_VALIDATION.md`
- `docs/V1_2_ROADMAP.md`
- `docs/00_PROJECT_STATE.md`（仅按最终决策更新）
- 必要的小型 fixture 或 validation script（仅在现有测试不足时）
- 一个与最终结论匹配的本地 Git commit
- 最终 22 项证据报告

## 8. 交付件验收指标

1. `v1.1.0` tag 类型为 `tag`，peeled target 精确匹配发布 commit；`v1.0.0` 未移动。
2. Fresh clone clean、detached，且无 `.env`、数据库、PDF、corpus、cache 或已有依赖目录。
3. Backend tests、Frontend build、默认 runtime 和 Docker 均有当前 exact-tag 证据。
4. 37 篇 fixture 的 Article/Graph legacy 与 versioned 契约通过。
5. JSON/SQLite migration、rollback、幂等和 failure atomicity 通过。
6. Backup、verify、isolated restore、cleanup 通过且不含 secret/PDF。
7. Findings 均有复现、证据、影响和推荐版本；patch 决策严格满足 A/B/C 条件。
8. v1.2 候选评分有理由，最终最多一个主功能、一个数据质量和一个平台主题。
9. 临时目录、容器、卷、进程和 archive 全部清理。
10. 不修改产品实现、冻结契约、已发布 tag 或 GitHub Release；不新增 runtime/private artifact。

## Confirmation

用户已确认：确认执行，方案准确无误。
