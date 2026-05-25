from __future__ import annotations

from typing import Protocol

from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.task import TaskConfig


class CheckRunnerPort(Protocol):
    def run_all(self, task: TaskConfig) -> HardCheckResult:
        ...
