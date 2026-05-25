# 恢复胶囊

- 任务需求：基于 V7 架构和 MVP 计划，使用 DDD 架构实现第一批 Mock 闭环。
- 关键决策：先实现纯本地 Mock 流程，不接真实 Codex/OMX；领域层不依赖基础设施。
- 当前阶段：第四批实现完成
- 已完成产物：DDD 包、领域模型/服务、端口、Mock/Fake 适配器、RunTaskUseCase、CLI、示例任务、基础测试、ShellCheckRunner、GitDiffProvider、ShellAgent、agent_mode/agent_commands 配置、SafeCommandRunner、FileHeartbeat。
- 剩余工作：后续阶段接入 Codex/OMX Agent、pending rule proposal、真实 Git diff 场景测试和更完整的命令 allowlist。
- 重要发现：当前项目无 git 仓库；pytest 和 pydantic 可用。

## 步骤列表

- [v] 创建 DDD 目录骨架和核心模型。
- [v] 实现领域服务：安全策略、Review 校验、Quality Gate、Diff 风险。
- [v] 实现端口与 mock/fake 适配器。
- [v] 实现 RunTaskUseCase、CLI、报告输出。
- [v] 添加测试并运行 pytest。
- [v] 更新文档状态并收尾。

## 研究发现

- MVP 第一阶段应先跑通 MockAgent + FakeCheckRunner。
- `change_type=config` 必须先 forbidden，再 elevated。
- Reviewer JSON 解析成功后仍需校验 `review.task_id == task.task_id`。
- `python -m pytest -q` 通过 6 个测试。
- `python -m orchestrator.interfaces.cli.main --task examples/task.mock.json` 成功生成 `.omx/runs/run-20260521-112436`。
- 第二批后 `python -m pytest -q` 通过 9 个测试。
- `python -m orchestrator.interfaces.cli.main --task examples/task.real-checks.json --real-checks` 成功生成 `.omx/runs/run-20260521-113011`，并真实执行 `python -m pytest -q tests`。
- 第三批后 `python -m pytest -q` 通过 11 个测试。
- `python -m orchestrator.interfaces.cli.main --task examples/task.shell-agent.json --real-checks` 成功生成 `.omx/runs/run-20260521-114325`，并通过 ShellAgent 调用 `examples/shell_reviewer.py`。
- 第四批后 `python -m pytest -q` 通过 13 个测试。
- `python -m orchestrator.interfaces.cli.main --task examples/task.shell-agent.json --real-checks` 成功生成 `.omx/runs/run-20260521-114703`，ShellAgent/ShellCheckRunner 均通过 SafeCommandRunner 执行。

## 错误记录

- 暂无。

## 2026-05-21 第五批实现记录

- 当前阶段：第五批实现完成。
- 已完成产物：`RuleProposal` 领域模型、`RuleProposalService`、`RuleProposalWriter`、`StateRepositoryPort.write_rule_proposal`、`FileStateRepository.write_rule_proposal`。
- 行为约束：仅在 `HALTED` 场景生成候选规则，写入 `.omx/runs/{run_id}/pending-rules/RP-001.md`；`DONE` 成功路径不生成候选规则；不自动修改正式 Skill。
- 覆盖场景：Hard Check 最终失败、Malformed Review JSON 超过重试、Quality Gate halt、Agent/Safety/Max attempts halt。
- 验证结果：`python -m pytest -q` 通过 14 个测试；`python -m orchestrator.interfaces.cli.main --task examples/task.shell-agent.json --real-checks` 成功生成 `.omx/runs/run-20260521-115833`。
- 下一步建议：补真实 Git diff 场景测试、扩展命令 allowlist，再评估接入 Codex/OMX Agent Adapter。

## 2026-05-21 第六批实现记录

- 当前阶段：第六批实现完成。
- 已完成产物：`tests/test_git_diff_integration.py` 真实临时 git 仓库集成测试；`DiffRiskService` 增加 `touches_forbidden_path` 强扣分。
- 覆盖场景：源码与测试同时变更、源码变更但测试未变更、大 diff 超 200 行、删除文件、命中 forbidden path、`refactor/config` 的测试覆盖扣分豁免。
- 验证结果：`python -m pytest -q` 通过 19 个测试；`python -m orchestrator.interfaces.cli.main --task examples/task.shell-agent.json --real-checks --git-diff` 成功生成 `.omx/runs/run-20260521-120408`。
- 下一步建议：进入第七批，增强命令 allowlist 策略，把命令安全从固定拦截升级为可配置允许策略。

## 2026-05-21 第七批实现记录

- 当前阶段：第七批实现完成。
- 已完成产物：`TaskConfig.allowed_command_prefixes`、`SafetyPolicy.validate_command(command, task)` allowlist 校验、`SafeCommandRunner` 传入 task 进行命令安全检查。
- 行为约束：危险命令模式仍优先阻断；随后检查命令是否匹配允许前缀；默认允许 `python/py/pytest/ruff/mypy/npm test/pnpm test` 等测试类命令；任务可通过 `allowed_command_prefixes` 扩展允许前缀。
- 覆盖场景：允许 `python -m pytest`、允许任务自定义 `git status`、拒绝未知命令、危险命令即使在 allowlist 中也被阻断、ShellCheckRunner 返回 allowlist 拒绝原因。
- 验证结果：`python -m pytest -q` 通过 24 个测试；`python -m orchestrator.interfaces.cli.main --task examples/task.shell-agent.json --real-checks --git-diff` 成功生成 `.omx/runs/run-20260521-120718`。
- 下一步建议：进入第八批，落地 Codex/OMX Agent Adapter 骨架，并把 prompt 构造从具体 agent 中抽离。

## 2026-05-21 第八批实现记录

- 当前阶段：第八批实现完成。
- 已完成产物：`AgentPromptBuilder`、`ExternalCommandAgent`、`CodexAgent`、`OmxAgent`、CLI `--agent codex|omx` 支持、`examples/task.codex-agent.json` dry-run 示例。
- 结构调整：ShellAgent 不再自行拼命令上下文，改为复用 `AgentPromptBuilder.render_command` 与 `write_reason_file`；Codex/OMX 适配器通过 `{prompt_file}`、`{task_id}`、`{run_dir}` 等占位符接入外部命令。
- 覆盖场景：prompt/命令上下文渲染、CodexAgent reviewer dry-run、OmxAgent 日志标识、ShellAgent 原有 reviewer/retry 行为保持。
- 验证结果：`python -m pytest -q` 通过 27 个测试；`python -m orchestrator.interfaces.cli.main --task examples/task.shell-agent.json --real-checks --git-diff` 成功生成 `.omx/runs/run-20260521-121217`；`python -m orchestrator.interfaces.cli.main --task examples/task.codex-agent.json --real-checks --git-diff` 成功生成 `.omx/runs/run-20260521-121251`。
- 下一步建议：进入第九批，补 requirements/design/plan/实现一致性 trace 审查，并决定 MVP 第一阶段是否收口。

## 2026-05-21 第九批 Trace 审查记录

- 当前阶段：第九批 trace 审查完成。
- 已完成产物：`docs/codex/v1/trace/自动循环进化编码智能体系统-mvp-trace.md`。
- 审查结论：MVP 第一阶段实现与 V7 架构、需求文档、MVP 计划总体一致；P0 主流程已闭环，P1/P2 中 heartbeat、状态持久化、候选规则也已具备基础能力。
- 主要缺口：真实 Codex/OMX Agent 协议、统一 phase logging、`quality_report.json` 文档/实现结构一致性、resume CLI、pending rule proposal 聚类与审批流。
- 验证结果：`python -m pytest -q` 通过 27 个测试。
- 下一步建议：优先做 phase logging 与 `quality_report.json` 文档/实现一致性收口，再进入真实 Agent 协议或 resume CLI。

## 2026-05-21 GAP-02 Phase Logging 收口记录

- 当前阶段：trace GAP-02 已补齐。
- 已完成产物：`PhaseLogger`、`logs/phase.log` 运行产物、phase logging 测试覆盖、微秒级 `run_id` 避免同秒运行目录碰撞。
- 覆盖场景：init/safety/code/hard_checks/review/quality_gate/fix/done/halt 的 start/end/retry/halt 事件；Shell 与 Codex dry-run CLI 均生成 phase 日志。
- 验证结果：`python -m pytest -q` 通过 28 个测试；Shell CLI 生成 `.omx/runs/run-20260521-122837-511924`；Codex dry-run CLI 生成 `.omx/runs/run-20260521-122837-536573`。
- 下一步建议：处理 GAP-03，统一 `quality_report.json` 文档示例与当前扁平实现结构。

## 2026-05-21 GAP-03 Quality Report 文档一致性收口记录

- 当前阶段：trace GAP-03 已补齐。
- 决策：`quality_report.json` 保持当前扁平结构；Hard Check 逐命令明细继续由同一 attempt 目录下的 `hard_checks.json` 承载。
- 已完成产物：更新 V7 设计中的 `quality_report.json` 示例；更新正式技术文档字段说明；更新 trace 与 status。
- 验证结果：`python -m pytest -q` 通过 28 个测试。
- 下一步建议：进入 GAP-04，补 pending rule proposal 的历史索引与重复问题聚类雏形，或进入 GAP-05 resume CLI。

## 2026-05-21 GAP-05 Resume CLI 收口记录

- 当前阶段：trace GAP-05 基础能力已补齐。
- 已完成产物：`FileStateRepository.load_state`、`FileStateRepository.task_path_for_run`、CLI `resume --run-id`、CLI `resume --run-id <id> --rerun`。
- 行为边界：`resume` 默认只读取既有 `run_state.json` 与 `task.json` 并输出恢复摘要；显式 `--rerun` 时基于原 `task.json` 新建 fresh run；暂不从半截 attempt 强行续跑。
- 兼容性：保留旧式 `python -m orchestrator.interfaces.cli.main --task ...`，新增 `run --task ...` 子命令。
- 验证结果：`python -m pytest -q` 通过 31 个测试；旧式 run、新式 run、resume inspect、resume rerun CLI 均通过。
- 下一步建议：进入 GAP-04，补 pending rule proposal 历史索引与重复问题聚类雏形。

## 2026-05-21 GAP-04 Rule Proposal 聚类收口记录

- 当前阶段：trace GAP-04 基础能力已补齐。
- 已完成产物：`RuleProposalIndex`、`RuleProposalCluster`、`RuleProposalIndexService`、`.omx/runs/rule_proposals_index.json` 历史索引。
- 行为边界：按 `source + reason` 生成稳定 `cluster_key`，统计 `observed_count`、`run_ids`、`task_ids`、first/last seen；只增强 pending proposal，不自动写正式 Skill。
- 验证结果：`python -m pytest -q` 通过 32 个测试；CLI hard check 失败场景生成 `.omx/runs/rule_proposals_index.json` 与带聚类字段的 `pending-rules/RP-001.md`。
- 下一步建议：补 Rule Proposal 人工审批状态流，或回到真实 Codex/OMX Agent 协议定义。

## 2026-05-21 Rule Proposal 审批状态流记录

- 当前阶段：Rule Proposal 人工审批状态流完成。
- 已完成产物：CLI `rules list`、CLI `rules review --cluster-key ... --status pending|approved|rejected`、索引字段 `reviewed_by/reviewed_at/review_note`。
- 行为边界：审批动作只更新 `.omx/runs/rule_proposals_index.json` 中的聚类状态，不自动写正式 Skill，不自动修改 proposal markdown 历史文件。
- 验证结果：`python -m pytest -q` 通过 33 个测试；CLI `rules list` 与 `rules review` 均通过。
- 下一步建议：进入真实 Codex/OMX Agent 协议定义，明确真实 CLI 命令模板、prompt 输入、退出码和 stdout/stderr 契约。

## 2026-05-21 GAP-01 Agent CLI 协议收口记录

- 当前阶段：真实 Codex/OMX Agent CLI 基础协议已固化。
- 已完成产物：`docs/codex/v1/designs/自动循环进化编码智能体系统-agent-protocol.md`、`examples/task.codex-real-template.json`、`examples/task.omx-real-template.json`。
- 协议范围：定义 Coder/Fixer/Reviewer 的命令模板、`{prompt_file}`/`{reason_file}`/`{run_dir}` 等占位符、prompt 文件路径、Reviewer stdout JSON、stderr 诊断、非 0 退出码和 allowlist 安全要求。
- 测试覆盖：新增 Codex external adapter 契约测试，覆盖 Coder prompt 写入、Fixer reason file 传递、Reviewer 非 0 退出码 halt 记录。
- 验证结果：`python -m pytest -q` 通过 36 个测试；`python -m orchestrator.interfaces.cli.main --task examples/task.codex-agent.json --real-checks --git-diff` 成功生成 `.omx/runs/run-20260521-151406-853011`。
- 剩余边界：尚未调用真实 Codex/OMX 二进制执行写操作；下一步需要基于本机 CLI 参数写包装脚本并在受控样例仓库验证。

## 2026-05-21 Agent Wrapper 验证记录

- 当前阶段：真实 Agent 稳定包装入口已落地。
- 本机探测：能找到 `codex.ps1`；未找到 `omx` 命令。
- 已完成产物：`scripts/run_external_agent.py`、`examples/task.codex-wrapper-dry-run.json`、`tests/test_external_agent_wrapper.py`。
- 行为边界：包装脚本支持 `--dry-run`，也支持 `--backend-command` 或 `OMX_{RUNTIME}_{ROLE}_COMMAND` 环境变量转发到真实后端命令；dry-run reviewer 会输出合法 review JSON。
- 验证结果：`python -m pytest -q` 通过 39 个测试；`python -m orchestrator.interfaces.cli.main --task examples/task.codex-wrapper-dry-run.json --real-checks --git-diff` 成功生成 `.omx/runs/run-20260521-152114-595301`。
- 下一步建议：基于本机 Codex CLI 实际参数配置 `OMX_CODEX_*_COMMAND`，在临时样例仓库执行一次真实 Coder 写操作。

## 2026-05-21 OMX Setup 与 stdin wrapper 记录

- 当前阶段：OMX 环境初始化完成，wrapper 已支持真实 `omx exec` 所需的 stdin prompt 模式。
- OMX setup：已执行 `omx setup --scope user --merge-agents`，保留用户级 AGENTS 并合并 OMX 管理段。
- Doctor 结果：`omx doctor` 为 15 passed、1 warning、0 failed；剩余 warning 为 Windows explore harness 限制，不影响 `omx exec`。
- 已完成产物：`scripts/run_external_agent.py` 新增 `--stdin-prompt`、`--output-last-message` 和 `{output_last_message}` 占位符；`examples/task.omx-real-template.json` 改为通过 wrapper 接入 `omx exec` stdin 模式。
- 测试覆盖：`tests/test_external_agent_wrapper.py` 增加 stdin prompt 传递和 output-last-message 回收测试。
- 验证结果：`python -m pytest -q` 通过 41 个测试；`python -m orchestrator.interfaces.cli.main --task examples/task.codex-wrapper-dry-run.json --real-checks --git-diff` 成功生成 `.omx/runs/run-20260521-160615-212899`。
- 下一步建议：在 `.tmp/omx-real-smoke/` 临时样例仓库中配置 `OMX_OMX_CODER_COMMAND` / `OMX_OMX_REVIEWER_COMMAND`，执行一次真实 OMX 写操作验证。

## 2026-05-21 真实 OMX Smoke 验证记录

- 当前阶段：受控真实 OMX 调用链路已验证，真实写操作被当前 Windows 执行环境阻断。
- Smoke 工作区：`.tmp/omx-real-smoke/`，包含 `calculator.py` 和 `test_calculator.py`，初始状态为 `add(1, 2)` 测试失败。
- Smoke 任务：`examples/task.omx-real-smoke.json`。
- 后端命令：`OMX_OMX_CODER_COMMAND` / `OMX_OMX_FIXER_COMMAND` 使用 `omx exec --full-auto --skip-git-repo-check -C <worktree> -`；Reviewer 使用 `examples/omx_smoke_reviewer.py` 输出合法 JSON。
- 暴露并修复的问题：
  - `TaskLoader` 改为 `utf-8-sig`，兼容 PowerShell UTF-8 BOM JSON。
  - `AgentPromptBuilder.render_command` 将 `task_json/run_dir/prompt_file/reason_file` 渲染为绝对路径，避免跨 worktree 调用找不到 `.omx` 产物。
  - `run_external_agent.py` 后端输出读取增加 `encoding='utf-8', errors='replace'`，避免非 UTF-8 输出导致 wrapper 读线程异常。
- 验证结果：`python -m pytest -q` 通过 44 个测试。
- 真实 smoke 结果：`run-20260521-161405-444000` 最终 `status=halted phase=hard_checks attempt=2/2`，原因是 `test failed`。
- 根因：真实 `omx exec` 成功启动并返回，但内部 Codex 在当前 Windows 环境中无法启动 shell/patch 子进程，日志显示 `windows sandbox: CreateProcessWithLogonW failed: 1385`，因此没有实际修改 `calculator.py`。
- 下一步建议：优先在 WSL/Linux 环境复测真实写操作，或为 Windows 配置可用的 Codex/OMX 执行策略；另一条路线是让模型只输出 patch，由 Orchestrator 受控应用 patch。

## 2026-05-21 Windows 兼容 Patch 模式记录

- 当前阶段：优先级 1 已完成第一版，即“模型输出 patch JSON，Orchestrator 校验并应用 patch”。
- 已完成产物：
  - `orchestrator/domain/models/patch_plan.py`
  - `orchestrator/domain/services/patch_validator.py`
  - `orchestrator/infrastructure/patches/patch_applier.py`
  - `orchestrator/infrastructure/agents/omx_patch_agent.py`
  - `examples/patch_smoke_backend.py`
  - `examples/task.omx-patch-smoke.json`
  - `tests/test_patch_agent.py`
- 行为边界：当前 patch schema 第一版仅支持 `replace_text`；目标路径必须通过 `SafetyPolicy.validate_write_path`，且 `task_id` 必须匹配。
- CLI 接入：新增 `--agent omx_patch` 和 `agent_mode=omx_patch`。
- Smoke 结果：`python -m orchestrator.interfaces.cli.main --task examples/task.omx-patch-smoke.json --agent omx_patch --real-checks` 成功，run_id 为 `run-20260521-162852-762772`，状态 `done`。
- 验证结果：`.tmp/omx-real-smoke/calculator.py` 从 `return a - b` 被受控替换为 `return a + b`；`python -m pytest -q` 通过 47 个测试。
- 下一步建议：把 patch 后端从 `examples/patch_smoke_backend.py` 替换为真实 `omx exec` patch-only prompt，要求模型只返回 patch JSON，不直接执行 shell/patch。

## 2026-05-21 真实 OMX Patch-only 后端记录

- 当前阶段：真实 `omx exec` patch-only 后端已跑通。
- 已完成产物：
  - `AgentPromptBuilder` patch prompt 注入 `allowed_paths` 文件快照。
  - `AgentPromptBuilder.render_command` 新增 `{attempt_dir}` 占位符。
  - `examples/task.omx-patch-real-smoke.json`。
- 后端命令：
  - `OMX_OMX_CODER_COMMAND=omx exec --full-auto --skip-git-repo-check -C "<worktree>" - --output-last-message {output_last_message}`
  - `OMX_OMX_FIXER_COMMAND=omx exec --full-auto --skip-git-repo-check -C "<worktree>" - --output-last-message {output_last_message}`
- 验证结果：
  - 第一次真实 patch-only smoke：`run-20260521-163226-234789` 到 `done`，但 `--output-last-message` 目录使用 `{attempt}` 导致写入失败，stdout 回退仍可解析。
  - 修正为 `{attempt_dir}` 后复测：`run-20260521-163411-124400` 到 `done`，last-message 文件成功写入 `attempts/001/omx_patch_coder_last_message.txt`。
  - `.tmp/omx-real-smoke/calculator.py` 被真实 OMX 生成的 patch JSON 受控修改为 `return a + b`。
  - `python -m pytest -q` 通过 48 个测试。
- 下一步建议：扩展 patch schema，支持 `create_file`、`delete_file` 或 unified diff；同时增加 patch 风险评分和人工审批开关。

## 2026-05-21 Patch Schema 扩展记录

- 当前阶段：patch schema 第二版完成。
- 已完成能力：
  - `replace_text`：替换已有文件中的精确文本。
  - `create_file`：创建新文件，默认不覆盖已有文件。
  - `delete_file`：删除文件，默认目标必须存在。
- 风险字段：`PatchApplyResult` 返回 `changed_files/created_files/deleted_files/risk_score/risk_reasons`，并写入 `logs/agent.log`。
- 风险规则：初始 10 分；修改文件数超过 5 扣分；删除文件每个扣 2 分；创建文件超过 2 个后扣分。
- 验证结果：
  - `tests/test_patch_agent.py` 覆盖 create/delete/forbidden path。
  - 本地 patch smoke `run-20260521-164448-058586` 到 `done`。
  - 真实 OMX patch-only smoke `run-20260521-164502-235168` 到 `done`，agent log 记录 `risk_score=10`。
  - `python -m pytest -q` 通过 50 个测试。
- 下一步建议：增加人工审批开关，例如当 `risk_score < threshold`、包含 `delete_file` 或触及高风险路径时，Orchestrator 只生成待审批 patch，不自动应用。

## 2026-05-21 Patch 人工审批开关记录

- 当前阶段：patch 自动应用与待审批分流已完成第一版。
- 新增配置：
  - `patch_auto_apply`
  - `patch_approval_risk_threshold`
  - `patch_require_approval_on_delete`
- 新增产物：
  - `orchestrator/infrastructure/patches/patch_approval.py`
  - `examples/patch_delete_backend.py`
  - `examples/task.omx-patch-approval-smoke.json`
- 行为规则：
  - 关闭自动应用时，所有 patch 写入 `pending-patches`。
  - `risk_score` 低于阈值时写入 `pending-patches`。
  - 包含 `delete_file` 且开启 delete 审批时写入 `pending-patches`。
- Smoke 结果：`run-20260521-165047-273285` halted，原因是 patch requires approval；生成 `.omx/runs/run-20260521-165047-273285/pending-patches/001-patch_coder.json`；`.tmp/omx-real-smoke/old_file.py` 未被删除。
- 回归验证：低风险 patch smoke `run-20260521-165119-985078` 仍自动应用并 done；`python -m pytest -q` 通过 52 个测试。
- 下一步建议：新增 `patches list/apply/reject` CLI，支持人工审批后应用 pending patch。

## 2026-05-21 Pending Patch CLI 记录

- 当前阶段：pending patch 人工审批 CLI 已完成。
- 已完成产物：
  - `orchestrator/infrastructure/patches/pending_patch_service.py`
  - CLI `patches list`
  - CLI `patches apply`
  - CLI `patches reject`
- 行为边界：
  - `list` 可按 run_id 查看 pending/applied/rejected patch。
  - `apply` 会重新加载 run 快照中的 `task.json`，再次通过 `PatchApplier` 做路径安全校验和应用。
  - `reject` 只改 patch 状态，不修改工作区文件。
- Smoke 验证：
  - 生成审批 patch：`run-20260521-170009-452873`。
  - `patches list --run-id run-20260521-170009-452873` 显示 `status=pending risk_score=8 ops=delete_file files=old_file.py`。
  - `patches apply --run-id run-20260521-170009-452873 --patch 001-patch_coder.json` 后状态为 `applied`，`.tmp/omx-real-smoke/old_file.py` 被删除。
- 测试结果：`python -m pytest -q` 通过 53 个测试。
- 下一步建议：补 `patches apply --rerun-checks`，审批应用后自动重跑 hard checks；或者补统一 diff 支持。

## 2026-05-21 Pending Patch 审批后验证记录

- 当前阶段：`patches apply --rerun-checks` 已完成。
- 行为：审批应用 patch 后，重新加载 run 快照中的 `task.json`，执行 `ShellCheckRunner.run_all(task)`，并把结果写入 pending patch JSON 的 `post_apply_checks` 字段。
- CLI 输出：`checks_passed=True/False`。
- 测试覆盖：`tests/test_cli_resume.py` 覆盖 apply 后真实检查命令通过，并断言 `post_apply_checks.commands[0].passed is True`。
- Smoke 验证：`run-20260521-170424-438800` 执行 `patches apply --rerun-checks` 后状态为 `applied`，CLI 输出 `checks_passed=True`。
- 测试结果：`python -m pytest -q` 通过 53 个测试。
- 下一步建议：进入 unified diff 支持，或补 `patches apply --rerun-task` 让审批后重新跑完整 review/quality gate。
# 2026-05-21 Patch Unified Diff 与 rerun-task 记录

- 当前阶段：Patch-only 审批与验证链路继续增强完成。
- 已完成产物：
  - `UnifiedDiffOperation` 与 `PatchOperation` schema 扩展。
  - `PatchApplier` 支持单文件 unified diff hunk 解析、上下文校验、dry-run 与受控应用。
  - Patch prompt schema 已提示模型可输出 `unified_diff`。
  - 新增 `ValidateAppliedPatchUseCase`，用于 `patches apply --rerun-task` 的补丁应用后验证闭环。
  - CLI `patches apply --rerun-task` 不再重新调用 coder/fixer，而是新建 post-apply validation run，执行 hard checks、Reviewer、Quality Gate，并写回 `post_apply_rerun`。
- 行为边界：
  - unified diff 当前只支持单文件 hunk，多文件 diff 需拆成多个 operation。
  - `--rerun-task` 会先应用 pending patch，再验证 patched worktree；它不是重新生成 patch 的入口。
  - hard checks 不通过时 post-apply validation 直接 halt，不浪费 reviewer token。
- 测试结果：
  - `python -m pytest -q tests/test_patch_agent.py` 通过，10 passed。
  - `python -m pytest -q tests/test_cli_resume.py` 通过，6 passed。
  - `python -m pytest -q` 通过，57 passed。
- 下一步建议：继续补真实 OMX 端到端 patch JSON/unified diff 样例，或增强 `patches list` 对 post-apply validation 结果的展示字段。

# 2026-05-21 第三步规划记录

- 当前阶段：第三步实施计划已落文档。
- 计划文档：`docs/codex/v1/plans/自动循环进化编码智能体系统-third-step-plan.md`。
- 第三步定义：真实 OMX/Codex patch-only unified diff 端到端验收 + pending patch 审计展示增强 + 失败诊断补齐。
- 建议优先级：
  1. 增强 `patches list` 输出，让 applied patch 能直接看到 `checks_passed/rerun_status/rerun_run_id`。
  2. 新增 unified diff smoke task 和可控 backend。
  3. 补 malformed patch JSON、context mismatch、rerun hard-check failed 的诊断产物。
  4. 同步 agent-protocol/status/task-control 并执行全量回归。
- 下一步恢复提示：从计划文档“实施步骤”第 1 项或“建议执行顺序”第 1 项开始实现；优先建议先做 `patches list` 审计展示增强。

# 2026-05-21 第三步 patches list 审计展示增强记录

- 当前阶段：第三步第 1 项已完成。
- 已完成产物：
  - `PendingPatchService._summary` 新增 `checks_status` 三态字段：`not_run`、`passed`、`failed`。
  - CLI `_print_patch_summary` 新增展示 `checks_status/rerun_phase/rerun_attempt`，并继续保留 `checks_passed/rerun_status/rerun_run_id`。
  - `tests/test_cli_resume.py` 覆盖 pending、`--rerun-task`、`--rerun-checks` 后的 list 展示。
- 验证：
  - `python -m pytest -q tests/test_cli_resume.py` 通过，6 passed。
  - `python -m pytest -q tests/test_patch_agent.py` 通过，10 passed。
- 下一步恢复提示：继续第三步第 2 项，新增 unified diff smoke task 与可控 backend。

# 2026-05-21 第三步 unified diff smoke 记录

- 当前阶段：第三步第 2 项已完成。
- 已完成产物：
  - `examples/patch_unified_diff_backend.py`：输出 `unified_diff` patch JSON。
  - `examples/task.omx-patch-unified-diff-smoke.json`：可执行 smoke task。
  - `.tmp/omx-unified-diff-smoke/`：独立 smoke 工作区，初始 `calculator.add` 故意失败。
  - `tests/test_cli_resume.py::test_omx_patch_unified_diff_smoke`：自动化验证 unified diff patch-only 链路。
  - `tests/test_patch_agent.py::test_patch_applier_unified_diff_rejects_missing_hunk`：防止没有 hunk 的 diff 被静默视为成功。
- 发现与修正：
  - 测试 helper 首次误用了字面量 `\\n`，导致 diff 没有真实 hunk；已修正为真实换行。
  - `PatchApplier` 增加 `hunk_count == 0` 拒绝逻辑。
  - 手工 smoke 中 PowerShell `Set-Content -Encoding utf8` 写入 BOM，触发 context mismatch；已确认这是有效保护，不是补丁逻辑失败。
- 验证：
  - `python -m pytest -q tests/test_cli_resume.py::test_omx_patch_unified_diff_smoke tests/test_patch_agent.py` 通过，12 passed。
  - `python -m orchestrator.interfaces.cli.main --task examples/task.omx-patch-unified-diff-smoke.json --agent omx_patch --real-checks` 通过，run_id=`run-20260521-173445-649699`，status=`done`。
- 下一步恢复提示：继续第三步第 3 项，补 malformed patch JSON、context mismatch、rerun hard-check failed 的诊断产物。

# 2026-05-21 第三步失败诊断产物记录

- 当前阶段：第三步第 3 项已完成。
- 已完成产物：
  - `OmxPatchAgent` 在 patch-only 输出失败时写入 `{role}_patch_raw_output.txt`。
  - `OmxPatchAgent` 在 malformed patch JSON、context mismatch、approval required 等异常时写入 `{role}_patch_diagnostics.json`。
  - `ValidateAppliedPatchUseCase` 将 post-apply validation 原因写入 `state.artifacts["validation_reason"]`。
  - `PendingPatchService.record_rerun_task` 将原因写回 pending patch JSON 的 `post_apply_rerun.reason`。
  - CLI `patches list/apply` 输出 `rerun_reason=...`。
- 测试覆盖：
  - malformed patch JSON 会保存 raw output 和 diagnostics。
  - `patches apply --rerun-task` 在 hard check 失败时回写 `test failed`。
  - 原有 context mismatch 与 no-hunk unified diff 拒绝继续由 `tests/test_patch_agent.py` 覆盖。
- 验证：
  - `python -m pytest -q tests/test_cli_resume.py tests/test_patch_agent.py` 通过，20 passed。
  - `python -m pytest -q tests/test_cli_resume.py::test_omx_patch_malformed_json_writes_diagnostics tests/test_cli_resume.py::test_patches_apply_rerun_task_records_failure_reason` 通过，2 passed。
- 下一步恢复提示：继续第三步第 4 项，补演示命令脚本/文档，并做全量回归与 trace 收口。

# 2026-05-21 第三步演示脚本记录

- 当前阶段：第三步第 4 项已完成。
- 已完成产物：
  - `scripts/run_patch_demo.py`：一键演示 unified diff patch-only smoke、pending patch list、审批 apply、`--rerun-task`。
  - `docs/codex/v1/plans/自动循环进化编码智能体系统-demo-script.md`：对外演示命令和讲解词。
- 演示结果：
  - `python scripts/run_patch_demo.py` 执行成功。
  - unified diff smoke：run_id=`run-20260521-174136-200457`，status=`done`。
  - pending patch approval：run_id=`run-20260521-174138-333591`，初始 `halted phase=code`，`patches list` 显示 `status=pending risk_score=8`。
  - 审批应用后：`rerun_status=done`，`rerun_run_id=run-20260521-174139-595059`，`rerun_reason=quality gate passed`。
- 下一步恢复提示：执行全量回归并补一版 trace 收口；第三步主体功能已完成。

# 2026-05-21 第三步 Trace 收口记录

- 当前阶段：第三步 trace 审查完成。
- 已完成产物：`docs/codex/v1/trace/自动循环进化编码智能体系统-third-step-trace.md`。
- 审查结论：
  - unified diff patch JSON 已闭环。
  - `patches list` 审计展示已闭环。
  - 失败诊断产物已闭环。
  - 演示脚本与演示文档已闭环。
- 剩余建议：真实 OMX/Codex unified diff smoke 可作为后续环境依赖型增强，不阻塞第三步收口。
- 验证基线：`python -m pytest -q` 当前为 61 passed；`python scripts/run_patch_demo.py` 已通过。
- 下一步恢复提示：进入下一阶段规划，建议优先做真实 OMX/Codex unified diff smoke 模板，或转入更高层的自动循环策略增强。

# 2026-05-21 真实 Unified Diff Smoke 模板记录

- 当前阶段：第三步后续增强项已补齐模板。
- 已完成产物：
  - `examples/task.omx-patch-unified-diff-real-smoke.json`
  - `examples/task.codex-patch-unified-diff-real-smoke.json`
  - `docs/codex/v1/plans/自动循环进化编码智能体系统-real-unified-diff-smoke.md`
- 行为边界：
  - 两个模板都使用 `agent_mode=omx_patch`，真实 OMX/Codex 只负责输出 patch JSON，不直接改文件。
  - 模板依赖环境变量 `OMX_OMX_CODER_COMMAND` / `OMX_OMX_FIXER_COMMAND` 或 `OMX_CODEX_CODER_COMMAND` / `OMX_CODEX_FIXER_COMMAND`。
  - 该验证项属于环境依赖型 smoke，不纳入默认 pytest，不影响第三步收口。
- 验证：
  - 两个 task 模板已通过 `TaskLoader` 读取验证。
  - `python -m pytest -q` 通过，61 passed。
- 下一步恢复提示：若用户要真实跑 smoke，先按 real-unified-diff-smoke 文档配置环境变量，再执行对应 task。

# 2026-05-21 Web UI MVP 记录

- 当前阶段：本地输入界面 MVP 已完成。
- 已完成产物：
  - `orchestrator/interfaces/web/main.py`
  - `orchestrator/interfaces/web/templates/index.html`
  - `orchestrator/interfaces/web/templates/run_detail.html`
  - `orchestrator/interfaces/web/static/styles.css`
  - `tests/test_web_ui.py`
  - `docs/codex/v1/plans/自动循环进化编码智能体系统-web-ui-mvp.md`
- 已完成能力：新建任务输入、示例任务运行、最近 runs 展示、run 详情展示、pending patch approve/reject、approve 后 rerun-task。
- 使用方式：`python -m orchestrator.interfaces.web.main`，默认访问 `http://127.0.0.1:8765`。
- 验证结果：`python -m pytest -q` 通过，当前为 63 passed。
- 后续建议：如进入产品化，可补鉴权、WebSocket/轮询运行进度、任务模板管理和更细粒度的 patch diff 可视化。

# 2026-05-22 Web UI 真实主线调整记录

- 当前决策：后续默认使用 OMX 编排智能体，并由 OMX 内部调用 Codex 执行。
- 调用链路：`Orchestrator -> run_external_agent.py --runtime omx -> omx exec -> codex exec -> patch JSON -> Orchestrator`。
- 已完成调整：
  - 首页说明改为“OMX 编排智能体，Codex 执行生成补丁”。
  - 新建任务默认 `Agent=omx_patch`，不再默认 mock。
  - Patch coder/fixer 默认命令改为 wrapper 调 `omx exec`。
  - 页面建议用户优先运行真实示例，再填写自己的任务。
- 本机确认：
  - `omx exec --help` 显示入口为 `codex exec`。
  - `omx doctor` 显示 Codex CLI installed，结果 15 passed、1 warning、0 failed。
- 验证结果：`python -m pytest -q` 通过，当前为 63 passed。
# 2026-05-22 Web UI 异步任务入库记录

- 当前阶段：下一阶段优先项“异步任务与运行状态入库”已完成。
- 已完成能力：
  - 新增 `SQLiteJobRepository`，使用 Python 标准库 SQLite，不引入额外依赖。
  - Web 提交任务后立即写入 `.omx/orchestrator.db` 的 `web_jobs` 表，记录 `running/failed/done`、`task_path`、`run_id`、开始和完成时间。
  - 后台线程完成 Orchestrator run 后更新数据库；`/jobs/{job_id}` 读取数据库状态，`done + run_id` 时跳转 `/runs/{run_id}`。
  - 首页新增“最近 Jobs”，用于恢复或查看仍在运行的异步任务。
  - 修复 Web 首页、任务状态页、运行详情页和测试断言中的乱码文本。
- 行为边界：
  - 当前仍使用后台线程执行任务；入库解决页面刷新/重启后状态可查的问题，不等同于独立任务队列。
  - `.omx/orchestrator.db` 是运行态数据库，不应手工编辑。
- 验证结果：
  - `python -m pytest -q` 通过，当前为 `66 passed`。
- 下一步恢复提示：
  - 继续按 next-step-plan 推进真实项目接入表单校验，然后做 Patch Diff 可视化审批。

# 2026-05-22 Web UI 表单校验记录

- 当前阶段：真实项目接入表单校验已完成。
- 已完成能力：
  - 首页任务提交前校验 Task ID 只能包含字母、数字、下划线和短横线。
  - 校验 `change_type`、`agent_mode` 必须属于受支持枚举。
  - 校验非默认 worktree 必须存在且为目录。
  - 校验 `allowed_paths` 至少一个，且只能是 worktree 内相对路径，拒绝绝对路径和 `..` 逃逸。
  - 启用真实检查时必须填写 `Test command`。
  - 对 Test command、Patch coder/fixer、Reviewer 做基础命令解析和高风险命令拦截。
  - 校验失败时返回 `422` 并在首页展示错误列表，不创建后台 Job 记录。
- 额外修复：
  - Web 首页、任务状态页、运行详情页乱码文本恢复为可读中文。
- 验证结果：
  - `python -m pytest -q` 通过，当前为 `68 passed`。
- 下一步恢复提示：
  - 建议进入 Patch Diff 可视化审批：在 run 详情页展示 pending patch 的操作、目标文件、风险原因和 diff/内容预览。

# 2026-05-22 Patch Diff 可视化审批记录

- 当前阶段：Patch Diff 可视化审批已完成。
- 已完成能力：
  - `PendingPatchService.list()` 返回 `summary`、`risk_reasons`、结构化 `operations` 预览。
  - `replace_text` 预览显示 old/new 对照。
  - `create_file` 预览显示新文件内容。
  - `delete_file` 预览显示删除意图。
  - `unified_diff` 预览显示 diff 内容。
  - 长预览自动截断，避免页面过长。
  - run 详情页补丁审批区展示风险原因、摘要、操作类型、目标文件和预览。
- 验证结果：
  - `python -m pytest -q tests/test_patch_agent.py tests/test_web_ui.py` 通过，`19 passed`。
  - `python -m pytest -q` 通过，当前为 `69 passed`。
- 下一步恢复提示：
  - 建议做真实项目回归 Smoke：创建独立临时 worktree，通过 Web 提交任务，观察 DB job、run detail、patch preview、审批和 rerun-task 是否完整闭环。

# 2026-05-22 真实项目回归 Smoke 记录

- 当前阶段：真实项目回归 Smoke 已完成。
- 已完成能力：
  - 新增 `scripts/run_real_project_smoke.py`，自动创建 `.tmp/real-project-smoke` 独立临时项目。
  - 生成任务配置 `.tmp/real-project-smoke-task.json`，强制 `patch_auto_apply=false`，确保进入 pending patch 审批路径。
  - 初始 run 验证 `status=halted phase=code` 且产生 pending patch。
  - 通过 `PendingPatchService.list()` 验证 patch preview 包含 `return a + b`。
  - 使用 CLI `patches apply --rerun-task` 审批、应用并重新执行 hard checks/review/quality gate。
  - 验证临时项目 `python -m pytest -q` 通过。
  - 新增 `tests/test_real_project_smoke.py` 纳入自动回归。
- 验证结果：
  - `python scripts/run_real_project_smoke.py` 通过。
  - `python -m pytest -q tests/test_real_project_smoke.py` 通过，`1 passed`。
  - `python -m pytest -q` 通过，当前为 `70 passed`。
- 下一步恢复提示：
  - 可进入 OMX team 编排模式：先设计 task/control 层如何表达 multi-agent stages，再接真实执行。

# 2026-05-22 OMX Team Protocol 设计契约记录

- 当前阶段：OMX team 编排模式第一步完成，先固化协议和示例，不改真实执行链路。
- 已完成产物：
  - `docs/codex/v1/designs/自动循环进化编码智能体系统-team-protocol.md`
  - `examples/team_task.omx-team-patch.json`
  - `examples/team_result.omx-team-patch.json`
  - `tests/test_team_protocol_examples.py`
- 关键决策：
  - Orchestrator 继续作为最终权威，负责 task state、权限、安全校验、patch 应用、人工审批、hard checks、review retry 和 Quality Gate。
  - OMX team 在 MVP 阶段只产出结构化 artifacts：`team_plan.json`、`patch_plan.json`、`review.json`、diagnostics。
  - Team 不直接修改真实 worktree；真实写入必须走 Orchestrator 的 PatchValidator / PatchApplier / PendingPatchService。
- 验证结果：
  - `python -m pytest -q tests/test_team_protocol_examples.py` 通过，`2 passed`。
  - `python -m pytest -q` 全量通过，当前为 `72 passed`。
- 下一步恢复提示：
  - 实现 `agent_mode=omx_team_patch`。
  - 新增 Team agent adapter：调用 OMX team，回收 `team_result.json`，解析其中 `artifacts.patch_plan` 与 `artifacts.review`。
  - 复用现有 `PatchValidator`、`ReviewValidator`、`PendingPatchService` 和 `patches apply --rerun-task`，避免重复实现安全与门禁逻辑。

# 2026-05-22 OMX Team Patch 最小执行链路记录

- 当前阶段：OMX team 编排模式第二步完成，已从协议契约推进到最小代码执行链路。
- 已完成产物：
  - `orchestrator/infrastructure/agents/omx_team_patch_agent.py`
  - `examples/team_patch_backend.py`
  - `examples/task.omx-team-patch-smoke.json`
  - `tests/test_omx_team_patch_agent.py`
  - `orchestrator/domain/enums.py`
  - `orchestrator/interfaces/cli/main.py`
- 关键行为：
  - CLI 支持 `--agent omx_team_patch`。
  - `AgentMode` 支持 `omx_team_patch`。
  - `OmxTeamPatchAgent.run_coder` 调用 team 后端，解析 `team_result.json`。
  - `artifacts.patch_plan` 复用现有 patch 校验、dry-run、审批策略和应用器。
  - `artifacts.review` 缓存在当前 run，review phase 直接复用，不额外调用 reviewer。
  - malformed team result 会写入 `team_result_raw_output.txt` 和 `team_diagnostics.json`。
- 验证结果：
  - `python -m pytest -q tests/test_omx_team_patch_agent.py` 通过，`2 passed`。
  - `python -m pytest -q tests/test_omx_team_patch_agent.py tests/test_team_protocol_examples.py tests/test_patch_agent.py tests/test_external_agent.py tests/test_cli_resume.py` 通过，`33 passed`。
  - `python -m orchestrator.interfaces.cli.main --task examples/task.omx-team-patch-smoke.json --agent omx_team_patch --real-checks` 通过，run_id=`run-20260522-163446-036926`，status=`done`。
  - `python -m pytest -q` 全量通过，当前为 `74 passed`。
- 下一步恢复提示：
  - 接入 Web UI：表单允许 `agent_mode=omx_team_patch`，后端校验允许该枚举。
  - run detail 展示 `team_result.json` 和 `team_diagnostics.json` 路径/摘要。
  - 后续再把 `examples/team_patch_backend.py` 替换为真实 `omx team` 或 `omx pipeline/team` 后端命令。

# 2026-05-22 Web UI 接入 OMX Team Patch 记录

- 当前阶段：OMX team 编排模式第三步完成，Web UI 已接入最小 Team Patch 链路。
- 已完成产物：
  - `orchestrator/interfaces/web/main.py`
  - `orchestrator/interfaces/web/templates/index.html`
  - `orchestrator/interfaces/web/templates/run_detail.html`
  - `tests/test_web_ui.py`
- 关键行为：
  - `ALLOWED_AGENT_MODES` 增加 `omx_team_patch`。
  - 首页 Agent 下拉加入 `omx_team_patch`，示例运行默认 Agent 改为 `omx_team_patch`。
  - run detail 读取并展示最新 `attempts/*/team_result.json` 与 `attempts/*/team_diagnostics.json`。
  - Web 测试改用稳定英文/结构断言，避免历史乱码文本导致脆弱失败。
- 验证结果：
  - `python -m pytest -q tests/test_web_ui.py` 通过，`9 passed`。
  - `python -m pytest -q tests/test_web_ui.py tests/test_omx_team_patch_agent.py tests/test_team_protocol_examples.py` 通过，`13 passed`。
  - `python -m pytest -q` 全量通过，当前为 `76 passed`。
  - `python -m orchestrator.interfaces.cli.main --task examples/task.omx-team-patch-smoke.json --agent omx_team_patch --real-checks` 通过，run_id=`run-20260522-170355-050572`，status=`done`。
- 下一步恢复提示：
  - 启动 `python -m orchestrator.interfaces.web.main`。
  - 浏览器打开 `http://127.0.0.1:8765`，用示例运行 `examples/task.omx-team-patch-smoke.json` 或新建任务选择 `omx_team_patch`。
  - 验证 job 页面跳转 run detail 后能看到 Team Result。

# 2026-05-22 Web UI 乱码修复记录

- 当前阶段：Web UI 可用性修复完成。
- 问题：浏览器首页出现历史中文乱码，影响用户理解和操作。
- 处理：
  - 重写 `orchestrator/interfaces/web/templates/index.html`
  - 重写 `orchestrator/interfaces/web/templates/job_status.html`
  - 重写 `orchestrator/interfaces/web/templates/run_detail.html`
  - 重写 `orchestrator/interfaces/web/main.py` 的默认表单、校验错误、Job 状态和 run summary 文案。
- 验证：
  - `python -m pytest -q tests/test_web_ui.py` 通过，`9 passed`。
  - `python -m pytest -q` 全量通过，`76 passed`。
  - 重启 Web 服务后访问 `http://127.0.0.1:8765/`，返回 `status=200`，包含“新建任务”和 `omx_team_patch`，不包含典型乱码 `锛`。
- 恢复提示：下一步可直接让用户刷新浏览器，使用 `omx_team_patch` 提交任务；若仍看到旧页面，强制刷新浏览器缓存。

# 2026-05-22 Web UI Team Patch 闭环验证记录

- 当前阶段：Web 侧 OMX Team Patch 闭环验证完成。
- 本次处理：
  - 重新写入 `orchestrator/interfaces/web/main.py` 的中文默认表单、校验错误、Job 状态和 Run Summary 文案。
  - 重新写入 `orchestrator/interfaces/web/templates/index.html`、`job_status.html`、`run_detail.html`，恢复干净 UTF-8 中文。
  - 新增 `tests/test_web_ui.py::test_web_omx_team_patch_job_runs_to_detail`，覆盖 Web 表单提交 `omx_team_patch`、SQLite Job 完成、worktree 文件被修复、Run Detail 展示 Team Result。
- 验证：
  - `python -m py_compile orchestrator/interfaces/web/main.py` 通过。
  - `python -m pytest -q tests/test_web_ui.py` 通过，当前为 `10 passed`。
  - `python -m pytest -q` 通过，当前为 `77 passed`。
  - 已重启本地 Web 服务，`http://127.0.0.1:8765/` 返回 `200`，包含“新建任务”和 `omx_team_patch`，不包含典型乱码标记。
- 下一步建议：
  - 用户可直接打开 `http://127.0.0.1:8765/` 提交默认 `omx_team_patch` 示例任务。
  - 后续增强可进入真实 OMX team 后端替换：把当前 `examples/team_patch_backend.py` 示例后端替换为真实 `omx team` / `omx pipeline` 调用。

# 2026-05-23 真实 OMX/Codex Team Patch 后端记录

- 当前阶段：真实 OMX/Codex 非交互 team_result 后端已接入。
- 本次处理：
  - 新增 `scripts/run_omx_team_patch.py`，默认通过 `omx exec --output-last-message ... -` 调用 Codex，要求只返回合法 `team_result.json`。
  - 新增 `examples/task.omx-team-real-template.json`，作为真实 OMX Team Patch 模板。
  - 新增 `scripts/run_omx_team_real_smoke.py`，用于环境依赖型真实 smoke。
  - 新增 `tests/test_omx_team_patch_backend_script.py`，覆盖 last-message JSON 提取、fenced JSON 清洗、非法 JSON 原样透传和日志落盘。
  - Web 默认 `Patch coder / Team command` 已从示例后端切换为 `scripts/run_omx_team_patch.py {task_id} {prompt_file} {run_dir}`。
  - 更新 `docs/codex/v1/designs/自动循环进化编码智能体系统-team-protocol.md` 第 13 节，记录真实后端边界、命令和验证结果。
- 验证：
  - `python -m py_compile orchestrator/interfaces/web/main.py scripts/run_omx_team_patch.py scripts/run_omx_team_real_smoke.py` 通过。
  - `python -m pytest -q tests/test_omx_team_patch_backend_script.py tests/test_omx_team_patch_agent.py tests/test_web_ui.py` 通过，`14 passed`。
  - `python scripts/run_omx_team_real_smoke.py` 通过，真实 run 为 `run-20260523-094306-547489`，状态 `done`。
  - `python -m pytest -q` 通过，当前为 `79 passed`。
- 下一步建议：
  - 在 Web 页面提交默认任务，验证浏览器侧真实 OMX/Codex 后端体验。
  - 下一阶段可做 durable `omx team` / `omx pipeline` 异步接入：Web 提交后启动 team runtime，再轮询 status/await 收集 `team_result.json`。
- 2026-05-23 Web UI running progress enhancement:
  - Repaired readable UTF-8 Chinese copy in `orchestrator/interfaces/web/main.py` for default task text, validation errors, job status, and run summary.
  - Rewrote `orchestrator/interfaces/web/templates/job_status.html` to show run id, status, phase, attempt, last heartbeat, latest heartbeat line, and latest phase log while a Web job is still running.
  - Added fallback run inference for Web jobs without `run_id`: match `.omx/runs/*/task.json` by `task_id`, then write the inferred `run_id` back to SQLite.
  - Added `tests/test_web_ui.py::test_job_status_infers_run_and_shows_progress`.
  - Verification: `python -m py_compile orchestrator/interfaces/web/main.py` passed; `python -m pytest -q tests/test_web_ui.py` passed with `11 passed`; `python -m pytest -q` passed with `80 passed`.
  - Web service restarted on `http://127.0.0.1:8765/`; HTTP smoke returned `200`, contained `新建任务`, `run_omx_team_patch.py`, `omx_team_patch`, and did not contain `锛`.
- 2026-05-23 Web real self-test and timeout hardening:
  - Ran a real Web submission through `/tasks/run`, using `scripts/run_omx_team_patch.py -> omx exec -> Codex`.
  - Verified the running Job page inferred and persisted `run_id=run-20260523-140939-176133`, and displayed heartbeat while the backend was still in `agent:omx_team_patch:team`.
  - Found two real issues from the self-test:
    - Windows timeout killed only the wrapper shell, allowing child `omx/codex` processes to keep the Job stuck in `running`.
    - Web marked any returned RunState as `done`, even when the run was actually `halted`.
  - Fixed `SafeCommandRunner` to terminate the whole process tree on Windows via `taskkill /F /T /PID`.
  - Fixed Web job completion mapping: only `RunStatus.DONE` becomes Web `done`; halted runs become Web `failed` with a linkable `run_id`.
  - Added regression coverage:
    - `tests/test_command_safety_and_heartbeat.py::test_timeout_returns_124_for_child_process`
    - `tests/test_web_ui.py::test_web_job_marks_halted_run_as_failed`
  - Verification: `python -m pytest -q tests/test_web_ui.py tests/test_command_safety_and_heartbeat.py` passed with `20 passed`; `python -m pytest -q` passed with `82 passed`.
  - Restarted Web service on `http://127.0.0.1:8765/`.
  - Ran a 5-second real OMX timeout self-test through Web. Result: Job `job-20260523-144249-498585` became `failed`, run `run-20260523-144249-678228` halted in `code`, final report says `exit code 124`, heartbeat reached 5s, and run detail page shows timeout without mojibake.
- 2026-05-23 Web Job recovery reconciliation:
  - Added Web Job reconciliation for service restarts and lost background threads.
  - `/jobs/{job_id}` and homepage recent Jobs now infer missing `run_id` from `.omx/runs/*/task.json` and reconcile terminal `run_state.json`:
    - `RunStatus.DONE` updates Web Job to `done` and redirects to run detail.
    - `RunStatus.HALTED` updates Web Job to `failed` and keeps the run detail link available.
  - Added regression coverage:
    - `tests/test_web_ui.py::test_job_status_reconciles_done_run_after_restart`
    - `tests/test_web_ui.py::test_index_reconciles_halted_run_after_restart`
  - Verification: `python -m pytest -q tests/test_web_ui.py` passed with `14 passed`; `python -m pytest -q` passed with `84 passed`.
  - Restarted Web service on `http://127.0.0.1:8765/`; HTTP smoke returned `200`, contained `新建任务`, `run_omx_team_patch.py`, and the historical timeout Job as `failed / run-20260523-144249-678228`, with no `锛` mojibake.
  - Next recommended implementation step: durable `omx team` / `omx pipeline` runtime integration, now that Web job persistence, terminal-state reconciliation, timeout handling, and progress display are stable.

- 2026-05-23 Durable OMX team runtime adapter foundation:
  - Extended `scripts/run_omx_team_patch.py` with `--runtime exec|team`; default remains `exec` for backward compatibility.
  - Added team runtime command templates:
    - launch: `omx team {workers}:{agent_type} "{task_description}"`
    - await: `omx team await {team_name} --timeout-ms {timeout_ms} --json`
  - Team runtime now writes `attempts/omx_team_runtime_prompt.txt`, instructs OMX team to write final `team_result.json` to the Orchestrator-controlled output path, awaits the team when a team name is available, and logs launch/await diagnostics in `logs/omx_team_patch_backend.json`.
  - Orchestrator contract is unchanged: it still consumes only standard `team_result.json`; patch validation, permission checks, apply, hard checks, review reuse, and quality gate stay in Orchestrator.
  - Added `examples/task.omx-team-runtime-template.json` as the non-blocking durable team template.
  - Updated `docs/codex/v1/designs/自动循环进化编码智能体系统-team-protocol.md` with the durable runtime section and current verification evidence.
  - Regression coverage: `tests/test_omx_team_patch_backend_script.py::test_run_omx_team_patch_team_runtime_collects_result_file`.
  - Verification: `python -m pytest -q tests/test_omx_team_patch_backend_script.py` passed with `3 passed`; `python -m pytest -q` passed with `85 passed`.
  - Next recommended implementation step: run a real environment-dependent `omx team` smoke with an explicit `--team-name` or command override if local OMX team output cannot expose the name automatically, then consider Web form support for choosing `exec` vs `team` runtime.

- 2026-05-25 Real OMX team runtime smoke and hardening:
  - Hardened `scripts/run_omx_team_patch.py` so team runtime fails with exit code `2` when launch succeeds but no `team_name` can be extracted and no `team_result.json` is written.
  - Added regression coverage for the no-team-name/no-result path in `tests/test_omx_team_patch_backend_script.py`.
  - Added `scripts/run_omx_team_runtime_smoke.py` as an environment-dependent real `omx team` smoke. It uses `--runtime team`, writes artifacts under `.tmp/omx-team-runtime-smoke/`, and prints backend diagnostics on failure.
  - Changed `examples/task.omx-team-runtime-template.json` to use relative `python scripts/run_omx_team_patch.py ...` instead of an absolute Chinese-path command, avoiding Windows path encoding fragility.
  - Added `tests/test_team_protocol_examples.py::test_team_runtime_template_uses_relative_script_command`.
  - Real smoke result on this machine: `python scripts/run_omx_team_runtime_smoke.py` reached real `omx team` and failed with `Error: Team mode requires tmux. Install with: apt install tmux / brew install tmux`. Backend diagnostics were written to `.tmp/omx-team-runtime-smoke/run/logs/omx_team_patch_backend.json`.
  - Verification: `python -m py_compile scripts/run_omx_team_patch.py scripts/run_omx_team_runtime_smoke.py` passed; `python -m pytest -q tests/test_omx_team_patch_backend_script.py` passed with `4 passed`; `python -m pytest -q` passed with `86 passed`.
  - Next recommended implementation step: keep Web default on `exec` runtime for this Windows environment; add Web runtime selection only after deciding whether durable team execution will run inside WSL/Linux/tmux or remain an optional advanced backend.

- 2026-05-25 Docker sandbox runner design:
  - Evaluated the proposal to move execution into Docker sandboxes and recorded the target design in `docs/codex/v1/designs/docker-sandbox-runner-design.md`.
  - Key decision: Docker is an execution isolation layer, not a replacement for Orchestrator safety. `SafetyPolicy`, `PatchValidator`, `PatchApplier`, approval, hard-check short circuit, review reuse, and Quality Gate remain Orchestrator-owned.
  - Recommended first implementation scope: Docker hard checks only. Keep Web default as `local`; keep patch generation patch-only; keep patch apply host-controlled.
  - Proposed future fields: `execution_backend=local|docker` and `sandbox` config for image, network, mounts, resource limits, user, and container workdir.
  - Document covers mount layout, permission matrix, network/env policy, failure mapping, logs, Web UI impact, OMX team relationship, and first-stage acceptance criteria.
  - Next recommended implementation step: implement `SandboxConfig` + `ExecutionBackend` parsing, split `LocalCommandRunner`, then add `DockerSandboxRunner` for hard checks behind an opt-in task config.

- 2026-05-25 Docker sandbox runner first implementation:
  - Added `ExecutionBackend` enum with `local|docker`.
  - Added `SandboxConfig` to `TaskConfig`, defaulting to safe local-compatible settings. Existing tasks default to `execution_backend=local`.
  - Split command execution into:
    - `CommandExecutionResult`
    - `LocalCommandRunner`
    - `DockerSandboxRunner`
    - `SafeCommandRunner` as safety-checking dispatcher.
  - Docker runner builds `docker run --rm` with `/worktree`, `/run`, `/cache` mounts, network/resource/user flags, timeout handling, heartbeat, and `logs/docker_sandbox.jsonl`.
  - Added tests proving default local dispatch, opt-in docker dispatch, readonly worktree mount command construction, and sandbox config parsing.
  - Verification: py_compile passed for changed modules; `python -m pytest -q tests/test_command_safety_and_heartbeat.py tests/test_domain_services.py` passed with `16 passed`; full `python -m pytest -q` passed with `91 passed`.
  - Next recommended implementation step: add real environment-dependent Docker hard-check smoke script, then optionally expose Docker backend in Web UI.

- 2026-05-25 Docker hard-check smoke:
  - Added `scripts/run_docker_hard_check_smoke.py`, which creates `.tmp/docker-hard-check-smoke`, writes a Docker-backed task, and runs CLI `--real-checks`.
  - Added `examples/task.docker-hard-check-smoke.json` as a reusable template.
  - Smoke now prints `docker_log`, the last `logs/docker_sandbox.jsonl` entry, and a targeted environment hint when Docker daemon or image availability blocks execution.
  - Real smoke reached `DockerSandboxRunner` and produced run `run-20260525-143108-385853`; it halted in `hard_checks` because Docker daemon is not running on this machine:
    - `docker_environment=daemon_not_running`
    - `hint=start Docker Desktop or Docker daemon, then rerun this smoke`
  - Verification: `python -m py_compile scripts/run_docker_hard_check_smoke.py` passed; `python -m pytest -q tests/test_command_safety_and_heartbeat.py tests/test_domain_services.py` passed with `16 passed`; full `python -m pytest -q` passed with `91 passed`.
  - Next recommended implementation step: after Docker daemon is started, rerun `python scripts/run_docker_hard_check_smoke.py`; if it passes, expose Docker backend as an optional Web form setting.

- 2026-05-25 Docker daemon enabled and smoke passed:
  - Started Docker Desktop and waited until `docker info --format "{{.ServerVersion}}"` returned `24.0.6`.
  - First rerun reached Docker and pulled `python:3.12-slim`, but failed because the base image does not include pytest.
  - Updated `scripts/run_docker_hard_check_smoke.py` and `examples/task.docker-hard-check-smoke.json` to use standard-library `python -m unittest -q`, keeping the smoke independent of package installation.
  - Real Docker smoke passed:
    - `python scripts/run_docker_hard_check_smoke.py`
    - `run_id=run-20260525-144626-202424 status=done phase=done`
    - `logs/docker_sandbox.jsonl` recorded `image=python:3.12-slim`, `network=none`, `worktree_mount=readonly`, `command=python -m unittest -q`, `exit_code=0`.
  - Verification: `python -m py_compile scripts/run_docker_hard_check_smoke.py` passed; full `python -m pytest -q` passed with `91 passed`.
  - Next recommended implementation step: expose Docker backend as an optional Web UI field with safe defaults, while keeping local as the default.

- 2026-05-25 Web UI optional Docker backend:
  - Exposed `execution_backend=local|docker` on the Web new-task form. Default remains `local`.
  - Added Web form sandbox fields: image, network, worktree mount, memory limit, and CPU limit.
  - Generated Web task JSON now persists `execution_backend` and `sandbox` so the existing `SafeCommandRunner` dispatcher can route Docker opt-in tasks to `DockerSandboxRunner`.
  - Added Docker-specific validation:
    - image must be non-empty.
    - network must be `none|bridge`.
    - worktree mount must be `readonly|rw`.
    - first Web phase rejects `rw` and only allows Docker worktree `readonly`.
    - memory and CPU limits must be basic valid values.
  - Added regression coverage:
    - Web index exposes Docker backend option.
    - Web task submission without Docker fields keeps `execution_backend=local`.
    - Docker Web submission writes expected sandbox config.
    - Invalid Docker sandbox values are rejected with HTTP 422.
  - Verification: `python -m py_compile orchestrator/interfaces/web/main.py` passed; `python -m pytest -q tests/test_web_ui.py` passed with `18 passed`; full `python -m pytest -q` passed with `95 passed`.
  - Next recommended implementation step: run a real Web-submitted Docker hard-check smoke, then decide whether Codex/OMX patch generation should also be containerized behind a separate explicit opt-in.

- 2026-05-25 Web-submitted Docker hard-check smoke:
  - Added `scripts/run_web_docker_hard_check_smoke.py`.
  - The smoke submits a real Web `/tasks/run` form through FastAPI `TestClient` with:
    - `execution_backend=docker`
    - `sandbox_image=python:3.12-slim`
    - `sandbox_network=none`
    - `sandbox_worktree_mount=readonly`
    - `check_command=python -m unittest -q`
    - `agent_mode=mock`
    - `real_checks=on`
  - The smoke waits for the persisted SQLite Web Job to reach a terminal state and then prints run evidence:
    - `run_state.json`
    - `logs/docker_sandbox.jsonl`
    - `attempts/001/hard_checks.json`
    - `attempts/001/quality_report.json`
  - Real local verification passed:
    - `python scripts/run_web_docker_hard_check_smoke.py`
    - `job_status=done`
    - `run_id=run-20260525-151613-420567`
    - Docker log recorded `image=python:3.12-slim`, `network=none`, `worktree_mount=readonly`, `command=python -m unittest -q`, `exit_code=0`.
    - `quality_score=100 quality_passed=True`.
  - Added lightweight regression coverage to compile the smoke script from `tests/test_web_ui.py`, while keeping the real Docker execution as an environment-dependent manual smoke.
  - Next recommended implementation step: evaluate whether Codex/OMX patch generation should run in Docker as a separate explicit opt-in, keeping patch apply host-controlled.

- 2026-05-25 Docker agent patch generation opt-in foundation:
  - Added Docker-aware placeholder rendering in `AgentPromptBuilder.render_command`.
  - When `execution_backend=docker`, run artifact placeholders now map to container paths:
    - `{run_dir}` -> `/run`
    - `{attempt_dir}` -> `/run/attempts/{attempt}`
    - `{task_json}` -> `/run/task.json`
    - `{prompt_file}` -> `/run/attempts/{attempt}/{role}_prompt.txt`
    - `{reason_file}` -> `/run/attempts/{attempt}/fix_reason.json`
    - `{worktree}` -> `/worktree`
  - Local backend behavior remains unchanged and continues to render host absolute paths.
  - Added `scripts/run_docker_agent_patch_smoke.py` as an environment-dependent proof that patch generation can run inside Docker while patch apply stays host Orchestrator-controlled.
  - Real local verification passed:
    - `python scripts/run_docker_agent_patch_smoke.py`
    - `run_id=run-20260525-165757-265904 status=done phase=done`
    - Docker agent phase used `/run/attempts/001/team_prompt.txt` and exited `0`.
    - Host Orchestrator applied the returned patch; `calculator_fixed=True`.
    - Docker hard check phase then ran `python -m unittest -q` and exited `0`.
  - Added regression coverage:
    - Docker path rendering contract in `tests/test_external_agent.py`.
    - Smoke script compilation coverage, keeping real Docker execution manual/environment-dependent.
  - Next recommended implementation step: decide whether Web UI should expose a clearly labeled advanced Docker-agent mode, or keep Docker agent execution task-json-only until image/credential/network policy is designed.

- 2026-05-25 Web UI Docker agent guardrail:
  - Added Docker command path validation in `orchestrator/interfaces/web/main.py`.
  - The guardrail runs only when `execution_backend=docker`.
  - It rejects Windows host absolute paths in Test/Patch coder/Patch fixer/Reviewer commands, such as `D:\tools\backend.py`.
  - It rejects unsupported container absolute paths and allows only `/worktree`, `/run`, and `/cache`.
  - Placeholder-based commands remain allowed, so `{prompt_file}`, `{run_dir}`, `{task_json}`, `{reason_file}`, and `{worktree}` can be rendered by Orchestrator.
  - Added a concise Web hint below the Docker sandbox fields explaining the accepted path model.
  - Added regression coverage:
    - Docker Web submission rejects host absolute command paths.
    - Docker Web submission accepts container paths and placeholders.
  - Verification: `python -m py_compile orchestrator/interfaces/web/main.py` passed; `python -m pytest -q tests/test_web_ui.py` passed with `21 passed`.
  - Next recommended implementation step: decide whether to add a curated Docker agent command preset in Web UI, instead of requiring users to hand-write container-compatible commands.
