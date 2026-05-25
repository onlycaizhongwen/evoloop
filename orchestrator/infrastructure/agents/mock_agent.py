from __future__ import annotations

import json

from orchestrator.domain.models.check_result import HardCheckResult
from orchestrator.domain.models.quality_report import QualityReport
from orchestrator.domain.models.run_state import RunState
from orchestrator.domain.models.task import TaskConfig


class MockAgent:
    def __init__(self, reviewer_outputs: list[str] | None = None):
        self.reviewer_outputs = reviewer_outputs or []
        self.coder_calls = 0
        self.fixer_calls = 0
        self.reviewer_calls = 0

    def run_coder(self, task: TaskConfig, state: RunState) -> None:
        self.coder_calls += 1

    def run_fixer(self, task: TaskConfig, state: RunState, reason: HardCheckResult | QualityReport) -> None:
        self.fixer_calls += 1

    def run_reviewer(self, task: TaskConfig, state: RunState, repair_prompt: str | None = None) -> str:
        self.reviewer_calls += 1
        if self.reviewer_outputs:
            return self.reviewer_outputs.pop(0)
        return json.dumps(
            {
                "schema_version": "1.0",
                "task_id": task.task_id,
                "pass": True,
                "confidence": 92,
                "summary": "Mock review passed.",
                "issues": [],
                "blocking": False,
                "recommended_next_action": "pass",
            },
            ensure_ascii=False,
        )
