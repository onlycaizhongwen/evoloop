# Docker Sandbox Runner 设计方案

## 1. 目标

在现有 Orchestrator 架构中引入 Docker 沙箱执行层，把测试、lint、typecheck、Codex/OMX 后端命令等高风险或环境敏感操作放入容器内执行。

核心目标：

- 降低命令误伤宿主机的风险。
- 固化执行环境，减少 Windows、tmux、依赖版本差异造成的失败。
- 为后续 `omx team`、多 Agent、并行 worktree 提供隔离边界。
- 保持 Orchestrator 仍是最终安全与质量裁决者。

非目标：

- 不让容器直接绕过 Orchestrator 修改宿主项目。
- 不把 Docker 当成权限系统的唯一防线。
- 第一阶段不实现自动构建任意项目镜像。
- 第一阶段不自动访问生产网络、数据库、密钥或 Docker socket。

## 2. 当前架构位置

当前执行链路：

```text
RunTaskUseCase
  -> Agent Adapter / ShellCheckRunner
  -> SafeCommandRunner
  -> host shell command
```

目标链路：

```text
RunTaskUseCase
  -> Agent Adapter / ShellCheckRunner
  -> SafeCommandRunner
  -> CommandRunner backend
       -> LocalCommandRunner
       -> DockerSandboxRunner
```

`SafeCommandRunner` 继续负责：

- 命令 allowlist 校验。
- forbidden command 拦截。
- timeout。
- heartbeat。
- stdout/stderr 采集。
- exit code 标准化。

`DockerSandboxRunner` 只负责：

- 构造 `docker run` 命令。
- 挂载 worktree、run artifacts、cache。
- 设置容器用户、网络、资源限制。
- 把容器退出码和输出映射回 `CommandExecutionResult`。

## 3. 关键原则

### 3.1 Orchestrator 仍是最终裁决者

Docker 只是执行隔离，不替代以下逻辑：

- `SafetyPolicy.validate_command`
- `SafetyPolicy.validate_write_path`
- `PatchValidator`
- `PatchApplier`
- `PatchApprovalPolicy`
- `QualityGate`
- `patches apply --rerun-task`

### 3.2 patch apply 默认不进容器

当前推荐保持：

```text
Codex/OMX in container -> 输出 patch JSON
Orchestrator on host -> 校验 patch -> pending approval -> apply 到 host worktree
```

理由：

- patch 应用是系统内最敏感的写操作。
- 宿主侧已有 allowed_paths、forbidden_paths、dry-run、审批、风险评分。
- 如果容器直接写 worktree，会让安全责任边界变模糊。

### 3.3 第一阶段优先 Docker 化 hard checks

最小可落地顺序：

1. `pytest` / `lint` / `typecheck` 在容器内执行。
2. `run_external_agent.py` / `run_omx_team_patch.py` 可选进入容器。
3. Web UI 增加执行后端选择。
4. 再评估 per-agent / per-team worker 容器隔离。

## 4. task.json 扩展

建议新增字段：

```json
{
  "execution_backend": "local",
  "sandbox": {
    "image": "auto-evolution-python:3.12",
    "network": "none",
    "worktree_mount": "readonly",
    "run_mount": "rw",
    "cache_mount": "rw",
    "memory_limit": "2g",
    "cpu_limit": 2,
    "user": "nonroot",
    "environment": {},
    "container_workdir": "/worktree"
  }
}
```

字段说明：

| 字段 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `execution_backend` | `local` | `local | docker` |
| `sandbox.image` | 按项目默认 | 容器镜像 |
| `sandbox.network` | `none` | `none | bridge`，默认禁止网络 |
| `sandbox.worktree_mount` | `readonly` | `readonly | rw` |
| `sandbox.run_mount` | `rw` | `.omx/runs/{run_id}` artifact 挂载权限 |
| `sandbox.cache_mount` | `rw` | pip/npm/uv 等缓存，可选 |
| `sandbox.memory_limit` | `2g` | Docker `--memory` |
| `sandbox.cpu_limit` | `2` | Docker `--cpus` |
| `sandbox.user` | `nonroot` | 默认容器内非 root 用户 |
| `sandbox.environment` | `{}` | 显式允许传入的环境变量 |
| `sandbox.container_workdir` | `/worktree` | 容器内命令工作目录 |

第一阶段可只实现：

- `execution_backend`
- `sandbox.image`
- `sandbox.network`
- `sandbox.worktree_mount`
- `sandbox.memory_limit`
- `sandbox.cpu_limit`

## 5. 挂载设计

推荐容器内路径：

```text
/worktree   -> task.worktree_path
/run        -> .omx/runs/{run_id}
/cache      -> .omx/cache/docker/{image-or-project-key}
```

### Hard checks

```text
/worktree: readonly
/run: rw
/cache: rw
network: none
```

适用：

- `python -m pytest`
- `ruff check`
- `mypy`
- `npm test`
- `pnpm test`

### Agent patch generation

```text
/worktree: readonly
/run: rw
/cache: rw
network: bridge 或按需
```

适用：

- `codex exec --sandbox read-only`
- `omx exec --sandbox read-only`
- `scripts/run_omx_team_patch.py`

约束：

- Agent 只读取 `/worktree`。
- Agent 只能写 `/run` 下的 `team_result.json`、last message、logs。
- 最终 patch apply 仍在宿主 Orchestrator 执行。

### 禁止挂载

默认禁止：

- `/var/run/docker.sock`
- 用户 home 目录整体挂载。
- SSH key 目录。
- `.env`、secrets、生产配置。
- 宿主根目录。

## 6. 命令映射

宿主命令：

```text
python -m pytest -q
```

容器命令：

```text
docker run --rm \
  --network none \
  --memory 2g \
  --cpus 2 \
  --user 1000:1000 \
  -v "<worktree>:/worktree:ro" \
  -v "<run_dir>:/run:rw" \
  -w /worktree \
  auto-evolution-python:3.12 \
  python -m pytest -q
```

Windows 路径注意事项：

- Docker CLI 接收宿主绝对路径，内部统一映射到 `/worktree`。
- Orchestrator 日志中同时记录 host path 和 container path。
- Prompt 中尽量使用容器内路径，避免模型混淆 Windows 中文路径。

## 7. Runner 接口建议

建议拆出协议：

```python
class CommandRunnerPort(Protocol):
    def run(
        self,
        task: TaskConfig,
        command: str,
        phase: str,
        state: RunState | None = None,
        cwd: Path | None = None,
    ) -> CommandExecutionResult:
        ...
```

实现：

```text
orchestrator/infrastructure/command/
  safe_command_runner.py
  local_command_runner.py
  docker_sandbox_runner.py
```

`SafeCommandRunner` 改为组合：

```text
SafeCommandRunner
  -> SafetyPolicy.validate_command
  -> runner = runner_factory(task.execution_backend)
  -> runner.run(...)
```

## 8. 权限策略

### 默认权限矩阵

| Phase | worktree | run artifacts | network | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| hard_checks | ro | rw | none | 第一阶段优先落地 |
| reviewer | ro | rw | none 或按需 | 如果 reviewer 只本地推理，可禁网 |
| patch_coder | ro | rw | 按需 | 输出 patch JSON，不写 worktree |
| patch_fixer | ro | rw | 按需 | 输出 fix patch JSON |
| patch_apply | host controlled | host controlled | none | 不进容器 |
| git_diff | host controlled | rw | none | 可保持宿主执行 |

### 网络

默认 `network=none`。

允许开启网络的场景：

- 调用外部模型 API。
- 首次安装依赖。
- 明确需要下载包。

开启网络时必须记录：

```text
reason=network_required
phase=<phase>
image=<image>
command=<command>
```

### 环境变量

默认不透传宿主环境变量。

只允许显式白名单：

- `OPENAI_API_KEY`
- `HTTPS_PROXY`
- `HTTP_PROXY`
- `NO_PROXY`
- 用户配置的模型网关变量

敏感变量不得写入日志，只记录变量名。

## 9. 失败恢复

Docker 失败映射：

| 场景 | exit_code | Orchestrator 行为 |
| :--- | ---: | :--- |
| Docker 未安装 | 127 | halt，提示安装 Docker |
| Docker daemon 未启动 | 125 | halt，提示启动 Docker |
| 镜像不存在 | 125 | halt 或进入 image build 流程 |
| 容器命令失败 | 原始退出码 | hard check failed 或 agent failed |
| Orchestrator timeout | 124 | kill container，进入 retry/halt |
| OOM killed | 137 | halt 或降低并发/内存 |
| 网络被禁止导致失败 | 原始退出码 | 诊断提示 `network=none` |

容器超时时必须：

- 停止容器。
- 清理同名临时容器。
- 写入 `logs/docker_sandbox.json`。
- 保留 stdout/stderr preview。

## 10. 日志与审计

每次容器执行写入：

```text
.omx/runs/{run_id}/logs/docker_sandbox.jsonl
```

建议字段：

```json
{
  "phase": "check:test",
  "image": "auto-evolution-python:3.12",
  "command": "python -m pytest -q",
  "container_command": "docker run ...",
  "worktree_host_path": "D:/project/worktree",
  "worktree_container_path": "/worktree",
  "network": "none",
  "worktree_mount": "readonly",
  "exit_code": 0,
  "duration_seconds": 12.4,
  "timed_out": false
}
```

日志中不得记录：

- API key 值。
- token。
- secret 文件内容。
- `.env` 内容。

## 11. Web UI 影响

建议新增字段：

- Execution backend: `local | docker`
- Docker image
- Network: `none | bridge`
- Worktree mount: `readonly | rw`
- Memory limit
- CPU limit

默认：

```text
execution_backend=local
```

当选择 Docker 时，Web 提交前校验：

- Docker image 非空。
- memory/cpu 格式合法。
- network 默认 none。
- 如果 `worktree_mount=rw`，必须显示风险提示。

## 12. 与 OMX Team 的关系

当前真实 `omx team` 在本机失败：

```text
Error: Team mode requires tmux
```

Docker/WSL/Linux 沙箱可以作为后续解决路径：

```text
Host Orchestrator
  -> DockerSandboxRunner
  -> Linux container with tmux + omx + codex
  -> omx team
  -> team_result.json
  -> Host Orchestrator validates and applies patch
```

注意：

- team worker 不应直接写宿主 worktree。
- 容器内 team 只能写 `/run/team_result.json`。
- 如果需要多 worker worktree，应使用容器内临时 worktree，不直接映射宿主真实项目为 rw。

## 13. 第一阶段验收标准

第一阶段只实现 Docker hard checks。

验收标准：

- `TaskConfig` 支持 `execution_backend=docker` 与最小 `sandbox` 配置。
- `ShellCheckRunner` 可通过 Docker 跑 `python -m pytest -q`。
- Docker 未安装时返回可读 halt 原因。
- timeout 能停止容器并返回 `exit_code=124`。
- `logs/docker_sandbox.jsonl` 有完整执行记录。
- 默认 local 行为不变。
- 全量测试通过。

建议新增测试：

- `test_docker_runner_builds_expected_command`
- `test_docker_runner_maps_worktree_readonly`
- `test_docker_runner_maps_timeout_to_124`
- `test_safe_command_runner_keeps_local_default`
- `test_task_loader_parses_sandbox_config`

环境依赖 smoke：

```text
python scripts/run_docker_hard_check_smoke.py
```

该 smoke 可创建 `.tmp/docker-hard-check-smoke`，容器内运行 `python -m pytest -q`，成功后报告 run_id 与 Docker 日志路径。

## 14. 推荐实施顺序

1. 增加 `SandboxConfig` 与 `ExecutionBackend` 枚举，保持默认 `local`。
2. 拆出 `LocalCommandRunner`，让现有行为保持不变。
3. 新增 `DockerSandboxRunner`，先只支持 hard checks。
4. 增加 Docker 日志。
5. 增加 CLI smoke。
6. Web UI 增加可选 Docker backend。
7. 再评估把 Codex/OMX patch generation 放进 Docker。
8. 最后评估 `omx team` 在 Linux/tmux 容器内运行。

## 15. 结论

Docker 沙箱方案值得采纳，但应作为执行层增强，而不是替代 Orchestrator 安全模型。

推荐第一阶段只做：

```text
Hard checks in Docker
Patch generation remains patch-only
Patch apply remains host Orchestrator controlled
Web default remains local
```

这样可以在不破坏现有 `87 passed` 稳定基线的前提下，把系统安全性和环境可复现性向前推进一大步。

## 16. 第一阶段实现记录

当前已完成第一阶段的基础代码切分：

- 新增 `ExecutionBackend` 枚举，支持 `local | docker`。
- 新增 `SandboxConfig`，支持镜像、网络、worktree 挂载、资源限制、用户、环境变量和容器工作目录。
- `TaskConfig` 默认保持 `execution_backend=local`，因此现有 CLI/Web 行为不变。
- 新增 `CommandExecutionResult` 公共结果模型。
- 新增 `LocalCommandRunner`，承接原宿主 shell 执行逻辑。
- 新增 `DockerSandboxRunner`，可构造并执行 `docker run` 命令，挂载 `/worktree`、`/run`、`/cache`，并写入 `logs/docker_sandbox.jsonl`。
- `SafeCommandRunner` 继续先做 `SafetyPolicy.validate_command`，再按 `task.execution_backend` 分发到 local 或 docker runner。

本阶段验证：

```text
python -m py_compile orchestrator/domain/enums.py orchestrator/domain/models/task.py orchestrator/infrastructure/command/safe_command_runner.py orchestrator/infrastructure/command/local_command_runner.py orchestrator/infrastructure/command/docker_sandbox_runner.py

python -m pytest -q tests/test_command_safety_and_heartbeat.py tests/test_domain_services.py
16 passed

python -m pytest -q
91 passed
```

## 18. Web UI Optional Docker Backend 记录

本轮已把 Docker backend 暴露为 Web UI 的可选执行设置，默认行为仍保持 `local`。

已落地行为：
- 首页新建任务表单增加 `execution_backend=local|docker`。
- 表单增加 Docker sandbox 基础字段：`sandbox_image`、`sandbox_network`、`sandbox_worktree_mount`、`sandbox_memory_limit`、`sandbox_cpu_limit`。
- Web 生成的 task JSON 会写入 `execution_backend` 与 `sandbox` 配置。
- 默认提交不传 Docker 字段时仍生成 `execution_backend=local`。
- 选择 Docker 时执行提交前校验：image 非空、network 仅允许 `none|bridge`、worktree mount 仅允许 `readonly|rw`、memory/cpu 使用基础合法格式。
- 当前 Web UI 第一阶段强制 Docker worktree `readonly`，拒绝 `rw`，避免容器直接写宿主 worktree。

安全边界：
- Docker 仍只是执行隔离层。
- patch apply 仍由宿主 Orchestrator 控制。
- Web UI 不授予容器直接写宿主 worktree 的能力。
- 默认 local 不变，避免破坏现有 Windows/本地闭环体验。

验证结果：
```text
python -m py_compile orchestrator/interfaces/web/main.py
passed

python -m pytest -q tests/test_web_ui.py
18 passed

python -m pytest -q
95 passed
```

下一步建议：
- 增加真实 Web 提交 Docker hard-check 端到端 smoke，确认浏览器提交的 Docker task 能进入 `DockerSandboxRunner` 并成功写入 `logs/docker_sandbox.jsonl`。
- 后续再评估把 Codex/OMX patch generation 也放入 Docker；patch apply 继续保持宿主受控。

## 19. Web Docker Hard Check Smoke 记录

已新增环境依赖型 smoke：
```text
scripts/run_web_docker_hard_check_smoke.py
```

该 smoke 不 mock Web 后台执行，而是通过 FastAPI `TestClient` 提交真实 `/tasks/run` 表单：
- `execution_backend=docker`
- `sandbox_image=python:3.12-slim`
- `sandbox_network=none`
- `sandbox_worktree_mount=readonly`
- `check_command=python -m unittest -q`
- `agent_mode=mock`
- `real_checks=on`

验证链路：
```text
Web form submission
  -> .omx/web-tasks/*.json
  -> Web Job / SQLite
  -> RunTaskUseCase
  -> ShellCheckRunner
  -> SafeCommandRunner
  -> DockerSandboxRunner
  -> logs/docker_sandbox.jsonl
  -> review / quality gate
  -> Web Job done
```

本机真实验证结果：
```text
python scripts/run_web_docker_hard_check_smoke.py
job_status=done
run_id=run-20260525-151613-420567
logs/docker_sandbox.jsonl_exists=True
docker_log_last=... "image": "python:3.12-slim" ... "network": "none" ... "worktree_mount": "readonly" ... "exit_code": 0 ...
quality_score=100 quality_passed=True
```

回归策略：
- 普通 pytest 只编译 smoke 脚本，避免无 Docker 环境阻断开发。
- 真实 Docker/Web 端到端验证通过手工运行 `python scripts/run_web_docker_hard_check_smoke.py` 完成。

## 20. Docker Agent Patch Generation 记录

已完成最小可行验证：OMX/Codex patch generation 可以选择进入 Docker，patch apply 仍由宿主 Orchestrator 负责。

关键实现：
- `AgentPromptBuilder.render_command` 在 `execution_backend=docker` 时会把 run artifact 路径映射为容器路径：
  - `{run_dir}` -> `/run`
  - `{attempt_dir}` -> `/run/attempts/{attempt}`
  - `{task_json}` -> `/run/task.json`
  - `{prompt_file}` -> `/run/attempts/{attempt}/{role}_prompt.txt`
  - `{reason_file}` -> `/run/attempts/{attempt}/fix_reason.json`
  - `{worktree}` -> `/worktree`
- `execution_backend=local` 时继续渲染宿主绝对路径，旧行为不变。
- Docker runner 继续挂载：
  - worktree -> `/worktree:ro`
  - run artifacts -> `/run:rw`
  - cache -> `/cache:rw`

新增环境依赖型 smoke：
```text
scripts/run_docker_agent_patch_smoke.py
```

验证链路：
```text
RunTaskUseCase
  -> OmxTeamPatchAgent
  -> DockerSandboxRunner
  -> container reads /run/attempts/001/team_prompt.txt
  -> container prints team_result JSON
  -> host Orchestrator validates patch_plan
  -> host Orchestrator applies patch to worktree
  -> DockerSandboxRunner runs hard check
  -> Quality Gate done
```

本机真实验证结果：
```text
python scripts/run_docker_agent_patch_smoke.py
run_id=run-20260525-165757-265904 status=done phase=done
docker_agent_log=... "phase": "agent:omx_team_patch:team" ... "command": "python /worktree/docker_team_backend.py ... /run/attempts/001/team_prompt.txt" ... "exit_code": 0 ...
docker_check_log=... "phase": "check:test" ... "command": "python -m unittest -q" ... "exit_code": 0 ...
calculator_fixed=True
```

安全结论：
- 容器内 agent 只读 `/worktree`，不能直接修改宿主 worktree。
- 容器内 agent 只能通过 stdout 返回 `team_result` / patch JSON。
- patch 校验、审批策略、patch apply、hard check、review reuse、Quality Gate 仍在宿主 Orchestrator。

下一步建议：
- Web UI 增加“Agent generation in Docker”说明或高级选项，但默认仍保持 local。
- 若要运行真实 Codex/OMX CLI in Docker，需要单独设计镜像构建、凭据注入白名单、网络策略和日志脱敏。

## 21. Web UI Docker Agent Guardrail 记录

Web UI 已增加 Docker 命令路径护栏。该能力不是把 Docker agent 默认打开，而是在用户选择 `execution_backend=docker` 后，防止明显无法在容器内运行或容易误伤宿主的命令进入任务。

校验规则：
- 仅在 `execution_backend=docker` 时启用。
- 拒绝 Windows 宿主绝对路径，例如 `D:\tools\backend.py`。
- 拒绝非白名单容器绝对路径。
- 允许容器内路径：
  - `/worktree`
  - `/run`
  - `/cache`
- 允许 Orchestrator 占位符：
  - `{prompt_file}`
  - `{reason_file}`
  - `{run_dir}`
  - `{attempt_dir}`
  - `{task_json}`
  - `{worktree}`

页面提示：
```text
Docker commands should use /worktree, /run, /cache, or placeholders like {prompt_file}; host absolute paths are rejected.
```

验证结果：
```text
python -m py_compile orchestrator/interfaces/web/main.py
passed

python -m pytest -q tests/test_web_ui.py
21 passed
```

安全结论：
- Web 的 Docker 模式现在可以承载容器内 agent 命令，但会阻止最常见的宿主路径误配置。
- `local` 模式不受影响，仍可使用宿主绝对命令。
- patch apply 仍保持宿主 Orchestrator 受控。

尚未完成：

- 尚未新增真实 Docker hard-check smoke。
- 尚未在 Web UI 暴露 Docker backend 选择。
- 尚未把 `ShellCheckRunner` 按 phase 强制限制为 Docker hard checks；当前是通过 `task.execution_backend=docker` 统一 opt-in。
- 尚未处理 Docker image 自动构建或缺失镜像拉取策略。

下一步建议：

1. 新增 `scripts/run_docker_hard_check_smoke.py`，用临时项目验证容器内 `python -m pytest -q`。
2. 若本机 Docker 可用，再新增环境依赖型测试或 smoke 文档记录。
3. Web UI 增加可选 Docker backend 字段，但默认继续 local。

## 17. Docker Hard Check Smoke 记录

已新增环境依赖型 smoke：

```text
scripts/run_docker_hard_check_smoke.py
examples/task.docker-hard-check-smoke.json
```

Smoke 行为：

- 创建 `.tmp/docker-hard-check-smoke` 临时 Python 项目。
- 生成 `execution_backend=docker` 的任务配置。
- 通过 CLI `--real-checks` 触发 `ShellCheckRunner`。
- Docker runner 挂载临时 worktree 为 `/worktree:ro`。
- 容器内运行 `python -m unittest -q`，避免基础镜像缺少 pytest 导致 smoke 依赖额外安装。
- 输出 run_id、run_dir、`logs/docker_sandbox.jsonl` 路径和最后一条 Docker 日志。

当前本机验证结果：

```text
python scripts/run_docker_hard_check_smoke.py
run_id=run-20260525-144626-202424 status=done phase=done
docker_log=.omx\runs\run-20260525-144626-202424\logs\docker_sandbox.jsonl
docker_log_last=... "command": "python -m unittest -q" ... "exit_code": 0 ...
```

结论：

- Docker CLI 已安装。
- Docker Desktop / Docker daemon 已可用。
- Orchestrator 已能按 `execution_backend=docker` 进入 `DockerSandboxRunner` 并完成真实容器内 hard check。
- Docker 执行日志已写入 `.omx/runs/{run_id}/logs/docker_sandbox.jsonl`，记录镜像、挂载、网络、退出码和耗时。
- `python:3.12-slim` 基础镜像已可用；smoke 使用标准库 unittest 保持镜像依赖最小。

补充验证：

```text
python -m py_compile scripts/run_docker_hard_check_smoke.py
python -m pytest -q tests/test_command_safety_and_heartbeat.py tests/test_domain_services.py
16 passed

python -m pytest -q
91 passed
```
