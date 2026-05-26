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
