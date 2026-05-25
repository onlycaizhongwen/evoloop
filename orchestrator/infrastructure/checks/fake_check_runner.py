from __future__ import annotations

from orchestrator.domain.models.check_result import CheckCommandResult, HardCheckResult
from orchestrator.domain.models.task import TaskConfig


class FakeCheckRunner:
    def __init__(self, pass_all: bool = True):
        self.pass_all = pass_all
        self.calls = 0

    def run_all(self, task: TaskConfig) -> HardCheckResult:
        self.calls += 1
        return HardCheckResult(
            commands=[
                CheckCommandResult(
                    name="test",
                    command=task.check_commands.test,
                    passed=self.pass_all,
                    exit_code=0 if self.pass_all else 1,
                    stdout="fake tests passed" if self.pass_all else "fake tests failed",
                    score=40 if self.pass_all else 0,
                ),
                CheckCommandResult(name="lint", command=task.check_commands.lint, passed=True, score=10),
                CheckCommandResult(
                    name="typecheck",
                    command=task.check_commands.typecheck,
                    passed=True,
                    score=10,
                ),
            ]
        )
