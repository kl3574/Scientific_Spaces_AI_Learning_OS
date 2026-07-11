# P2-006 Post-Corpus Product Hardening and Recovery Audit

## 1. 背景

项目已完成全语料处理。当前任务是强化本地数据资产管理、备份、恢复、清理与健康检查，不重新爬取文章、不批量生成 PDF、不修改业务内容。

## 2. 需求

1. 盘点 `.local_data` 数据资产并划分 Tier 1/2/3。
2. 建立确定性的统一数据清单。
3. 实现 essential/complete 备份、校验和隔离恢复。
4. 实现安全清理、健康检查和容量审计。
5. 执行真实 essential 备份、验证和 `/tmp` 恢复演练。
6. 使用多并发加速本地文件扫描、哈希、验证和独立测试。
7. 禁止并发爬取 Scientific Spaces，禁止重新生成全部 PDF。
8. 禁止提交运行时语料、备份包、恢复目录或敏感文件。

## 3. 目的

建立可验证、可恢复、可维护的本地数据运维体系，并判断项目是否具备进入 v1.1 release-readiness audit 的条件。

## 4. 计划执行方案

1. 检查返工记录、路线图、工作区和现有存储接口。
2. 审计现有数据路径、manifest、fingerprint 与容量。
3. 在 `backend/app/operations/` 实现资产模型、清单、备份、校验、恢复、清理、健康检查和容量检查。
4. 在 `scripts/ops/` 提供对应 CLI。
5. 对只读操作使用有界线程池，默认 4 个 worker，并支持 `--workers` 调整。
6. 并发执行文件哈希、记录计数、独立资产健康检查和备份验证；所有输出按路径排序，保证结果确定。
7. 备份归档写入、restore 原子切换、cleanup 删除等写操作保持串行，避免归档损坏或竞态。
8. 可独立的 backend tests、frontend build 和只读回归检查并发运行；真实备份和恢复演练按依赖顺序执行。
9. 在 `/tmp` 完成 essential backup -> verify -> restore -> derived capability smoke，并清理临时产物。
10. 更新 README、项目状态和完整审计报告，通过后提交指定 commit。

## 5. 方案选型理由

有界并发适合当前主要耗时点，即大量文件扫描与 SHA-256 计算。归档写入、恢复切换和删除操作不适合多写并发，因此采用“并发读取与计算、串行提交与变更”的模型，在提高速度的同时保持确定性和恢复安全。

## 6. 优缺点对比

- 有界并发，默认 4 workers（采用）：明显加速扫描和校验，资源占用可控，输出仍可确定；实现中需要处理结果排序和异常聚合。
- 高并发 8 个以上 workers：可能进一步加速 SSD 环境，但容易造成磁盘争用、内存压力，反而降低归档速度。
- 完全串行：逻辑最简单，但对 PDF、Markdown、RAG、Graph 等大量资产的校验明显过慢。

并发只用于本地只读工作，不用于站点抓取。

## 7. 交付件

- `backend/app/operations/` 运维模块。
- `scripts/ops/audit_local_data.py`。
- `scripts/ops/backup_local_data.py`。
- `scripts/ops/verify_local_backup.py`。
- `scripts/ops/restore_local_backup.py`。
- `scripts/ops/cleanup_local_data.py`。
- `scripts/ops/check_local_system.py`。
- 运行时统一清单 `.local_data/scientific_spaces/operations/local_data_manifest.json`。
- `backend/tests/` 对应测试。
- `docs/POST_CORPUS_HARDENING_RECOVERY_REPORT.md`。
- 更新 `README.md`、`.gitignore`、`.env.example`。
- 通过时更新 `docs/00_PROJECT_STATE.md`。
- 通过时提交 `feat: harden local data backup and recovery`。

## 8. 交付件验收指标

1. 清单覆盖 Article、classification、Markdown、PDF、RAG、Graph、Learning、Zotero 和 Tutor 数据，且 fingerprint 可重复。
2. 并发运行与串行运行生成相同的确定性 manifest。
3. essential backup 默认排除 PDF 和可重建资产，不包含 `.env`、密钥、缓存或浏览器 profile。
4. backup 可打开，文件哈希、数量、profile 和路径安全检查通过。
5. restore 默认只允许空目录，并防止路径穿越、symlink escape 和部分恢复。
6. `/tmp` 恢复后 Article 数量和唯一 URL 均为 1,311，缺失 content 为 0，Article fingerprint 和 classification registry 保持一致。
7. Learning、Zotero、Tutor 等用户数据计数保持一致。
8. 至少完成一种派生能力恢复后验证。
9. cleanup 默认 dry-run，Tier 1 永不被普通清理删除。
10. health check 输出 PASS/WARN/BLOCKED，并为每个问题提供 remediation command。
11. backend pytest、frontend build和规定回归检查通过。
12. 不重新爬取文章、不重新生成全部 PDF、不修改 Article.content。
13. 仓库中没有备份包、恢复数据、PDF、HTML、trace、cache、`.env` 或运行时语料。
14. 最终报告明确给出 PASS/CONDITIONAL/BLOCKED 和 A/B/C 推荐结论。

## Confirmation

用户已确认：确认执行，方案准确无误。
