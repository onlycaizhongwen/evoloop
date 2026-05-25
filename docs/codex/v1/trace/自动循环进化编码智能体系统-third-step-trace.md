# 自动循环进化编码智能体系统第三步 Trace 审查

## 审查范围

本次审查覆盖第三步计划与实现结果：

- 计划文档：`docs/codex/v1/plans/自动循环进化编码智能体系统-third-step-plan.md`
- 演示文档：`docs/codex/v1/plans/自动循环进化编码智能体系统-demo-script.md`
- 协议文档：`docs/codex/v1/designs/自动循环进化编码智能体系统-agent-protocol.md`
- 实现与测试：patch-only unified diff、pending patch 审批、`--rerun-task`、诊断产物、演示脚本
- 过程记录：`.codex/plans/main/auto-evolution-implementation/process.md`

## 已对齐项

### 1. Unified Diff Patch JSON

计划要求：提供 patch-only unified diff 端到端样例。

实现结果：

- `PatchPlan` 增加 `UnifiedDiffOperation`。
- `PatchApplier` 支持单文件 hunk 解析、上下文校验、dry-run 和受控应用。
- 新增 `examples/patch_unified_diff_backend.py`。
- 新增 `examples/task.omx-patch-unified-diff-smoke.json`。
- 新增 `.tmp/omx-unified-diff-smoke/` 独立 smoke 工作区。

验证结果：

- `python -m orchestrator.interfaces.cli.main --task examples/task.omx-patch-unified-diff-smoke.json --agent omx_patch --real-checks`
- smoke run：`run-20260521-173445-649699`
- 结果：`status=done`

结论：已闭环。

### 2. patches list 审计展示

计划要求：`patches list` 能直接展示 apply 后验证状态。

实现结果：

- `PendingPatchService._summary` 新增 `checks_status=not_run|passed|failed`。
- CLI 输出新增 `rerun_phase`、`rerun_attempt`、`rerun_reason`。
- 保留 `checks_passed`、`rerun_status`、`rerun_run_id` 兼容字段。

验证结果：

- pending patch 输出 `checks_status=not_run`。
- `--rerun-checks` 后输出 `checks_status=passed`。
- `--rerun-task` 后输出 `rerun_status=done|halted` 与 `rerun_reason=...`。

结论：已闭环。

### 3. 失败诊断产物

计划要求：覆盖 malformed patch JSON、context mismatch、rerun hard check failed。

实现结果：

- patch 输出失败时写入 `{role}_patch_raw_output.txt`。
- patch 校验/应用失败时写入 `{role}_patch_diagnostics.json`。
- diagnostics 包含 `role/error_type/error/raw_output_path/raw_output_preview`。
- `PatchApplier` 对 no-hunk unified diff 直接拒绝，避免静默假成功。
- `patches apply --rerun-task` 将验证失败原因写入 `post_apply_rerun.reason`。

验证结果：

- `test_omx_patch_malformed_json_writes_diagnostics`
- `test_patches_apply_rerun_task_records_failure_reason`
- `test_patch_applier_unified_diff_rejects_context_mismatch`
- `test_patch_applier_unified_diff_rejects_missing_hunk`

结论：已闭环。

### 4. 演示脚本与演示文档

计划要求：补一份可对外演示的最小命令序列。

实现结果：

- 新增 `scripts/run_patch_demo.py`。
- 新增 `docs/codex/v1/plans/自动循环进化编码智能体系统-demo-script.md`。
- 演示脚本自动重置 smoke 工作区，串联 unified diff smoke、pending patch list、审批 apply、`--rerun-task`。

验证结果：

- `python scripts/run_patch_demo.py` 执行成功。
- unified diff smoke：`run-20260521-174136-200457 status=done`
- pending patch approval：`run-20260521-174138-333591`
- rerun validation：`run-20260521-174139-595059`
- 输出包含 `rerun_status=done` 与 `rerun_reason=quality gate passed`

结论：已闭环。

## 未完全对齐项

### 1. “真实 OMX/Codex”表述与当前实现边界

计划中提到“真实 OMX/Codex patch-only unified diff 端到端样例”。当前第三步已经提供可控 backend 的端到端 smoke，并已有早前真实 `omx exec` patch-only JSON 链路验证记录；但第三步新增的 unified diff smoke 默认仍使用本地可控 backend，而不是每次都调用真实 `omx exec`。

原因：

- 本地可控 backend 更稳定，适合作为回归测试和演示基线。
- Windows 环境下真实 OMX/Codex 子进程写操作曾出现 sandbox 限制；当前架构已通过 patch-only 模式绕开直接写文件风险。

影响：

- 不影响第三步“可演示、可审计、可运维”的收口。
- 若要做生产级外部模型验收，仍建议后续增加一个可选真实 OMX unified diff smoke。

建议后续动作：

- 新增 `examples/task.omx-patch-unified-diff-real-smoke.json`。
- 复用 `scripts/run_external_agent.py` 与 `omx exec --output-last-message`。
- 将真实 OMX smoke 标记为环境依赖测试，不纳入默认 pytest。

## 风险与影响

- 当前 unified diff 支持范围限定为单文件 hunk，多文件 diff 需要拆成多个 operation。这与第三步计划一致。
- `patches list` 输出字段增加，但保留旧字段，兼容风险低。
- 失败诊断会保存 raw output preview，当前限制为 1000 字符，避免日志过大。
- 演示脚本会重置 `.tmp/omx-unified-diff-smoke` 和 `.tmp/omx-real-smoke/old_file.py`，只应作为本地 smoke 使用。

## 验证汇总

- `python -m pytest -q tests/test_cli_resume.py tests/test_patch_agent.py`：20 passed
- `python -m pytest -q`：61 passed
- `python scripts/run_patch_demo.py`：通过

## 总结结论

第三步主体目标已完成并闭环：

- patch-only unified diff 能力可运行。
- pending patch 审批状态可审计。
- rerun-task 验证结果可追踪。
- 失败诊断产物可定位问题。
- 演示脚本和演示文档可用于对外讲解。

剩余项属于后续增强：补一个真实 OMX/Codex unified diff smoke 模板，并将其作为环境依赖型验证项管理。

## 后续增强更新

已补真实 OMX/Codex unified diff smoke 模板：

- `examples/task.omx-patch-unified-diff-real-smoke.json`
- `examples/task.codex-patch-unified-diff-real-smoke.json`
- `docs/codex/v1/plans/自动循环进化编码智能体系统-real-unified-diff-smoke.md`

验证情况：

- 两个 task 模板可被 `TaskLoader` 正常读取。
- 默认回归 `python -m pytest -q` 通过，61 passed。

边界说明：

- 真实 smoke 仍属于环境依赖型验证项，需要本机 OMX/Codex CLI 和对应 `OMX_*_COMMAND` 环境变量。
- 不纳入默认 pytest，不改变第三步已收口结论。
