# 自动循环进化编码智能体系统 Agent CLI 协议

## 1. 目标

本文档固化 Orchestrator 与外部 Agent Runtime（Codex CLI / OMX / 其他等价命令行智能体）之间的最小可执行协议。

协议目标：

- 让 Coder、Fixer、Reviewer 三类 Agent 能通过统一命令模板接入。
- 让 Orchestrator 只依赖退出码、stdout、stderr、prompt 文件和运行产物，不绑定某个具体 CLI 的内部实现。
- 让真实写代码能力可由 Codex/OMX 命令承载，同时保留 mock、shell、本地脚本的可测试性。

## 2. 角色职责

| 角色 | 必需性 | 输入 | 输出 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| Coder | 可选 | `coder_prompt.txt` | 修改工作区文件 | 首次实现任务。未配置时跳过，适合纯检查或演示任务。 |
| Fixer | 可选 | `fixer_prompt.txt`、`fix_reason.json` | 修改工作区文件 | 根据 Hard Check 或 Quality Gate 失败原因修复。未配置时跳过。 |
| Reviewer | 必需（真实审查阶段） | `reviewer_prompt.txt` | stdout 输出 `review.json` | 必须返回合法 JSON，Orchestrator 会做 schema 与 `task_id` 校验。 |

## 3. 命令模板

`task.json` 通过 `agent_commands` 配置三类命令：

```json
{
  "agent_mode": "codex",
  "agent_commands": {
    "coder": "codex exec --full-auto --cwd {worktree_path} --prompt-file {prompt_file}",
    "fixer": "codex exec --full-auto --cwd {worktree_path} --prompt-file {prompt_file}",
    "reviewer": "codex exec --full-auto --cwd {worktree_path} --prompt-file {prompt_file}"
  }
}
```

当前实现支持以下占位符：

| 占位符 | 含义 |
| :--- | :--- |
| `{task_id}` | 当前任务 ID |
| `{task_title}` | 当前任务标题 |
| `{task_json}` | 本次运行快照中的 `task.json` 路径 |
| `{run_dir}` | `.omx/runs/{run_id}` 运行目录 |
| `{attempt}` | 当前 attempt 序号 |
| `{attempt_dir}` | 当前 attempt 目录，例如 `.omx/runs/{run_id}/attempts/001` |
| `{prompt_file}` | 当前角色 prompt 文件路径 |
| `{reason_file}` | Fixer 失败原因 JSON 文件路径，非 Fixer 为空 |
| `{repair_prompt_file}` | 兼容 ShellAgent 的 Review JSON 修复提示文件，ExternalCommandAgent 默认不使用 |

说明：如果具体 CLI 不支持 `--prompt-file`，可以用 shell 包装脚本读取 `{prompt_file}` 后再调用真实 CLI。

## 4. Codex 模板

推荐模板：

```json
{
  "allowed_command_prefixes": ["codex", "python", "python -m pytest"],
  "agent_mode": "codex",
  "agent_commands": {
    "coder": "codex exec --full-auto --cwd . --prompt-file {prompt_file}",
    "fixer": "codex exec --full-auto --cwd . --prompt-file {prompt_file}",
    "reviewer": "codex exec --full-auto --cwd . --prompt-file {prompt_file}"
  }
}
```

如果 Codex CLI 的实际参数名称与模板不同，应优先使用包装脚本，保持 Orchestrator 侧协议稳定。例如：

```text
python scripts/run_external_agent.py --runtime codex --role reviewer --task-id {task_id} --prompt-file {prompt_file} --run-dir {run_dir}
```

包装脚本支持 dry-run，也支持通过 `--backend-command` 或环境变量转发到真实 Codex CLI：

```text
OMX_CODEX_REVIEWER_COMMAND="codex exec --full-auto --cwd {worktree} --prompt-file {prompt_file}"
python scripts/run_external_agent.py --runtime codex --role reviewer --task-id {task_id} --prompt-file {prompt_file} --run-dir {run_dir}
```

## 5. OMX 模板

推荐模板：

```json
{
  "allowed_command_prefixes": ["omx", "python", "python -m pytest"],
  "agent_mode": "omx",
  "agent_commands": {
    "coder": "omx run --role coder --task {task_id} --prompt-file {prompt_file} --run-dir {run_dir}",
    "fixer": "omx run --role fixer --task {task_id} --prompt-file {prompt_file} --reason-file {reason_file} --run-dir {run_dir}",
    "reviewer": "omx run --role reviewer --task {task_id} --prompt-file {prompt_file} --run-dir {run_dir}"
  }
}
```

OMX 若使用 `$ralph` 或 `$team`，建议由包装命令封装内部细节，对 Orchestrator 仍暴露同一套输入输出契约。

OMX 包装命令示例：

```text
python scripts/run_external_agent.py --runtime omx --role fixer --task-id {task_id} --prompt-file {prompt_file} --reason-file {reason_file} --run-dir {run_dir} --stdin-prompt
```

可通过 `OMX_OMX_FIXER_COMMAND` 环境变量或 `--backend-command` 指向真实 OMX 命令。

当前验证过的 `omx exec` 命令形态接近：

```text
omx exec --full-auto --skip-git-repo-check -C {worktree} - --output-last-message {output_last_message}
```

其中 `-` 表示从 stdin 读取 prompt。包装脚本使用 `--stdin-prompt` 读取 `{prompt_file}` 并传入 stdin，Reviewer 可通过 `--output-last-message` 指定文件回收最终 JSON。

## 6. Prompt 文件契约

Orchestrator 会在每个 attempt 下生成：

```text
.omx/runs/{run_id}/attempts/{attempt}/coder_prompt.txt
.omx/runs/{run_id}/attempts/{attempt}/fixer_prompt.txt
.omx/runs/{run_id}/attempts/{attempt}/reviewer_prompt.txt
.omx/runs/{run_id}/attempts/{attempt}/fix_reason.json
```

Agent 必须按 prompt 要求工作：

- Coder/Fixer 只修改 `worktree_path` 内文件。
- 不修改 `forbidden_paths`。
- 不进行超出任务描述的大规模重构。
- Reviewer 不修改文件，只输出审查 JSON。

## 7. stdout/stderr 契约

| 角色 | stdout | stderr |
| :--- | :--- | :--- |
| Coder | 可输出执行摘要，Orchestrator 仅记录，不解析 | 可输出诊断信息 |
| Fixer | 可输出修复摘要，Orchestrator 仅记录，不解析 | 可输出诊断信息 |
| Reviewer | 必须输出合法 JSON；允许 JSON 前后有少量非 JSON 文本，但不推荐 | 可输出诊断信息，不参与 JSON 解析 |

Reviewer 推荐只输出：

```json
{
  "schema_version": "1.0",
  "task_id": "当前 task.task_id",
  "pass": true,
  "confidence": 90,
  "summary": "审查结论",
  "issues": [],
  "blocking": false,
  "recommended_next_action": "pass"
}
```

`task_id` 必须等于当前任务的 `task_id`，否则 Orchestrator 会视为非法审查结果并触发 Review JSON retry。

## 8. 退出码契约

| 退出码 | 含义 | Orchestrator 行为 |
| :--- | :--- | :--- |
| `0` | Agent 命令成功完成 | 继续后续阶段 |
| `1-123` | Agent 命令失败 | 当前 attempt 失败，进入 fix/retry 或 halt |
| `124` | 命令超时 | 记录 timeout，进入 fix/retry 或 halt |
| 其他非 0 | 未分类失败 | 记录 stdout/stderr，进入 fix/retry 或 halt |

命令失败时，Orchestrator 会把命令、退出码、stdout、stderr 写入：

```text
.omx/runs/{run_id}/logs/agent.log
```

## 9. 安全与权限

外部 Agent 命令执行前必须通过 `SafetyPolicy.validate_command`：

- 命令不能匹配危险模式，例如递归删除、管道执行远程脚本、危险 SQL。
- 命令必须匹配 `task.allowed_command_prefixes`。
- `change_type=config` 默认提升为 `elevated`，但仍不能访问 `forbidden_paths`。

真实 Codex/OMX 接入时，需要在任务模板中显式加入命令前缀，例如 `codex` 或 `omx`。

## 10. 最小接入清单

接入新的真实 Agent CLI 时，至少完成：

1. 在 `task.json` 中配置 `agent_mode`、`agent_commands`、`allowed_command_prefixes`。
2. 确认 Coder/Fixer 会读取 `{prompt_file}` 并在 `worktree_path` 内修改文件。
3. 确认 Reviewer stdout 返回合法 `review.json`。
4. 确认非 0 退出码能被 Orchestrator 捕获。
5. 运行 `python -m pytest -q`。
6. 用模板任务跑一次 dry-run 或受控真实任务。

## 11. 包装脚本模式

`scripts/run_external_agent.py` 是推荐的稳定接入入口：

- `--dry-run`：不调用真实 CLI，只校验 prompt/reason 文件，并在 Reviewer 角色输出合法 `review.json`。
- `--stdin-prompt`：读取 `--prompt-file` 并通过 stdin 传给后端命令，适合 `omx exec ... -`。
- `--output-last-message`：从指定文件读取后端最终回复并输出给 Orchestrator，适合 `omx exec --output-last-message <file>`。
- `--backend-command`：本次调用临时指定真实后端命令模板。
- `OMX_CODEX_CODER_COMMAND`、`OMX_CODEX_FIXER_COMMAND`、`OMX_CODEX_REVIEWER_COMMAND`：Codex 角色级默认后端命令。
- `OMX_OMX_CODER_COMMAND`、`OMX_OMX_FIXER_COMMAND`、`OMX_OMX_REVIEWER_COMMAND`：OMX 角色级默认后端命令。

后端命令模板支持 `{runtime}`、`{role}`、`{task_id}`、`{prompt_file}`、`{reason_file}`、`{run_dir}`、`{worktree}`、`{output_last_message}`。

推荐先运行：

```text
python -m orchestrator.interfaces.cli.main --task examples/task.codex-wrapper-dry-run.json --real-checks --git-diff
```

确认 Orchestrator、包装脚本、Reviewer JSON 和 Quality Gate 链路全部通过后，再切到真实后端命令。

## 12. Windows OMX Smoke 结论

已在 `.tmp/omx-real-smoke/` 做过受控真实 OMX 调用验证：

- Orchestrator 可以通过 `OmxAgent` 调用 `scripts/run_external_agent.py`。
- wrapper 可以读取 prompt 文件，并通过 stdin 调用 `omx exec --full-auto --skip-git-repo-check -C {worktree} -`。
- Hard Check、Fixer retry、heartbeat、agent log、final report 均能生成。
- 在当前 Windows 环境下，真实 `omx exec` 内部 Codex 执行 shell/patch 时遇到 `CreateProcessWithLogonW failed: 1385`，导致 Agent 无法实际修改临时仓库文件。

因此，当前结论是“真实 OMX 调用链路已接通，但真实写操作受 Windows 执行沙箱限制”。后续生产验证建议优先选择：

1. 在 WSL/Linux 环境验证 `omx exec` 写操作。
2. 或为 Windows 配置可用的 Codex/OMX 执行策略，确保 Agent 子进程能启动 shell 与 patch 工具。
3. 或在 wrapper 后端接入更受控的本地执行器，只让模型输出 patch，再由 Orchestrator 审批后应用。

## 13. Windows 兼容 Patch 模式

为绕开 Windows 下真实 `omx exec` 直接写文件时的 shell/patch 子进程限制，新增 `omx_patch` Agent 模式。

该模式的职责分工：

- Agent 只输出 patch JSON，不直接修改文件。
- Orchestrator 校验 patch JSON 的 schema、`task_id` 和操作列表。
- Orchestrator 使用 `SafetyPolicy.validate_write_path` 校验目标路径。
- Orchestrator 仅支持受控 patch 操作，当前支持 `replace_text`、`create_file`、`delete_file`。
- Hard Check、Reviewer、Quality Gate 仍沿用原闭环。

Patch JSON 示例：

```json
{
  "schema_version": "1.0",
  "task_id": "task-omx-patch-smoke-001",
  "summary": "Replace subtraction with addition.",
  "operations": [
    {
      "op": "replace_text",
      "path": "calculator.py",
      "old": "return a - b",
      "new": "return a + b"
    },
    {
      "op": "create_file",
      "path": "new_file.py",
      "content": "VALUE = 1\n",
      "overwrite": false
    },
    {
      "op": "delete_file",
      "path": "old_file.py",
      "must_exist": true
    }
  ]
}
```

已验证 smoke：

```text
python -m orchestrator.interfaces.cli.main --task examples/task.omx-patch-smoke.json --agent omx_patch --real-checks
```

验证结果：

- run_id: `run-20260521-162852-762772`
- status: `done`
- 受控修改 `.tmp/omx-real-smoke/calculator.py`
- 全量测试：`47 passed`

后续可以把 `examples/patch_smoke_backend.py` 替换为真实 `omx exec` patch-only prompt 后端，让模型输出 patch JSON，仍由 Orchestrator 负责应用。

## 14. 真实 OMX Patch-only 后端验证

已将 patch 后端替换为真实 `omx exec`，并保持“模型只输出 patch JSON，Orchestrator 应用 patch”的职责边界。

关键改动：

- Patch prompt 注入 `allowed_paths` 对应文件快照，模型无需启动 shell 也能看到源码。
- 新增 `{attempt_dir}` 命令占位符，用于稳定写入 `--output-last-message`。
- `examples/task.omx-patch-real-smoke.json` 使用 wrapper 调用真实 `omx exec`。

真实后端命令：

```text
OMX_OMX_CODER_COMMAND='omx exec --full-auto --skip-git-repo-check -C "{worktree}" - --output-last-message {output_last_message}'
OMX_OMX_FIXER_COMMAND='omx exec --full-auto --skip-git-repo-check -C "{worktree}" - --output-last-message {output_last_message}'
```

验证结果：

- run_id: `run-20260521-163411-124400`
- status: `done`
- last message: `.omx/runs/run-20260521-163411-124400/attempts/001/omx_patch_coder_last_message.txt`
- patch 由真实 `omx exec` 生成，Orchestrator 受控应用。
- 全量测试：`48 passed`

## 15. Patch Schema 扩展与风险字段

Patch schema 第二版补充文件级操作：

- `replace_text`：在已有文件中替换精确文本。
- `create_file`：创建新文件，默认不覆盖已有文件。
- `delete_file`：删除已有文件，默认要求目标存在。

Patch 应用完成后，`OmxPatchAgent` 会在 `logs/agent.log` 记录：

- `changed_files`
- `created_files`
- `deleted_files`
- `risk_score`
- `risk_reasons`

当前风险评分为轻量规则：

- 初始分 10。
- 修改文件数超过 5 后，每多 1 个文件扣 1 分。
- 每删除 1 个文件扣 2 分，并记录 `files_deleted`。
- 创建文件超过 2 个后开始扣分，并记录 `files_created`。

验证结果：

- 真实 OMX patch-only smoke：`run-20260521-164502-235168`
- status: `done`
- agent log 中记录 `risk_score=10`
- 全量测试：`50 passed`

## 16. Patch 人工审批开关

任务可配置 patch 自动应用策略：

```json
{
  "patch_auto_apply": true,
  "patch_approval_risk_threshold": 7,
  "patch_require_approval_on_delete": true
}
```

判定规则：

- `patch_auto_apply=false`：所有 patch 都只落盘待审批。
- `risk_score < patch_approval_risk_threshold`：只落盘待审批。
- `patch_require_approval_on_delete=true` 且包含 `delete_file`：只落盘待审批。

待审批 patch 会写入：

```text
.omx/runs/{run_id}/pending-patches/{attempt}-{role}.json
```

文件内容包含：

- patch plan
- risk result
- run/task/attempt/role
- status: `pending`

已验证审批 smoke：

- task: `examples/task.omx-patch-approval-smoke.json`
- run_id: `run-20260521-165047-273285`
- status: `halted`
- pending patch: `.omx/runs/run-20260521-165047-273285/pending-patches/001-patch_coder.json`
- 目标文件 `old_file.py` 未被删除。
- 全量测试：`52 passed`

## 17. Pending Patch 审批 CLI

新增 `patches` CLI：

```text
python -m orchestrator.interfaces.cli.main patches list [--run-id <run_id>]
python -m orchestrator.interfaces.cli.main patches apply --run-id <run_id> --patch <patch.json> [--reviewer <name>] [--note <text>] [--rerun-checks]
python -m orchestrator.interfaces.cli.main patches reject --run-id <run_id> --patch <patch.json> [--reviewer <name>] [--note <text>]
```

行为：

- `list` 展示 pending/applied/rejected patch 的 run、task、status、risk、操作类型和文件列表。
- `apply` 重新加载 run 快照中的 `task.json`，再次执行路径安全校验后应用 patch，并把 pending patch 状态改为 `applied`。
- `apply --rerun-checks` 会在应用后重跑 `task.check_commands`，并把 `post_apply_checks` 写回 patch JSON。
- `reject` 不修改文件，只把状态改为 `rejected` 并记录 reviewer/note。

已验证：

- run_id: `run-20260521-170009-452873`
- `patches list` 能看到 `001-patch_coder.json`
- `patches apply` 后状态为 `applied`
- `.tmp/omx-real-smoke/old_file.py` 被删除
- 全量测试：`53 passed`

审批后验证 smoke：

- run_id: `run-20260521-170424-438800`
- 命令：`patches apply --rerun-checks`
- patch JSON 写入 `post_apply_checks`
- CLI 输出 `checks_passed=True`
# Patch 协议增量：unified diff 与 rerun-task

本节补充当前实现中的 patch-only 协议增量，适用于 `agent_mode=omx_patch`。

## Unified Diff / Patch JSON

`omx_patch` 支持两类受控补丁表达：

- 结构化文件操作：`replace_text`、`create_file`、`delete_file`。
- 单文件 `unified_diff` 操作：由模型输出标准 hunk，Orchestrator 负责校验上下文并应用。

`unified_diff` 示例：

```json
{
  "schema_version": "1.0",
  "task_id": "task-001",
  "summary": "Update calculator implementation.",
  "operations": [
    {
      "op": "unified_diff",
      "path": "calculator.py",
      "diff": "--- a/calculator.py\n+++ b/calculator.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"
    }
  ]
}
```

约束：

- `path` 必须是相对 `worktree_path` 的路径，最终会解析到绝对路径并经过 `SafetyPolicy.validate_write_path`。
- 当前 `unified_diff` 只支持单文件 hunk；多文件变更应拆成多个 operation。
- Orchestrator 会校验 context 行和删除行是否与当前文件一致；不一致时拒绝应用。
- `dry_run=True` 会完整解析和校验补丁，但不修改文件，用于审批前风险判断。

## patches apply --rerun-task

`patches apply --rerun-task` 的语义是“审批应用补丁后重新跑任务验证闭环”，不是再次调用 coder/fixer 生成补丁。

执行顺序：

1. 重新加载原 run 快照中的 `task.json`。
2. 应用 pending patch，并把 patch 状态写为 `applied`。
3. 创建新的 post-apply validation run。
4. 执行 hard checks。
5. hard checks 通过后执行 Reviewer，并沿用 malformed JSON retry 逻辑。
6. 执行 Quality Gate。
7. 将新 run 的 `run_id/status/phase/attempt/run_dir` 写回 pending patch JSON 的 `post_apply_rerun`。

CLI：

```text
python -m orchestrator.interfaces.cli.main patches apply --run-id <run_id> --patch <patch.json> --rerun-task
```

输出会包含：

```text
rerun_run_id=run-... rerun_status=done|halted
```

该模式会生成独立的 `.omx/runs/{rerun_run_id}/final_report.md`、`hard_checks.json`、`review.json` 和 `quality_report.json`，便于审计。

## Patch 失败诊断产物

Patch-only 模式在失败时会保留最小诊断材料，便于复盘模型输出和 Orchestrator 校验结果。

Coder/Fixer patch 输出失败时，attempt 目录会写入：

```text
.omx/runs/{run_id}/attempts/{attempt}/{role}_patch_raw_output.txt
.omx/runs/{run_id}/attempts/{attempt}/{role}_patch_diagnostics.json
```

`patch_diagnostics.json` 包含：

- `role`：`patch_coder` 或 `patch_fixer`
- `error_type`：例如 `MalformedReview`、`PatchApplyError`
- `error`：具体失败原因
- `raw_output_path`：原始 stdout 文件路径
- `raw_output_preview`：最多前 1000 字符的输出预览

典型失败：

- patch JSON 非法：`error_type=MalformedReview`
- `task_id` 不一致：`error` 包含 expected/actual
- unified diff context mismatch：`error` 包含 path、expected、actual
- unified diff 无 hunk：直接拒绝，避免静默假成功

`patches apply --rerun-task` 失败时，pending patch JSON 的 `post_apply_rerun.reason` 会记录验证失败原因，例如 `test failed`。CLI 会同步输出 `rerun_reason=...`。
