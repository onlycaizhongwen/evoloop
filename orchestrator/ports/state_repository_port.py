from __future__ import annotations

from typing import Protocol

from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.review import ReviewResult
from orchestrator.domain.models.rule_proposal import RuleProposal
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig


class StateRepositoryPort(Protocol):
    def create_run(self, task: TaskConfig) -> RunState:
        ...

    def save_state(self, state: RunState) -> None:
        ...

    def save_hard_check(self, state: RunState, result: HardCheckResult) -> None:
        ...

    def save_review(self, state: RunState, review: ReviewResult) -> None:
        ...

    def save_quality_report(self, state: RunState, report: QualityReport) -> None:
        ...

    def save_malformed_review(self, state: RunState, retry_count: int, raw_output: str) -> None:
        ...

    def write_final_report(self, state: RunState, content: str) -> None:
        ...

    def write_rule_proposal(self, state: RunState, proposal: RuleProposal, content: str) -> None:
        ...
