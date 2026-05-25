from __future__ import annotations

from datetime import datetime
from pathlib import Path

from orchestrator.domain.models.run_state import RunState


class PhaseLogger:
    def info(self, state: RunState, phase: str, event: str, **fields: object) -> None:
        run_dir = Path(state.artifacts["run_dir"])
        log_dir = run_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        details = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
        line = (
            f"{datetime.now().isoformat()} INFO run_id={state.run_id} task_id={state.task_id} "
            f"phase={phase} attempt={state.attempt} event={event}"
        )
        if details:
            line = f"{line} {details}"
        with (log_dir / "phase.log").open("a", encoding="utf-8") as file:
            file.write(line + "\n")
