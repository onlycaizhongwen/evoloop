from __future__ import annotations

from datetime import datetime
from pathlib import Path

from orchestrator.domain.models.run_state import RunState


class FileHeartbeat:
    def beat(self, state: RunState, phase: str, message: str) -> None:
        now = datetime.now()
        state.last_heartbeat_at = now
        run_dir = Path(state.artifacts["run_dir"])
        log_dir = run_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "heartbeat.log").open("a", encoding="utf-8") as file:
            file.write(
                f"{now.isoformat()} run_id={state.run_id} task_id={state.task_id} "
                f"phase={phase} attempt={state.attempt} {message}\n"
            )
