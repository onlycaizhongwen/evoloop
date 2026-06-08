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

## 2026-06-08 审计结果筛选增量

- `/tasks/audit` 新增 `outcome` 参数和页面下拉，支持 `all`、`skipped`、`failed`、`clean` 四种只读筛选。
- `skipped` 匹配存在 `skipped_job_ids` 的记录，`failed` 匹配存在 `failed_job_ids` 的记录，`clean` 匹配无跳过且无失败的记录。
- 非法 `outcome` 回退到 `all`；筛选发生在读取最近记录之后、关键字搜索之前，不修改 JSONL 审计文件。
- 新增测试覆盖存在跳过、无跳过失败和非法结果回退。

## 2026-06-08 审计空筛选提示增量

- `/tasks/audit` 在 `total > 0` 且当前筛选组合无命中时，显示事件类型、结果和搜索词摘要，并提供清空筛选入口。
- 无审计记录时仍显示原始空状态，避免把“没有任何审计事件”和“筛选后无结果”混淆。
- 新增测试覆盖 `event_type=batch_delete`、`outcome=skipped`、`q=missing task.json` 的无命中组合。
- 该增量只影响页面展示，不修改 JSONL 审计写入、读取数量、Markdown 导出或删除边界。

## 2026-06-08 筛选态 Markdown 导出增量

- `/tasks/audit.md` 新增 `event_type`、`outcome`、`q`、`limit` 查询参数，和 `/tasks/audit` 复用同一套最近记录读取与过滤逻辑。
- `/tasks/audit` 的 `导出 Markdown` 链接会保留当前筛选条件；无筛选时仍输出原始 `/tasks/audit.md` 链接。
- 无命中筛选导出仍返回合法 Markdown 空结果，不修改 JSONL 审计文件，也不改变默认 Markdown 导出的 50 条语义。
- 新增测试覆盖筛选页导出链接、按 outcome 导出的 Markdown 内容和无命中筛选导出。
