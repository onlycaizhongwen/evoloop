# Web UI Task Manager Operational Audit

## 恢复胶囊

- 任务需求：为 Web UI 任务管理页的单条/批量 stop、rerun、delete 增加持久化操作审计，并提供 `/tasks/audit.md` Markdown 导出。
- 关键决策：第一版使用追加式 `.omx/web-job-audit.jsonl`，不迁移 SQLite，不删除 run 目录或既有审计产物。
- 当前阶段：实现中。
- 已完成产物：`docs/codex/v1/plans/web-ui-task-manager-operational-audit.md`；`docs/codex/v1/status.md` 计划记录；新增审计 writer 初稿。
- 剩余工作：接入 Web handler、补测试、运行验证、补 trace/status 收口。
- 重要发现：现有批量 helper 只返回 processed/skipped/failed 计数，需要扩展为明细但保留页面提示兼容。

## 步骤列表

- [v] 建立计划与状态记录。
- [~] 新增审计 writer 并接入 Web 任务操作。
  - 当前产物：`orchestrator/infrastructure/persistence/web_job_audit_log.py`
  - 下一步：修改 `orchestrator/interfaces/web/main.py`，让单条/批量操作写入审计。
  - 涉及文件：`orchestrator/interfaces/web/main.py`、`tests/test_web_ui.py`
- [ ] 增加 `/tasks/audit.md` 导出与入口。
- [ ] 补测试并运行针对性/全量验证。
- [ ] 更新 trace 与 status。

## 研究发现

- `delete_task()` 当前直接删除 SQLite Web Job 记录，删除前需要读取 job 快照以写入 details。
- `_batch_stop_jobs()`、`_batch_delete_jobs()`、`_batch_rerun_jobs()` 当前只返回计数；审计需要 processed/skipped/failed ID 列表、run_ids 和跳过原因。
- `/jobs/{job_id}/rerun` 不保留 task manager 查询参数，审计仍可记录 source job 与 new job。

## 错误记录

- 暂无。
