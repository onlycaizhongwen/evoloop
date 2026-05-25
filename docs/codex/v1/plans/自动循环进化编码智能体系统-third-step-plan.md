# 自动循环进化编码智能体系统第三步实施计划

## 目标

在已完成 `unified_diff` patch JSON、pending patch 审批、`--rerun-task` 验证闭环的基础上，第三步聚焦把能力打磨成可演示、可审计、可运维的端到端链路。

核心目标：

- 提供真实 OMX/Codex patch-only unified diff 端到端样例。
- 增强 `patches list` 的审计展示，能直接看到 apply 后验证结果。
- 补齐失败诊断产物，让 patch JSON 解析失败、diff context mismatch、rerun-task halt 都能快速定位。
- 保持 DDD 边界清晰，避免把 CLI 逻辑堆进领域层。

## 前置条件

- 当前 `python -m pytest -q` 已通过，基线为 `57 passed`。
- `omx_patch` 已支持 `replace_text/create_file/delete_file/unified_diff`。
- `patches apply --rerun-task` 已改为 post-apply validation run，不再重新调用 coder/fixer。
- `docs/codex/v1/designs/自动循环进化编码智能体系统-agent-protocol.md` 已补充 patch 协议。

## 实施步骤

### 1. 真实 unified diff smoke 样例

新增一个最小端到端样例，覆盖“模型输出 unified diff JSON，Orchestrator 应用并验证”：

- 新增 `examples/task.omx-patch-unified-diff-smoke.json`。
- 新增本地可控 backend，例如 `examples/patch_unified_diff_backend.py`，模拟 OMX/Codex stdout 输出。
- 如本机 `omx exec` 稳定可用，再补一个真实 OMX backend 命令模板。
- 验证目标：修改 `.tmp/omx-real-smoke/calculator.py` 或独立临时样例文件，hard checks 通过。

验收：

- `python -m orchestrator.interfaces.cli.main --task examples/task.omx-patch-unified-diff-smoke.json --agent omx_patch --real-checks` 成功。
- run 状态为 `done`。
- `logs/agent.log` 记录 `op=unified_diff` 对应风险结果。

### 2. patches list 审计展示增强

让审批后的 patch 状态更直观，减少翻 JSON 的成本：

- `patches list` 增加展示 `post_apply_checks` 通过状态。
- `patches list` 增加展示 `post_apply_rerun.status`、`post_apply_rerun.run_id`。
- 对 applied/rejected/pending 三类状态保持兼容输出。

建议输出字段：

```text
patch=001-patch_coder.json status=applied checks_passed=True rerun_status=done rerun_run_id=run-...
```

验收：

- 已 apply 但未 rerun 的 patch 输出 `rerun_status=None`。
- `--rerun-checks` 后输出 `checks_passed=True/False`。
- `--rerun-task` 后输出 `rerun_status=done|halted`。

### 3. 失败诊断与错误分层

补齐 patch-only 常见失败的诊断信息：

- malformed patch JSON：记录原始 stdout 到 attempts 目录。
- `task_id` mismatch：错误信息包含 expected/actual。
- unified diff context mismatch：错误信息包含 path、expected、actual。
- post-apply validation halt：pending patch JSON 写入 `post_apply_rerun.reason`。

验收：

- 测试覆盖 malformed JSON、context mismatch、rerun hard check failed。
- CLI 输出保持简洁，但 JSON 产物可追溯。

### 4. 文档和演示脚本

补一份可以对外演示的最小命令序列：

- 生成 pending patch。
- `patches list` 查看风险。
- `patches apply --rerun-task` 审批应用并重跑验证闭环。
- 查看 `final_report.md` 与 pending patch JSON。

落点：

- 更新 `agent-protocol.md`。
- 可选新增 `docs/codex/v1/plans/自动循环进化编码智能体系统-demo-script.md`。

## 验证方式

每个子步骤完成后至少执行：

```text
python -m pytest -q tests/test_patch_agent.py
python -m pytest -q tests/test_cli_resume.py
python -m pytest -q
```

若新增真实 OMX smoke，则额外执行对应 task：

```text
python -m orchestrator.interfaces.cli.main --task examples/task.omx-patch-unified-diff-smoke.json --agent omx_patch --real-checks
```

## 风险与回滚

- 真实 OMX 输出不稳定：先用本地 backend 固化协议，再把真实 `omx exec` 作为可选 smoke。
- CLI 输出字段变多影响测试：保持旧字段不删除，只追加字段。
- 失败诊断写入过多：只保存必要 stdout/stderr 和结构化 reason，不保存无关大日志。
- unified diff 支持范围扩大过快：第三步仍限定单文件 hunk，多文件 diff 暂按多个 operation 表达。

## 建议执行顺序

1. 先做 `patches list` 审计展示增强。
2. 再补 unified diff smoke 样例。
3. 然后补失败诊断字段和测试。
4. 最后同步协议文档、status、task-control，并跑全量回归。

## 完成判定

- 全量测试通过。
- 至少一个 unified diff patch-only smoke 到 `done`。
- `patches list` 能直接展示 apply、checks、rerun-task 的核心审计状态。
- 文档中能按命令复现完整演示链路。
