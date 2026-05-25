from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from orchestrator.domain.enums import RunStatus


class RunState(BaseModel):
    run_id: str
    task_id: str
    status: RunStatus = RunStatus.RUNNING
    attempt: int = 0
    max_attempts: int
    current_phase: str = "init"
    started_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_heartbeat_at: datetime | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)

    def can_attempt(self) -> bool:
        return self.attempt < self.max_attempts

    def next_attempt(self) -> int:
        self.attempt += 1
        self.updated_at = datetime.now()
        return self.attempt

    def set_phase(self, phase: str) -> None:
        self.current_phase = phase
        self.updated_at = datetime.now()
