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
