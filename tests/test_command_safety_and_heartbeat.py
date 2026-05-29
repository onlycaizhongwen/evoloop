from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

from orchestrator.domain.enums import ChangeType, ExecutionBackend
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import CheckCommands, TaskConfig
from orchestrator.domain.services.exceptions import SafetyViolation
from orchestrator.domain.services.safety_policy import SafetyPolicy
from orchestrator.infrastructure.checks.shell_check_runner import ShellCheckRunner
from orchestrator.infrastructure.command.cancellation import CancellationRegistry, CommandCancelled
from orchestrator.infrastructure.command.command_result import CommandExecutionResult
from orchestrator.infrastructure.command.docker_sandbox_runner import DockerSandboxRunner
from orchestrator.infrastructure.command.safe_command_runner import SafeCommandRunner
from orchestrator.infrastructure.logging.file_heartbeat import FileHeartbeat


def make_task(tmp_path: Path, command_timeout: int = 5, heartbeat_interval: int = 1) -> TaskConfig:
    return TaskConfig(
        task_id="task-001",
        title="Test",
        description="Test task",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path,
        allowed_paths=["."],
        forbidden_paths=[".env"],
        check_commands=CheckCommands(test=None),
        command_timeout_seconds=command_timeout,
        heartbeat_interval_seconds=heartbeat_interval,
    )


def make_state(tmp_path: Path) -> RunState:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    return RunState(run_id="run-test", task_id="task-001", max_attempts=1, artifacts={"run_dir": str(run_dir)})


def test_forbidden_command_is_blocked(tmp_path: Path):
    task = make_task(tmp_path)
    runner = SafeCommandRunner()
    with pytest.raises(SafetyViolation):
        runner.run(task, "rm -rf ./something", phase="test")


def test_allowed_command_prefix_accepts_python_module(tmp_path: Path):
    task = make_task(tmp_path)
    SafetyPolicy().validate_command(f"\"{sys.executable}\" -m pytest -q tests", task)


def test_allowed_command_prefix_can_be_configured(tmp_path: Path):
    task = make_task(tmp_path)
    task.allowed_command_prefixes = ["git status"]
    SafetyPolicy().validate_command("git status --short", task)


def test_unknown_command_is_blocked_by_allowlist(tmp_path: Path):
    task = make_task(tmp_path)
    with pytest.raises(SafetyViolation, match="not allowed by allowlist"):
        SafetyPolicy().validate_command("git status --short", task)


def test_dangerous_command_is_blocked_before_allowlist(tmp_path: Path):
    task = make_task(tmp_path)
    task.allowed_command_prefixes = ["rm"]
    with pytest.raises(SafetyViolation, match="forbidden by safety policy"):
        SafetyPolicy().validate_command("rm -rf ./something", task)


def test_shell_check_runner_reports_allowlist_rejection(tmp_path: Path):
    task = make_task(tmp_path)
    task.check_commands = CheckCommands(test="git status --short")
    result = ShellCheckRunner().run_all(task)
    assert not result.passed
    assert result.commands[0].exit_code == 126
    assert "not allowed by allowlist" in result.commands[0].stderr


def test_heartbeat_updates_state_and_log(tmp_path: Path):
    task = make_task(tmp_path, command_timeout=5, heartbeat_interval=1)
    state = make_state(tmp_path)
    runner = SafeCommandRunner(heartbeat=FileHeartbeat())
    command = f"\"{sys.executable}\" -c \"import time; time.sleep(2); print('done')\""

    result = runner.run(task, command, phase="test", state=state)

    assert result.exit_code == 0
    assert state.last_heartbeat_at is not None
    heartbeat_log = Path(state.artifacts["run_dir"]) / "logs" / "heartbeat.log"
    assert heartbeat_log.exists()
    assert "phase=test" in heartbeat_log.read_text(encoding="utf-8")


def test_timeout_returns_124_for_child_process(tmp_path: Path):
    task = make_task(tmp_path, command_timeout=1, heartbeat_interval=1)
    runner = SafeCommandRunner()
    command = f"\"{sys.executable}\" -c \"import subprocess, sys; subprocess.run([sys.executable, '-c', 'import time; time.sleep(30)'])\""

    result = runner.run(task, command, phase="test")

    assert result.exit_code == 124
    assert result.timed_out
    assert "command timed out after 1s" in result.stderr


def test_cancellation_registry_terminates_running_local_command(tmp_path: Path):
    task = make_task(tmp_path, command_timeout=30, heartbeat_interval=1)
    registry = CancellationRegistry()
    runner = SafeCommandRunner(cancellation_registry=registry, cancellation_key="job-cancel-test")
    command = f"\"{sys.executable}\" -c \"import time; time.sleep(30)\""
    errors: list[BaseException] = []

    def run_command() -> None:
        try:
            runner.run(task, command, phase="test")
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=run_command)
    thread.start()
    deadline = time.monotonic() + 5
    while not registry.cancel("job-cancel-test") and time.monotonic() < deadline:
        time.sleep(0.05)
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert any(isinstance(error, CommandCancelled) for error in errors)


class RecordingRunner:
    def __init__(self, label: str):
        self.label = label
        self.calls: list[tuple[TaskConfig, str, str]] = []

    def run(self, task: TaskConfig, command: str, phase: str, state=None, cwd=None):
        self.calls.append((task, command, phase))
        return CommandExecutionResult(command=command, exit_code=0, stdout=self.label, stderr="", duration_seconds=0.0)


def test_safe_command_runner_uses_local_backend_by_default(tmp_path: Path):
    task = make_task(tmp_path)
    local = RecordingRunner("local")
    docker = RecordingRunner("docker")
    runner = SafeCommandRunner(local_runner=local, docker_runner=docker)

    result = runner.run(task, f"\"{sys.executable}\" --version", phase="test")

    assert result.stdout == "local"
    assert len(local.calls) == 1
    assert docker.calls == []


def test_safe_command_runner_uses_docker_backend_when_configured(tmp_path: Path):
    task = make_task(tmp_path)
    task.execution_backend = ExecutionBackend.DOCKER
    local = RecordingRunner("local")
    docker = RecordingRunner("docker")
    runner = SafeCommandRunner(local_runner=local, docker_runner=docker)

    result = runner.run(task, f"\"{sys.executable}\" --version", phase="test")

    assert result.stdout == "docker"
    assert local.calls == []
    assert len(docker.calls) == 1


def test_docker_runner_builds_readonly_worktree_command(tmp_path: Path):
    task = make_task(tmp_path)
    task.execution_backend = ExecutionBackend.DOCKER
    task.sandbox.image = "python:3.12-slim"
    state = make_state(tmp_path)

    command = DockerSandboxRunner().build_docker_command(task, "python -m pytest -q", state=state)

    assert "docker" in command
    assert "python:3.12-slim" in command
    assert ":/worktree:ro" in command.replace("\\", "/")
    assert ":/run:rw" in command.replace("\\", "/")
    assert "--network none" in command
    assert "python -m pytest -q" in command
