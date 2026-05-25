# 自动循环进化编码智能体系统 - MVP Trace 审查

## 1. 审查范围

本次审查对齐以下产物：

- Requirements：`docs/codex/v1/requirements/自动循环进化编码智能体系统-requirements.md`
- Technical Design：`docs/codex/v1/designs/自动循环进化编码智能体系统-technical-design.md`
- V7 Design：`docs/codex/v1/designs/自动循环进化编码智能体系统-v7.md`
- MVP Plan：`docs/codex/v1/plans/自动循环进化编码智能体系统-mvp-plan.md`
- 实现范围：`orchestrator/`、`examples/`、`tests/`
- 验证基线：`python -m pytest -q`，结果为 27 passed

## 2. 总体结论

MVP 主链路已经基本闭环：任务读取、DDD 分层、状态持久化、Hard Check 短路、Reviewer JSON 重试、`task_id` 一致性校验、Quality Gate、Diff 风险、命令安全、Heartbeat、Pending Rule Proposal、Shell/Codex/OMX 命令适配骨架均已落地。

当前结论：MVP 第一阶段可以进入收口评审，但不建议标记为“生产可用”。仍需补齐真实 Coder/Fixer 代码修改能力、正式 Agent CLI 合约、人工审批流和更完整的运行恢复能力。

## 3. 需求追踪

| 需求 ID | 需求摘要 | 实现状态 | 对应实现/验证 |
| :--- | :--- | :--- | :--- |
| FR-01 | 读取并校验 `task.json` | 已对齐 | `TaskConfig`、`TaskLoader`、CLI 示例任务 |
| FR-02 | 调用 Coder/Fixer 执行单任务修改 | 已对齐基础协议 | `AgentPort`、`MockAgent`、`ShellAgent`、`CodexAgent`、`OmxAgent`；已固化真实 CLI 命令模板、prompt/reason 文件契约和退出码契约，真实写操作需按模板配置具体 Codex/OMX 命令 |
| FR-03 | 执行测试、lint、typecheck | 已对齐 | `ShellCheckRunner`、`FakeCheckRunner` |
| FR-04 | Hard Check 失败短路 Reviewer | 已对齐 | `RunTaskUseCase`；测试覆盖 reviewer calls 为 0 |
| FR-05 | 调用 Reviewer 并解析 `review.json` | 已对齐 | `ReviewValidator`、`MockAgent`、`ShellAgent`、External adapters |
| FR-06 | Reviewer JSON 非法最多重试 2 次 | 已对齐 | `_run_review_with_retry`、`malformed_review_*.txt` |
| FR-07 | 校验 `review.task_id == task.task_id` | 已对齐 | `ReviewValidator.parse_and_validate` |
| FR-08 | 质量评分并决策 done/retry/halt | 已对齐 | `QualityGate`、`QualityReport` |
| FR-09 | 按 Diff 规则计算风险分 | 已对齐 | `GitDiffProvider`、`DiffRiskService`、真实 git 集成测试 |
| FR-10 | 按 `change_type` 调整测试覆盖扣分 | 已对齐 | `DiffRiskService`，`refactor/config` 豁免已测 |
| FR-11 | `config` 先 forbidden 再 elevated | 已对齐 | `SafetyPolicy.resolve_permission/precheck` |
| FR-12 | 输出 heartbeat 与阶段日志 | 部分对齐 | `FileHeartbeat` 支持长命令 heartbeat；CLI phase INFO 日志尚不完整 |
| FR-13 | 持久化运行状态和产物 | 已对齐 | `FileStateRepository`、`.omx/runs/{run_id}` |
| FR-14 | 生成 pending rule proposal | 已对齐 | `RuleProposalService`、`RuleProposalWriter` |

## 4. 计划追踪

| MVP Step | 计划内容 | 实现状态 | 说明 |
| :--- | :--- | :--- | :--- |
| Step 1 | Orchestrator CLI 骨架 | 已对齐 | `orchestrator/interfaces/cli/main.py` |
| Step 2 | `task.json` 校验 | 已对齐 | Pydantic 模型校验已覆盖核心字段 |
| Step 3 | 安全策略 | 已对齐 | 路径、权限、危险命令、allowlist 均已实现 |
| Step 4 | State Store | 已对齐 | run state、attempt、报告产物均已写入 |
| Step 5 | Check Runner | 已对齐 | Shell/Fake runner 均可用 |
| Step 6 | Review Parser | 已对齐 | JSON 提取、schema、task_id、重试已实现 |
| Step 7 | Quality Gate | 已对齐 | 评分、retry/halt/done、diff 风险已实现 |
| Step 8 | Agent Adapter | 已对齐基础协议 | Shell/Codex/OMX 命令适配骨架已完成；真实 Codex/OMX CLI 协议已固化为 `agent-protocol.md`，并补充真实接入模板 |
| Step 9 | Final Report | 已对齐 | `final_report.md` 已生成 |
| Step 10 | Pending Rule Proposal | 已对齐 | halt 场景生成候选规则，不写正式 Skill |

## 5. 主要差异

| 编号 | 差异 | 影响 | 建议 |
| :--- | :--- | :--- | :--- |
| GAP-01 | Coder/Fixer 在 Codex/OMX adapter 中仍依赖外部命令配置，尚未接真实 CLI 协议 | 已补齐基础协议 | 新增 `docs/codex/v1/designs/自动循环进化编码智能体系统-agent-protocol.md`，定义 Codex/OMX 命令模板、prompt/reason 输入、stdout/stderr、退出码与安全 allowlist；新增 `examples/task.codex-real-template.json` 和 `examples/task.omx-real-template.json` |
| GAP-02 | CLI phase INFO 日志不完整，主要依赖状态文件和 heartbeat | 已补齐 | 新增 `PhaseLogger`，写入 `logs/phase.log`，覆盖 init/safety/code/hard_checks/review/quality_gate/fix/done/halt 的 start/end/retry/halt 事件 |
| GAP-03 | `quality_report.json` 当前为扁平模型，设计文档示例为嵌套 hard/soft checks | 已补齐 | 保留扁平实现结构，已同步 V7 示例和正式技术文档字段说明 |
| GAP-04 | Rule Proposal 目前以 halt 原因为主，没有重复错误聚类 | 已补齐 | 新增 `rule_proposals_index.json` 聚类索引，并支持 `rules list/review` 人工审批状态流；仍不自动写正式 Skill |
| GAP-05 | 运行恢复仍停留在可读状态和产物层，没有提供 resume CLI | 已补齐基础能力 | 新增 `resume --run-id` 查看恢复摘要，`resume --run-id <id> --rerun` 基于原 `task.json` 启动 fresh rerun；暂不做半截续跑 |

## 6. 风险与影响

- 当前实现适合作为本地 MVP、演示和工程验证基础。
- 不建议直接接入生产仓库执行真实写操作，除非先完成具体 Codex/OMX CLI 包装脚本验证、人工审批和更细粒度权限策略。
- 现有测试覆盖了核心分支、外部 Agent prompt/reason 文件契约和非 0 退出码，但尚未覆盖真实 Codex/OMX 二进制在长时间任务中的行为。

## 7. 后续动作

1. 已定义 Codex/OMX Agent 的真实 CLI 合约，包括 prompt 输入、工作目录、退出码、stdout/stderr 结构；下一步是按本机实际 Codex/OMX CLI 参数补包装脚本并做受控真实写操作验证。
2. 已补统一 phase logging；后续可继续把日志同步输出到控制台或接入结构化日志采集。
3. 已决定 `quality_report.json` 保持扁平结构；Hard Check 逐命令明细继续由 `hard_checks.json` 承载。
4. 已补 resume CLI 基础能力；后续可评估是否增加真正的半截续跑。
5. 已为 pending rule proposal 增加重复错误聚类索引和人工审批状态流；后续可接入正式 PR/Skill 审批流程。

## 8. 审查结论

MVP 第一阶段实现与 V7 架构、需求文档、MVP 计划总体一致。P0 主流程已闭环，P1/P2 中 heartbeat、状态持久化、候选规则也已具备基础能力。

建议状态：实现阶段可标记为“MVP 第一阶段完成，待真实 Agent 协议与运行恢复增强”。
