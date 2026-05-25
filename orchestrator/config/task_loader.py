from __future__ import annotations

import json
from pathlib import Path

from orchestrator.domain.models.task import TaskConfig


class TaskLoader:
    def load(self, path: Path | str) -> TaskConfig:
        task_path = Path(path)
        payload = json.loads(task_path.read_text(encoding="utf-8-sig"))
        return TaskConfig.model_validate(payload)
