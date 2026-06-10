# 2026-06-09 Web Audit Source Provenance

- Status: completed.
- Summary: `/tasks/audit` and `/tasks/audit.md` are gaining source provenance for active vs archived audit records, using read-time metadata without rewriting JSONL audit files.
- Process file: `.codex/plans/main/web-audit-source-provenance/process.md`
- Resume hint: read the process file for verification evidence. Do not commit unless requested.

# 2026-06-09 Web Health Footprint Evidence

- Status: completed.
- Summary: `/tasks/health` is gaining read-only footprint evidence for rotated task audit archives and `.omx/runs` artifacts so operators can judge cleanup pressure before using maintenance actions.
- Process file: `.codex/plans/main/web-health-footprint-evidence/process.md`
- Resume hint: read the process file for verification evidence; remaining operational step is commit/push if not already done.

# 2026-06-09 Web Run Artifact Cleanup

- Status: completed.
- Summary: `/tasks` is gaining an explicit maintenance action to prune old `.omx/runs/{run_id}` artifact directories while preserving Web Job records and audit logs. The action skips running-linked and missing-state run directories and writes `maintenance_prune_runs` audit evidence.
- Process file: `.codex/plans/main/web-run-artifact-cleanup/process.md`
- Resume hint: read the process file for verification evidence; remaining operational step is commit/push if not already done.

# 2026-05-26 Web UI Task Template Preview HTML

- 状态：已完成
- 摘要：新增静态 HTML 预览页，用于直观看到首页任务模板增强效果，包括配置预览、推荐标签、最近运行状态、状态色和 `直接运行` 按钮。
- 产物：`项目工程文档/WebUI任务模板增强预览.html`
- 验证：已确认文件生成，大小约 12KB，可直接用浏览器打开查看。

# 2026-05-26 Web UI Direct Run Template

- 状态：已完成
- 摘要：首页任务模板卡片新增 `直接运行` 按钮，提交到 `/templates/run`，由后端白名单模板生成 task JSON 并直接启动 Job。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `40 passed`；`python -m pytest -q` 为 `119 passed`。

# 2026-05-26 Web UI Task Template Recent Job Status Color

- 状态：已完成
- 摘要：首页任务模板卡片的最近运行链接新增状态色：`done` 绿色、`failed` 红色、`running` 蓝色。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `39 passed`；`python -m pytest -q` 为 `118 passed`。

# 2026-05-26 Web UI Task Template Recent Job

- 状态：已完成
- 摘要：首页任务模板卡片新增最近运行提示，根据 SQLite 最近 Job 和 task JSON 的 `template_id` 显示该模板最近一次 `status/run_id`，并链接到 Job 状态页。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `39 passed`；`python -m pytest -q` 为 `118 passed`。

# 2026-05-26 Web UI Task Template Badges

- 状态：已完成
- 摘要：首页任务模板卡片新增 `Default`、`Recommended`、`Docker`、`Local`、`Demo` 标签，标签由 application registry 提供，页面只负责渲染。
- 产物：`orchestrator/application/task_template_registry.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_task_template_registry.py`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `38 passed`；`python -m pytest -q` 为 `117 passed`。

# 2026-05-26 Web UI Task Template Preview

- 状态：已完成
- 摘要：Homepage task template cards now show startup config preview before applying a template, including backend, agent, command preset, allowed paths, and check command.
- 产物：`orchestrator/application/task_template_registry.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_task_template_registry.py`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `38 passed`；`python -m pytest -q` 为 `117 passed`。

# 2026-05-25 Web UI Docker Agent Command Presets

- 状态：已完成
- 摘要：Web UI 新增 Docker agent 命令预设，用户可选择安全模板生成容器内 agent 命令，无需手写 `/worktree`、`/run`、`/cache` 路径。
- 安全策略：预设由后端 `DOCKER_AGENT_COMMAND_PRESETS` 白名单定义；非 `custom` 预设会覆盖表单命令字段，并强制匹配 `execution_backend=docker` 与对应 `agent_mode`。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_web_ui.py`、`docs/codex/v1/designs/docker-sandbox-runner-design.md`
- 验证：`python -m pytest -q tests/test_web_ui.py` 为 `24 passed`；`python -m pytest -q` 为 `103 passed`。

# 2026-05-25 Web UI Docker Agent Preset Closed Loop

- 状态：已完成
- 摘要：默认 smoke worktree 自动生成 Docker agent backend，页面选择 Docker backend + `team_patch_backend` 预设即可完成 Web 提交到 Docker agent、patch apply、Docker hard check 和 run detail 展示的真实闭环。
- 产物：`orchestrator/interfaces/web/main.py`、`tests/test_web_ui.py`、`docs/codex/v1/designs/docker-sandbox-runner-design.md`、`docs/codex/v1/status.md`
- 验证：新增定向闭环测试 2 passed；`python -m pytest -q tests/test_web_ui.py` 为 `26 passed`；`python -m pytest -q` 为 `105 passed`。

# 2026-05-25 Run Detail Docker Evidence

- 状态：已完成
- 摘要：Run detail 新增 Docker 执行证据面板，展示 Docker 执行次数、image、network、mount、容器路径、阶段列表和最近 Docker 日志。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/run_detail.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_web_ui.py`、`docs/codex/v1/designs/docker-sandbox-runner-design.md`
- 验证：新增定向证据测试 2 passed；`python -m pytest -q tests/test_web_ui.py` 为 `27 passed`；`python -m pytest -q` 为 `106 passed`。

# 2026-05-25 Web UI Docker Agent Quickstart

- 状态：已完成
- 摘要：首页新增 Docker Agent 快速上手面板，并新增 Web UI Docker Agent 快速上手文档，降低页面使用门槛。
- 产物：`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`docs/codex/v1/plans/web-ui-docker-agent-quickstart.md`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_web_ui.py` 为 `27 passed`；`python -m pytest -q` 为 `106 passed`。

# 2026-05-26 Web UI Task Templates

- 状态：已完成
- 摘要：Web UI 新增后端白名单任务模板，用户可选择模板自动填充 agent/backend/preset/paths/check command；Job Status 和 Run Detail 均新增启动配置面板用于复盘运行来源。
- 产物：`orchestrator/application/task_template_registry.py`、`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/templates/job_status.html`、`orchestrator/interfaces/web/templates/run_detail.html`、`tests/test_task_template_registry.py`、`tests/test_web_ui.py`、`docs/codex/v1/plans/web-ui-task-template-management.md`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `38 passed`；`python -m pytest -q` 为 `117 passed`。

# TASKS

# 2026-06-09 Web External Agent Wrapper Provenance

- Status: completed.
- Summary: Run detail and exported run audit Markdown now surface `logs/external_agent_wrapper.log` as structured wrapper command provenance, including runtime, roles, task ID, exit code/dry-run status, backend command, prompt file, and raw diagnostics.
- Process file: `.codex/plans/main/external-agent-closed-loop-smoke/process.md`
- Verification: `python -m py_compile orchestrator/interfaces/web/main.py` passed; `python -m pytest -q tests/test_web_ui.py -k "run_audit_markdown or wrapper_provenance or run_detail"` passed with `9 passed, 53 deselected`.

## v1-自动循环进化编码智能体系统-文档补齐
- 状态：已完成
- 摘要：基于 V7 架构设计补齐需求文档、对外技术文档、MVP 实施计划和演讲大纲。
- 过程文件：.codex/plans/main/auto-evolution-docs/process.md
- 恢复提示：读取 process.md，继续完成或校验四份文档与 status.md。

## v1-自动循环进化编码智能体系统-MVP实现
- 状态：第四批完成
- 摘要：按 DDD 架构实现第一批 Mock 闭环：任务读取、状态持久化、安全策略、Hard Check 短路、Review 校验、Quality Gate 和最终报告。
- 过程文件：.codex/plans/main/auto-evolution-implementation/process.md
- 恢复提示：读取 process.md，从未完成步骤继续实现或验证。

### 2026-05-21 状态增量
- MVP 实现任务第五批已完成：新增 pending rule proposal 运行产物能力。
- 恢复提示：读取 `.codex/plans/main/auto-evolution-implementation/process.md` 的“2026-05-21 第五批实现记录”，下一步从真实 Git diff 场景测试或命令 allowlist 扩展继续。

### 2026-05-21 状态增量 2
- MVP 实现任务第六批已完成：补真实 Git diff 集成测试，并让 forbidden path diff 进入风险扣分。
- 恢复提示：下一步从第七批“命令 allowlist 策略增强”继续。

### 2026-05-21 状态增量 3
- MVP 实现任务第七批已完成：新增可配置命令 allowlist，保留危险命令优先阻断。
- 恢复提示：下一步从第八批“Codex/OMX Agent Adapter 骨架与 prompt builder”继续。

### 2026-05-21 状态增量 4
- MVP 实现任务第八批已完成：新增 Codex/OMX Agent Adapter 骨架与共享 prompt builder，并补 dry-run 示例任务。
- 恢复提示：下一步进入第九批 trace 审查，对 requirements/design/plan/实现做一致性闭环。

### 2026-05-21 状态增量 5
- MVP 实现任务第九批已完成：新增 trace 审查文档，确认 MVP 第一阶段主链路基本闭环。
- 恢复提示：下一步优先做 phase logging 与 `quality_report.json` 文档/实现一致性收口。

### 2026-05-21 状态增量 6
- Trace GAP-02 已完成：新增统一 phase logging 和微秒级 run_id，避免同秒运行目录碰撞。
- 恢复提示：下一步处理 GAP-03，统一 `quality_report.json` 文档示例与当前实现结构。

### 2026-05-21 状态增量 7
- Trace GAP-03 已完成：`quality_report.json` 保持扁平结构，V7 示例和正式技术文档已同步。
- 恢复提示：下一步可进入 GAP-04 pending rule proposal 聚类，或 GAP-05 resume CLI。

### 2026-05-21 状态增量 8
- Trace GAP-05 基础能力已完成：新增 resume inspect 和 fresh rerun CLI。
- 恢复提示：下一步进入 GAP-04 pending rule proposal 历史索引与重复问题聚类。

### 2026-05-21 状态增量 9
- Trace GAP-04 基础能力已完成：新增 rule proposal 历史索引和重复问题聚类统计。
- 恢复提示：下一步可补 Rule Proposal 人工审批状态流，或开始真实 Codex/OMX Agent 协议定义。

### 2026-05-21 状态增量 10
- Rule Proposal 人工审批状态流已完成：新增 `rules list` 和 `rules review`，支持 pending/approved/rejected。
- 恢复提示：下一步进入真实 Codex/OMX Agent 协议定义。
### 2026-05-21 状态增量 11
- Trace GAP-01 基础协议已完成：新增真实 Codex/OMX Agent CLI 协议文档、Codex/OMX 真实接入模板，并补外部 Agent 契约测试。
- 恢复提示：下一步基于本机真实 Codex/OMX CLI 参数实现包装脚本，或进入半截运行续跑/人工审批 PR 流程增强。
### 2026-05-21 状态增量 12
- Agent Wrapper 已完成：新增 `scripts/run_external_agent.py`、wrapper dry-run 示例任务和包装脚本测试，支持 dry-run 与后端命令模板转发。
- 恢复提示：下一步可配置 `OMX_CODEX_CODER_COMMAND` 等环境变量，在临时样例仓库做真实 Codex 写操作验证。
### 2026-05-21 状态增量 13
- OMX setup 与 stdin wrapper 已完成：`omx doctor` 为 15 passed、1 warning、0 failed；wrapper 支持 stdin prompt 与 output-last-message；全量测试 41 passed。
- 恢复提示：下一步创建 `.tmp/omx-real-smoke/` 临时样例仓库，配置真实 `omx exec` 后端命令，做一次受控写操作验证。
### 2026-05-21 状态增量 14
- 真实 OMX smoke 已执行：Orchestrator 能调起 `omx exec`，但 Windows Codex 执行沙箱报 `CreateProcessWithLogonW failed: 1385`，真实写操作未完成；已补 BOM、绝对路径和输出编码容错，全量测试 44 passed。
- 恢复提示：下一步优先选择 WSL/Linux 复测真实写操作，或设计“模型输出 patch、Orchestrator 审批应用 patch”的 Windows 兼容路线。
### 2026-05-21 状态增量 15
- Windows 兼容 Patch 模式第一版完成：新增 `omx_patch` Agent、patch JSON 校验和受控应用器；patch smoke `run-20260521-162852-762772` 成功到 done；全量测试 47 passed。
- 恢复提示：下一步把 patch 后端切到真实 `omx exec` patch-only prompt，让模型输出 patch JSON，由 Orchestrator 应用。
### 2026-05-21 状态增量 16
- 真实 `omx exec` patch-only 后端已跑通：patch prompt 注入允许文件快照，真实 OMX 输出 patch JSON，Orchestrator 应用 patch；复测 run `run-20260521-163411-124400` 到 done；全量测试 48 passed。
- 恢复提示：下一步扩展 patch schema 和审批能力，例如 `create_file`、`delete_file`、unified diff、patch 风险评分和人工审批开关。
### 2026-05-21 状态增量 17
- Patch schema 第二版完成：支持 `create_file`/`delete_file`，PatchApplyResult 记录 changed/created/deleted 与 risk_score；真实 OMX patch smoke `run-20260521-164502-235168` 到 done；全量测试 50 passed。
- 恢复提示：下一步实现 patch 人工审批开关，高风险 patch 先落盘待审批，不自动应用。
### 2026-05-21 状态增量 18
- Patch 人工审批开关完成：支持风险阈值、delete_file 强制审批、pending-patches 落盘；审批 smoke `run-20260521-165047-273285` halted 且未删除文件；全量测试 52 passed。
- 恢复提示：下一步新增 `patches list/apply/reject` CLI，让人工审批后的 pending patch 可被应用或拒绝。
### 2026-05-21 状态增量 19
- Pending Patch CLI 完成：新增 `patches list/apply/reject` 和 PendingPatchService；审批 smoke `run-20260521-170009-452873` 经 apply 后删除目标文件；全量测试 53 passed。
- 恢复提示：下一步可补 `patches apply --rerun-checks`，审批应用后自动重跑 hard checks，或进入 unified diff 支持。
### 2026-05-21 状态增量 20
- `patches apply --rerun-checks` 完成：审批应用后重跑 hard checks，写入 `post_apply_checks`，CLI 输出 `checks_passed`；验证 run `run-20260521-170424-438800` 通过；全量测试 53 passed。
- 恢复提示：下一步可进入 unified diff patch 支持，或实现 `patches apply --rerun-task` 重新跑完整 review/quality gate。
# 2026-05-21 最新状态增量

- Patch unified diff 与 `patches apply --rerun-task` 已完成：Orchestrator 可解析/校验/应用 `unified_diff` patch JSON，并在审批应用后新建 post-apply validation run 重跑 hard checks、Reviewer、Quality Gate。
- 验证：`python -m pytest -q` 通过，57 passed。
- 恢复提示：继续从 `.codex/plans/main/auto-evolution-implementation/process.md` 顶部“Patch Unified Diff 与 rerun-task 记录”读取最新上下文；下一步可做真实 OMX unified diff 端到端样例或增强 patches 审计展示。

# 2026-05-21 第三步规划

- 已新增第三步计划：`docs/codex/v1/plans/自动循环进化编码智能体系统-third-step-plan.md`。
- 第三步主题：真实 unified diff smoke、`patches list` 审计展示增强、失败诊断与演示脚本。
- 恢复提示：优先从 `patches list` 审计展示增强开始实现，然后补 unified diff smoke。

# 2026-05-21 第三步进度 1

- `patches list` 审计展示增强已完成：输出 `checks_status` 三态，以及 `rerun_phase/rerun_attempt`。
- 恢复提示：下一步进入 unified diff smoke task 与可控 backend。

# 2026-05-21 第三步进度 2

- unified diff smoke 已完成：新增可控 backend、smoke task 与独立 `.tmp/omx-unified-diff-smoke/` 工作区。
- 验证：smoke run `run-20260521-173445-649699` 到 `done`；相关 pytest 通过。
- 恢复提示：下一步补失败诊断产物，优先覆盖 malformed patch JSON、context mismatch、rerun hard-check failed。

# 2026-05-21 第三步进度 3

- 失败诊断产物已完成：patch raw output、patch diagnostics、post-apply rerun reason 均已落盘/输出。
- 验证：`tests/test_cli_resume.py` 与 `tests/test_patch_agent.py` 合计 20 passed。
- 恢复提示：下一步补第三步演示命令脚本/文档，并执行全量回归。

# 2026-05-21 第三步进度 4

- 演示脚本与演示文档已完成：`scripts/run_patch_demo.py`、`docs/codex/v1/plans/自动循环进化编码智能体系统-demo-script.md`。
- 验证：`python scripts/run_patch_demo.py` 已跑通，覆盖 unified diff smoke 与 pending patch 审批 rerun。
- 恢复提示：下一步执行全量回归并补 trace 收口。

# 2026-05-21 第三步 Trace 收口

- 第三步 trace 已完成：`docs/codex/v1/trace/自动循环进化编码智能体系统-third-step-trace.md`。
- 结论：第三步主体目标已闭环；真实 OMX/Codex unified diff smoke 属于后续环境依赖型增强。
- 恢复提示：下一步可规划真实 OMX/Codex unified diff smoke 模板，或进入下一阶段自动循环策略增强。

# 2026-05-21 真实 Unified Diff Smoke 模板

- 已补真实 OMX/Codex unified diff smoke 模板与说明文档。
- 文件：`examples/task.omx-patch-unified-diff-real-smoke.json`、`examples/task.codex-patch-unified-diff-real-smoke.json`、`docs/codex/v1/plans/自动循环进化编码智能体系统-real-unified-diff-smoke.md`。
- 验证：TaskLoader 可读取，`python -m pytest -q` 为 61 passed。
- 恢复提示：真实执行前按说明文档配置后端命令环境变量。

# 2026-05-21 Web UI MVP

- 已完成本地输入界面：支持新建任务、运行示例、查看 runs、查看日志/报告、审批 pending patch 并触发 rerun-task。
- 新增文档：`docs/codex/v1/plans/自动循环进化编码智能体系统-web-ui-mvp.md`。
- 验证：`python -m pytest -q` 通过，当前为 63 passed。
- 使用：`python -m orchestrator.interfaces.web.main` 后打开 `http://127.0.0.1:8765`。

# 2026-05-22 Web UI 真实主线调整

- 已将默认路线调整为 `Orchestrator -> OMX -> Codex -> patch JSON -> Orchestrator`。
- Web 新建任务默认使用 `omx_patch`，Patch coder/fixer 默认通过 wrapper 调 `omx exec`。
- 已确认 `omx exec` 帮助显示其执行入口为 `codex exec`，`omx doctor` 显示 Codex CLI 已安装。
- 验证：`python -m pytest -q` 通过，当前为 63 passed。

# 2026-05-22 下一阶段规划

- 已新增计划文档：`docs/codex/v1/plans/自动循环进化编码智能体系统-next-step-plan.md`。
- 当前成功基线：真实 OMX/Codex patch-only run `run-20260522-140604-839823` 到 `done`，工作区测试 `1 passed`，系统回归 `64 passed`。
- 下一步优先级：先实现异步任务与运行状态落盘，再做真实项目接入表单校验、Patch Diff 可视化审批、真实项目回归 Smoke、OMX team 编排模式。
- 恢复提示：从 `next-step-plan.md` 的“优先级二：异步任务与运行状态”开始实现。
# 2026-05-22 Web UI 异步任务入库

- 状态：已完成
- 摘要：Web 提交任务后写入 SQLite 数据库 `.omx/orchestrator.db` 的 `web_jobs` 表，任务状态页从数据库恢复，完成后跳转到运行详情页。
- 改动范围：`orchestrator/infrastructure/persistence/sqlite_job_repository.py`、`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/templates/job_status.html`、`orchestrator/interfaces/web/templates/run_detail.html`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q` 通过，当前为 `66 passed`。
- 恢复提示：下一步可继续做真实项目接入表单校验、Patch Diff 可视化审批、真实项目回归 Smoke 或 OMX team 编排模式。

# 2026-05-22 Web UI 真实项目接入表单校验

- 状态：已完成
- 摘要：首页任务提交前校验已补齐，覆盖 Task ID、类型、Agent 模式、worktree、allowed paths、真实检查命令和高风险命令。
- 改动范围：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/templates/job_status.html`、`orchestrator/interfaces/web/templates/run_detail.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q` 通过，当前为 `68 passed`。
- 恢复提示：下一步建议做 Patch Diff 可视化审批，让 pending patch 在页面里能直接看 diff 内容和风险原因。

# 2026-05-22 Patch Diff 可视化审批

- 状态：已完成
- 摘要：pending patch 列表和 run 详情页已展示 summary、risk_reasons、operation previews，支持 replace/create/delete/unified diff 预览。
- 改动范围：`orchestrator/infrastructure/patches/pending_patch_service.py`、`orchestrator/interfaces/web/templates/run_detail.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_patch_agent.py`。
- 验证：`python -m pytest -q` 通过，当前为 `69 passed`。
- 恢复提示：下一步可做真实项目回归 Smoke，验证对一个独立临时项目从提交任务到审批 patch 再 rerun 的完整链路。

# 2026-05-22 真实项目回归 Smoke

- 状态：已完成
- 摘要：新增可重复 smoke 脚本，自动创建独立临时 worktree，并验证 pending patch、预览、审批、应用、rerun-task 和临时项目 pytest 闭环。
- 改动范围：`scripts/run_real_project_smoke.py`、`tests/test_real_project_smoke.py`。
- 验证：`python scripts/run_real_project_smoke.py` 通过；`python -m pytest -q` 通过，当前为 `70 passed`。
- 恢复提示：下一步建议进入 OMX team 编排模式设计/实现，或继续增强 Web 任务历史和运行详情。

# 2026-05-22 OMX Team Protocol 状态增量

- 状态：设计契约完成
- 摘要：已补 OMX team 编排模式的协议文档、team_task/team_result 示例和 JSON 契约测试；当前回归基线为 `72 passed`。
- 产物：`docs/codex/v1/designs/自动循环进化编码智能体系统-team-protocol.md`，`examples/team_task.omx-team-patch.json`，`examples/team_result.omx-team-patch.json`，`tests/test_team_protocol_examples.py`
- 恢复提示：下一步从实现 `agent_mode=omx_team_patch` 继续，先让 Orchestrator 调用 OMX team 读取 `team_result.json`，不要让 team 直接改 worktree。

# 2026-05-22 OMX Team Patch 执行链路状态增量

- 状态：最小执行链路完成
- 摘要：已实现 `agent_mode=omx_team_patch`，Orchestrator 可调用 team 后端、解析 `team_result.json`、应用其中 patch_plan 并复用 review。
- 产物：`orchestrator/infrastructure/agents/omx_team_patch_agent.py`，`examples/task.omx-team-patch-smoke.json`，`examples/team_patch_backend.py`，`tests/test_omx_team_patch_agent.py`
- 验证：team patch smoke run=`run-20260522-163446-036926`，全量 `python -m pytest -q` 为 `74 passed`。
- 恢复提示：下一步接 Web UI，允许页面选择 `omx_team_patch` 并展示 team result / diagnostics。

# 2026-05-22 Web UI Team Patch 接入状态增量

- 状态：Web 接入完成
- 摘要：Web 表单已允许 `omx_team_patch`，示例默认 Agent 改为 Team 模式，运行详情页展示 team result / diagnostics。
- 产物：`orchestrator/interfaces/web/main.py`，`orchestrator/interfaces/web/templates/index.html`，`orchestrator/interfaces/web/templates/run_detail.html`，`tests/test_web_ui.py`
- 验证：`tests/test_web_ui.py` 为 `9 passed`，全量 `python -m pytest -q` 为 `76 passed`，team patch smoke run=`run-20260522-170355-050572`。
- 恢复提示：下一步启动 Web 服务并做浏览器侧真实点击验证，必要时补 Playwright/HTTP smoke。

# 2026-05-22 Web UI 乱码修复状态增量

- 状态：已完成
- 摘要：Web 首页、Job 状态页、Run 详情页和后端动态文案已恢复为正常 UTF-8 中文。
- 产物：`orchestrator/interfaces/web/main.py`，`orchestrator/interfaces/web/templates/index.html`，`orchestrator/interfaces/web/templates/job_status.html`，`orchestrator/interfaces/web/templates/run_detail.html`
- 验证：Web 首页 `status=200`，包含“新建任务”和 `omx_team_patch`，无典型乱码 `锛`；全量 `python -m pytest -q` 为 `76 passed`。
# 2026-05-27 Web UI Direct Run Duplicate Guard

- 状态：已完成
- 摘要：`/templates/run` 复用同模板运行中的 persisted Job，首页直接运行按钮提交后进入 `提交中...` 禁用态，降低重复提交风险。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 通过，`41 passed`；`python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` 通过。
- 2026-05-27 Web UI Task Management Navigation：已完成。新增顶部菜单和 `/tasks` 任务管理页，支持按全部、运行中、已完成、失败筛选 persisted Web Jobs；重复模板运行会打开已有 Job 并显示说明。验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 通过，`43 passed`。
- 2026-05-27 Web UI Task Management Workspace：已完成。`/tasks` 改为左侧菜单工作台布局，任务列表上方提供 `新建任务` 按钮，点击后弹出表单并复用 `/tasks/run` 提交流程。验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 通过，`44 passed`。
- 2026-05-27 Web UI Task List Table：已完成。`/tasks` 任务列表改为真实表格，列为状态、Job ID、Run ID、模板、执行、更新时间、操作，并保留窄屏横向滚动。验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 通过，`44 passed`。
# 2026-06-09 Web Audit Archive Search

- Status: completed.
- Summary: add opt-in `scope=all` search/export for rotated Web task-manager audit archives while preserving active-only default behavior.
- Process file: `.codex/plans/main/web-audit-archive-search/process.md`
- Verification: focused audit tests passed with `12 passed, 54 deselected`; Web/audit-log tests passed with `66 passed`; full `python -m pytest -q` passed with `154 passed`.

# 2026-06-09 External Agent Closed Loop Smoke

- Status: completed.
- Summary: add a script-level smoke for external command-agent execution from task JSON through CLI, wrapper process, reviewer JSON, quality gate, and final report artifacts.
- Process file: `.codex/plans/main/external-agent-closed-loop-smoke/process.md`
- Verification: `python scripts/run_external_agent_closed_loop_smoke.py` passed with `external_agent_closed_loop_smoke=passed`; targeted external-agent pytest passed with `17 passed`; full `python -m pytest -q` passed with `152 passed`.

# 2026-06-09 Web Browser Smoke

- Status: completed.
- Summary: add a real Uvicorn-process Web smoke that exercises the main operator path over HTTP in process-scoped `.tmp/web-browser-smoke/run-{pid}` workspaces with stale `run-*` cleanup, including archived audit provenance, mock template run flow, and external-agent wrapper provenance on run detail plus run audit Markdown.
- Process file: `.codex/plans/main/web-browser-smoke/process.md`
- Verification: `python scripts/run_web_browser_smoke.py` passed with `web_external_agent_provenance_smoke=passed` and `web_browser_smoke=passed`; `python -m pytest -q tests/test_web_browser_smoke.py` passed with `2 passed`; `python -m pytest -q` passed with `151 passed`.
