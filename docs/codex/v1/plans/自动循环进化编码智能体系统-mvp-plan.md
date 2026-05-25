# 自动循环进化编码智能体系统 - MVP 实施计划

## 1. 目标

基于 V7 技术方案，实现一个可运行的单任务自动循环 MVP。MVP 重点验证自动编码、Hard Check、Reviewer JSON、质量门控、安全策略、状态持久化和人工介入报告。

## 2. 前置条件

- 已确定 V7 架构设计。
- 已具备 Codex CLI 或可替代 Agent 调用方式。
- 目标项目具备至少一个测试命令。
- 能在本地工作区创建运行产物目录。
- 用户接受 MVP 暂不实现多 Agent 并行和自动 PR。

## 3. 里程碑

| 阶段 | 目标 | 产物 |
| :--- | :--- | :--- |
| M1 | CLI 骨架和任务读取 | `main.py`、`task.json` 校验 |
| M2 | 安全策略和状态持久化 | `safety.py`、`state.py` |
| M3 | Hard Check 与短路 | `checks.py`、hard check report |
| M4 | Reviewer JSON 解析 | `review.py`、malformed JSON 重试 |
| M5 | Quality Gate | `gate.py`、`quality_report.json` |
| M6 | Agent Adapter | `agent_adapter.py` 接入 Codex/OMX |
| M7 | 最终报告和候选规则 | `final_report.md`、pending rule |

## 4. 实施步骤

### Step 1: Orchestrator CLI 骨架

内容：

- 创建 `orchestrator/main.py`。
- 支持传入 `task.json` 路径。
- 初始化 `run_id`。
- 创建 `.omx/runs/{run_id}/`。
- 配置日志格式和 heartbeat 参数。

验收：

- 能读取任务文件。
- 能创建运行目录。
- 能输出 phase 日志。

### Step 2: task.json 校验

内容：

- 定义任务模型。
- 校验 `change_type` 是否为 `feature | bugfix | refactor | config`。
- 校验 `max_attempts`、`max_review_json_retries`、`heartbeat_interval_seconds`。
- 校验路径字段。

验收：

- 缺少必要字段时失败。
- 非法 `change_type` 时失败。
- 合法任务能进入下一步。

### Step 3: 安全策略

内容：

- 实现 `allowed_paths` 和 `forbidden_paths` 检查。
- 实现权限等级：read-only、workspace-write、elevated、forbidden。
- 实现 `change_type=config` 权限映射。
- 实现 forbidden 优先。

验收：

- 命中 forbidden 时直接 halt。
- config 类型未命中 forbidden 时映射 elevated。
- 日志记录 `reason=change_type_config_requires_elevated`。

### Step 4: State Store

内容：

- 定义 `run_state.json`。
- 每个阶段更新 `current_phase`。
- 每次 heartbeat 更新 `last_heartbeat_at`。
- 每次 attempt 保存产物。

验收：

- 中途失败仍能看到当前阶段和最近产物。
- attempt 目录按序创建。

### Step 5: Check Runner

内容：

- 执行 `task.check_commands.test`。
- 执行 lint 和 typecheck。
- 捕获退出码、stdout、stderr、耗时。
- 长命令输出 heartbeat。

验收：

- 测试失败能生成 hard check report。
- Hard Check 失败不会调用 Reviewer。
- Hard Check 成功才进入 Review。

### Step 6: Review Parser

内容：

- 调用 Reviewer Agent。
- 提取 JSON。
- 校验 Schema。
- 校验 `review.task_id == task.task_id`。
- malformed JSON 或 task_id 不匹配时最多重试 2 次。
- 保存 `malformed_review_*.txt`。

验收：

- 非法 JSON 能重试。
- task_id 不匹配能重试。
- 超过重试次数能 halt。

### Step 7: Quality Gate

内容：

- 实现综合评分。
- 实现 Diff 风险评分。
- 根据 `change_type` 处理测试覆盖扣分。
- 输出 done/retry/halt。

验收：

- 分数低于 80 时 retry。
- blocking issue 时 retry 或 halt。
- critical issue 时 halt。
- refactor 不因源码改但测试未改扣分。

### Step 8: Agent Adapter

内容：

- 封装 Coder 调用。
- 封装 Fixer 调用。
- 封装 Reviewer 调用。
- MVP 可以先用命令行适配层，后续替换为 OMX。

验收：

- Orchestrator 不直接依赖具体 CLI 细节。
- Agent 输出可被记录。

### Step 9: Final Report

内容：

- 输出最终状态。
- 输出尝试次数。
- 输出质量分。
- 输出失败原因或完成摘要。
- 输出人工介入建议。

验收：

- done 时报告可用于交付。
- halt 时报告可用于人工接手。

### Step 10: Pending Rule Proposal

内容：

- 从失败日志或重复错误生成候选规则。
- 写入 `pending-rules/`。
- 不自动写入正式 Skill。

验收：

- 候选规则包含来源、证据、适用范围和审核状态。

## 5. 验证方式

### 5.1 正向验证

- 输入一个简单 bugfix 任务。
- Coder 修改代码。
- 测试通过。
- Reviewer 输出合法 JSON。
- Quality Gate 通过。
- 输出 final report。

### 5.2 失败验证

- 构造测试失败，确认 Reviewer 被短路。
- 构造非法 Review JSON，确认重试。
- 构造 task_id 不匹配，确认重试。
- 构造 forbidden path，确认阻断。
- 构造 config 任务，确认 elevated 映射。

## 6. 风险与回滚

| 风险 | 应对 | 回滚 |
| :--- | :--- | :--- |
| Agent 命令不可用 | Adapter 先支持 mock 模式 | 回退到 mock 测试 |
| 测试命令耗时过长 | heartbeat 和超时配置 | 手动停止进程 |
| JSON 解析不稳定 | 重试和模板提示 | halt 并人工接手 |
| 安全策略误杀 | 输出阻断原因 | 调整 task 配置 |
| 自动修复反复失败 | max attempts | 输出 final report |

## 7. 检查点

- Checkpoint 1：CLI 能读任务并生成 run_state。
- Checkpoint 2：Hard Check 短路可用。
- Checkpoint 3：Reviewer JSON 重试可用。
- Checkpoint 4：Quality Gate 可用。
- Checkpoint 5：真实 bugfix demo 跑通。

## 8. 不在 MVP 内的事项

- 多 Agent 并行。
- 自动 PR。
- Web Dashboard。
- 自动写正式 Skill。
- 跨仓库任务。
- 生产环境操作。
