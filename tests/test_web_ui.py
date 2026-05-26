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
from orchestrator.domain.models.run_state import RunState
from orchestrator.infrastructure.persistence.sqlite_job_repository import SQLiteJobRepository
from orchestrator.interfaces.web.main import app


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
    SQLiteJobRepository(tmp_path / ".omx" / "orchestrator.db").create(
        {
            "job_id": "job-test",
            "status": "running",
            "message": "running",
            "task_path": "task.json",
            "run_id": "",
        }
    )

    response = TestClient(app).get("/jobs/job-test")

    assert response.status_code == 200
    assert "job-test" in response.text
    assert "running" in response.text


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
    assert "任务已提交" in response.text
    assert "锛" not in response.text
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
    assert "Docker 执行证据" in response.text
    assert "本次运行没有 Docker sandbox 执行记录" in response.text


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
