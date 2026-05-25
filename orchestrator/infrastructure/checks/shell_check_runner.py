from __future__ import annotations

from orchestrator.domain.models.check_result import CheckCommandResult, HardCheckResult
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig
from orchestrator.domain.services.exceptions import SafetyViolation
from orchestrator.infrastructure.command.safe_command_runner import SafeCommandRunner


class ShellCheckRunner:
    SCORE_BY_NAME = {
        "test": 40,
        "lint": 10,
        "typecheck": 10,
    }

    def run_all(self, task: TaskConfig) -> HardCheckResult:
        results: list[CheckCommandResult] = []
        for name, command in [
            ("test", task.check_commands.test),
            ("lint", task.check_commands.lint),
            ("typecheck", task.check_commands.typecheck),
        ]:
            if not command:
                results.append(
                    CheckCommandResult(
                        name=name,
                        command=None,
                        passed=True,
                        stdout="skipped: command not configured",
                        score=self.SCORE_BY_NAME[name],
                    )
                )
                continue
            results.append(self._run_command(task, name, command))
        return HardCheckResult(commands=results)

    def _run_command(self, task: TaskConfig, name: str, command: str) -> CheckCommandResult:
        try:
            completed = self.command_runner.run(task, command, phase=f"check:{name}", state=self.state)
            passed = completed.exit_code == 0
            return CheckCommandResult(
                name=name,
                command=command,
                passed=passed,
                exit_code=completed.exit_code,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_seconds=completed.duration_seconds,
                score=self.SCORE_BY_NAME[name] if passed else 0,
            )
        except SafetyViolation as exc:
            return CheckCommandResult(
                name=name,
                command=command,
                passed=False,
                exit_code=126,
                stderr=str(exc),
                score=0,
            )
    def __init__(self, command_runner: SafeCommandRunner | None = None, state: RunState | None = None):
        self.command_runner = command_runner or SafeCommandRunner()
        self.state = state
