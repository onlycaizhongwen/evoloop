from __future__ import annotations

from pydantic import BaseModel, Field


class CheckCommandResult(BaseModel):
    name: str
    command: str | None = None
    passed: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    score: int = 0


class HardCheckResult(BaseModel):
    commands: list[CheckCommandResult] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(command.passed for command in self.commands)

    @property
    def score(self) -> int:
        return sum(command.score for command in self.commands if command.passed)

    def first_failure_reason(self) -> str | None:
        for command in self.commands:
            if not command.passed:
                return f"{command.name} failed"
        return None
