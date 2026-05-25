from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.domain.enums import ChangeType, ExecutionBackend, PermissionLevel
from orchestrator.domain.models.diff import DiffStats
from orchestrator.domain.models.task import CheckCommands, TaskConfig
from orchestrator.domain.services.diff_risk import DiffRiskService
from orchestrator.domain.services.exceptions import MalformedReview
from orchestrator.domain.services.review_validator import ReviewValidator
from orchestrator.domain.services.safety_policy import SafetyPolicy


def make_task(change_type: ChangeType = ChangeType.BUGFIX) -> TaskConfig:
    return TaskConfig(
        task_id="task-001",
        title="Test",
        description="Test task",
        change_type=change_type,
        repo_path=Path("."),
        worktree_path=Path("."),
        allowed_paths=["orchestrator", "tests"],
        forbidden_paths=[".env", "secrets"],
        check_commands=CheckCommands(test="pytest"),
    )


def test_config_change_type_maps_to_elevated():
    task = make_task(ChangeType.CONFIG)
    permission, reason = SafetyPolicy().precheck(task)
    assert permission == PermissionLevel.ELEVATED
    assert reason == "change_type_config_requires_elevated"


def test_review_task_id_mismatch_is_malformed():
    task = make_task()
    raw = """{"schema_version":"1.0","task_id":"other","pass":true,"confidence":90,"summary":"ok","issues":[],"blocking":false,"recommended_next_action":"pass"}"""
    with pytest.raises(MalformedReview, match="task_id_mismatch"):
        ReviewValidator().parse_and_validate(raw, task)


def test_refactor_source_without_tests_no_penalty():
    stats = DiffStats(changed_files=2, total_changed_lines=40, source_changed_without_tests=True)
    assert DiffRiskService().calculate_score(stats, ChangeType.REFACTOR) == 10


def test_bugfix_source_without_tests_penalty():
    stats = DiffStats(changed_files=2, total_changed_lines=40, source_changed_without_tests=True)
    assert DiffRiskService().calculate_score(stats, ChangeType.BUGFIX) == 8


def test_task_config_parses_docker_sandbox_config(tmp_path: Path):
    task = TaskConfig(
        task_id="task-docker",
        title="Docker task",
        description="Run checks in Docker",
        change_type=ChangeType.BUGFIX,
        repo_path=tmp_path,
        worktree_path=tmp_path,
        execution_backend="docker",
        sandbox={
            "image": "python:3.12-slim",
            "network": "none",
            "worktree_mount": "readonly",
            "memory_limit": "1g",
            "cpu_limit": 1,
        },
        check_commands=CheckCommands(test="python -m pytest -q"),
    )

    assert task.execution_backend == ExecutionBackend.DOCKER
    assert task.sandbox.image == "python:3.12-slim"
    assert task.sandbox.worktree_mount == "readonly"
    assert task.sandbox.memory_limit == "1g"
    assert task.sandbox.cpu_limit == 1
