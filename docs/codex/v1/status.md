# 项目状态

- 当前版本：v1
- 当前阶段：实现中
- 当前主题：自动循环进化编码智能体系统
- 说明：此文件用于记录需求、设计、计划、实现与追踪的主线状态。

## 需求索引

| 主题 | 需求文档 | 设计文档 | 计划文档 | Trace 文档 |
| :--- | :--- | :--- | :--- | :--- |
| 自动循环进化编码智能体系统 | `docs/codex/v1/requirements/自动循环进化编码智能体系统-requirements.md` | `docs/codex/v1/designs/自动循环进化编码智能体系统-technical-design.md` | `docs/codex/v1/plans/自动循环进化编码智能体系统-mvp-plan.md` | 待补充 |

## 进度与状态

| 主题 | 当前状态 | 需求状态 | 设计状态 | 计划状态 | 实现状态 | 备注 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 自动循环进化编码智能体系统 | 实现中 | 已完成 | 已完成 | 已完成 | 第四批命令安全与 heartbeat 完成 | 已创建 DDD 骨架，跑通 ShellAgent + ShellCheckRunner；新增 SafeCommandRunner、命令安全策略和 FileHeartbeat。 |

## 变更记录

| 时间 | 主题 | 变更 |
| :--- | :--- | :--- |
| 2026-05-21 | 自动循环进化编码智能体系统 | 新增 V3 设计文档，更新项目状态为已设计。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 新增 V4 设计文档，补充 malformed JSON 重试、质量门控短路、Diff 风险评分和 Orchestrator 心跳。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 新增 V5 设计文档，补充 Review JSON 修复提示字段模板和 change_type 测试覆盖扣分豁免。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 新增 V6 设计文档，补充 Review 修复提示动态 task_id 和 change_type=config 的 elevated 权限映射。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 新增 V7 设计文档，固化 review.task_id 一致性校验和 config 权限映射顺序。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 基于 V7 补齐需求文档、对外技术方案、MVP 实施计划和演讲大纲，状态推进到已计划。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成第一批 DDD 实现：领域模型/服务、端口、Mock/Fake 适配器、RunTaskUseCase、CLI、示例任务和基础测试。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成第二批实现：新增 ShellCheckRunner、GitDiffProvider、真实检查示例任务和基础设施适配器测试。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成第三批实现：新增 ShellAgent、agent_mode/agent_commands 配置、CLI agent 开关、shell reviewer 示例和重试测试。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成第四批实现：新增 SafeCommandRunner、命令安全校验、FileHeartbeat，并让 ShellAgent/ShellCheckRunner 共用安全命令执行器。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成第五批实现：新增 pending rule proposal 能力。HALTED 场景生成 `.omx/runs/{run_id}/pending-rules/RP-001.md` 候选规则，DONE 场景不生成；全量测试 14 passed，shell-agent real-checks 烟测通过。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成第六批实现：新增真实 Git diff 集成测试，覆盖源码/测试变更、大 diff、删除文件、forbidden path、refactor/config 豁免；`DiffRiskService` 增加 forbidden path 风险扣分；全量测试 19 passed，CLI `--git-diff` 烟测通过。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成第七批实现：新增 `allowed_command_prefixes` 可配置命令 allowlist，`SafeCommandRunner` 执行前按 task 校验命令；危险命令仍优先阻断；全量测试 24 passed，CLI real-checks + git-diff 烟测通过。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成第八批实现：新增 `AgentPromptBuilder`、`CodexAgent`、`OmxAgent` 与 CLI `--agent codex|omx` 支持；ShellAgent 复用共享 prompt/命令上下文；新增 `examples/task.codex-agent.json` dry-run 示例；全量测试 27 passed，shell/codex 两条 CLI 烟测通过。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成第九批 trace 审查：新增 `docs/codex/v1/trace/自动循环进化编码智能体系统-mvp-trace.md`，结论为 MVP 第一阶段主链路基本闭环，仍需补真实 Agent 协议、统一 phase logging、resume CLI 和规则聚类审批流。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 收口 GAP-01：新增真实 Codex/OMX Agent CLI 协议文档、Codex/OMX 真实接入模板，并补充外部 Agent prompt/reason/退出码契约测试；全量测试 36 passed，Codex dry-run CLI 烟测通过。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 新增 `scripts/run_external_agent.py` 稳定包装入口和 `examples/task.codex-wrapper-dry-run.json`，支持 dry-run 与后端命令模板转发；全量测试 39 passed，wrapper dry-run CLI 烟测通过。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成 OMX setup 验证，`omx doctor` 为 15 passed、1 warning、0 failed；增强 wrapper 支持 stdin prompt 和 output-last-message，更新 OMX real template；全量测试 41 passed。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成受控真实 OMX smoke：Orchestrator 能调起 `omx exec`，但当前 Windows Codex 执行沙箱报 `CreateProcessWithLogonW failed: 1385`，导致真实写操作未完成；补 BOM、绝对路径和后端输出编码容错，全量测试 44 passed。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成 Windows 兼容 Patch 模式：新增 `omx_patch` Agent、patch JSON 模型/校验/应用器和 smoke 示例；Orchestrator 受控应用 `replace_text` patch，smoke `run-20260521-162852-762772` 到 done，全量测试 47 passed。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 完成真实 `omx exec` patch-only 后端验证：patch prompt 注入允许文件快照，真实 OMX 输出 patch JSON，Orchestrator 应用 patch；smoke `run-20260521-163411-124400` 到 done，全量测试 48 passed。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 扩展 patch schema 支持 `create_file`/`delete_file`，PatchApplier 返回 changed/created/deleted 与 risk_score；真实 OMX patch smoke `run-20260521-164502-235168` 到 done，全量测试 50 passed。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 新增 patch 人工审批开关：支持风险阈值、delete_file 强制审批、pending-patches 落盘；审批 smoke `run-20260521-165047-273285` halted 且未删除文件，全量测试 52 passed。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 新增 `patches list/apply/reject` CLI 和 PendingPatchService；审批 smoke `run-20260521-170009-452873` 经 apply 后删除目标文件，全量测试 53 passed。 |
| 2026-05-21 | 自动循环进化编码智能体系统 | 新增 `patches apply --rerun-checks`，审批应用后重跑 hard checks 并写入 `post_apply_checks`；验证 run `run-20260521-170424-438800` 输出 `checks_passed=True`，全量测试 53 passed。 |

## 2026-05-21 Trace 状态增量

- Trace 文档：`docs/codex/v1/trace/自动循环进化编码智能体系统-mvp-trace.md`
- 审查结论：MVP 第一阶段实现与 V7 架构、需求文档、MVP 计划总体一致；P0 主流程已闭环。
- 主要缺口：真实 Codex/OMX 二进制的受控写操作验证、半截运行续跑、正式人工审批/PR 流程和生产级权限策略。
- GAP-02 更新：统一 phase logging 已补齐，新增 `logs/phase.log`；同秒运行目录碰撞已通过微秒级 `run_id` 修复。
- GAP-03 更新：`quality_report.json` 保持扁平结构，V7 示例和正式技术文档字段说明已同步；Hard Check 明细继续写入 `hard_checks.json`。
- GAP-05 更新：新增 `resume --run-id` 恢复查看和 `resume --run-id <id> --rerun` fresh rerun；当前不做半截续跑。
- GAP-04 更新：新增 `.omx/runs/rule_proposals_index.json` 历史索引，按 `source + reason` 聚类候选规则并统计 observed_count/run_ids/task_ids。
- Rule Proposal 审批流更新：新增 `rules list` 与 `rules review --cluster-key ... --status pending|approved|rejected`，只更新索引审批状态，不自动写正式 Skill。
# 2026-05-21 最新实现增量

- Patch 协议扩展：`omx_patch` 支持 `unified_diff` operation，Orchestrator 会解析 hunk、校验上下文/删除行，并在绝对路径 worktree 内受控应用。
- Pending Patch 审批增强：`patches apply --rerun-task` 已改为补丁应用后的验证闭环，会新建 post-apply validation run，执行 hard checks、Reviewer 与 Quality Gate，不会再次调用 coder/fixer 生成补丁。
- 审计记录：pending patch JSON 会写入 `post_apply_rerun.run_id/status/phase/attempt/run_dir`；新 run 会生成 `final_report.md`、`hard_checks.json`、`review.json`、`quality_report.json`。
- 验证结果：`python -m pytest -q` 通过，当前为 `57 passed`。

# 2026-05-21 第三步规划

- 新增计划文档：`docs/codex/v1/plans/自动循环进化编码智能体系统-third-step-plan.md`。
- 第三步目标：把 patch-only 能力推进到可演示、可审计、可运维，重点包括真实 unified diff smoke、`patches list` 审计展示增强、失败诊断与演示脚本。
- 建议执行顺序：先增强 `patches list`，再补 unified diff smoke，然后补失败诊断，最后同步文档并全量回归。

# 2026-05-21 第三步实现进度

- 已完成 `patches list` 审计展示增强：新增 `checks_status=not_run|passed|failed`，并展示 `rerun_status/rerun_run_id/rerun_phase/rerun_attempt`。
- 兼容性：保留旧字段 `checks_passed=True|False`，避免影响已有调用方。
- 验证：`tests/test_cli_resume.py` 与 `tests/test_patch_agent.py` 已通过。
- 已完成 unified diff smoke：新增 `examples/task.omx-patch-unified-diff-smoke.json`、`examples/patch_unified_diff_backend.py` 和 `.tmp/omx-unified-diff-smoke/` 工作区。
- Smoke 结果：`run-20260521-173445-649699` 到 `status=done`。
- 额外修正：`PatchApplier` 对没有 hunk 的 unified diff 直接拒绝，避免静默假成功。
- 已完成失败诊断增强：patch 输出失败时写入 `{role}_patch_raw_output.txt` 与 `{role}_patch_diagnostics.json`；`patches apply --rerun-task` 会把验证失败原因写入 `post_apply_rerun.reason` 并通过 CLI 输出 `rerun_reason`。
- 已完成第三步演示脚本：新增 `scripts/run_patch_demo.py` 与 `docs/codex/v1/plans/自动循环进化编码智能体系统-demo-script.md`。
- 演示验证：`python scripts/run_patch_demo.py` 跑通，unified diff smoke run=`run-20260521-174136-200457` 到 `done`，pending patch approval run=`run-20260521-174138-333591` 经 `--rerun-task` 后 `rerun_status=done`。

# 2026-05-21 第三步 Trace 收口

- 新增 trace 文档：`docs/codex/v1/trace/自动循环进化编码智能体系统-third-step-trace.md`。
- 审查结论：第三步主体目标已闭环，包括 unified diff smoke、`patches list` 审计展示、失败诊断产物和演示脚本。
- 剩余建议：真实 OMX/Codex unified diff smoke 可作为后续环境依赖型增强，不阻塞第三步收口。

# 2026-05-21 真实 Unified Diff Smoke 模板

- 已补环境依赖型模板：`examples/task.omx-patch-unified-diff-real-smoke.json`、`examples/task.codex-patch-unified-diff-real-smoke.json`。
- 已补说明文档：`docs/codex/v1/plans/自动循环进化编码智能体系统-real-unified-diff-smoke.md`。
- 验证：两个 task 模板可被 `TaskLoader` 正常读取；`python -m pytest -q` 通过，61 passed。
- 说明：真实 smoke 需要本机配置 `OMX_OMX_*_COMMAND` 或 `OMX_CODEX_*_COMMAND`，不纳入默认 pytest。

# 2026-05-21 Web UI MVP

- 新增本地 Web 输入界面，入口为 `orchestrator/interfaces/web/main.py`。
- 支持新建任务、运行 examples、查看 run 详情、查看 phase/agent 日志、审批 pending patch，并可在审批后触发 rerun-task。
- 新增样式与模板：`orchestrator/interfaces/web/static/styles.css`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/templates/run_detail.html`。
- 新增说明文档：`docs/codex/v1/plans/自动循环进化编码智能体系统-web-ui-mvp.md`。
- 验证：`python -m pytest -q` 通过，当前为 63 passed。
- 使用：运行 `python -m orchestrator.interfaces.web.main`，打开 `http://127.0.0.1:8765`。

# 2026-05-22 Web UI 真实主线调整

- 明确后续默认路线为 `Orchestrator -> OMX -> Codex exec -> patch JSON -> Orchestrator 审批/应用/验证`。
- Web UI 新建任务默认改为 `agent_mode=omx_patch`，Patch coder/fixer 默认通过 `scripts/run_external_agent.py --runtime omx` 调用 `omx exec`。
- 页面顶部补充“真实模式：OMX -> Codex -> Patch JSON”说明，弱化 mock 模式。
- 本机 `omx exec --help` 显示其底层入口为 `codex exec`，`omx doctor` 显示 Codex CLI 已安装。
- 验证：`python -m pytest -q` 通过，当前为 63 passed。

# 2026-05-22 下一阶段规划

- 已确认真实链路跑通：`Orchestrator -> OMX -> Codex exec -> patch JSON -> Orchestrator`。
- 成功样例：`run-20260522-140604-839823`，修改 `.tmp/omx-unified-diff-smoke/calculator.py`，工作区测试 `1 passed`。
- 已新增下一阶段计划：`docs/codex/v1/plans/自动循环进化编码智能体系统-next-step-plan.md`。
- 推荐下一步优先做“异步任务与运行状态落盘”，随后做真实项目接入表单校验、Patch Diff 可视化审批、真实项目回归 Smoke 和 OMX team 编排模式。
- 当前系统回归基线：`python -m pytest -q` 为 64 passed。
# 2026-05-22 Web UI 异步任务落盘

- 已完成“异步任务与运行状态入库”：Web 提交任务后不再依赖内存态，任务状态写入 SQLite 数据库 `.omx/orchestrator.db` 的 `web_jobs` 表。
- `/jobs/{job_id}` 会读取数据库状态，任务完成后自动跳转到 `/runs/{run_id}`；运行中页面每 3 秒刷新一次。
- 首页已新增“最近 Jobs”区域，可直接看到仍在运行、失败或已完成的异步任务。
- 同步修复 Web 模板与测试中的乱码文本，首页、任务状态页、运行详情页恢复可读中文。
- 验证结果：`python -m pytest -q` 通过，当前为 `66 passed`。

# 2026-05-22 Web UI 真实项目接入表单校验

- 已完成首页任务提交前校验：Task ID、change_type、agent_mode、worktree、allowed paths、真实检查命令和高风险命令会在提交前拦截。
- 校验失败时直接在首页展示错误列表并返回 `422`，不会创建后台 Job 记录。
- Web 首页、任务状态页、运行详情页再次统一修复为可读中文。
- 验证结果：`python -m pytest -q` 通过，当前为 `68 passed`。

# 2026-05-22 Patch Diff 可视化审批

- 已完成 pending patch 可视化摘要：`PendingPatchService.list()` 会返回 patch summary、risk_reasons 和 operation previews。
- 运行详情页的补丁审批区已展示风险原因、摘要、操作类型、目标文件和预览内容。
- 预览覆盖 `replace_text`、`create_file`、`delete_file`、`unified_diff`，长内容会截断避免页面过长。
- 验证结果：`python -m pytest -q` 通过，当前为 `69 passed`。

# 2026-05-22 真实项目回归 Smoke

- 已新增 `scripts/run_real_project_smoke.py`，自动创建独立临时 worktree `.tmp/real-project-smoke`。
- Smoke 覆盖：生成 pending patch、读取 patch preview、审批应用、`--rerun-task` 重新跑 hard checks/review/quality gate、验证临时项目 pytest。
- 已新增 `tests/test_real_project_smoke.py`，把该 smoke 纳入回归。
- 验证结果：`python scripts/run_real_project_smoke.py` 通过；`python -m pytest -q` 通过，当前为 `70 passed`。

# 2026-05-22 OMX Team Protocol 设计契约

- 已新增 OMX team 编排协议文档：`docs/codex/v1/designs/自动循环进化编码智能体系统-team-protocol.md`。
- 已新增可解析示例：`examples/team_task.omx-team-patch.json` 与 `examples/team_result.omx-team-patch.json`。
- 协议明确边界：OMX team 只产出结构化 `patch_plan.json`、`review.json` 与 diagnostics，真实 worktree 写入、审批、测试和 Quality Gate 仍由 Orchestrator 最终负责。
- 已新增契约测试：`tests/test_team_protocol_examples.py`，校验示例 JSON 与现有 `PatchPlan` / `ReviewResult` 模型兼容。
- 验证结果：`python -m pytest -q tests/test_team_protocol_examples.py` 通过，`2 passed`；`python -m pytest -q` 全量通过，当前为 `72 passed`。
- 下一步建议：实现 `agent_mode=omx_team_patch`，让 Orchestrator 调用 OMX team 后读取 `team_result.json`，再复用现有 PatchValidator、ReviewValidator、PendingPatchService 和 rerun-task 闭环。

# 2026-05-22 OMX Team Patch 最小执行链路

- 已实现 `agent_mode=omx_team_patch`：新增 `OmxTeamPatchAgent`，支持调用 OMX team 后端并解析 `team_result.json`。
- Team 返回的 `artifacts.patch_plan` 会复用现有 `PatchValidator` / `PatchApplier` / `PatchApprovalPolicy`；`artifacts.review` 会缓存并在 review phase 复用。
- 已新增 smoke 示例：`examples/task.omx-team-patch-smoke.json` 与 `examples/team_patch_backend.py`。
- 已新增测试：`tests/test_omx_team_patch_agent.py`，覆盖成功应用 team patch 与非法 team result diagnostics。
- 验证结果：`python -m orchestrator.interfaces.cli.main --task examples/task.omx-team-patch-smoke.json --agent omx_team_patch --real-checks` 成功，run_id=`run-20260522-163446-036926`，status=`done`；`python -m pytest -q` 全量通过，当前为 `74 passed`。
- 下一步建议：把 Web UI 的 agent_mode 选项接入 `omx_team_patch`，并展示 team result / diagnostics。

# 2026-05-22 Web UI 接入 OMX Team Patch

- Web 后端已允许 `agent_mode=omx_team_patch`，表单提交校验不再拦截 Team 模式。
- 首页 Agent 下拉与示例运行默认值已接入 `omx_team_patch`。
- Run detail 诊断区新增 `Team Result` 与 `Team Diagnostics`，会读取当前 run 下最新的 `attempts/*/team_result.json` 和 `attempts/*/team_diagnostics.json`。
- Web 测试已改为稳定结构断言，避免继续依赖历史乱码文本。
- 验证结果：`python -m pytest -q tests/test_web_ui.py` 通过，`9 passed`；`python -m pytest -q` 全量通过，当前为 `76 passed`。
- CLI smoke 复测通过：`python -m orchestrator.interfaces.cli.main --task examples/task.omx-team-patch-smoke.json --agent omx_team_patch --real-checks`，run_id=`run-20260522-170355-050572`，status=`done`。
- 下一步建议：启动 Web 服务，用页面提交一次 `omx_team_patch` 任务，确认浏览器侧 job -> run detail -> team result 展示闭环。

# 2026-05-22 Web UI 中文乱码修复

- 已将 Web 三个模板 `index.html`、`job_status.html`、`run_detail.html` 重写为干净 UTF-8 中文。
- 已将 `orchestrator/interfaces/web/main.py` 中的默认表单、校验错误、Job 状态和 run summary 文案恢复为正常中文。
- 已重启 8765 Web 服务，并验证首页返回 `status=200`、包含“新建任务”、包含 `omx_team_patch`，且不再包含典型乱码片段 `锛`。
- 验证结果：`python -m pytest -q tests/test_web_ui.py` 通过，`9 passed`；`python -m pytest -q` 全量通过，当前为 `76 passed`。
# 2026-05-25 Web UI Docker Agent Command Presets

- Web UI 新增 `Docker agent 命令预设`，支持从页面选择安全模板生成容器内 agent 命令。
- 当前内置 `custom`、`team_patch_backend`、`patch_json_backend` 三类预设。
- 后端按 `DOCKER_AGENT_COMMAND_PRESETS` 白名单解析预设；非 `custom` 预设会覆盖手写命令，并校验必须使用 `execution_backend=docker` 和匹配的 `agent_mode`。
- Docker path guardrail 继续生效，生成后的命令仍拒绝 Windows 宿主路径和非白名单绝对路径。
- 验证：`python -m pytest -q tests/test_web_ui.py` 为 `24 passed`；`python -m pytest -q` 为 `103 passed`。
# 2026-05-25 Web UI Docker Agent Preset Closed Loop

- 默认 smoke worktree 现在会自动生成 `docker_team_backend.py` 和 `patch_backend.py`，配合 Docker agent 命令预设可直接运行真实闭环。
- Web 表单选择 `execution_backend=docker`、`agent_mode=omx_team_patch`、`command_preset=team_patch_backend` 后，无需手写容器路径即可提交任务。
- 验证链路覆盖：Web 提交 -> Docker agent 生成 `team_result` -> Orchestrator 校验并应用 patch -> Docker hard check -> run detail 展示结果。
- 验证：`python -m pytest -q tests/test_web_ui.py` 为 `26 passed`；`python -m pytest -q` 为 `105 passed`。
# 2026-05-25 Run Detail Docker Evidence

- Run detail 新增 `Docker 执行证据` 面板，读取 `.omx/runs/{run_id}/logs/docker_sandbox.jsonl`。
- 页面展示 Docker 执行次数、image、network、worktree mount、容器路径、最后阶段、退出码、阶段列表和最近 5 条 Docker 日志。
- 无 Docker 日志时展示空状态，避免用户误以为本地任务也跑在容器里。
- 验证：`python -m pytest -q tests/test_web_ui.py` 为 `27 passed`；`python -m pytest -q` 为 `106 passed`。
# 2026-05-25 Web UI Docker Agent Quickstart

- 首页右侧新增 `Docker Agent 快速上手` 面板，明确 Docker backend、Agent、命令预设和 Run detail 证据查看入口。
- 新增文档：`docs/codex/v1/plans/web-ui-docker-agent-quickstart.md`。
- 文档覆盖启动 Web UI、选择 Docker agent 预设、默认模板文件、安全边界和验证证据。
- 验证：`python -m pytest -q tests/test_web_ui.py` 为 `27 passed`；`python -m pytest -q` 为 `106 passed`。
# 2026-05-26 Web UI Task Templates

- 状态：已完成
- 摘要：Web UI 新增后端白名单任务模板，用户可在首页选择模板自动填充 agent/backend/preset/paths/check command；Job Status 和 Run Detail 均新增启动配置面板用于复盘运行来源。
- 产物：`orchestrator/application/task_template_registry.py`、`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/templates/job_status.html`、`orchestrator/interfaces/web/templates/run_detail.html`、`tests/test_task_template_registry.py`、`tests/test_web_ui.py`、`docs/codex/v1/plans/web-ui-task-template-management.md`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `38 passed`；`python -m pytest -q` 为 `117 passed`。
# 2026-05-26 Web UI Task Template Preview

- 状态：已完成
- 摘要：Homepage task template cards now preview startup config before applying a template: `execution_backend`, `agent_mode`, `command_preset`, `allowed_paths`, and `check_command`.
- 产物：`orchestrator/application/task_template_registry.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_task_template_registry.py`、`tests/test_web_ui.py`、`docs/codex/v1/plans/web-ui-task-template-management.md`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `38 passed`；`python -m pytest -q` 为 `117 passed`；`python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` 通过。
# 2026-05-26 Web UI Task Template Badges

- 状态：已完成
- 摘要：首页任务模板卡片新增后端驱动标签，展示 `Default`、`Recommended`、`Docker`、`Local`、`Demo` 等提示，帮助用户优先选择推荐模板。
- 产物：`orchestrator/application/task_template_registry.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_task_template_registry.py`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `38 passed`；`python -m pytest -q` 为 `117 passed`；`python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` 通过。
# 2026-05-26 Web UI Task Template Recent Job

- 状态：已完成
- 摘要：首页任务模板卡片新增最近运行提示，会根据 SQLite 最近 Job 和 task JSON 的 `template_id` 显示该模板最近一次 Job 的 `status/run_id`，并链接到 Job 状态页。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_web_ui.py`、`docs/codex/v1/plans/web-ui-task-template-management.md`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `39 passed`；`python -m pytest -q` 为 `118 passed`；`python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` 通过。
# 2026-05-26 Web UI Task Template Recent Job Status Color

- 状态：已完成
- 摘要：首页任务模板卡片的最近运行链接新增状态色：`done` 为绿色、`failed` 为红色、`running` 为蓝色，便于快速判断模板最近一次运行结果。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `39 passed`；`python -m pytest -q` 为 `118 passed`；`python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` 通过。
# 2026-05-26 Web UI Direct Run Template

- 状态：已完成
- 摘要：首页任务模板卡片新增 `直接运行` 按钮，提交到 `/templates/run`，由后端白名单模板生成 task JSON 并直接启动 Job。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`orchestrator/interfaces/web/static/styles.css`、`tests/test_web_ui.py`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 为 `40 passed`；`python -m pytest -q` 为 `119 passed`；`python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` 通过。
# 2026-05-26 Web UI Task Template Preview HTML

- 状态：已完成
- 摘要：新增静态 HTML 预览页，用于直观看到首页任务模板增强效果，包括配置预览、推荐标签、最近运行状态、状态色和 `直接运行` 按钮。
- 产物：`项目工程文档/WebUI任务模板增强预览.html`
- 验证：已确认文件生成，大小约 12KB，可直接用浏览器打开查看。
# 2026-05-27 Web UI Direct Run Duplicate Guard

- 状态：已完成
- 摘要：首页任务模板 `直接运行` 现在具备前后端双层防重复提交：浏览器提交后按钮禁用并显示 `提交中...`；后端 `/templates/run` 会复用同模板仍在 `running` 的 SQLite Job，避免重复创建任务。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/index.html`、`tests/test_web_ui.py`、`docs/codex/v1/plans/web-ui-task-template-management.md`
- 验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 通过，`41 passed`；`python -m py_compile orchestrator/application/task_template_registry.py orchestrator/interfaces/web/main.py` 通过。
- 2026-05-27 Web UI Task Management Navigation：已完成。新增顶部菜单和 `/tasks` 任务管理页，支持按全部、运行中、已完成、失败筛选 persisted Web Jobs；重复点击模板直接运行时会打开已有任务并显示说明。验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 通过，`43 passed`。
- 2026-05-27 Web UI Task Management Workspace：已完成。`/tasks` 改为左侧菜单工作台布局，任务列表上方提供 `新建任务` 按钮，点击后弹出表单并复用 `/tasks/run` 提交流程。验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 通过，`44 passed`。
- 2026-05-27 Web UI Task List Table：已完成。`/tasks` 任务列表改为真实表格，列为状态、Job ID、Run ID、模板、执行、更新时间、操作，并保留窄屏横向滚动。验证：`python -m pytest -q tests/test_task_template_registry.py tests/test_web_ui.py` 通过，`44 passed`。

# 2026-06-02 真实演示验收与对外文档收口

- 状态：已完成。
- 真实演示：使用受控 Web 服务 `http://127.0.0.1:8766` 提交 `Docker OMX Team Patch` 推荐模板，Job `job-20260602-100617-498307`、Run `run-20260602-100617-650766` 跑通到 `done`。
- 质量证据：Docker `python:3.12-slim`、`network=none`、`worktree_mount=readonly`；hard check `python -m unittest -q` 通过；Review `pass=true`、`confidence=91`；Quality Gate `quality_score=100`、`decision=done`。
- 页面证据：任务管理页可看到已完成 Job 和重新运行入口；Run 详情页可看到运行成功、执行摘要、阶段时间线、运行产物、Docker 执行证据、执行链路和 Team Result。
- 文档产物：新增 `docs/codex/v1/plans/demo-readiness.md`，README 已补齐常用链接、目录、阅读路径、Web 页面入口、演示前检查清单、最近真实演示摘要、Mermaid 架构图和自动循环流程图。
- 当前验证基线：`python -m pytest -q tests/test_web_ui.py` 为 `48 passed`；`python -m pytest -q` 为 `133 passed`。
- 当前结论：Evoloop 本地真实演示链路可用，可用于对外演讲和技术评审；后续建议围绕演示稳定性、UI 细节和真实 Codex/OMX 环境依赖继续增强。

# 2026-06-04 Web UI Task Manager Rerun Filter

- 状态：已完成。
- 摘要：任务管理页新增 `Rerun` 筛选，可按全部、可重新运行、不可重新运行过滤任务；筛选状态会在分页、停止和删除操作中保留。
- 搜索增强：任务列表搜索现在包含不可重新运行原因，例如 `缺少原始 task.json`。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/tasks.html`、`tests/test_web_ui.py`、`docs/codex/v1/plans/web-ui-task-template-management.md`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager"` 通过，`5 passed, 46 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`51 passed`；`python -m pytest -q` 通过，`136 passed`。
- Trace：`docs/codex/v1/trace/web-ui-task-manager-rerun-filter-trace.md`，结论为计划、实现、测试和状态记录已闭环，未发现未对齐项。

# 2026-06-04 Web UI Task Manager Batch Operations

- 状态：已完成。
- 摘要：任务管理页新增当前页批量选择和批量操作，支持停止运行中任务、重新运行可重跑任务、删除 Web Job 记录，并显示成功/跳过/失败数量。
- 安全边界：批量删除只移除 Web Job 记录，不删除 run 目录和审计日志；批量重新运行跳过 running Job 和缺少原始 `task.json` 的 Job。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/tasks.html`、`tests/test_web_ui.py`、`docs/codex/v1/plans/web-ui-task-template-management.md`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager"` 通过，`6 passed, 46 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`python -m pytest -q` 通过，`137 passed`；渲染 `/tasks` 返回 200，页面包含批量表单、全选控件、`/tasks/batch` endpoint 和全选 JS 绑定；本地 Uvicorn smoke `http://127.0.0.1:8767/tasks` 返回 200，并包含同一组任务管理控件；非破坏性 `POST /tasks/batch` 未选择任务时返回 303 到已编码的 `batch=` 提示，回跳页显示 `未选择任务，未执行批量操作。`。
- 视觉检查：本地 Chrome headless 截图 `.tmp/task-manager-8767.png` 显示任务管理标题、筛选区、批量操作下拉、checkbox 列、任务表格和行操作按钮正常渲染，未见明显重叠。
- Trace：`docs/codex/v1/trace/web-ui-task-manager-batch-operations-trace.md`，结论为计划、实现、测试和状态记录已闭环，未发现未对齐项。
# 2026-06-08 Web UI Task Manager Operational Audit

- 状态：已计划。
- 摘要：下一步优先补齐任务管理页操作审计能力，为单条/批量停止、重跑、删除记录持久化事件证据，覆盖 selected/processed/skipped/failed Job、run 关联、请求筛选上下文和页面可导出的 Markdown 摘要。
- 计划文档：`docs/codex/v1/plans/web-ui-task-manager-operational-audit.md`。
- 推荐实施顺序：先新增 JSONL 审计写入器，再接入单条操作，然后接入批量操作结构化 summary，最后增加 `/tasks/audit.md` 和测试/trace。
- 验证计划：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"`；`python -m py_compile orchestrator/interfaces/web/main.py`；`python -m pytest -q tests/test_web_ui.py`；`python -m pytest -q`；`git diff --check`。

# 2026-06-08 Web UI Task Manager Operational Audit 实现

- 状态：已完成。
- 摘要：任务管理页单条/批量 stop、rerun、delete 已写入 `.omx/web-job-audit.jsonl`，记录 selected/processed/skipped/failed Job、run 关联、请求上下文和原因明细；新增 `/tasks/audit.md` Markdown 导出和页面 `操作审计` 入口。
- 产物：`orchestrator/infrastructure/persistence/web_job_audit_log.py`、`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/tasks.html`、`tests/test_web_ui.py`、`docs/codex/v1/trace/web-ui-task-manager-operational-audit-trace.md`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`python -m pytest -q` 通过，`137 passed`。
- Trace：`docs/codex/v1/trace/web-ui-task-manager-operational-audit-trace.md`，结论为计划、实现、测试和状态记录已闭环，剩余风险为 JSONL 暂未轮转且审计写入失败静默忽略。

# 2026-06-08 Web UI Task Manager Audit Page

- 状态：已完成。
- 摘要：新增 `/tasks/audit` 可浏览审计页，直接展示最近 50 条任务操作审计记录，包括事件类型、成功/跳过/失败数量、Job 明细、Run 关联和跳过原因，并保留 `/tasks/audit.md` Markdown 导出。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/task_audit.html`、`orchestrator/interfaces/web/templates/tasks.html`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`。

# 2026-06-08 Web UI Task Manager Audit Filter

- 状态：已完成。
- 摘要：`/tasks/audit` 新增事件类型筛选，可按 `batch_stop`、`batch_rerun`、`batch_delete` 等审计事件过滤最近记录；同时将新审计模板整理为可读中文。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/task_audit.html`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`git diff --check` 通过。

# 2026-06-08 Web UI Task Manager Audit Search

- 状态：已完成。
- 摘要：`/tasks/audit` 新增关键词搜索，可按 Job ID、Run ID、事件类型、消息、请求上下文和原因明细过滤最近审计记录，并保留事件类型筛选组合使用。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/task_audit.html`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`git diff --check` 通过。

# 2026-06-08 Web UI Task Manager Audit Limit

- 状态：已完成。
- 摘要：`/tasks/audit` 新增最近记录数量选择，支持 25、50、100、200 条，默认仍为 50；非法 limit 自动回退到 50。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/task_audit.html`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`git diff --check` 通过。

# 2026-06-08 Web UI Task Manager Audit Outcome Filter

- 状态：已完成。
- 摘要：`/tasks/audit` 新增结果筛选，支持按全部、存在跳过、存在失败、无跳过且无失败查看最近任务操作审计记录；非法 `outcome` 会回退到 `all`。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/task_audit.html`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`python -m pytest -q` 通过，`137 passed`；`git diff --check` 通过。

# 2026-06-08 Web UI Task Manager Audit Empty Filter Hint

- 状态：已完成。
- 摘要：`/tasks/audit` 在存在审计记录但当前事件类型、结果和搜索组合无命中时，会显示当前筛选条件摘要和清空筛选入口，区分“无审计记录”和“筛选无结果”。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/task_audit.html`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`python -m pytest -q` 通过，`137 passed`；`git diff --check` 通过。

# 2026-06-08 Web UI Task Manager Audit Filtered Markdown Export

- 状态：已完成。
- 摘要：`/tasks/audit.md` 支持复用审计页的 `event_type`、`outcome`、`q`、`limit` 参数；`/tasks/audit` 的导出 Markdown 链接会带上当前筛选条件，默认无筛选导出仍保持 `/tasks/audit.md`。
- 产物：`orchestrator/interfaces/web/main.py`、`orchestrator/interfaces/web/templates/task_audit.html`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`python -m pytest -q` 通过，`137 passed`；`git diff --check` 通过。

# 2026-06-08 Web UI Task Manager Audit Markdown Filter Summary

- 状态：已完成。
- 摘要：`/tasks/audit.md` 导出内容顶部新增 Filters 行；无筛选时标记 `all`，带筛选时写入事件类型、结果和搜索词摘要，便于导出的审计证据离开页面后仍能识别范围。
- 产物：`orchestrator/interfaces/web/main.py`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`python -m pytest -q` 通过，`137 passed`；`git diff --check` 通过。

# 2026-06-08 Web UI Task Manager Audit Markdown Summary Counts

- 状态：已完成。
- 摘要：`/tasks/audit.md` 导出顶部新增 Records、Processed jobs、Skipped jobs、Failed jobs 汇总，便于直接判断当前导出证据覆盖范围和异常数量；汇总基于当前筛选后的记录计算。
- 产物：`orchestrator/interfaces/web/main.py`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`8 passed, 44 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py` 通过；`python -m pytest -q tests/test_web_ui.py` 通过，`52 passed`；`python -m pytest -q` 通过，`137 passed`；`git diff --check` 通过。
# 2026-06-08 Web UI Task Manager Audit Write Failure Logging

- 状态：已完成。
- 摘要：`_append_web_job_audit()` 在审计 JSONL 写入发生 `OSError` 时会写入 Web 模块 warning 日志并保留异常栈，同时继续保持任务 stop/delete/rerun 操作不被审计文件临时不可写阻断；非 `OSError` 不再被宽泛吞掉。
- 产物：`orchestrator/interfaces/web/main.py`、`tests/test_web_ui.py`。
- 验证：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"` 通过，`9 passed, 44 deselected`；`python -m py_compile orchestrator/interfaces/web/main.py` 通过。
# 2026-06-08 Web UI Operational Maintenance Hardening Plan

- 状态：已计划。
- 摘要：下一步建议从“继续堆功能”转为运维硬化，优先处理审计 JSONL 保留/轮转，再做保守的任务管理维护动作，最后补演示前只读健康检查。
- 计划文档：`docs/codex/v1/plans/web-ui-operational-maintenance-hardening.md`。
- 推荐顺序：Audit Log Retention And Rotation -> Task Manager Maintenance Actions -> Demo Readiness Health Check。
- 验证计划：`python -m pytest -q tests/test_web_ui.py -k "task_manager or audit"`；`python -m py_compile orchestrator/interfaces/web/main.py orchestrator/infrastructure/persistence/web_job_audit_log.py`；`python -m pytest -q tests/test_web_ui.py`；`python -m pytest -q`；`git diff --check`。
