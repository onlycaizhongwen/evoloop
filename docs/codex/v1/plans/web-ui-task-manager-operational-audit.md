# Web UI Task Manager Operational Audit Plan

## 目标

为任务管理页的停止、重新运行、删除和批量操作补齐可追溯审计能力，让运维动作不仅能执行，还能复盘是谁对哪些 Job 做了什么、哪些成功、哪些跳过、哪些失败，以及删除 Web Job 记录后仍能保留最小审计证据。

## 背景

当前已完成：

- `/tasks` 支持状态、质量、rerun 和搜索筛选。
- `/tasks` 支持当前页批量选择。
- 批量操作支持停止运行中任务、重新运行可重跑任务、删除 Web Job 记录。
- 删除只移除 Web Job 记录，不删除 run 目录和审计日志。

当前缺口：

- 单条和批量操作只通过页面即时提示反馈，缺少长期审计记录。
- 批量删除后，Web Job 记录从 SQLite 移除，任务列表不再能直接看到该操作发生过。
- 对演示和多人协作来说，操作证据分散在页面、run 目录和 commit 文档里，不够统一。

## 前置条件

- 保持现有 SQLite `web_jobs` 表结构不强制迁移，第一版优先使用追加式 JSONL 审计文件降低风险。
- 保持现有单条 stop/delete/rerun 和批量 stop/delete/rerun 行为不变。
- 不删除 run 目录、不删除 `.omx/runs/{run_id}` 下的审计产物。

## 实施步骤

### 1. 新增 Web Job 操作审计写入器

- 新增轻量服务，例如 `orchestrator/infrastructure/persistence/web_job_audit_log.py`。
- 默认写入 `.omx/web-job-audit.jsonl`。
- 每条记录至少包含：
  - `event_id`
  - `event_type`: `single_stop` / `single_delete` / `single_rerun` / `batch_stop` / `batch_delete` / `batch_rerun`
  - `created_at`
  - `actor`: 第一版固定为 `web`
  - `request_context`: status / quality / rerun / page / page_size / q
  - `selected_job_ids`
  - `processed_job_ids`
  - `skipped_job_ids`
  - `failed_job_ids`
  - `run_ids`
  - `message`

### 2. 接入单条操作

- `stop_task()` 成功冻结 running Job 后写审计。
- `delete_task()` 删除 Web Job 记录前读取并保存最小快照，再写审计。
- `rerun_job()` 成功创建新 Job 后写审计，记录 source job 和 new job。

### 3. 接入批量操作

- `_batch_stop_jobs()`、`_batch_delete_jobs()`、`_batch_rerun_jobs()` 返回结构化 summary，不只返回计数。
- `batch_tasks()` 统一写一条批量审计记录。
- 对 skipped/failed 明确记录原因，至少区分：
  - job missing
  - not running
  - running cannot rerun
  - missing task.json
  - exception

### 4. Run Detail / Task Manager 入口

第一版只做最小入口，避免 UI 扩张过大：

- `/tasks` 增加“操作审计”链接。
- 新增 `GET /tasks/audit.md` 导出 Markdown 审计摘要。
- Markdown 内容从 `.omx/web-job-audit.jsonl` 读取最近 N 条，展示操作类型、数量、Job ID、Run ID 和消息。

### 5. 测试

新增或扩展 `tests/test_web_ui.py`：

- 单条 delete 写入删除前快照。
- 单条 rerun 写入 source/new job 关系。
- 批量 stop 写入 processed/skipped。
- 批量 rerun 写入 missing task 跳过原因。
- `/tasks/audit.md` 能展示最近审计事件。

必要时新增单元测试覆盖审计 writer 的 JSONL 追加和容错读取。

## 验证方式

最小验证：

- `python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"`
- `python -m py_compile orchestrator/interfaces/web/main.py`
- `python -m pytest -q tests/test_web_ui.py`
- `python -m pytest -q`
- `git diff --check`

可选 smoke：

- 启动本地 Uvicorn 到空闲端口。
- 打开 `/tasks/audit.md`，确认 Markdown 可访问。
- 非破坏性执行未选择批量操作，确认不会写误导性 processed 记录。

## 风险与回滚考虑

- JSONL 写入失败不能阻断原操作；第一版应尽量捕获审计写入异常，并在页面提示或日志中体现。
- 审计文件可能增长，第一版读取最近 N 条，避免页面或导出过大。
- 不引入数据库迁移，回滚时只需移除 writer 调用和审计入口。
- 如果未来需要正式多用户 actor，再从认证层注入 actor，不在本阶段假造用户体系。

## 检查点

- 检查点 1：审计 writer 和测试通过。
- 检查点 2：单条操作审计接入完成。
- 检查点 3：批量操作审计接入完成。
- 检查点 4：`/tasks/audit.md` 可访问并覆盖测试。
- 检查点 5：更新 `status.md` 并补 trace 审查。

## 交付产物

- `orchestrator/infrastructure/persistence/web_job_audit_log.py`
- `orchestrator/interfaces/web/main.py`
- `tests/test_web_ui.py`
- `docs/codex/v1/plans/web-ui-task-manager-operational-audit.md`
- `docs/codex/v1/trace/web-ui-task-manager-operational-audit-trace.md`
- `docs/codex/v1/status.md`
