# 自动循环进化编码智能体系统演示脚本

## 演示目标

用一组最小命令展示当前 Orchestrator 的 patch-only 闭环：

1. Agent 只输出 patch JSON，不直接改文件。
2. Orchestrator 解析、校验并应用 unified diff。
3. 高风险 patch 先落盘等待审批。
4. 审批后应用 patch，并通过 `--rerun-task` 重跑 hard checks、Reviewer、Quality Gate。
5. 所有关键结果写入 `.omx/runs/{run_id}`，可审计、可复盘。

## 一键演示

```text
python scripts/run_patch_demo.py
```

脚本会自动重置两个 smoke 工作区：

- `.tmp/omx-unified-diff-smoke`
- `.tmp/omx-real-smoke`

并依次执行：

```text
python -m orchestrator.interfaces.cli.main --task examples/task.omx-patch-unified-diff-smoke.json --agent omx_patch --real-checks
python -m orchestrator.interfaces.cli.main --task examples/task.omx-patch-approval-smoke.json --agent omx_patch --real-checks
python -m orchestrator.interfaces.cli.main patches list --run-id <approval_run_id>
python -m orchestrator.interfaces.cli.main patches apply --run-id <approval_run_id> --patch <patch.json> --reviewer demo --note "approved by demo script" --rerun-task
```

## 预期输出

第一段 unified diff smoke 应输出：

```text
run_id=run-... status=done phase=done
```

审批 smoke 初次运行会因为 delete patch 需要人工审批而 halted：

```text
run_id=run-... status=halted phase=code
```

`patches list` 会展示：

```text
status=pending risk_score=8 ops=delete_file files=old_file.py checks_status=not_run
```

审批应用并 rerun 后会展示：

```text
status=applied rerun_status=done rerun_run_id=run-... rerun_reason=quality gate passed
```

## 讲解词建议

- “模型不直接写文件，而是输出 patch JSON。”
- “Orchestrator 对 patch 做 schema、task_id、路径权限和 diff context 校验。”
- “删除文件这类高风险操作不会自动落地，而是进入 pending-patches。”
- “审批后可以触发 `--rerun-task`，重新执行测试、审查和质量门禁。”
- “失败时有 raw output、diagnostics、final_report 和 pending patch JSON，方便追责和复盘。”

## 关键产物位置

```text
.omx/runs/{run_id}/final_report.md
.omx/runs/{run_id}/logs/agent.log
.omx/runs/{run_id}/logs/phase.log
.omx/runs/{run_id}/attempts/001/hard_checks.json
.omx/runs/{run_id}/attempts/001/review.json
.omx/runs/{run_id}/attempts/001/quality_report.json
.omx/runs/{run_id}/pending-patches/001-patch_coder.json
```

## 验收命令

```text
python -m pytest -q
```

当前第三步目标要求：

- unified diff smoke 至少一个 run 到 `done`。
- pending patch 可以 `list/apply --rerun-task`。
- CLI 能展示 `checks_status`、`rerun_status`、`rerun_reason`。
- 全量测试通过。
