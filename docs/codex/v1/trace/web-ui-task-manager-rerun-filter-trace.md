# Web UI Task Manager Rerun Filter Trace

## 审查范围

本次审查覆盖 2026-06-04 任务管理页 `Rerun` 筛选增强：

- 计划记录：`docs/codex/v1/plans/web-ui-task-template-management.md`
- 状态记录：`docs/codex/v1/status.md`
- 实现文件：`orchestrator/interfaces/web/main.py`
- 页面模板：`orchestrator/interfaces/web/templates/tasks.html`
- 回归测试：`tests/test_web_ui.py`

## 已对齐项

### 1. Rerun 筛选参数

计划要求：`/tasks` 支持 `rerun=all|available|unavailable`。

实现结果：

- `task_manager()` 接收并规范化 `rerun` 参数。
- `_filter_task_manager_jobs()` 同时应用质量筛选、rerun 筛选和搜索关键字。
- `_task_manager_rerun_matches()` 将 `available` 映射到 `can_rerun`，将 `unavailable` 映射到 `rerun_unavailable_reason`。

验证结果：

- `tests/test_web_ui.py::test_task_manager_lists_and_filters_jobs` 覆盖 `rerun=available` 与 `rerun=unavailable`。

结论：已闭环。

### 2. 筛选计数与页面展示

计划要求：任务管理页展示可重新运行和不可重新运行数量。

实现结果：

- `_count_task_manager_rerun()` 统计 `all/available/unavailable`。
- `tasks.html` 新增 `Rerun` 下拉框，展示三类计数并保留选中态。

验证结果：

- 测试断言页面包含 `name="rerun"`。
- 测试断言 `Available (1)` 与 `Unavailable (1)` 展示和选中态。

结论：已闭环。

### 3. 导航与操作状态保持

计划要求：状态卡片、分页、停止和删除操作保留当前 rerun 筛选。

实现结果：

- `_tasks_query()` 和 `_tasks_url()` 增加 `rerun` 参数。
- 状态卡片链接、分页链接、停止表单和删除表单统一复用包含 `rerun` 的查询字符串。
- `stop_task()` 与 `delete_task()` 接收 `rerun` 并回跳到原筛选上下文。

验证结果：

- 测试断言停止、删除和分页 URL 包含 `rerun=...`。
- `test_task_manager_url_preserves_query` 覆盖 `_tasks_url()` 对 rerun 的编码结果。

结论：已闭环。

### 4. 不可重新运行原因可搜索

计划要求：搜索能找到不可重新运行原因，例如 `缺少原始 task.json`。

实现结果：

- `_task_manager_job_matches()` 将 `rerun_unavailable_reason` 纳入搜索 haystack。

验证结果：

- 测试通过 `/tasks?q=缺少原始+task.json` 命中缺少原始任务文件的失败 Job。

结论：已闭环。

## 未对齐项

未发现计划、实现、测试和状态记录之间的未对齐项。

## 风险与影响

- 本次变更只影响 Web 任务管理页的查询、展示和回跳 URL，不改变 Job 持久化结构、Run 执行流程、重新运行接口语义或底层 Orchestrator 行为。
- `rerun=unavailable` 当前以 `rerun_unavailable_reason` 是否存在作为判定标准，符合页面已有“无法重新运行”展示逻辑；未来如果新增更多不可重跑原因，应继续复用该字段或集中抽取判定函数。
- 页面模板曾存在 `每页` label 嵌套问题，本次已顺手修复，降低表单结构风险。

## 验证证据

- `python -m pytest -q tests/test_web_ui.py -k "task_manager"`：`5 passed, 46 deselected`
- `python -m py_compile orchestrator/interfaces/web/main.py`：通过
- `python -m pytest -q tests/test_web_ui.py`：`51 passed`
- `python -m pytest -q`：`136 passed`

## 总结结论

2026-06-04 Web UI Task Manager Rerun Filter 已完成从计划、实现、测试到状态记录的闭环。当前无阻塞缺口，可作为本轮任务管理页增强的交付状态。
