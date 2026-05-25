# 自动循环进化编码智能体系统 Team Protocol

## 1. 目标

本文档定义 OMX team 编排模式下，Orchestrator 与 OMX 多智能体团队之间的最小稳定协议。

目标链路为：

```text
Orchestrator -> OMX team -> Codex exec -> patch JSON / review JSON -> Orchestrator 审批、应用、测试、质量门禁
```

第一版 team protocol 只固化输入输出契约，不让 team 直接修改真实工作区。真实文件写入仍由 Orchestrator 基于 patch JSON 校验后执行。

## 2. 职责边界

### Orchestrator 负责

- 创建 `team_task.json`，声明任务、工作区、路径权限、角色和最终产物。
- 调用 OMX team，并收集 `team_result.json`。
- 校验 `patch_plan.json`、`review.json`、diagnostics 等结构化产物。
- 进行路径安全校验、forbidden path 拦截、patch dry-run、风险评分和人工审批。
- 应用 patch 到绝对路径 worktree。
- 运行 hard checks、Reviewer 复核、Quality Gate 和 `patches apply --rerun-task`。
- 维护 run state、SQLite web job、pending patch、final report 和审计日志。

### OMX team 负责

- 按角色拆解任务、生成方案、调用 Codex 执行具体推理或产物生成。
- 产出结构化 artifacts，而不是直接改真实工作区。
- 在失败时返回可诊断信息，说明失败角色、阶段、原因和建议动作。
- 不绕过 Orchestrator 的路径权限、审批、测试和质量门禁。

## 3. MVP 角色

| 角色 | 必需 | 主要输入 | 主要输出 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| Planner | 是 | `team_task.json` | `team_plan.json` | 拆解目标、约束、执行阶段和风险点。 |
| Coder | 是 | `team_plan.json`、允许文件快照 | `patch_plan.json` | 生成 patch JSON，不直接写 worktree。 |
| Reviewer | 是 | `patch_plan.json`、任务上下文 | `review.json` | 返回合法 Review JSON。 |
| Tester | 否 | patch 意图、check 命令 | `test_recommendation.json` | 给出测试建议或环境依赖提示。 |
| Gatekeeper | 否 | review、测试建议、风险信息 | `gate_advice.json` | 给出是否建议进入 Orchestrator gate 的建议。 |
| Fixer | 否 | diagnostics、失败原因 | `fix_patch_plan.json` | 生成修复 patch JSON，仍需 Orchestrator 校验。 |

## 4. team_task.json

`team_task.json` 是 Orchestrator 发给 OMX team 的任务控制面。

必需字段：

- `schema_version`: 当前为 `1.0`。
- `task_id`: 与 Orchestrator task id 一致。
- `mode`: 当前建议为 `omx_team_patch`。
- `change_type`: `feature | bugfix | refactor | config`。
- `title`: 任务标题。
- `description`: 任务描述。
- `worktree_path`: 工作区路径，可为相对路径，但 Orchestrator 执行前会解析成绝对路径。
- `allowed_paths`: 允许读取和生成 patch 的相对路径。
- `forbidden_paths`: 禁止访问或修改的相对路径。
- `roles`: 本次 team 需要执行的角色列表。
- `final_artifacts`: Orchestrator 最终会读取和校验的产物映射。
- `constraints`: 安全、输出和执行约束。

示例文件：

```text
examples/team_task.omx-team-patch.json
```

## 5. team_result.json

`team_result.json` 是 OMX team 返回给 Orchestrator 的唯一顶层结果。

必需字段：

- `schema_version`: 当前为 `1.0`。
- `task_id`: 必须等于 `team_task.json.task_id`。
- `status`: `completed | failed | partial`。
- `roles`: 每个角色的执行状态和 artifact 名称。
- `artifacts`: 内嵌或引用的结构化产物。
- `diagnostics`: 失败、跳过、降级和环境依赖说明。

示例文件：

```text
examples/team_result.omx-team-patch.json
```

## 6. 产物契约

### patch_plan.json

必须兼容现有 `PatchPlan` 模型：

```json
{
  "schema_version": "1.0",
  "task_id": "task-omx-team-patch-001",
  "summary": "Replace subtraction with addition.",
  "operations": [
    {
      "op": "replace_text",
      "path": "calculator.py",
      "old": "return a - b",
      "new": "return a + b"
    }
  ]
}
```

支持操作继续沿用当前 patch-only 协议：

- `replace_text`
- `create_file`
- `delete_file`
- `unified_diff`

### review.json

必须兼容现有 `ReviewResult` 模型：

```json
{
  "schema_version": "1.0",
  "task_id": "task-omx-team-patch-001",
  "pass": true,
  "confidence": 90,
  "summary": "Patch is scoped and safe.",
  "issues": [],
  "blocking": false,
  "recommended_next_action": "pass"
}
```

`task_id` 必须与当前任务一致，否则 Orchestrator 按非法 review 处理，并进入 retry 或 halt。

## 7. Phase Flow

推荐 MVP 流程：

```text
Planner -> Coder -> Reviewer -> Tester -> Gatekeeper -> Fixer(loop on failure)
```

执行语义：

1. Orchestrator 生成 `team_task.json`。
2. OMX team 读取任务并执行 Planner。
3. Coder 基于计划生成 `patch_plan.json`。
4. Reviewer 对 patch 产物返回 `review.json`。
5. Tester 只给建议或环境依赖说明，不直接运行 Orchestrator hard checks。
6. Gatekeeper 给出建议，不替代 Orchestrator Quality Gate。
7. 任一必需角色失败时，返回 `status=failed` 或 `partial`，并写入 diagnostics。
8. Orchestrator 校验 team_result 后，进入现有 patch approval / apply / rerun-task 链路。

## 8. 失败处理

OMX team 失败时不得静默成功。`diagnostics` 至少包含：

- `role`: 失败角色。
- `phase`: 失败阶段。
- `severity`: `info | warning | error`。
- `message`: 可读失败原因。
- `recommended_next_action`: `retry | fix | halt | manual_review`。

常见失败映射：

| 失败类型 | team status | Orchestrator 行为 |
| :--- | :--- | :--- |
| Planner 无法拆解 | `failed` | halt，并落诊断。 |
| Coder 无法生成合法 patch JSON | `failed` 或 `partial` | 进入 patch JSON retry，超过阈值 halt。 |
| Reviewer 输出非法 JSON | `partial` | 进入 review JSON repair/retry，超过阈值 halt。 |
| Tester 环境不可用 | `partial` | 记录 warning，Orchestrator hard checks 仍是最终依据。 |
| Gatekeeper 建议阻断 | `completed` | Orchestrator 仍运行自己的 gate，但把建议纳入审计。 |

## 9. 安全约束

- Team 角色不能直接修改 `worktree_path`。
- Team 角色只能输出结构化 JSON artifacts。
- `allowed_paths` 必须是 worktree 内相对路径。
- `forbidden_paths` 优先级高于 allowed paths。
- `change_type=config` 时，Orchestrator 仍按既有规则提升默认权限到 elevated，并先检查 forbidden paths。
- patch 风险评分、人工审批和最终 apply 必须由 Orchestrator 执行。
- hard checks 失败时短路，不继续消耗 token 运行后续 Reviewer / Gatekeeper。

## 10. 与现有协议映射

| Team Protocol | 现有系统 |
| :--- | :--- |
| `patch_plan.json` | `PatchPlan`、`PatchValidator`、`PatchApplier` |
| `review.json` | `ReviewResult`、`ReviewValidator` |
| `diagnostics` | attempt diagnostics、agent log、pending patch reason |
| `team_result.status=partial` | Orchestrator 可进入 retry/fix/halt |
| `patch_plan.operations[].op=unified_diff` | 当前 unified diff patch-only 能力 |
| `patches apply --rerun-task` | 审批后重跑 hard checks / review / quality gate |

## 11. 下一步落地建议

1. 保持本版为 docs/examples/tests，不改变真实执行路径。
2. 下一版新增 `agent_mode=omx_team_patch`，由 Orchestrator 调用 OMX team 并读取 `team_result.json`。
3. 复用当前 `PatchValidator`、`ReviewValidator` 和 `PendingPatchService`，不要重复实现安全校验。
4. 在 Web UI 增加 Team 模式选择和 team diagnostics 展示。

## 12. 当前实现状态

已完成 `agent_mode=omx_team_patch` 的最小可运行链路：

- 新增 `OmxTeamPatchAgent`，通过 `patch_coder` 或 `coder` 命令调用 OMX team 后端。
- 后端返回 `team_result.json`，Orchestrator 解析 `artifacts.patch_plan` 与 `artifacts.review`。
- `patch_plan` 继续交给现有 `PatchValidator`、`PatchApplier`、`PatchApprovalPolicy` 处理。
- `review` 会缓存到当前 run，后续 review phase 直接复用 team 返回的 review JSON。
- 失败时写入 `team_result_raw_output.txt` 与 `team_diagnostics.json`，保持可审计。
- 已新增可控 smoke：`examples/task.omx-team-patch-smoke.json` 与 `examples/team_patch_backend.py`。

已验证：

```text
python -m orchestrator.interfaces.cli.main --task examples/task.omx-team-patch-smoke.json --agent omx_team_patch --real-checks
run_id=run-20260522-163446-036926 status=done phase=done

python -m pytest -q
74 passed
```

下一步建议进入 Web UI 接入：在首页 `agent_mode` 下拉中加入 `omx_team_patch`，并在 run detail 页面展示 `team_result.json` 与 `team_diagnostics.json`。

## 13. 真实 OMX/Codex 后端接入

已新增真实非交互后端入口：

```text
scripts/run_omx_team_patch.py
```

调用方式：

```text
python scripts/run_omx_team_patch.py {task_id} {prompt_file} {run_dir}
```

默认后端命令：

```text
omx exec --skip-git-repo-check --sandbox read-only --output-last-message "{output_last_message}" -
```

职责边界：

- `run_omx_team_patch.py` 只负责把 Orchestrator 的 team prompt 包装为更严格的 `team_result.json` 输出提示，并调用 `omx exec`。
- Codex/OMX 仍然不得直接修改 worktree；只能输出 `team_result.json`。
- Orchestrator 继续负责 `patch_plan` 校验、补丁应用、测试、review 复用和 quality gate。
- 后端 stdout/stderr 会写入 `logs/omx_team_patch_backend.json`，用于诊断真实 OMX/Codex 调用失败。
- 可通过环境变量 `OMX_TEAM_PATCH_COMMAND` 或 `--backend-command` 替换底层命令，后续可接入 durable `omx team` / `omx pipeline`。

已新增模板与 smoke：

```text
examples/task.omx-team-real-template.json
scripts/run_omx_team_real_smoke.py
```

验证记录：

```text
python scripts/run_omx_team_real_smoke.py
run_id=run-20260523-094306-547489 status=done phase=done

python -m pytest -q
79 passed
```

当前 Web 首页默认 `Patch coder / Team command` 已切换为真实脚本：

```text
python ".../scripts/run_omx_team_patch.py" {task_id} {prompt_file} {run_dir}
```

## 14. Durable OMX Team Runtime 适配

`scripts/run_omx_team_patch.py` 现在支持两种 runtime：

- `exec`：默认模式，调用 `omx exec --output-last-message ... -`，由 Codex 直接返回标准 `team_result.json`。
- `team`：实验性 durable team 模式，调用 `omx team ...` 启动团队，再通过 `omx team await ...` 等待完成，并从约定路径读取最终 `team_result.json`。

关键约束保持不变：

- Orchestrator 仍只消费标准 `team_result.json`。
- OMX team 只能把最终结果写入脚本传入的 `team_result_path`，不能直接修改目标 worktree。
- patch 校验、路径权限、pending patch 审批、apply、hard checks、review 复用和 quality gate 仍由 Orchestrator 执行。
- `team` runtime 会写入 `attempts/omx_team_runtime_prompt.txt`，其中包含完整 Orchestrator prompt 和最终 JSON 写入路径。
- `logs/omx_team_patch_backend.json` 会记录 launch/await 命令、team_name、returncode、stdout/stderr preview 和结果路径，便于排查真实 OMX team 调用问题。

命令示例：

```text
python scripts/run_omx_team_patch.py {task_id} {prompt_file} {run_dir} --runtime team --team-workers 3 --team-agent-type executor
```

可覆盖命令模板：

```text
python scripts/run_omx_team_patch.py {task_id} {prompt_file} {run_dir} ^
  --runtime team ^
  --team-launch-command "omx team {workers}:{agent_type} \"{task_description}\"" ^
  --team-await-command "omx team await {team_name} --timeout-ms {timeout_ms} --json"
```

示例任务：

```text
examples/task.omx-team-runtime-template.json
```

当前验证记录：

```text
python -m pytest -q tests/test_omx_team_patch_backend_script.py
3 passed

python -m pytest -q
85 passed
```

注意：`team` runtime 的默认 launch 命令依赖真实 `omx team` 输出中能提取 `team_name`。如果当前环境的 `omx team` 输出格式不同，应显式传入 `--team-name`，或用 `--team-launch-command` / `--team-await-command` 覆盖命令模板。

## 15. 真实 Team Runtime Smoke 记录

新增环境依赖型验证脚本：

```text
scripts/run_omx_team_runtime_smoke.py
```

验证目标：

- 使用 `scripts/run_omx_team_patch.py --runtime team` 走真实 `omx team` launch/await 入口。
- 不修改真实业务 worktree，只验证 team runtime 能否产出标准 `team_result.json`。
- 成功时 stdout 必须是合法 JSON，且 `task_id=task-omx-team-runtime-smoke`。
- 失败时必须把 `logs/omx_team_patch_backend.json` 和 `attempts/omx_team_runtime_prompt.txt` 留在 `.tmp/omx-team-runtime-smoke/` 便于诊断。

当前本机 smoke 结果：

```text
python scripts/run_omx_team_runtime_smoke.py
Error: Team mode requires tmux. Install with: apt install tmux / brew install tmux
```

结论：

- `team` runtime 适配层已经能调用真实 `omx team` 并落盘失败诊断。
- 当前 Windows 环境缺少 tmux，因此 durable OMX team 模式不能在本机直接完成真实闭环。
- 默认 `exec` runtime 不受影响，仍可继续作为 Web 默认真实 Codex 后端。

补充验证：

```text
python -m py_compile scripts/run_omx_team_patch.py scripts/run_omx_team_runtime_smoke.py
python -m pytest -q tests/test_omx_team_patch_backend_script.py
4 passed

python -m pytest -q
86 passed
```
