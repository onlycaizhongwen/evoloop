# Evoloop 真实演示验收记录

本文档记录 2026-06-02 的真实 Web UI + Docker 演示验收结果，用于对外演讲、技术评审和后续回归对照。

## 结论

真实演示主链路已跑通：

```text
Web UI -> Docker OMX Team Patch 模板 -> Orchestrator -> Docker sandbox agent
-> patch_plan/team_result -> Patch apply -> Docker hard check -> Quality Gate
-> Run detail 审计展示
```

本次验收结论：可用于本地对外演示。

## 环境

| 项目 | 结果 |
| :--- | :--- |
| 日期 | 2026-06-02 |
| Web 服务 | `http://127.0.0.1:8766` |
| Docker | `Client=24.0.6 Server=24.0.6` |
| OMX | `oh-my-codex v0.18.1` |
| Codex CLI | `codex-cli 0.118.0` |
| `omx doctor` | `15 passed, 1 warning, 0 failed` |
| Git 工作区 | `main...origin/main`，演示前后均干净 |

说明：8765 当时已有旧 Web 进程，验收使用 8766 启动当前仓库的受控 Web 服务，避免上下文混淆。

## 演示任务

| 项目 | 值 |
| :--- | :--- |
| 模板 | `Docker OMX Team Patch` |
| Template ID | `docker_team_patch` |
| Job ID | `job-20260602-100617-498307` |
| Run ID | `run-20260602-100617-650766` |
| Task ID | `task-docker-team-web-001` |
| 最终状态 | `done` |
| 阶段 | `done` |
| 尝试次数 | `1/2` |
| 结果原因 | `quality gate passed` |

## 页面验收

| 页面 | 验收结果 |
| :--- | :--- |
| 任务管理页 | `200 OK`；能看到 Job、已完成状态、重新运行入口和任务名称 |
| Run 详情页 | `200 OK`；包含运行成功、执行摘要、阶段时间线、运行产物、Docker 执行证据、执行链路和 Team Result |

## 运行证据

关键产物位于：

```text
.omx/runs/run-20260602-100617-650766/
  final_report.md
  run_state.json
  task.json
  attempts/001/
    hard_checks.json
    quality_report.json
    review.json
    team_prompt.txt
    team_result.json
    team_result_raw_output.txt
  logs/
    agent.log
    docker_sandbox.jsonl
    phase.log
```

Docker sandbox 记录显示：

```text
image: python:3.12-slim
network: none
worktree_mount: readonly
agent command: python /worktree/docker_team_backend.py task-docker-team-web-001 /run/attempts/001/team_prompt.txt
check command: python -m unittest -q
```

## 质量结果

| 项目 | 结果 |
| :--- | :--- |
| hard checks | 通过；`Ran 1 test ... OK` |
| review | `pass=true`, `confidence=91` |
| quality_score | `100` |
| diff_risk_score | `10` |
| decision | `done` |
| review_json_retry_count | `0` |

最终报告摘要：

```text
status: done
phase: done
reason: quality gate passed
```

## 补丁结果

默认 smoke worktree：

```text
.tmp/omx-unified-diff-smoke/
```

演示补丁已将：

```python
return a - b
```

修复为：

```python
return a + b
```

## 演示讲解顺序

1. 打开任务管理页，说明这是推荐主入口。
2. 点击新建任务或模板直跑，选择 `Docker OMX Team Patch`。
3. 在 Job 状态页说明 Web Job、启动配置、执行链路和心跳。
4. 任务完成后进入 Run 详情页。
5. 讲解执行摘要、阶段时间线、运行产物和 Docker 执行证据。
6. 展示 `final_report.md`、`quality_report.json`、`review.json`。
7. 回到任务管理页，展示已完成状态和重新运行入口。

## 风险与预案

- 真实 Docker 或 agent 环境可能受本机状态影响；演示前先跑 `docker version`、`omx doctor` 和 Web UI smoke。
- 如果 8765 已被旧进程占用，可改用 8766 启动当前仓库 Web 服务。
- 如果真实 Docker 演示波动，可切换到 `Mock Flow Demo` 讲 Orchestrator 状态流转，或打开本次 Run 详情讲审计能力。
