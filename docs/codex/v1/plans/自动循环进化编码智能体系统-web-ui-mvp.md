# 自动循环进化编码智能体系统 Web UI MVP

## 目标

为当前 Orchestrator 增加一个本地输入界面，降低纯 CLI 使用门槛。该界面定位为开发/演示控制台，不承担公网访问、账号权限和多人协作能力。

## 已落地能力

- 新建任务表单：填写 task_id、标题、描述、change_type、worktree、allowed_paths、检查命令和 Agent 命令。
- 示例任务运行：从 `examples/task*.json` 中选择任务并触发运行。
- 最近运行记录：展示 `.omx/runs` 下最近 run，并可进入详情页。
- 运行详情：展示 final_report、phase.log、agent.log 和当前 run 的 pending patches。
- Patch 审批：支持在页面上 Approve / Reject pending patch；Approve 可触发 rerun-task 验证链路。

## 使用方式

```powershell
python -m orchestrator.interfaces.web.main
```

默认访问地址：

```text
http://127.0.0.1:8765
```

## 边界

- 当前仅面向本机使用，没有登录鉴权。
- 表单任务会写入 `.omx/web-tasks/`，运行结果仍写入 `.omx/runs/`。
- Web UI 复用现有 CLI composition 和 UseCase，不绕过 DDD 分层。
- 真实 OMX/Codex 后端仍依赖本机命令和环境变量配置。

## 验证

- `python -m pytest -q`：63 passed。
- 覆盖项：入口页渲染、静态样式可访问、既有 CLI/patch/orchestrator 回归。
