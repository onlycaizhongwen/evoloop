# Web UI Docker Agent 快速上手

本文档说明如何通过 Web UI 使用 Docker agent 命令预设完成一次安全闭环。

## 使用步骤

1. 启动 Web UI：

```bash
python -m orchestrator.interfaces.web.main
```

2. 打开：

```text
http://127.0.0.1:8765
```

3. 在“新建任务”表单中选择：

```text
Execution backend = docker
Agent = omx_team_patch
Docker agent 命令预设 = Docker team_result backend
运行真实检查 = 勾选
```

4. 提交任务。

5. 任务完成后打开 Run detail，查看：

```text
Docker 执行证据
Team Result
阶段日志
Agent 日志
```

## 默认模板说明

默认 smoke worktree 会自动生成：

```text
calculator.py
test_calculator.py
docker_team_backend.py
patch_backend.py
```

因此用户不需要手写下面这些容器路径：

```text
/worktree
/run
/cache
```

选择 `team_patch_backend` 后，后端会自动写入：

```text
python /worktree/docker_team_backend.py {task_id} {prompt_file}
```

## 安全边界

- Docker agent 只读取 `/worktree`，worktree 默认只读挂载。
- Agent 通过 stdout 返回 `team_result` JSON。
- Orchestrator 在宿主机校验 patch、审批策略、应用 patch 和运行质量门禁。
- Web 后端会拒绝 Windows 宿主绝对路径和非白名单容器绝对路径。

## 验证证据

当前回归结果：

```text
python -m pytest -q tests/test_web_ui.py
27 passed

python -m pytest -q
106 passed
```
