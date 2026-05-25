from __future__ import annotations

from typing import Protocol

from orchestrator.domain.models.run_state import RunState


class HeartbeatPort(Protocol):
    def beat(self, state: RunState, phase: str, message: str) -> None:
        ...
