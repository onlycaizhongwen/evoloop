from __future__ import annotations

from typing import Protocol

from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig


class AgentPort(Protocol):
    def run_coder(self, task: TaskConfig, state: RunState) -> None:
        ...

    def run_fixer(self, task: TaskConfig, state: RunState, reason: HardCheckResult | QualityReport) -> None:
        ...

    def run_reviewer(self, task: TaskConfig, state: RunState, repair_prompt: str | None = None) -> str:
        ...
