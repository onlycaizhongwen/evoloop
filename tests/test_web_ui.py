from __future__ import annotations

import json
import subprocess
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from orchestrator.domain.enums import RunStatus
from orchestrator.domain.models.patch_plan import PatchApplyResult, PatchPlan
from orchestrator.domain.models.run_state import RunState
from orchestrator.infrastructure.patches.patch_approval import PendingPatchWriter
from orchestrator.infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository
from orchestrator.interfaces.web.main import _tasks_url, app


def test_web_index_renders(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "task.mock.json").write_text("{}", encoding="utf-8")

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Auto Evolution Orchestrator" in response.text
    assert "task.mock.json" in response.text


def test_job_status_reads_persisted_job(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = tmp_path / ".omx" / "web-tasks" / "task-job-context.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text(
        json.dumps(
            {
                "task_id": "task-job-context",
                "title": "Job 详情任务",
                "template_id": "docker_patch_json",
                "execution_backend": "docker",
                "agent_mode": "omx_patch",
                "command_preset": "patch_json_backend",
                "allowed_paths": ["calculator.py", "patch_backend.py"],
                "check_commands": {"test": "python -m unittest -q"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-test",
            "status": "running",
            "message": "running",
            "task_path": str(task_path),
            "run_id": "",
        }
    )

    response = TestClient(app).get("/jobs/job-test")

    assert response.status_code == 200
    assert "job-test" in response.text
    assert "Job 详情任务" in response.text
    assert "task-job-context / job-test" in response.text
    assert "running" in response.text
    assert "启动配置" in response.text
    assert "执行链路" in response.text
    assert "当前任务由 docker / omx_patch 执行" in response.text
    assert "OMX Patch Agent" in response.text
    assert "Docker sandbox" in response.text
    assert "计划使用 Docker，等待执行证据" in response.text
    assert "Docker Patch JSON" in response.text
    assert "docker_patch_json" in response.text
    assert "patch_json_backend" in response.text
    assert 'action="/jobs/job-test/rerun"' in response.text
    assert 'action="/tasks/job-test/stop"' in response.text
    assert 'action="/tasks/job-test/delete"' in response.text
    assert "重新运行" in response.text
    assert "停止任务" in response.text
    assert "删除记录" in response.text


def test_job_status_stopped_does_not_auto_refresh(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-stopped",
            "status": "stopped",
            "message": "已收到停止请求。",
            "task_path": "",
            "run_id": "",
        }
    )

    response = TestClient(app).get("/jobs/job-stopped")

    assert response.status_code == 200
    assert "已提交停止请求" in response.text
    assert '<meta http-equiv="refresh" content="3">' not in response.text


def test_job_status_reruns_task_from_original_task_json(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = tmp_path / ".omx" / "web-tasks" / "task-rerun-source.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text(
        json.dumps(
            {
                "task_id": "task-rerun-source",
                "title": "原始任务",
                "description": "rerun me",
                "change_type": "bugfix",
                "repo_path": str(tmp_path),
                "worktree_path": str(tmp_path),
                "allowed_paths": ["calculator.py"],
                "forbidden_paths": [".env"],
                "allowed_command_prefixes": ["python"],
                "execution_backend": "local",
                "check_commands": {"test": None, "lint": None, "typecheck": None},
                "agent_mode": "mock",
                "agent_commands": {"patch_coder": None, "patch_fixer": None, "reviewer": None},
                "max_attempts": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-rerun-source",
            "status": "failed",
            "message": "failed",
            "task_path": str(task_path),
            "run_id": "",
        }
    )

    response = TestClient(app).post("/jobs/job-rerun-source/rerun", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/jobs/job-")
    copied_tasks = sorted((tmp_path / ".omx" / "web-tasks").glob("task-rerun-source-rerun-*.json"))
    assert copied_tasks
    copied = json.loads(copied_tasks[-1].read_text(encoding="utf-8"))
    assert copied["task_id"].startswith("task-rerun-source-rerun-")
    assert copied["title"].endswith("（重新运行）")


def test_job_status_rerun_missing_task_shows_feedback(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-missing-task-rerun",
            "status": "failed",
            "message": "legacy failed",
            "task_path": "",
            "run_id": "",
        }
    )
    client = TestClient(app)

    response = client.post("/jobs/job-missing-task-rerun/rerun", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/jobs/job-missing-task-rerun?rerun_error=missing_task"

    detail = client.get(response.headers["location"])

    assert detail.status_code == 200
    assert "无法重新运行" in detail.text
    assert "没有找到该任务的原始 task.json" in detail.text


def test_job_status_shows_reused_template_notice(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = tmp_path / ".omx" / "web-tasks" / "task-reused-template.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text(
        json.dumps({"task_id": "task-reused-template", "template_id": "docker_team_patch"}, ensure_ascii=False),
        encoding="utf-8",
    )
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-reused-template",
            "status": "running",
            "message": "running",
            "task_path": str(task_path),
            "run_id": "",
        }
    )

    response = TestClient(app).get("/jobs/job-reused-template?reused=1")

    assert response.status_code == 200
    assert "该模板已有任务运行中" in response.text
    assert "任务管理" in response.text


def test_job_status_frontloads_failed_reason(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = tmp_path / ".omx" / "web-tasks" / "task-failed-reason.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text('{"task_id": "task-failed-reason"}', encoding="utf-8")
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-failed-reason",
            "status": "failed",
            "message": "任务未完成，停在 review 阶段。",
            "task_path": str(task_path),
            "run_id": "",
        }
    )

    response = TestClient(app).get("/jobs/job-failed-reason")

    assert response.status_code == 200
    assert "失败原因" in response.text
    assert "阶段：未记录" in response.text
    assert "任务未完成，停在 review 阶段。" in response.text
    assert "review JSON" in response.text


def test_job_status_infers_run_and_shows_progress(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = tmp_path / ".omx" / "web-tasks" / "task-progress.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text('{"task_id": "task-progress"}', encoding="utf-8")
    run_dir = tmp_path / ".omx" / "runs" / "run-progress"
    (run_dir / "logs").mkdir(parents=True)
    (run_dir / "task.json").write_text('{"task_id": "task-progress"}', encoding="utf-8")
    (run_dir / "run_state.json").write_text(
        "\n".join(
            [
                "{",
                '  "run_id": "run-progress",',
                '  "task_id": "task-progress",',
                '  "status": "running",',
                '  "attempt": 1,',
                '  "max_attempts": 2,',
                '  "current_phase": "quality_gate",',
                '  "started_at": "2026-05-23T09:00:00",',
                '  "updated_at": "2026-05-23T09:01:00",',
                '  "last_heartbeat_at": "2026-05-23T09:01:05",',
                '  "artifacts": {"run_dir": ".omx/runs/run-progress"}',
                "}",
            ]
        ),
        encoding="utf-8",
    )
    (run_dir / "logs" / "heartbeat.log").write_text("phase=coding\nphase=quality_gate\n", encoding="utf-8")
    (run_dir / "logs" / "phase.log").write_text("hard_check passed\nreview running\n", encoding="utf-8")
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")
    repository.create(
        {
            "job_id": "job-progress",
            "status": "running",
            "message": "running",
            "task_path": str(task_path),
            "run_id": "",
        }
    )

    response = TestClient(app).get("/jobs/job-progress")
    job = repository.get("job-progress")

    assert response.status_code == 200
    assert "run-progress" in response.text
    assert "quality_gate" in response.text
    assert "1/2" in response.text
    assert "phase=quality_gate" in response.text
    assert "review running" in response.text
    assert "task-progress / job-progress" in response.text
    assert "锛" not in response.text
    assert "启动配置" in response.text
    assert job is not None
    assert job["run_id"] == "run-progress"


def test_job_status_reconciles_done_run_after_restart(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    task_path = tmp_path / ".omx" / "web-tasks" / "task-done.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text('{"task_id": "task-done"}', encoding="utf-8")
    _write_run_state(tmp_path, "run-done", "task-done", RunStatus.DONE, "done")
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")
    repository.create(
        {
            "job_id": "job-done",
            "status": "running",
            "message": "running before restart",
            "task_path": str(task_path),
            "run_id": "",
        }
    )

    response = TestClient(app).get("/jobs/job-done", follow_redirects=False)
    job = repository.get("job-done")

    assert response.status_code == 303
    assert response.headers["location"] == "/runs/run-done"
    assert job is not None
    assert job["status"] == "done"
    assert job["run_id"] == "run-done"


def test_run_detail_shows_no_docker_evidence_for_local_run(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    _write_run_state(tmp_path, "run-local", "task-local", RunStatus.DONE, "done")

    response = TestClient(app).get("/runs/run-local")

    assert response.status_code == 200
    assert "执行摘要" in response.text
    assert "Docker 执行" in response.text
    assert "无记录" in response.text
    assert "Docker 执行证据" in response.text
    assert "本次运行没有 Docker sandbox 执行记录" in response.text


def test_run_detail_frontloads_halted_failure_reason(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / ".omx" / "runs" / "run-halted-reason"
    _write_run_state(tmp_path, "run-halted-reason", "task-halted-reason", RunStatus.HALTED, "hard_checks")
    (run_dir / "final_report.md").write_text("Reason: pytest failed on calculator test\nMore details", encoding="utf-8")
    (run_dir / "logs" / "phase.log").write_text("phase=hard_checks event=halt\n", encoding="utf-8")

    response = TestClient(app).get("/runs/run-halted-reason")

    assert response.status_code == 200
    assert "失败原因" in response.text
    assert "阶段：hard_checks" in response.text
    assert "Reason: pytest failed on calculator test" in response.text
    assert "确认测试失败原因" in response.text
    assert "阶段时间线" in response.text
    assert "hard_checks" in response.text
    assert "halt" in response.text


def test_run_detail_shows_task_template_context(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / ".omx" / "runs" / "run-template-context"
    _write_run_state(tmp_path, "run-template-context", "task-template-context", RunStatus.DONE, "done")
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "task_id": "task-template-context",
                "title": "Run 详情任务",
                "template_id": "docker_team_patch",
                "execution_backend": "docker",
                "agent_mode": "omx_team_patch",
                "command_preset": "team_patch_backend",
                "worktree_path": str(tmp_path / "worktree"),
                "allowed_paths": ["calculator.py", "docker_team_backend.py"],
                "check_commands": {"test": "python -m unittest -q"},
                "agent_commands": {
                    "patch_coder": "python /worktree/docker_team_backend.py {task_id} {prompt_file}"
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "final_report.md").write_text("done", encoding="utf-8")
    (run_dir / "logs" / "phase.log").write_text("phase=done event=end\n", encoding="utf-8")
    patch_plan = PatchPlan(
        task_id="task-template-context",
        summary="fix calculator",
        operations=[{"op": "replace_text", "path": "calculator.py", "old": "return a - b", "new": "return a + b"}],
    )
    patch_result = PatchApplyResult(changed_files=["calculator.py"], risk_score=8)
    state = RunState(
        run_id="run-template-context",
        task_id="task-template-context",
        attempt=1,
        max_attempts=1,
        artifacts={"run_dir": str(run_dir)},
    )
    PendingPatchWriter().write(state, "patch_coder", patch_plan, patch_result)

    response = TestClient(app).get("/runs/run-template-context")

    assert response.status_code == 200
    assert "Run 详情任务" in response.text
    assert "task-template-context / run-template-context" in response.text
    assert "docker / omx_team_patch" in response.text
    assert "启动配置" in response.text
    assert "执行链路" in response.text
    assert "本次运行由 docker / omx_team_patch 执行" in response.text
    assert "OMX Team 编排" in response.text
    assert "Docker sandbox" in response.text
    assert "python /worktree/docker_team_backend.py" in response.text
    assert "运行产物" in response.text
    assert ".omx/runs/run-template-context" in response.text
    assert "final_report.md" in response.text
    assert "phase.log" in response.text
    assert "001-patch_coder.json" in response.text
    assert "calculator.py" in response.text
    assert "已生成" in response.text
    assert "Docker OMX Team Patch" in response.text
    assert "docker_team_patch" in response.text
    assert "team_patch_backend" in response.text
    assert "omx_team_patch" in response.text
    assert "python -m unittest -q" in response.text
    assert "docker_team_backend.py" in response.text
    assert 'action="/runs/run-template-context/rerun"' in response.text


def test_run_detail_reruns_task_from_run_task_json(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / ".omx" / "runs" / "run-rerun-source"
    _write_run_state(tmp_path, "run-rerun-source", "task-run-rerun-source", RunStatus.DONE, "done")
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "task_id": "task-run-rerun-source",
                "title": "Run 原始任务",
                "description": "rerun me",
                "change_type": "bugfix",
                "repo_path": str(tmp_path),
                "worktree_path": str(tmp_path),
                "allowed_paths": ["calculator.py"],
                "forbidden_paths": [".env"],
                "allowed_command_prefixes": ["python"],
                "execution_backend": "local",
                "check_commands": {"test": None, "lint": None, "typecheck": None},
                "agent_mode": "mock",
                "agent_commands": {"patch_coder": None, "patch_fixer": None, "reviewer": None},
                "max_attempts": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    response = TestClient(app).post("/runs/run-rerun-source/rerun", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/jobs/job-")
    copied_tasks = sorted((tmp_path / ".omx" / "web-tasks").glob("task-run-rerun-source-rerun-*.json"))
    assert copied_tasks


def test_run_detail_infers_command_preset_for_legacy_task(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / ".omx" / "runs" / "run-legacy-template-context"
    _write_run_state(tmp_path, "run-legacy-template-context", "task-legacy-template", RunStatus.DONE, "done")
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "task_id": "task-legacy-template",
                "execution_backend": "docker",
                "agent_mode": "omx_team_patch",
                "allowed_paths": ["calculator.py"],
                "check_commands": {"test": "python -m unittest -q"},
                "agent_commands": {
                    "patch_coder": "python /worktree/docker_team_backend.py {task_id} {prompt_file}"
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    response = TestClient(app).get("/runs/run-legacy-template-context")

    assert response.status_code == 200
    assert "team_patch_backend" in response.text
    assert "docker" in response.text


def test_index_reconciles_halted_run_after_restart(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    task_path = tmp_path / ".omx" / "web-tasks" / "task-halted.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text('{"task_id": "task-halted"}', encoding="utf-8")
    _write_run_state(tmp_path, "run-halted", "task-halted", RunStatus.HALTED, "code")
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")
    repository.create(
        {
            "job_id": "job-halted",
            "status": "running",
            "message": "running before restart",
            "task_path": str(task_path),
            "run_id": "",
        }
    )

    response = TestClient(app).get("/")
    job = repository.get("job-halted")

    assert response.status_code == 200
    assert "job-halted" in response.text
    assert "failed / run-halted" in response.text
    assert job is not None
    assert job["status"] == "failed"
    assert job["run_id"] == "run-halted"


def test_web_index_shows_persisted_jobs(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-test",
            "status": "running",
            "message": "running",
            "task_path": "task.json",
            "run_id": "",
        }
    )

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "job-test" in response.text
    assert "running" in response.text
    assert 'href="/tasks"' in response.text
    assert "任务管理" in response.text


def test_task_manager_lists_and_filters_jobs(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    running_task = tmp_path / ".omx" / "web-tasks" / "task-running-template.json"
    done_task = tmp_path / ".omx" / "web-tasks" / "task-done-template.json"
    running_task.parent.mkdir(parents=True)
    running_task.write_text(
        json.dumps(
            {"task_id": "task-running-template", "title": "运行中模板任务", "template_id": "docker_team_patch"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    done_task.write_text(
        json.dumps(
            {"task_id": "task-done-template", "title": "已完成模板任务", "template_id": "docker_patch_json"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")
    repository.create(
        {
            "job_id": "job-running-template",
            "status": "running",
            "message": "running",
            "task_path": str(running_task),
            "run_id": "",
        }
    )
    repository.create(
        {
            "job_id": "job-done-template",
            "status": "done",
            "message": "done",
            "task_path": str(done_task),
            "run_id": "run-done-template",
        }
    )

    response = TestClient(app).get("/tasks")

    assert response.status_code == 200
    assert "任务管理" in response.text
    assert "运行中" in response.text
    assert "已完成" in response.text
    assert "已停止" in response.text
    assert "job-running-template" in response.text
    assert "job-done-template" in response.text
    assert "Docker OMX Team Patch" in response.text
    assert "Docker Patch JSON" in response.text
    assert "<table" in response.text
    assert "<th>任务名称</th>" in response.text
    assert "<th>Job ID</th>" in response.text
    assert "<th>Run ID</th>" in response.text
    assert "<th>模板</th>" in response.text
    assert "<th>执行</th>" in response.text
    assert response.text.index("<th>任务名称</th>") < response.text.index("<th>Job ID</th>")
    assert response.text.index("<th>更新时间</th>") < response.text.index("<th>状态</th>")
    assert "运行中模板任务" in response.text
    assert "已完成模板任务" in response.text
    assert 'href="/jobs/job-running-template"' in response.text
    assert 'href="/runs/run-done-template"' in response.text
    assert 'action="/tasks/job-running-template/stop?status=all&amp;page=1&amp;page_size=10&amp;q="' in response.text
    assert 'action="/jobs/job-running-template/rerun"' not in response.text
    assert 'action="/jobs/job-done-template/rerun"' in response.text
    assert 'action="/tasks/job-running-template/delete?status=all&amp;page=1&amp;page_size=10&amp;q="' in response.text
    assert "停止" in response.text
    assert "重新运行" in response.text
    assert "删除" in response.text
    assert 'data-confirm="确认停止该任务？系统会向当前 local/Docker 命令发送终止信号；若任务尚未进入命令执行阶段，则冻结 Web 状态。"' in response.text
    assert 'data-confirm="确认从任务列表移除该记录？run 目录和审计日志会保留。"' in response.text
    assert "共 2 条，第 1 / 1 页" in response.text
    assert 'class="sidebar"' in response.text
    assert '<nav class="side-nav">\n        <a class="active" href="/tasks">任务管理</a>\n      </nav>' in response.text
    assert 'data-open-modal="task-create-modal"' in response.text
    assert 'id="task-create-modal"' in response.text
    assert 'action="/tasks/run"' in response.text
    assert 'name="q"' in response.text
    assert 'placeholder="任务名称、Task ID、Job ID、Run ID、模板"' in response.text
    assert 'name="page_size"' in response.text
    assert 'name="task_id"' in response.text
    assert 'name="description"' in response.text
    assert 'name="command_preset"' in response.text
    assert "基础信息" in response.text
    assert "执行方式" in response.text
    assert "工作区与权限" in response.text
    assert "验证配置" in response.text
    assert "高级配置" in response.text
    assert "将会如何执行" in response.text
    assert "使用推荐模板时无需手写 /worktree、/run 等容器路径" in response.text
    assert "提交任务" in response.text
    assert 'data-submitting-text="提交中..."' in response.text

    filtered = TestClient(app).get("/tasks?status=running")

    assert filtered.status_code == 200
    assert "job-running-template" in filtered.text
    assert "job-done-template" not in filtered.text
    assert '<meta http-equiv="refresh" content="5">' in filtered.text
    assert "运行中列表会自动刷新" in filtered.text

    stopped = TestClient(app).get("/tasks?status=stopped")

    assert stopped.status_code == 200
    assert "已停止任务不会自动刷新" in stopped.text
    assert '<meta http-equiv="refresh" content="5">' not in stopped.text

    searched = TestClient(app).get("/tasks?q=已完成模板任务")

    assert searched.status_code == 200
    assert "job-done-template" in searched.text
    assert "job-running-template" not in searched.text
    assert 'value="已完成模板任务"' in searched.text
    assert 'href="/tasks?status=running' in searched.text
    assert "&amp;q=" in searched.text


def test_task_manager_paginates_jobs(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    task_dir = tmp_path / ".omx" / "web-tasks"
    task_dir.mkdir(parents=True)
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")
    for index in range(12):
        task_path = task_dir / f"task-page-{index:02d}.json"
        task_path.write_text(
            json.dumps({"task_id": f"task-page-{index:02d}", "title": f"分页任务 {index:02d}"}, ensure_ascii=False),
            encoding="utf-8",
        )
        repository.create(
            {
                "job_id": f"job-page-{index:02d}",
                "status": "failed",
                "message": "failed",
                "task_path": str(task_path),
                "run_id": "",
                "updated_at": f"2026-05-27T10:{index:02d}:00",
            }
        )

    response = TestClient(app).get("/tasks?status=failed&page=2&page_size=5")

    assert response.status_code == 200
    assert "共 12 条，第 2 / 3 页" in response.text
    assert 'href="/tasks?status=failed&amp;page=1&amp;page_size=5&amp;q="' in response.text
    assert 'href="/tasks?status=failed&amp;page=3&amp;page_size=5&amp;q="' in response.text
    assert "job-page-06" in response.text
    assert "job-page-05" in response.text
    assert "job-page-11" not in response.text

    searched = TestClient(app).get("/tasks?status=failed&q=分页任务 11&page=1&page_size=5")

    assert searched.status_code == 200
    assert "共 1 条，第 1 / 1 页" in searched.text
    assert "job-page-11" in searched.text
    assert "job-page-10" not in searched.text


def test_task_manager_stops_and_deletes_jobs(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")
    repository.create(
        {
            "job_id": "job-stop-delete",
            "status": "running",
            "message": "running",
            "task_path": "",
            "run_id": "",
        }
    )
    client = TestClient(app)

    stop_response = client.post(
        "/tasks/job-stop-delete/stop?status=running&page=1&page_size=10&q=运行中 任务",
        follow_redirects=False,
    )

    assert stop_response.status_code == 303
    assert stop_response.headers["location"] == "/tasks?status=running&page=1&page_size=10&q=%E8%BF%90%E8%A1%8C%E4%B8%AD+%E4%BB%BB%E5%8A%A1"
    stopped = repository.get("job-stop-delete")
    assert stopped is not None
    assert stopped["status"] == "stopped"
    assert "停止请求" in stopped["message"]
    assert "冻结" in stopped["message"]

    stopped_detail = client.get("/jobs/job-stop-delete")
    assert stopped_detail.status_code == 200
    assert "已提交停止请求" in stopped_detail.text

    delete_response = client.post(
        "/tasks/job-stop-delete/delete?status=all&page=1&page_size=10&q=运行中 任务",
        follow_redirects=False,
    )

    assert delete_response.status_code == 303
    assert delete_response.headers["location"] == "/tasks?status=all&page=1&page_size=10&q=%E8%BF%90%E8%A1%8C%E4%B8%AD+%E4%BB%BB%E5%8A%A1"
    assert repository.get("job-stop-delete") is None


def test_task_manager_url_preserves_query():
    url = _tasks_url(status="running", page=2, page_size=20, q="abc def")

    assert url == "/tasks?status=running&page=2&page_size=20&q=abc+def"


def test_task_manager_tolerates_legacy_job_without_task_path(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-legacy-empty-task-path",
            "status": "running",
            "message": "legacy",
            "task_path": "",
            "run_id": "",
        }
    )

    response = TestClient(app).get("/tasks")

    assert response.status_code == 200
    assert "job-legacy-empty-task-path" in response.text
    assert "历史任务" in response.text
    assert "旧任务未记录" in response.text
    assert "早期任务缺少模板元数据" in response.text
    assert "早期任务缺少执行后端元数据" in response.text


def test_web_index_shows_recent_job_on_template_card(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    task_path = tmp_path / ".omx" / "web-tasks" / "task-template-recent.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text(
        json.dumps({"task_id": "task-template-recent", "template_id": "docker_team_patch"}, ensure_ascii=False),
        encoding="utf-8",
    )
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-template-recent",
            "status": "done",
            "message": "done",
            "task_path": str(task_path),
            "run_id": "run-template-recent",
        }
    )

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Docker OMX Team Patch" in response.text
    assert "Recent: done / run-template-recent" in response.text
    assert 'class="template-recent done"' in response.text
    assert 'href="/jobs/job-template-recent"' in response.text


def test_task_form_validation_rejects_bad_input(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "bad id!",
            "title": "bad",
            "description": "bad",
            "change_type": "bugfix",
            "allowed_paths": "../escape.py",
            "worktree_path": str(tmp_path / "missing-worktree"),
            "check_command": "",
            "agent_mode": "omx_patch",
            "patch_coder": "python coder.py",
            "patch_fixer": "python fixer.py",
            "reviewer": "python reviewer.py",
            "real_checks": "on",
        },
    )

    assert response.status_code == 422
    assert "Task ID" in response.text
    assert "Allowed paths" in response.text
    assert "missing-worktree" in response.text
    db_path = tmp_path / ".omx" / "orchestrator.db"
    with sqlite3.connect(db_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM web_jobs").fetchone()[0]
    assert count == 0


def test_task_form_validation_rejects_dangerous_command(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-safe-id",
            "title": "bad command",
            "description": "bad command",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "rm -rf .",
            "agent_mode": "omx_patch",
            "patch_coder": "python coder.py",
            "patch_fixer": "python fixer.py",
            "reviewer": "python reviewer.py",
            "real_checks": "on",
        },
    )

    assert response.status_code == 422


def test_sqlite_job_repository_updates_and_lists_recent(tmp_path: Path):
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")

    repository.create(
        {
            "job_id": "job-test",
            "status": "running",
            "message": "running",
            "task_path": "task.json",
            "run_id": "",
        }
    )
    repository.update("job-test", status="done", message="done", run_id="run-001", finished_at="now")

    job = repository.get("job-test")
    jobs = repository.list_recent()

    assert job is not None
    assert job["status"] == "done"
    assert job["run_id"] == "run-001"
    assert jobs[0]["job_id"] == "job-test"


def test_web_static_styles_available():
    response = TestClient(app).get("/static/styles.css")

    assert response.status_code == 200
    assert ".shell" in response.text


def test_web_index_exposes_omx_team_patch_mode(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "omx_team_patch" in response.text


def test_web_index_exposes_docker_backend_option(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'name="execution_backend"' in response.text
    assert 'value="local"' in response.text
    assert 'value="docker"' in response.text
    assert 'name="command_preset"' in response.text
    assert 'value="team_patch_backend"' in response.text
    assert "Docker Agent 快速上手" in response.text
    assert "Docker 执行证据" in response.text


def test_web_index_exposes_task_template_selector(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'name="template_id"' in response.text
    assert 'value="local_omx_team"' in response.text
    assert 'value="docker_team_patch"' in response.text
    assert 'value="docker_patch_json"' in response.text
    assert "Local OMX Team Patch" in response.text
    assert "Docker OMX Team Patch" in response.text
    assert "Default" in response.text
    assert "Recommended" in response.text
    assert "Backend: docker" in response.text
    assert "Agent: omx_team_patch" in response.text
    assert "Preset: team_patch_backend" in response.text
    assert "Checks: python -m unittest -q" in response.text
    assert "Paths: calculator.py, test_calculator.py, docker_team_backend.py" in response.text
    assert 'action="/templates/run"' in response.text
    assert "直接运行" in response.text
    assert 'data-submitting-text="提交中..."' in response.text
    assert 'button.disabled = true' in response.text


def test_web_index_applies_docker_team_template(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()

    response = TestClient(app).get("/?template_id=docker_team_patch")

    assert response.status_code == 200
    assert 'name="template_id" value="docker_team_patch"' in response.text
    assert 'value="task-docker-team-web-001"' in response.text
    assert 'value="docker" selected' in response.text
    assert 'value="team_patch_backend" selected' in response.text
    assert 'value="omx_team_patch" selected' in response.text
    assert "docker_team_backend.py" in response.text
    assert "python /worktree/docker_team_backend.py {task_id} {prompt_file}" in response.text


def test_web_index_invalid_template_falls_back_to_local(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()

    response = TestClient(app).get("/?template_id=missing-template")

    assert response.status_code == 200
    assert 'name="template_id" value="local_omx_team"' in response.text
    assert 'value="task-omx-team-web-001"' in response.text


def test_task_form_submission_defaults_to_local_backend(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    captured: dict[str, Path] = {}

    def fake_start(task_path: Path, *, agent_mode: str, real_checks: bool) -> str:
        captured["task_path"] = task_path
        return "job-local"

    monkeypatch.setattr("orchestrator.interfaces.web.main._start_background_run", fake_start)

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-local-web",
            "title": "local",
            "description": "local",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "",
            "agent_mode": "mock",
            "patch_coder": "",
            "patch_fixer": "",
            "reviewer": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    task = json.loads(captured["task_path"].read_text(encoding="utf-8"))
    assert task["execution_backend"] == "local"
    assert task["sandbox"]["image"] == "python:3.12-slim"
    assert task["sandbox"]["worktree_mount"] == "readonly"


def test_task_form_submission_writes_docker_config(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    captured: dict[str, Path] = {}

    def fake_start(task_path: Path, *, agent_mode: str, real_checks: bool) -> str:
        captured["task_path"] = task_path
        return "job-docker"

    monkeypatch.setattr("orchestrator.interfaces.web.main._start_background_run", fake_start)

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-docker-web",
            "title": "docker",
            "description": "docker",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "",
            "agent_mode": "mock",
            "patch_coder": "",
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "docker",
            "sandbox_image": "python:3.12-slim",
            "sandbox_network": "none",
            "sandbox_worktree_mount": "readonly",
            "sandbox_memory_limit": "512m",
            "sandbox_cpu_limit": "0.5",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    task = json.loads(captured["task_path"].read_text(encoding="utf-8"))
    assert task["execution_backend"] == "docker"
    assert task["sandbox"] == {
        "image": "python:3.12-slim",
        "network": "none",
        "worktree_mount": "readonly",
        "memory_limit": "512m",
        "cpu_limit": 0.5,
    }


def test_task_form_validation_rejects_bad_docker_config(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-bad-docker-web",
            "title": "docker",
            "description": "docker",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "",
            "agent_mode": "mock",
            "patch_coder": "",
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "docker",
            "sandbox_image": "",
            "sandbox_network": "host",
            "sandbox_worktree_mount": "rw",
            "sandbox_memory_limit": "huge",
            "sandbox_cpu_limit": "0",
        },
    )

    assert response.status_code == 422
    assert "Docker image" in response.text
    assert "Docker network" in response.text
    assert "readonly" in response.text
    assert "Docker memory limit" in response.text
    assert "Docker CPU limit" in response.text


def test_task_form_validation_rejects_host_paths_for_docker_commands(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-docker-host-path-web",
            "title": "docker",
            "description": "docker",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "python -m unittest -q",
            "agent_mode": "omx_team_patch",
            "patch_coder": r'python "D:\tools\backend.py" {task_id} {prompt_file}',
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "docker",
            "sandbox_image": "python:3.12-slim",
            "sandbox_network": "none",
            "sandbox_worktree_mount": "readonly",
            "sandbox_memory_limit": "1g",
            "sandbox_cpu_limit": "1",
        },
    )

    assert response.status_code == 422
    assert "Windows host path" in response.text
    assert "/worktree" in response.text


def test_task_form_validation_allows_container_paths_for_docker_commands(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    captured: dict[str, Path] = {}

    def fake_start(task_path: Path, *, agent_mode: str, real_checks: bool) -> str:
        captured["task_path"] = task_path
        return "job-docker-agent"

    monkeypatch.setattr("orchestrator.interfaces.web.main._start_background_run", fake_start)

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-docker-container-path-web",
            "title": "docker",
            "description": "docker",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "python -m unittest -q",
            "agent_mode": "omx_team_patch",
            "patch_coder": "python /worktree/backend.py {task_id} {prompt_file}",
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "docker",
            "sandbox_image": "python:3.12-slim",
            "sandbox_network": "none",
            "sandbox_worktree_mount": "readonly",
            "sandbox_memory_limit": "1g",
            "sandbox_cpu_limit": "1",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    task = json.loads(captured["task_path"].read_text(encoding="utf-8"))
    assert task["agent_commands"]["patch_coder"] == "python /worktree/backend.py {task_id} {prompt_file}"


def test_task_form_docker_command_preset_writes_safe_agent_command(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    captured: dict[str, Path] = {}

    def fake_start(task_path: Path, *, agent_mode: str, real_checks: bool) -> str:
        captured["task_path"] = task_path
        return "job-docker-preset"

    monkeypatch.setattr("orchestrator.interfaces.web.main._start_background_run", fake_start)

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-docker-preset-web",
            "title": "docker preset",
            "description": "docker preset",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "python -m unittest -q",
            "agent_mode": "omx_team_patch",
            "command_preset": "team_patch_backend",
            "patch_coder": r'python "D:\unsafe\backend.py" {task_id} {prompt_file}',
            "patch_fixer": "ignored",
            "reviewer": "ignored",
            "execution_backend": "docker",
            "sandbox_image": "python:3.12-slim",
            "sandbox_network": "none",
            "sandbox_worktree_mount": "readonly",
            "sandbox_memory_limit": "1g",
            "sandbox_cpu_limit": "1",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    task = json.loads(captured["task_path"].read_text(encoding="utf-8"))
    assert task["agent_commands"] == {
        "patch_coder": "python /worktree/docker_team_backend.py {task_id} {prompt_file}",
        "patch_fixer": None,
        "reviewer": None,
    }


def test_task_form_template_submission_writes_template_id(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    captured: dict[str, Path] = {}

    def fake_start(task_path: Path, *, agent_mode: str, real_checks: bool) -> str:
        captured["task_path"] = task_path
        return "job-docker-template"

    monkeypatch.setattr("orchestrator.interfaces.web.main._start_background_run", fake_start)

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "template_id": "docker_team_patch",
            "task_id": "task-docker-template-web",
            "title": "docker template",
            "description": "docker template",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py\ntest_calculator.py\ndocker_team_backend.py",
            "worktree_path": str(tmp_path / ".tmp" / "omx-unified-diff-smoke"),
            "check_command": "python -m unittest -q",
            "agent_mode": "omx_team_patch",
            "command_preset": "team_patch_backend",
            "patch_coder": "",
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "docker",
            "sandbox_image": "python:3.12-slim",
            "sandbox_network": "none",
            "sandbox_worktree_mount": "readonly",
            "sandbox_memory_limit": "1g",
            "sandbox_cpu_limit": "1",
            "real_checks": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    task = json.loads(captured["task_path"].read_text(encoding="utf-8"))
    assert task["template_id"] == "docker_team_patch"
    assert task["execution_backend"] == "docker"
    assert task["agent_mode"] == "omx_team_patch"
    assert task["agent_commands"]["patch_coder"] == "python /worktree/docker_team_backend.py {task_id} {prompt_file}"


def test_template_direct_run_uses_whitelisted_template(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    captured: dict[str, Path] = {}

    def fake_start(task_path: Path, *, agent_mode: str, real_checks: bool) -> str:
        captured["task_path"] = task_path
        captured["agent_mode"] = agent_mode
        captured["real_checks"] = real_checks
        return "job-direct-template"

    monkeypatch.setattr("orchestrator.interfaces.web.main._start_background_run", fake_start)

    response = TestClient(app).post(
        "/templates/run",
        data={"template_id": "docker_team_patch"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/jobs/job-direct-template"
    task = json.loads(captured["task_path"].read_text(encoding="utf-8"))
    assert captured["agent_mode"] == "omx_team_patch"
    assert captured["real_checks"] is True
    assert task["template_id"] == "docker_team_patch"
    assert task["task_id"] == "task-docker-team-web-001"
    assert task["execution_backend"] == "docker"
    assert task["agent_commands"]["patch_coder"] == "python /worktree/docker_team_backend.py {task_id} {prompt_file}"


def test_template_direct_run_reuses_running_job_for_same_template(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    task_path = tmp_path / ".omx" / "web-tasks" / "task-running-template.json"
    task_path.parent.mkdir(parents=True)
    task_path.write_text(
        json.dumps({"task_id": "task-running-template", "template_id": "docker_team_patch"}, ensure_ascii=False),
        encoding="utf-8",
    )
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-existing-template",
            "status": "running",
            "message": "running",
            "task_path": str(task_path),
            "run_id": "",
        }
    )

    def fail_start(task_path: Path, *, agent_mode: str, real_checks: bool) -> str:
        raise AssertionError("duplicate template direct run should reuse the existing running job")

    monkeypatch.setattr("orchestrator.interfaces.web.main._start_background_run", fail_start)

    response = TestClient(app).post(
        "/templates/run",
        data={"template_id": "docker_team_patch"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/jobs/job-existing-template?reused=1"


def test_default_smoke_worktree_includes_docker_agent_backends(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    captured: dict[str, Path] = {}

    def fake_start(task_path: Path, *, agent_mode: str, real_checks: bool) -> str:
        captured["task_path"] = task_path
        return "job-default-docker-backends"

    monkeypatch.setattr("orchestrator.interfaces.web.main._start_background_run", fake_start)

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-default-docker-backends",
            "title": "default docker backends",
            "description": "default docker backends",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py\ndocker_team_backend.py\npatch_backend.py",
            "worktree_path": str(tmp_path / ".tmp" / "omx-unified-diff-smoke"),
            "check_command": "python -m unittest -q",
            "agent_mode": "omx_team_patch",
            "command_preset": "team_patch_backend",
            "patch_coder": "",
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "docker",
            "sandbox_image": "python:3.12-slim",
            "sandbox_network": "none",
            "sandbox_worktree_mount": "readonly",
            "sandbox_memory_limit": "1g",
            "sandbox_cpu_limit": "1",
        },
        follow_redirects=False,
    )

    worktree = tmp_path / ".tmp" / "omx-unified-diff-smoke"
    assert response.status_code == 303
    assert (worktree / "docker_team_backend.py").exists()
    assert (worktree / "patch_backend.py").exists()
    task = json.loads(captured["task_path"].read_text(encoding="utf-8"))
    assert "docker_team_backend.py" in task["allowed_paths"]
    assert task["agent_commands"]["patch_coder"] == "python /worktree/docker_team_backend.py {task_id} {prompt_file}"


def test_task_form_docker_command_preset_rejects_wrong_agent_mode(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-docker-preset-bad-agent",
            "title": "docker preset",
            "description": "docker preset",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "python -m unittest -q",
            "agent_mode": "mock",
            "command_preset": "team_patch_backend",
            "patch_coder": "",
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "docker",
            "sandbox_image": "python:3.12-slim",
            "sandbox_network": "none",
            "sandbox_worktree_mount": "readonly",
            "sandbox_memory_limit": "1g",
            "sandbox_cpu_limit": "1",
        },
    )

    assert response.status_code == 422
    assert "team_patch_backend" in response.text
    assert "omx_team_patch" in response.text


def test_task_form_docker_command_preset_requires_docker_backend(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-docker-preset-local",
            "title": "docker preset",
            "description": "docker preset",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "",
            "agent_mode": "omx_team_patch",
            "command_preset": "team_patch_backend",
            "patch_coder": "",
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "local",
        },
    )

    assert response.status_code == 422
    assert "require execution backend docker" in response.text


def test_web_docker_hard_check_smoke_script_compiles():
    script = Path("scripts/run_web_docker_hard_check_smoke.py")

    completed = subprocess.run(
        [sys.executable, "-m", "py_compile", str(script)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_task_form_validation_allows_omx_team_patch(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    backend = tmp_path / "team_backend.py"
    backend.write_text(
        "\n".join(
            [
                "import json, sys",
                "task_id = sys.argv[1]",
                "print(json.dumps({'schema_version':'1.0','task_id':task_id,'status':'completed','roles':{},'artifacts':{'patch_plan':{'schema_version':'1.0','task_id':task_id,'summary':'fix','operations':[{'op':'replace_text','path':'calculator.py','old':'return a - b','new':'return a + b'}]},'review':{'schema_version':'1.0','task_id':task_id,'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}},'diagnostics':[]}))",
            ]
        ),
        encoding="utf-8",
    )

    response = TestClient(app).post(
        "/tasks/run",
        data={
            "task_id": "task-team-web",
            "title": "team",
            "description": "team",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "",
            "agent_mode": "omx_team_patch",
            "patch_coder": f'"{__import__("sys").executable}" "{backend}" {{task_id}}',
            "patch_fixer": "",
            "reviewer": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/jobs/")


def test_web_omx_team_patch_job_runs_to_detail(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (worktree / "test_calculator.py").write_text(
        "from calculator import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )
    backend = tmp_path / "team_backend.py"
    backend.write_text(
        "\n".join(
            [
                "import json, sys",
                "task_id = sys.argv[1]",
                "print(json.dumps({'schema_version':'1.0','task_id':task_id,'status':'completed','roles':{},'artifacts':{'patch_plan':{'schema_version':'1.0','task_id':task_id,'summary':'fix','operations':[{'op':'replace_text','path':'calculator.py','old':'return a - b','new':'return a + b'}]},'review':{'schema_version':'1.0','task_id':task_id,'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}},'diagnostics':[]}))",
            ]
        ),
        encoding="utf-8",
    )
    client = TestClient(app)

    response = client.post(
        "/tasks/run",
        data={
            "task_id": "task-team-web-closed-loop",
            "title": "team",
            "description": "team",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "python -m pytest -q",
            "agent_mode": "omx_team_patch",
            "patch_coder": f'"{sys.executable}" "{backend}" {{task_id}}',
            "patch_fixer": "",
            "reviewer": "",
            "real_checks": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    job_id = response.headers["location"].rsplit("/", 1)[-1]
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")
    job = _wait_for_job(repository, job_id)

    assert job["status"] == "done"
    assert job["run_id"].startswith("run-")
    assert "return a + b" in (worktree / "calculator.py").read_text(encoding="utf-8")

    detail = client.get(f"/runs/{job['run_id']}")
    assert detail.status_code == 200
    assert "Team Result" in detail.text
    assert "task-team-web-closed-loop" in detail.text


def test_web_docker_agent_preset_job_runs_to_detail(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (worktree / "test_calculator.py").write_text(
        (
            "import unittest\n\n"
            "from calculator import add\n\n\n"
            "class CalculatorTest(unittest.TestCase):\n"
            "    def test_add(self):\n"
            "        self.assertEqual(add(1, 2), 3)\n\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n"
        ),
        encoding="utf-8",
    )
    (worktree / "docker_team_backend.py").write_text(
        "\n".join(
            [
                "import json, pathlib, sys",
                "task_id = sys.argv[1]",
                "prompt = pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')",
                "assert 'Allowed file snapshot' in prompt",
                "print(json.dumps({'schema_version':'1.0','task_id':task_id,'status':'completed','roles':{},'artifacts':{'patch_plan':{'schema_version':'1.0','task_id':task_id,'summary':'fix','operations':[{'op':'replace_text','path':'calculator.py','old':'return a - b','new':'return a + b'}]},'review':{'schema_version':'1.0','task_id':task_id,'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}},'diagnostics':[]}))",
            ]
        ),
        encoding="utf-8",
    )
    client = TestClient(app)

    response = client.post(
        "/tasks/run",
        data={
            "task_id": "task-docker-agent-preset-closed-loop",
            "title": "docker preset",
            "description": "docker preset",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py\ntest_calculator.py\ndocker_team_backend.py",
            "worktree_path": str(worktree),
            "check_command": "python -m unittest -q",
            "agent_mode": "omx_team_patch",
            "command_preset": "team_patch_backend",
            "patch_coder": "",
            "patch_fixer": "",
            "reviewer": "",
            "execution_backend": "docker",
            "sandbox_image": "python:3.12-slim",
            "sandbox_network": "none",
            "sandbox_worktree_mount": "readonly",
            "sandbox_memory_limit": "1g",
            "sandbox_cpu_limit": "1",
            "real_checks": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    job_id = response.headers["location"].rsplit("/", 1)[-1]
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")
    job = _wait_for_job(repository, job_id, timeout_seconds=120)

    assert job["status"] == "done"
    assert job["run_id"].startswith("run-")
    assert "return a + b" in (worktree / "calculator.py").read_text(encoding="utf-8")

    run_dir = tmp_path / ".omx" / "runs" / job["run_id"]
    docker_log = run_dir / "logs" / "docker_sandbox.jsonl"
    assert docker_log.exists()
    docker_log_text = docker_log.read_text(encoding="utf-8")
    assert "/worktree/docker_team_backend.py" in docker_log_text
    assert '"phase": "agent:omx_team_patch:team"' in docker_log_text

    detail = client.get(f"/runs/{job['run_id']}")
    assert detail.status_code == 200
    assert "Docker 执行证据" in detail.text
    assert "python:3.12-slim" in detail.text
    assert "readonly" in detail.text
    assert "/worktree/docker_team_backend.py" in detail.text
    assert "agent:omx_team_patch:team" in detail.text
    assert "Team Result" in detail.text
    assert "task-docker-agent-preset-closed-loop" in detail.text


def test_web_job_marks_halted_run_as_failed(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "examples").mkdir()
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    backend = tmp_path / "team_backend.py"
    backend.write_text(
        "\n".join(
            [
                "import json, sys",
                "task_id = sys.argv[1]",
                "print(json.dumps({'schema_version':'1.0','task_id':task_id,'status':'completed','roles':{},'artifacts':{'patch_plan':{'schema_version':'1.0','task_id':task_id,'summary':'noop','operations':[{'op':'replace_text','path':'calculator.py','old':'missing old text','new':'return a + b'}]},'review':{'schema_version':'1.0','task_id':task_id,'pass':True,'confidence':90,'summary':'ok','issues':[],'blocking':False,'recommended_next_action':'pass'}},'diagnostics':[]}))",
            ]
        ),
        encoding="utf-8",
    )
    client = TestClient(app)

    response = client.post(
        "/tasks/run",
        data={
            "task_id": "task-team-web-halted",
            "title": "team",
            "description": "team",
            "change_type": "bugfix",
            "allowed_paths": "calculator.py",
            "worktree_path": str(worktree),
            "check_command": "python -m pytest -q",
            "agent_mode": "omx_team_patch",
            "patch_coder": f'"{sys.executable}" "{backend}" {{task_id}}',
            "patch_fixer": "",
            "reviewer": "",
            "real_checks": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    job_id = response.headers["location"].rsplit("/", 1)[-1]
    repository = SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db")
    job = _wait_for_job(repository, job_id)

    assert job["status"] == "failed"
    assert job["run_id"].startswith("run-")
    assert "停在 code 阶段" in job["message"]


def _wait_for_job(repository: SQLiteJobRepository, job_id: str, timeout_seconds: int = 10) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        job = repository.get(job_id)
        if job and job["status"] in {"done", "failed"}:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job did not finish: {job_id}")


def _write_run_state(tmp_path: Path, run_id: str, task_id: str, status: RunStatus, phase: str) -> None:
    run_dir = tmp_path / ".omx" / "runs" / run_id
    (run_dir / "logs").mkdir(parents=True)
    (run_dir / "task.json").write_text(f'{{"task_id": "{task_id}"}}', encoding="utf-8")
    state = RunState(
        run_id=run_id,
        task_id=task_id,
        status=status,
        attempt=1,
        max_attempts=1,
        current_phase=phase,
        started_at=datetime(2026, 5, 23, 9, 0, 0),
        updated_at=datetime(2026, 5, 23, 9, 1, 0),
        artifacts={"run_dir": str(run_dir)},
    )
    (run_dir / "run_state.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")
