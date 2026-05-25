# 自动循环进化编码智能体系统下一步规划

## 当前基线

截至 2026-05-22，核心真实链路已经跑通：

```text
Web UI / CLI
-> Orchestrator
-> OMX
-> Codex exec
-> patch JSON
-> Orchestrator 校验与应用
-> Hard Check
-> Reviewer
-> Quality Gate
-> Final Report
```

已验证样例：

- 任务：`task-real-omx-codex-002`
- 运行：`run-20260522-140604-839823`
- 修改文件：`.tmp/omx-unified-diff-smoke/calculator.py`
- 结果：`done`
- 测试：工作区测试 `1 passed`，系统回归 `64 passed`

## 下一阶段目标

把当前“示例工作区跑通”推进为“真实项目可持续使用”的 MVP+ 阶段。

目标不是继续堆功能，而是补齐真实使用时最容易踩坑的四件事：

1. 真实项目接入时不容易填错。
2. 长任务运行时页面不假死。
3. patch 审批前能看懂改了什么。
4. OMX 不只是单 Agent 调用，而能逐步承担智能体编排。

## 优先级一：真实项目接入体验

### 目标

让用户可以在 Web UI 上选择真实 worktree、填写允许修改路径，然后安全地提交任务。

### 实施项

- 新增“真实项目任务”表单模式：
  - worktree 路径
  - allowed_paths 多行输入
  - forbidden_paths 多行输入
  - check command
  - change_type
- 提交前做后端校验：
  - worktree 必须存在
  - allowed_paths 至少一个
  - forbidden_paths 不允许为空，默认包含 `.env`、`secrets`、`deploy/prod`
  - test command 必须命中 allowlist
- 页面增加“本次会允许修改哪些文件”的确认摘要。
- 默认仍使用 `omx_patch`，避免模型直接写工作区。

### 验证

- 提交不存在 worktree 时页面返回可读错误。
- 提交合法真实 worktree 后能生成 `.omx/web-tasks/*.json`。
- 不影响当前 smoke 工作区。

## 优先级二：异步任务与运行状态

### 目标

真实 OMX/Codex 执行几十秒时，页面应立即反馈“已提交”，并能持续查看状态。

### 实施项

- 将当前内存 `BACKGROUND_TASKS` 升级为落盘 job：
  - `.omx/jobs/{job_id}.json`
  - 记录 task_path、run_id、status、message、started_at、finished_at
- 新增 Job 状态页：
  - running / done / failed
  - 自动刷新
  - 显示 run_id
  - 完成后跳转结果页
- 防重复提交：
  - 提交按钮点击后禁用
  - 后端可按 task_id + 近时间窗口提示重复任务
- 增加失败时的人话提示：
  - patch JSON malformed
  - empty operations
  - unified diff no hunks
  - hard check failed

### 验证

- 提交任务后浏览器不阻塞。
- 服务重启后仍能查看 job 状态。
- 任务完成后能跳转 run 详情。

## 优先级三：Patch Diff 可视化审批

### 目标

当 patch 需要人工审批时，用户不用读 JSON，也能看懂改了什么。

### 实施项

- pending patch 页面展示：
  - 文件列表
  - 操作类型：replace/create/delete/unified_diff
  - 风险分
  - 风险原因
- 对 `replace_text` 渲染 before/after。
- 对 `unified_diff` 渲染 diff hunk。
- 对 `delete_file` 高亮危险操作。
- Approve 前显示“批准后会立即应用到哪个 worktree”。

### 验证

- pending patch 能在 Web 上看到可读 diff。
- delete_file 必须人工确认。
- approve 后 rerun-task 结果能回写页面。

## 优先级四：OMX 智能体编排增强

### 目标

让 OMX 不只承担“调用 Codex 生成 patch”，而逐步承担智能体编排职责。

### 实施项

- 定义 Orchestrator 与 OMX 编排模式的边界：
  - Orchestrator：任务状态、权限、安全、审批、测试、质量门禁
  - OMX：Coder/Fixer/Reviewer/Researcher 等智能体编排
- 新增 `agent_mode=omx_team_patch` 设计：
  - Coder 产出 patch JSON
  - Reviewer 产出 review JSON
  - 可选 Planner 产出执行摘要
- 第一版仍要求最终产物回到 Orchestrator schema：
  - patch JSON
  - review JSON
  - diagnostics
- 禁止 OMX team 直接绕过 Orchestrator 写正式区。

### 验证

- OMX team 产出的 patch JSON 能被当前 PatchValidator 接收。
- Reviewer JSON 能被 ReviewValidator 接收。
- 任一 Agent 输出不合法时能进入诊断页。

## 优先级五：真实项目回归 Smoke

### 目标

选择一个小型真实项目或当前仓库中的安全目录，做一次真实任务闭环。

### 建议 Smoke

- 只允许改一个小文件。
- 任务类型选择 `bugfix` 或 `refactor`。
- 测试命令先用轻量命令。
- 禁止改配置、密钥、部署目录。

### 验证

- run 到 `done`。
- 测试通过。
- final_report 能说明修改内容。
- 变更文件与 allowed_paths 一致。

## 推荐执行顺序

1. 先做“异步任务与运行状态落盘”。
2. 再做“真实项目接入表单校验”。
3. 然后做“Patch Diff 可视化审批”。
4. 接着补“真实项目回归 Smoke”。
5. 最后进入“OMX team 编排模式”。

## 下一步建议

下一步优先实现：

```text
异步任务与运行状态落盘
```

原因：

- 真实 Codex 执行时间不可控。
- 当前内存 job 服务重启会丢。
- 用户最直观的痛点是“点了按钮不知道有没有在跑”。
- 这个能力会支撑后续真实项目接入和多 Agent 编排。

## 验收标准

- `python -m pytest -q` 通过。
- Web 提交任务后 1 秒内进入 job 页面。
- Job 页面可在服务重启后恢复展示。
- 任务完成后可跳到 run 结果页。
- 状态文档与 task-control 记录同步更新。
