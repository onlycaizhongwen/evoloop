# 真实 OMX/Codex Unified Diff Smoke 模板

## 定位

这是环境依赖型验证项，用于在本机真实 OMX/Codex CLI 可用时，验证“真实模型输出 unified diff patch JSON，Orchestrator 受控应用并完成验证闭环”。

它不纳入默认 pytest，也不阻塞第三步收口。

## 已提供模板

- `examples/task.omx-patch-unified-diff-real-smoke.json`
- `examples/task.codex-patch-unified-diff-real-smoke.json`

两个模板都使用：

- `agent_mode=omx_patch`
- `.tmp/omx-unified-diff-smoke` 作为 worktree
- `calculator.py` 作为唯一允许修改文件
- `python -m pytest -q` 作为 hard check

## 重置 Smoke 工作区

```powershell
@'
def add(a, b):
    return a - b
'@ | Set-Content -Path .tmp\omx-unified-diff-smoke\calculator.py -Encoding utf8NoBOM
```

注意：不要使用会写入 BOM 的编码方式。BOM 会导致 unified diff context mismatch，这是预期保护。

## OMX 后端命令示例

PowerShell：

```powershell
$env:OMX_OMX_CODER_COMMAND='omx exec --full-auto --skip-git-repo-check -C "{worktree}" - --output-last-message {output_last_message}'
$env:OMX_OMX_FIXER_COMMAND='omx exec --full-auto --skip-git-repo-check -C "{worktree}" - --output-last-message {output_last_message}'
```

执行：

```powershell
python -m orchestrator.interfaces.cli.main --task examples/task.omx-patch-unified-diff-real-smoke.json --agent omx_patch --real-checks
```

预期：

```text
run_id=run-... status=done phase=done
```

## Codex 后端命令示例

Codex CLI 参数可能随本机安装版本变化；建议优先用 wrapper 转发，并把 prompt 通过 stdin 传入。

示例：

```powershell
$env:OMX_CODEX_CODER_COMMAND='codex exec --full-auto --skip-git-repo-check -C "{worktree}" - --output-last-message {output_last_message}'
$env:OMX_CODEX_FIXER_COMMAND='codex exec --full-auto --skip-git-repo-check -C "{worktree}" - --output-last-message {output_last_message}'
```

执行：

```powershell
python -m orchestrator.interfaces.cli.main --task examples/task.codex-patch-unified-diff-real-smoke.json --agent omx_patch --real-checks
```

如果本机 Codex CLI 不支持上述参数，需要调整环境变量中的 backend command，但 Orchestrator 侧 task 模板无需改动。

## 模型输出要求

真实 OMX/Codex 后端必须只输出 patch JSON：

```json
{
  "schema_version": "1.0",
  "task_id": "当前 task_id",
  "summary": "Fix calculator.add with unified diff.",
  "operations": [
    {
      "op": "unified_diff",
      "path": "calculator.py",
      "diff": "--- a/calculator.py\n+++ b/calculator.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"
    }
  ]
}
```

## 排错路径

失败时优先查看：

```text
.omx/runs/{run_id}/final_report.md
.omx/runs/{run_id}/logs/agent.log
.omx/runs/{run_id}/logs/phase.log
.omx/runs/{run_id}/attempts/001/patch_coder_patch_raw_output.txt
.omx/runs/{run_id}/attempts/001/patch_coder_patch_diagnostics.json
```

常见原因：

- 模型输出了 Markdown 包裹或解释文字，导致 patch JSON malformed。
- `task_id` 与当前任务不一致。
- unified diff context 与当前文件不一致。
- 本机 OMX/Codex CLI 不支持示例 backend command 参数。
- Windows 环境的执行沙箱限制导致真实 CLI 内部子进程失败。

## 收口标准

满足以下任一项即可认为真实 smoke 通过：

- OMX 模板运行到 `status=done`。
- Codex 模板运行到 `status=done`。

若两者均受本机环境限制失败，不影响默认回归；保留 diagnostics 即可用于后续环境修复。
