# Web UI Task Manager Operational Audit Trace

## 结论

已完成 Web UI 任务管理操作审计闭环。实现与计划一致：单条 stop/delete/rerun 和批量 stop/delete/rerun 均写入追加式 JSONL 审计记录，并提供 `/tasks/audit.md` Markdown 导出。

## 对齐结果

- 审计落盘：新增 `orchestrator/infrastructure/persistence/web_job_audit_log.py`，默认写入 `.omx/web-job-audit.jsonl`。
- 单条操作：`stop_task()`、`delete_task()`、`rerun_job()` 写入 `single_stop`、`single_delete`、`single_rerun` 事件。
- 批量操作：`batch_tasks()` 写入 `batch_stop`、`batch_delete`、`batch_rerun` 事件，记录 selected、processed、skipped、failed、run_ids 和原因明细。
- 导出入口：新增 `GET /tasks/audit.md`，任务管理页提供 `操作审计` 链接。
- 可浏览页面：新增 `GET /tasks/audit`，直接展示最近 50 条操作审计记录，并保留 Markdown 导出入口。
- 删除边界：删除仍只移除 Web Job 记录，不删除 run 目录和已有审计产物；删除前 job 快照进入审计 details。

## 验证证据

- `python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"`：8 passed, 44 deselected。
- `python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py`：通过。
- `python -m pytest -q tests/test_web_ui.py`：52 passed。
- `python -m pytest -q`：137 passed。

## 2026-06-08 增量验证

- `python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"`：8 passed, 44 deselected。
- `python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py`：通过。
- `python -m pytest -q tests/test_web_ui.py`：52 passed。

## 2026-06-08 审计筛选增量

- `/tasks/audit` 新增 `event_type` 筛选，支持在最近 50 条审计记录内按事件类型查看。
- 无效事件类型会回退到 `all`，避免空白或误导性视图。
- 新增测试覆盖 `batch_rerun` 筛选和无效筛选回退。

## 2026-06-08 审计搜索增量

- `/tasks/audit` 新增关键词搜索，覆盖事件类型、消息、Job ID、Run ID、请求上下文和 details/reasons。
- 搜索与事件类型筛选组合生效，仍只读取最近 50 条 JSONL 记录，不修改审计文件。
- 新增测试覆盖按 `missing task.json` 原因搜索和按 Job ID 搜索。

## 2026-06-08 审计记录数量增量

- `/tasks/audit` 新增 `limit` 参数和页面下拉，可选择最近 25、50、100、200 条。
- 默认保持 50 条；非法 limit 回退到 50，避免异常或过大读取。
- Markdown 导出仍保持最近 50 条，维持原分享产物语义。

## 剩余风险

- 审计文件第一版为追加式 JSONL，未做轮转；当前 Markdown 导出只读取最近 50 条，避免大文件影响页面响应。
- 审计写入失败不会阻断原操作，符合可用性优先策略，但失败只静默忽略，后续可接入 Web 日志提示。
