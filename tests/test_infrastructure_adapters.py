from __future__ import annotations

import sys
from pathlib import Path

from orchestrator.domain.enums import ChangeType
from orchestrator.domain.models.task import CheckCommands, TaskConfig
from orchestrator.config.task_loader import TaskLoader
from orchestrator.infrastructure.checks.shell_check_runner import ShellCheckRunner
from orchestrator.infrastructure.git.git_diff_provider import GitDiffProvider
from orchestrator.infrastructure.persistence.file_state_repository import FileStateRepository


def make_task(tmp_path: Path, command: str) -> TaskConfig:
    return TaskConfig(
        task_id="task-001",
        title="Test",
        description="Test task",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path,
        allowed_paths=["."],
        forbidden_paths=[".env"],
        check_commands=CheckCommands(test=command),
        command_timeout_seconds=5,
    )


def test_shell_check_runner_passes_command(tmp_path: Path):
    task = make_task(tmp_path, f"\"{sys.executable}\" -c \"print('ok')\"")
    result = ShellCheckRunner().run_all(task)
    assert result.passed
    assert result.commands[0].score == 40
    assert "ok" in result.commands[0].stdout


def test_shell_check_runner_fails_command(tmp_path: Path):
    task = make_task(tmp_path, f"\"{sys.executable}\" -c \"import sys; sys.exit(3)\"")
    result = ShellCheckRunner().run_all(task)
    assert not result.passed
    assert result.commands[0].exit_code == 3
    assert result.commands[0].score == 0


def test_git_diff_provider_returns_empty_stats_outside_git(tmp_path: Path):
    task = make_task(tmp_path, f"\"{sys.executable}\" -c \"print('ok')\"")
    stats = GitDiffProvider().get_diff_stats(task)
    assert stats.changed_files == 0
    assert stats.total_changed_lines == 0


def test_file_state_repository_generates_unique_run_ids(tmp_path: Path):
    task = make_task(tmp_path, f"\"{sys.executable}\" -c \"print('ok')\"")
    repository = FileStateRepository(tmp_path / "runs")
    first = repository.create_run(task)
    second = repository.create_run(task)
    assert first.run_id != second.run_id
    assert Path(first.artifacts["run_dir"]).exists()
    assert Path(second.artifacts["run_dir"]).exists()


def test_task_loader_accepts_utf8_bom_json(tmp_path: Path):
    task = make_task(tmp_path, f"\"{sys.executable}\" -c \"print('ok')\"")
    task_path = tmp_path / "task.json"
    task_path.write_text(task.model_dump_json(), encoding="utf-8-sig")

    loaded = TaskLoader().load(task_path)

    assert loaded.task_id == "task-001"
