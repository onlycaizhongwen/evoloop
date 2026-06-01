# Evoloop

Evoloop 是一个自动循环进化编码智能体系统原型。它把任务提交、智能体执行、补丁生成、安全校验、测试回归、质量门禁、人工审批和运行审计串成一条可观察的闭环。

当前重点是让 OMX 负责编排智能体，由 Codex/OMX/本地或 Docker agent 负责执行，Orchestrator 负责解析输出、校验风险、应用补丁并记录结果。

## 当前能力

- Web UI 任务管理：`/tasks` 提供任务列表、运行中/已完成/失败/停止状态、搜索、分页、分区式新建任务表单、停止和删除记录。
- 任务模板：内置 `Local OMX Team Patch`、`Docker OMX Team Patch`、`Docker Patch JSON` 和 `Mock Flow Demo`，避免用户手写复杂命令。
- OMX/Codex 执行适配：支持 `mock`、`shell`、`codex`、`omx`、`omx_patch`、`omx_team_patch` agent mode。
- Docker 沙箱：Docker 后端使用安全的 `/worktree`、`/run`、`/cache` 路径约束，运行证据写入 run 日志。
- 补丁审批：agent 产出的 patch JSON/team result 会进入 pending patch 流程，支持 Web 审批、拒绝、审批后重新验证。
- 执行链路：Job 和 Run 页面展示 Web UI、Orchestrator、Agent、执行环境、Patch、Quality Gate 的链路摘要。
- 运行详情：Run 详情页展示任务元数据、失败原因、执行摘要、阶段时间线、执行链路、运行产物、Docker 证据、最终报告和诊断日志。
- 任务控制：Web 启动的 local/Docker 命令会注册到取消表，停止任务时会尝试终止底层进程。

## 项目结构

```text
orchestrator/
  application/          # 用例、DTO、任务模板注册
  domain/               # 状态、质量门禁、安全策略、review 校验
  infrastructure/       # agent、命令执行、Docker、本地持久化、patch 服务
  interfaces/
    cli/                # 命令行入口
    web/                # FastAPI Web UI
  report/               # final_report 输出
docs/codex/v1/          # 需求、设计、计划、追踪和状态文档
examples/               # 示例任务与默认 smoke worktree 资源
tests/                  # pytest 回归测试
```

## 快速启动 Web UI

先确认 Python 环境已经安装项目所需依赖，并且已经安装 OMX。如果要使用 Docker 模板，需要提前启动 Docker Desktop。

启动 Web：

```bash
python -m orchestrator.interfaces.web.main
```

打开：

```text
http://127.0.0.1:8765/tasks?page=1&page_size=10
```

推荐先在任务管理页点击“新建任务”，选择模板。新建弹窗按基础信息、执行方式、工作区与权限、验证配置和高级配置分区，并会在提交前展示“将会如何执行”的摘要：

- `Docker OMX Team Patch`：推荐路径，使用 Docker 沙箱运行 team result backend。
- `Docker Patch JSON`：单 agent patch JSON 验证路径。
- `Local OMX Team Patch`：本地 OMX team result 风格任务。
- `Mock Flow Demo`：不调用真实外部 agent，用于验证 Orchestrator 状态流转。

提交后先进入 Job 状态页。页面会展示执行链路，说明任务当前由哪个 agent mode、哪个 backend 和哪个命令预设执行。任务完成后可进入 Run 详情页查看最终报告、补丁审批、运行产物、阶段时间线和 Docker 执行证据。

## CLI 使用

运行一个任务：

```bash
python -m orchestrator.interfaces.cli.main run --task path/to/task.json --agent mock
```

启用真实检查命令：

```bash
python -m orchestrator.interfaces.cli.main run --task path/to/task.json --agent omx_team_patch --real-checks
```

查看历史 run：

```bash
python -m orchestrator.interfaces.cli.main resume --run-id <run_id>
```

从历史 run 重新运行：

```bash
python -m orchestrator.interfaces.cli.main resume --run-id <run_id> --rerun --real-checks
```

查看待审批补丁：

```bash
python -m orchestrator.interfaces.cli.main patches list --run-id <run_id>
```

审批并重新验证：

```bash
python -m orchestrator.interfaces.cli.main patches apply --run-id <run_id> --patch <patch_file> --reviewer cli --rerun-task
```

## 运行产物

默认运行产物写入 `.omx/`：

```text
.omx/
  orchestrator.db       # Web Job SQLite 状态
  web-tasks/            # Web 提交生成的 task.json
  runs/<run_id>/        # 单次运行审计目录
    task.json
    run_state.json
    final_report.md
    logs/
      phase.log
      heartbeat.log
      agent.log
      docker_sandbox.jsonl
```

Web UI 不会因为删除任务列表记录而删除 run 审计目录。Run 目录是排查和复盘的主要依据。

## Docker 沙箱说明

Docker 模板会把执行限制在容器内的安全路径：

- `/worktree`：任务工作区挂载路径
- `/run`：运行时文件路径
- `/cache`：缓存路径

Web UI 的 Docker agent 命令预设会自动生成容器内命令，例如：

```bash
python /worktree/docker_team_backend.py {task_id} {prompt_file}
```

这能避免用户手写 Windows 宿主路径、错误挂载路径或不安全命令。

## 验证

当前已验证基线：

```bash
python -m pytest -q tests/test_command_safety_and_heartbeat.py tests/test_web_ui.py
# 57 passed

python -m pytest -q
# 130 passed
```

## 推荐使用流程

1. 启动 Web UI。
2. 进入 `/tasks`。
3. 点击“新建任务”。
4. 优先选择 `Docker OMX Team Patch` 模板。
5. 提交任务，等待 Job 状态变化。
6. 进入 Run 详情查看执行摘要、运行产物、阶段时间线、失败原因或最终报告。
7. 如果生成待审批补丁，检查补丁预览后选择批准并验证或拒绝。

## 当前边界

- 系统仍是原型阶段，重点验证自动循环编码闭环和可观测性。
- 真实 Codex/OMX 能力依赖本机已安装并可用的 `omx`、Codex CLI 和对应认证配置。
- Docker 模板依赖 Docker Desktop 正常运行。
- Web UI 当前面向本地开发和演示环境，不建议直接暴露到公网。
