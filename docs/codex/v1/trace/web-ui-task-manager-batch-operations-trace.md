# Web UI Task Manager Batch Operations Trace

## 审查范围

本次审查覆盖 2026-06-04 任务管理页批量操作增强：

- 计划记录：`docs/codex/v1/plans/web-ui-task-template-management.md`
- 状态记录：`docs/codex/v1/status.md`
- 实现文件：`orchestrator/interfaces/web/main.py`
- 页面模板：`orchestrator/interfaces/web/templates/tasks.html`
- 回归测试：`tests/test_web_ui.py`

## 已对齐项

### 1. 当前页批量选择

计划要求：任务管理页支持当前页任务选择，并避免误操作全库。

实现结果：

- `tasks.html` 新增当前页 checkbox 列。
- 表头新增当前页全选 checkbox。
- checkbox 使用 `form="task-batch-form"` 绑定到独立批量表单，避免嵌套每行已有操作表单。

验证结果：

- `test_task_manager_lists_and_filters_jobs` 断言页面包含 `task-batch-form`、`data-select-all-tasks` 和 `job_ids`。

结论：已闭环。

### 2. 批量停止

计划要求：批量停止只影响运行中任务，并保留当前筛选上下文。

实现结果：

- `POST /tasks/batch` 支持 `action=stop`。
- `_batch_stop_jobs()` 只处理 `status=running` 的 Job。
- 处理时复用 `WEB_CANCELLATION_REGISTRY.cancel()` 和 Web Job 状态冻结语义。
- 回跳 URL 保留 status、quality、rerun、page、page_size 和 q。

验证结果：

- `test_task_manager_batch_operations` 覆盖运行中任务成功停止、非运行中任务跳过、回跳上下文保留和页面摘要展示。

结论：已闭环。

### 3. 批量重新运行

计划要求：批量重新运行只处理可重跑任务，不可重跑任务跳过。

实现结果：

- `POST /tasks/batch` 支持 `action=rerun`。
- `_batch_rerun_jobs()` 跳过 running Job、缺失 Job 和缺少原始 `task.json` 的 Job。
- 可重跑 Job 复用 `_rerun_task_path()`，保持现有 task-copy 与后台启动行为。

验证结果：

- `test_task_manager_batch_operations` 覆盖 1 个可重跑 Job 成功生成 rerun task，2 个不可重跑/不可处理 Job 被跳过。

结论：已闭环。

### 4. 批量删除

计划要求：批量删除只移除 Web Job 记录，不删除 run 目录和审计日志。

实现结果：

- `POST /tasks/batch` 支持 `action=delete`。
- `_batch_delete_jobs()` 仅调用 `SQLiteJobRepository.delete(job_id)`。
- 页面确认文案明确“删除只移除任务记录，run 目录和审计日志会保留”。

验证结果：

- `test_task_manager_batch_operations` 覆盖选中 Job 被删除，未选中 Job 保留。

结论：已闭环。

### 5. 批量操作结果反馈

计划要求：页面显示成功、跳过和失败数量，避免静默部分处理。

实现结果：

- 批量接口返回 `batch` 查询参数。
- `/tasks` 渲染 `batch_notice` 信息卡。
- 未选择任务时返回“未选择任务，未执行批量操作。”

验证结果：

- `test_task_manager_batch_operations` 覆盖未选择、批量停止、批量重新运行和批量删除的结果摘要。

结论：已闭环。

## 未对齐项

未发现计划、实现、测试和状态记录之间的未对齐项。

## 风险与影响

- 第一版批量操作限定为当前页勾选任务，不做跨页或全筛选结果批量处理，误操作风险较低。
- 批量重新运行可能启动多个后台 Job；当前测试覆盖任务复制结果，但未做浏览器侧长时间并发运行观察。
- 批量删除不删除 run 目录和审计日志，符合既有单条删除语义。

## 验证证据

- `python -m pytest -q tests/test_web_ui.py -k "task_manager"`：`6 passed, 46 deselected`
- `python -m py_compile orchestrator/interfaces/web/main.py`：通过
- `python -m pytest -q tests/test_web_ui.py`：`52 passed`
- `python -m pytest -q`：`137 passed`
- 渲染 `/tasks`：返回 200，页面包含批量表单、全选控件、`/tasks/batch` endpoint 和全选 JS 绑定
- 本地 Uvicorn smoke：`http://127.0.0.1:8767/tasks` 返回 200，并包含批量表单
- 非破坏性 `POST /tasks/batch`：未选择任务时返回 303 到已编码的 `batch=` 提示，回跳页显示 `未选择任务，未执行批量操作。`
- 本地 Chrome headless 视觉检查：截图 `.tmp/task-manager-8767.png` 显示任务管理标题、筛选区、批量操作下拉、checkbox 列、任务表格和行操作按钮正常渲染，未见明显重叠

## 总结结论

2026-06-04 Web UI Task Manager Batch Operations 已完成计划范围内的实现、Web UI 回归验证和项目全量回归验证。当前无阻塞缺口，`status.md` 已推进为已完成。
