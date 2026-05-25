from __future__ import annotations

import subprocess
from pathlib import Path

from orchestrator.domain.enums import ChangeType
from orchestrator.domain.models.diff import DiffStats
from orchestrator.domain.models.task import CheckCommands, TaskConfig
from orchestrator.domain.services.diff_risk import DiffRiskService
from orchestrator.infrastructure.git.git_diff_provider import GitDiffProvider


def make_task(repo: Path, change_type: ChangeType = ChangeType.BUGFIX) -> TaskConfig:
    return TaskConfig(
        task_id="task-001",
        title="Git diff test",
        description="Exercise real git diff stats",
        change_type=change_type,
        repo_path=repo,
        worktree_path=repo,
        allowed_paths=["src", "tests", "config"],
        forbidden_paths=[".env", "secrets"],
        check_commands=CheckCommands(test="pytest"),
    )


def init_repo(repo: Path) -> None:
    run(repo, "git", "init")
    run(repo, "git", "config", "user.email", "test@example.com")
    run(repo, "git", "config", "user.name", "Test User")
    write(repo / "src" / "service.py", "def value():\n    return 1\n")
    write(repo / "tests" / "test_service.py", "def test_value():\n    assert True\n")
    write(repo / "config" / "app.yml", "enabled: true\n")
    run(repo, "git", "add", ".")
    run(repo, "git", "commit", "-m", "initial")


def run(cwd: Path, *command: str) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append(path: Path, content: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + content, encoding="utf-8")


def test_real_git_diff_source_and_tests_changed(tmp_path: Path):
    init_repo(tmp_path)
    append(tmp_path / "src" / "service.py", "\ndef other():\n    return 2\n")
    append(tmp_path / "tests" / "test_service.py", "\ndef test_other():\n    assert True\n")

    stats = GitDiffProvider().get_diff_stats(make_task(tmp_path))

    assert stats.changed_files == 2
    assert stats.total_changed_lines == 6
    assert stats.max_file_changed_lines == 3
    assert not stats.source_changed_without_tests
    assert not stats.only_tests_changed
    assert DiffRiskService().calculate_score(stats, ChangeType.BUGFIX) == 10


def test_real_git_diff_source_without_tests_penalizes_feature_and_bugfix(tmp_path: Path):
    init_repo(tmp_path)
    append(tmp_path / "src" / "service.py", "\ndef changed():\n    return 3\n")

    stats = GitDiffProvider().get_diff_stats(make_task(tmp_path, ChangeType.BUGFIX))

    assert stats.changed_files == 1
    assert stats.source_changed_without_tests
    assert DiffRiskService().calculate_score(stats, ChangeType.BUGFIX) == 8
    assert DiffRiskService().calculate_score(stats, ChangeType.REFACTOR) == 10


def test_real_git_diff_large_diff_penalty(tmp_path: Path):
    init_repo(tmp_path)
    append(tmp_path / "src" / "service.py", "".join(f"line_{index} = {index}\n" for index in range(201)))

    stats = GitDiffProvider().get_diff_stats(make_task(tmp_path))

    assert stats.changed_files == 1
    assert stats.total_changed_lines == 201
    assert DiffRiskService().calculate_score(stats, ChangeType.BUGFIX) == 6


def test_real_git_diff_deleted_file_and_forbidden_path_penalty(tmp_path: Path):
    init_repo(tmp_path)
    write(tmp_path / ".env", "SECRET=0\n")
    run(tmp_path, "git", "add", ".env")
    run(tmp_path, "git", "commit", "-m", "track forbidden file")
    (tmp_path / "src" / "service.py").unlink()
    append(tmp_path / ".env", "SECRET=1\n")

    stats = GitDiffProvider().get_diff_stats(make_task(tmp_path))

    assert stats.changed_files == 2
    assert stats.deleted_files == 1
    assert stats.touches_forbidden_path
    assert DiffRiskService().calculate_score(stats, ChangeType.CONFIG) == 3


def test_diff_risk_config_does_not_use_source_without_tests_penalty():
    stats = DiffStats(changed_files=1, total_changed_lines=10, source_changed_without_tests=True)
    assert DiffRiskService().calculate_score(stats, ChangeType.CONFIG) == 10
