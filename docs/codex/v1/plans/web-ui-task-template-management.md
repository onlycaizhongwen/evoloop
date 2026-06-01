# Web UI 任务模板管理

## 目标

在 Web UI 首页提供后端白名单任务模板，让用户不用手动组合 Agent、Execution backend、Docker 命令预设、allowed paths 和测试命令。

## 已实现

- 新增后端 `TASK_TEMPLATES` 模板注册表。
- 模板注册表位于 `orchestrator/application/task_template_registry.py`，Web adapter 只负责表单渲染、校验和任务提交。
- 首页右侧新增“任务模板”选择入口，通过 `GET /?template_id=...` 套用模板。
- 新建任务表单保留 `template_id` 隐藏字段。
- 任务提交后生成的 `.omx/web-tasks/*.json` 写入 `template_id`，便于追踪任务来源。
- Run Detail 新增“启动配置”面板，展示模板、backend、agent、command preset、worktree、allowed paths 和 test command。
- Job Status 新增“启动配置”面板，任务等待 run 目录创建时从 job task JSON 读取，run 创建后优先从 run/task.json 读取。
- 历史任务未写入 `command_preset` 时，会根据 `patch_coder` 命令尽量反推内置 preset。
- Docker Team Patch 模板自动填充：
  - `execution_backend=docker`
  - `agent_mode=omx_team_patch`
  - `command_preset=team_patch_backend`
  - `allowed_paths=calculator.py,test_calculator.py,docker_team_backend.py`
  - `check_command=python -m unittest -q`
- Docker Patch JSON 模板自动填充：
  - `execution_backend=docker`
  - `agent_mode=omx_patch`
  - `command_preset=patch_json_backend`
  - `allowed_paths=calculator.py,test_calculator.py,patch_backend.py`

## 安全边界

- 模板由后端白名单定义，前端只负责选择模板 ID。
- 非法模板 ID 自动回退到 `local_omx_team`，不执行任意用户定义模板。
- Docker 命令仍复用现有路径校验，只允许 `/worktree`、`/run`、`/cache` 和占位符路径。

## 验证

- `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py`：38 passed。
- `python -m pytest -q tests/test_web_ui.py`：31 passed。
- `python -m pytest -q`：117 passed。

## 下一步建议

1. 给首页加“最近使用模板”或“推荐模板”标记。
2. 增加真实 OMX/Codex 模板入口，和 Docker 模板并列展示。
3. 给首页模板卡片补关键配置预览，让提交前也能看见 backend/agent/preset。
## 2026-05-26 Homepage Template Preview

- Homepage task template cards now preview `execution_backend`, `agent_mode`, `command_preset`, `allowed_paths`, and `check_command` before the user applies a template.
- The preview data comes from `orchestrator/application/task_template_registry.py`, keeping the Web adapter as a renderer instead of duplicating template configuration.
- Validation: `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` passed with `38 passed`; `python -m pytest -q` passed with `117 passed`; `python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` passed.

## 2026-05-26 Homepage Template Badges

- Homepage task template cards now show backend-provided badges such as `Default`, `Recommended`, `Docker`, `Local`, and `Demo`.
- Badge metadata is owned by `orchestrator/application/task_template_registry.py`, so recommended/default labels stay close to the template whitelist.
- Validation: `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` passed with `38 passed`; `python -m pytest -q` passed with `117 passed`; `python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` passed.

## 2026-05-26 Homepage Template Recent Job

- Homepage task template cards now show the most recent persisted Web job for that template when available, including status and `run_id`.
- The Web adapter derives this from recent SQLite jobs and each job task JSON `template_id`; the template registry remains the whitelist/source of template metadata.
- Validation: `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` passed with `39 passed`; `python -m pytest -q` passed with `118 passed`; `python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` passed.

## 2026-05-26 Homepage Template Recent Job Status Color

- Recent job links on homepage task template cards now carry a status CSS class: `done`, `failed`, `running`, or `unknown`.
- The UI colors successful recent jobs green, failed jobs red, and running jobs blue, making the template history easier to scan.
- Validation: `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` passed with `39 passed`; `python -m pytest -q` passed with `118 passed`; `python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` passed.

## 2026-05-26 Direct Run Template

- Homepage task template cards now include a `直接运行` action that posts to `/templates/run`.
- The Web adapter builds the task from the backend whitelist template, writes the same `.omx/web-tasks/*.json` payload as the normal form path, and redirects to the Job status page.
- Validation: `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` passed with `40 passed`; `python -m pytest -q` passed with `119 passed`; `python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` passed.
## 2026-05-27 Direct Run Duplicate Guard

- `/templates/run` now checks recent persisted Web jobs before creating a new task. If the same template already has a `running` job, it redirects to the existing Job status page instead of starting a duplicate.
- Homepage template direct-run forms now disable the clicked submit button and show `提交中...` while the browser submits, reducing accidental double clicks.
- The guard remains backend-authoritative: frontend locking improves usability, while SQLite job reuse prevents duplicate execution even if the same POST arrives twice.
- Validation: `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` passed with `41 passed`; `python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` passed.

## 2026-06-01 Docker Template Stdlib Check

- Docker task templates now default to `python -m unittest -q` so the recommended `python:3.12-slim` sandbox can run hard checks without installing pytest.
- The generated default smoke worktree now writes `test_calculator.py` as a standard-library `unittest` test while preserving the same calculator patch scenario.
- The default smoke worktree is still reset only for `.tmp/omx-unified-diff-smoke`, so user-provided worktrees are not overwritten.

## 2026-05-27 Task Management Navigation

- Web UI now has a top navigation menu with `新建任务` and `任务管理`.
- Added `/tasks`, a task management page backed by persisted SQLite Web jobs. It shows all jobs and filters for `运行中`, `已完成`, and `失败`.
- Task rows link to the right detail surface: running/failed jobs go to `/jobs/{job_id}`, completed jobs with `run_id` go to `/runs/{run_id}`.
- When direct-run reuses a running template job, the redirect adds `?reused=1` and the Job Status page shows a visible notice explaining that the existing task was opened.
- Validation: `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` passed with `43 passed`.

## 2026-05-27 Task Management Workspace

- `/tasks` is now structured as the primary workspace with a left sidebar menu.
- The task list header includes a `新建任务` button that opens an in-page modal form instead of sending users back to the homepage.
- The modal posts to the existing `/tasks/run` endpoint and reuses the same validation/execution path as the original homepage form.
- Validation: `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` passed with `44 passed`; `python -m py_compile orchestrator/interfaces/web/main.py` passed.

## 2026-05-27 Task List Table

- The `/tasks` task list now renders as a real HTML table instead of stacked rows.
- Columns are `状态`, `Job ID`, `Run ID`, `模板`, `执行`, `更新时间`, and `操作`, with horizontal scrolling on narrower screens.
- Validation: `python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` passed with `44 passed`; `python -m py_compile orchestrator/interfaces/web/main.py` passed.

## 2026-05-27 Sidebar Simplification

- The `/tasks` sidebar now keeps only the `任务管理` menu item.
- The create action remains in the task list toolbar as the `新建任务` button, which opens the existing in-page modal.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `39 passed`; `python -m pytest -q` passed with `123 passed`.

## 2026-05-27 Task Table Operations And Pagination

- The `/tasks` table now puts `任务名称` first, moves `状态` behind `更新时间`, and keeps Job/Run/template/backend fields for traceability.
- Each row now exposes `详情`, `停止`, and `删除` actions. Stop marks a running Web job as `stopped`; delete removes the Web job list record without deleting run audit artifacts.
- The task list supports `page` and `page_size` query parameters, preserves the active status filter, and renders previous/next pagination controls.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `41 passed`; `python -m pytest -q` passed with `125 passed`.

## 2026-05-27 Stop/Delete Guardrails

- Running task lists now auto-refresh every 5 seconds.
- Stop and delete actions require browser confirmation. The stop confirmation states that the system sends a termination signal to the active local/Docker command when one is registered, otherwise it freezes Web Job state.
- Job status now renders `stopped` as a visible stopped-request state instead of continuing to look like an active execution.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `41 passed`; `python -m pytest -q` passed with `125 passed`.

## 2026-05-27 Cancellable Web Commands

- Web-started jobs now use a `CancellationRegistry` shared by the Web process.
- Local and Docker command runners register their active `Popen` under the Web Job ID. Calling `停止` now attempts to terminate the current local/Docker command process tree.
- If the job is not inside a command runner when stop is clicked, the Web Job is still frozen as `stopped`; if a process is active, it receives a termination signal and the worker preserves the stopped status.
- Validation: `python -m pytest -q tests/test_command_safety_and_heartbeat.py tests/test_web_ui.py` passed with `53 passed`; `python -m pytest -q` passed with `126 passed`.

## 2026-05-28 Rerun From Detail Pages

- Job status pages and run detail pages now include a `重新运行` action.
- Rerun copies the original `task.json` into `.omx/web-tasks/`, assigns a new rerun-flavored `task_id/title`, starts a new Web Job, and redirects to the new Job status page.
- The action works from both pre-run Web jobs and completed/failed run detail pages, so users do not need to manually recreate the task form.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `43 passed`; `python -m pytest -q` passed with `128 passed`.

## 2026-05-28 Legacy Metadata Copy

- Task list copy now renders missing template metadata as `历史任务` instead of `未记录模板`.
- Missing execution backend metadata now renders as `旧任务未记录`, with muted helper text explaining that early tasks lack backend/template fields.
- Web background workers now capture the submission-time workspace root for run storage and SQLite updates, avoiding path drift if tests or callers change the process working directory while a worker thread is still running.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `43 passed`; `python -m pytest -q` passed with `128 passed`.

## 2026-05-29 Task Search And Page Size

- `/tasks` now supports a `q` query parameter for searching task name, Task ID, Job ID, Run ID, template, backend, agent, and status text.
- The task list toolbar includes a search box and page size selector with 5/10/20/50 options.
- Status filters, pagination links, stop, and delete actions preserve the current search query and page size.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `43 passed`; `python -m pytest -q` passed with `128 passed`.

## 2026-05-29 Detail Page Task Metadata

- Job status and run detail pages now use the task title/name as the main heading instead of generic page titles.
- Both detail surfaces show task metadata near the top: Task ID, Job/Run ID, template, backend, agent, status, and update time.
- Job status pages now expose a unified action area with stop, rerun, delete-record, and return-to-list actions. Run detail pages keep rerun and return-to-list actions while preserving run audit artifacts.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `43 passed`; `python -m pytest -q` passed with `128 passed`.

## 2026-05-29 Frontloaded Failure Reason

- Failed Job status pages now show a top-level `失败原因` card with phase, reason, and suggested next action.
- Halted/Retrying Run detail pages now extract the first useful reason from `final_report.md`, falling back to `phase.log` or current phase.
- Suggested next actions are phase-aware for patch approval, hard checks/tests, review JSON issues, safety policy failures, and agent/code phases.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `45 passed`; `python -m pytest -q` passed with `130 passed`.

## 2026-05-29 Run Detail Execution Summary And Timeline

- Run detail pages now show an `执行摘要` panel near the top with status, phase, attempt count, patch approval counts, Docker evidence state, update time, and latest phase event.
- `logs/phase.log` is parsed into a tolerant `阶段时间线` list. It supports structured `key=value` phase logger lines and simpler legacy lines used by older tests/runs.
- Docker sandbox evidence is loaded once per run detail request and reused by both the summary panel and diagnostics section.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `45 passed`; `python -m pytest -q` passed with `130 passed`.

## 2026-05-29 Execution Chain Summary

- Job status and Run detail pages now include an `执行链路` panel showing the path from Web UI to Orchestrator, Agent, execution environment, Patch, and Quality Gate.
- The chain distinguishes `codex`, `omx`, `omx_patch`, `omx_team_patch`, `shell`, and `mock` agent modes without claiming Codex was called unless the selected mode implies it.
- Docker chain copy now separates planned Docker backend from recorded Docker sandbox evidence, so users can see whether the run is still waiting for evidence or has concrete Docker logs.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `45 passed`; `python -m pytest -q tests/test_command_safety_and_heartbeat.py tests/test_web_ui.py` passed with `57 passed`; `python -m pytest -q` passed with `130 passed`.

## 2026-05-30 Run Artifact Entry Points

- Run detail pages now include a `运行产物` panel with the run directory, worktree, patch count, changed-file summary, and status rows for task, run_state, final_report, phase log, heartbeat log, agent log, and Docker log files.
- Patch artifacts are summarized in the same panel with patch file name, status, risk score, and changed files, so users can locate generated patch JSON without manually browsing `.omx/runs`.
- Missing files render as `暂无记录` instead of failing the page, preserving compatibility with legacy or partially-created runs.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `45 passed`.

## 2026-06-01 Productized Task Creation Form

- The `/tasks` create-task modal is now grouped into `基础信息`, `执行方式`, `工作区与权限`, `验证配置`, and a collapsed `高级配置` section.
- The form includes a `将会如何执行` preview that summarizes backend, agent mode, command preset, check command, allowed paths, and worktree before submission.
- Advanced Docker sandbox and raw agent command fields remain available but are no longer mixed into the primary path for recommended templates.
- Submit buttons now switch to `提交中...` and disable themselves while the browser posts the task form.
- Validation: `python -m pytest -q tests/test_web_ui.py` passed with `45 passed`.
