from __future__ import annotations

from typing import Protocol

from orchestrator.domain.models.diff import DiffStats
from orchestrator.domain.models.task import TaskConfig


class DiffProviderPort(Protocol):
    def get_diff_stats(self, task: TaskConfig) -> DiffStats:
        ...
