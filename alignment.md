# P2-008 v1.1 API Compatibility and Migration Revision

## 1. 背景

当前正式版本为 `v1.0.0`，候选版本为 `v1.1.0`。P2-007 因无参数 `GET /articles` 从 v1.0 全量列表变为默认 20 条而 BLOCKED。当前任务先完成 P2-008，push 并等待 main CI，再从 clean main 重跑 P2-007。

禁止创建 tag、GitHub Release、移动 `v1.0.0`、访问 Scientific Spaces、重新抓取正文、重新生成 PDF 或重建 full corpus/RAG/Graph。

## 2. 需求

1. 从 peeled `v1.0.0` 恢复 `/articles` 全量、精确三字段、原始顺序、搜索和空结果契约。
2. 增加至少 37 Article 的 legacy 兼容回归和 1,311 Article full-corpus smoke。
3. 保留分页能力，通过明确版本化 endpoint `/v1.1/articles` 提供 page/page_size/q/category/sort。
4. Frontend Reader/Search 直接使用版本化分页 API，不在浏览器获取 legacy 全列表后分页。
5. 审计并恢复 M6 legacy Graph endpoint 的响应结构、total 语义和状态码兼容性。
6. 创建 M1 post-freeze revision ADR，不回滚已验证的正文抽取修复。
7. 实现可执行、幂等、失败原子的 JSON -> SQLite migration 和 SQLite -> JSON export/restore。
8. 保留 Learning state/bookmark/note/session 的字段、ID、timestamp 和 read_count。
9. 完成完整回归、artifact/secret audit、P2-008 commit/push/main CI。
10. 从 clean main 重跑 P2-007；只有 Recommendation A 才能记录 release readiness PASS。

## 3. 目的

将 full-corpus scaling 从冻结契约回归修订为可审计的向后兼容增强，并证明 Learning 数据可以安全迁移和恢复，为 v1.1 release readiness 提供完整证据。

## 4. 计划执行方案

1. Fetch 并审计本地/远端状态；如已有完整成果则只做审计、push 和 CI，不重复实现。
2. 从 `v1.0.0^{}` 提取 M2/M6 真实契约，建立代码、OpenAPI、测试和文档矩阵。
3. 先增加失败测试：37-Article legacy、版本化分页、full-corpus API、Graph compatibility、SQLite round-trip/idempotency/failure atomicity。
4. 恢复 `/articles` legacy adapter，并将现有分页能力迁移到 `/v1.1/articles`。
5. 将 Frontend Reader/Search 迁移到版本化 API。
6. 保留 M6 legacy 行为；可扩展行为使用新增/版本化接口。managed Graph build 使用安全兼容 adapter，若无法兼容则停止并选择 C。
7. 增加结构化 Learning migration/export 模块和 CLI，采用事务、临时文件与原子替换。
8. 创建 API revision report 和 M1 ADR，更新 README、CHANGELOG、release draft、checklist 与 project state；P2-008 PASS 时 Release Readiness 仅为 Pending re-audit。
9. 有界并发运行独立 backend/frontend/eval/smoke；共享 runtime、migration drill 和 Git/CI 串行执行。
10. P2-008 PASS 后提交 `fix: restore v1.1 API compatibility and migration safety`，push `origin/main` 并等待 CI。
11. 从 clean synced main 重跑 P2-007；若 A，提交并 push `docs: complete v1.1 release readiness audit`，等待 main CI。
12. 最终复核 branch、CI、artifact、tag 不变，并输出附件要求的 18 项报告。

## 5. 方案选型理由

版本化分页 endpoint 同时保留旧客户端契约和大语料性能。显式双向 migration 比仅切换 backend 可验证且不会误导 rollback。Graph 兼容 adapter 可避免以安全为名改变旧状态码，也避免破坏 managed Graph。

## 6. 优缺点对比

- Legacy adapter + versioned API + 双向 migration（采用）：兼容性最强且证据完整；代价是维护两套入口。
- 同一路径查询参数区分 legacy/paged：路径较少，但默认语义容易再次漂移。
- 接受 breaking change 并升 major：实施简单，但不满足 v1.1 minor 目标；仅在无法安全兼容时选择。

Graph 的危险原地 rebuild 不采用；switch-only rollback 不采用。

## 7. 交付件

- Article/Graph API 与 service 兼容实现。
- Frontend Reader/Search 迁移。
- Learning migration/export 模块及 CLI。
- 37-Article、Graph、migration 和 frontend 回归测试。
- `docs/API_COMPATIBILITY_MIGRATION_REVISION.md`。
- `docs/ADR/0005-m1-post-freeze-corpus-compatibility-revisions.md`。
- 更新 README、CHANGELOG、release draft、checklist、project state。
- 更新 `docs/V1_1_RELEASE_READINESS_AUDIT.md`。
- P2-008 和 re-audit commits 及对应 main CI 证据。

## 8. 交付件验收指标

1. Legacy `/articles` 对 37/1,311 条分别返回 37/1,311，顶层精确为 `items,total,query`，顺序与 v1.0 相同。
2. `/v1.1/articles` 默认 20、total 1,311、最大 page_size 100、无结果为空、错误参数为明确 4xx、排序确定。
3. Article detail 保持完整 content；Frontend 使用版本化 API。
4. M6 legacy 默认/空/错误/managed-profile 契约通过。
5. M1 ADR 完整，Article schema 不变，正文质量修复不回滚。
6. JSON <-> SQLite 全字段、ID、timestamp round-trip、幂等、失败不修改源、backup/restore 通过。
7. 完整 pytest、frontend tests/build、RAG/Graph/Tutor eval、Chromium 和 production smoke 通过。
8. 不访问 source、不重建 full corpus/RAG/Graph/PDF。
9. 无 tracked runtime/private/large artifact 或 secret。
10. P2-008 CI 成功；P2-007 唯一 Recommendation 明确，只有 A 才写 PASS/Ready to tag。
11. `v1.0.0` 不变，无 tag 或 Release 创建。

## Confirmation

用户已确认：确认执行，方案准确无误。
